"""Nested-CV harness shared by every analysis in Phase 3: primary, nuisance,
benchmark, both positive controls. Pooled out-of-fold AUC across repeats
(phase_3.md §0a), full-pipeline permutation test, bootstrap CI, per-fold
diagnostics for feature stability (§3b).
"""
from __future__ import annotations

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler


def run_outer_fold(X_train, y_train, groups_train, X_test, cv_cfg: dict) -> tuple[np.ndarray, dict]:
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    inner_cv = StratifiedGroupKFold(n_splits=cv_cfg["inner_n_splits"], shuffle=True,
                                     random_state=cv_cfg["seed"])
    search = GridSearchCV(
        LogisticRegression(solver="lbfgs", max_iter=2000),  # l1_ratio=0.0 default == L2
        param_grid={"C": cv_cfg["c_grid"]}, cv=inner_cv, scoring="roc_auc")
    search.fit(X_train_scaled, y_train, groups=groups_train)

    final = LogisticRegression(solver="lbfgs", max_iter=2000, C=search.best_params_["C"])
    final.fit(X_train_scaled, y_train)
    proba = final.predict_proba(X_test_scaled)[:, 1]

    diag = {"best_c": search.best_params_["C"], "scaler_mean": scaler.mean_,
            "coef": final.coef_[0], "selected": np.abs(final.coef_[0]) > 1e-8}
    return proba, diag


def pooled_repeated_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, cfg: dict,
                        seed: int, n_repeats: int | None = None) -> dict:
    cv_cfg = cfg["cv"]
    n_repeats = n_repeats if n_repeats is not None else cv_cfg["n_repeats"]
    pooled_aucs, fold_diagnostics, oof_last = [], [], None

    for rep in range(n_repeats):
        skf = StratifiedGroupKFold(n_splits=cv_cfg["n_splits"], shuffle=True,
                                    random_state=seed + rep)
        oof_proba = np.full(len(y), np.nan)
        rep_diagnostics = []
        for train_idx, test_idx in skf.split(X, y, groups):
            proba, diag = run_outer_fold(X[train_idx], y[train_idx], groups[train_idx],
                                          X[test_idx], cv_cfg)
            oof_proba[test_idx] = proba
            diag["test_idx"] = test_idx
            rep_diagnostics.append(diag)
        assert not np.any(np.isnan(oof_proba)), "every subject must be covered exactly once per repeat"
        pooled_aucs.append(roc_auc_score(y, oof_proba))
        fold_diagnostics.append(rep_diagnostics)
        oof_last = oof_proba

    return {
        "pooled_auc_per_repeat": pooled_aucs,
        "mean_pooled_auc": float(np.mean(pooled_aucs)),
        "oof_proba_last_repeat": oof_last,
        "fold_diagnostics": fold_diagnostics,
    }


def permutation_test(X, y, groups, cfg: dict, seed: int, observed_auc: float,
                      n_permutations: int | None = None) -> tuple[float, np.ndarray]:
    cv_cfg = cfg["cv"]
    n_perm = n_permutations if n_permutations is not None else cv_cfg["n_permutations"]
    rng = np.random.default_rng(seed)
    perm_aucs = np.empty(n_perm)
    for i in range(n_perm):
        y_perm = rng.permutation(y)
        result = pooled_repeated_cv(X, y_perm, groups, cfg, seed=seed + i + 1,
                                     n_repeats=cv_cfg["permutation_n_repeats"])
        perm_aucs[i] = result["mean_pooled_auc"]
    p = (float((perm_aucs >= observed_auc).sum()) + 1) / (n_perm + 1)
    return p, perm_aucs


def bootstrap_ci(X, y, groups, cfg: dict, seed: int,
                  n_bootstrap: int | None = None) -> tuple[float, float]:
    cv_cfg = cfg["cv"]
    n_boot = n_bootstrap if n_bootstrap is not None else cv_cfg["n_bootstrap"]
    rng = np.random.default_rng(seed)
    boot_aucs = []
    class0_idx = np.where(y == 0)[0]
    class1_idx = np.where(y == 1)[0]
    for _ in range(n_boot):
        idx0 = rng.choice(class0_idx, size=len(class0_idx), replace=True)
        idx1 = rng.choice(class1_idx, size=len(class1_idx), replace=True)
        idx = np.concatenate([idx0, idx1])
        result = pooled_repeated_cv(X[idx], y[idx], groups[idx], cfg, seed=seed,
                                     n_repeats=cv_cfg["bootstrap_n_repeats"])
        boot_aucs.append(result["mean_pooled_auc"])
    lo, hi = np.percentile(boot_aucs, [2.5, 97.5])
    return float(lo), float(hi)


def holm_correction(pvalues: dict[str, float]) -> dict[str, float]:
    names = list(pvalues.keys())
    pvals = np.array([pvalues[n] for n in names])
    order = np.argsort(pvals)
    n = len(pvals)
    adjusted = np.empty(n)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, pvals[idx] * (n - rank))
        running_max = max(running_max, val)
        adjusted[idx] = running_max
    return {names[i]: float(adjusted[i]) for i in range(n)}
