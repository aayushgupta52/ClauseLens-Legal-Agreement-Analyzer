"""Evaluate facts, risk, segmenter and the full pipeline; write reports/components.json + SUMMARY.md.

Everything here is measured on SYNTHETIC data (held-out phrasing where noted). It checks that
the components work and do not regress; it is not a real-world accuracy estimate. Only a gold
set of real agreements can give that (see `python -m clauselens.gold`).
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from clauselens.baselines import load_records
from clauselens.evalkit import evaluate_facts, evaluate_pipeline, macro_f1_and_accuracy
from clauselens.facts import extract_facts
from clauselens.paths import PROCESSED, REPORTS
from clauselens.pipeline import Analyzer, Engine
from clauselens.risk import LEVELS, RiskEngine, _worse, rule_flags, train_risk_model
from clauselens.segment import clause_recovery, segment_document
from clauselens.synth.generator import generate_documents, generate_samples


def _synth_split(name: str) -> list[dict]:
    records = load_records(PROCESSED / "synth_v1" / f"{name}.jsonl")
    if records:
        return records
    samples, _ = generate_samples()
    return [r.model_dump() for r in samples if r.split == name]


def evaluate_risk(train: list[dict], test: list[dict]) -> dict:
    engine = RiskEngine(train_risk_model(train))
    rows = [r for r in test if r.get("risk")]
    ids, texts, truth = (
        [r["labels"][0] for r in rows],
        [r["text"] for r in rows],
        [r["risk"] for r in rows],
    )
    probas = engine.ml_predict(ids, texts)
    preds: dict[str, list[str]] = {"ml_only": [], "rules_only": [], "combined": []}
    for row, proba in zip(rows, probas, strict=True):
        facts = extract_facts(row["text"], row["labels"][0])
        level = "green"
        for _, lv in rule_flags(row["text"], facts):
            level = _worse(level, lv)
        preds["ml_only"].append(max(proba, key=proba.get))
        preds["rules_only"].append(level)
        preds["combined"].append(engine.assess(row["labels"][0], row["text"], facts, proba).risk)
    out = {}
    for name, pred in preds.items():
        m = macro_f1_and_accuracy(truth, pred, list(LEVELS))
        out[name] = {"accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                     "red_recall": m["per_class"]["red"]["recall"],
                     "red_precision": m["per_class"]["red"]["precision"]}  # fmt: skip
    out["n"] = len(rows)
    return out


def write_summary(path: Path, components: dict, baselines: dict | None) -> None:
    lines = ["# ClauseLens evaluation summary", "",
             "> Everything below is measured on SYNTHETIC data unless stated. It shows the "
             "components work; it is NOT a real-world accuracy estimate. Build a gold set of "
             "real agreements for that.", ""]  # fmt: skip
    if baselines:
        lines += ["## Clause classifier baselines (micro / macro F1)", "",
                  "| model | " + " | ".join(next(iter(baselines["models"].values()))) + " |",
                  "|---|" + "---|" * len(next(iter(baselines["models"].values())))]  # fmt: skip
        for name, sets in baselines["models"].items():
            lines.append(
                f"| {name} | "
                + " | ".join(f"{v['micro_f1']:.3f} / {v['macro_f1']:.3f}" for v in sets.values())
                + " |"
            )
        lines += [
            "",
            "`synth_val` shares templates with the training data (memorised); `synth_test` uses unseen phrasing.",
            "",
        ]
    f = components["facts"]
    lines += ["## Key-fact extraction (synthetic test split, unseen phrasing)", "",
              "| type | precision | recall | F1 |", "|---|---|---|---|"]  # fmt: skip
    lines += [
        f"| {k} | {v['precision']} | {v['recall']} | {v['f1']} |" for k, v in f["per_type"].items()
    ]
    lines += [
        "",
        f"Role accuracy: {f['role_accuracy']}. Formats outside the templates (e.g. 'Rs. 5 lakh', words for amounts) are only partly covered.",
        "",
    ]
    r = components["risk"]
    lines += ["## Risk engine (synthetic test split, unseen phrasing)", "",
              "| layer | accuracy | macro F1 | red recall | red precision |", "|---|---|---|---|---|"]  # fmt: skip
    lines += [
        f"| {k} | {v['accuracy']} | {v['macro_f1']} | {v['red_recall']} | {v['red_precision']} |"
        for k, v in r.items()
        if k != "n"
    ]
    lines += [
        "",
        "The rules were written after reading BOTH phrasing pools, so `rules_only` is not a held-out estimate; `ml_only` is.",
        "",
    ]
    p = components["pipeline"]
    lines += [
        "## End-to-end pipeline (60 synthetic documents, unseen phrasing)",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    lines += [f"| {k.replace('_', ' ')} | {v} |" for k, v in p.items() if not isinstance(v, dict)]
    lines += [
        "",
        f"Segmenter clause recovery: {components['segmenter']['recovered']}/{components['segmenter']['total']} (generator and segmenter are written by the same people, so this is a regression guard).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-docs", type=int, default=60)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS)
    args = parser.parse_args()
    warnings.filterwarnings("ignore")

    train = _synth_split("train") + _synth_split("val")
    test = _synth_split("test")
    docs = generate_documents(args.n_docs, seed=2026)
    found = total = 0
    for doc in docs:
        f, t = clause_recovery(
            [i["text"] for i in doc["items"] if i["kind"] == "clause"],
            segment_document(doc["text"]),
        )
        found, total = found + f, total + t

    components = {
        "facts": evaluate_facts(test),
        "risk": evaluate_risk(train, test),
        "pipeline": evaluate_pipeline(Analyzer(Engine.load()), docs),
        "segmenter": {"recovered": found, "total": total},
    }
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "components.json").write_text(
        json.dumps(components, indent=2), encoding="utf-8"
    )
    baselines_path = args.reports_dir / "baselines_v1.json"
    baselines = (
        json.loads(baselines_path.read_text(encoding="utf-8")) if baselines_path.exists() else None
    )
    write_summary(args.reports_dir / "SUMMARY.md", components, baselines)
    print((args.reports_dir / "SUMMARY.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
