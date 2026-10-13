"""Side-by-side table of the TF-IDF baselines and every fine-tuned transformer report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from clauselens.paths import ROOT

SETS = ("real_val", "real_test", "synth_val", "synth_test", "gold")


def collect(reports_dir: Path) -> dict[str, dict[str, dict]]:
    rows: dict[str, dict[str, dict]] = {}
    baselines = reports_dir / "baselines_v1.json"
    if baselines.exists():
        rows.update(json.loads(baselines.read_text(encoding="utf-8"))["models"])
    for path in sorted(reports_dir.glob("transformer_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows[data["config"]["model_name"]] = data["final"]
    return rows


def to_markdown(rows: dict[str, dict[str, dict]]) -> str:
    sets = [s for s in SETS if any(s in per_set for per_set in rows.values())]
    lines = [
        "| model | " + " | ".join(f"{s} micro / macro F1" for s in sets) + " |",
        "|---|" + "---|" * len(sets),
    ]
    for name, per_set in rows.items():
        cells = [
            f"{per_set[s]['micro_f1']:.3f} / {per_set[s]['macro_f1']:.3f}" if s in per_set else "-"
            for s in sets
        ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    rows = collect(args.reports_dir)
    if not rows:
        raise SystemExit("no reports found; run train_baselines.py / train_transformer.py")
    table = to_markdown(rows)
    (args.reports_dir / "comparison.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
