"""One command: download data, build datasets, train, evaluate and test the whole project.

python scripts/run_all.py              # everything
python scripts/run_all.py --skip-ledgar  # CUAD + synthetic only (no Hugging Face needed)
python scripts/run_all.py --skip-tests
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(name: str, *args: str, required: bool = True) -> bool:
    print(f"\n{'=' * 70}\n>> {name}\n{'=' * 70}", flush=True)
    started = time.time()
    code = subprocess.call([sys.executable, *args], cwd=SCRIPTS.parent)
    status = "ok" if code == 0 else f"FAILED (exit {code})"
    print(f"<< {name}: {status} in {time.time() - started:.0f}s", flush=True)
    if code != 0 and required:
        raise SystemExit(f"step '{name}' failed; fix it and re-run (finished steps are cached)")
    return code == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-ledgar", action="store_true", help="do not download LEDGAR")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    run("download CUAD", str(SCRIPTS / "download_cuad.py"))
    use_ledgar = not args.skip_ledgar
    if use_ledgar:
        use_ledgar = run("download LEDGAR (needs internet + `pip install -e .[data]`)",
                         str(SCRIPTS / "download_ledgar.py"), required=False)  # fmt: skip
        if not use_ledgar:
            print("!! LEDGAR unavailable: continuing with CUAD + synthetic data only", flush=True)
    build = [str(SCRIPTS / "build_dataset_v1.py")] + ([] if use_ledgar else ["--skip-ledgar"])
    run("build dataset v1", *build)
    run("generate synthetic data + documents", str(SCRIPTS / "generate_synthetic.py"))
    run("train TF-IDF baselines (saves models/)", str(SCRIPTS / "train_baselines.py"))
    run("evaluate components (writes reports/SUMMARY.md)", str(SCRIPTS / "evaluate_components.py"))
    if not args.skip_tests:
        run("pytest", "-m", "pytest", "-q")
    print(
        "\nAll done. Start the app with:  python scripts/serve.py   then open http://127.0.0.1:8000"
    )


if __name__ == "__main__":
    main()
