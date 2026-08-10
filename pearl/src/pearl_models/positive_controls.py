"""§1 — positive controls, run before the hypothesis.

Both controls reuse the exact same nested-CV machinery (pearl_models.cv) as
the primary analysis. 1a is a within-subject comparison (two rows per
subject: eyes-open, eyes-closed) so groups must be subject-level to prevent
both conditions of one subject from straddling a fold. 1b is a genuine
cross-subject problem, structurally identical to the primary analysis.
"""
from __future__ import annotations

import mne
import numpy as np
import pandas as pd

from pearl_models import cv


def run_sex_control(cfg: dict, pswt_features: pd.DataFrame, nuisance: pd.DataFrame) -> dict:
    joined = pswt_features.join(nuisance[["sex"]], how="inner").dropna(subset=["sex"])
    feature_cols = [c for c in pswt_features.columns]
    X = joined[feature_cols].to_numpy(dtype=float)
    y = joined["sex"].to_numpy(dtype=int)
    groups = np.arange(len(y))

    seed = cfg["cv"]["seed"]
    observed = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed)
    p_value, _ = cv.permutation_test(X, y, groups, cfg, seed=seed,
                                      observed_auc=observed["mean_pooled_auc"])
    ci = cv.bootstrap_ci(X, y, groups, cfg, seed=seed)

    floor = cfg["positive_controls"]["sex_auc_reference_floor"]
    verdict = "pass" if observed["mean_pooled_auc"] >= floor else "fail"
    return {"auc": observed["mean_pooled_auc"], "ci": ci, "p_value": p_value,
            "n_subjects_used": len(y), "verdict": verdict}


def build_eyes_open_closed_matrix(subjects: list[str], features_cfg: dict,
                                   iaf_by_subject: dict[str, float],
                                   eyes_closed_features: pd.DataFrame,
                                   preproc_dir, min_duration_s: float = 60.0
                                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], int]:
    from pearl_preproc.preprocess import eyes_open_window
    from pearl_features.features import compute_subject_features

    feature_cols = list(eyes_closed_features.columns)
    rows_X, rows_y, rows_groups = [], [], []
    n_dropped = 0

    for gi, subject in enumerate(subjects):
        if subject not in eyes_closed_features.index or subject not in iaf_by_subject:
            n_dropped += 1
            continue
        fif_path = preproc_dir / subject / "eeg" / f"{subject}_task-rest_desc-preproc_eeg.fif"
        raw_full = mne.io.read_raw_fif(fif_path, preload=True, verbose=False)
        window = eyes_open_window(raw_full.annotations, raw_full.times[-1],
                                   min_duration_s=min_duration_s)
        if window is None:
            n_dropped += 1
            continue
        start, end = window
        eo_raw = raw_full.copy().crop(tmin=start, tmax=min(end, raw_full.times[-1]))

        try:
            eo_feats, _ = compute_subject_features(subject, features_cfg,
                                                     iaf_by_subject[subject], raw=eo_raw)
        except (AssertionError, ValueError):
            n_dropped += 1
            continue

        ec_row = eyes_closed_features.loc[subject, feature_cols].to_numpy(dtype=float)
        eo_row = np.array([eo_feats.get(c, np.nan) for c in feature_cols], dtype=float)

        rows_X.append(ec_row); rows_y.append(1); rows_groups.append(gi)
        rows_X.append(eo_row); rows_y.append(0); rows_groups.append(gi)

    X = np.stack(rows_X, axis=0)
    y = np.array(rows_y, dtype=int)
    groups = np.array(rows_groups, dtype=int)
    return X, y, groups, feature_cols, n_dropped


def run_eyes_open_closed_control(cfg: dict, features_cfg: dict) -> dict:
    from pearl_features.cohort import load_qc_metrics
    from pearl_preproc.paths import PREPROC_DIR
    from pearl_models.data import load_pswt_features

    eyes_closed_features = load_pswt_features()
    qc = load_qc_metrics()
    rest_qc = qc[qc["task"].isin(["rest", "task-rest"])].drop_duplicates(subset="subject")
    iaf_by_subject = dict(zip(rest_qc["subject"], rest_qc["iaf_hz"].astype(float)))

    subjects = list(eyes_closed_features.index)
    min_duration_s = cfg["positive_controls"]["eyes_open_min_duration_s"]
    X, y, groups, _feature_cols, n_dropped = build_eyes_open_closed_matrix(
        subjects, features_cfg, iaf_by_subject, eyes_closed_features, PREPROC_DIR, min_duration_s)

    seed = cfg["cv"]["seed"]
    observed = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed)
    p_value, _ = cv.permutation_test(X, y, groups, cfg, seed=seed,
                                      observed_auc=observed["mean_pooled_auc"])
    ci = cv.bootstrap_ci(X, y, groups, cfg, seed=seed)

    floor = cfg["positive_controls"]["eyes_open_closed_auc_floor"]
    verdict = "pass" if observed["mean_pooled_auc"] >= floor else "fail"
    return {"auc": observed["mean_pooled_auc"], "ci": ci, "p_value": p_value,
            "n_subjects_used": len(groups) // 2, "n_dropped": n_dropped, "verdict": verdict}
