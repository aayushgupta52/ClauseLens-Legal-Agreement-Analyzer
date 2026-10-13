"""Generate synthetic clause samples and full documents (Phase 2)."""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

from clauselens.data.io import write_jsonl
from clauselens.paths import INTERIM, PROCESSED
from clauselens.segment import clause_recovery, segment_document
from clauselens.synth.generator import generate_documents, generate_samples


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=PROCESSED / "synth_v1")
    p.add_argument("--docs-out", type=Path, default=INTERIM / "synth_docs.jsonl")
    p.add_argument("--n-train", type=int, default=60, help="target samples per (clause, risk)")
    p.add_argument("--n-val", type=int, default=10)
    p.add_argument("--n-test", type=int, default=15)
    p.add_argument("--n-docs", type=int, default=60)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    records, stats = generate_samples(
        n_train=args.n_train, n_val=args.n_val, n_test=args.n_test, seed=args.seed
    )
    for split in ("train", "val", "test"):
        write_jsonl(args.out_dir / f"{split}.jsonl", (r for r in records if r.split == split))

    docs = generate_documents(args.n_docs, args.seed)
    write_jsonl(args.docs_out, docs)

    # Regression check of the Phase 3 segmenter on documents with known clause boundaries.
    # Circular by construction (we wrote both sides), so it guards against regressions only.
    recovery: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for doc in docs:
        found, total = clause_recovery(
            [i["text"] for i in doc["items"] if i["kind"] == "clause"],
            segment_document(doc["text"]),
        )
        recovery[doc["style"]["numbering"]][0] += found
        recovery[doc["style"]["numbering"]][1] += total
    stats["segmenter_recovery_by_numbering"] = dict(recovery)
    (args.out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"records: {stats['n_records']}  splits: {stats['per_split']}")
    print(f"near-duplicates removed: {stats['near_dup_removed']}  risk mix: {stats['per_risk']}")
    print(f"documents: {len(docs)} -> {args.docs_out}")
    print(f"segmenter clause recovery: {dict(recovery)}")


if __name__ == "__main__":
    main()
