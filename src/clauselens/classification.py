"""Torch-free helpers shared by the TF-IDF baselines and the transformer classifier."""

from __future__ import annotations

from typing import Any

import numpy as np


def multihot_from_scores(scores: np.ndarray) -> np.ndarray:
    """Every label with score > 0 (logit > 0, i.e. probability > 0.5), else the single best label.

    Labels that were never seen in training carry -inf and therefore can never be chosen.
    """
    pred = scores > 0
    empty = ~pred.any(axis=1)
    pred[empty, scores[empty].argmax(axis=1)] = True
    return pred.astype(int)


def class_pos_weights(y: np.ndarray, active: np.ndarray, cap: float) -> np.ndarray:
    """BCE positive-class weights: (negatives / positives) clipped to [1, cap]; 1 if unseen."""
    positives = y.sum(axis=0)
    weights = np.ones(y.shape[1], dtype=np.float32)
    weights[active] = np.clip((len(y) - positives[active]) / positives[active], 1.0, cap)
    return weights


def compact_metrics(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep only the headline numbers of evaluate() results (for per-epoch logs)."""
    return {k: {m: v[m] for m in ("n", "micro_f1", "macro_f1")} for k, v in metrics.items()}
