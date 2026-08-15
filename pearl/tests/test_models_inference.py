from unittest.mock import MagicMock, patch

import numpy as np

from pearl_models.inference import score_bids_subject


def test_score_bids_subject_includes_disclaimer_and_status():
    with patch("pearl_models.inference._preprocess_subject") as mock_pp, \
         patch("pearl_models.inference._extract_features") as mock_feat, \
         patch("pearl_models.inference._load_model") as mock_model:
        mock_pp.return_value = {"n_bad_channels": 2, "n_ica_removed": 10, "artifact_frac": 0.05,
                                 "iaf_hz": 10.0, "alpha_peak_height_db": 5.0}
        mock_feat.return_value = [[0.1] * 18]
        fake_pipeline = MagicMock()
        fake_pipeline.predict_proba.return_value = np.array([[0.4, 0.6]])
        mock_model.return_value = (
            {"training_qc_ranges": {"n_bad_channels": (0, 10), "n_ica_removed": (0, 30),
                                    "artifact_frac": (0, 0.5)},
             "run_id": "test-run", "git_sha": "abc123", "feature_columns": ["f"] * 18},
            fake_pipeline,
        )
        result = score_bids_subject("fake_bids_dir", "sub-01", "fake_model_path")
    assert "disclaimer" in result
    assert "not validated" in result["disclaimer"].lower()
    assert result["actionable"] is False
    assert result["status"] in {"scored", "cannot_score"}


def test_score_bids_subject_refuses_ood_input():
    with patch("pearl_models.inference._preprocess_subject") as mock_pp, \
         patch("pearl_models.inference._extract_features") as mock_feat, \
         patch("pearl_models.inference._load_model") as mock_model:
        mock_pp.return_value = {"n_bad_channels": 99, "n_ica_removed": 10, "artifact_frac": 0.05,
                                 "iaf_hz": 10.0, "alpha_peak_height_db": 5.0}
        mock_model.return_value = (
            {"training_qc_ranges": {"n_bad_channels": (0, 10), "n_ica_removed": (0, 30),
                                    "artifact_frac": (0, 0.5)},
             "run_id": "test-run", "git_sha": "abc123", "feature_columns": ["f"] * 18},
            object(),
        )
        result = score_bids_subject("fake_bids_dir", "sub-99", "fake_model_path")
    assert result["status"] == "cannot_score"
    mock_feat.assert_not_called()
