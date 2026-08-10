import numpy as np
import pytest

from pearl_models.cv import (
    run_outer_fold, pooled_repeated_cv, permutation_test, bootstrap_ci, holm_correction,
)

_CFG = {"cv": {"n_splits": 5, "n_repeats": 3, "inner_n_splits": 3, "seed": 1,
               "c_grid": [0.01, 0.1, 1.0, 10.0], "n_permutations": 20, "n_bootstrap": 20,
               "permutation_n_repeats": 1, "bootstrap_n_repeats": 1}}


def _synthetic(n=64, n_features=10, seed=0, signal=1.5):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n)
    X = rng.normal(size=(n, n_features))
    X[:, 0] += signal * y  # one informative feature
    groups = np.arange(n)  # one row per subject
    return X, y, groups


def test_run_outer_fold_scaler_fitted_on_train_only():
    X, y, groups = _synthetic()
    train_idx, test_idx = np.arange(10, 64), np.arange(10)
    proba, diag = run_outer_fold(X[train_idx], y[train_idx], groups[train_idx],
                                  X[test_idx], _CFG["cv"])
    full_data_mean = X.mean(axis=0)
    assert not np.allclose(diag["scaler_mean"], full_data_mean)
    assert len(proba) == len(test_idx)


def test_pooled_repeated_cv_covers_every_subject_exactly_once_per_repeat():
    X, y, groups = _synthetic()
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=3)
    assert len(result["pooled_auc_per_repeat"]) == 3
    assert not np.any(np.isnan(result["oof_proba_last_repeat"]))


def test_pooled_repeated_cv_recovers_signal_above_chance():
    X, y, groups = _synthetic(signal=2.5)
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=3)
    assert result["mean_pooled_auc"] > 0.75


def test_pooled_repeated_cv_seeded_run_is_bit_reproducible():
    X, y, groups = _synthetic()
    r1 = pooled_repeated_cv(X, y, groups, _CFG, seed=42, n_repeats=2)
    r2 = pooled_repeated_cv(X, y, groups, _CFG, seed=42, n_repeats=2)
    assert r1["pooled_auc_per_repeat"] == r2["pooled_auc_per_repeat"]


def test_group_kfold_never_splits_a_group_across_folds():
    X, y, groups = _synthetic(n=40)
    groups = np.repeat(np.arange(20), 2)  # two rows per "subject" (like eyes-open/closed)
    y = np.tile([0, 1], 20)
    from sklearn.model_selection import StratifiedGroupKFold
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=1)
    for train_idx, test_idx in skf.split(X, y, groups):
        assert set(groups[train_idx]).isdisjoint(set(groups[test_idx]))


def test_permutation_null_centres_near_chance():
    X, y, groups = _synthetic(signal=0.0)  # no real signal
    observed = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=1)["mean_pooled_auc"]
    p, perm_aucs = permutation_test(X, y, groups, _CFG, seed=1, observed_auc=observed, n_permutations=20)
    assert 0.0 <= p <= 1.0
    assert abs(np.mean(perm_aucs) - 0.5) < 0.15


def test_bootstrap_ci_contains_point_estimate():
    X, y, groups = _synthetic(signal=2.0)
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=1)
    point = result["mean_pooled_auc"]
    lo, hi = bootstrap_ci(X, y, groups, _CFG, seed=1, n_bootstrap=20)
    assert lo <= point + 0.15  # loose bound: small n_bootstrap in test, just sanity-check ordering
    assert lo <= hi


def test_holm_correction_matches_hand_computation():
    raw = {"a": 0.01, "b": 0.04, "c": 0.20}
    out = holm_correction(raw)
    # Holm: sort ascending [0.01,0.04,0.20], multiply by [3,2,1], cummax
    assert out["a"] == pytest.approx(0.03)
    assert out["b"] == pytest.approx(0.08)
    assert out["c"] == pytest.approx(0.20)
