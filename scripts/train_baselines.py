"""Train and evaluate the TF-IDF baselines (Phase 3)."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import joblib

from clauselens.baselines import encode, evaluate, fit, load_records, make_models, predict
from clauselens.data.taxonomy import Taxonomy
from clauselens.paths import DATA, PROCESSED, ROOT

log = logging.getLogger("train_baselines")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--real-dir", type=Path, default=PROCESSED / "v1")
    p.add_argument("--synth-dir", type=Path, default=PROCESSED / "synth_v1")
    p.add_argument("--gold", type=Path, default=DATA / "gold" / "gold_v1.jsonl")
    p.add_argument("--train-on", choices=("both", "real", "synth"), default="both")
    p.add_argument("--out", type=Path, default=ROOT / "reports" / "baselines_v1.json")
    p.add_argument("--models-dir", type=Path, default=ROOT / "models")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    labels = Taxonomy.load().with_other(["out_of_domain"]).clause_ids
    real = {s: load_records(args.real_dir / f"{s}.jsonl") for s in ("train", "val", "test")}
    synth = {s: load_records(args.synth_dir / f"{s}.jsonl") for s in ("train", "val", "test")}

    train = (real["train"] if args.train_on != "synth" else []) + (
        synth["train"] if args.train_on != "real" else []
    )
    if not train:
        raise SystemExit("no training data found; run build_dataset_v1.py / generate_synthetic.py")
    eval_sets = {
        "real_val": real["val"],
        "real_test": real["test"],
        "synth_val": synth["val"],
        "synth_test": synth["test"],
        "gold": load_records(args.gold),
    }
    eval_sets = {k: v for k, v in eval_sets.items() if v}
    log.info("train=%d  eval sets=%s", len(train), {k: len(v) for k, v in eval_sets.items()})

    x_train, y_train = [r["text"] for r in train], encode(train, labels)
    results: dict[str, dict] = {"train_on": args.train_on, "n_train": len(train), "models": {}}
    args.models_dir.mkdir(parents=True, exist_ok=True)

    for name, model in make_models().items():
        active = fit(model, x_train, y_train)
        joblib.dump(
            {"model": model, "labels": labels, "active": active},
            args.models_dir / f"{name}.joblib",
        )
        results["models"][name] = {
            split: evaluate(
                encode(rs, labels), predict(model, [r["text"] for r in rs], active), labels
            )
            for split, rs in eval_sets.items()
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _print(results, eval_sets)


def _print(results: dict, eval_sets: dict) -> None:
    sets = list(eval_sets)
    print(f"\ntrain_on={results['train_on']}  n_train={results['n_train']}")
    print(f"\n{'model':16}" + "".join(f"{s + ' mic/mac':>22}" for s in sets))
    for name, per_set in results["models"].items():
        row = "".join(
            f"{per_set[s]['micro_f1']:>11.3f}/{per_set[s]['macro_f1']:<10.3f}" for s in sets
        )
        print(f"{name:16}{row}")
    best = results["models"]["tfidf_lr"]
    for s in ("real_test", "synth_test", "gold"):
        if s in best:
            print(f"\nper-label F1 (tfidf_lr, {s}):")
            for lab, m in best[s]["per_label"].items():
                print(f"  {lab:28} f1={m['f1']:.2f}  p={m['precision']:.2f}  r={m['recall']:.2f}  "
                      f"n={m['support']}")  # fmt: skip


if __name__ == "__main__":
    main()
