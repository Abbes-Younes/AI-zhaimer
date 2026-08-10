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


from pearl_models.reports import render_positive_controls


def test_render_positive_controls_is_verdict_first():
    eo = {"auc": 0.9, "ci": (0.8, 0.95), "p_value": 0.001, "n_subjects_used": 60,
          "n_dropped": 4, "verdict": "pass"}
    sex = {"auc": 0.7, "ci": (0.55, 0.85), "p_value": 0.01, "n_subjects_used": 64, "verdict": "pass"}
    text = render_positive_controls(eo, sex)
    first_line = text.strip().splitlines()[0].upper()
    assert "VERDICT" in first_line
    assert "0.9" in text


def test_render_positive_controls_flags_stop_when_1a_below_floor():
    eo = {"auc": 0.6, "ci": (0.4, 0.75), "p_value": 0.2, "n_subjects_used": 60,
          "n_dropped": 4, "verdict": "fail"}
    sex = {"auc": 0.7, "ci": (0.55, 0.85), "p_value": 0.01, "n_subjects_used": 64, "verdict": "pass"}
    text = render_positive_controls(eo, sex)
    assert "STOP" in text.strip().splitlines()[0].upper()


def test_render_positive_controls_flags_caveat_when_1b_at_chance():
    eo = {"auc": 0.9, "ci": (0.8, 0.95), "p_value": 0.001, "n_subjects_used": 60,
          "n_dropped": 4, "verdict": "pass"}
    sex = {"auc": 0.5, "ci": (0.3, 0.7), "p_value": 0.6, "n_subjects_used": 64, "verdict": "fail"}
    text = render_positive_controls(eo, sex)
    assert "PROCEED_WITH_CAVEAT" in text.strip().splitlines()[0].upper()
