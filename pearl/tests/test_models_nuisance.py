from pearl_models.nuisance import run_nuisance_only
from pearl_models.data import load_pswt_features


def test_run_nuisance_only_returns_expected_keys():
    cfg = {"cv": {"n_splits": 5, "n_repeats": 2, "inner_n_splits": 3, "seed": 1,
                  "c_grid": [0.1, 1.0, 10.0], "n_permutations": 10, "n_bootstrap": 10,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1}}
    result = run_nuisance_only(cfg)
    assert set(result) >= {"auc", "ci", "p_value", "n_subjects_used", "verdict"}
    assert 0.0 <= result["auc"] <= 1.0


def test_run_nuisance_only_restricted_to_frozen_64_subject_cohort():
    """Regression: run_nuisance_only must use the same population as the
    PSWT/baseline feature analyses (64 subjects), not the full 79-subject
    participants.tsv/qc_metrics.csv population — otherwise it isn't a
    comparable reference line."""
    cfg = {"cv": {"n_splits": 5, "n_repeats": 1, "inner_n_splits": 3, "seed": 1,
                  "c_grid": [0.1, 1.0, 10.0], "n_permutations": 3, "n_bootstrap": 3,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1}}
    result = run_nuisance_only(cfg)
    assert result["n_subjects_used"] == len(load_pswt_features())
