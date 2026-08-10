"""§2a — benchmark reproduction on MSIT.

Pipeline-validation test, not a result: the published 0.58 came from
task-state MSIT with spectral features. If MSIT + baseline features lands
near 0.58, this project's preprocessing and CV machinery are comparable to
published work. If it lands at chance, the pipeline differs from theirs in a
way that must be understood before quoting their number as a target.
"""
from __future__ import annotations

import numpy as np

from pearl_models import cv
from pearl_models.data import load_baseline_features, load_labels

_MSIT_COLUMNS = [
    "msit_band_power_delta", "msit_band_power_theta", "msit_band_power_alpha",
    "msit_band_power_beta", "msit_band_power_gamma",
    "msit_aperiodic_offset", "msit_aperiodic_slope",
]


def run_msit_benchmark(cfg: dict) -> dict:
    baseline = load_baseline_features()
    labels = load_labels().set_index("subject_id")

    joined = baseline[_MSIT_COLUMNS].dropna(how="any").join(labels[["risk_vs_none"]], how="inner")
    X = joined[_MSIT_COLUMNS].to_numpy(dtype=float)
    y = joined["risk_vs_none"].to_numpy(dtype=int)
    groups = np.arange(len(y))

    seed = cfg["cv"]["seed"]
    observed = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed)
    p_value, _ = cv.permutation_test(X, y, groups, cfg, seed=seed,
                                      observed_auc=observed["mean_pooled_auc"])
    ci = cv.bootstrap_ci(X, y, groups, cfg, seed=seed)

    auc = observed["mean_pooled_auc"]
    if abs(auc - 0.58) <= 0.10:
        verdict = "near_benchmark"
    elif auc <= 0.55:
        verdict = "at_chance"
    else:
        verdict = "other"

    return {"auc": auc, "ci": ci, "p_value": p_value, "n_subjects_used": len(y), "verdict": verdict}
