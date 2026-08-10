"""§3 — the primary analysis, and §3a/§3b/§0e. One run, per the declared plan."""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from pearl_models import cv


def run_one_analysis(name: str, X: np.ndarray, y: np.ndarray, groups: np.ndarray,
                      cfg: dict, seed: int, subject_ids: list[str] | None = None) -> dict:
    observed = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed)
    p_value, perm_aucs = cv.permutation_test(X, y, groups, cfg, seed=seed,
                                              observed_auc=observed["mean_pooled_auc"])
    ci = cv.bootstrap_ci(X, y, groups, cfg, seed=seed)
    return {
        "name": name,
        "auc": observed["mean_pooled_auc"],
        "pooled_auc_per_repeat": observed["pooled_auc_per_repeat"],
        "ci": ci,
        "p_value": p_value,
        "perm_aucs": perm_aucs,
        "fold_diagnostics": observed["fold_diagnostics"],
        "oof_proba_last_repeat": observed["oof_proba_last_repeat"],
        "y": y,
        "subject_ids": subject_ids if subject_ids is not None else list(range(len(y))),
        "n_subjects_used": len(y),
        "reference_lines": cfg["reference_lines"],
    }


def feature_stability(fold_diagnostics: list[list[dict]], feature_names: list[str]) -> pd.DataFrame:
    n_features = len(feature_names)
    selected_counts = np.zeros(n_features)
    total = 0
    sign_agree = np.zeros(n_features)
    signs_seen: list[list[int]] = [[] for _ in range(n_features)]

    for repeat in fold_diagnostics:
        for fold in repeat:
            total += 1
            selected = fold["selected"]
            coef = fold["coef"]
            for i in range(n_features):
                if selected[i]:
                    selected_counts[i] += 1
                    signs_seen[i].append(int(np.sign(coef[i])))

    rows = []
    for i, name in enumerate(feature_names):
        freq = selected_counts[i] / total if total else 0.0
        if signs_seen[i]:
            mode_sign, mode_count = Counter(signs_seen[i]).most_common(1)[0]
            sign_consistency = mode_count / len(signs_seen[i])
        else:
            sign_consistency = float("nan")
        rows.append({"feature": name, "selection_frequency": freq,
                     "sign_consistency": sign_consistency, "stable": freq > 0.8})
    return pd.DataFrame(rows)


def run_primary_analysis(cfg: dict) -> dict:
    from pearl_models.data import load_pswt_features, load_labels, load_nuisance
    from pearl_models.nuisance import run_nuisance_only, NUISANCE_COLUMNS

    pswt = load_pswt_features()
    labels = load_labels().set_index("subject_id")
    nuisance = load_nuisance()

    joined = pswt.join(labels[["risk_vs_none"]], how="inner")
    feature_cols = list(pswt.columns)
    X_feat = joined[feature_cols].to_numpy(dtype=float)
    y = joined["risk_vs_none"].to_numpy(dtype=int)
    groups = np.arange(len(y))
    seed = cfg["cv"]["seed"]

    features_only = run_one_analysis("features_only", X_feat, y, groups, cfg, seed=seed,
                                      subject_ids=list(joined.index))

    joined_fn = pswt.join(nuisance[NUISANCE_COLUMNS], how="inner").join(
        labels[["risk_vs_none"]], how="inner")
    fn_cols = feature_cols + NUISANCE_COLUMNS
    X_fn = joined_fn[fn_cols].to_numpy(dtype=float)
    y_fn = joined_fn["risk_vs_none"].to_numpy(dtype=int)
    groups_fn = np.arange(len(y_fn))
    features_plus_nuisance = run_one_analysis("features_plus_nuisance", X_fn, y_fn, groups_fn,
                                               cfg, seed=seed, subject_ids=list(joined_fn.index))

    nuisance_only = run_nuisance_only(cfg)
    nuisance_only["name"] = "nuisance_only"
    nuisance_only["reference_lines"] = cfg["reference_lines"]

    return {"features_only": features_only, "features_plus_nuisance": features_plus_nuisance,
            "nuisance_only": nuisance_only}


def run_secondary_set(cfg: dict) -> dict:
    from pearl_models.data import load_pswt_features, load_baseline_features, load_labels
    from pearl_models.benchmark import run_msit_benchmark

    labels = load_labels().set_index("subject_id")
    seed = cfg["cv"]["seed"]

    baseline = load_baseline_features()
    rest_cols = [c for c in baseline.columns if not c.startswith("msit_")]
    joined_rest = baseline[rest_cols].dropna(how="any").join(labels[["risk_vs_none"]], how="inner")
    X_rest = joined_rest[rest_cols].to_numpy(dtype=float)
    y_rest = joined_rest["risk_vs_none"].to_numpy(dtype=int)
    baseline_rest = run_one_analysis("baseline_rest", X_rest, y_rest,
                                      np.arange(len(y_rest)), cfg, seed=seed)

    pswt = load_pswt_features()
    combo_cols = list(pswt.columns) + rest_cols
    # No dropna here: PSWT's harmonic_amplitude_profile_h5_* columns are
    # intentionally NaN for most subjects (the per-subject 50Hz-exclusion
    # index from Phase 2, phase_2.md §6b) -- cv.py's SimpleImputer handles
    # this inside each fold, same as run_primary_analysis's features_only.
    # dropna(how="any") here would silently collapse the cohort to the ~6
    # subjects with a non-standard excluded index, which is exactly the kind
    # of leakage-adjacent silent data loss the leakage checklist (Task 9)
    # exists to catch -- caught here instead, before that task even runs.
    joined_combo = pswt.join(baseline[rest_cols], how="inner").join(
        labels[["risk_vs_none"]], how="inner")
    X_combo = joined_combo[combo_cols].to_numpy(dtype=float)
    y_combo = joined_combo["risk_vs_none"].to_numpy(dtype=int)
    pswt_plus_baseline_rest = run_one_analysis("pswt_plus_baseline_rest", X_combo, y_combo,
                                                np.arange(len(y_combo)), cfg, seed=seed)

    msit_result = run_msit_benchmark(cfg)
    baseline_msit = {**msit_result, "name": "baseline_msit", "reference_lines": cfg["reference_lines"]}

    results = {"baseline_rest": baseline_rest, "pswt_plus_baseline_rest": pswt_plus_baseline_rest,
               "baseline_msit": baseline_msit}

    pvalues = {name: r["p_value"] for name, r in results.items()}
    holm_adjusted = cv.holm_correction(pvalues)
    for name, r in results.items():
        r["p_value_holm"] = holm_adjusted[name]

    return results
