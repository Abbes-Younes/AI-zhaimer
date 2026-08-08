"""Measured Phase 1 disk budget (phase_1.md §0c) — a DoD gate.

Writes ``reports/phase1_budget_actual.md`` from *measured* per-subject
durations (backed out of the size-survey .eeg byte sizes) BEFORE any bulk
download. If the measured continuous-derivative total exceeds 30 GB the
duration model is wrong — stop and report (phase_1.md §8).
"""
from __future__ import annotations

import csv
from pathlib import Path

from .config import target_sfreq, load_preproc_config
from .paths import (
    N_CHANNELS_NATIVE,
    NATIVE_SFREQ_HZ,
    BYTES_PER_SAMPLE,
    REPORTS_DIR,
    SIZE_SURVEY_CSV,
    MANIFEST_CSV,
    ensure_dirs,
)


class BudgetExceededError(Exception):
    """Measured derivative footprint exceeds the 30 GB gate."""

DERIVATIVE_GATE_GB = 30.0
GB = 1024 ** 3


def _read_size_survey() -> list[dict]:
    if not SIZE_SURVEY_CSV.exists():
        raise FileNotFoundError(f"{SIZE_SURVEY_CSV} missing — run Phase 0.5 first")
    with open(SIZE_SURVEY_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_manifest() -> list[dict]:
    if not MANIFEST_CSV.exists():
        raise FileNotFoundError(f"{MANIFEST_CSV} missing — run Phase 0.5 first")
    with open(MANIFEST_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def measured_durations(rows: list[dict]) -> dict[tuple[str, str], float]:
    """duration_s per (subject, task) from measured .eeg byte sizes."""
    out: dict[tuple[str, str], float] = {}
    for row in rows:
        if row.get("modality") != "eeg" or not (row.get("path") or "").endswith(".eeg"):
            continue
        subj, task = row.get("subject"), row.get("task")
        nbytes = int(row["bytes"])
        n_samples = nbytes / (N_CHANNELS_NATIVE * BYTES_PER_SAMPLE)
        out[(subj, task)] = n_samples / NATIVE_SFREQ_HZ
    return out


def compute_budget(cfg: dict, quiet: bool = True) -> dict:
    rows = _read_size_survey()
    manifest = _read_manifest()
    durations = measured_durations(rows)

    # Scope the budget to the approved manifest (rest + msit): the size survey
    # also lists sternberg, which is deliberately not part of Phase 1 (§0d).
    scope_tasks = {r["task"] for r in manifest}
    durations = {k: v for k, v in durations.items() if k[1] in scope_tasks}

    # Per-task aggregates
    per_task: dict[str, dict] = {}
    for (subj, task), dur in durations.items():
        t = per_task.setdefault(task, {"n": 0, "durations": [], "raw_bytes": 0.0})
        t["n"] += 1
        t["durations"].append(dur)
        t["raw_bytes"] += dur * N_CHANNELS_NATIVE * NATIVE_SFREQ_HZ * BYTES_PER_SAMPLE

    # Raw bytes straight from the manifest (the Phase 1 contract)
    raw_total = sum(int(r["bytes"]) for r in manifest)
    raw_per_task: dict[str, int] = {}
    for r in manifest:
        raw_per_task[r["task"]] = raw_per_task.get(r["task"], 0) + int(r["bytes"])

    deriv_per_task: dict[str, float] = {}
    for task, t in per_task.items():
        sfreq = target_sfreq(cfg, task)
        deriv_per_task[task] = (
            sum(d * N_CHANNELS_NATIVE * sfreq * BYTES_PER_SAMPLE for d in t["durations"])
            / GB
        )
    deriv_total_gb = sum(deriv_per_task.values())

    # Peak raw on disk: worst single subject + one lookahead subject (§0a)
    subj_raw: dict[str, float] = {}
    for (subj, task), dur in durations.items():
        subj_raw[subj] = subj_raw.get(subj, 0.0) + (
            dur * N_CHANNELS_NATIVE * NATIVE_SFREQ_HZ * BYTES_PER_SAMPLE)
    top2 = sorted(subj_raw.values(), reverse=True)[:2] if subj_raw else [0.0]
    peak_raw_gb = (top2[0] + (top2[1] if len(top2) > 1 else 0.0)) / GB

    return {
        "n_subjects": len(subj_raw),
        "n_records": len(durations),
        "raw_total_gb": round(raw_total / GB, 2),
        "raw_per_task_gb": {k: round(v / GB, 2) for k, v in raw_per_task.items()},
        "per_task": {
            task: {
                "n": t["n"],
                "mean_duration_s": round(sum(t["durations"]) / t["n"], 1),
                "min_duration_s": round(min(t["durations"]), 1),
                "max_duration_s": round(max(t["durations"]), 1),
                "raw_gb": round(t["raw_bytes"] / GB, 2),
            }
            for task, t in per_task.items()
        },
        "derivatives_per_task_gb": {k: round(v, 2) for k, v in deriv_per_task.items()},
        "derivatives_total_gb": round(deriv_total_gb, 2),
        "peak_raw_on_disk_gb": round(peak_raw_gb, 2),
        "gate_gb": DERIVATIVE_GATE_GB,
    }


def write_budget_report(cfg: dict, budget: dict) -> Path:
    ensure_dirs()
    lines = [
        "# Phase 1 Budget — Measured (ds004796)",
        "",
        f"Gate: continuous-derivative total **≤ {budget['gate_gb']} GB** "
        f"(phase_1.md §0c). Measured total: "
        f"**{budget['derivatives_total_gb']} GB** "
        f"→ {'PASS' if budget['derivatives_total_gb'] <= budget['gate_gb'] else 'EXCEEDED — STOP'}.",
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
        f"Raw total (manifest): **{budget['raw_total_gb']} GB**.",
        f"Derivative total: **{budget['derivatives_total_gb']} GB** "
        f"(one float32 continuous file per subject per task at the target rate; "
        f"ICA solutions are kilobytes — not counted as data, phase_1.md §0b).",
        "",
        "## §0a Streaming consequence",
        "",
        "Raw and derivatives never coexist: each subject is downloaded, "
        f"preprocessed, verified, and its raw deleted. Peak raw on disk with a "
        f"one-subject lookahead: **{budget['peak_raw_on_disk_gb']} GB** — not the "
        f"{budget['raw_total_gb']} GB full-download figure. Raw is therefore never "
        "the binding constraint.",
        "",
        "## §0d Scope A is now reachable",
        "",
        "Phase 0.5 rejected Scope A (full EEG, incl. Sternberg) because raw "
        "(75.87 GB) plus derivatives (~67 GB under the old double-counting model) "
        "did not fit 95 GB. Under streaming, peak raw is ~1.2 GB regardless of "
        "scope, so the full dataset is affordable. Sternberg is deliberately NOT "
        "added this phase (prove the pipeline on rest + MSIT first); this note "
        "records that Scope A can be revisited cheaply in Phase 2.",
        "",
        "## vs Phase 0.5 estimate",
        "",
        "Phase 0.5 estimated 46.47 GB raw + 40.93 GB derivatives = 87.4 GB "
        "co-resident. The Phase 0.5 derivative model double-counted (epoched "
        "copies ×1.5 and full-size ICA copies). The measured model stores only "
        f"the continuous derivative ({budget['derivatives_total_gb']} GB), so the "
        f"total footprint is ~{budget['derivatives_total_gb'] + budget['peak_raw_on_disk_gb']} GB.",
        "",
        "## Method",
        "",
        f"duration_s = .eeg bytes / ({N_CHANNELS_NATIVE} ch × {BYTES_PER_SAMPLE} B "
        f"float32 × {NATIVE_SFREQ_HZ:.0f} Hz native) — per subject per task from "
        "the measured size survey. Continuous bytes = 127 × duration × target "
        "rate × 4 B, target rates from config/preproc.yaml (rest 500 Hz, "
        "msit 250 Hz).",
        "",
    ]
    out = REPORTS_DIR / "phase1_budget_actual.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run() -> dict:
    cfg = load_preproc_config()
    budget = compute_budget(cfg)
    report_path = write_budget_report(cfg, budget)
    if budget["derivatives_total_gb"] > budget["gate_gb"]:
        raise BudgetExceededError(
            f"Measured derivative total {budget['derivatives_total_gb']} GB "
            f"exceeds the {budget['gate_gb']} GB gate — the duration model is "
            f"wrong. Stop and report (phase_1.md §8).")
    return {"budget": budget, "report_path": str(report_path)}
