"""QC metrics table and frozen exclusion list (phase_1.md §3).

Label-free: exclusion is decided purely from QC metrics with the fixed
thresholds of config/preproc.yaml. The exclusion list is FROZEN here; the
per-group breakdown is computed only afterwards, in report_qc.py.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from .paths import (
    PREPROC_DIR,
    QC_DIR,
    SIZE_SURVEY_CSV,
    get_run_id,
    ensure_dirs,
)


def load_all_sidecars() -> list[dict]:
    rows = []
    for subj_dir in sorted(PREPROC_DIR.glob("sub-*/eeg")):
        for sidecar in sorted(subj_dir.glob("*_desc-preproc_eeg.json")):
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            rows.append(data)
    return rows


def expected_durations() -> dict[tuple[str, str], float]:
    """Expected duration_s per (subject, task) from the size-survey listing."""
    if not SIZE_SURVEY_CSV.exists():
        return {}
    out = {}
    with open(SIZE_SURVEY_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("modality") != "eeg" or not (row.get("path") or "").endswith(".eeg"):
                continue
            nbytes = int(row["bytes"])
            out[(row["subject"], row["task"])] = nbytes / (127 * 4 * 1000.0)
    return out


def _task_key(task: str) -> str:
    """Sidecar TaskName is "rest"/"msit"; config keys are "task-rest"/"task-msit"."""
    return task if task.startswith("task-") else f"task-{task}"


def _fifth_harmonic_flag(iaf_hz: float, cfg: dict) -> bool:
    if not iaf_hz:
        return False
    width = float(cfg["line_noise"]["notch_width_hz"])
    margin = float(cfg["line_noise"]["margin_hz"])
    return abs(5.0 * iaf_hz - 50.0) < width / 2 + margin


def classify_sidecar(sidecar: dict, cfg: dict,
                     expected: dict[tuple[str, str], float]) -> dict:
    """Map one sidecar onto a QC row with pass/warn/fail + flags."""
    q = cfg.get("qc", {})
    task = sidecar.get("TaskName", "?")
    subject = sidecar.get("ParticipantID") or "unknown"

    bad = sidecar["BadChannels"]
    ica = sidecar["ICA"]
    dur_s = sidecar["Duration"]["s"]
    ln = sidecar["LineNoisePower"]
    iaf = sidecar.get("IAF", {})
    ica_frac = len(ica["excluded_components"]) / max(1, ica["n_components"])

    expected_s = expected.get((subject, task))
    reasons_fail, reasons_warn = [], []

    if bad["n"] >= int(q["bad_channels_fail"]):
        reasons_fail.append(f"{bad['n']} bad channels (>= {q['bad_channels_fail']})")
    elif bad["n"] > int(q["bad_channels_warn"]):
        reasons_warn.append(f"{bad['n']} bad channels (> {q['bad_channels_warn']})")

    if bad["occipital_bads"] >= int(q["max_occipital_bads_fail"]):
        reasons_fail.append(
            f"{bad['occipital_bads']} occipital bads (>= {q['max_occipital_bads_fail']})")
    elif bad["occipital_bads"] > int(q["max_occipital_bads_warn"]):
        reasons_warn.append(
            f"{bad['occipital_bads']} occipital bads (> {q['max_occipital_bads_warn']})")

    # Client decision 2026-08-06: warn-only. Removed components are verified
    # high-confidence muscle (p_brain ~ 0), so no hard exclusion is applied;
    # the fraction stays in the table as the over-cleaning outlier flag.
    ica_fail_thr = q.get("ica_removed_frac_fail")
    if ica_fail_thr is not None and ica_frac >= float(ica_fail_thr):
        reasons_fail.append(
            f"{ica_frac:.0%} ICA removed (>= {float(ica_fail_thr):.0%})")
    elif ica_frac > float(q["ica_removed_frac_warn"]):
        reasons_warn.append(
            f"{ica_frac:.0%} ICA removed (> {q['ica_removed_frac_warn']:.0%})")

    if sidecar["ArtifactAnnotation"]["fraction"] >= float(q["artifact_frac_fail"]):
        reasons_fail.append(
            f"artifact {sidecar['ArtifactAnnotation']['fraction']:.0%} (>= {q['artifact_frac_fail']:.0%})")
    elif sidecar["ArtifactAnnotation"]["fraction"] > float(q["artifact_frac_warn"]):
        reasons_warn.append(
            f"artifact {sidecar['ArtifactAnnotation']['fraction']:.0%} (> {q['artifact_frac_warn']:.0%})")

    if (ln.get("before_index", 0) > float(q.get("line_noise_present_before_index", 1.5))
            and ln.get("after_index", 0) > float(q.get("line_noise_fail_after_index", 1.5))):
        reasons_fail.append(
            f"line-noise removal failed: 50 Hz index {ln.get('after_index')} "
            f"after treatment (before {ln.get('before_index')})")

    if expected_s and dur_s < expected_s * float(q["min_duration_frac"]):
        reasons_fail.append(
            f"truncated: {dur_s:.0f}s < {expected_s * float(q['min_duration_frac']):.0f}s expected")

    # Normalize so the alpha-required rule (phase_1.md §2c, §8) actually fires.
    task_key = _task_key(task)
    require_alpha = task_key in set(cfg["iaf"].get("require_for_tasks", []))
    if require_alpha and not iaf.get("present"):
        reasons_fail.append("no identifiable alpha peak (rest)")

    verdict = "fail" if reasons_fail else ("warn" if reasons_warn else "pass")
    return {
        "subject": subject,
        "task": task,
        "duration_s": dur_s,
        "expected_duration_s": round(expected_s, 1) if expected_s else "",
        "n_samples_final": sidecar["Duration"]["n_samples_final"],
        "n_bad_channels": bad["n"],
        "bad_channels": ",".join(bad["names"]),
        "occipital_bads": bad["occipital_bads"],
        "n_ica_components": ica["n_components"],
        "n_ica_removed": len(ica["excluded_components"]),
        "ica_removed_labels": ",".join(ica["excluded_labels"]),
        "ica_removed_frac": round(ica_frac, 3),
        "ica_labeling": ica["labeling"],
        "line_noise_method": sidecar["LineNoiseRemoval"]["method"],
        "line_noise_index_before": ln.get("before_index", ""),
        "line_noise_index_after": ln.get("after_index", ""),
        "iaf_hz": iaf.get("iaf_hz", ""),
        "alpha_peak_height_db": iaf.get("peak_height_db", ""),
        "alpha_present": iaf.get("present", False),
        "artifact_frac": sidecar["ArtifactAnnotation"]["fraction"],
        "fifth_harmonic_collision": _fifth_harmonic_flag(iaf.get("iaf_hz") or 0, cfg),
        "verdict": verdict,
        "flags": ";".join(reasons_fail + reasons_warn),
    }


def build_qc_table(cfg: dict) -> list[dict]:
    """Compute QC rows for every processed (subject, task) and write CSV."""
    ensure_dirs()
    expected = expected_durations()
    rows = [classify_sidecar(s, cfg, expected) for s in load_all_sidecars()]
    rows.sort(key=lambda r: (r["subject"], r["task"]))
    out = QC_DIR / "qc_metrics.csv"
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return rows


def freeze_exclusions(rows: list[dict], cfg: dict) -> list[dict]:
    """FROZEN exclusion list — decided purely from QC, before labels join."""
    exc_cfg = cfg.get("exclusion", {})
    max_bads = int(exc_cfg.get("max_bad_channels", 10))
    max_occ = int(exc_cfg.get("max_occipital_bads", 5))
    require_tasks = set(cfg["iaf"].get("require_for_tasks", []))

    by_subject: dict[str, list[str]] = {}
    for r in rows:
        if r["verdict"] == "fail":
            by_subject.setdefault(r["subject"], []).append(
                f"{r['task']}: {r['flags']}")
        if r["n_bad_channels"] >= max_bads:
            by_subject.setdefault(r["subject"], []).append(
                f"{r['n_bad_channels']} bad channels >= {max_bads}")
        if _task_key(r["task"]) in require_tasks and r["occipital_bads"] >= max_occ:
            by_subject.setdefault(r["subject"], []).append(
                f"{r['occipital_bads']} occipital bads (alpha sites) >= {max_occ}")

    frozen_at = datetime.now(timezone.utc).isoformat()
    run_id = get_run_id() or "unmanaged"
    excluded = [
        {"subject": s, "reason": " | ".join(sorted(set(reasons))),
         "frozen_at": frozen_at, "run_id": run_id}
        for s, reasons in sorted(by_subject.items())
    ]
    out = QC_DIR / "excluded_subjects.csv"
    # "Frozen" was a comment, not a property: archive the previous list
    # before overwriting so a refreeze is a visible, recoverable act rather
    # than a silent overwrite.
    if out.exists():
        archive = QC_DIR / f"excluded_subjects.{frozen_at.replace(':', '-')}.csv"
        archive.write_bytes(out.read_bytes())
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["subject", "reason", "frozen_at", "run_id"])
        writer.writeheader()
        writer.writerows(excluded)
    return excluded


def run(cfg: dict) -> dict:
    rows = build_qc_table(cfg)
    excluded = freeze_exclusions(rows, cfg)
    n_pass = sum(1 for r in rows if r["verdict"] == "pass")
    n_warn = sum(1 for r in rows if r["verdict"] == "warn")
    n_fail = sum(1 for r in rows if r["verdict"] == "fail")
    return {
        "n_rows": len(rows), "n_pass": n_pass, "n_warn": n_warn, "n_fail": n_fail,
        "n_excluded": len(excluded), "excluded": excluded,
        "qc_metrics_csv": str(QC_DIR / "qc_metrics.csv"),
        "excluded_csv": str(QC_DIR / "excluded_subjects.csv"),
    }
