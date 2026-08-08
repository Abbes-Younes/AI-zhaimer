"""Phase 1 CLI — ``python -m pearl_preproc.cli {budget|download|preprocess|qc|report|analysis-plan|run-all}``."""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import analysis_plan as analysis_plan_mod
from .config import load_preproc_config
from .paths import (
    PREPROC_DIR,
    ensure_dirs,
    finalize_run,
    load_audit_provenance,
    make_run_id,
    set_run_id,
    stamp_run_meta,
)

PIPELINE_VERSION = "1.0.0"


def _banner(msg: str) -> None:
    print(f"\n{'=' * 70}\n  {msg}\n{'=' * 70}")


def _step(name: str, func, *args, **kwargs):
    _banner(name)
    try:
        result = func(*args, **kwargs)
        print(f"  [OK] {name}")
        return result
    except Exception as exc:
        print(f"  [FAIL] {name} raised: {exc}")
        traceback.print_exc()
        raise


def write_dataset_description() -> None:
    prov = load_audit_provenance()
    doc = {
        "Name": "PEARL-Neuro preprocessed derivatives (rest + MSIT)",
        "BIDSVersion": "1.8.0",
        "GeneratedBy": [{
            "Name": "pearl_preproc",
            "Version": PIPELINE_VERSION,
            "Description": ("Label-blind preprocessing: montage, average "
                            "reference, bad-channel interpolation, 0.5 Hz "
                            "zero-phase FIR high-pass, anti-alias resample "
                            "(500 Hz rest / 250 Hz MSIT), 50 Hz line-noise "
                            "removal, ICA + ICLabel exclusion. See sidecars "
                            "for per-file provenance."),
        }],
        "SourceDatasets": [{
            "URL": "https://openneuro.org/datasets/ds004796",
            "Version": prov.get("version_string", "v1.0.0"),
            "SHA256": prov.get("participants_tsv_sha256"),
            "DOI": "10.18112/openneuro.ds004796.v1.0.0",
        }],
        "PipelineDescription": {"Name": "pearl_preproc",
                                "Version": PIPELINE_VERSION},
    }
    out = PREPROC_DIR / "dataset_description.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_budget(args: argparse.Namespace) -> int:
    from . import budget
    result = budget.run()
    print(f"  Derivatives total: {result['budget']['derivatives_total_gb']} GB "
          f"(gate {result['budget']['gate_gb']} GB)")
    print(f"  Raw total:         {result['budget']['raw_total_gb']} GB")
    print(f"  Peak raw on disk:  {result['budget']['peak_raw_on_disk_gb']} GB")
    print(f"  Report: {result['report_path']}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from . import download
    cfg = load_preproc_config()
    subjects = args.subjects
    totals = download.download_all(cfg, subjects=subjects, n_workers=args.workers)
    print(f"  Downloaded {totals['downloaded_files']} files, "
          f"{totals['bytes'] / 1024**3:.2f} GB "
          f"(skipped {totals['skipped_files']} already-present)")
    if totals["quarantined"]:
        print(f"  QUARANTINED: {totals['quarantined']}")
        return 1
    return 0


def cmd_preprocess(args: argparse.Namespace) -> int:
    from . import pipeline
    cfg = load_preproc_config()
    result = pipeline.preprocess_all(cfg, subjects=args.subjects)
    print(f"  Preprocessed {len(result['completed'])} subjects, "
          f"{len(result['failed'])} failed")
    for f in result["failed"]:
        print(f"    FAIL {f['subject']}: {f.get('reason')}")
    return 0 if not result["failed"] else 1


def cmd_backfill_iaf(args: argparse.Namespace) -> int:
    from . import preprocess
    ensure_dirs()
    run_id = make_run_id()
    set_run_id(run_id)
    try:
        cfg = load_preproc_config()
        result = preprocess.backfill_iaf(cfg, subjects=args.subjects)
    finally:
        set_run_id(None)
    print(f"  Rewrote IAF for {result['n_rewritten']} (subject, task) sidecars")
    n_gained = sum(1 for r in result["results"]
                  if not (r["iaf_before"] or {}).get("present") and r["iaf_after"]["present"])
    n_lost = sum(1 for r in result["results"]
                if (r["iaf_before"] or {}).get("present") and not r["iaf_after"]["present"])
    print(f"  alpha_present: +{n_gained} gained, -{n_lost} lost")
    return 0


def cmd_qc(args: argparse.Namespace) -> int:
    from . import qc
    cfg = load_preproc_config()
    summary = qc.run(cfg)
    print(f"  Rows: {summary['n_rows']} (pass {summary['n_pass']}, "
          f"warn {summary['n_warn']}, fail {summary['n_fail']})")
    print(f"  Excluded (frozen): {summary['n_excluded']}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from . import qc, report_qc
    cfg = load_preproc_config()
    qc_summary = qc.run(cfg)
    result = report_qc.generate(qc_summary, cfg)
    print(f"  Verdict: {result['verdict']}")
    print(f"  HTML: {result['html_path']}")
    return 0 if result["verdict"] == "PROCEED" else 1


def cmd_analysis_plan(args: argparse.Namespace) -> int:
    path = analysis_plan_mod.write_analysis_plan()
    print(f"  Frozen analysis plan: {path}")
    print("  REMINDER: commit it; do not change it after features exist.")
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    from . import budget, pipeline, qc, report_qc
    ensure_dirs()
    run_id = make_run_id()
    set_run_id(run_id)
    stamp_run_meta()
    print(f"PEARL-Neuro Phase 1 (run {run_id})")

    try:
        # DoD gate #1: measured budget BEFORE any bulk download.
        budget_result = _step("Budget gate (§0c)", budget.run)
        if budget_result["budget"]["derivatives_total_gb"] > budget_result["budget"]["gate_gb"]:
            _banner("STOP — measured derivative total exceeds 30 GB gate")
            print("  The duration model is wrong. Report and wait (phase_1.md §8).")
            return 1

        cfg = load_preproc_config()
        pipe = _step("Streaming download + preprocess (§0a/§1/§2)",
                     pipeline.run_all, cfg, subjects=args.subjects,
                     keep_raw=args.keep_raw, n_workers=args.workers)
        print(f"  Completed {pipe['n_completed']} subjects, skipped {pipe['n_skipped']}, "
              f"failed {pipe['n_failed']}")
        if pipe["failed"]:
            print("  FAILED (raw retained for re-processing):")
            for f in pipe["failed"]:
                print(f"    {f['subject']}: {f.get('reason')}")

        qc_summary = _step("QC metrics + frozen exclusions (§3)", qc.run, cfg)
        print(f"  Excluded (frozen): {qc_summary['n_excluded']}")

        report = _step("QC report (§3)", report_qc.generate, qc_summary, cfg)
        print(f"  QC verdict: {report['verdict']}")

        plan_path = _step("Frozen analysis plan (§5)",
                          analysis_plan_mod.write_analysis_plan)
        _step("BIDS-Derivatives dataset_description", write_dataset_description)

        finalize_run()

        _banner("Phase 1 Complete")
        print(f"  Budget report:     {budget_result['report_path']}")
        print(f"  QC HTML:           {report['html_path']}")
        print(f"  Analysis plan:     {plan_path}")
        print(f"  Excluded subjects: {qc_summary['excluded_csv']}")
        print(f"  Run ID:            {run_id}")
        return 0 if report["verdict"] == "PROCEED" else 1
    except Exception:
        from .paths import staging_dir
        staged = staging_dir()
        if staged.exists() and any(staged.iterdir()):
            print(f"\n  [NOTE] Bulk artifacts staged in {staged} were NOT swapped "
                  f"into place (run failed). Inspect or delete this directory.")
        raise
    finally:
        set_run_id(None)


def main() -> None:
    parser = argparse.ArgumentParser(prog="pearl-preproc",
                                     description="PEARL-Neuro Phase 1 pipeline")
    sub = parser.add_subparsers(dest="command")

    p_budget = sub.add_parser("budget", help="measured disk budget (DoD gate)")
    p_budget.set_defaults(func=cmd_budget)

    p_dl = sub.add_parser("download", help="download the approved manifest")
    p_dl.add_argument("--subjects", nargs="*", default=None)
    p_dl.add_argument("--workers", type=int, default=None)
    p_dl.set_defaults(func=cmd_download)

    p_pp = sub.add_parser("preprocess", help="preprocess downloaded raw (keeps raw)")
    p_pp.add_argument("--subjects", nargs="*", default=None)
    p_pp.set_defaults(func=cmd_preprocess)

    p_bf = sub.add_parser("backfill-iaf", help="re-derive IAF from existing derivatives (no re-download)")
    p_bf.add_argument("--subjects", nargs="*", default=None)
    p_bf.set_defaults(func=cmd_backfill_iaf)

    p_qc = sub.add_parser("qc", help="compute QC metrics + freeze exclusions")
    p_qc.set_defaults(func=cmd_qc)

    p_rep = sub.add_parser("report", help="generate the QC HTML report")
    p_rep.set_defaults(func=cmd_report)

    p_plan = sub.add_parser("analysis-plan", help="write the frozen Phase 2 plan")
    p_plan.set_defaults(func=cmd_analysis_plan)

    p_all = sub.add_parser("run-all", help="full streaming Phase 1 pipeline")
    p_all.add_argument("--subjects", nargs="*", default=None)
    p_all.add_argument("--keep-raw", action="store_true", default=False)
    p_all.add_argument("--workers", type=int, default=2)
    p_all.set_defaults(func=cmd_run_all)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
