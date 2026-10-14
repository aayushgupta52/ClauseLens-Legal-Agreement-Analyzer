"""Key-fact extraction (Phase 5): money, durations, percentages and dates, plus their role.

Rule-based on purpose: every extracted value is a verbatim span of the clause text, so the
explanations built on top of it cannot invent numbers.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_NUM_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
    "sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
)
_WORD = rf"(?:{_NUM_WORDS})(?:-(?:{_NUM_WORDS}))?"
_UNIT = r"(?:days?|months?|years?|hours?|weeks?)\b"
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"

PATTERNS: dict[str, re.Pattern[str]] = {
    "money": re.compile(
        r"(?:Rs\.?\s?|INR\s?|₹\s?)\d+(?:,\d+)*(?:\.\d+)?(?:\s?/-)?(?:\s?(?:lakhs?|lacs?|crores?)\b)?",
        re.I,
    ),
    "duration": re.compile(
        rf"(?:\b{_WORD}\s*\(\s*\d+\s*\)|(?<![\d.,])\d+(?:\.\d+)?|\b{_WORD})\s*{_UNIT}", re.I
    ),
    "percent": re.compile(r"(?<![\d.])\d+(?:\.\d+)?\s?(?:%|per\s?cent(?:age)?\b|percent\b)", re.I),
    "date": re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?(?:\s+day)?\s+(?:of\s+)?(?:{_MONTHS}),?\s+\d{{4}}\b"
        r"|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
        re.I,
    ),
}

# (pattern searched in the text BEFORE the value, role). The closest match wins.
ROLE_RULES: dict[str, list[tuple[str, str]]] = {
    "money": [
        (r"stamp duty|registration fee|registration charges", "registration_charge"),
        (r"booking amount|earnest money", "booking_amount"),
        (r"purchase price|sale consideration|purchase consideration|consideration", "purchase_price"),
        (r"deposit", "deposit_amount"),
        (r"\brent\b", "monthly_rent"),
        (r"society|maintenance of|maintenance charge|charges of", "maintenance_charge"),
        (r"repairs?[^.]{0,40}up to|costing", "repair_limit"),
        (r"bond|liquidated", "bond_amount"),
        (r"training|onboarding", "training_cost"),
        (r"salary|stipend|pay\b", "pay"),
    ],
    "duration": [
        (r"lock-in|lock in", "lock_in_period"),
        (r"refund|return|vacat", "refund_window"),
        (r"cure|remedy", "cure_period"),
        (r"unpaid|default|non-payment", "default_grace"),
        (r"guest|visitor|stay", "guest_limit"),
        (r"verification|moving in|taking possession", "verification_window"),
        (r"retain|retention|held by|background verification", "retention_period"),
        (r"training|refund the", "recovery_period"),
        (r"bond|serve|service|resign|leave|leaves|completing|ends before", "bond_period"),
        (r"entry|prior notice|visit|hours", "entry_notice"),
        (r"escalat|increase|revis|every|each|renew", "escalation_interval"),
        (r"notice|giving|require", "notice_period"),
        (r"payment equal to|pay\b|compensation", "exit_penalty"),
    ],
    "percent": [
        (r"deduct", "deduction_cap"),
        (r"increase|escalat|rent|revis", "rent_increase"),
    ],
    "date": [(r"", "date")],
}
# In these clauses the role follows from the clause type itself (checked before the keywords).
CLAUSE_ROLE: dict[tuple[str, str], str] = {
    ("registration_charges", "money"): "registration_charge",
    ("cancellation_refund", "money"): "booking_amount",
    ("security_deposit", "money"): "deposit_amount",
    ("security_deposit", "duration"): "refund_window",
    ("rent_escalation", "money"): "monthly_rent",
    ("rent_escalation", "percent"): "rent_increase",
    ("rent_escalation", "duration"): "escalation_interval",
    ("maintenance_repairs", "money"): "repair_limit",
    ("utilities_and_charges", "money"): "maintenance_charge",
    ("owner_entry_inspection", "duration"): "entry_notice",
    ("subletting_guests", "duration"): "guest_limit",
    ("tenant_verification", "duration"): "verification_window",
    ("service_bond", "money"): "bond_amount",
    ("service_bond", "duration"): "bond_period",
    ("training_cost_recovery", "money"): "training_cost",
    ("training_cost_recovery", "duration"): "recovery_period",
    ("notice_period", "duration"): "notice_period",
    ("document_retention", "duration"): "retention_period",
    ("salary_deductions", "percent"): "deduction_cap",
}
_WINDOW = 70


@dataclass(frozen=True)
class Fact:
    type: str
    text: str
    start: int
    end: int
    role: str

    def as_dict(self) -> dict:
        return asdict(self)


def _role(kind: str, text: str, start: int, end: int, clause_id: str | None) -> str:
    if clause_id and (clause_id, kind) in CLAUSE_ROLE:
        return CLAUSE_ROLE[(clause_id, kind)]
    window = text[max(0, start - _WINDOW) : start].lower()
    after = text[end : end + 25].lower()
    if kind == "duration" and re.match(r"\s*(?:to\s+)?(?:remedy|cure)", after):
        return "cure_period"
    if clause_id == "lock_in_period" and kind == "duration":
        if re.search(r"pay|payment|compensation", window):
            return "exit_penalty"
        return "lock_in_period" if "month" in text[start:end].lower() else "notice_period"
    best_pos, best_role = -1, f"other_{kind}"
    for pattern, role in ROLE_RULES[kind]:
        found = [m.start() for m in re.finditer(pattern, window)]
        if found and max(found) > best_pos:
            best_pos, best_role = max(found), role
    return best_role


def extract_facts(text: str, clause_id: str | None = None) -> list[Fact]:
    """All money / duration / percent / date values of `text`, non-overlapping, in order.

    `clause_id` (the predicted clause type) sharpens the role of each value.
    """
    spans: list[tuple[int, int, str]] = []
    for kind, pattern in PATTERNS.items():
        spans += [(m.start(), m.end(), kind) for m in pattern.finditer(text)]
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    facts: list[Fact] = []
    last_end = -1
    for start, end, kind in spans:
        if start < last_end:
            continue
        facts.append(
            Fact(kind, text[start:end], start, end, _role(kind, text, start, end, clause_id))
        )
        last_end = end
    return facts


_WORD_VALUES = {
    w: i for i, w in enumerate(_NUM_WORDS.split("|")[:10], start=1)
} | {"eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
     "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
     "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}  # fmt: skip


def to_number(value: str) -> float | None:
    """'Rs. 1,50,000/-' -> 150000, 'twelve (12) months' -> 12, '5 percent' -> 5."""
    text = value.lower()
    m = re.search(r"\(\s*(\d+)\s*\)", text) or re.search(r"\d+(?:,\d+)*(?:\.\d+)?", text)
    if m:
        number = float((m.group(1) if m.lastindex else m.group(0)).replace(",", ""))
        if re.search(r"lakhs?|lacs?", text):
            number *= 100_000
        elif re.search(r"crores?", text):
            number *= 10_000_000
        return number
    words = re.findall(rf"{_WORD}", text)
    if words:
        return float(sum(_WORD_VALUES.get(w, 0) for w in words[0].split("-")))
    return None


def to_months(value: str) -> float | None:
    """Duration text -> months (days/30, years*12); None if it is not a duration."""
    number = to_number(value)
    if number is None:
        return None
    text = value.lower()
    if "year" in text:
        return number * 12
    if "month" in text:
        return number
    if "week" in text:
        return number * 7 / 30
    if "day" in text:
        return number / 30
    return None


def to_days(value: str) -> float | None:
    months = to_months(value)
    if months is not None and "hour" not in value.lower():
        return months * 30
    if "hour" in value.lower():
        number = to_number(value)
        return None if number is None else number / 24
    return None
