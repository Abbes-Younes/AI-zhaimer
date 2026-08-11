"""Resample rates read from config, not hardcoded (phase_1.md §2b, §6)."""
from __future__ import annotations

import pytest

from pearl_preproc.config import PreprocConfigError, load_preproc_config, target_sfreq


def test_target_rates_from_config():
    cfg = load_preproc_config()
    assert target_sfreq(cfg, "task-rest") == 500.0
    assert target_sfreq(cfg, "task-msit") == 250.0
    assert target_sfreq(cfg, "task-sternberg") == 250.0


def test_rates_are_not_hardcoded():
    cfg = load_preproc_config()
    cfg["sampling_rates_hz"]["task-rest"] = 256.0
    assert target_sfreq(cfg, "task-rest") == 256.0  # follows config, not code


def test_task_without_rate_raises():
    cfg = load_preproc_config()
    with pytest.raises(PreprocConfigError):
        target_sfreq(cfg, "task-nback")  # never configured for this dataset


def test_config_file_mentions_both_rates():
    import yaml
    from pearl_preproc.paths import PREPROC_YAML
    data = yaml.safe_load(PREPROC_YAML.read_text(encoding="utf-8"))
    rates = data["sampling_rates_hz"]
    assert rates["task-rest"] == 500
    assert rates["task-msit"] == 250
    assert rates["task-sternberg"] == 250
