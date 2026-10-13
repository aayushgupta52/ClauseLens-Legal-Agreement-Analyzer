from __future__ import annotations

import copy

import pytest

from clauselens.pipeline import Analyzer, build_graph, run_sequential
from clauselens.synth.generator import generate_documents

DOCS = generate_documents(4, seed=11)


def _strip(report):
    report = copy.deepcopy(report)
    for key in ("report_id", "created_utc", "runner"):
        report.pop(key, None)
    return report


def test_langgraph_and_sequential_runners_agree(engine):
    graph = build_graph(engine)
    for doc in DOCS[:2]:
        state = {"text": doc["text"], "language": "en"}
        assert _strip(graph.invoke(state)["report"]) == _strip(
            run_sequential(engine, state)["report"]
        )


def test_report_structure(analyzer):
    doc = DOCS[0]
    report = analyzer.analyze(doc["text"], "en")
    assert report["doc_type"] == doc["doc_type"] and report["runner"] in ("langgraph", "sequential")
    summary = report["summary"]
    assert set(summary["counts"]) == {"green", "amber", "red"}
    assert summary["n_assessed"] == sum(summary["counts"].values()) > 0
    assert 0 <= summary["risk_score"] <= 100
    kinds = [c["kind"] for c in report["clauses"]]
    assert kinds[0] == "preamble" and kinds[-1] == "trailer"
    for c in report["clauses"]:
        assert {
            "index",
            "text",
            "labels",
            "primary",
            "risk",
            "flags",
            "facts",
            "needs_review",
        } <= set(c)
        assert "_facts" not in c
        if c["risk"]:
            assert c["explanation"]["reasons"] is not None


def test_report_is_json_serialisable(analyzer):
    import json

    json.dumps(analyzer.analyze(DOCS[1]["text"], "hinglish"))


def test_pii_is_masked_before_anything_is_stored(analyzer):
    text = ("1. SECURITY DEPOSIT: The Tenant (Aadhaar 1234 5678 9012, mobile 9876543210) pays a "
            "refundable deposit of Rs. 50,000/- within 30 days.\n")  # fmt: skip
    report = analyzer.analyze(text, "en")
    blob = str(report)
    assert "1234 5678 9012" not in blob and "9876543210" not in blob
    assert report["pii_masked"] == {"AADHAAR": 1, "PHONE": 1}


def test_language_changes_the_wording_not_the_decisions(analyzer):
    en = analyzer.analyze(DOCS[0]["text"], "en")
    hi = analyzer.analyze(DOCS[0]["text"], "hinglish")
    assert [c["risk"] for c in en["clauses"]] == [c["risk"] for c in hi["clauses"]]
    assert en["disclaimer"] != hi["disclaimer"]


def test_invalid_input_is_rejected(analyzer):
    with pytest.raises(ValueError):
        analyzer.analyze("   ", "en")
    with pytest.raises(ValueError):
        analyzer.analyze("1. Deposit text here.", "fr")


def test_gibberish_does_not_crash_and_is_not_assessed(analyzer):
    report = analyzer.analyze("lorem ipsum dolor sit amet\n\nconsectetur adipiscing elit", "en")
    assert report["summary"]["n_assessed"] == 0 and report["summary"]["overall_risk"] == "green"


def test_sequential_fallback_works_without_langgraph(engine):
    analyzer = Analyzer(engine, use_graph=False)
    assert analyzer.runner == "sequential"
    assert analyzer.analyze(DOCS[0]["text"], "en")["summary"]["n_assessed"] > 0
