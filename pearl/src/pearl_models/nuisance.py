"""§2b — the nuisance-only reference line.

Fits the primary CV machinery on nuisance variables alone: age, sex, SES,
BDI, education, bad-channel count, ICA components removed, artifact_frac
(the last three declared per Amendment 2 §0d). This becomes the row every
feature model in §3 is measured against — a feature model that does not beat
this line has not demonstrated anything about EEG.
"""
from __future__ import annotations

import numpy as np

from pearl_models import cv
from pearl_models.data import load_labels, load_nuisance, load_pswt_features

NUISANCE_COLUMNS = ["age", "sex", "education", "BDI", "SES",
                     "n_bad_channels", "n_ica_removed", "artifact_frac"]


def run_nuisance_only(cfg: dict) -> dict:
    # Restrict to the frozen 64-subject rest cohort (same population as the
    # PSWT/baseline feature analyses) so this reference line is comparable to
    # the others -- qc_metrics.csv and participants.tsv both cover all 79
    # subjects, so without this the nuisance-only line would be fit on a
    # different, larger population than everything it's compared against.
    cohort_subjects = load_pswt_features().index

    nuisance = load_nuisance()
    labels = load_labels().set_index("subject_id")
    joined = nuisance[NUISANCE_COLUMNS].join(labels[["risk_vs_none"]], how="inner")
    joined = joined.loc[joined.index.intersection(cohort_subjects)]

    X = joined[NUISANCE_COLUMNS].to_numpy(dtype=float)
    y = joined["risk_vs_none"].to_numpy(dtype=int)
    groups = np.arange(len(y))

    seed = cfg["cv"]["seed"]
    observed = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed)
    p_value, _ = cv.permutation_test(X, y, groups, cfg, seed=seed,
                                      observed_auc=observed["mean_pooled_auc"])
    ci = cv.bootstrap_ci(X, y, groups, cfg, seed=seed)

    return {"auc": observed["mean_pooled_auc"], "ci": ci, "p_value": p_value,
            "n_subjects_used": len(y), "verdict": "reference_line"}
