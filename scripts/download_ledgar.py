"""Download LEDGAR (via LexGLUE on Hugging Face) and export it as JSONL with label names."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from clauselens.data.sources import export_ledgar
from clauselens.paths import RAW

log = logging.getLogger("download_ledgar")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=RAW / "ledgar")
    parser.add_argument("--force", action="store_true", help="re-export even if present")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if (args.out_dir / "train.jsonl").exists() and not args.force:
        log.info("%s already populated, skipping (use --force)", args.out_dir)
        return

    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit(
            "LEDGAR needs the 'datasets' package: pip install -e \".[data]\""
        ) from None

    log.info("loading coastalcph/lex_glue (ledgar) from Hugging Face")
    ds = load_dataset("coastalcph/lex_glue", "ledgar")
    counts = export_ledgar(ds, args.out_dir)
    log.info("exported %s to %s", counts, args.out_dir)


if __name__ == "__main__":
    main()
