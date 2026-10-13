from __future__ import annotations

import pytest

from clauselens.explain import FLAG_TEXT, RISK_LABEL, check_grounded, explain_clause, facts_line
from clauselens.facts import extract_facts

CLAUSE = "The deposit of Rs. 1,50,000/- shall be refunded within 30 days."


def test_explanation_languages_and_content():
    facts = extract_facts(CLAUSE, "security_deposit")
    flags = [("forfeiture", "red"), ("no_limit", "red")]
    en = explain_clause("security_deposit", "red", flags, facts, "en")
    hi = explain_clause("security_deposit", "red", flags, facts, "hinglish")
    assert en["risk_label"] == RISK_LABEL["en"]["red"] and hi["risk_label"] == "Zyada risky"
    assert len(en["reasons"]) == len(en["tips"]) == 2 and en["reasons"] != hi["reasons"]
    assert "Deposit: Rs. 1,50,000/-" in en["facts_line"]
    assert "Deposit kitna hai" in hi["summary"]


def test_unknown_language_and_unscored_clause():
    with pytest.raises(ValueError):
        explain_clause("security_deposit", "red", [], [], "fr")
    plain = explain_clause("governing_law", None, [], [], "en")
    assert plain["risk_label"] is None and plain["reasons"] == []


def test_facts_line_is_grounded_in_the_clause():
    line = facts_line(extract_facts(CLAUSE, "security_deposit"))
    assert check_grounded(line, CLAUSE)
    assert not check_grounded("Deposit: Rs. 99,999/-", CLAUSE)


def test_every_flag_text_has_four_parts():
    assert all(len(v) == 4 and all(v) for v in FLAG_TEXT.values())
