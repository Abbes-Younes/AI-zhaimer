from __future__ import annotations

import argparse

from pearl_models.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="pearl-models")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    summary = run(run_id=args.run_id)
    print(summary)


if __name__ == "__main__":
    main()
