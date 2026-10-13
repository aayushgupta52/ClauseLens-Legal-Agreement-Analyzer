"""Fine-tune a BERT-style encoder for multi-label clause classification (Phase 4)."""

from __future__ import annotations

import json
import random
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import transformers
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from clauselens.baselines import encode, evaluate
from clauselens.classification import class_pos_weights, compact_metrics, multihot_from_scores

HEAD_FILE = "clauselens_head.json"  # labels + active mask + max_len, saved next to the HF files


@dataclass
class TrainConfig:
    model_name: str = "nlpaueb/legal-bert-base-uncased"
    max_len: int = 256
    epochs: int = 4
    batch_size: int = 16
    lr: float = 3e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    grad_clip: float = 1.0
    pos_weight_cap: float = 5.0  # BCE positive-class weight, capped for rare labels
    fp16: bool = True  # only used on CUDA
    seed: int = 42
    select_on: str = "real_val"  # eval set used to pick the best epoch (never a test set)
    max_train_examples: int | None = None  # for smoke runs


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class _TextDataset(Dataset):
    def __init__(self, tokenizer, texts: Sequence[str], y: np.ndarray | None, max_len: int):
        enc = tokenizer(list(texts), truncation=True, max_length=max_len)
        keys = list(enc.keys())
        self.features = [{k: enc[k][i] for k in keys} for i in range(len(texts))]
        self.y = None if y is None else torch.as_tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, i: int) -> dict[str, Any]:
        item = dict(self.features[i])
        if self.y is not None:
            item["labels"] = self.y[i]
        return item


def _collate(tokenizer):
    def fn(batch: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        labels = [b.pop("labels") for b in batch] if "labels" in batch[0] else None
        out = tokenizer.pad(batch, return_tensors="pt")
        if labels is not None:
            out["labels"] = torch.stack(labels)
        return out

    return fn


def truncated_fraction(tokenizer, texts: Sequence[str], max_len: int) -> float:
    """Share of texts that do not fit in `max_len` tokens (report this; it hides information)."""
    lengths = tokenizer(list(texts), add_special_tokens=False)["input_ids"]
    return float(np.mean([len(x) > max_len - 2 for x in lengths])) if lengths else 0.0


@torch.no_grad()
def score_texts(
    model, tokenizer, texts: Sequence[str], active: np.ndarray, *,
    max_len: int, batch_size: int = 32, device: torch.device | None = None,
) -> np.ndarray:  # fmt: skip
    """Logits (n, n_labels); labels that were never seen in training get -inf."""
    device = device or next(model.parameters()).device
    if not len(texts):
        return np.zeros((0, len(active)), dtype=np.float32)
    model.eval()
    ds = _TextDataset(tokenizer, texts, None, max_len)
    order = np.argsort(
        [len(f["input_ids"]) for f in ds.features]
    )  # similar lengths -> less padding
    out = np.full((len(texts), len(active)), -np.inf, dtype=np.float32)
    for start in range(0, len(order), batch_size):
        idx = order[start : start + batch_size]
        batch = tokenizer.pad([ds.features[i] for i in idx], return_tensors="pt").to(device)
        logits = model(**batch).logits.float().cpu().numpy()
        logits[:, ~active] = -np.inf
        out[idx] = logits
    return out


def evaluate_sets(
    model, tokenizer, eval_sets: dict[str, list[dict]], labels: Sequence[str],
    active: np.ndarray, cfg: TrainConfig, device: torch.device,
) -> dict[str, dict[str, Any]]:  # fmt: skip
    results = {}
    for name, records in eval_sets.items():
        scores = score_texts(
            model, tokenizer, [r["text"] for r in records], active,
            max_len=cfg.max_len, batch_size=cfg.batch_size * 2, device=device,
        )  # fmt: skip
        results[name] = evaluate(encode(records, labels), multihot_from_scores(scores), labels)
    return results


def train(
    train_records: list[dict[str, Any]],
    eval_sets: dict[str, list[dict[str, Any]]],
    labels: Sequence[str],
    cfg: TrainConfig,
    out_dir: Path,
) -> dict[str, Any]:
    """Fine-tune, keep the best epoch on `cfg.select_on`, save model + report dict."""
    started = time.time()
    set_seed(cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = cfg.fp16 and device.type == "cuda"

    if cfg.max_train_examples and len(train_records) > cfg.max_train_examples:
        rng = random.Random(cfg.seed)
        train_records = rng.sample(train_records, cfg.max_train_examples)

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)
    y = encode(train_records, labels)
    active = y.sum(axis=0) > 0
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.model_name,
        num_labels=len(labels),
        problem_type="multi_label_classification",
        id2label=dict(enumerate(labels)),
        label2id={lab: i for i, lab in enumerate(labels)},
    ).to(device)

    pos_weight = class_pos_weights(y, active, cfg.pos_weight_cap)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.as_tensor(pos_weight, device=device))

    dataset = _TextDataset(tokenizer, [r["text"] for r in train_records], y, cfg.max_len)
    loader = DataLoader(
        dataset, batch_size=cfg.batch_size, shuffle=True, collate_fn=_collate(tokenizer),
        generator=torch.Generator().manual_seed(cfg.seed),
    )  # fmt: skip

    no_decay = ("bias", "LayerNorm.weight")
    params = [
        {"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)],
         "weight_decay": cfg.weight_decay},
        {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)],
         "weight_decay": 0.0},
    ]  # fmt: skip
    optimizer = torch.optim.AdamW(params, lr=cfg.lr)
    total_steps = max(1, len(loader) * cfg.epochs)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(cfg.warmup_ratio * total_steps), total_steps
    )
    scaler_cls = getattr(torch.amp, "GradScaler", None)
    scaler = (
        scaler_cls("cuda", enabled=use_amp)
        if scaler_cls
        else torch.cuda.amp.GradScaler(enabled=use_amp)
    )

    select_on = cfg.select_on if cfg.select_on in eval_sets else next(iter(eval_sets), None)
    best_score, best_epoch, best_state = -1.0, cfg.epochs, None
    history: list[dict[str, Any]] = []

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        t0, running = time.time(), 0.0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            targets = batch.pop("labels")
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                logits = model(**batch).logits
            loss = loss_fn(logits.float(), targets)
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running += loss.item()

        metrics = evaluate_sets(model, tokenizer, eval_sets, labels, active, cfg, device)
        entry = {
            "epoch": epoch,
            "train_loss": round(running / len(loader), 5),
            "seconds": round(time.time() - t0, 1),
            "metrics": compact_metrics(metrics),
        }
        history.append(entry)
        print(f"epoch {epoch}/{cfg.epochs} loss={entry['train_loss']} ({entry['seconds']}s)  "
              + "  ".join(f"{k}: {v['micro_f1']:.3f}/{v['macro_f1']:.3f}"
                          for k, v in entry["metrics"].items()))  # fmt: skip
        score = metrics[select_on]["macro_f1"] if select_on else float(epoch)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    final = evaluate_sets(model, tokenizer, eval_sets, labels, active, cfg, device)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    head = {"labels": list(labels), "active": active.tolist(), "max_len": cfg.max_len,
            "base_model": cfg.model_name}  # fmt: skip
    (out_dir / HEAD_FILE).write_text(json.dumps(head, indent=2), encoding="utf-8")

    return {
        "config": asdict(cfg),
        "device": str(device),
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__},
        "n_train": len(train_records),
        "truncated_train_fraction": round(
            truncated_fraction(tokenizer, [r["text"] for r in train_records], cfg.max_len), 4
        ),
        "inactive_labels": [lab for lab, a in zip(labels, active, strict=True) if not a],
        "selected_on": select_on,
        "best_epoch": best_epoch,
        "history": history,
        "final": final,
        "seconds": round(time.time() - started, 1),
    }
