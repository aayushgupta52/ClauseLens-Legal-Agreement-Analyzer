"""Data contracts shared across the data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Split = Literal["train", "val", "test"]


@dataclass(frozen=True, slots=True)
class RawExample:
    """One labeled text span exactly as a source dataset provides it."""

    text: str
    source: str  # "cuad" | "ledgar"
    source_label: str  # exact label string from the source
    doc_id: str | None = None  # contract title (CUAD); LEDGAR has none
    split_hint: Split | None = None  # official split (LEDGAR); None for CUAD


class ClauseRecord(BaseModel):
    """One deduplicated clause example in the processed dataset."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(min_length=1)
    labels: list[str] = Field(min_length=1)  # taxonomy clause ids
    sources: list[str]
    source_labels: list[str]  # "source:label", for traceability
    doc_id: str | None = None
    split: Split
