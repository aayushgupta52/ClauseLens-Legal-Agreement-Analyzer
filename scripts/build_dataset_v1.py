"""Build processed dataset v1 from the raw CUAD (+ optional LEDGAR) downloads."""

from __future__ import annotations

import argparse
import json
import logging
import platform
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path

from clauselens import __version__
from clauselens.data.build import build_dataset
from clauselens.data.io import sha256_file, write_jsonl
from clauselens.data.sources import (
    CUAD_CATEGORIES,
    LEDGAR_LABELS,
    load_cuad,
    parse_cuad,
    read_ledgar,
)
from clauselens.data.taxonomy import Taxonomy
from clauselens.paths import INTERIM, PROCESSED, RAW


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cuad", type=Path, default=RAW / "cuad" / "CUADv1.json")
    p.add_argument("--ledgar-dir", type=Path, default=RAW / "ledgar")
    p.add_argument("--skip-ledgar", action="store_true", help="build from CUAD only")
    p.add_argument("--out-dir", type=Path, default=PROCESSED / "v1")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-words", type=int, default=5)
    p.add_argument("--near-dup-threshold", type=float, default=0.85)
    p.add_argument(
        "--other-groups",
        nargs="*",
        default=["out_of_domain"],
        help='excluded label groups to keep as the "other" class (empty = drop them)',
    )
    p.add_argument(
        "--max-other-ratio",
        type=float,
        default=1.0,
        help='per split, cap "other" at this multiple of the positive examples',
    )
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    taxonomy = Taxonomy.load()
    taxonomy.validate_against("cuad", CUAD_CATEGORIES, require_full_coverage=True)
    taxonomy.validate_against("ledgar", LEDGAR_LABELS)
    if args.other_groups:
        taxonomy = taxonomy.with_other(args.other_groups)

    cuad_examples, contracts = parse_cuad(load_cuad(args.cuad))
    inputs = {"cuad": str(args.cuad)}
    sources = [cuad_examples]
    if not args.skip_ledgar:
        sources.append(list(read_ledgar(args.ledgar_dir)))
        inputs["ledgar"] = str(args.ledgar_dir)

    records, stats = build_dataset(
        chain.from_iterable(sources),
        taxonomy,
        [c["doc_id"] for c in contracts],
        seed=args.seed,
        min_words=args.min_words,
        near_dup_threshold=args.near_dup_threshold,
        max_other_ratio=args.max_other_ratio if args.other_groups else None,
    )

    for split in ("train", "val", "test"):
        write_jsonl(args.out_dir / f"{split}.jsonl", (r for r in records if r.split == split))
    write_jsonl(INTERIM / "cuad_contracts.jsonl", contracts)  # for Phase 3 negative mining

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "clauselens_version": __version__,
        "python": platform.python_version(),
        "taxonomy_version": taxonomy.version,
        "params": {
            "seed": args.seed,
            "min_words": args.min_words,
            "near_dup_threshold": args.near_dup_threshold,
            "skip_ledgar": args.skip_ledgar,
            "other_groups": args.other_groups,
            "max_other_ratio": args.max_other_ratio,
        },
        "inputs": inputs,
        "cuad_sha256": sha256_file(args.cuad),
    }
    (args.out_dir / "stats.json").write_text(
        json.dumps({"manifest": manifest, **stats}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _print_summary(stats)


def _print_summary(stats: dict) -> None:
    print(f"\nrecords: {stats['n_records']}  splits: {stats['per_split']}")
    print(f"dropped: {stats['dropped']}")
    print(f"near-duplicates removed from train: {stats['n_near_duplicates_removed_from_train']}")
    print(f"\n{'label':30} {'train':>7} {'val':>6} {'test':>6}")
    for label, c in stats["per_label"].items():
        if c.get("total"):
            print(f"{label:30} {c.get('train', 0):>7} {c.get('val', 0):>6} {c.get('test', 0):>6}")
    print(f"\nlabels with no examples in this build: {stats['labels_without_data']}")


if __name__ == "__main__":
    main()
