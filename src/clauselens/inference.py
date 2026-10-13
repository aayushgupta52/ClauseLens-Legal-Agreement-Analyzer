"""Load a fine-tuned clause classifier and run it on texts or whole documents."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from clauselens.classification import multihot_from_scores
from clauselens.finetune import HEAD_FILE, score_texts
from clauselens.segment import segment_document


class ClauseClassifier:
    def __init__(self, model_dir: str | Path, device: str | None = None) -> None:
        model_dir = Path(model_dir)
        head = json.loads((model_dir / HEAD_FILE).read_text(encoding="utf-8"))
        self.labels: list[str] = head["labels"]
        self.active = np.asarray(head["active"], dtype=bool)
        self.max_len: int = head["max_len"]
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device).eval()
        )

    def scores(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        return score_texts(
            self.model, self.tokenizer, texts, self.active,
            max_len=self.max_len, batch_size=batch_size, device=self.device,
        )  # fmt: skip

    def predict_proba(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        """Independent per-label probabilities (sigmoid); never-seen labels are 0."""
        return 1.0 / (1.0 + np.exp(-self.scores(texts, batch_size)))

    def predict(self, texts: Sequence[str], top_k: int = 3) -> list[dict[str, Any]]:
        scores = self.scores(texts)
        probs = 1.0 / (1.0 + np.exp(-scores))
        hot = multihot_from_scores(scores)
        out = []
        for row_probs, row_hot in zip(probs, hot, strict=True):
            top = np.argsort(-row_probs)[:top_k]
            out.append(
                {
                    "labels": [self.labels[i] for i in np.flatnonzero(row_hot)],
                    "top": [(self.labels[i], round(float(row_probs[i]), 4)) for i in top],
                }
            )
        return out


def classify_document(text: str, clf: ClauseClassifier, **segment_kwargs) -> list[dict[str, Any]]:
    """Segment a document, then classify every segment."""
    segments = segment_document(text, **segment_kwargs)
    predictions = clf.predict([s.text for s in segments])
    return [
        {"index": s.index, "kind": s.kind, "number": s.number, "heading": s.heading,
         "text": s.text, **p}
        for s, p in zip(segments, predictions, strict=True)
    ]  # fmt: skip
