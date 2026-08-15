from __future__ import annotations

import argparse
import json

from pearl_models.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="pearl-models")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="run the full Phase 3 pipeline")
    run_parser.add_argument("--run-id", default=None)

    score_parser = sub.add_parser(
        "score",
        help=("reproduce the reported analysis on one subject's BIDS EEG. NOT a "
              "prediction: the model was not validated and does not detect its "
              "target -- output carries no demonstrated predictive meaning "
              "(see reports/phase7_delivery_decision.md)"))
    score_parser.add_argument("--subject", required=True)
    score_parser.add_argument("--bids-dir", required=True)
    score_parser.add_argument("--model-dir", default=None,
                               help="defaults to pearl_models.paths.MODELS_DIR")

    args = parser.parse_args()

    if args.command == "score":
        from pearl_models.inference import score_bids_subject
        from pearl_models.paths import MODELS_DIR

        model_dir = args.model_dir or str(MODELS_DIR)
        result = score_bids_subject(args.bids_dir, args.subject, model_dir)
        print(json.dumps(result, indent=2))
    elif args.command == "run":
        summary = run(run_id=args.run_id)
        print(summary)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
