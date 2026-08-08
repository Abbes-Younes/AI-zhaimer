"""Filter-spec sidecar round-trip (phase_1.md §6) + synthetic IAF (also §6)."""
from __future__ import annotations

import json

import numpy as np

from pearl_preproc.config import load_preproc_config
from pearl_preproc.preprocess import estimate_iaf, filter_spec


def test_filter_spec_round_trips_into_sidecar():
    cfg = load_preproc_config()
    spec = filter_spec(cfg)
    # exactly as configured
    assert spec["high_pass"]["l_freq_hz"] == cfg["filters"]["high_pass"]["l_freq_hz"]
    assert spec["high_pass"]["phase"] == "zero"
    # json round-trip is lossless
    sidecar = {"SoftwareFilters": spec}
    rt = json.loads(json.dumps(sidecar))
    assert rt == sidecar
    assert rt["SoftwareFilters"] == spec


def test_iaf_synthetic_10hz():
    rng = np.random.default_rng(7)
    sfreq = 500.0
    t = np.arange(0, 30, 1 / sfreq)
    # 8 "channels", 10 Hz alpha + tiny noise, as V-scale EEG
    data = np.stack([
        4e-6 * np.sin(2 * np.pi * 10 * t) + rng.normal(0, 2e-7, t.size)
        for _ in range(8)
    ])
    iaf = estimate_iaf(data, sfreq, (7, 13), 3.0)
    assert abs(iaf["iaf_hz"] - 10.0) <= 0.5
    assert iaf["present"] is True
    assert iaf["peak_height_db"] > 0


def test_iaf_no_alpha_flat_spectrum():
    rng = np.random.default_rng(3)
    sfreq = 250.0
    t = np.arange(0, 30, 1 / sfreq)
    data = np.stack([rng.normal(0, 1e-6, t.size) for _ in range(6)])
    iaf = estimate_iaf(data, sfreq, (7, 13), 3.0)
    # broadband noise may still have a weak max, but not a 3 dB prominence peak
    assert iaf["present"] is False or iaf["peak_height_db"] < 3.0
