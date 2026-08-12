"""Track B benchmark_diagnostic scope lock (phase_5_stage2.md §3,
mirrors test_models_control_diagnostic.py's ALLOWED_TARGETS pattern --
here the lock is structural: no parameter exists to redirect the feature
source or target, so the test asserts that shape rather than a runtime
ValueError branch)."""
from __future__ import annotations

import inspect

import pandas as pd

from pearl_features.benchmark_diagnostic import (
    MSIT_TFA_PREFIX,
    PRIOR_SIMPLE_BASELINE_AUC,
    PUBLISHED_BENCHMARK_AUC,
    _determine_verdict,
    _load_msit_tfa_matrix,
    run,
)


def test_determine_verdict_requires_significance_not_just_a_higher_point_estimate():
    # phase_4.md's own self-caught lesson: a point estimate above the prior
    # baseline with a non-significant p-value must NOT read as "improved".
    assert _determine_verdict(observed=0.546, p_value=0.315) == "not_significant"
    assert _determine_verdict(observed=0.55, p_value=0.01) == "improved"
    assert _determine_verdict(observed=0.30, p_value=0.01) == "worse"
    assert _determine_verdict(observed=0.30, p_value=0.5) == "not_significant"


def test_run_has_no_target_or_feature_source_parameter():
    params = set(inspect.signature(run).parameters)
    # only tuning knobs for the CV procedure itself are allowed -- nothing
    # that could point this module at a different label framing or a
    # different feature file/column set.
    assert params <= {"n_splits", "n_repeats", "n_permutations", "seed"}


def test_msit_tfa_prefix_excludes_sternberg_columns(tmp_path, monkeypatch):
    # Craft a features_tfa.csv with both msit_ and sternberg_ columns and
    # confirm only msit_tfa_* is ever selected, even though the file has
    # other label-adjacent-looking columns sitting right next to it.
    df = pd.DataFrame({
        "msit_tfa_alpha_mean": [0.1, 0.2, 0.3, 0.4],
        "sternberg_encoding_tfa_alpha_mean": [0.9, 0.8, 0.7, 0.6],
    }, index=["sub-01", "sub-02", "sub-03", "sub-04"])
    df.to_csv(tmp_path / "features_tfa.csv")

    class _FakePaths:
        FEATURES_DIR = tmp_path

    monkeypatch.setitem(__import__("sys").modules, "pearl_features.paths", _FakePaths)
    monkeypatch.setattr(
        "pearl_features.confound_gate.load_group_map",
        lambda: {"sub-01": "N", "sub-02": "N", "sub-03": "A_P_plus", "sub-04": "A_P_minus"})

    X, y, cols, n_before = _load_msit_tfa_matrix()
    assert cols == ["msit_tfa_alpha_mean"]
    assert "sternberg_encoding_tfa_alpha_mean" not in cols
    assert n_before == 4
    assert X.shape == (4, 1)


def test_constants_match_declared_frozen_plan_values():
    assert MSIT_TFA_PREFIX == "msit_tfa_"
    assert PUBLISHED_BENCHMARK_AUC == 0.58
    assert PRIOR_SIMPLE_BASELINE_AUC == 0.459
