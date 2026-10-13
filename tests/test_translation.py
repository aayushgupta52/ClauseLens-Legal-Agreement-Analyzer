from __future__ import annotations

from clauselens import translation


def test_detects_common_indian_scripts_without_network_or_models():
    assert translation.detect_language("किरायेदार को जमा राशि वापस मिलेगी।") == "hi"
    marathi = "भाडेकरूने दर महिन्याला भाडे द्यावे आणि मालकाला कळवावे।"
    assert translation.detect_language(marathi) == "mr"
    assert translation.detect_language("ભાડૂઆતે દર મહિને ભાડું ચૂકવવું પડશે.") == "gu"
    assert translation.detect_language("தமிழில் வாடகை ஒப்பந்தம்") == "ta"


def test_protected_literals_round_trip_without_changing_money_or_dates():
    original = "Rent is ₹25,000 for 11 months, with a 12/10/2026 review date and 5% increase."
    protected, literals = translation._protect_literals(original)
    restored = translation._restore_literals(protected, literals)
    assert restored == original
    assert "₹25,000" not in protected


def test_report_translation_preserves_original_clause_and_machine_fields(monkeypatch):
    def fake_translate_many(values, source, target):
        assert source == "en"
        assert target == "hi"
        return [f"हिन्दी: {value}" for value in values]

    monkeypatch.setattr(translation, "translate_many", fake_translate_many)
    report = {
        "language": "en",
        "disclaimer": "Not legal advice.",
        "summary": {"overall_label": "High risk", "risk_score": 78},
        "missing": [{"name": "Deposit refund date", "message": "No refund deadline found."}],
        "clauses": [{
            "heading": "Security deposit",
            "text": "The landlord may retain the deposit.",
            "original_text": "मकान मालिक जमा राशि रख सकता है।",
            "explanation": {
                "summary": "The entire deposit may be kept.",
                "risk_label": "High risk",
                "facts_line": "Deposit: ₹25,000",
                "reasons": ["No conditions are stated."],
                "tips": ["Ask for a written refund deadline."],
            },
            "flags": [{"flag": "security_deposit", "display_text": "Deposit may be withheld"}],
        }],
        "key_facts": [{"role": "monthly_rent", "value": "₹25,000"}],
    }

    translated = translation.translate_report(report, "hi")
    clause = translated["clauses"][0]
    assert translated["language"] == "hi"
    assert translated["disclaimer"].startswith("हिन्दी:")
    assert clause["explanation"]["summary"].startswith("हिन्दी:")
    assert clause["original_text"] == "मकान मालिक जमा राशि रख सकता है।"
    assert clause["text"] == "The landlord may retain the deposit."
    assert clause["flags"][0]["flag"] == "security_deposit"
    assert translated["key_facts"][0]["value"] == "₹25,000"
    assert report["language"] == "en"  # source object wasn't mutated


def test_invalid_language_is_rejected():
    try:
        translation.validate_language("xx")
    except ValueError as exc:
        assert "Unsupported language" in str(exc)
    else:
        raise AssertionError("unsupported language unexpectedly accepted")


def test_latin_script_language_detection_accepts_langdetect_result(monkeypatch):
    monkeypatch.setattr(translation, "_langdetect", lambda text: "fr")
    text = "Ce contrat de location définit le dépôt de garantie et les obligations du locataire."
    assert translation.detect_language(text) == "fr"


def test_translate_text_preserves_protected_amounts(monkeypatch):
    calls = []

    def fake_translate_raw(text, source, target, output_format="text"):
        calls.append((source, target, output_format))
        return text

    monkeypatch.setattr(translation, "_translate_raw", fake_translate_raw)
    original = "Le loyer est de ₹25,000 par mois pour 11 mois."
    assert translation.translate_text(original, "fr", "hi") == original
    assert calls == [("fr", "hi", "text")]


def test_modified_money_placeholder_fails_closed():
    import pytest

    protected, literals = translation._protect_literals("Deposit is ₹25,000.")
    altered = protected.replace("ZXQCLLITERAL0000QXZ", "changed-token")
    with pytest.raises(
        translation.TranslationUnavailable, match="altered a protected amount/date token"
    ):
        translation._restore_literals(altered, literals)


def test_unicode_digits_are_normalized_only_for_analysis_copy():
    assert translation.normalize_unicode_digits("₹२०,०००; ૩૦ દિવસ; ١٢") == "₹20,000; 30 દિવસ; 12"


def test_original_segment_matching_uses_numbers_when_order_changes():
    from types import SimpleNamespace

    source = [
        SimpleNamespace(number="२.", text="जमा राशि", heading="जमा", index=1),
        SimpleNamespace(number="१.", text="किराया", heading="किराया", index=2),
    ]
    analysis = [
        SimpleNamespace(number="1.", text="rent", heading="Rent", index=1),
        SimpleNamespace(number="2.", text="deposit", heading="Deposit", index=2),
    ]
    clauses = [{"number": "1."}, {"number": "2."}]
    matched = translation.match_original_segments(source, analysis, clauses)
    assert [segment.text if segment else None for segment in matched] == ["किराया", "जमा राशि"]


def test_original_segment_matching_does_not_pair_unequal_number_sequences_by_position():
    from types import SimpleNamespace

    source = [SimpleNamespace(number="१.", text="पहली धारा", heading=None, index=1)]
    analysis = [SimpleNamespace(number="2.", text="second clause", heading=None, index=1)]
    clauses = [{"number": "2."}]
    matched = translation.match_original_segments(source, analysis, clauses)
    assert matched == [None]



def test_persian_script_is_detected_when_language_detector_identifies_fa(monkeypatch):
    monkeypatch.setattr(translation, "_langdetect", lambda text: "fa")
    assert translation.detect_language("این قرارداد اجاره شامل ودیعه و تعهدات مستأجر است.") == "fa"


def test_translation_status_reports_directional_language_pairs(monkeypatch):
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps([
                {"code": "en", "name": "English", "targets": ["hi", "fr"]},
                {"code": "hi", "name": "Hindi", "targets": ["en"]},
                {"code": "fr", "name": "French", "targets": ["en"]},
                {"code": "de", "name": "German", "targets": []},
            ]).encode("utf-8")

    monkeypatch.setattr(translation, "translate_url", lambda: "http://127.0.0.1:5000")
    monkeypatch.setattr(translation.urllib.request, "urlopen", lambda *a, **k: FakeResponse())
    status = translation.translation_status()
    assert status["ready"] is True
    assert status["local"] is True
    assert status["supported_output_codes"] == ["fr", "hi"]
    assert status["supported_source_codes_to_english"] == ["en", "fr", "hi"]


def test_report_translation_adds_display_labels_without_overwriting_machine_flags(monkeypatch):
    monkeypatch.setattr(
        translation,
        "translate_many",
        lambda values, source, target: [f"हिंदी {value}" for value in values],
    )
    report = {
        "language": "en",
        "summary": {"overall_risk": "red", "red_flags": [{"heading": "Deposit", "flag": "security_deposit"}]},
        "clauses": [],
    }
    translated = translation.translate_report(report, "hi")
    red_flag = translated["summary"]["red_flags"][0]
    assert red_flag["display_heading"] == "हिंदी Deposit"
    assert red_flag["display_flag"] == "हिंदी security deposit"
    assert red_flag["flag"] == "security_deposit"
    assert report["summary"]["red_flags"][0] == {"heading": "Deposit", "flag": "security_deposit"}
