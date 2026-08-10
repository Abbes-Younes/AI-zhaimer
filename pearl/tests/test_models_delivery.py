import pytest

from pearl_models.delivery import is_out_of_distribution, score_subject, write_model_card


def test_is_out_of_distribution_flags_metric_outside_training_range():
    ranges = {"n_bad_channels": (0, 10)}
    ood, reason = is_out_of_distribution({"n_bad_channels": 15}, ranges)
    assert ood is True
    assert "n_bad_channels" in reason


def test_is_out_of_distribution_false_within_range():
    ranges = {"n_bad_channels": (0, 10)}
    ood, reason = is_out_of_distribution({"n_bad_channels": 5}, ranges)
    assert ood is False


def test_score_subject_refuses_ood_without_calling_model():
    class _ExplodingPipeline:
        def predict_proba(self, X):
            raise AssertionError("must not be called for OOD input")

    ranges = {"n_bad_channels": (0, 10)}
    result = score_subject(_ExplodingPipeline(), {"n_bad_channels": 99}, None, ranges)
    assert result["status"] == "cannot_score"


def test_write_model_card_fails_on_missing_required_field(tmp_path):
    incomplete = {"run_id": "x", "git_sha": None}
    with pytest.raises(ValueError):
        write_model_card(incomplete, tmp_path / "model_card.md")
