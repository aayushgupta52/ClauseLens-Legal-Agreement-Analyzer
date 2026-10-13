"""Local-first language detection and translation helpers for ClauseLens.

Translation uses a LibreTranslate-compatible service. By default, the service is expected at
http://127.0.0.1:5000 so legal documents are not silently sent to a third party. Configure
CLAUSELENS_TRANSLATE_URL and (when required) CLAUSELENS_TRANSLATE_API_KEY to use another instance.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.request
import unicodedata
from collections.abc import Iterable
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

LANGUAGE_NAMES: dict[str, str] = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "as": "Assamese",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "eo": "Esperanto",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "kn": "Kannada",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ms": "Malay",
    "ne": "Nepali",
    "nl": "Dutch",
    "no": "Norwegian",
    "or": "Odia",
    "pa": "Punjabi",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sv": "Swedish",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh": "Chinese",
}

# The UI offers these output languages. A particular LibreTranslate installation may not have
# every model pair installed; if a pair is missing, the API reports that instead of faking output.
OUTPUT_LANGUAGES: tuple[str, ...] = tuple(LANGUAGE_NAMES)
LEGACY_LANGUAGES = {"hinglish"}

DEFAULT_TRANSLATE_URL = "http://127.0.0.1:5000"
_REQUEST_TIMEOUT_SECONDS = 45
_MAX_TRANSLATION_CHARS = 2400

# Currency/amount/time/date literals are protected while a machine-translation engine operates.
_LITERAL_RE = re.compile(
    r"(?i)(?:₹|rs\.?|inr|usd|eur|gbp|\$|€|£)\s*[\d,]+(?:\.\d+)?"
    r"|\b\d{1,4}(?:[./-]\d{1,2}){1,2}\b"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent|days?|months?|years?|weeks?|hours?|minutes?|"
    r"rupees?|lakh(?:s)?|crore(?:s)?)\b"
    r"|\b\d[\d,]*(?:\.\d+)?\b"
)


class TranslationUnavailable(RuntimeError):
    """Translation could not be performed safely with the configured provider."""


def normalize_unicode_digits(text: str) -> str:
    """Convert Unicode decimal digits (Hindi, Gujarati, Arabic, etc.) to ASCII digits.

    This is only for the internal analysis copy. The separately retained original clause text
    remains unchanged so amounts and wording can be compared with the uploaded agreement.
    """
    output: list[str] = []
    for char in text:
        if char.isdecimal():
            try:
                output.append(str(unicodedata.decimal(char)))
            except (TypeError, ValueError):
                output.append(char)
        else:
            output.append(char)
    return "".join(output)


def _normalized_clause_number(value: Any) -> str:
    if value is None:
        return ""
    normalized = normalize_unicode_digits(str(value)).strip().lower()
    normalized = re.sub(r"^(?:clause|section|article)\s+", "", normalized)
    return normalized.rstrip(".:)] ")


def match_original_segments(
    source_segments: list[Any],
    analysis_segments: list[Any],
    clauses: list[dict[str, Any]],
) -> list[Any | None]:
    """Match analyzed English clauses back to source-language segments conservatively.

    Position matching is used only when all three sequences align and numbering agrees. When
    structure differs after translation, only unique clause-number matches are accepted; uncertain
    matches become None instead of attaching the wrong source clause to a risk finding.
    """
    if not clauses:
        return []

    source_numbers = [_normalized_clause_number(getattr(item, "number", None)) for item in source_segments]
    analysis_numbers = [_normalized_clause_number(getattr(item, "number", None)) for item in analysis_segments]
    report_numbers = [_normalized_clause_number(item.get("number")) for item in clauses]

    if len(source_segments) == len(analysis_segments) == len(clauses):
        if source_numbers == analysis_numbers == report_numbers:
            return list(source_segments)
        # Unnumbered paragraphs can be safely aligned by position only when none of the three
        # representations assigned numbering and the segmentation counts are identical.
        if not any(source_numbers) and not any(analysis_numbers) and not any(report_numbers):
            return list(source_segments)


    source_by_number: dict[str, list[Any]] = {}
    analysis_by_number: dict[str, list[Any]] = {}
    for number, segment in zip(source_numbers, source_segments):
        if number:
            source_by_number.setdefault(number, []).append(segment)
    for number, segment in zip(analysis_numbers, analysis_segments):
        if number:
            analysis_by_number.setdefault(number, []).append(segment)

    matched = []
    for number in report_numbers:
        source_matches = source_by_number.get(number, []) if number else []
        analysis_matches = analysis_by_number.get(number, []) if number else []
        matched.append(
            source_matches[0]
            if len(source_matches) == 1 and len(analysis_matches) == 1
            else None
        )
    return matched


def translate_url() -> str:
    return os.environ.get("CLAUSELENS_TRANSLATE_URL", DEFAULT_TRANSLATE_URL).rstrip("/")


def _api_url(path: str) -> str:
    base = translate_url()
    if base.endswith("/translate"):
        base = base[: -len("/translate")]
    return f"{base}/{path.lstrip('/')}"


def _is_local_endpoint(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def translation_provider_label() -> str:
    """Describe the configured provider without falsely promising local processing."""
    endpoint = translate_url()
    if _is_local_endpoint(endpoint):
        return "Local LibreTranslate"
    return "Configured LibreTranslate service (remote; document text leaves this machine)"


def _script_language(text: str) -> str | None:
    counts = {
        "hi": 0, "gu": 0, "ta": 0, "te": 0, "kn": 0, "ml": 0, "or": 0,
        "bn": 0, "pa": 0, "ur": 0, "ar": 0, "zh": 0, "ja": 0, "th": 0, "ru": 0,
    }
    for char in text:
        point = ord(char)
        if 0x0900 <= point <= 0x097F:
            counts["hi"] += 1  # Hindi, Marathi and Nepali share Devanagari.
        elif 0x0A80 <= point <= 0x0AFF:
            counts["gu"] += 1
        elif 0x0B00 <= point <= 0x0B7F:
            counts["or"] += 1
        elif 0x0B80 <= point <= 0x0BFF:
            counts["ta"] += 1
        elif 0x0C00 <= point <= 0x0C7F:
            counts["te"] += 1
        elif 0x0C80 <= point <= 0x0CFF:
            counts["kn"] += 1
        elif 0x0D00 <= point <= 0x0D7F:
            counts["ml"] += 1
        elif 0x0980 <= point <= 0x09FF:
            counts["bn"] += 1  # Bengali/Assamese; langdetect refines if possible.
        elif 0x0A00 <= point <= 0x0A7F:
            counts["pa"] += 1
        elif 0x0600 <= point <= 0x06FF or 0x0750 <= point <= 0x077F:
            counts["ur"] += 1
            counts["ar"] += 1
        elif 0x4E00 <= point <= 0x9FFF:
            counts["zh"] += 1
        elif 0x3040 <= point <= 0x30FF:
            counts["ja"] += 1
        elif 0x0E00 <= point <= 0x0E7F:
            counts["th"] += 1
        elif 0x0400 <= point <= 0x04FF:
            counts["ru"] += 1
    code, score = max(counts.items(), key=lambda item: item[1])
    if score < 2:
        return None
    if code in {"ur", "ar"}:
        # Arabic and Urdu share script. Prefer a confident detector result, then use
        # Urdu-specific letters as a deterministic fallback rather than always guessing Urdu.
        detected = _langdetect(text)
        if detected in {"ur", "ar", "fa"}:
            return detected
        if any(char in text for char in "ٹ ڈ ڑ ں ھ ے ۂ ګ پ چ ژ".replace(" ", "")):
            return "ur"
        if any(char in text for char in "پ چ ژ گ ک ی".replace(" ", "")):
            return "fa"
        return "ar"
    if code == "hi":
        # Devanagari is shared by Hindi, Marathi, and Nepali. For short legal phrases,
        # generic statistical detectors can mislabel ordinary Hindi as Nepali. Prefer
        # high-signal lexical clues before asking langdetect to guess.
        low = text.lower()

        marathi_markers = (
            "आहे", "आणि", "भाडेकरू", "भाडे", "मालकाला", "महाराष्ट्र",
            "द्यावे", "कळवावे", "करारनामा", "रक्कम",
        )
        if sum(marker in low for marker in marathi_markers) >= 2:
            return "mr"

        nepali_markers = (
            "नेपाल", "गर्नुहोस्", "भाडादार", "घरधनी", "छैन", "हुनुहुन्छ",
            "सम्झौतामा", "गर्नेछ", "भाडामा", "रकम फिर्ता",
        )
        if any(marker in low for marker in nepali_markers):
            return "ne"

        hindi_markers = (
            "किरायेदार", "किराया", "जमा राशि", "वापस मिलेगी", "मकान मालिक",
            "सुरक्षा जमा", "महीने", "भुगतान", "अनुबंध", "समझौता", "देना होगा",
            "नहीं होगा", "राशि वापस", "मालिक को", "किराएदार",
        )
        if any(marker in low for marker in hindi_markers):
            return "hi"

        detected = _langdetect(text)
        if detected in {"hi", "mr", "ne"}:
            return detected
        return "hi"

    if code == "bn":
        detected = _langdetect(text)
        if detected in {"bn", "as"}:
            return detected
        return "bn"
    if code == "zh" and any(0x3040 <= ord(ch) <= 0x30FF for ch in text):
        return "ja"
    return code


def _langdetect(text: str) -> str | None:
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        guesses = detect_langs(text[:5000])
        if guesses and guesses[0].prob >= 0.55:
            return str(guesses[0].lang)
    except Exception:
        # Optional import/fallback is deliberate; script-based detection remains available.
        return None
    return None


def detect_language(text: str) -> str:
    """Detect the likely source language, with deterministic script-based fallback."""
    sample = (text or "").strip()
    if not sample:
        return "en"
    script = _script_language(sample)
    if script:
        return script

    # Recognize common romanized Hindi terms before the language detector mistakes Hinglish for
    # another Latin-script language. This is a convenience heuristic, not a linguistic guarantee.
    low = sample.lower()
    hinge_terms = (
        " hai ", " hain ", " kya ", " aur ", " nahi ", " karo ", " karna ",
        " hoga ", " milega ",
    )
    padded = f" {re.sub(r'[^a-z\s]', ' ', low)} "
    if sum(term in padded for term in hinge_terms) >= 2:
        return "hinglish"

    # Tiny samples are unreliable for language detection; leave them as English unless their script
    # made the language unambiguous above. Users can override the detected source in the UI.
    letters = sum(ch.isalpha() for ch in sample)
    if letters < 35:
        return "en"
    detected = _langdetect(sample)
    if detected in LANGUAGE_NAMES or detected == "hinglish":
        return detected
    return "en"


def validate_language(code: str, *, allow_auto: bool = False) -> str:
    value = (code or "").strip().lower()
    if allow_auto and value == "auto":
        return value
    if value in LANGUAGE_NAMES or value in LEGACY_LANGUAGES:
        return value
    choices = ", ".join(sorted((*LANGUAGE_NAMES, *LEGACY_LANGUAGES)))
    raise ValueError(f"Unsupported language '{code}'. Supported language codes: {choices}.")


def _split_text(text: str, max_chars: int = _MAX_TRANSLATION_CHARS) -> list[str]:
    """Split at line/word boundaries while preserving every source character."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if cut > start + max_chars // 2:
                end = cut + 1
        pieces.append(text[start:end])
        start = end
    return pieces


def _protect_literals(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = f"ZXQCLLITERAL{len(replacements):04d}QXZ"
        replacements[token] = match.group(0)
        return token

    return _LITERAL_RE.sub(repl, text), replacements


def _restore_literals(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for token, original in replacements.items():
        if token not in restored:
            # Some translation engines change placeholders; do not return silently corrupted
            # monetary figures or dates in a legal agreement.
            raise TranslationUnavailable(
                "The translation engine altered a protected amount/date token. "
                "Try another local translation model or review this document manually."
            )
        restored = restored.replace(token, original)
    return restored


def _translate_raw(text: str, source: str, target: str, output_format: str = "text") -> str:
    if source == target or not text:
        return text
    url = _api_url("translate")
    payload: dict[str, Any] = {
        "q": text,
        "source": source,
        "target": target,
        "format": output_format,
    }
    api_key = os.environ.get("CLAUSELENS_TRANSLATE_API_KEY", "").strip()
    if api_key:
        payload["api_key"] = api_key
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {400, 404, 422}:
            reason = (
                f"The translation service rejected language pair {source!r} → {target!r}. "
                "Check that both language models are installed on the configured LibreTranslate "
                "instance."
            )
        elif exc.code == 429:
            reason = "The translation service is rate-limiting requests. Wait and try again."
        else:
            reason = f"The translation service returned HTTP {exc.code}."
        raise TranslationUnavailable(reason) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        endpoint = translate_url()
        privacy_note = (
            ""
            if not _is_local_endpoint(endpoint)
            else " No document text was sent to a remote translation server."
        )
        raise TranslationUnavailable(
            f"Cannot reach the configured translation service at {endpoint}. Start a local "
            "LibreTranslate server on http://127.0.0.1:5000 or configure "
            "CLAUSELENS_TRANSLATE_URL (and CLAUSELENS_TRANSLATE_API_KEY if required)."
            f"{privacy_note}"
        ) from exc
    translated = result.get("translatedText") if isinstance(result, dict) else None
    if not isinstance(translated, str):
        raise TranslationUnavailable("The translation service returned an invalid response.")
    return translated


def translate_text(text: str, source: str, target: str) -> str:
    """Translate plain text in chunks and preserve monetary/date literals exactly."""
    if not text or source == target:
        return text
    source = validate_language(source)
    target = validate_language(target)
    translated_chunks: list[str] = []
    for chunk in _split_text(text):
        protected, literals = _protect_literals(chunk)
        translated = _translate_raw(protected, source, target, "text")
        translated_chunks.append(_restore_literals(translated, literals))
    return "".join(translated_chunks)


class _ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, str] = {}
        self._current: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self._current = dict(attrs).get("id")
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._current is not None:
            self.values[self._current] = "".join(self._parts)
            self._current = None
            self._parts = []


def translate_many(texts: Iterable[str], source: str, target: str) -> list[str]:
    """Translate many report strings in batched HTML requests, preserving order and numbers."""
    items = list(texts)
    if source == target:
        return items
    if not items:
        return []
    source = validate_language(source)
    target = validate_language(target)
    output = list(items)
    indexed = [(idx, text) for idx, text in enumerate(items) if text.strip()]
    # Small HTML batches reduce translation round trips while keeping markup and report structure.
    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    size = 0
    for item in indexed:
        estimated = len(item[1]) + 60
        if current and size + estimated > _MAX_TRANSLATION_CHARS:
            batches.append(current)
            current, size = [], 0
        current.append(item)
        size += estimated
    if current:
        batches.append(current)

    for batch in batches:
        ids: dict[str, tuple[int, dict[str, str]]] = {}
        paragraphs: list[str] = []
        for index, value in batch:
            protected, literals = _protect_literals(value)
            token_id = f"clsl-{index:05d}"
            ids[token_id] = (index, literals)
            paragraphs.append(f'<p id="{token_id}">{html.escape(protected)}</p>')
        markup = "<div>" + "".join(paragraphs) + "</div>"
        translated_markup = _translate_raw(markup, source, target, "html")
        parser = _ParagraphParser()
        parser.feed(translated_markup)
        if all(token in parser.values for token in ids):
            for token, (index, literals) in ids.items():
                output[index] = _restore_literals(parser.values[token], literals)
        else:
            # When a compatible server removes markup, use single-field calls as a safe fallback.
            for index, literals in ((entry[0], ids[f"clsl-{entry[0]:05d}"][1]) for entry in batch):
                protected, _ = _protect_literals(items[index])
                translated = _translate_raw(protected, source, target, "text")
                output[index] = _restore_literals(translated, literals)
    return output


def translate_report(report: dict[str, Any], target: str) -> dict[str, Any]:
    """Return a copy of a canonical English report with human-facing text translated.

    Clause source text and extracted values are retained. Numeric literals are protected during
    translation, and classifier labels/IDs are never translated because they drive calculations.
    """
    import copy

    target = validate_language(target)
    if target == "hinglish":
        if report.get("language") == "hinglish":
            return copy.deepcopy(report)
        raise TranslationUnavailable(
            "Hinglish is available for new analyses using the built-in templates. "
            "For existing reports choose English or a supported translation language."
        )
    result = copy.deepcopy(report)
    if target == "en":
        result["language"] = "en"
        return result

    # Canonical reports saved by the API are English. Never translate the original legal wording.
    fields: list[tuple[tuple[Any, ...], str]] = []

    def add(path: tuple[Any, ...], value: Any) -> None:
        if isinstance(value, str) and value.strip():
            fields.append((path, value))

    add(("disclaimer",), result.get("disclaimer"))
    add(("translation_notice",), result.get("translation_notice"))
    summary = result.setdefault("summary", {})
    add(("summary", "overall_label"), summary.get("overall_label"))
    risk_labels = {"red": "High risk", "amber": "Medium risk", "green": "Low risk"}
    summary.setdefault("display_risk_labels", {})
    for risk_code, label in risk_labels.items():
        add(("summary", "display_risk_labels", risk_code), label)
    for idx, red_flag in enumerate(summary.get("red_flags", [])):
        if not isinstance(red_flag, dict):
            continue
        if red_flag.get("heading"):
            red_flag.setdefault("original_heading", red_flag["heading"])
            red_flag["display_heading"] = red_flag["heading"]
            add(("summary", "red_flags", idx, "display_heading"), red_flag["display_heading"])
        if red_flag.get("flag"):
            red_flag["display_flag"] = str(red_flag["flag"]).replace("_", " ")
            add(("summary", "red_flags", idx, "display_flag"), red_flag["display_flag"])
    risk_code = summary.get("overall_risk")
    if risk_code in risk_labels:
        summary["display_risk_description"] = {
            "red": "Several clauses may deserve careful review before you proceed.",
            "amber": "Some clauses could benefit from clarification or negotiation.",
            "green": "No high-severity flags were identified by the current rules.",
        }[risk_code]
        add(("summary", "display_risk_description"), summary["display_risk_description"])
    doc_type = result.get("doc_type")
    doc_labels = {
        "rent_agreement": "Rental agreement",
        "offer_and_bond": "Employment offer and service bond",
        "unknown": "Agreement",
    }
    if doc_type in doc_labels:
        result["display_doc_type"] = doc_labels[doc_type]
        add(("display_doc_type",), result["display_doc_type"])
    for idx, item in enumerate(result.get("missing", [])):
        add(("missing", idx, "name"), item.get("name"))
        add(("missing", idx, "message"), item.get("message"))
    for idx, clause in enumerate(result.get("clauses", [])):
        if clause.get("heading"):
            clause["original_heading"] = clause.get("original_heading") or clause["heading"]
            add(("clauses", idx, "heading"), clause.get("heading"))
        clause_risk = clause.get("risk")
        if clause_risk in risk_labels:
            clause["display_risk_label"] = risk_labels[clause_risk]
            add(("clauses", idx, "display_risk_label"), clause["display_risk_label"])
        explanation = clause.get("explanation") or {}
        clause["explanation"] = explanation
        for key in ("summary", "text", "risk_label", "facts_line"):
            add(("clauses", idx, "explanation", key), explanation.get(key))
        for key in ("reasons", "tips"):
            values = explanation.get(key) or []
            for item_index, value in enumerate(values):
                add(("clauses", idx, "explanation", key, item_index), value)
        for flag_idx, flag in enumerate(clause.get("flags", [])):
            if flag.get("flag"):
                display_text = flag.get("flag", "").replace("_", " ")
                add(("clauses", idx, "flags", flag_idx, "display_text"), display_text)
    for idx, fact in enumerate(result.get("key_facts", [])):
        if fact.get("role"):
            add(("key_facts", idx, "display_role"), str(fact["role"]).replace("_", " "))
        if fact.get("type"):
            add(("key_facts", idx, "display_type"), str(fact["type"]).replace("_", " "))
    translated = translate_many([value for _, value in fields], "en", target)
    for (path, _), value in zip(fields, translated, strict=True):
        node: Any = result
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    result["language"] = target
    return result


def translation_status() -> dict[str, Any]:
    """Report whether the configured LibreTranslate instance is reachable and list its languages."""
    endpoint = translate_url()
    try:
        request = urllib.request.Request(
            _api_url("languages"), headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=2.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        available = [
            {
                "code": item.get("code"),
                "name": item.get("name"),
                "targets": item.get("targets", []),
            }
            for item in payload
            if isinstance(item, dict) and item.get("code")
        ]
        by_code = {item["code"]: item for item in available}
        codes = set(by_code)
        english_targets = set(by_code.get("en", {}).get("targets") or [])
        # Older LibreTranslate-compatible providers may omit directional target metadata.
        if not english_targets:
            english_targets = codes
        source_codes = {
            code for code, item in by_code.items()
            if code == "en" or "en" in set(item.get("targets") or [])
        }
        return {
            "ready": True,
            "local": _is_local_endpoint(endpoint),
            "endpoint": endpoint,
            "languages": available,
            "supported_output_codes": sorted((english_targets & codes) & set(LANGUAGE_NAMES)),
            "supported_source_codes_to_english": sorted(source_codes & set(LANGUAGE_NAMES)),
        }
    except Exception:
        return {
            "ready": False,
            "local": _is_local_endpoint(endpoint),
            "endpoint": endpoint,
            "languages": [],
            "supported_output_codes": [],
            "supported_source_codes_to_english": [],
            "detail": (
                "Translation is not running. Start LibreTranslate locally on port 5000 "
                "or configure CLAUSELENS_TRANSLATE_URL. Multilingual document classification and "
                "translated reports are unavailable until a translator is configured; "
                "English analysis remains available."
            ),
        }
