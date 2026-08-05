"""Tests for report rendering and run_id assertions (phase_0,5.md Tasks 4/7/9)."""
from __future__ import annotations

import json

import pytest

from pearl_audit import report
from pearl_audit.paths import (
    RunIdMismatchError,
    set_run_id,
    artifact_dir,
    stamp_run_meta,
)


def _minimal_recon_summary(**overrides) -> dict:
    summary = {
        "mismatch_count": 0,
        "missing_from_tsv": [],
        "sub_69": {"present_in_tsv": False, "status": "absent_from_tsv"},
        "e4_homozygotes_in_A_P_plus": 2,
        "e4_homozygotes_claim": 2,
        "cohort": [{"subject": "sub-01", "in_client_list": True,
                    "in_participants_tsv": True, "has_any_eeg": True, "final_include": True}],
        "total_subjects_in_tsv": 192,
        "genetic_cohort_only_count": 113,
        "analysis_cohort_count": 79,
    }
    summary.update(overrides)
    return summary


class TestVerdictLogic:
    def test_verdict_proceed_when_zero_blocking(self):
        verdict, text = report._compute_verdict(
            _minimal_recon_summary(), {"thresholds": {"max_mismatches": 2}}
        )
        assert verdict == "proceed"
        assert "sub-69" in text

    def test_verdict_stop_when_blocking_exceeds(self):
        verdict, text = report._compute_verdict(
            _minimal_recon_summary(mismatch_count=5), {"thresholds": {"max_mismatches": 2}}
        )
        assert verdict == "stop"

    def test_verdict_text_matches_sub69_state(self):
        # absent → verdict text must say sub-69 is not among genotyped participants
        verdict, text = report._compute_verdict(
            _minimal_recon_summary(), {"thresholds": {"max_mismatches": 2}}
        )
        assert "not among the genotyped participants" in text

    def test_verdict_text_when_sub69_present(self):
        verdict, text = report._compute_verdict(
            _minimal_recon_summary(sub_69={"present_in_tsv": True}),
            {"thresholds": {"max_mismatches": 2}},
        )
        assert verdict == "proceed"


class TestRunIdAssertion:
    def test_mismatched_run_id_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report, "artifact_dir", lambda: tmp_path)
        set_run_id("run-B")
        try:
            (tmp_path / "_meta.json").write_text(json.dumps({"run_id": "run-A"}), encoding="utf-8")
            with pytest.raises(RunIdMismatchError, match="run-A"):
                report._assert_same_run_id()
        finally:
            set_run_id(None)

    def test_missing_meta_raises_when_run_active(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report, "artifact_dir", lambda: tmp_path)
        set_run_id("run-B")
        try:
            with pytest.raises(RunIdMismatchError):
                report._assert_same_run_id()
        finally:
            set_run_id(None)

    def test_matching_run_id_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report, "artifact_dir", lambda: tmp_path)
        set_run_id("run-A")
        try:
            (tmp_path / "_meta.json").write_text(json.dumps({"run_id": "run-A"}), encoding="utf-8")
            report._assert_same_run_id()  # must not raise
        finally:
            set_run_id(None)

    def test_no_run_skips_assertion(self):
        # no active run → assertion is skipped, even with no meta file
        report._assert_same_run_id()


class TestMarkdownRender:
    def test_sub69_line_in_markdown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report, "AUDIT_YAML", tmp_path / "audit.yaml")
        (tmp_path / "audit.yaml").write_text("dataset:\n  accession: ds004796\n", encoding="utf-8")
        md = report._generate_markdown({
            "reconciliation": {
                "rows": [],
                "mismatch_count": 0,
                "missing_from_tsv": [],
                "sub_69": {"present_in_tsv": False},
                "e4_homozygotes_in_A_P_plus": 2,
                "e4_homozygotes_claim": 2,
                "cohort": [],
                "total_subjects_in_tsv": 192,
                "genetic_cohort_only_count": 113,
                "analysis_cohort_count": 79,
            },
            "inventory": {"effective_n_table": [], "missingness_table": [],
                          "verified_known_missing": {}},
            "confounds": {"framing_results": {}},
            "size_survey": {},
            "download_plan": {"scopes": {}, "derivatives_per_scope_gb": {},
                              "recommendation": "B_rest_msit", "manifest_path": "x",
                              "sidecar_params": {}},
            "fetch": {"total_bytes": 0, "total_files": 0},
            "audit_config": {"thresholds": {"max_mismatches": 2}},
            "run_id": "test",
            "verdict": "proceed",
            "verdict_text": "PROCEED: all 79 analysis-cohort subjects reconcile. sub-69 is not among the genotyped participants.",
        })
        assert "not among the genotyped participants" in md
        assert "## 6. Open Questions & Assumptions" in md
        assert "## 0. Cohort Definition" in md
