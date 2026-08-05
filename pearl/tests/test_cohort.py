"""Tests for the cohort reframe and strict column resolution (phase_0,5.md Tasks 2/3/9)."""
from __future__ import annotations

import pandas as pd
import pytest

from pearl_audit.reconcile_groups import (
    build_cohort_definition,
    RECONCILED,
    MISMATCH,
    GENETIC_COHORT_ONLY,
    MISSING_FROM_TSV,
    BLOCKING_STATUSES,
    _resolve_columns,
)


class TestCohortDefinition:
    def test_192_vs_79_framing(self):
        # 192 genotyped, 79 in client list with EEG
        tsv = {f"sub-{i:03d}" for i in range(1, 201)}  # includes gaps? use exact set
        tsv = {f"sub-{i:03d}" for i in range(1, 201) if i not in (69, 103)}
        client = {f"sub-{i:03d}" for i in range(1, 81) if i != 69}
        eeg = client  # all client subjects have EEG
        cohort = build_cohort_definition(tsv, client, eeg)
        assert len(cohort) == len(tsv | client)
        included = cohort[cohort["final_include"]]
        assert len(included) == 79
        assert "sub-069" not in set(included["subject"])

    def test_genetic_only_not_included(self):
        tsv = {"sub-01", "sub-150"}
        client = {"sub-01"}
        cohort = build_cohort_definition(tsv, client, {"sub-01"})
        row = cohort[cohort["subject"] == "sub-150"].iloc[0]
        assert bool(row["in_client_list"]) is False
        assert bool(row["in_participants_tsv"]) is True
        assert bool(row["final_include"]) is False

    def test_missing_from_tsv_not_included(self):
        tsv = {"sub-01"}
        client = {"sub-01", "sub-99"}
        cohort = build_cohort_definition(tsv, client, {"sub-01"})
        row = cohort[cohort["subject"] == "sub-99"].iloc[0]
        assert bool(row["in_client_list"]) is True
        assert bool(row["in_participants_tsv"]) is False
        assert bool(row["final_include"]) is False


class TestStatusRefactor:
    def test_blocking_statuses(self):
        assert set(BLOCKING_STATUSES) == {MISMATCH, MISSING_FROM_TSV}
        assert RECONCILED not in BLOCKING_STATUSES
        assert GENETIC_COHORT_ONLY not in BLOCKING_STATUSES


class TestStrictColumns:
    def test_missing_mapping_raises(self, monkeypatch):
        from pearl_audit import reconcile_groups
        df = pd.DataFrame({"participant_id": ["sub-01"], "APOE_haplotype": ["e3/e3"],
                           "PICALM_rs3851179": ["A/A"]})
        # audit.yaml has no resolved columns
        monkeypatch.setattr(reconcile_groups, "load_audit_yaml", lambda: {"columns": {}})
        with pytest.raises(ValueError, match="no resolved column mapping"):
            _resolve_columns(df)

    def test_stale_mapping_raises(self, monkeypatch):
        from pearl_audit import reconcile_groups
        df = pd.DataFrame({"participant_id": ["sub-01"], "APOE_haplotype": ["e3/e3"]})
        monkeypatch.setattr(reconcile_groups, "load_audit_yaml", lambda: {
            "columns": {"subject_id": "participant_id", "apoe": "APOE_haplotype",
                        "picalm": "PICALM_rs3851179"}
        })
        with pytest.raises(ValueError, match="not present"):
            _resolve_columns(df)

    def test_resolved_mapping_ok(self, monkeypatch):
        from pearl_audit import reconcile_groups
        df = pd.DataFrame({"participant_id": ["sub-01"], "APOE_haplotype": ["e3/e3"],
                           "PICALM_rs3851179": ["A/A"]})
        monkeypatch.setattr(reconcile_groups, "load_audit_yaml", lambda: {
            "columns": {"subject_id": "participant_id", "apoe": "APOE_haplotype",
                        "picalm": "PICALM_rs3851179"}
        })
        col_map = _resolve_columns(df)
        assert col_map["apoe"] == "APOE_haplotype"
