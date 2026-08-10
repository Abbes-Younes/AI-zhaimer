from pearl_models.benchmark import run_msit_benchmark
from pearl_models.reports import render_benchmark_reproduction


def test_run_msit_benchmark_returns_expected_keys():
    cfg = {"cv": {"n_splits": 5, "n_repeats": 2, "inner_n_splits": 3, "seed": 1,
                  "c_grid": [0.1, 1.0, 10.0], "n_permutations": 10, "n_bootstrap": 10,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1}}
    result = run_msit_benchmark(cfg)
    assert set(result) >= {"auc", "ci", "p_value", "n_subjects_used", "verdict"}
    assert result["verdict"] in {"near_benchmark", "at_chance", "other"}
    assert 0.0 <= result["auc"] <= 1.0


def test_render_benchmark_reproduction_is_verdict_first():
    result = {"auc": 0.55, "ci": (0.4, 0.7), "p_value": 0.2, "n_subjects_used": 55,
              "verdict": "near_benchmark"}
    text = render_benchmark_reproduction(result)
    assert "VERDICT" in text.strip().splitlines()[0].upper()
    assert "0.55" in text
