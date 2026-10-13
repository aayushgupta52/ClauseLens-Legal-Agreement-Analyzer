"""Clause classifier backends for the analysis pipeline (TF-IDF by default, BERT optional)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np

from clauselens.baselines import encode, fit, load_records, make_models
from clauselens.classification import multihot_from_scores
from clauselens.data.taxonomy import Taxonomy
from clauselens.paths import MODELS, PROCESSED

log = logging.getLogger(__name__)
TFIDF_NAME = "tfidf_char_svm"


@dataclass
class Prediction:
    labels: list[str]
    top: list[tuple[str, float]] = field(default_factory=list)  # (label, sigmoid(score))

    @property
    def confidence(self) -> float:
        return self.top[0][1] if self.top else 0.0


class Classifier(Protocol):
    name: str
    active_labels: list[str]

    def predict(self, texts: list[str]) -> list[Prediction]: ...


def clause_labels() -> list[str]:
    return Taxonomy.load().with_other(["out_of_domain"]).clause_ids


class TfidfClassifier:
    name = TFIDF_NAME

    def __init__(self, model, labels: list[str], active: np.ndarray) -> None:
        self.model, self.labels, self.active = model, labels, np.asarray(active, dtype=bool)

    @property
    def active_labels(self) -> list[str]:
        return [lab for lab, a in zip(self.labels, self.active, strict=True) if a]

    def predict(self, texts: list[str], top_k: int = 3) -> list[Prediction]:
        if not texts:
            return []
        scores = np.full((len(texts), len(self.labels)), -np.inf)
        scores[:, self.active] = np.asarray(self.model.decision_function(texts)).reshape(
            len(texts), -1
        )
        hot = multihot_from_scores(scores)
        with np.errstate(over="ignore"):
            probs = 1.0 / (1.0 + np.exp(-scores))
        out = []
        for row_probs, row_hot in zip(probs, hot, strict=True):
            top = np.argsort(-row_probs)[:top_k]
            out.append(
                Prediction(
                    labels=[self.labels[i] for i in np.flatnonzero(row_hot)],
                    top=[(self.labels[i], round(float(row_probs[i]), 4)) for i in top],
                )
            )
        return out


def _training_records() -> list[dict]:
    """Real data if it has been built, plus synthetic data (generated on the fly if missing)."""
    records: list[dict] = []
    for directory in (PROCESSED / "v1", PROCESSED / "synth_v1"):
        records += load_records(directory / "train.jsonl")
    if not any("synth" in r["sources"] for r in records):
        from clauselens.synth.generator import generate_samples

        samples, _ = generate_samples()
        records += [r.model_dump() for r in samples if r.split == "train"]
    if not any("cuad" in r["sources"] or "ledgar" in r["sources"] for r in records):
        log.warning("real data not built yet: classifier trained on synthetic data only")
    return records


def train_tfidf(models_dir: Path = MODELS) -> TfidfClassifier:
    labels = clause_labels()
    records = _training_records()
    model = make_models()[TFIDF_NAME]
    active = fit(model, [r["text"] for r in records], encode(records, labels))
    models_dir.mkdir(parents=True, exist_ok=True)
    blob = {"model": model, "labels": labels, "active": active}
    joblib.dump(blob, models_dir / f"{TFIDF_NAME}.joblib")
    return TfidfClassifier(model, labels, active)


def load_tfidf(models_dir: Path = MODELS) -> TfidfClassifier:
    path = models_dir / f"{TFIDF_NAME}.joblib"
    if not path.exists():
        log.info("%s missing, training it now", path)
        return train_tfidf(models_dir)
    blob = joblib.load(path)
    return TfidfClassifier(blob["model"], blob["labels"], blob["active"])


class TransformerClassifier:
    """Wraps a Phase 4 fine-tuned model. Needs torch + transformers (pip install -e .[nlp])."""

    def __init__(self, model_dir: str | Path) -> None:
        from clauselens.inference import ClauseClassifier

        self._clf = ClauseClassifier(model_dir)
        self.name = f"transformer:{Path(model_dir).name}"
        self.active_labels = [
            lab for lab, a in zip(self._clf.labels, self._clf.active, strict=True) if a
        ]

    def predict(self, texts: list[str]) -> list[Prediction]:
        return [Prediction(p["labels"], p["top"]) for p in self._clf.predict(texts)]


def load_classifier(models_dir: Path = MODELS) -> Classifier:
    """CLAUSELENS_CLASSIFIER=tfidf (default) | transformer; CLAUSELENS_TRANSFORMER_DIR=path."""
    backend = os.environ.get("CLAUSELENS_CLASSIFIER", "tfidf").lower()
    if backend == "transformer":
        directory = os.environ.get("CLAUSELENS_TRANSFORMER_DIR")
        if not directory:
            raise RuntimeError("set CLAUSELENS_TRANSFORMER_DIR to a fine-tuned model directory")
        return TransformerClassifier(directory)
    return load_tfidf(models_dir)
