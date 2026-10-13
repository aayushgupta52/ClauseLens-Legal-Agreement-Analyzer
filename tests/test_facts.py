from __future__ import annotations

import pytest

from clauselens.evalkit import evaluate_facts
from clauselens.facts import extract_facts, to_days, to_months, to_number
from clauselens.synth.generator import generate_samples


def _pairs(text, clause_id=None):
    return [(f.type, f.text) for f in extract_facts(text, clause_id)]


def test_money_formats():
    text = "Rs. 1,50,000/-, Rs.35,000/-, INR 25,000, ₹40,000, Rs. 5 lakh and rupees."
    assert _pairs(text) == [
        ("money", "Rs. 1,50,000/-"), ("money", "Rs.35,000/-"), ("money", "INR 25,000"),
        ("money", "₹40,000"), ("money", "Rs. 5 lakh"),
    ]  # fmt: skip


def test_durations_percentages_and_dates():
    text = ("Within twelve (12) months, 30 days or two months' rent; 1.5 times is not a duration; "
            "increase of 10 per cent and 5%; signed on 5th day of March, 2025 and 01/04/2025.")  # fmt: skip
    assert _pairs(text) == [
        ("duration", "twelve (12) months"), ("duration", "30 days"), ("duration", "two months"),
        ("percent", "10 per cent"), ("percent", "5%"),
        ("date", "5th day of March, 2025"), ("date", "01/04/2025"),
    ]  # fmt: skip


def test_values_never_overlap_and_are_verbatim_spans():
    text = "Pay Rs. 25,000/- within 30 days; 12 months bond."
    facts = extract_facts(text)
    assert all(text[f.start : f.end] == f.text for f in facts)
    assert all(a.end <= b.start for a, b in zip(facts, facts[1:], strict=False))


@pytest.mark.parametrize(
    ("clause_id", "text", "roles"),
    [
        ("security_deposit", "A deposit of Rs. 50,000/- refunded within 30 days.",
         ["deposit_amount", "refund_window"]),
        ("service_bond", "If the Employee leaves before 12 months, pay Rs. 1,00,000/-.",
         ["bond_period", "bond_amount"]),
        ("rent_escalation", "Rent Rs. 30,000 rises 5% after every 12 months.",
         ["monthly_rent", "rent_increase", "escalation_interval"]),
    ],
)  # fmt: skip
def test_roles_follow_the_clause_type(clause_id, text, roles):
    assert [f.role for f in extract_facts(text, clause_id)] == roles


def test_numeric_conversion():
    assert to_number("Rs. 1,50,000/-") == 150000 and to_number("Rs. 2 lakh") == 200000
    assert to_number("twelve (12) months") == 12 and to_number("forty-five days") == 45
    assert to_number("no digits here") is None
    assert to_months("one year") == 12 and to_months("90 days") == 3 and to_months("5%") is None
    assert to_days("two months") == 60 and to_days("48 hours") == 2


def test_synthetic_extraction_quality():
    samples, _ = generate_samples(n_train=3, n_val=1, n_test=6, seed=3)
    result = evaluate_facts([r.model_dump() for r in samples if r.split == "test"])
    assert all(v["f1"] == 1.0 for v in result["per_type"].values())
    assert result["role_accuracy"] >= 0.9
