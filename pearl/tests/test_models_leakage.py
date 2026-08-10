import numpy as np

from pearl_models.leakage import (
    check_no_subject_leakage, check_permutation_null_centred, run_full_checklist,
)


def test_check_no_subject_leakage_passes_for_unique_groups():
    groups = np.arange(64)
    cfg = {"cv": {"n_splits": 5, "inner_n_splits": 3, "seed": 1}}
    assert check_no_subject_leakage(groups, cfg, seed=1) is True


def test_check_no_subject_leakage_passes_for_paired_groups():
    groups = np.repeat(np.arange(32), 2)
    cfg = {"cv": {"n_splits": 5, "inner_n_splits": 3, "seed": 1}}
    assert check_no_subject_leakage(groups, cfg, seed=1) is True


def test_check_permutation_null_centred_true_near_half():
    perm_aucs = np.random.default_rng(0).normal(0.5, 0.05, size=200)
    assert check_permutation_null_centred(perm_aucs) is True


def test_check_permutation_null_centred_false_when_elevated():
    perm_aucs = np.random.default_rng(0).normal(0.75, 0.05, size=200)
    assert check_permutation_null_centred(perm_aucs) is False


def test_run_full_checklist_returns_documented_manual_items():
    result = {"perm_aucs": np.random.default_rng(0).normal(0.5, 0.05, size=200)}
    groups = np.arange(64)
    cfg = {"cv": {"n_splits": 5, "inner_n_splits": 3, "seed": 1}}
    out = run_full_checklist(result, result["perm_aucs"], groups, cfg)
    assert out["no_subject_leakage"] is True
    assert out["permutation_null_centred"] is True
    assert "manual_review_notes" in out
