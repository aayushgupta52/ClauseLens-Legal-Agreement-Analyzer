from __future__ import annotations

import pytest

from clauselens import ingest
from clauselens.ingest import IngestError, extract_text


def test_scanned_pdf_uses_configured_ocr_language_when_available(monkeypatch):
    monkeypatch.setattr(ingest, "_pdf_text", lambda data: "")
    seen = {}

    def fake_ocr(data, source_language="auto"):
        seen["language"] = source_language
        return "किरायेदार को ₹20,000 जमा राशि देनी होगी। यह एक पर्याप्त लंबा परीक्षण दस्तावेज है।"

    monkeypatch.setattr(ingest, "_ocr_pdf_text", fake_ocr)
    text = extract_text("scanned.pdf", b"%PDF-test", source_language="hi")
    assert "किरायेदार" in text
    assert seen["language"] == "hi"


def test_unsupported_ocr_languages_fail_instead_of_silently_using_english(monkeypatch):
    monkeypatch.setattr(ingest, "_pdf_text", lambda data: "")
    monkeypatch.setattr(
        ingest,
        "_ocr_pdf_text",
        lambda data, source_language="auto": (_ for _ in ()).throw(
            IngestError("OCR language data 'xyz' is not installed in Tesseract.")
        ),
    )
    with pytest.raises(IngestError, match="language data"):
        extract_text("scanned.pdf", b"%PDF-test", source_language="xyz")
