from __future__ import annotations

import pytest

from clauselens.explain import FLAG_TEXT
from clauselens.facts import extract_facts
from clauselens.risk import (
    RISK_CLAUSES,
    RULES,
    THRESHOLDS,
    RiskEngine,
    overall_score,
    rule_flags,
)


def flags(text, clause_id=None):
    return {f for f, _ in rule_flags(text, extract_facts(text, clause_id))}


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("The Owner may deduct any amount, and the balance is refunded at the Owner's discretion.",
         "discretionary_deductions"),
        ("The Employer may terminate the employment at any time without notice.", "no_notice"),
        ("The Employer shall retain the original certificates until the bond is complete.",
         "originals_withheld"),
        ("The full bond amount of Rs. 1,00,000/- is payable, irrespective of the period served.",
         "full_amount_regardless"),
        ("The deposit shall stand forfeited.", "forfeiture"),
        ("The Tenant shall bear all repairs, including structural repairs.",
         "tenant_bears_structural"),
    ],
)  # fmt: skip
def test_red_rules_fire_on_clear_examples(text, flag):
    assert flag in flags(text)
    assert dict(rule_flags(text, []))[flag] == "red"


def test_a_fair_clause_raises_no_flag():
    fair = ("The deposit shall be refunded within 15 days of the Tenant vacating the premises, "
            "after deducting only unpaid rent and the cost of proven damage.")  # fmt: skip
    assert flags(fair, "security_deposit") == set()


def test_numeric_thresholds_raise_amber_flags():
    assert "long_lock_in" in flags("A lock-in period of 18 months applies.", "lock_in_period")
    assert "long_lock_in" not in flags("A lock-in period of 11 months applies.", "lock_in_period")
    assert "high_escalation" in flags("Rent rises by 15% after every 12 months.", "rent_escalation")
    assert "long_refund_window" in flags("Deposit refunded within 60 days.", "security_deposit")


def test_every_flag_has_an_explanation_and_a_consistent_level():
    names = {r.flag for r in RULES} | {v[0] for v in THRESHOLDS.values()}
    assert names <= set(FLAG_TEXT)
    assert {r.level for r in RULES} == {"amber", "red"}


class _Fake:
    classes_ = ["amber", "green", "red"]


def test_final_risk_is_the_worse_of_rules_and_model():
    engine = RiskEngine(None)
    clause = "The Employer may terminate the employment at any time without notice."
    result = engine.assess("notice_period", clause, [], {"green": 0.9, "amber": 0.05, "red": 0.05})
    assert result.risk == "red" and result.source == "rules" and not result.needs_review
    fair = "Either party may end the employment by giving 30 days written notice."
    assert (
        engine.assess("notice_period", fair, [], {"green": 0.9, "amber": 0.1, "red": 0.0}).risk
        == "green"
    )
    model_only = engine.assess("notice_period", fair, [], {"green": 0.1, "amber": 0.1, "red": 0.8})
    assert model_only.risk == "red" and model_only.source == "model" and model_only.needs_review


def test_trained_engine_scores_synthetic_clauses(engine):
    text = ("The Owner may increase the rent at any time and by any amount, and the Tenant must "
            "pay the revised rent from the next month.")  # fmt: skip
    result = engine.risk.assess("rent_escalation", text, extract_facts(text, "rent_escalation"))
    assert result.risk == "red" and result.flags


def test_scope_and_score():
    assert len(RISK_CLAUSES) == 15
    assert overall_score([]) == 0 and overall_score(["green", "green"]) == 0
    assert overall_score(["red", "red"]) == 100 and overall_score(["green", "red"]) == 50
