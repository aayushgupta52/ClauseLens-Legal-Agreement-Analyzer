"""Dataset v1 pipeline: map -> normalise -> merge duplicates -> split -> purge leakage."""

from __future__ import annotations

import logging
import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from clauselens.data.dedupe import find_near_duplicates
from clauselens.data.split import assign_groups
from clauselens.data.taxonomy import OTHER_ID, Taxonomy
from clauselens.data.text import fingerprint, normalize_text, word_count
from clauselens.schemas import ClauseRecord, RawExample

log = logging.getLogger(__name__)

# When identical text lands in different splits, keep it in the most protected one.
_STRICTNESS: dict[str, int] = {"train": 0, "val": 1, "test": 2}


@dataclass
class _Item:
    text: str
    labels: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    source_labels: set[str] = field(default_factory=set)
    doc_ids: set[str] = field(default_factory=set)
    splits: set[str] = field(default_factory=set)


def build_dataset(
    examples: Iterable[RawExample],
    taxonomy: Taxonomy,
    cuad_doc_ids: Iterable[str],
    *,
    seed: int = 42,
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    min_words: int = 5,
    near_dup_threshold: float = 0.85,
    max_other_ratio: float | None = None,
) -> tuple[list[ClauseRecord], dict[str, Any]]:
    # CUAD is split by contract. Using *all* contracts (not only those that yield examples)
    # keeps the assignment stable when the taxonomy changes.
    doc_split = assign_groups(cuad_doc_ids, ratios=ratios, seed=seed)

    dropped: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    items: dict[str, _Item] = {}
    n_input = 0
    n_accepted = 0

    for ex in examples:
        n_input += 1
        clause_id = taxonomy.resolve(ex.source, ex.source_label)
        if clause_id is None:
            if taxonomy.is_excluded(ex.source, ex.source_label):
                dropped["excluded_label"] += 1
            else:
                dropped["unmapped_label"] += 1
                unmapped[f"{ex.source}:{ex.source_label}"] += 1
            continue

        text = normalize_text(ex.text)
        if word_count(text) < min_words:
            dropped["too_short"] += 1
            continue

        split = ex.split_hint or (doc_split.get(ex.doc_id) if ex.doc_id else None)
        if split is None:
            raise ValueError(f"no split for example from {ex.source} (doc_id={ex.doc_id!r})")

        n_accepted += 1
        item = items.setdefault(fingerprint(text), _Item(text=text))
        item.labels.add(clause_id)
        item.sources.add(ex.source)
        item.source_labels.add(f"{ex.source}:{ex.source_label}")
        item.splits.add(split)
        if ex.doc_id:
            item.doc_ids.add(ex.doc_id)

    ordered = sorted(items.items())  # by fingerprint -> deterministic output
    final_split = [max(item.splits, key=_STRICTNESS.__getitem__) for _, item in ordered]
    cross_split_exact = sum(1 for _, item in ordered if len(item.splits) > 1)

    train_idx = [i for i, s in enumerate(final_split) if s == "train"]
    held_idx = [i for i, s in enumerate(final_split) if s != "train"]
    near_dup_hits = find_near_duplicates(
        [ordered[i][1].text for i in train_idx],
        [ordered[i][1].text for i in held_idx],
        threshold=near_dup_threshold,
    )
    removed = {train_idx[h] for h in near_dup_hits}
    log.info("near-duplicate leakage: removed %d train examples", len(removed))

    records: list[ClauseRecord] = []
    for i, (fp, item) in enumerate(ordered):
        if i in removed:
            continue
        records.append(
            ClauseRecord(
                id=f"c_{fp[:16]}",
                text=item.text,
                labels=sorted(_resolve_other(item.labels)),
                sources=sorted(item.sources),
                source_labels=sorted(item.source_labels),
                doc_id=min(item.doc_ids) if item.doc_ids else None,
                split=final_split[i],
            )
        )

    if max_other_ratio is not None:
        records = _cap_other(records, max_other_ratio, dropped)

    stats = _summarise(
        records,
        taxonomy,
        dropped,
        unmapped,
        n_input,
        n_accepted,
        len(items),
        cross_split_exact,
        len(removed),
    )
    return records, stats


def _resolve_other(labels: set[str]) -> set[str]:
    """A real clause label always wins over the catch-all "other"."""
    return labels - {OTHER_ID} if len(labels) > 1 else labels


def _cap_other(
    records: list[ClauseRecord], ratio: float, dropped: Counter[str]
) -> list[ClauseRecord]:
    """Per split, keep at most ceil(ratio * n_positive) "other" records (deterministic)."""
    kept: list[ClauseRecord] = []
    for split in ("train", "val", "test"):
        in_split = [r for r in records if r.split == split]
        others = sorted((r for r in in_split if r.labels == [OTHER_ID]), key=lambda r: r.id)
        positives = [r for r in in_split if r.labels != [OTHER_ID]]
        limit = math.ceil(ratio * len(positives))
        if len(others) > limit:
            dropped["other_cap"] += len(others) - limit
        kept += positives + others[:limit]
    return sorted(kept, key=lambda r: r.id)


def _summarise(
    records: list[ClauseRecord],
    taxonomy: Taxonomy,
    dropped: Counter[str],
    unmapped: Counter[str],
    n_input: int,
    n_accepted: int,
    n_unique: int,
    cross_split_exact: int,
    n_near_dup_removed: int,
) -> dict[str, Any]:
    per_label: dict[str, Counter[str]] = {cid: Counter() for cid in taxonomy.clause_ids}
    per_split: Counter[str] = Counter()
    per_source: Counter[str] = Counter()
    for r in records:
        per_split[r.split] += 1
        per_source["+".join(r.sources)] += 1
        for label in r.labels:
            per_label[label][r.split] += 1
            per_label[label]["total"] += 1

    return {
        "n_input_examples": n_input,
        "n_accepted_examples": n_accepted,
        "dropped": dict(dropped),
        "n_unique_texts_after_exact_dedup": n_unique,
        "n_texts_in_multiple_splits_before_resolution": cross_split_exact,
        "n_near_duplicates_removed_from_train": n_near_dup_removed,
        "n_records": len(records),
        "n_multi_label_records": sum(len(r.labels) > 1 for r in records),
        "per_split": dict(per_split),
        "per_source": dict(per_source),
        "per_label": {k: dict(v) for k, v in per_label.items()},
        "labels_without_data": sorted(k for k, v in per_label.items() if not v["total"]),
        "top_unmapped_labels": unmapped.most_common(25),
    }
