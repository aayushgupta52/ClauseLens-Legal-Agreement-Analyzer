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


PROPERTY_CLAUSE_RULES: list[tuple[str, str]] = [
    (r"carpet area|property specifications?|layout|fixtures|common facilities|parking allocation|building specifications|amenities", "property_specifications"),
    (r"title (?:is )?(?:clear|free)|clear and marketable title|encumbrance|lien|charge on the property|ownership of the property", "title_and_encumbrances"),
    (r"possession|handover|handing over|completion date|delay in completion", "possession_handover"),
    (r"booking amount|purchase consideration|sale consideration|instalments?|installments?|payment milestone|balance consideration", "booking_payment"),
    (r"cancel(?:lation)?|refund|forfeit|forfeiture|non-refundable|nonrefundable", "cancellation_refund"),
    (r"stamp duty|registration fee|registration charges|government charges|transaction costs", "registration_charges"),
]


def property_clause_label(doc_type: str, heading: str | None, text: str) -> str | None:
    """High-precision override for unmistakable property-sale clause wording.

    Only used after the whole document has been detected as a property purchase agreement.
    It deliberately returns no label when the wording is ambiguous, leaving the model's
    prediction intact and the normal review workflow available.
    """
    if doc_type != "property_purchase":
        return None
    heading_text = (heading or "").lower()
    heading_matches = {
        label for pattern, label in PROPERTY_CLAUSE_RULES if heading_text and re.search(pattern, heading_text)
    }
    if len(heading_matches) == 1:
        return next(iter(heading_matches))
    haystack = f"{heading or ''} {text}".lower()
    matches = {label for pattern, label in PROPERTY_CLAUSE_RULES if re.search(pattern, haystack)}
    if len(matches) == 1:
        return next(iter(matches))
    # Prefer the narrow specification/title/possession/payment subject over secondary mentions
    # of cancellation, charges or refund remedies in the same paragraph.
    for preferred in ("property_specifications", "title_and_encumbrances", "possession_handover",
                      "booking_payment", "registration_charges", "cancellation_refund"):
        if preferred in matches:
            return preferred
    return None
