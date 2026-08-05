"""Tests for the EEG inventory / effective-N computation (phase_0,5.md Task 5 / Task 9)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pearl_audit.inventory import build_inventory, compute_effective_n, missingness_by_group
from pearl_audit.reconcile_groups import build_cohort_definition


def _synthetic_survey() -> pd.DataFrame:
    """Three subjects × three tasks, with known gaps (sub-51 sternberg, sub-55 rest)."""
    rows = []
    for subj in ["sub-51", "sub-55", "sub-01"]:
        for task in ["rest", "msit", "sternberg"]:
            # sub-51 missing sternberg; sub-55 missing rest
            if subj == "sub-51" and task == "sternberg":
                continue
            if subj == "sub-55" and task == "rest":
                continue
            rows.append({"path": f"{subj}/eeg/{subj}_task-{task}_eeg.eeg",
                         "bytes": 1000, "modality": "eeg", "subject": subj, "task": task})
    return pd.DataFrame(rows)


def _cohort() -> pd.DataFrame:
    return build_cohort_definition(
        tsv_subjects={"sub-51", "sub-55", "sub-01", "sub-69"},
        client_subjects={"sub-51", "sub-55", "sub-01"},
        eeg_subjects={"sub-51", "sub-55", "sub-01"},
    )


def _groups() -> dict[str, list[str]]:
    return {
        "N": ["sub-01"],
        "A_P_minus": [],
        "A_P_plus": ["sub-51", "sub-55"],
    }


class TestBuildInventory:
    def test_has_task_columns(self):
        inv = build_inventory(_synthetic_survey(), _cohort())
        assert {"has_rest", "has_msit", "has_sternberg"} <= set(inv.columns)
        assert set(inv["subject"]) == {"sub-01", "sub-51", "sub-55"}

    def test_known_missingness_reflected(self):
        inv = build_inventory(_synthetic_survey(), _cohort())
        s51 = inv[inv["subject"] == "sub-51"].iloc[0]
        s55 = inv[inv["subject"] == "sub-55"].iloc[0]
        assert bool(s51["has_sternberg"]) is False
        assert bool(s51["has_rest"]) is True
        assert bool(s55["has_rest"]) is False
        assert bool(s55["has_sternberg"]) is True

    def test_non_cohort_subject_excluded(self):
        survey = _synthetic_survey()
        # sub-69 has EEG rows in the survey but is not in the analysis cohort
        extra = pd.DataFrame([{"path": "sub-69/eeg/sub-69_task-rest_eeg.eeg",
                               "bytes": 1000, "modality": "eeg",
                               "subject": "sub-69", "task": "rest"}])
        inv = build_inventory(pd.concat([survey, extra], ignore_index=True), _cohort())
        assert "sub-69" not in set(inv["subject"])


class TestEffectiveN:
    def test_counts_per_task_per_group(self):
        inv = build_inventory(_synthetic_survey(), _cohort())
        en = compute_effective_n(inv, _groups())
        row = en[en["task"] == "sternberg"].iloc[0]
        assert row["A_P_plus"] == 1          # only sub-55 has sternberg
        assert row["total"] == 2
        row = en[en["task"] == "rest"].iloc[0]
        assert row["A_P_plus"] == 1          # only sub-51 has rest
        assert row["total"] == 2

    def test_wide_shape(self):
        inv = build_inventory(_synthetic_survey(), _cohort())
        en = compute_effective_n(inv, _groups())
        assert list(en.columns) == ["task", "N", "A_P_minus", "A_P_plus", "total"]
        assert len(en) == 3


class TestMissingness:
    def test_fisher_output(self):
        inv = build_inventory(_synthetic_survey(), _cohort())
        miss = missingness_by_group(inv, _groups())
        sternberg = miss[miss["task"] == "sternberg"]
        # A_P_minus has no subjects in this fixture, so it is skipped
        assert len(sternberg) == 2
        assert "missingness_p" in sternberg.columns
        assert sternberg["missingness_p"].notna().all()
