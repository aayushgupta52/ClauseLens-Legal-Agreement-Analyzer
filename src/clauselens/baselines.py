"""TF-IDF baselines for multi-label clause classification (Phase 3)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.svm import LinearSVC

from clauselens.classification import multihot_from_scores
from clauselens.data.io import read_jsonl


def load_records(path: Path) -> list[dict[str, Any]]:
    return list(read_jsonl(path)) if path.exists() else []


def make_models() -> dict[str, Pipeline]:
    def words() -> TfidfVectorizer:
        return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)

    return {
        "tfidf_lr": Pipeline(
            [
                ("tfidf", words()),
                (
                    "clf",
                    OneVsRestClassifier(
                        LogisticRegression(C=10, max_iter=1000, class_weight="balanced")
                    ),
                ),
            ]  # fmt: skip
        ),
        "tfidf_char_svm": Pipeline(
            [
                (
                    "tfidf",
                    FeatureUnion(
                        [
                            ("word", words()),
                            (
                                "char",
                                TfidfVectorizer(
                                    analyzer="char_wb",
                                    ngram_range=(2, 5),
                                    sublinear_tf=True,
                                    min_df=2,
                                ),
                            ),
                        ]
                    ),
                ),
                (
                    "clf",
                    OneVsRestClassifier(
                        LinearSVC(C=0.5, class_weight="balanced", random_state=0, max_iter=5000)
                    ),
                ),
            ]  # fmt: skip
        ),
    }


def encode(records: Sequence[dict[str, Any]], labels: Sequence[str]) -> np.ndarray:
    known = set(labels)
    unknown = {lab for r in records for lab in r["labels"]} - known
    if unknown:
        raise ValueError(f"labels not in the label space: {sorted(unknown)}")
    return MultiLabelBinarizer(classes=list(labels)).fit_transform([r["labels"] for r in records])


def fit(model: Pipeline, texts: Sequence[str], y: np.ndarray) -> np.ndarray:
    """Fit on the labels that have training examples; returns the boolean mask of those labels.

    Labels without any positive example are never predicted. (Letting sklearn build constant
    predictors for them is a trap: their score 0 beats every real negative score.)
    """
    active = y.sum(axis=0) > 0
    model.fit(list(texts), y[:, active])
    return active


def predict(model: Pipeline, texts: Sequence[str], active: np.ndarray) -> np.ndarray:
    """Multi-hot prediction: every active label with score > 0, else the single best label."""
    texts = list(texts)
    scores = np.full((len(texts), len(active)), -np.inf)
    scores[:, active] = np.asarray(model.decision_function(texts)).reshape(len(texts), -1)
    return multihot_from_scores(scores)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[str]) -> dict[str, Any]:
    p, r, f, support = precision_recall_fscore_support(y_true, y_pred, zero_division=0)
    micro = precision_recall_fscore_support(y_true, y_pred, average="micro", zero_division=0)
    present = support > 0
    per_label = {
        lab: {
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f[i]), 4),
            "support": int(support[i]),
        }
        for i, lab in enumerate(labels)
        if support[i] > 0 or y_pred[:, i].any()
    }
    return {
        "n": int(len(y_true)),
        "micro_f1": round(float(micro[2]), 4),
        "macro_f1": round(float(f[present].mean()), 4) if present.any() else 0.0,
        "n_labels_with_support": int(present.sum()),
        "exact_match": round(float((y_true == y_pred).all(axis=1).mean()), 4),
        "per_label": per_label,
    }
