"""Text normalisation and fingerprinting used for dedup and leakage control."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Unicode-normalise (NFKC) and collapse all whitespace to single spaces."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def word_count(text: str) -> int:
    return len(text.split())


def fingerprint(text: str) -> str:
    """Stable identity of a text, insensitive to case and whitespace differences."""
    key = normalize_text(text).casefold()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
