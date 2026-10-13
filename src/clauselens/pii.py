"""PII Shield (Phase 7): mask structured personal identifiers before anything else sees the text.

Covers Aadhaar, PAN, IFSC, e-mail, bank-account numbers and Indian mobile numbers. Names and
addresses are NOT masked (that needs an NER model); the UI says so.
"""

from __future__ import annotations

import re
from collections import Counter

# Each pattern has an optional "pre" group (kept as is) and a "val" group (replaced by a token).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ACCOUNT",
        re.compile(
            r"(?i)(?P<pre>\b(?:account|a/c)\b[\s.:#-]*(?:no\.?|number)?[\s.:#-]*)(?P<val>\d{9,18})\b"
        ),
    ),
    ("AADHAAR", re.compile(r"(?<!\d)(?P<val>\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)")),
    ("PAN", re.compile(r"\b(?P<val>[A-Z]{5}\d{4}[A-Z])\b")),
    ("IFSC", re.compile(r"\b(?P<val>[A-Z]{4}0[A-Z0-9]{6})\b")),
    ("EMAIL", re.compile(r"\b(?P<val>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)\b")),
    ("PHONE", re.compile(r"(?<![\d.,])(?P<val>(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5})(?!\d)")),
]


def _identity(kind: str, raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if kind == "PHONE":
        return digits[-10:]  # +91 98765 43210 and 9876543210 are the same person
    return digits if kind in ("AADHAAR", "ACCOUNT") else raw.strip()


def mask_pii(text: str) -> tuple[str, dict[str, int], dict[str, str]]:
    """Return (masked text, count per type, token -> original value).

    The same value always gets the same token. The mapping lives only in memory for the
    caller; ClauseLens never stores it.
    """
    mapping: dict[str, str] = {}
    value_to_token: dict[tuple[str, str], str] = {}
    counts: Counter[str] = Counter()
    for kind, pattern in _PATTERNS:

        def _sub(m: re.Match[str], kind: str = kind) -> str:
            raw = m.group("val")
            key = (kind, _identity(kind, raw))
            if key not in value_to_token:
                counts[kind] += 1
                value_to_token[key] = f"[{kind}_{counts[kind]}]"
                mapping[value_to_token[key]] = raw.strip()
            pre = m.groupdict().get("pre") or ""
            return pre + value_to_token[key]

        text = pattern.sub(_sub, text)
    return text, dict(counts), mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text
