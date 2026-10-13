from __future__ import annotations

import joblib
import numpy as np

from clauselens.classifier import TfidfClassifier, load_classifier, load_tfidf


def test_predictions_have_valid_labels_and_never_use_unseen_ones(engine):
    clf = engine.classifier
    preds = clf.predict(
        ["The Tenant shall pay a refundable security deposit of Rs. 50,000/-.", "zzz qqq", ""]
    )
    inactive = set(clf.labels) - set(clf.active_labels)
    assert len(preds) == 3 and "termination" in inactive
    for pred in preds:
        assert pred.labels and not set(pred.labels) & inactive
        assert 0.0 <= pred.confidence <= 1.0 and len(pred.top) == 3
    assert preds[0].labels[0] == "security_deposit"
    assert clf.predict([]) == []


def test_saved_model_reloads_identically(engine, tmp_path):
    clf = engine.classifier
    joblib.dump(
        {"model": clf.model, "labels": clf.labels, "active": np.asarray(clf.active)},
        tmp_path / "tfidf_char_svm.joblib",
    )
    loaded = load_tfidf(tmp_path)
    text = ["The Employer may deduct any amount from the salary."]
    assert isinstance(loaded, TfidfClassifier)
    assert loaded.predict(text) == clf.predict(text)
    assert load_classifier(tmp_path).name == "tfidf_char_svm"
