"""Component evaluation helpers (facts, risk, retrieval) shared by scripts and tests."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from clauselens.facts import extract_facts

# Synthetic slot -> entity type / role (names/places/dates are not extracted).
SLOT_TYPE = {
    **dict.fromkeys(
        ("rent", "deposit_amount", "repair_limit", "maintenance_charge", "bond_amount",
         "training_cost"), "money"),
    **dict.fromkeys(
        ("refund_days", "long_refund_days", "notice_days", "emp_notice_days", "er_notice_days",
         "cure_days", "default_days", "verification_days", "guest_days", "lock_in_months",
         "escalation_months", "bond_months", "recovery_months", "retention_months",
         "entry_notice_hours", "penalty_months"), "duration"),
    **dict.fromkeys(("escalation_pct", "deduction_pct"), "percent"),
}  # fmt: skip
SLOT_ROLE = {
    "rent": "monthly_rent", "deposit_amount": "deposit_amount", "repair_limit": "repair_limit",
    "maintenance_charge": "maintenance_charge", "bond_amount": "bond_amount",
    "training_cost": "training_cost", "refund_days": "refund_window",
    "long_refund_days": "refund_window", "notice_days": "notice_period",
    "emp_notice_days": "notice_period", "er_notice_days": "notice_period",
    "cure_days": "cure_period", "default_days": "default_grace",
    "verification_days": "verification_window", "guest_days": "guest_limit",
    "lock_in_months": "lock_in_period", "escalation_months": "escalation_interval",
    "bond_months": "bond_period", "recovery_months": "recovery_period",
    "retention_months": "retention_period", "entry_notice_hours": "entry_notice",
    "penalty_months": "exit_penalty", "escalation_pct": "rent_increase",
    "deduction_pct": "deduction_cap",
}  # fmt: skip


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / max(1, b[1] - b[0])  # share of the gold span that is covered


def evaluate_facts(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Span precision/recall/F1 per type (>=50% of the gold span covered) and role accuracy."""
    tp, fp, fn = Counter(), Counter(), Counter()
    role_ok, role_n = 0, 0
    wrong_roles: Counter = Counter()
    for r in records:
        gold = [e for e in r.get("entities", []) if e["label"] in SLOT_TYPE]
        pred = [
            f
            for f in extract_facts(r["text"], r["labels"][0])
            if f.type in ("money", "duration", "percent")
        ]
        used: set[int] = set()
        for e in gold:
            kind = SLOT_TYPE[e["label"]]
            hit = next(
                (i for i, f in enumerate(pred)
                 if i not in used and f.type == kind
                 and _overlap((f.start, f.end), (e["start"], e["end"])) >= 0.5),
                None,
            )  # fmt: skip
            if hit is None:
                fn[kind] += 1
                continue
            used.add(hit)
            tp[kind] += 1
            role_n += 1
            if pred[hit].role == SLOT_ROLE[e["label"]]:
                role_ok += 1
            else:
                wrong_roles[(SLOT_ROLE[e["label"]], pred[hit].role)] += 1
        for i, f in enumerate(pred):
            if i not in used:
                fp[f.type] += 1
    out: dict[str, Any] = {"per_type": {}, "n_records": len(records)}
    for kind in ("money", "duration", "percent"):
        p = tp[kind] / max(1, tp[kind] + fp[kind])
        rec = tp[kind] / max(1, tp[kind] + fn[kind])
        out["per_type"][kind] = {
            "precision": round(p, 4), "recall": round(rec, 4),
            "f1": round(2 * p * rec / max(1e-9, p + rec), 4), "support": tp[kind] + fn[kind],
        }  # fmt: skip
    out["role_accuracy"] = round(role_ok / max(1, role_n), 4)
    out["top_role_confusions"] = [(list(k), v) for k, v in wrong_roles.most_common(8)]
    return out


def macro_f1_and_accuracy(
    y_true: list[str], y_pred: list[str], labels: list[str]
) -> dict[str, Any]:
    per: dict[str, dict[str, float]] = defaultdict(dict)
    for lab in labels:
        tp = sum(t == lab and p == lab for t, p in zip(y_true, y_pred, strict=True))
        fp = sum(t != lab and p == lab for t, p in zip(y_true, y_pred, strict=True))
        fn = sum(t == lab and p != lab for t, p in zip(y_true, y_pred, strict=True))
        pr, rc = tp / max(1, tp + fp), tp / max(1, tp + fn)
        per[lab] = {"precision": round(pr, 4), "recall": round(rc, 4),
                    "f1": round(2 * pr * rc / max(1e-9, pr + rc), 4)}  # fmt: skip
    correct = sum(t == p for t, p in zip(y_true, y_pred, strict=True))
    return {
        "accuracy": round(correct / max(1, len(y_true)), 4),
        "macro_f1": round(sum(v["f1"] for v in per.values()) / max(1, len(per)), 4),
        "per_class": dict(per),
    }  # fmt: skip


def evaluate_pipeline(analyzer, docs: list[dict[str, Any]]) -> dict[str, Any]:
    """End-to-end check on synthetic documents (ground truth known per clause)."""
    from clauselens.data.text import normalize_text

    label_ok = label_n = risk_ok = risk_n = red_tp = red_n = other_ok = other_n = type_ok = 0
    by_source: Counter = Counter()
    for doc in docs:
        report = analyzer.analyze(doc["text"], "en")
        type_ok += report["doc_type"] == doc["doc_type"]
        by_text = {normalize_text(c["text"]): c for c in report["clauses"]}
        for item in doc["items"]:
            clause = by_text.get(normalize_text(item["text"]))
            if clause is None:
                continue
            if item["kind"] == "clause":
                label_n += 1
                label_ok += clause["primary"] == item["clause_id"]
                by_source[clause["label_source"]] += 1
                if item["risk"]:
                    risk_n += 1
                    risk_ok += clause["risk"] == item["risk"]
                    if item["risk"] == "red":
                        red_n += 1
                        red_tp += clause["risk"] == "red"
            else:
                other_n += 1
                other_ok += clause["primary"] == "other"
    return {
        "n_docs": len(docs), "n_clauses": label_n,
        "doc_type_accuracy": round(type_ok / max(1, len(docs)), 4),
        "clause_label_accuracy": round(label_ok / max(1, label_n), 4),
        "risk_accuracy_on_assessable_clauses": round(risk_ok / max(1, risk_n), 4),
        "red_recall": round(red_tp / max(1, red_n), 4),
        "non_clause_segments_labelled_other": round(other_ok / max(1, other_n), 4),
        "label_source_counts": dict(by_source),
    }  # fmt: skip
