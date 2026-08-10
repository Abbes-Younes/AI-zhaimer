import numpy as np

from pearl_models.positive_controls import run_sex_control
from pearl_models.data import load_pswt_features, load_nuisance


def test_run_sex_control_returns_expected_keys():
    cfg = {"cv": {"n_splits": 5, "n_repeats": 2, "inner_n_splits": 3, "seed": 1,
                  "c_grid": [0.1, 1.0, 10.0], "n_permutations": 10, "n_bootstrap": 10,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
           "positive_controls": {"sex_auc_reference_floor": 0.65}}
    pswt = load_pswt_features()
    nuisance = load_nuisance()
    result = run_sex_control(cfg, pswt, nuisance)
    assert set(result) >= {"auc", "ci", "p_value", "verdict"}
    assert result["verdict"] in {"pass", "fail"}
    assert 0.0 <= result["auc"] <= 1.0
