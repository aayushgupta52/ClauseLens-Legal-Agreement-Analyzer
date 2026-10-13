from __future__ import annotations

import io
import json

import pytest
from conftest import make_pdf
from fastapi.testclient import TestClient

from clauselens.api import create_app
from clauselens.storage import Store
from clauselens.synth.generator import generate_documents

DOC = generate_documents(2, seed=21)[0]


@pytest.fixture()
def client(analyzer):
    return TestClient(create_app(analyzer, Store("sqlite://")))


def test_health_and_ui_and_security_headers(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["classifier"] == "tfidf_char_svm"
    page = client.get("/")
    assert page.status_code == 200 and "ClauseLens" in page.text
    assert (
        page.headers["x-frame-options"] == "DENY"
        and "default-src 'self'" in page.headers["content-security-policy"]
    )


def test_analyze_persist_list_get_and_delete(client):
    report = client.post("/api/analyze", json={"text": DOC["text"], "language": "hinglish"}).json()
    rid = report["report_id"]
    assert report["persisted"] and report["language"] == "hinglish"
    assert client.get("/api/reports").json()[0]["report_id"] == rid
    assert client.get(f"/api/reports/{rid}").json()["summary"] == report["summary"]
    assert client.delete(f"/api/reports/{rid}").json() == {"deleted": True}
    assert client.get(f"/api/reports/{rid}").status_code == 404
    assert client.delete(f"/api/reports/{rid}").status_code == 404


def test_persist_false_stores_nothing(client):
    report = client.post("/api/analyze", json={"text": DOC["text"], "persist": False}).json()
    assert report["persisted"] is False and client.get("/api/reports").json() == []


def test_validation_errors(client):
    assert client.post("/api/analyze", json={"text": ""}).status_code == 422
    assert client.post("/api/analyze", json={"text": "x", "language": "xx"}).status_code == 422
    assert client.post("/api/analyze", json={"text": "   "}).status_code == 422
    assert client.get("/api/reports/nope").status_code == 404


def test_file_uploads(client):
    from docx import Document

    txt = client.post("/api/analyze/file", files={"file": ("a.txt", DOC["text"].encode())})
    assert txt.status_code == 200 and txt.json()["summary"]["n_assessed"] > 0
    buf = io.BytesIO()
    document = Document()
    for line in DOC["text"].splitlines():
        document.add_paragraph(line)
    document.save(buf)
    assert (
        client.post("/api/analyze/file", files={"file": ("a.docx", buf.getvalue())}).status_code
        == 200
    )
    pdf = client.post(
        "/api/analyze/file",
        files={
            "file": (
                "a.pdf",
                make_pdf(
                    "1. SECURITY DEPOSIT: The Tenant pays a refundable deposit of Rs. 40,000/- refunded within 30 days."
                ),
            )
        },
    )
    assert pdf.status_code == 200
    bad = client.post("/api/analyze/file", files={"file": ("a.exe", b"MZ")})
    assert bad.status_code == 400 and "unsupported" in bad.json()["detail"]


def test_ask_stored_and_stateless(client):
    report = client.post("/api/analyze", json={"text": DOC["text"]}).json()
    question = {
        "question": "What is the notice period?"
        if report["doc_type"] == "offer_and_bond"
        else "Security deposit kitna hai?"
    }
    stored = client.post(f"/api/reports/{report['report_id']}/ask", json=question).json()
    stateless = client.post("/api/ask", json={**question, "clauses": report["clauses"]}).json()
    assert stored["found"] and stored == stateless
    assert client.post("/api/reports/nope/ask", json=question).status_code == 404


def test_feedback(client):
    report = client.post("/api/analyze", json={"text": DOC["text"]}).json()
    url = f"/api/reports/{report['report_id']}/feedback"
    assert client.post(
        url, json={"clause_index": 1, "risk": "red", "note": "too harsh"}
    ).json() == {"saved": True}
    assert client.post(url, json={"clause_index": 9999}).status_code == 422
    assert client.post(url, json={"clause_index": 1, "risk": "purple"}).status_code == 422
    assert client.post("/api/reports/nope/feedback", json={"clause_index": 0}).status_code == 404


def test_bond_calculator_and_sample(client):
    ok = client.post(
        "/api/calc/bond", json={"bond_amount": 120000, "bond_months": 12, "months_served": 3}
    )
    assert ok.json()["payable"] == 90000
    assert (
        client.post(
            "/api/calc/bond", json={"bond_amount": 1, "bond_months": 0, "months_served": 1}
        ).status_code
        == 422
    )
    for doc_type in ("rent_agreement", "offer_and_bond"):
        assert len(client.get(f"/api/sample?doc_type={doc_type}").json()["text"]) > 500
    assert client.get("/api/sample?doc_type=loan").status_code == 422


def test_metrics_endpoint(client, tmp_path, monkeypatch):
    import clauselens.api as api

    monkeypatch.setattr(api, "REPORTS", tmp_path)
    assert client.get("/api/metrics").json() == {}
    (tmp_path / "components.json").write_text(json.dumps({"facts": {"role_accuracy": 1}}))
    assert client.get("/api/metrics").json() == {"components": {"facts": {"role_accuracy": 1}}}


def test_multilingual_hindi_analysis_preserves_original_and_uses_english_for_classifier(client, monkeypatch):
    import clauselens.api as api

    original = (
        "1. सुरक्षा जमा: किरायेदार को ₹20,000 जमा राशि देनी होगी।\n"
        "2. मासिक किराया: किरायेदार हर महीने ₹15,000 किराया देगा।"
    )
    translated_english = (
        "1. SECURITY DEPOSIT: The tenant must pay ₹20,000 as a deposit.\n"
        "2. MONTHLY RENT: The tenant pays ₹15,000 rent each month."
    )
    calls = []

    def fake_translate(text, source, target):
        calls.append((source, target))
        if source == "hi" and target == "en":
            return translated_english
        if source == "en" and target == "hi":
            return "हिन्दी अनुवाद: " + text
        return text

    monkeypatch.setattr(api, "translate_text", fake_translate)
    monkeypatch.setattr(
        api,
        "translate_report",
        lambda report, target: {**report, "language": target, "disclaimer": "यह कानूनी सलाह नहीं है।"},
    )

    response = client.post(
        "/api/analyze",
        json={"text": original, "language": "hi", "source_language": "auto", "persist": False},
    )
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["language"] == "hi"
    assert view["source_language"] == "hi"
    assert view["translated_for_analysis"] is True
    assert view["canonical_report"]["language"] == "en"
    assert calls[0] == ("hi", "en")
    original_clauses = [clause for clause in view["clauses"] if clause.get("original_text")]
    assert original_clauses
    assert any("किरायेदार" in clause["original_text"] for clause in original_clauses)


def test_translate_report_endpoint_uses_canonical_copy(client, monkeypatch):
    import clauselens.api as api

    base = {"report_id": "demo", "language": "en", "summary": {}, "clauses": []}
    monkeypatch.setattr(
        api, "translate_report", lambda report, target: {**report, "language": target, "disclaimer": "हिन्दी"}
    )
    response = client.post("/api/translate/report", json={"report": {**base, "canonical_report": base}, "language": "hi"})
    assert response.status_code == 200
    assert response.json()["language"] == "hi"
    assert response.json()["canonical_report"]["language"] == "en"


def test_translation_status_endpoint_is_visible(client, monkeypatch):
    import clauselens.api as api

    monkeypatch.setattr(api, "translation_status", lambda: {"ready": False, "supported_output_codes": []})
    response = client.get("/api/translation/status")
    assert response.status_code == 200
    assert response.json()["ready"] is False


def test_non_english_analysis_fails_closed_when_translation_is_unavailable(client, monkeypatch):
    import clauselens.api as api

    def unavailable(*args, **kwargs):
        raise api.TranslationUnavailable("local translation service is unavailable")

    monkeypatch.setattr(api, "detect_language", lambda text: "hi")
    monkeypatch.setattr(api, "translate_text", unavailable)
    response = client.post(
        "/api/analyze",
        json={"text": "किरायेदार को सुरक्षा जमा राशि वापस मिलेगी।", "language": "en", "persist": False},
    )
    assert response.status_code == 503
    assert "translation service is unavailable" in response.json()["detail"]


def test_hindi_question_is_translated_for_retrieval_and_answer(client, monkeypatch):
    import clauselens.api as api

    def fake_translate(text, source, target):
        if source == "hi" and target == "en":
            return "What is the security deposit amount?"
        if source == "en" and target == "hi":
            return "सुरक्षा जमा के बारे में: " + text
        return text

    monkeypatch.setattr(api, "translate_text", fake_translate)
    clauses = [{
        "index": 2, "kind": "clause", "number": "2", "heading": "Security deposit",
        "text": "The tenant shall pay a refundable security deposit of ₹20,000.",
        "original_text": "किरायेदार ₹20,000 की वापसी योग्य सुरक्षा जमा राशि देगा।",
        "original_heading": "सुरक्षा जमा", "original_number": "2",
        "labels": ["security_deposit"],
        "explanation": {"facts_line": "security deposit: ₹20,000"},
    }]
    response = client.post(
        "/api/ask",
        json={"question": "सुरक्षा जमा कितनी है?", "language": "hi", "clauses": clauses},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["found"] is True
    assert result["answer"].startswith("सुरक्षा जमा के बारे में:")
    assert result["citations"][0]["text"] == clauses[0]["original_text"]
