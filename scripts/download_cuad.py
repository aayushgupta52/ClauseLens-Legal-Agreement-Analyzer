"""Download CUAD v1 (CC BY 4.0) from the official GitHub repo and extract CUADv1.json."""

from __future__ import annotations

import argparse
import hashlib
import logging
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from clauselens.paths import RAW

URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
SHA256 = "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a"
MEMBER = "CUADv1.json"

log = logging.getLogger("download_cuad")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=RAW / "cuad")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    target = args.out_dir / MEMBER
    if target.exists() and not args.force:
        log.info("%s already exists, skipping (use --force to re-download)", target)
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "cuad.zip"
        log.info("downloading %s", URL)
        digest = hashlib.sha256()
        with urllib.request.urlopen(URL, timeout=60) as resp, zip_path.open("wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)

        if digest.hexdigest() != SHA256:
            raise SystemExit(
                f"checksum mismatch: expected {SHA256}, got {digest.hexdigest()}. "
                "The upstream file changed; verify it before updating SHA256."
            )

        with zipfile.ZipFile(zip_path) as zf:
            target.write_bytes(zf.read(MEMBER))  # read one member; no extractall

    log.info("saved %s (CUAD is CC BY 4.0, cite Hendrycks et al. 2021)", target)


if __name__ == "__main__":
    main()
