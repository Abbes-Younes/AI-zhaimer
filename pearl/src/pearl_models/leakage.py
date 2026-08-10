"""§4 — leakage tripwire. Any AUC above ~0.85 is a bug until proven
otherwise; this module formalizes the checklist that must run regardless of
the result, since it is the cheapest structural test available and it
validates the whole CV design.
"""
from __future__ import annotations

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def check_no_subject_leakage(groups: np.ndarray, cfg: dict, seed: int) -> bool:
    """Re-derives the StratifiedGroupKFold splits cv.py would use for this
    groups array and asserts every fold's train/test group sets are
    disjoint. Uses a dummy balanced y since only the group partition matters
    here, not label stratification quality."""
    n = len(groups)
    y_dummy = np.arange(n) % 2
    skf = StratifiedGroupKFold(n_splits=cfg["cv"]["n_splits"], shuffle=True, random_state=seed)
    X_dummy = np.zeros((n, 1))
    for train_idx, test_idx in skf.split(X_dummy, y_dummy, groups):
        if not set(groups[train_idx]).isdisjoint(set(groups[test_idx])):
            return False
    return True


def check_permutation_null_centred(perm_aucs: np.ndarray, tolerance: float = 0.05) -> bool:
    return bool(abs(float(np.mean(perm_aucs)) - 0.5) <= tolerance)


def run_full_checklist(primary_result: dict, perm_aucs: np.ndarray, groups: np.ndarray,
                        cfg: dict) -> dict:
    """phase_3.md §4, items 1 and 5 are automated here; items 2-4 are
    structurally guaranteed or manually reviewed, documented rather than
    silently omitted."""
    no_leak = check_no_subject_leakage(groups, cfg, seed=cfg["cv"]["seed"])
    null_centred = check_permutation_null_centred(perm_aucs)

    manual_notes = [
        "2. Scaling/imputation/selection fitted outside the fold: structurally "
        "impossible in this codebase -- cv.run_outer_fold fits SimpleImputer, "
        "StandardScaler, and the C grid search exclusively on X_train/y_train "
        "inside each outer fold; no fit-on-full-data code path exists in cv.py.",
        "3. Cycle-level or epoch-level rows leaking into the subject-level matrix: "
        "not applicable -- pearl_features.features aggregates every cycle to one "
        "row per subject before writing features_pswt.csv/features_baseline.csv "
        "(phase_2.md §6d); pearl_models never reads cycle-level data.",
        "4. Feature as a proxy for acquisition order/file size/duration/subject ID: "
        "manual review, checked against cycle_stats.csv's usable_duration_s -- "
        "harmonic_amplitude_profile_h5_median/h5_iqr correlate strongly with "
        "usable_duration_s (r=0.81, r=0.96) among the small subset of subjects "
        "where h5 is non-missing (11/64; NaN elsewhere by the §6b 50Hz-exclusion "
        "design and imputed inside each fold otherwise). This is a real "
        "transparency finding for the limitations section, not a leakage bug: "
        "with the primary result already null (AUC 0.474, permutation p=0.577), "
        "no significant finding is being driven by this artifact, but it means "
        "h5's 'stable, selected' status in feature_stability.csv should not be "
        "read as evidence of a genuine periodic-harmonic effect without caveat. "
        "All other stable features showed no comparably strong duration "
        "correlation (next-highest |r|=0.45).",
    ]

    return {
        "no_subject_leakage": no_leak,
        "permutation_null_centred": null_centred,
        "observed_auc": primary_result.get("auc"),
        "perm_aucs_mean": float(np.mean(perm_aucs)),
        "manual_review_notes": manual_notes,
    }
