import numpy as np
import pytest

from pearl_models.control_diagnostic import run_rung, ALLOWED_TARGETS


_CFG = {"cv": {"n_splits": 2, "n_repeats": 1, "inner_n_splits": 2, "seed": 1,
               "c_grid": [1.0], "n_permutations": 2, "n_bootstrap": 2,
               "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
        "reference_lines": {}}


def test_run_rung_raises_on_primary_target():
    X = np.zeros((10, 3)); y = np.zeros(10, dtype=int); groups = np.arange(10)
    with pytest.raises(ValueError, match="binary_risk_vs_none"):
        run_rung("rung1", "binary_risk_vs_none", X, y, groups, _CFG)


def test_run_rung_raises_on_any_other_non_sanctioned_target():
    X = np.zeros((10, 3)); y = np.zeros(10, dtype=int); groups = np.arange(10)
    for bad_target in ["A_P_plus", "multiclass_3", "binary_high_vs_rest", "genotype"]:
        with pytest.raises(ValueError):
            run_rung("rung1", bad_target, X, y, groups, _CFG)


def test_run_rung_allows_sex():
    X = np.random.default_rng(0).normal(size=(10, 3))
    y = np.array([0, 1] * 5)
    groups = np.arange(10)
    result = run_rung("rung1", "sex", X, y, groups, _CFG)
    assert result["rung"] == "rung1"
    assert "binary_risk_vs_none" not in ALLOWED_TARGETS
    assert ALLOWED_TARGETS == {"sex"}


def test_run_ladder_stopped_at_uses_permutation_p_value_not_ci():
    """Regression: stopped_at must be driven by permutation p < alpha (the
    project-wide significance convention), not an unrelated CI-lower-bound
    heuristic -- a rung with p=0.013 but a CI crossing 0.5 (typical at n=64)
    must still count as clearly above chance."""
    from unittest.mock import patch
    from pearl_models.control_diagnostic import run_ladder

    rung1 = {"auc": 0.693, "ci": (0.402, 0.829), "p_value": 0.013, "rung": "rung1_baseline"}
    rung2 = {"auc": 0.556, "ci": (0.336, 0.764), "p_value": 0.265, "rung": "rung2_pswt_plus_baseline"}
    rung3 = {"auc": 0.685, "ci": (0.418, 0.840), "p_value": 0.024, "rung": "rung3_per_channel"}

    with patch("pearl_models.control_diagnostic.run_rung1_baseline", return_value=rung1), \
         patch("pearl_models.control_diagnostic.run_rung2_pswt_plus_baseline", return_value=rung2), \
         patch("pearl_models.control_diagnostic.run_rung3_per_channel", return_value=rung3):
        result = run_ladder(_CFG, {})
    assert result["stopped_at"] == "rung1_baseline"


def test_render_control_diagnostic_is_verdict_first_and_reports_all_rungs():
    from pearl_models.reports import render_control_diagnostic

    ladder_result = {
        "rung1": {"auc": 0.693, "ci": (0.402, 0.829), "p_value": 0.013},
        "rung2": {"auc": 0.556, "ci": (0.336, 0.764), "p_value": 0.265},
        "rung3": {"auc": 0.685, "ci": (0.418, 0.840), "p_value": 0.024},
        "stopped_at": "rung1_baseline",
    }
    text = render_control_diagnostic(ladder_result)
    assert "VERDICT" in text.strip().splitlines()[0].upper()
    assert "0.693" in text and "0.556" in text and "0.685" in text
    assert "negative result for the method" in text
