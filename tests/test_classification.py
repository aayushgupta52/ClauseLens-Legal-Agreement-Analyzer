from __future__ import annotations

import numpy as np

from clauselens.classification import class_pos_weights, compact_metrics, multihot_from_scores


def test_multihot_masks_never_seen_labels_and_falls_back_to_best():
    scores = np.array([[2.0, -1.0, -np.inf], [-3.0, -2.0, -np.inf], [1.0, 1.0, -np.inf]])
    assert multihot_from_scores(scores).tolist() == [[1, 0, 0], [0, 1, 0], [1, 1, 0]]


def test_pos_weights_are_clipped_and_neutral_for_unseen_labels():
    y = np.zeros((100, 4), dtype=int)
    y[:50, 0] = 1  # balanced        -> weight 1
    y[:10, 1] = 1  # 10 vs 90        -> 9, clipped to the cap
    y[:2, 2] = 1  # very rare        -> clipped to the cap
    active = y.sum(axis=0) > 0  # label 3 never appears
    weights = class_pos_weights(y, active, cap=5.0)
    assert weights.tolist() == [1.0, 5.0, 5.0, 1.0]
    y[:30, 1] = 1  # 30 vs 70 -> 2.33
    assert round(float(class_pos_weights(y, active, cap=5.0)[1]), 2) == 2.33


def test_compact_metrics_keeps_only_headline_numbers():
    full = {"real_val": {"n": 3, "micro_f1": 0.5, "macro_f1": 0.4, "per_label": {"a": {}}}}
    assert compact_metrics(full) == {"real_val": {"n": 3, "micro_f1": 0.5, "macro_f1": 0.4}}
