"""CLI entry point for Phase 0/0.5 audit — ``python -m pearl_audit.cli run-all``."""
from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .paths import (
    ensure_scaffold,
    require_free_space,
    PROJECT_ROOT,
    get_cumulative_bytes,
    MAX_DOWNLOAD_BYTES,
    set_run_id,
    finalize_run,
    stamp_run_meta,
)


def _make_run_id() -> str:
    """UTC timestamp + short git SHA (phase_0,5.md Task 4)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        sha = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT.parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        sha = "nogit"
    return f"{ts}-{sha or 'nogit'}"


def _banner(msg: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {msg}")
    print(f"{'=' * 70}")


def _step(name: str, func, *args, **kwargs):
    """Run a step, printing status and catching errors."""
    _banner(name)
    try:
        result = func(*args, **kwargs)
        print(f"  [OK] {name} completed.")
        return result
    except Exception as exc:
        print(f"  [FAIL] {name} raised: {exc}")
        traceback.print_exc()
        raise


def cmd_run_all(args: argparse.Namespace) -> int:
    """Execute the full Phase 0/0.5 pipeline."""
    print("PEARL-Neuro Phase 0.5 Audit")
    print(f"Project root: {PROJECT_ROOT}")

    # 0. Scaffold + run identity (phase_0,5.md Task 4)
    ensure_scaffold()
    run_id = _make_run_id()
    set_run_id(run_id)
    stamp_run_meta()
    print(f"Run ID: {run_id}")

    try:
        rc = _run_all_steps(run_id)
        return rc
    except SystemExit:
        raise
    except Exception:
        # Task 4: staged artifacts are kept in the tmp dir for inspection.
        from .paths import artifact_dir
        staged = artifact_dir()
        if staged.exists() and staged != staged.parent / "phase0" and any(staged.iterdir()):
            print(f"\n  [NOTE] Artifacts staged in {staged} were NOT swapped into place "
                  f"(run failed). Inspect or delete this directory.")
        raise
    finally:
        set_run_id(None)


def _run_all_steps(run_id: str) -> int:
    """Run every audit step; artifacts are staged and swapped atomically."""
    # 0.1 Environment verification
    _banner("Environment verification")
    free_gb = require_free_space()
    print(f"  Free space on {PROJECT_ROOT.drive}: {free_gb:.1f} GB")

    import tempfile
    print(f"  sys.prefix:      {sys.prefix}")
    print(f"  tempfile dir:    {tempfile.gettempdir()}")

    if not str(sys.prefix).startswith(str(PROJECT_ROOT)):
        print("  WARNING: sys.prefix does not resolve under project root.")
    if not tempfile.gettempdir().startswith(str(PROJECT_ROOT)):
        print("  WARNING: tempfile.gettempdir() does not resolve under project root.")

    # 1. Fetch metadata (§3)
    from . import fetch_metadata
    fetch_summary = _step("§3 Fetch metadata", fetch_metadata.run)
    print(f"  Fetched {len(fetch_summary.get('files', {}))} files.")
    if "genotype_info" in fetch_summary:
        gi = fetch_summary["genotype_info"]
        print(f"  APOE unique values:   {gi.get('apoe_unique_values', [])}")
        print(f"  PICALM unique values: {gi.get('picalm_unique_values', [])}")

    # Stop-gate: check genotype columns were identified
    gi = fetch_summary.get("genotype_info", {})
    col_map = gi.get("columns", {})
    if not col_map.get("apoe") or not col_map.get("picalm"):
        _banner("STOP — Cannot identify APOE/PICALM columns")
        print("  The genotype columns in participants.tsv could not be identified.")
        print("  Full schema written to reports/participants_schema.txt")
        print("  Aborting. Fix config/audit.yaml and re-run.")
        return 1

    # 2. Size survey (§4)
    from . import size_survey
    size_summary = _step("§4 Size survey", size_survey.run)
    print(f"  Total dataset: {size_summary['total_bytes']:,} bytes")
    print(f"  EEG total:     {size_summary['eeg_total_gb']} GB")
    print(f"  Observed tasks: {size_summary['observed_tasks']}")

    # 3. Group reconciliation (§5)
    from . import reconcile_groups
    recon_summary = _step("§5 Group reconciliation", reconcile_groups.run)
    print(f"  Blocking statuses: {recon_summary['mismatch_count']}")
    print(f"  Analysis cohort: {recon_summary['analysis_cohort_count']} subjects")
    print(f"  sub-69: {recon_summary['sub_69']}")
    print(f"  e4/e4 homozygotes: {recon_summary['e4_homozygotes_in_A_P_plus']}")

    # Stop-gate: too many blocking statuses (Task 2)
    from .paths import load_audit_yaml
    audit_cfg = load_audit_yaml()
    max_mismatches = audit_cfg.get("thresholds", {}).get("max_mismatches", 2)
    if recon_summary["mismatch_count"] > max_mismatches:
        _banner("STOP — Too many blocking reconciliation statuses")
        print(f"  {recon_summary['mismatch_count']} blocking statuses exceed threshold of {max_mismatches}.")
        print("  The client's grouping rule differs from the stated definition.")
        print("  Every label in the project is suspect. Aborting.")
        return 1

    # 4. EEG inventory (§6)
    from . import inventory
    inv_summary = _step("§6 EEG inventory", inventory.run)
    print(f"  Tasks found: {inv_summary['tasks_found']}")

    # 5. Confound analysis (§7 + Task 8)
    from . import confounds
    conf_summary = _step("§7 Confound analysis", confounds.run)
    print(f"  Subjects analysed: {conf_summary['n_subjects_analysed']}")

    # 6. Phase 1 download plan (phase_0,5.md Task 6) — no downloads
    from . import download_plan
    plan_summary = _step("§ Task 6 Phase 1 download plan", download_plan.run)
    print(f"  Recommendation: {plan_summary['recommendation']}")
    print(f"  Manifest: {plan_summary['manifest_path']}")

    # 7. Report (§8 + Task 7)
    from . import report
    fetch_log_summary = {"total_bytes": get_cumulative_bytes(), "total_files": len(fetch_summary.get("files", {}))}
    report_summary = _step(
        "§8 Generate report",
        report.generate,
        recon_summary, inv_summary, conf_summary, size_summary, fetch_log_summary,
        plan_summary,
    )
    print(f"  HTML: {report_summary['html_path']}")
    print(f"  MD:   {report_summary['md_path']}")
    print(f"  Verdict: {report_summary['verdict']}")

    # Task 4: swap staged artifacts into place only after every step succeeded
    finalize_run()

    # Final summary
    _banner("Phase 0.5 Complete")
    cumulative = get_cumulative_bytes()
    print(f"  Total downloaded:  {cumulative:,} bytes ({cumulative / 1024**2:.1f} MB)")
    print(f"  Budget:            {MAX_DOWNLOAD_BYTES:,} bytes ({MAX_DOWNLOAD_BYTES / 1024**2:.1f} MB)")
    print(f"  Verdict:           {report_summary['verdict'].upper()}")
    print(f"  Reports:           {report_summary['html_path']}")
    print(f"                     {report_summary['md_path']}")

    if cumulative > MAX_DOWNLOAD_BYTES:
        print("\n  WARNING: Byte budget exceeded!")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="pearl-audit",
        description="PEARL-Neuro Phase 0 Audit Toolkit",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run-all", help="Execute the full Phase 0 pipeline")
    p_run.set_defaults(func=cmd_run_all)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    rc = args.func(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
