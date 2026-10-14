"""End-to-end analysis pipeline (Phases 7-9): PII shield -> segment -> classify -> facts ->
risk -> (review) -> explain -> gaps -> report.

The steps are plain functions over a state dict. `build_graph` wires them into a LangGraph
StateGraph (with a conditional "review" edge for uncertain clauses); `run_sequential` runs the
very same functions without LangGraph, and the tests assert both give the same report.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict

from clauselens.classifier import Classifier, load_classifier
from clauselens.data.taxonomy import Taxonomy
from clauselens.explain import RISK_LABEL, explain_clause
from clauselens.facts import extract_facts
from clauselens.gaps import GAP_TEXT, detect_doc_type, find_gaps
from clauselens.hints import hint_label, property_clause_label
from clauselens.ingest import MAX_CHARS
from clauselens.paths import MODELS
from clauselens.pii import mask_pii
from clauselens.risk import LEVELS, RISK_CLAUSES, RiskEngine, load_risk_engine, overall_score
from clauselens.segment import segment_document

log = logging.getLogger(__name__)
LOW_CONFIDENCE = 0.5
DISCLAIMER = {
    "en": "ClauseLens is an awareness tool, not legal advice. Risk labels are heuristics; have an advocate review anything important.",
    "hinglish": "ClauseLens ek awareness tool hai, legal advice nahi. Risk labels sirf heuristics hain; zaroori cheezein kisi advocate se check karwao.",
}


class State(TypedDict, total=False):
    text: str
    language: str
    pii: dict[str, int]
    doc_type: str
    doc_type_confidence: float
    clauses: list[dict[str, Any]]
    missing: list[dict[str, Any]]
    report: dict[str, Any]


@dataclass
class Engine:
    classifier: Classifier
    risk: RiskEngine
    taxonomy: Taxonomy
    use_hints: bool = True

    @property
    def clause_ids(self) -> set[str]:
        return {c.id for c in self.taxonomy.clauses}

    @classmethod
    def load(cls, models_dir=MODELS) -> Engine:
        return cls(
            load_classifier(models_dir),
            load_risk_engine(models_dir),
            Taxonomy.load().with_other(["out_of_domain"]),
        )


def primary_label(labels: list[str], top: list[dict[str, Any]]) -> str:
    """The clause type to act on: best-scoring predicted label, "other" if nothing else."""
    for item in top:
        if item["label"] in labels:
            return item["label"]
    return labels[0] if labels else "other"


def make_nodes(engine: Engine) -> dict[str, Callable[[State], State]]:
    def ingest(state: State) -> State:
        text = state["text"].replace("\r\n", "\n").replace("\r", "\n")[:MAX_CHARS]
        masked, counts, _ = mask_pii(text)
        return {"text": masked, "pii": counts}

    def segment(state: State) -> State:
        doc_type, confidence = detect_doc_type(state["text"])
        clauses = [
            {
                "index": s.index,
                "number": s.number,
                "heading": s.heading,
                "kind": s.kind,
                "text": s.text,
            }
            for s in segment_document(state["text"])
        ]
        return {"clauses": clauses, "doc_type": doc_type, "doc_type_confidence": confidence}

    def classify(state: State) -> State:
        clauses = state["clauses"]
        body = [c for c in clauses if c["kind"] == "clause"]
        preds = engine.classifier.predict([c["text"] for c in body])
        for clause in clauses:
            clause.update(
                labels=["other"], top=[], confidence=None, primary="other", label_source="none"
            )
        doc_type = state.get("doc_type", "unknown")
        for clause, pred in zip(body, preds, strict=True):
            labels = pred.labels or ["other"]
            top = [{"label": lab, "score": score} for lab, score in pred.top]
            clause.update(
                labels=labels,
                top=top,
                confidence=pred.confidence,
                primary=primary_label(labels, top),
                label_source="classifier",
            )
            # A precise property-sale phrase must override a misleading generic ML label,
            # even when the ML model reports high confidence.
            property_label = property_clause_label(doc_type, clause.get("heading"), clause["text"])
            if property_label:
                clause.update(labels=[property_label], primary=property_label,
                              label_source="property_rule", confidence=max(pred.confidence, 0.85))
                continue
            if engine.use_hints:
                hint, kind = hint_label(clause["heading"], clause["text"])
                weak = clause["primary"] == "other" or (clause["confidence"] or 0) < LOW_CONFIDENCE
                if hint in engine.clause_ids and (kind == "heading" or weak):
                    clause.update(labels=[hint], primary=hint, label_source=kind)
        return {"clauses": clauses}

    def facts(state: State) -> State:
        for clause in state["clauses"]:
            found = extract_facts(clause["text"], clause["primary"])
            clause["facts"] = [f.as_dict() for f in found]
            clause["_facts"] = found
        return {"clauses": state["clauses"]}

    def risk(state: State) -> State:
        clauses = state["clauses"]
        scored = [c for c in clauses if c["primary"] in RISK_CLAUSES]
        # The current risk model was trained primarily on rental/employment clauses. For new
        # property-only categories, use transparent rule flags until labelled property data exists.
        property_rule_only = {"property_specifications", "title_and_encumbrances", "possession_handover",
                              "booking_payment", "cancellation_refund", "registration_charges"}
        model_scored = [c for c in scored if c["primary"] not in property_rule_only]
        model_probas = engine.risk.ml_predict([c["primary"] for c in model_scored], [c["text"] for c in model_scored])
        proba_by_index = {c["index"]: p for c, p in zip(model_scored, model_probas, strict=True)}
        for clause in clauses:
            clause.update(
                risk=None, risk_source=None, flags=[], needs_review=False, review_reasons=[]
            )
        for clause in scored:
            proba = proba_by_index.get(clause["index"], {})
            result = engine.risk.assess(clause["primary"], clause["text"], clause["_facts"], proba)
            clause.update(
                risk=result.risk,
                risk_source=result.source,
                flags=[{"flag": f, "level": lv} for f, lv in result.flags],
                needs_review=result.needs_review,
            )
            if result.needs_review:
                clause["review_reasons"].append("model says high risk but no explicit rule matched")
        return {"clauses": clauses}

    def needs_review(clause: dict[str, Any]) -> bool:
        low = clause["confidence"] is not None and clause["confidence"] < LOW_CONFIDENCE
        return bool((low and clause["primary"] != "other") or clause["needs_review"])

    def route(state: State) -> str:
        return "review" if any(needs_review(c) for c in state["clauses"]) else "explain"

    def review(state: State) -> State:
        for clause in state["clauses"]:
            if clause["confidence"] is not None and clause["confidence"] < LOW_CONFIDENCE:
                if clause["primary"] != "other":
                    clause["review_reasons"].append("low classifier confidence")
            clause["needs_review"] = needs_review(clause)
        return {"clauses": state["clauses"]}

    def explain(state: State) -> State:
        lang = state.get("language", "en")
        for clause in state["clauses"]:
            flags = [(f["flag"], f["level"]) for f in clause["flags"]]
            if clause["primary"] == "other" and not clause["facts"]:
                clause["explanation"] = None
            else:
                clause["explanation"] = explain_clause(
                    clause["primary"], clause["risk"], flags, clause["_facts"], lang
                )
            clause.pop("_facts", None)
        return {"clauses": state["clauses"]}

    def gaps(state: State) -> State:
        lang = 0 if state.get("language", "en") == "en" else 1
        present = {c["primary"] for c in state["clauses"]}
        predictable = set(engine.classifier.active_labels)
        if state.get("doc_type") == "property_purchase":
            predictable.update({"property_specifications", "title_and_encumbrances", "possession_handover",
                                "booking_payment", "cancellation_refund", "registration_charges"})
        names = {c.id: c.name for c in engine.taxonomy.clauses}
        missing = [
            {"clause_id": cid, "name": names.get(cid, cid), "message": GAP_TEXT[cid][lang]}
            for cid in find_gaps(state["doc_type"], present, predictable)
        ]
        return {"missing": missing}

    def report(state: State) -> State:
        lang = state.get("language", "en")
        clauses = state["clauses"]
        assessed = [c["risk"] for c in clauses if c["risk"]]
        counts = {lv: assessed.count(lv) for lv in LEVELS}
        overall = max(assessed, key=LEVELS.index) if assessed else "green"
        top_flags = [
            {"clause_index": c["index"], "heading": c["heading"] or c["primary"], "flag": f["flag"]}
            for c in clauses for f in c["flags"] if f["level"] == "red"
        ]  # fmt: skip
        key_facts = [
            {"clause_index": c["index"], "role": f["role"], "type": f["type"], "text": f["text"]}
            for c in clauses for f in c["facts"] if f["type"] != "date"
        ]  # fmt: skip
        return {
            "report": {
                "report_id": uuid.uuid4().hex[:12],
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "language": lang,
                "doc_type": state["doc_type"],
                "doc_type_confidence": state["doc_type_confidence"],
                "classifier": engine.classifier.name,
                "summary": {
                    "overall_risk": overall,
                    "overall_label": RISK_LABEL[lang][overall] if assessed else None,
                    "risk_score": overall_score(assessed),
                    "counts": counts,
                    "n_segments": len(clauses),
                    "n_assessed": len(assessed),
                    "n_needs_review": sum(c["needs_review"] for c in clauses),
                    "red_flags": top_flags,
                },
                "clauses": clauses,
                "missing": state["missing"],
                "key_facts": key_facts,
                "pii_masked": state["pii"],
                "disclaimer": DISCLAIMER[lang],
            }
        }

    return {"ingest": ingest, "segment": segment, "classify": classify, "facts": facts, "risk": risk,
            "review": review, "explain": explain, "gaps": gaps, "report": report, "_route": route}  # fmt: skip


ORDER = ["ingest", "segment", "classify", "facts", "risk"]


def run_sequential(engine: Engine, state: State) -> State:
    nodes = make_nodes(engine)
    state = dict(state)  # type: ignore[assignment]
    for name in ORDER:
        state.update(nodes[name](state))
    if nodes["_route"](state) == "review":
        state.update(nodes["review"](state))
    for name in ("explain", "gaps", "report"):
        state.update(nodes[name](state))
    return state


def build_graph(engine: Engine):
    """LangGraph version of the same pipeline (conditional edge risk -> review | explain)."""
    from langgraph.graph import END, START, StateGraph

    nodes = make_nodes(engine)
    graph = StateGraph(State)
    for name in (*ORDER, "review", "explain", "gaps", "report"):
        graph.add_node(name, nodes[name])
    graph.add_edge(START, "ingest")
    for a, b in zip(ORDER, ORDER[1:], strict=False):
        graph.add_edge(a, b)
    graph.add_conditional_edges("risk", nodes["_route"], {"review": "review", "explain": "explain"})
    graph.add_edge("review", "explain")
    graph.add_edge("explain", "gaps")
    graph.add_edge("gaps", "report")
    graph.add_edge("report", END)
    return graph.compile()


class Analyzer:
    """Holds the engine (and the compiled graph, if LangGraph is installed)."""

    def __init__(self, engine: Engine | None = None, use_graph: bool = True) -> None:
        self.engine = engine or Engine.load()
        self.graph = None
        if use_graph:
            try:
                self.graph = build_graph(self.engine)
            except ImportError:
                log.warning("langgraph not installed: using the sequential runner")
        self.runner = "langgraph" if self.graph is not None else "sequential"

    def analyze(self, text: str, language: str = "en") -> dict[str, Any]:
        if language not in ("en", "hinglish"):
            raise ValueError("language must be 'en' or 'hinglish'")
        if not text or not text.strip():
            raise ValueError("text is empty")
        state: State = {"text": text, "language": language}
        final = (
            self.graph.invoke(state)
            if self.graph is not None
            else run_sequential(self.engine, state)
        )
        report = final["report"]
        report["runner"] = self.runner
        return report
