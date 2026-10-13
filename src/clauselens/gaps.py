"""Document-type detection and missing-clause detection (Phase 7)."""

from __future__ import annotations

import re

_RENT = ("tenant", "tenancy", "licensee", "licensor", "landlord", "rent", "premises", "flat",
         "lock-in", "security deposit", "leave and license", "vacat")  # fmt: skip
_OFFER = ("employee", "employer", "salary", "stipend", "intern", "trainee", "designation",
          "bond", "notice period", "offer", "appointment", "probation", "training")  # fmt: skip

# Clause types a good agreement of this kind should state clearly.
EXPECTED: dict[str, list[str]] = {
    "rent_agreement": [
        "security_deposit", "lock_in_period", "rent_escalation", "maintenance_repairs",
        "utilities_and_charges", "owner_entry_inspection", "eviction_default",
        "handover_inventory",
    ],
    "offer_and_bond": ["notice_period", "compensation", "termination"],
}  # fmt: skip

GAP_TEXT: dict[str, tuple[str, str]] = {
    "security_deposit": (
        "No security-deposit clause found. Amount, allowed deductions and the refund timeline should be written down.",
        "Security deposit ka clause nahi mila. Amount, kaun si deductions allowed hain aur refund kitne din mein hoga, ye likha hona chahiye.",
    ),
    "lock_in_period": (
        "No lock-in clause found. Ask who is bound, for how long, and what an early exit costs.",
        "Lock-in ka clause nahi mila. Poochho kaun bound hai, kitne time ke liye, aur jaldi nikalne ka cost kya hai.",
    ),
    "rent_escalation": (
        "No rent-revision clause found. A fixed percentage and date avoids surprise increases.",
        "Rent badhne ka clause nahi mila. Fixed percentage aur date likhwao taaki achanak hike na ho.",
    ),
    "maintenance_repairs": (
        "No repairs clause found. Say who pays for structural and minor repairs.",
        "Repairs ka clause nahi mila. Likhwao ki structural aur chhote repairs kaun bharega.",
    ),
    "utilities_and_charges": (
        "No utilities clause found. List who pays electricity, water and society charges.",
        "Utilities ka clause nahi mila. Bijli, paani aur society charges kaun dega, ye likhwao.",
    ),
    "owner_entry_inspection": (
        "No owner-entry clause found. Agree on notice and hours for visits.",
        "Owner ke entry ka clause nahi mila. Visit ke liye notice aur timing pehle se tay kar lo.",
    ),
    "eviction_default": (
        "No default/eviction clause found. Ask for a notice and cure period before eviction.",
        "Default/eviction ka clause nahi mila. Eviction se pehle notice aur cure period maango.",
    ),
    "handover_inventory": (
        "No inventory/handover clause found. A signed inventory protects your deposit.",
        "Inventory/handover ka clause nahi mila. Signed inventory se tera deposit safe rehta hai.",
    ),
    "notice_period": (
        "No notice-period clause found. Ask for the same notice for both sides.",
        "Notice period ka clause nahi mila. Dono taraf ke liye same notice maango.",
    ),
    "compensation": (
        "No compensation clause found. Pay, stipend and payment dates should be stated.",
        "Compensation ka clause nahi mila. Salary/stipend aur payment dates likhi honi chahiye.",
    ),
    "termination": (
        "No termination clause found. Ask how either side can end the agreement.",
        "Termination ka clause nahi mila. Poochho ki dono taraf se agreement kaise khatam ho sakta hai.",
    ),
}  # fmt: skip


def detect_doc_type(text: str) -> tuple[str, float]:
    """('rent_agreement' | 'offer_and_bond' | 'unknown', confidence in 0-1)."""
    low = text.lower()
    rent = sum(len(re.findall(re.escape(w), low)) for w in _RENT)
    offer = sum(len(re.findall(re.escape(w), low)) for w in _OFFER)
    total = rent + offer
    if total < 3 or rent == offer:
        return "unknown", 0.0
    winner = "rent_agreement" if rent > offer else "offer_and_bond"
    return winner, round(max(rent, offer) / total, 3)


def find_gaps(doc_type: str, present: set[str], predictable: set[str]) -> list[str]:
    """Expected clause ids that are absent. Only clause types the classifier can predict count."""
    return [c for c in EXPECTED.get(doc_type, []) if c in predictable and c not in present]
