"""Tests for the BIDS entity parser (phase_0,5.md Task 1 / Task 9)."""
from __future__ import annotations

import pytest

from pearl_audit.bids import parse_bids_entities


class TestParseBidsEntities:
    """Real filenames observed in the ds004796 listing."""

    def test_msit_eeg(self):
        assert parse_bids_entities("sub-80_task-msit_eeg.eeg") == {
            "sub": "80", "task": "msit", "run": None,
            "suffix": "eeg", "ext": ".eeg",
        }

    def test_msit_vhdr(self):
        assert parse_bids_entities("sub-80_task-msit_eeg.vhdr")["task"] == "msit"
        assert parse_bids_entities("sub-80_task-msit_eeg.vhdr")["ext"] == ".vhdr"
        assert parse_bids_entities("sub-80_task-msit_eeg.vhdr")["suffix"] == "eeg"

    def test_msit_vmrk(self):
        assert parse_bids_entities("sub-80_task-msit_eeg.vmrk")["task"] == "msit"
        assert parse_bids_entities("sub-80_task-msit_eeg.vmrk")["sub"] == "80"

    def test_rest_eeg_json(self):
        assert parse_bids_entities("sub-01_task-rest_eeg.json") == {
            "sub": "01", "task": "rest", "run": None,
            "suffix": "eeg", "ext": ".json",
        }

    def test_full_path_input(self):
        parsed = parse_bids_entities("sub-80/eeg/sub-80_task-msit_eeg.eeg")
        assert parsed["sub"] == "80"
        assert parsed["task"] == "msit"
        assert parsed["ext"] == ".eeg"

    def test_no_entities_dataset_description(self):
        # No key-value chunks → {} (caller decides)
        assert parse_bids_entities("dataset_description.json") == {}

    def test_no_entities_participants_tsv(self):
        assert parse_bids_entities("participants.tsv") == {}

    def test_events_suffix(self):
        parsed = parse_bids_entities("sub-01_task-msit_events.tsv")
        assert parsed["task"] == "msit"
        assert parsed["suffix"] == "events"

    def test_run_and_acq_entities(self):
        """Entities beyond sub/task (acq-, run-) must survive the parser."""
        parsed = parse_bids_entities("sub-01_ses-1_task-rest_acq-eo_run-2_eeg.eeg")
        assert parsed["sub"] == "01"
        assert parsed["ses"] == "1"
        assert parsed["task"] == "rest"
        assert parsed["acq"] == "eo"
        assert parsed["run"] == "2"
        assert parsed["suffix"] == "eeg"

    def test_never_raises_on_malformed(self):
        # Malformed names must not raise — return {} or partial dict
        for bad in ["", "_.eeg", "foo-", "-bar_eeg.eeg", "task-msit-extra_eeg.eeg", "   "]:
            result = parse_bids_entities(bad)
            assert isinstance(result, dict)
