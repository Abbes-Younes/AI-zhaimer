from unittest.mock import patch

import numpy as np
import pandas as pd

from pearl_models.pipeline import assemble_cv_predictions, assemble_cv_metrics, write_outputs


def test_assemble_cv_predictions_shape():
    oof = np.array([0.1, 0.9, 0.4])
    subjects = ["sub-01", "sub-02", "sub-03"]
    y = np.array([0, 1, 0])
    df = assemble_cv_predictions("features_only", subjects, y, oof, repeat=0)
    assert list(df.columns) >= ["analysis", "subject", "y_true", "oof_proba", "repeat"]
    assert len(df) == 3


def test_assemble_cv_metrics_one_row_per_analysis_and_reference():
    results = {
        "features_only": {"auc": 0.5, "ci": (0.3, 0.7), "p_value": 0.5, "n_subjects_used": 64,
                          "reference_lines": {"chance": 0.5, "qc_only_auc": 0.545,
                                              "published_benchmark_auc": 0.58}},
    }
    df = assemble_cv_metrics(results)
    assert "features_only" in df["analysis"].values
    assert set(df.columns) >= {"analysis", "auc", "ci_low", "ci_high", "p_value", "n_subjects_used"}


def test_write_outputs_creates_expected_files(tmp_path):
    predictions = pd.DataFrame({"analysis": ["a"], "subject": ["sub-01"], "y_true": [1],
                                "oof_proba": [0.6], "repeat": [0]})
    metrics = pd.DataFrame({"analysis": ["a"], "auc": [0.5], "ci_low": [0.3], "ci_high": [0.7],
                            "p_value": [0.5], "n_subjects_used": [64]})
    stability = pd.DataFrame({"feature": ["f1"], "selection_frequency": [1.0],
                              "sign_consistency": [0.9], "stable": [True]})
    write_outputs(predictions, metrics, stability, out_dir=tmp_path, run_id="testrun",
                  git_sha_value="abc123", gate_verdict="NULL")
    assert (tmp_path / "cv_predictions.csv").exists()
    assert (tmp_path / "cv_metrics.csv").exists()
    assert (tmp_path / "feature_stability.csv").exists()
    assert (tmp_path / "_meta.json").exists()
