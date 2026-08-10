import pandas as pd

from pearl_models.reports import render_results


_CFG = {
    "reference_lines": {"chance": 0.5, "qc_only_auc": 0.545, "qc_only_ci": [0.435, 0.800],
                        "published_benchmark_auc": 0.58},
    "positive_controls": {"eyes_open_closed_auc_floor": 0.80, "sex_auc_reference_floor": 0.65},
}


def _analysis(auc, p=0.5, n=64):
    return {"auc": auc, "ci": (auc - 0.1, auc + 0.1), "p_value": p,
            "pooled_auc_per_repeat": [auc] * 3, "n_subjects_used": n}


def test_render_results_has_all_eight_sections():
    primary = {
        "features_only": _analysis(0.474, p=0.577),
        "features_plus_nuisance": _analysis(0.517, p=0.408),
        "nuisance_only": _analysis(0.523, p=0.395),
    }
    secondary = {
        "baseline_rest": {**_analysis(0.375, p=0.883), "p_value_holm": 1.0},
        "pswt_plus_baseline_rest": {**_analysis(0.513, p=0.418), "p_value_holm": 1.0},
        "baseline_msit": {**_analysis(0.459, p=0.580, n=55), "p_value_holm": 1.0},
    }
    eo_result = {"auc": 0.830, "ci": (0.710, 0.898), "p_value": 0.005}
    sex_result = {"auc": 0.486, "ci": (0.301, 0.745), "p_value": 0.627}
    benchmark_result = {"auc": 0.459, "verdict": "at_chance"}
    feature_stability = pd.DataFrame([
        {"feature": "f1", "selection_frequency": 1.0, "sign_consistency": 0.9, "stable": True},
        {"feature": "f2", "selection_frequency": 0.0, "sign_consistency": float("nan"), "stable": False},
    ])
    leakage_result = {"perm_aucs_mean": 0.492}

    text = render_results(primary, secondary, eo_result, sex_result, benchmark_result,
                           feature_stability, leakage_result, _CFG)

    assert "VERDICT" in text.strip().splitlines()[0].upper()
    for heading in ["## 1. Verdict", "## 2. All four reference lines", "## 3. Positive control",
                    "## 4. Benchmark reproduction", "## 5. Secondary comparisons",
                    "## 6. Feature stability", "## 7. Limitations",
                    "## 8. What would be needed"]:
        assert heading in text, f"missing section: {heading}"
    assert "0.474" in text
