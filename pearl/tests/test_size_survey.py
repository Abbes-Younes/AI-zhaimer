"""Regression tests for the size-survey task column (phase_0,5.md Task 1 / Task 9).

The original bug: `re.match(r"task-(\\w+)", fname)` anchored at the start of the
filename, so subject-level files like `sub-80_task-msit_eeg.eeg` got an empty
task column and the whole EEG inventory silently collapsed.
"""
from __future__ import annotations

import pytest

from pearl_audit.size_survey import _parse_listing


class TestTaskColumnPopulated:
    def test_real_listing_rows_get_tasks(self):
        rows = [
            {"rel_path": "sub-80/eeg/sub-80_task-msit_eeg.eeg", "bytes": 100},
            {"rel_path": "sub-80/eeg/sub-80_task-rest_eeg.vhdr", "bytes": 10},
            {"rel_path": "sub-01/eeg/sub-01_task-sternberg_eeg.eeg", "bytes": 200},
        ]
        parsed = _parse_listing(rows)
        tasks = [r["task"] for r in parsed]
        assert tasks == ["msit", "rest", "sternberg"]

    def test_observed_tasks_non_empty_for_subject_eeg(self):
        rows = [
            {"rel_path": "sub-80/eeg/sub-80_task-msit_eeg.eeg", "bytes": 100},
            {"rel_path": "sub-80/func/sub-80_task-msit_dir-AP_bold.nii.gz", "bytes": 999},
        ]
        parsed = _parse_listing(rows)
        eeg_subject_tasks = {
            r["task"] for r in parsed
            if r["subject"] and r["modality"] == "eeg" and r["task"]
        }
        assert eeg_subject_tasks  # must be non-empty — the original bug

    def test_root_metadata_gets_no_task(self):
        rows = [
            {"rel_path": "participants.tsv", "bytes": 10},
            {"rel_path": "dataset_description.json", "bytes": 10},
        ]
        parsed = _parse_listing(rows)
        assert all(r["task"] is None for r in parsed)
        assert all(r["subject"] is None for r in parsed)
