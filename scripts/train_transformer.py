"""Fine-tune a transformer clause classifier and compare it with the TF-IDF baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from clauselens.baselines import load_records
from clauselens.data.taxonomy import Taxonomy
from clauselens.finetune import TrainConfig, train
from clauselens.paths import DATA, PROCESSED, ROOT

SETS = ("real_val", "real_test", "synth_val", "synth_test", "gold")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-name", default=TrainConfig.model_name, help="HF id or local dir")
    p.add_argument("--real-dir", type=Path, default=PROCESSED / "v1")
    p.add_argument("--synth-dir", type=Path, default=PROCESSED / "synth_v1")
    p.add_argument("--gold", type=Path, default=DATA / "gold" / "gold_v1.jsonl")
    p.add_argument("--train-on", choices=("both", "real", "synth"), default="both")
    p.add_argument("--epochs", type=int, default=TrainConfig.epochs)
    p.add_argument("--batch-size", type=int, default=TrainConfig.batch_size)
    p.add_argument("--lr", type=float, default=TrainConfig.lr)
    p.add_argument("--max-len", type=int, default=TrainConfig.max_len)
    p.add_argument("--seed", type=int, default=TrainConfig.seed)
    p.add_argument("--select-on", default=TrainConfig.select_on)
    p.add_argument("--max-train-examples", type=int, default=None, help="smoke runs")
    p.add_argument("--no-fp16", action="store_true")
    p.add_argument("--models-dir", type=Path, default=ROOT / "models")
    p.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    args = p.parse_args()

    labels = Taxonomy.load().with_other(["out_of_domain"]).clause_ids
    real = {s: load_records(args.real_dir / f"{s}.jsonl") for s in ("train", "val", "test")}
    synth = {s: load_records(args.synth_dir / f"{s}.jsonl") for s in ("train", "val", "test")}
    train_records = (real["train"] if args.train_on != "synth" else []) + (
        synth["train"] if args.train_on != "real" else []
    )
    if not train_records:
        raise SystemExit("no training data; run build_dataset_v1.py / generate_synthetic.py first")
    eval_sets = {
        "real_val": real["val"],
        "real_test": real["test"],
        "synth_val": synth["val"],
        "synth_test": synth["test"],
        "gold": load_records(args.gold),
    }
    eval_sets = {k: v for k, v in eval_sets.items() if v}

    cfg = TrainConfig(
        model_name=args.model_name, max_len=args.max_len, epochs=args.epochs,
        batch_size=args.batch_size, lr=args.lr, seed=args.seed, select_on=args.select_on,
        fp16=not args.no_fp16, max_train_examples=args.max_train_examples,
    )  # fmt: skip
    slug = Path(args.model_name).name if Path(args.model_name).exists() else args.model_name
    slug = slug.replace("/", "__")
    report = train(train_records, eval_sets, labels, cfg, args.models_dir / slug)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.reports_dir / f"transformer_{slug}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{args.model_name}: best epoch {report['best_epoch']} (selected on "
          f"{report['selected_on']}), {report['seconds']}s on {report['device']}")  # fmt: skip
    print(f"truncated train texts: {report['truncated_train_fraction']:.1%}  "
          f"never-seen labels: {report['inactive_labels']}")  # fmt: skip
    for name in SETS:
        if name in report["final"]:
            r = report["final"][name]
            print(f"  {name:11} micro={r['micro_f1']:.3f} macro={r['macro_f1']:.3f} n={r['n']}")
    for name in ("synth_test", "gold"):
        if name in report["final"]:
            print(f"\nper-label F1 on {name}:")
            for lab, m in report["final"][name]["per_label"].items():
                print(f"  {lab:28} f1={m['f1']:.2f} p={m['precision']:.2f} r={m['recall']:.2f} "
                      f"n={m['support']}")  # fmt: skip
    print(f"\nmodel -> {args.models_dir / slug}\nreport -> {report_path}")


if __name__ == "__main__":
    main()
