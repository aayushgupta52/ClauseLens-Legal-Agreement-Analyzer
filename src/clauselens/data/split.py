"""Deterministic, group-aware splitting (a contract never spans two splits)."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable

from clauselens.schemas import Split


def assign_groups(
    group_ids: Iterable[str],
    *,
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 42,
) -> dict[str, Split]:
    """Map each group id to train/val/test.

    Groups are ordered by a seeded hash, so the result does not depend on input order
    or on the Python version, and is reproducible from (ids, ratios, seed) alone.
    """
    if len(ratios) != 3 or not math.isclose(sum(ratios), 1.0) or min(ratios) <= 0:
        raise ValueError(f"ratios must be 3 positive numbers summing to 1, got {ratios}")

    ids = sorted(
        set(group_ids),
        key=lambda g: hashlib.sha256(f"{seed}:{g}".encode()).hexdigest(),
    )
    n = len(ids)
    n_train = round(n * ratios[0])
    n_val = round(n * ratios[1])

    assignment: dict[str, Split] = {}
    for i, gid in enumerate(ids):
        if i < n_train:
            assignment[gid] = "train"
        elif i < n_train + n_val:
            assignment[gid] = "val"
        else:
            assignment[gid] = "test"
    return assignment
