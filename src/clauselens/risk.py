"""Risk engine (Phase 6): transparent rules plus a small ML model, combined conservatively.

green / amber / red follow docs/risk_rubric.md. Thresholds and patterns are working
hypotheses that an advocate must validate; the tool never claims a clause is illegal.
The final risk is the WORSE of the rule layer and the model, so a rule can only raise it.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from clauselens.baselines import load_records
from clauselens.facts import Fact, to_days, to_months, to_number
from clauselens.paths import MODELS, PROCESSED
from clauselens.synth.templates import SPECS

log = logging.getLogger(__name__)
LEVELS = ("green", "amber", "red")
RISK_CLAUSES = frozenset(SPECS)  # the clause types the engine can assess
RISK_MODEL_FILE = "risk_lr.joblib"


@dataclass(frozen=True)
class Rule:
    flag: str
    level: str
    pattern: re.Pattern[str]


def _r(flag: str, level: str, pattern: str) -> Rule:
    return Rule(flag, level, re.compile(pattern, re.I))


_PARTY = r"(?:owner|landlord|licensor|employer|company|organisation)"
RULES: list[Rule] = [
    # ---- red: hard flags ----
    _r("discretionary_deductions", "red", r"at the " + _PARTY + r"'s discretion|as it deems fit"),
    _r(
        "no_limit",
        "red",
        r"no (?:time )?limit|without any (?:ceiling|limit)|a stated limit|no ceiling|reimburse the entire (?:training )?cost",
    ),
    _r(
        "no_notice",
        "red",
        r"without (?:any |prior )?(?:notice|intimation|compensation)|with or without notice"
        r"|at any time and by any amount|immediately without",
    ),  # fmt: skip
    _r("forfeiture", "red", r"forfeit|retain the deposit"),
    _r(
        "originals_withheld",
        "red",
        r"original[^.]{0,120}(?:until|for the duration|for the entire|entire tenancy)",
    ),  # fmt: skip
    _r(
        "one_sided_exit",
        "red",
        r"only the (?:tenant|licensee) is bound|may terminate at any time, but",
    ),  # fmt: skip
    _r(
        "full_amount_regardless",
        "red",
        r"(?:irrespective|regardless) of (?:the period|how much)|in full if service ends",
    ),  # fmt: skip
    _r(
        "unilateral_change",
        "red",
        r"from time to time, without prior consent|as decided by the " + _PARTY,
    ),  # fmt: skip
    _r("seller_specification_change", "red",
       r"(?:seller|promoter|builder)[^.]{0,240}(?:change|alter|modify)[^.]{0,240}without prior (?:written )?consent|(?:change|alter|modify)[^.]{0,160}(?:carpet area|property specifications|parking allocation|common facilities)[^.]{0,120}without prior (?:written )?consent"),
    _r("unclear_title", "red",
       r"no assurance of clear title|not responsible for undisclosed liens|accepts the property even if[^.]{0,100}(?:lien|ownership claim|encumbrance)"),
    _r("possession_delay", "red",
       r"possession[^.]{0,100}(?:indefinitely|without compensation)|waives claims arising from possession delay|no fixed handover date"),
    _r("booking_forfeiture", "red",
       r"(?:entire|all) (?:booking amount|amounts paid)[^.]{0,100}(?:non-refundable|forfeit|forfeited)|forfeit(?:ure|ed)?[^.]{0,100}(?:booking amount|amounts paid)"),
    _r("entry_without_notice", "red", r"without prior intimation|at all hours"),
    _r(
        "no_inventory",
        "red",
        r"no inventory is recorded|alone shall decide|final and binding on the",
    ),  # fmt: skip
    _r("self_help_eviction", "red", r"lock the premises|take back possession at once"),
    _r("tenant_bears_structural", "red", r"including structural"),
    _r(
        "unitemised_charges",
        "red",
        r"without any right to see the bills|demand shall be final|specifies from time to time",
    ),  # fmt: skip
    _r(
        "withholding_final_dues",
        "red",
        r"withhold(?:ing)? the final|final (?:dues|settlement)[^.]{0,40}withheld",
    ),
    # ---- amber ----
    _r(
        "undefined_amount",
        "amber",
        r"as (?:determined|calculated|computed) by the|calculates it|a reasonable amount",
    ),
    _r("exit_penalty", "amber", r"(?:shall pay|payment equal to)[^.]{0,60}rent"),
    _r("informal_notice", "amber", r"orally or by message|in any manner"),
    _r("market_rate_reset", "amber", r"market rates?|prevailing market"),
    _r("future_increases_on_tenant", "amber", r"future increase|later revisions"),
    _r(
        "tenant_bears_fittings",
        "amber",
        r"all repairs and replacements of fittings|all wear and tear",
    ),
    _r(
        "strict_guest_limit",
        "amber",
        r"requires the prior consent|unless the " + _PARTY + r" approves",
    ),
    _r("short_default_window", "amber", r"remains unpaid for|non-payment of rent beyond"),
    _r("costs_on_tenant", "amber", r"at the (?:tenant|licensee)'s (?:own cost|expense)"),
    _r("mandatory_repainting", "amber", r"repainting"),
    _r("loss_recovery", "amber", r"recovery of advances|recover any dues or losses"),
    _r(
        "temporary_retention",
        "amber",
        r"retain the original[^.]{0,80}for up to|held by the [a-z]+ for background verification",
    ),  # fmt: skip
    _r("flat_refund", "amber", r"shall refund the training cost|towards training shall be payable"),
    _r("broad_deductions", "amber", r"adjusts all dues, damages|settled all charges"),
]

# Numeric thresholds on extracted facts. [VALIDATE] with an advocate before relying on them.
THRESHOLDS = {
    "refund_window": ("long_refund_window", to_days, 30),  # days
    "lock_in_period": ("long_lock_in", to_months, 12),  # months
    "rent_increase": ("high_escalation", to_number, 10),  # percent
    "deduction_cap": ("high_deduction_cap", to_number, 10),  # percent
    "bond_period": ("long_bond", to_months, 24),  # months
    "notice_period": ("long_notice", to_days, 90),  # days
}


@dataclass
class RiskResult:
    risk: str
    source: str  # rules | model | both
    flags: list[tuple[str, str]] = field(default_factory=list)  # (flag, level)
    ml_risk: str | None = None
    ml_proba: dict[str, float] = field(default_factory=dict)
    needs_review: bool = False


def _worse(a: str, b: str) -> str:
    return a if LEVELS.index(a) >= LEVELS.index(b) else b


def rule_flags(text: str, facts: list[Fact]) -> list[tuple[str, str]]:
    found = [(r.flag, r.level) for r in RULES if r.pattern.search(text)]
    for fact in facts:
        spec = THRESHOLDS.get(fact.role)
        if spec:
            flag, convert, limit = spec
            value = convert(fact.text)
            if value is not None and value > limit and (flag, "amber") not in found:
                found.append((flag, "amber"))
    return found


def _pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
                        (
                            "char",
                            TfidfVectorizer(
                                analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2
                            ),
                        ),
                    ]  # fmt: skip
                ),
            ),
            ("clf", LogisticRegression(C=10, max_iter=2000, class_weight="balanced")),
        ]
    )


def _ml_text(clause_id: str, text: str) -> str:
    return f"clause_{clause_id} {text}"


class RiskEngine:
    def __init__(self, model: Pipeline | None) -> None:
        self.model = model

    def ml_predict(self, clause_ids: list[str], texts: list[str]) -> list[dict[str, float]]:
        if self.model is None or not texts:
            return [{} for _ in texts]
        probs = self.model.predict_proba(
            [_ml_text(c, t) for c, t in zip(clause_ids, texts, strict=True)]
        )
        return [dict(zip(self.model.classes_, map(float, row), strict=True)) for row in probs]

    def assess(
        self, clause_id: str, text: str, facts: list[Fact], ml_proba: dict[str, float] | None = None
    ) -> RiskResult:
        flags = rule_flags(text, facts)
        rule_level = "green"
        for _, level in flags:
            rule_level = _worse(rule_level, level)
        ml_proba = ml_proba if ml_proba is not None else self.ml_predict([clause_id], [text])[0]
        ml_level = max(ml_proba, key=ml_proba.get) if ml_proba else None
        final = _worse(rule_level, ml_level) if ml_level else rule_level
        if flags and ml_level == rule_level:
            source = "both"
        elif flags and LEVELS.index(rule_level) >= LEVELS.index(ml_level or "green"):
            source = "rules"
        else:
            source = "model"
        review = final == "red" and not any(level == "red" for _, level in flags)
        return RiskResult(final, source, flags, ml_level, ml_proba, review)


def train_risk_model(records: list[dict]) -> Pipeline:
    rows = [r for r in records if r.get("risk") and r["labels"][0] in RISK_CLAUSES]
    model = _pipeline()
    model.fit([_ml_text(r["labels"][0], r["text"]) for r in rows], [r["risk"] for r in rows])
    return model


def _risk_training_records() -> list[dict]:
    records = []
    for split in ("train", "val"):
        records += load_records(PROCESSED / "synth_v1" / f"{split}.jsonl")
    if not records:
        from clauselens.synth.generator import generate_samples

        samples, _ = generate_samples()
        records = [r.model_dump() for r in samples if r.split in ("train", "val")]
    return records


def load_risk_engine(models_dir: Path = MODELS) -> RiskEngine:
    path = models_dir / RISK_MODEL_FILE
    if path.exists():
        return RiskEngine(joblib.load(path))
    log.info("%s missing, training it now", path)
    model = train_risk_model(_risk_training_records())
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return RiskEngine(model)


def overall_score(levels: list[str]) -> int:
    """0-100 document risk: share of the worst possible outcome over the assessed clauses."""
    if not levels:
        return 0
    return round(100 * sum(LEVELS.index(lv) for lv in levels) / (2 * len(levels)))
