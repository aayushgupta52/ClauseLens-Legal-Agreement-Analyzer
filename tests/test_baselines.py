from __future__ import annotations

import numpy as np
import pytest

from clauselens.baselines import encode, evaluate, fit, make_models, predict

LABELS = ["deposit", "notice", "unseen", "other"]


def _train():
    texts, labels = [], []
    for i in range(8):
        texts.append(f"the security deposit shall be refunded within {i + 5} days")
        labels.append(["deposit"])
        texts.append(f"either party may end this by giving {i + 5} days notice period")
        labels.append(["notice"])
        texts.append(f"the licensor grants a non exclusive licence to distribute product {i}")
        labels.append(["other"])
    return texts, [{"labels": lab} for lab in labels]


def test_labels_without_training_data_are_never_predicted():
    texts, recs = _train()
    model = make_models()["tfidf_lr"]
    active = fit(model, texts, encode(recs, LABELS))
    assert active.tolist() == [True, True, False, True]
    pred = predict(model, ["zzz qqq completely unrelated words", texts[0]], active)
    assert pred[:, 2].sum() == 0  # the "unseen" label can never win the fallback
    assert pred.sum(axis=1).tolist() == [1, 1]  # every row gets at least one label
    assert pred[1, 0] == 1  # and a clear deposit sentence is recognised


def test_evaluate_known_values():
    y_true = np.array([[1, 0], [0, 1], [1, 1]])
    y_pred = np.array([[1, 0], [1, 0], [1, 1]])
    res = evaluate(y_true, y_pred, ["a", "b"])
    assert res["micro_f1"] == 0.75
    assert res["macro_f1"] == round((0.8 + 2 / 3) / 2, 4)
    assert res["exact_match"] == round(2 / 3, 4)
    assert res["per_label"]["b"] == {"precision": 1.0, "recall": 0.5, "f1": 0.6667, "support": 2}


def test_encode_rejects_labels_outside_the_label_space():
    with pytest.raises(ValueError):
        encode([{"labels": ["nope"]}], LABELS)
