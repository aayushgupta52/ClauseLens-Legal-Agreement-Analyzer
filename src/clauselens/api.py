"""FastAPI app (Phase 10): analysis API plus the single-page UI (Phase 11)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from clauselens import __version__
from clauselens.calculators import bond_cost
from clauselens.ingest import MAX_BYTES, MAX_CHARS, IngestError, extract_text
from clauselens.paths import REPORTS, ROOT
from clauselens.pii import mask_pii
from clauselens.pipeline import Analyzer
from clauselens.qa import ask
from clauselens.segment import segment_document
from clauselens.storage import Store
from clauselens.synth.generator import _rng, assemble_document
from clauselens.translation import (
    LANGUAGE_NAMES,
    TranslationUnavailable,
    detect_language,
    match_original_segments,
    normalize_unicode_digits,
    translate_report,
    translate_text,
    translation_provider_label,
    translation_status,
    validate_language,
)

WEB_DIR = Path(__file__).parent / "web"
# Use the configured repository root. In Docker the package is installed into
# site-packages, so deriving the project root from __file__ points to Python's
# installation directory instead of /app. ROOT honors CLAUSELENS_ROOT and is
# resolved correctly both in local development and in the Render container.
PROJECT_DIR = ROOT
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
Language = str


def _validate_output_language(value: str) -> str:
    try:
        return validate_language(value)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _validate_source_language(value: str) -> str:
    try:
        return validate_language(value, allow_auto=True)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    language: Language = "en"  # explanation/report language
    source_language: str = "auto"
    persist: bool = True

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _validate_output_language(value)

    @field_validator("source_language")
    @classmethod
    def validate_source_language(cls, value: str) -> str:
        return _validate_source_language(value)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    language: Language = "en"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _validate_output_language(value)


class StatelessAskRequest(AskRequest):
    clauses: list[dict[str, Any]] = Field(max_length=2000)


class TranslateReportRequest(BaseModel):
    report: dict[str, Any]
    language: str

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _validate_output_language(value)


class FeedbackRequest(BaseModel):
    clause_index: int = Field(ge=0)
    labels: list[str] | None = None
    risk: Literal["green", "amber", "red"] | None = None
    note: str = Field(default="", max_length=1000)


class BondRequest(BaseModel):
    bond_amount: float = Field(ge=0)
    bond_months: float = Field(gt=0)
    months_served: float = Field(ge=0)
    mode: Literal["pro_rata", "full"] = "pro_rata"


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'",
}


def create_app(analyzer: Analyzer | None = None, store: Store | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.analyzer = analyzer or Analyzer()
        app.state.store = store or Store()
        yield

    app = FastAPI(title="ClauseLens", version=__version__, lifespan=lifespan)
    if analyzer is not None and store is not None:  # tests may skip the lifespan
        app.state.analyzer, app.state.store = analyzer, store

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response

    def _analyze(
        text: str, language: str, persist: bool, source_language: str = "auto"
    ) -> dict[str, Any]:
        if not text or not text.strip():
            raise HTTPException(422, "text is empty")
        safe_source, source_pii_counts, _ = mask_pii(text.strip())
        detected = detect_language(safe_source) if source_language == "auto" else source_language
        if detected == "auto":
            detected = "en"

        analysis_text = safe_source
        source_was_translated = False
        translation_notice = None
        if detected not in {"en", "hinglish"}:
            try:
                # Normalize decimal digits only in the temporary analysis copy so machine
                # translation is less likely to alter Hindi/Gujarati/Arabic-script amounts.
                analysis_text = translate_text(normalize_unicode_digits(safe_source), detected, "en")
            except TranslationUnavailable as exc:
                raise HTTPException(503, str(exc)) from exc
            source_was_translated = True
            privacy_sentence = (
                "Translation ran on this computer. "
                if translation_provider_label() == "Local LibreTranslate"
                else (
                    "Warning: document text was sent to the configured "
                    "remote translation service. "
                )
            )
            translation_notice = (
                f"This document was detected as {LANGUAGE_NAMES.get(detected, detected)} and "
                "translated to English for clause classification. " + privacy_sentence +
                "Machine translation may miss legal nuance. Compare findings with the original "
                "wording before relying on them."
            )
        elif detected == "hinglish":
            translation_notice = (
                "This document appears to use romanized Hinglish. "
                "English-oriented clause detection may be less reliable; "
                "compare findings with the original wording."
            )

        # The current fact extractor and classifier use ASCII-oriented number patterns. Normalize
        # decimal digits in the private analysis copy only; original_text below keeps the upload's
        # exact wording (including Devanagari/Gujarati/Arabic digits).
        analysis_text = normalize_unicode_digits(analysis_text)

        # Keep the existing deterministic English/Hinglish explainer; other languages are applied
        # to the human-facing report fields after classification.
        internal_language = language if language == "hinglish" else "en"
        try:
            canonical = app.state.analyzer.analyze(analysis_text, internal_language)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

        source_segments = segment_document(safe_source)
        analysis_segments = segment_document(analysis_text)
        report_clauses = canonical.get("clauses", [])
        matched_segments = match_original_segments(source_segments, analysis_segments, report_clauses)
        for clause, original_segment in zip(report_clauses, matched_segments, strict=True):
            if original_segment is not None:
                clause["original_text"] = original_segment.text
                clause["original_heading"] = original_segment.heading
                clause["original_number"] = original_segment.number
            else:
                clause["original_text"] = None
                clause["original_heading"] = None
                clause["original_number"] = None

        canonical["source_language"] = detected
        canonical["source_language_name"] = LANGUAGE_NAMES.get(detected, detected.title())
        canonical["source_language_was_auto_detected"] = source_language == "auto"
        canonical["translated_for_analysis"] = source_was_translated
        canonical["translation_provider"] = (
            translation_provider_label() if source_was_translated else None
        )
        canonical["translation_notice"] = translation_notice
        canonical["pii_masked"] = {
            key: max(int(canonical.get("pii_masked", {}).get(key, 0)), int(value))
            for key, value in source_pii_counts.items()
        } | {
            key: value for key, value in canonical.get("pii_masked", {}).items()
            if key not in source_pii_counts
        }
        canonical["persisted"] = persist

        try:
            if language in {"en", "hinglish"}:
                view_report = deepcopy(canonical)
            else:
                view_report = translate_report(canonical, language)
        except TranslationUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

        if persist:
            app.state.store.save(canonical)
        # The React client keeps this canonical copy so changing the output language never chains
        # translations (e.g. Hindi -> Marathi); stored reports remain the auditable base analysis.
        view_report["persisted"] = persist
        view_report["canonical_report"] = deepcopy(canonical)
        return view_report

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        # Prefer the compiled React app when present; keep the original HTML UI as fallback.
        react_index = FRONTEND_DIST / "index.html"
        return FileResponse(react_index if react_index.is_file() else WEB_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        a: Analyzer = app.state.analyzer
        return {"status": "ok", "version": __version__, "classifier": a.engine.classifier.name,
                "runner": a.runner, "labels": a.engine.classifier.active_labels}  # fmt: skip

    @app.get("/api/translation/status")
    def get_translation_status() -> dict[str, Any]:
        return translation_status()

    @app.post("/api/translate/report")
    def translate_existing_report(req: TranslateReportRequest) -> dict[str, Any]:
        # React includes canonical_report; direct API callers may send the base report.
        canonical = req.report.get("canonical_report") or req.report
        try:
            view_report = translate_report(canonical, req.language)
        except TranslationUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        view_report["canonical_report"] = deepcopy(canonical)
        view_report["persisted"] = bool(canonical.get("persisted", False))
        return view_report

    @app.post("/api/analyze")
    def analyze(req: AnalyzeRequest) -> dict[str, Any]:
        return _analyze(req.text, req.language, req.persist, req.source_language)

    @app.post("/api/analyze/file")
    async def analyze_file(
        file: UploadFile = File(...), language: str = Form("en"),
        source_language: str = Form("auto"), persist: bool = Form(True)
    ) -> dict[str, Any]:
        try:
            language = _validate_output_language(language)
            source_language = _validate_source_language(source_language)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        data = await file.read(MAX_BYTES + 1)
        try:
            text = extract_text(file.filename or "", data, source_language=source_language)
        except IngestError as exc:
            raise HTTPException(400, str(exc)) from exc
        return await run_in_threadpool(_analyze, text, language, persist, source_language)

    @app.get("/api/sample")
    def sample(doc_type: Literal["rent_agreement", "offer_and_bond"] = "rent_agreement") -> dict:
        doc = assemble_document(doc_type, _rng("sample", doc_type), doc_id="sample", pool=1)
        return {"doc_type": doc_type, "text": doc["text"]}

    @app.get("/api/reports")
    def list_reports() -> list[dict[str, Any]]:
        return app.state.store.list()

    @app.get("/api/reports/{report_id}")
    def get_report(report_id: str) -> dict[str, Any]:
        report = app.state.store.get(report_id)
        if report is None:
            raise HTTPException(404, "report not found")
        return report

    @app.delete("/api/reports/{report_id}")
    def delete_report(report_id: str) -> dict[str, bool]:
        if not app.state.store.delete(report_id):
            raise HTTPException(404, "report not found")
        return {"deleted": True}

    def _answer_question(
        clauses: list[dict[str, Any]], question: str, language: str
    ) -> dict[str, Any]:
        detected_question_language = detect_language(question)
        analysis_question = question
        if detected_question_language not in {"en", "hinglish"}:
            try:
                analysis_question = translate_text(
                    normalize_unicode_digits(question), detected_question_language, "en"
                )
            except TranslationUnavailable as exc:
                raise HTTPException(503, str(exc)) from exc
        analysis_question = normalize_unicode_digits(analysis_question)
        analysis_language = "hinglish" if language == "hinglish" else "en"
        result = ask(clauses, analysis_question, analysis_language)
        if language not in {"en", "hinglish"}:
            try:
                result["answer"] = translate_text(result["answer"], "en", language)
            except TranslationUnavailable as exc:
                raise HTTPException(503, str(exc)) from exc
        return result

    @app.post("/api/reports/{report_id}/ask")
    def ask_report(report_id: str, req: AskRequest) -> dict[str, Any]:
        report = app.state.store.get(report_id)
        if report is None:
            raise HTTPException(404, "report not found")
        return _answer_question(report["clauses"], req.question, req.language)

    @app.post("/api/ask")
    def ask_stateless(req: StatelessAskRequest) -> dict[str, Any]:
        return _answer_question(req.clauses, req.question, req.language)

    @app.post("/api/reports/{report_id}/feedback")
    def feedback(report_id: str, req: FeedbackRequest) -> dict[str, bool]:
        report = app.state.store.get(report_id)
        if report is None:
            raise HTTPException(404, "report not found")
        if req.clause_index >= len(report["clauses"]):
            raise HTTPException(422, "clause_index out of range")
        app.state.store.add_feedback(report_id, req.clause_index, req.labels, req.risk, req.note)
        return {"saved": True}

    @app.post("/api/calc/bond")
    def calc_bond(req: BondRequest) -> dict[str, Any]:
        return bond_cost(req.bond_amount, req.bond_months, req.months_served, req.mode)

    @app.get("/api/metrics")
    def metrics() -> JSONResponse:
        out: dict[str, Any] = {}
        for name in ("baselines_v1", "components"):
            path = REPORTS / f"{name}.json"
            if path.exists():
                out[name] = json.loads(path.read_text(encoding="utf-8"))
        return JSONResponse(out)

    # Static assets for a production React build. Mounted after API routes so /api/* stays active.
    if (FRONTEND_DIST / "index.html").is_file():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="react-frontend")

    return app
