from __future__ import annotations

import pytest

from clauselens import gold

VALID = {"security_deposit", "service_bond", "termination", "other"}


def _rows(types, risks):
    return [
        {"doc_id": "d1", "idx": str(i), "kind": "clause", "text": f"text {i}",
         "clause_types": t, "risk": r, "notes": ""}
        for i, (t, r) in enumerate(zip(types, risks, strict=True))
    ]  # fmt: skip


A = _rows(
    ["security_deposit", "service_bond", "other", "security_deposit", "other", "service_bond"],
    ["green", "red", "", "amber", "", "red"],
)


def test_prepare_rows_segments_a_document():
    rows = gold.prepare_rows(
        "doc1", "1. First clause text goes here.\n2. Second clause text here.\n"
    )
    assert [r["idx"] for r in rows] == [0, 1]
    assert all(r["clause_types"] == "" and r["risk"] == "" for r in rows)


def test_validation_reports_each_problem():
    bad = _rows(["", "nonsense", "other|service_bond", "service_bond", "termination"],
                ["", "green", "", "purple", ""])  # fmt: skip
    errors = "\n".join(gold.validate_rows(bad, VALID))
    for needle in (
        "empty",
        "unknown clause",
        "cannot be combined",
        "risk must be",
        "risk is required",
    ):
        assert needle in errors
    assert gold.validate_rows(A, VALID) == []


def test_csv_roundtrip(tmp_path):
    path = tmp_path / "x.csv"
    gold.write_csv(path, [{**r, "idx": int(r["idx"])} for r in A])
    assert gold.read_csv(path) == A


def test_agreement_perfect_and_partial():
    labels = sorted(VALID)
    perfect = gold.agreement(A, A, labels)
    assert perfect["clause_type_kappa_macro"] == 1.0 and perfect["risk_kappa_linear"] == 1.0
    b = _rows(
        ["other", "service_bond", "other", "security_deposit", "other", "service_bond"],
        ["", "red", "", "red", "", "amber"],
    )
    partial = gold.agreement(A, b, labels)
    assert partial["n_rows_compared"] == 6
    assert partial["clause_type_kappa_macro"] < 1.0 and partial["risk_kappa_linear"] < 1.0


def test_export_records_and_rejection_of_invalid_sheets():
    recs = gold.to_records(A, VALID)
    assert recs[0]["split"] == "test" and recs[0]["sources"] == ["gold"]
    assert recs[0]["labels"] == ["security_deposit"] and recs[2]["risk"] is None
    with pytest.raises(ValueError):
        gold.to_records(_rows([""], [""]), VALID)
