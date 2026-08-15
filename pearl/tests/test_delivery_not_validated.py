"""phase_7.md §1 (Task B) and §2 (Task C).

The shipped artefact is a reproducibility reference, not a predictor. The
model does not detect its target: its own validation retracted the only
positive result it ever produced, and Phase 6 established that the null is
real rather than an artifact of an insensitive measurement.

Every surface that emits a score must therefore say so, unmissably. These
tests pin that so a future change cannot quietly re-present the output as
actionable.
"""
from __future__ import annotations

import numpy as np

from pearl_models.delivery import _DISCLAIMER, score_subject


class _StubPipeline:
    def predict_proba(self, X):
        return np.array([[0.4, 0.6]])


def test_disclaimer_states_the_model_was_not_validated():
    text = _DISCLAIMER.lower()
    assert "not validated" in text, "the disclaimer must say the model was not validated"
    assert "no demonstrated predictive" in text or "no demonstrated meaning" in text, (
        "the disclaimer must state the output carries no demonstrated predictive meaning")


def test_disclaimer_is_not_merely_a_research_score_caveat():
    """The previous wording ('a research score, not a risk assessment') implied
    the number meant something, just not clinically. It does not: the model
    failed its own validation. Guard against regressing to that framing."""
    text = _DISCLAIMER.lower()
    assert not text.strip().startswith("research pipeline output"), (
        "disclaimer regressed to the pre-Phase-7 'research score' framing")


def test_scored_output_carries_the_not_validated_disclaimer():
    result = score_subject(_StubPipeline(), qc_row={}, feature_row=np.zeros((1, 3)),
                            training_qc_ranges={})
    assert result["status"] == "scored"
    assert "not validated" in result["disclaimer"].lower()


def test_scored_output_is_explicitly_flagged_not_actionable():
    """phase_7.md §2: no code path may present a score as actionable."""
    result = score_subject(_StubPipeline(), qc_row={}, feature_row=np.zeros((1, 3)),
                            training_qc_ranges={})
    assert result.get("actionable") is False, (
        "a scored result must carry an explicit machine-readable not-actionable flag")


def test_cannot_score_path_still_reports_a_reason():
    result = score_subject(_StubPipeline(), qc_row={"n_bad_channels": 99},
                            feature_row=np.zeros((1, 3)),
                            training_qc_ranges={"n_bad_channels": (0, 10)})
    assert result["status"] == "cannot_score"
    assert result["reason"]
