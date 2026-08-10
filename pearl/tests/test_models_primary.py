import numpy as np
import pandas as pd

from pearl_models.primary import run_one_analysis, feature_stability


_CFG = {"cv": {"n_splits": 5, "n_repeats": 2, "inner_n_splits": 3, "seed": 1,
               "c_grid": [0.1, 1.0, 10.0], "n_permutations": 10, "n_bootstrap": 10,
               "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
        "reference_lines": {"chance": 0.5, "qc_only_auc": 0.545,
                             "qc_only_ci": [0.435, 0.800], "published_benchmark_auc": 0.58}}


def _synthetic(n=64, n_features=10, seed=0, signal=2.0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n)
    X = rng.normal(size=(n, n_features))
    X[:, 0] += signal * y
    groups = np.arange(n)
    return X, y, groups


def test_run_one_analysis_tags_name_and_reference_lines():
    X, y, groups = _synthetic()
    result = run_one_analysis("features_only", X, y, groups, _CFG, seed=1)
    assert result["name"] == "features_only"
    assert result["reference_lines"] == _CFG["reference_lines"]
    assert 0.0 <= result["auc"] <= 1.0


def test_feature_stability_recovers_known_frequencies():
    # 2 repeats x 2 folds = 4 (repeat, fold) combinations
    fold_diagnostics = [
        [{"selected": np.array([True, False, True]), "coef": np.array([1.0, 0.0, -1.0])},
         {"selected": np.array([True, False, False]), "coef": np.array([1.0, 0.0, 0.5])}],
        [{"selected": np.array([True, True, True]), "coef": np.array([-1.0, 1.0, -1.0])},
         {"selected": np.array([False, False, True]), "coef": np.array([0.0, 0.0, 1.0])}],
    ]
    df = feature_stability(fold_diagnostics, ["f0", "f1", "f2"])
    df = df.set_index("feature")
    # f0 selected in 3/4 folds
    assert df.loc["f0", "selection_frequency"] == 3 / 4
    # f1 selected in 1/4 folds
    assert df.loc["f1", "selection_frequency"] == 1 / 4
    # f2 selected in 3/4 folds (rep0/fold0, rep1/fold0, rep1/fold1), signs -1,-1,1 -> not unanimous
    assert df.loc["f2", "selection_frequency"] == 3 / 4
    assert df.loc["f2", "sign_consistency"] < 1.0
    assert set(df.columns) >= {"selection_frequency", "sign_consistency", "stable"}
