"""Track B orchestration (phase_5_stage2.md §2, frozen plan §4). Writes
features_tfa.csv as a separate file from features_baseline.csv -- Track B
is a separately-budgeted, benchmark-validated-only family, never claimed to
supersede the existing baseline/PSWT features (phase_5_stage2.md non-goals).
"""
from __future__ import annotations

import json
from pathlib import Path

import mne
import pandas as pd

from pearl_features.paths import FEATURES_DIR, git_sha
from pearl_features.tfa import epoch_locked_tfa, marker_onsets_with_min_gap, windowed_tfa

ROI_FRONTOCENTRAL = ["Fz", "FC1", "FC2", "Cz", "F3", "F4", "FC5", "FC6", "C3", "C4"]

_ENCODING_CODE = 4
_ENCODING_MIN_GAP_S = 3.0
_ENCODING_DURATION_S = 3.0
_RETRIEVAL_CODE = 12
_RETRIEVAL_MIN_GAP_S = 0.4
_RETRIEVAL_DURATION_S = 0.4


def _read_task_continuous(subject: str, task: str):
    from pearl_preproc.paths import PREPROC_DIR
    fif_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-{task}_desc-preproc_eeg.fif"
    if not fif_path.exists():
        raise FileNotFoundError(fif_path)
    return mne.io.read_raw_fif(fif_path, preload=True, verbose=False)


def compute_msit_tfa(subject: str) -> dict[str, float]:
    raw = _read_task_continuous(subject, "msit")
    picks = [ch for ch in ROI_FRONTOCENTRAL if ch in raw.ch_names]
    return {f"msit_{k}": v for k, v in windowed_tfa(raw, picks, window_s=4.0).items()}


def compute_sternberg_tfa(subject: str) -> dict[str, float]:
    raw = _read_task_continuous(subject, "sternberg")
    picks = [ch for ch in ROI_FRONTOCENTRAL if ch in raw.ch_names]

    enc_onsets, enc_skipped = marker_onsets_with_min_gap(
        raw, code=_ENCODING_CODE, min_gap_s=_ENCODING_MIN_GAP_S)
    ret_onsets, ret_skipped = marker_onsets_with_min_gap(
        raw, code=_RETRIEVAL_CODE, min_gap_s=_RETRIEVAL_MIN_GAP_S)

    enc = epoch_locked_tfa(raw, picks, enc_onsets, duration_s=_ENCODING_DURATION_S,
                            prefix="sternberg_encoding_")
    ret = epoch_locked_tfa(raw, picks, ret_onsets, duration_s=_RETRIEVAL_DURATION_S,
                            prefix="sternberg_retrieval_")
    out = {**enc, **ret}
    out["sternberg_encoding_n_trials_used"] = len(enc_onsets)
    out["sternberg_encoding_n_trials_skipped"] = enc_skipped
    out["sternberg_retrieval_n_trials_used"] = len(ret_onsets)
    out["sternberg_retrieval_n_trials_skipped"] = ret_skipped
    return out


def run(msit_included: set[str], sternberg_included: set[str],
        run_id: str, out_dir: Path = FEATURES_DIR) -> dict:
    """Iterates the union of msit_included/sternberg_included -- NOT
    rest_included. Track A's baseline extension stayed rest-anchored
    (matching pipeline.run()'s pre-existing convention), but Track B's
    benchmark_diagnostic must match phase3_benchmark_reproduction.md's own
    population (MSIT-QC-surviving subjects, N=55 there -- not the
    rest-based 64) per the frozen plan §4's "mirrors...exact scope"
    requirement. Restricting to rest_included would needlessly drop MSIT
    data from subjects whose rest recording failed QC or whose PSWT
    construction failed for DSP reasons unrelated to MSIT at all."""
    subjects = msit_included | sternberg_included
    rows: dict[str, dict] = {}
    errors: list[dict] = []
    for subject in sorted(subjects):
        row: dict[str, float] = {}
        if subject in msit_included:
            try:
                row.update(compute_msit_tfa(subject))
            except FileNotFoundError:
                pass
        if subject in sternberg_included:
            try:
                row.update(compute_sternberg_tfa(subject))
            except FileNotFoundError:
                pass
        if row:
            rows[subject] = row

    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "subject"
    df.to_csv(out_dir / "features_tfa.csv")
    (out_dir / "features_tfa_meta.json").write_text(json.dumps({
        "run_id": run_id, "git_sha": git_sha(),
        "roi_channels": ROI_FRONTOCENTRAL,
        "n_subjects": len(rows),
    }, indent=2) + "\n", encoding="utf-8")
    return {"n_subjects": len(rows), "n_features": len(next(iter(rows.values()), {})), "errors": errors}
