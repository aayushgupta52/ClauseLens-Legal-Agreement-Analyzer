"""Gold-set tooling: build annotation sheets, validate, measure agreement, export.

Workflow: put anonymised agreements as .txt in data/gold/raw/, run `prepare`, let two people
fill clause_types / risk independently, check `agreement`, adjudicate into one CSV, `export`.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from sklearn.metrics import cohen_kappa_score

from clauselens.data.io import write_jsonl
from clauselens.data.taxonomy import OTHER_ID, Taxonomy
from clauselens.paths import DATA
from clauselens.segment import segment_document

FIELDS = ("doc_id", "idx", "kind", "text", "clause_types", "risk", "notes")
RISK_SCORE = {"green": 0, "amber": 1, "red": 2}


def prepare_rows(doc_id: str, text: str) -> list[dict[str, Any]]:
    return [
        {"doc_id": doc_id, "idx": s.index, "kind": s.kind, "text": s.text,
         "clause_types": "", "risk": "", "notes": ""}
        for s in segment_document(text)
    ]  # fmt: skip


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _types(row: dict[str, str]) -> list[str]:
    return [t.strip() for t in (row.get("clause_types") or "").split("|") if t.strip()]


def validate_rows(rows: list[dict[str, str]], valid_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for row in rows:
        where = f"{row.get('doc_id')}#{row.get('idx')}"
        types = _types(row)
        if not types:
            errors.append(f"{where}: clause_types is empty (use 'other' for non-clauses)")
            continue
        bad = [t for t in types if t not in valid_ids]
        if bad:
            errors.append(f"{where}: unknown clause type(s) {bad}")
        if OTHER_ID in types and len(types) > 1:
            errors.append(f"{where}: 'other' cannot be combined with other types")
        risk = (row.get("risk") or "").strip()
        if risk and risk not in RISK_SCORE:
            errors.append(f"{where}: risk must be green/amber/red, got {risk!r}")
        if types != [OTHER_ID] and not risk:
            errors.append(f"{where}: risk is required for clause rows")
    return errors


def agreement(
    rows_a: list[dict[str, str]], rows_b: list[dict[str, str]], labels: list[str]
) -> dict[str, Any]:
    """Cohen's kappa between two annotators (macro over labels, plus ordinal kappa for risk)."""
    by_key_b = {(r["doc_id"], r["idx"]): r for r in rows_b}
    pairs = [
        (a, by_key_b[(a["doc_id"], a["idx"])])
        for a in rows_a
        if (a["doc_id"], a["idx"]) in by_key_b
    ]
    per_label: dict[str, float] = {}
    for label in labels:
        ya = [int(label in _types(a)) for a, _ in pairs]
        yb = [int(label in _types(b)) for _, b in pairs]
        if len(set(ya) | set(yb)) > 1:
            per_label[label] = round(float(cohen_kappa_score(ya, yb)), 4)
    risk_pairs = [
        (RISK_SCORE[a["risk"]], RISK_SCORE[b["risk"]])
        for a, b in pairs
        if a.get("risk") in RISK_SCORE and b.get("risk") in RISK_SCORE
    ]
    risk_kappa = None
    if len({x for pair in risk_pairs for x in pair}) > 1:
        ra, rb = zip(*risk_pairs, strict=True)
        risk_kappa = round(float(cohen_kappa_score(ra, rb, weights="linear")), 4)
    macro = round(sum(per_label.values()) / len(per_label), 4) if per_label else None
    return {
        "n_rows_compared": len(pairs),
        "clause_type_kappa_macro": macro,
        "per_label_kappa": per_label,
        "risk_kappa_linear": risk_kappa,
    }


def to_records(rows: list[dict[str, str]], valid_ids: set[str]) -> list[dict[str, Any]]:
    errors = validate_rows(rows, valid_ids)
    if errors:
        raise ValueError("invalid annotations:\n" + "\n".join(errors[:20]))
    return [
        {
            "id": f"g_{r['doc_id']}_{r['idx']}",
            "text": r["text"],
            "labels": sorted(_types(r)),
            "sources": ["gold"],
            "source_labels": [f"gold:{t}" for t in sorted(_types(r))],
            "doc_id": r["doc_id"],
            "split": "test",
            "risk": (r.get("risk") or "").strip() or None,
        }
        for r in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare", help="segment .txt agreements into an annotation CSV")
    prep.add_argument("--input-dir", type=Path, default=DATA / "gold" / "raw")
    prep.add_argument("--out", type=Path, default=DATA / "gold" / "annotation_template.csv")
    val = sub.add_parser("validate", help="check an annotated CSV")
    val.add_argument("csv", type=Path)
    agr = sub.add_parser("agreement", help="Cohen's kappa between two annotators")
    agr.add_argument("--a", type=Path, required=True)
    agr.add_argument("--b", type=Path, required=True)
    exp = sub.add_parser("export", help="adjudicated CSV -> gold_v1.jsonl")
    exp.add_argument("--csv", type=Path, required=True)
    exp.add_argument("--out", type=Path, default=DATA / "gold" / "gold_v1.jsonl")
    args = parser.parse_args()

    labels = Taxonomy.load().with_other(["out_of_domain"]).clause_ids
    if args.cmd == "prepare":
        rows: list[dict[str, Any]] = []
        for path in sorted(args.input_dir.glob("*.txt")):
            rows += prepare_rows(path.stem, path.read_text(encoding="utf-8"))
        write_csv(args.out, rows)
        print(
            f"{len(rows)} rows from {len(list(args.input_dir.glob('*.txt')))} files -> {args.out}"
        )
    elif args.cmd == "validate":
        errors = validate_rows(read_csv(args.csv), set(labels))
        print("\n".join(errors) if errors else "OK")
    elif args.cmd == "agreement":
        print(agreement(read_csv(args.a), read_csv(args.b), labels))
    else:
        n = write_jsonl(args.out, to_records(read_csv(args.csv), set(labels)))
        print(f"{n} gold records -> {args.out}")


if __name__ == "__main__":
    main()
