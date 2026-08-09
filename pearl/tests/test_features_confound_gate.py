import numpy as np
import pandas as pd

from pearl_features.confound_gate import (
    association_tests, exclusion_status_association, CONTINUOUS_METRICS,
)


def _fake_qc(n_per_group=15, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    groups = {}
    subj = 0
    for g, shift in [("N", 0.0), ("A_P_minus", 0.0), ("A_P_plus", 0.0)]:
        for _ in range(n_per_group):
            subj += 1
            sid = f"sub-{subj:02d}"
            groups[sid] = g
            rows.append({
                "subject": sid, "task": "rest",
                "n_bad_channels": rng.integers(0, 5) + shift,
                "occipital_bads": rng.integers(0, 2),
                "n_ica_removed": rng.integers(5, 20),
                "line_noise_index_before": rng.normal(5, 1),
                "line_noise_index_after": rng.normal(0.01, 0.005),
                "artifact_frac": rng.uniform(0, 0.1),
                "iaf_hz": rng.normal(10, 0.5),
                "alpha_peak_height_db": rng.normal(5, 2),
                "verdict": "pass",
            })
    return pd.DataFrame(rows), groups


def test_association_tests_returns_one_row_per_metric_with_fdr():
    qc, groups = _fake_qc()
    out = association_tests(qc, groups, CONTINUOUS_METRICS)
    assert list(out["metric"]) == CONTINUOUS_METRICS
    assert (out["p_fdr"] >= out["p_value"] - 1e-12).all()  # BH-FDR never < raw p
    assert out["p_value"].between(0, 1).all()


def test_association_tests_detects_a_real_group_difference():
    qc, groups = _fake_qc()
    # inject a strong, real group-dependent shift into one metric
    qc.loc[qc["subject"].map(groups) == "A_P_plus", "n_bad_channels"] += 20
    out = association_tests(qc, groups, CONTINUOUS_METRICS)
    row = out[out["metric"] == "n_bad_channels"].iloc[0]
    assert row["p_value"] < 0.01


def test_exclusion_status_association_runs_fisher():
    per_task = pd.DataFrame({
        "subject": [f"sub-{i:02d}" for i in range(1, 11)],
        "task": ["rest"] * 10,
        "included": [True, True, True, False, False, True, True, True, False, True],
    })
    groups = {f"sub-{i:02d}": ("N" if i <= 5 else "A_P_plus") for i in range(1, 11)}
    result = exclusion_status_association(per_task, groups)
    assert 0.0 <= result["p_value"] <= 1.0
    assert "odds_ratio" in result


from pearl_features.confound_gate import qc_only_auc


def test_qc_only_auc_near_chance_on_random_labels():
    qc, groups = _fake_qc(n_per_group=20, seed=1)
    binary_map = {s: (0 if g == "N" else 1) for s, g in groups.items()}
    result = qc_only_auc(qc, binary_map, CONTINUOUS_METRICS,
                          n_splits=3, n_repeats=1, n_permutations=20, seed=1)
    assert 0.3 <= result["mean_auc"] <= 0.7
    assert result["verdict"] in {"proceed", "proceed_with_baseline"}
    assert 0.0 <= result["p_value"] <= 1.0


def test_qc_only_auc_escalates_when_metric_is_a_perfect_group_proxy():
    qc, groups = _fake_qc(n_per_group=20, seed=2)
    binary_map = {s: (0 if g == "N" else 1) for s, g in groups.items()}
    qc["n_bad_channels"] = qc["subject"].map(lambda s: 0.0 if binary_map[s] == 0 else 100.0)
    result = qc_only_auc(qc, binary_map, CONTINUOUS_METRICS,
                          n_splits=3, n_repeats=1, n_permutations=20, seed=2)
    assert result["mean_auc"] > 0.9
    assert result["verdict"] == "escalate"


import pandas as pd

from pearl_features.confound_gate_report import render


def test_render_report_is_verdict_first_markdown():
    full = pd.DataFrame({"metric": ["n_bad_channels"], "test": ["kruskal-wallis"],
                          "statistic": [1.0], "p_value": [0.5], "p_fdr": [0.5],
                          "effect_size": [0.0], "ci_low": [0.0], "ci_high": [0.1]})
    gate_result = {"mean_auc": 0.51, "ci_low": 0.45, "ci_high": 0.58,
                   "p_value": 0.42, "verdict": "proceed"}
    exclusion_assoc = {"odds_ratio": 1.1, "p_value": 0.8}
    text = render(full, full, exclusion_assoc, gate_result)
    first_line = text.strip().splitlines()[0]
    assert "PROCEED" in first_line.upper() or "VERDICT" in first_line.upper()
    assert "0.51" in text
