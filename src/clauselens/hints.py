"""Clause-type hints from headings and a few unmistakable phrases.

A heading such as "SECURITY DEPOSIT" or "Notice Period" is strong evidence in a real agreement, so
an unambiguous heading hint overrides the classifier. Phrase hints are weaker and are only used
when the classifier says "other" or is unsure.
"""

from __future__ import annotations

import re

from clauselens.qa import route_question

STRONG_PHRASES: list[tuple[str, str]] = [
    (r"lock-?\s?in period", "lock_in_period"),
    (r"security deposit", "security_deposit"),
    (r"service agreement|service bond|bond period|bond amount|serve the (?:company|employer|organi[sz]ation)"
     r"|minimum period of \d+ months?", "service_bond"),
    (r"police verification", "tenant_verification"),
    (r"original (?:educational )?(?:certificates|documents|marksheets)", "document_retention"),
    (r"notice period", "notice_period"),
    (r"sub-?let", "subletting_guests"),
    (r"governed by (?:and construed in accordance with )?the laws? of", "governing_law"),
]  # fmt: skip


def hint_label(heading: str | None, text: str) -> tuple[str | None, str | None]:
    """(clause type, "heading" | "phrase") or (None, None)."""
    if heading:
        routed = route_question(heading)
        if len(routed) == 1:
            return routed[0], "heading"
    low = text.lower()
    found = {cid for pattern, cid in STRONG_PHRASES if re.search(pattern, low)}
    return (next(iter(found)), "phrase") if len(found) == 1 else (None, None)
