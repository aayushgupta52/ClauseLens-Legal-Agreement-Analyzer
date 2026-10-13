"""Single source of truth for filesystem locations."""

from __future__ import annotations

import os
from pathlib import Path


def _find_root() -> Path:
    override = os.environ.get("CLAUSELENS_ROOT")
    if override:
        return Path(override).resolve()
    # src/clauselens/paths.py -> parents[2] is the repository root
    return Path(__file__).resolve().parents[2]


ROOT = _find_root()
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
