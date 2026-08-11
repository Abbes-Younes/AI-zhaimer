"""phase_5.md §0c, Task 3: regenerate phase1_manifest.csv for the
rest+msit+sternberg scope (A_full_eeg) and write the measured Sternberg-
inclusive budget to reports/phase5_budget_actual.md.

Scope A was rejected in Phase 0.5 under a co-resident-storage disk model
(75.87 GB raw + ~67 GB derivatives > 95 GB budget). pearl_preproc.budget's
own §0d note (written during Phase 1) already established that under the
proven streaming download->process->delete design, peak raw on disk is
~1.2 GB regardless of scope -- so Scope A is affordable and this script
selects it directly rather than deferring to download_plan.recommend_scope
(which still prefers the smallest scope that fits the old co-resident
model and would keep re-selecting C).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from pearl_audit.download_plan import build_scopes, write_manifest
from pearl_audit.paths import artifact_dir
from pearl_preproc.budget import compute_budget, N_CHANNELS_NATIVE, BYTES_PER_SAMPLE, NATIVE_SFREQ_HZ
from pearl_preproc.config import load_preproc_config
from pearl_preproc.paths import REPORTS_DIR, ensure_dirs


def write_phase5_budget_report(budget: dict) -> Path:
    ensure_dirs()
    lines = [
        "# Phase 5 Stage 1 Budget — Measured, rest+msit+sternberg (ds004796)",
        "",
        "Sternberg ingestion (phase_5.md §0c) adds a third task to the manifest "
        "used by Phase 1. Gate: continuous-derivative total "
        f"**≤ {budget['gate_gb']} GB** (same gate as phase_1.md §0c). "
        f"Measured total: **{budget['derivatives_total_gb']} GB** → "
        f"{'PASS' if budget['derivatives_total_gb'] <= budget['gate_gb'] else 'EXCEEDED — STOP'}.",
        "",
        "## Measured per-task figures",
        "",
        "| Task | Subjects | Mean duration (s) | Min–max (s) | Raw GB (measured) | Continuous @ target (GB) |",
        "|---|---|---|---|---|---|",
    ]
    for task in sorted(budget["per_task"]):
        t = budget["per_task"][task]
        lines.append(
            f"| {task} | {t['n']} | {t['mean_duration_s']} | "
            f"{t['min_duration_s']}–{t['max_duration_s']} | {t['raw_gb']} | "
            f"{budget['derivatives_per_task_gb'][task]} |")
    lines += [
        "",
        f"Raw total (manifest, all 3 tasks): **{budget['raw_total_gb']} GB**.",
        f"Derivative total: **{budget['derivatives_total_gb']} GB** "
        "(one float32 continuous file per subject per task at the target rate; "
        "ICA solutions are kilobytes, not counted as data).",
        "",
        "## Why Scope A is now selected (reverses Phase 0.5's rejection)",
        "",
        "Phase 0.5 rejected Scope A because its co-resident-storage model put "
        "raw (75.87 GB) + derivatives (~67 GB, since corrected — that model "
        "double-counted epoched/ICA copies) over the 95 GB budget. Phase 1's "
        "streaming download→process→verify→delete design (proven in "
        "production, phase_1.md §0d) means raw and derivatives never "
        "co-reside: peak raw on disk is bounded by a one-subject lookahead, "
        "**not** the full-scope raw total. That note was written but not acted "
        "on during Phase 1 (rest+msit only, to prove the pipeline first); "
        "Stage 1 of Phase 5 acts on it now.",
        "",
        "## Streaming consequence (unchanged from Phase 1)",
        "",
        "Raw and derivatives never coexist: each subject is downloaded, "
        f"preprocessed, verified, and its raw deleted. Peak raw on disk with a "
        f"one-subject lookahead: **{budget['peak_raw_on_disk_gb']} GB** — not "
        f"the {budget['raw_total_gb']} GB full-download figure. Raw is "
        "therefore never the binding constraint, for any of the 3 tasks.",
        "",
        "## Method",
        "",
        f"duration_s = .eeg bytes / ({N_CHANNELS_NATIVE} ch × {BYTES_PER_SAMPLE} B "
        f"float32 × {NATIVE_SFREQ_HZ:.0f} Hz native) — per subject per task "
        "from the measured size survey (data/derivatives/phase0/size_survey.csv, "
        "which already contains sternberg rows from Phase 0's original full-"
        "dataset listing). Continuous bytes = 127 × duration × target rate "
        "× 4 B, target rates from config/preproc.yaml (rest 500 Hz, msit/"
        "sternberg 250 Hz).",
        "",
    ]
    out = REPORTS_DIR / "phase5_budget_actual.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    size_path = artifact_dir() / "size_survey.csv"
    size_df = pd.read_csv(size_path)
    scopes = build_scopes(size_df)
    assert scopes["A_full_eeg"]["tasks"] == ["msit", "rest", "sternberg"], scopes["A_full_eeg"]["tasks"]

    manifest_path = write_manifest("A_full_eeg", size_df, scopes["A_full_eeg"])
    print(f"wrote {manifest_path} ({scopes['A_full_eeg']['n_files']} files, "
          f"{scopes['A_full_eeg']['raw_gb']} GB raw)")

    cfg = load_preproc_config()
    budget = compute_budget(cfg)
    report_path = write_phase5_budget_report(budget)
    print(f"wrote {report_path}")
    print(f"derivatives_total_gb={budget['derivatives_total_gb']} "
          f"(gate={budget['gate_gb']}), peak_raw_on_disk_gb={budget['peak_raw_on_disk_gb']}")
