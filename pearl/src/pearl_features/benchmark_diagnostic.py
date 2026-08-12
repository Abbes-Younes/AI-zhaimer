"""Track B benchmark-reproduction diagnostic (phase_5_stage2.md §0c,
reports/phase5_stage2_plan_frozen.md §4).

Sanctioned exception to pearl_features label blindness, alongside
confound_gate.py: reads group labels to answer exactly one question --
does the richer `msit_tfa_*` feature family (Track B) reproduce the
published ~0.58 MSIT benchmark any better than
reports/phase3_benchmark_reproduction.md's 0.459? This is a diagnostic
about feature richness, never a claim about `binary_risk_vs_none` as this
project's primary target. The feature source (`msit_tfa_*` columns only)
and the CV/selection procedure are hardcoded, not parameters -- there is no
call signature that redirects this module to evaluate a different feature
set or a different question. Nothing downstream of pearl_features.features
imports this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from pearl_features.confound_gate import _bh_fdr, load_group_map

MSIT_TFA_PREFIX = "msit_tfa_"
PUBLISHED_BENCHMARK_AUC = 0.58
PRIOR_SIMPLE_BASELINE_AUC = 0.459  # reports/phase3_benchmark_reproduction.md
FDR_ALPHA = 0.05


def _select_and_fit_fold(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray,
                          model: str) -> tuple[np.ndarray, int]:
    """t-test + BH-FDR feature selection fit on the training fold only
    (frozen plan §4), then a classifier fit on the selected columns."""
    pvals = np.array([
        stats.ttest_ind(X_train[y_train == 1, j], X_train[y_train == 0, j],
                         equal_var=False, nan_policy="omit").pvalue
        for j in range(X_train.shape[1])
    ])
    pvals = np.nan_to_num(pvals, nan=1.0)
    qvals = _bh_fdr(pvals)
    selected = np.where(qvals < FDR_ALPHA)[0]
    if len(selected) == 0:
        # Nothing survives selection this fold -- fall back to all features
        # rather than crashing. This is itself diagnostic information
        # (n_selected == 0), not silently hidden.
        selected = np.arange(X_train.shape[1])

    clf_cls = (LogisticRegression(max_iter=1000) if model == "logreg"
               else SVC(kernel="linear", probability=True))
    clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), clf_cls)
    clf.fit(X_train[:, selected], y_train)
    proba = clf.predict_proba(X_test[:, selected])[:, 1]
    return proba, len(selected)


def _cv_mean_auc(X: np.ndarray, y: np.ndarray, n_splits: int, n_repeats: int, seed: int,
                  model: str = "logreg") -> tuple[float, list[int]]:
    aucs = []
    n_selected_all = []
    rng = np.random.default_rng(seed)
    for _rep in range(n_repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                               random_state=int(rng.integers(0, 2**31 - 1)))
        for train_idx, test_idx in skf.split(X, y):
            if len(np.unique(y[test_idx])) < 2:
                continue
            proba, n_sel = _select_and_fit_fold(X[train_idx], y[train_idx], X[test_idx], model)
            aucs.append(roc_auc_score(y[test_idx], proba))
            n_selected_all.append(n_sel)
    return (float(np.mean(aucs)) if aucs else 0.5), n_selected_all


def _load_msit_tfa_matrix() -> tuple[np.ndarray, np.ndarray, list[str], int]:
    from pearl_features.paths import FEATURES_DIR

    tfa = pd.read_csv(FEATURES_DIR / "features_tfa.csv", index_col=0)
    msit_cols = [c for c in tfa.columns if c.startswith(MSIT_TFA_PREFIX)]
    group_map = load_group_map()

    df = tfa[msit_cols].copy()
    df["group"] = pd.Series(df.index, index=df.index).map(group_map)
    n_before = len(df)
    df = df.dropna(subset=["group"] + msit_cols, how="any")
    y = df["group"].map(lambda g: 0 if g == "N" else 1).to_numpy(dtype=int)
    X = df[msit_cols].to_numpy(dtype=float)
    return X, y, msit_cols, n_before


def run(n_splits: int = 5, n_repeats: int = 10, n_permutations: int = 1000,
        seed: int = 42) -> dict:
    """The one question this module answers (see module docstring). No
    parameter here can point it at a different feature set or target."""
    X, y, msit_cols, n_before = _load_msit_tfa_matrix()
    n = len(y)

    observed, n_selected = _cv_mean_auc(X, y, n_splits, n_repeats, seed, model="logreg")
    observed_svm, _ = _cv_mean_auc(X, y, n_splits, n_repeats, seed, model="svm")

    rng = np.random.default_rng(seed)
    perm_aucs = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = rng.permutation(y)
        perm_aucs[i], _ = _cv_mean_auc(X, y_perm, n_splits, 1, seed + i + 1, model="logreg")
    p_value = float((perm_aucs >= observed).sum() + 1) / (n_permutations + 1)
    permutation_null_mean = float(perm_aucs.mean())

    boot_aucs = []
    rng2 = np.random.default_rng(seed + 1)
    for _ in range(2000):
        idx = rng2.integers(0, n, size=n)
        if len(np.unique(y[idx])) < 2:
            continue
        auc_b, _ = _cv_mean_auc(X[idx], y[idx], n_splits, 1, seed, model="logreg")
        boot_aucs.append(auc_b)
    ci_low, ci_high = (np.percentile(boot_aucs, [2.5, 97.5]) if boot_aucs else (observed, observed))

    if observed > PRIOR_SIMPLE_BASELINE_AUC + 0.02:
        verdict = "improved"
    elif observed < PRIOR_SIMPLE_BASELINE_AUC - 0.02:
        verdict = "worse"
    else:
        verdict = "unchanged"

    return {
        "verdict": verdict,
        "auc_logreg": observed,
        "auc_svm": observed_svm,
        "ci_low": float(ci_low), "ci_high": float(ci_high),
        "permutation_p": p_value,
        "permutation_null_mean": permutation_null_mean,
        "n_subjects": n, "n_subjects_before_dropna": n_before,
        "n_features_available": len(msit_cols),
        "mean_n_selected": float(np.mean(n_selected)) if n_selected else 0.0,
        "prior_simple_baseline_auc": PRIOR_SIMPLE_BASELINE_AUC,
        "published_benchmark_auc": PUBLISHED_BENCHMARK_AUC,
    }
