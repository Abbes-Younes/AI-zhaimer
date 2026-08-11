"""phase_5.md §0b — ICA n_components re-evaluation. A reproducible
comparison script, not a permanent pipeline module: run once, record the
evidence in reports/phase5_ica_component_evaluation.md, decide, done.

Every call here uses process_subject_task(..., output_dir=<scratch>) so the
live derivative tree is never touched (see the phase_5.md Stage 1 incident
this discipline exists because of).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd

from .download import download_subject, load_manifest, load_url_map, manifest_for_subject
from .paths import RAW_DIR
from .preprocess import process_subject_task


def ensure_raw_present(subject: str, task: str, cfg: dict) -> None:
    """Downloads just this (subject, task)'s BrainVision triplet if missing,
    reusing the existing manifest-driven, verified, retry-on-failure
    download path -- no new download logic."""
    manifest = load_manifest()
    rows = [r for r in manifest_for_subject(manifest, subject)
            if r.get("task") == task or r["path"].split("/")[-1].startswith(f"{subject}_task-{task}")]
    if not rows:
        raise ValueError(f"no manifest rows found for {subject}/{task}")
    url_map = load_url_map()
    summary = download_subject(subject, rows, url_map, cfg)
    if summary["quarantined"]:
        raise RuntimeError(f"download failed for {subject}/{task}: {summary['errors']}")


def delete_raw(subject: str) -> None:
    """Cleanup after evaluation, matching Phase 1's streaming discipline --
    raw is not meant to accumulate on disk."""
    import shutil
    subj_dir = RAW_DIR / subject
    if subj_dir.exists():
        shutil.rmtree(subj_dir)


def compare_n_components(subjects_tasks: list[tuple[str, str]], cfg: dict,
                         scratch_dir: Path) -> pd.DataFrame:
    """Runs process_subject_task twice per (subject, task) -- once with the
    current fixed n_components=30, once with n_components=0.99 (explained
    variance) -- both writing to scratch_dir, never the live tree. Returns
    one row per (subject, task, config)."""
    rows = []
    for subject, task in subjects_tasks:
        ensure_raw_present(subject, task, cfg)
        try:
            for label, n_comp in [("fixed_30", 30), ("explained_variance_0.99", 0.99)]:
                run_cfg = copy.deepcopy(cfg)
                run_cfg["ica"]["n_components"] = n_comp
                out_dir = scratch_dir / label / subject / "eeg"
                result = process_subject_task(subject, task, run_cfg, output_dir=out_dir)
                sidecar = json.loads(Path(result["sidecar_path"]).read_text(encoding="utf-8"))
                n_fit = sidecar["ICA"]["n_components"]
                rows.append({
                    "subject": subject, "task": task, "n_components_config": label,
                    "n_bad_channels": result["n_bad_channels"],
                    "n_fit": n_fit,
                    "n_removed": result["n_ica_removed"],
                    "removed_frac": round(result["n_ica_removed"] / max(1, n_fit), 3),
                })
        finally:
            delete_raw(subject)
    return pd.DataFrame(rows)
