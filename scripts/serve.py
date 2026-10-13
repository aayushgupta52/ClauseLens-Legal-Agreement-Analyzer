"""Start the ClauseLens API + web UI (http://127.0.0.1:8000 by default)."""

from __future__ import annotations

import argparse

import uvicorn

from clauselens.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"ClauseLens -> http://{args.host}:{args.port}  (first start trains the models, ~30 s)")
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
