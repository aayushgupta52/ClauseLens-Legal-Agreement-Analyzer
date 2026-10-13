from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from clauselens.hints import hint_label
from clauselens.pipeline import Analyzer

DATA = Path(__file__).parent / "data"


def test_heading_hints_are_unambiguous_only():
    assert hint_label("SECURITY DEPOSIT", "x") == ("security_deposit", "heading")
    assert hint_label("Notice Period", "x") == ("notice_period", "heading")
    assert hint_label("Service Agreement", "x") == ("service_bond", "heading")
    assert hint_label("Resignation", "nothing special") == (None, None)  # two clause types match
    assert hint_label("GRANT OF LICENSE", "nothing special") == (None, None)


def test_phrase_hints():
    assert hint_label(None, "You agree to serve the Company for 24 months.") == (
        "service_bond",
        "phrase",
    )
    assert hint_label(None, "The Licensee shall not sub-let the flat.") == (
        "subletting_guests",
        "phrase",
    )
    assert hint_label(None, "security deposit and lock-in period") == (None, None)  # conflicting
    assert hint_label(None, "The sky is blue.") == (None, None)


def test_heading_overrides_the_classifier_but_only_when_hints_are_on(engine):
    text = "1. SERVICE BOND: zzz qqq lorem ipsum.\n"
    with_hints = Analyzer(engine).analyze(text, "en")["clauses"][0]
    assert with_hints["primary"] == "service_bond" and with_hints["label_source"] == "heading"
    plain = Analyzer(replace(engine, use_hints=False)).analyze(text, "en")["clauses"][0]
    assert plain["label_source"] == "classifier"


def _clauses(analyzer, name):
    report = analyzer.analyze((DATA / name).read_text(encoding="utf-8"), "en")
    return report, {c["heading"] or c["index"]: c for c in report["clauses"]}


def test_real_style_offer_letter(analyzer):
    report, clauses = _clauses(analyzer, "real_style_offer.txt")
    assert report["doc_type"] == "offer_and_bond"
    expected = {
        "Service Agreement": ("service_bond", "full_amount_regardless"),
        "Training": ("training_cost_recovery", "no_limit"),
        "Notice Period": ("notice_period", "no_notice"),
        "Documents": ("document_retention", "originals_withheld"),
        "Deductions": ("salary_deductions", "withholding_final_dues"),
    }
    for heading, (clause_id, flag) in expected.items():
        clause = clauses[heading]
        assert clause["primary"] == clause_id and clause["risk"] == "red", heading
        assert flag in [f["flag"] for f in clause["flags"]], heading
    assert report["summary"]["overall_risk"] == "red"
    bond = clauses["Service Agreement"]
    assert {"bond_amount", "bond_period"} <= {f["role"] for f in bond["facts"]}


def test_real_style_rent_agreement(analyzer):
    report, clauses = _clauses(analyzer, "real_style_rent.txt")
    assert report["doc_type"] == "rent_agreement"
    assert report["pii_masked"] == {"AADHAAR": 1, "PHONE": 1}
    assert "4567 1234 9087" not in str(report) and "9820012345" not in str(report)
    assert clauses["LOCK-IN"]["primary"] == "lock_in_period"
    assert "forfeiture" in [f["flag"] for f in clauses["LOCK-IN"]["flags"]]
    assert clauses["DEPOSIT"]["primary"] == "security_deposit"
    assert clauses["LICENSE FEE"]["primary"] == "payment_terms"
    assert {"rent_escalation", "eviction_default"} <= {m["clause_id"] for m in report["missing"]}
