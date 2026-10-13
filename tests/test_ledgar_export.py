from __future__ import annotations

import pytest

pytest.importorskip("datasets")

from datasets import ClassLabel, Dataset, DatasetDict, Features, Value  # noqa: E402

from clauselens.data.io import read_jsonl  # noqa: E402
from clauselens.data.sources import LEDGAR_LABELS, export_ledgar, read_ledgar  # noqa: E402


def _ledgar_dataset(rows_by_split: dict[str, list[tuple[str, str]]]) -> DatasetDict:
    feats = Features({"text": Value("string"), "label": ClassLabel(names=list(LEDGAR_LABELS))})

    def make(rows):
        return Dataset.from_dict(
            {
                "text": [text for text, _ in rows],
                "label": [LEDGAR_LABELS.index(label) for _, label in rows],
            },
            features=feats,
        )

    return DatasetDict({k: make(v) for k, v in rows_by_split.items()})


def test_export_and_read_ledgar_roundtrip(tmp_path):
    ds = _ledgar_dataset(
        {
            "train": [("This agreement may be terminated by either party.", "Terminations")],
            "validation": [("Notices shall be in writing and delivered by hand.", "Notices")],
            "test": [("All disputes shall be settled by arbitration.", "Arbitration")],
        }
    )
    assert export_ledgar(ds, tmp_path) == {"train": 1, "validation": 1, "test": 1}
    assert next(read_jsonl(tmp_path / "train.jsonl"))["label"] == "Terminations"
    got = list(read_ledgar(tmp_path))
    assert [(e.source_label, e.split_hint) for e in got] == [
        ("Terminations", "train"),
        ("Notices", "val"),
        ("Arbitration", "test"),
    ]
