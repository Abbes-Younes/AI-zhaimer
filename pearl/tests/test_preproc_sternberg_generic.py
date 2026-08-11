"""phase_5.md §0c: Sternberg must be a first-class task, same as rest/msit."""
from __future__ import annotations

from pearl_preproc.config import load_preproc_config, target_sfreq


def test_sternberg_sampling_rate_configured():
    cfg = load_preproc_config()
    assert target_sfreq(cfg, "sternberg") == 250.0
