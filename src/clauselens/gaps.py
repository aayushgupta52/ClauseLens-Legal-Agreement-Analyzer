"""Document-type detection and missing-clause detection (Phase 7)."""

from __future__ import annotations

import re

_RENT = ("tenant", "tenancy", "licensee", "licensor", "landlord", "rent", "premises", "flat",
         "lock-in", "security deposit", "leave and license", "vacat")  # fmt: skip
_OFFER = ("employee", "employer", "salary", "stipend", "intern", "trainee", "designation",
          "bond", "notice period", "offer", "appointment", "probation", "training")  # fmt: skip
_PROPERTY = ("agreement for sale", "agreement to sell", "sale deed", "purchaser", "allottee",
             "carpet area", "possession date", "booking amount", "purchase consideration",
             "stamp duty", "registration charges", "encumbrance", "builder", "promoter",
             "property specifications", "flat purchase", "buyer", "seller")  # fmt: skip

# Clause types a good agreement of this kind should state clearly.
EXPECTED: dict[str, list[str]] = {
    "rent_agreement": [
        "security_deposit", "lock_in_period", "rent_escalation", "maintenance_repairs",
        "utilities_and_charges", "owner_entry_inspection", "eviction_default",
        "handover_inventory",
    ],
    "offer_and_bond": ["notice_period", "compensation", "termination"],
    "property_purchase": ["property_specifications", "title_and_encumbrances", "possession_handover",
                          "booking_payment", "cancellation_refund", "registration_charges"],
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
    "property_specifications": (
        "No clear property-specification clause was identified. Confirm carpet area, layout, fixtures, amenities and whether changes require written buyer consent.",
        "Property specifications ka clear clause nahi mila. Carpet area, layout, fixtures, amenities aur changes ke liye buyer ki written consent check karo.",
    ),
    "title_and_encumbrances": (
        "No clear title/encumbrance clause was identified. Ask for title documents and written disclosure of liens or claims; verify independently.",
        "Title/encumbrance ka clear clause nahi mila. Title documents aur kisi lien/claim ka written disclosure maango; independently verify karao.",
    ),
    "possession_handover": (
        "No clear possession/handover clause was identified. Confirm the date, completion conditions, delay consequences and remedies.",
        "Possession/handover ka clear clause nahi mila. Date, completion conditions, delay par consequences aur remedies confirm karo.",
    ),
    "booking_payment": (
        "No clear booking/payment schedule was identified. Confirm amounts, due dates, milestones and receipt requirements.",
        "Booking/payment schedule clear nahi mila. Amount, due dates, milestones aur receipts confirm karo.",
    ),
    "cancellation_refund": (
        "No clear cancellation/refund clause was identified. Confirm when money can be retained and the refund timeline.",
        "Cancellation/refund clause clear nahi mila. Paisa kab roka ja sakta hai aur refund timeline confirm karo.",
    ),
    "registration_charges": (
        "No clear allocation of stamp duty, registration fees and transaction charges was identified. Confirm who pays each item.",
        "Stamp duty, registration fees aur transaction charges ka allocation clear nahi mila. Har charge ka payer confirm karo.",
    ),
    "termination": (
        "No termination clause found. Ask how either side can end the agreement.",
        "Termination ka clause nahi mila. Poochho ki dono taraf se agreement kaise khatam ho sakta hai.",
    ),
}  # fmt: skip


def detect_doc_type(text: str) -> tuple[str, float]:
    """Return rent, employment, property-purchase or unknown plus keyword confidence.

    This is a triage heuristic, not a trained document classifier. Property-specific evidence
    is scored separately because buyer/seller words alone also occur in unrelated documents.
    """
    low = text.lower()
    counts = {
        "rent_agreement": sum(len(re.findall(re.escape(w), low)) for w in _RENT),
        "offer_and_bond": sum(len(re.findall(re.escape(w), low)) for w in _OFFER),
        "property_purchase": sum(len(re.findall(re.escape(w), low)) for w in _PROPERTY),
    }
    # Avoid letting generic words such as "buyer" or "seller" classify a document alone.
    property_specific = sum(
        len(re.findall(re.escape(w), low)) for w in _PROPERTY
        if w not in {"buyer", "seller", "builder"}
    )
    if property_specific < 2:
        counts["property_purchase"] = 0
    winner, score = max(counts.items(), key=lambda item: item[1])
    total = sum(counts.values())
    if score < 3 or list(counts.values()).count(score) > 1 or total == 0:
        return "unknown", 0.0
    return winner, round(score / total, 3)


def find_gaps(doc_type: str, present: set[str], predictable: set[str]) -> list[str]:
    """Expected clause ids that are absent. Only clause types the classifier can predict count."""
    return [c for c in EXPECTED.get(doc_type, []) if c in predictable and c not in present]
