"""Track B multitaper TFA features (phase_5_stage2.md §2-3,
reports/phase5_stage2_plan_frozen.md)."""
from __future__ import annotations

import mne
import numpy as np
import pytest

import pearl_features.tfa as tfa_mod
from pearl_features.tfa import (
    BANDS,
    aggregate_tfa_features,
    epoch_locked_tfa,
    marker_onsets_with_min_gap,
    multitaper_band_areas,
    windowed_tfa,
)


def _pure_tone(freq_hz, sfreq=250.0, n_seconds=4.0, amplitude=1.0, seed=0):
    rng = np.random.default_rng(seed)
    n = int(sfreq * n_seconds)
    t = np.arange(n) / sfreq
    noise = rng.normal(0, amplitude * 0.01, size=n)
    return amplitude * np.sin(2 * np.pi * freq_hz * t) + noise


def test_multitaper_band_areas_concentrates_power_in_the_true_band():
    # A pure 10 Hz tone (alpha, 8-13 Hz) should dominate the alpha band area
    # by a wide margin over every other band -- a hand-verifiable ground
    # truth independent of this module's own machinery.
    data = _pure_tone(10.0)
    areas = multitaper_band_areas(data, sfreq=250.0)
    assert areas["alpha"] > 10 * areas["delta"]
    assert areas["alpha"] > 10 * areas["theta"]
    assert areas["alpha"] > 10 * areas["beta"]
    assert areas["alpha"] > 10 * areas["gamma"]


def test_multitaper_band_areas_is_deterministic():
    data = _pure_tone(20.0, seed=42)
    a1 = multitaper_band_areas(data, sfreq=250.0)
    a2 = multitaper_band_areas(data, sfreq=250.0)
    assert a1 == a2


def test_aggregate_tfa_features_mean_and_iqr():
    window_areas = [{"delta": 1.0, "theta": 2.0, "alpha": 3.0, "beta": 4.0, "gamma": 5.0},
                     {"delta": 3.0, "theta": 4.0, "alpha": 5.0, "beta": 6.0, "gamma": 7.0}]
    out = aggregate_tfa_features(window_areas, aperiodic=(1.5, -2.0), prefix="msit_")
    assert out["msit_tfa_delta_mean"] == pytest.approx(2.0)
    assert out["msit_tfa_delta_iqr"] == pytest.approx(1.0)
    assert out["msit_tfa_aperiodic_offset"] == 1.5
    assert out["msit_tfa_aperiodic_slope"] == -2.0
    assert len(out) == len(BANDS) * 2 + 2


def _raw_with_annotations(n_seconds=20.0, sfreq=250.0):
    rng = np.random.default_rng(0)
    n = int(sfreq * n_seconds)
    data = rng.normal(0, 1e-6, size=(1, n))
    info = mne.create_info(["ch0"], sfreq, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    # Two "S 4"-coded markers: one with a safe 3.0s gap to the next event,
    # one with only a 1.0s gap -- must be skipped under a 3.0s min-gap rule.
    onsets = [1.0, 4.5, 10.0, 11.0]
    descriptions = ["Stimulus/S  4", "Stimulus/S 11", "Stimulus/S  4", "Stimulus/S 11"]
    raw.set_annotations(mne.Annotations(onset=onsets, duration=[0.001] * 4,
                                         description=descriptions))
    return raw


def test_marker_onsets_with_min_gap_skips_short_gaps():
    raw = _raw_with_annotations()
    onsets, n_skipped = marker_onsets_with_min_gap(raw, code=4, min_gap_s=3.0)
    # first S4@1.0 -> next event@4.5, gap 3.5s >= 3.0 -> kept
    # second S4@10.0 -> next event@11.0, gap 1.0s < 3.0 -> skipped
    assert list(onsets) == [1.0]
    assert n_skipped == 1


def test_marker_onsets_with_min_gap_no_match_returns_empty():
    raw = _raw_with_annotations()
    onsets, n_skipped = marker_onsets_with_min_gap(raw, code=99, min_gap_s=0.1)
    assert len(onsets) == 0
    assert n_skipped == 0


def test_windowed_tfa_calls_multitaper_exactly_once(monkeypatch):
    # Regression test for a real bug (phase5_stage2_plan_frozen.md): the
    # aperiodic fit originally re-ran multitaper PSD on the whole,
    # un-windowed recording separately from the windowed band-area call --
    # DPSS taper cost blows up with segment length, measured at >1500s for
    # one subject's MSIT recording. The fit must reuse the windowed PSD
    # batch (its mean across windows), never trigger a second multitaper
    # call on a long segment.
    calls = []
    real = tfa_mod.psd_array_multitaper

    def counting_wrapper(x, *args, **kwargs):
        calls.append(np.asarray(x).shape)
        return real(x, *args, **kwargs)

    monkeypatch.setattr(tfa_mod, "psd_array_multitaper", counting_wrapper)

    rng = np.random.default_rng(1)
    n = int(250.0 * 20)
    data = rng.normal(0, 1e-6, size=(2, n))
    info = mne.create_info(["ch0", "ch1"], 250.0, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    windowed_tfa(raw, picks=["ch0", "ch1"], window_s=4.0)

    assert len(calls) == 1, f"expected exactly one multitaper call, got {len(calls)}: {calls}"
    n_segments, n_samples = calls[0]
    assert n_samples == int(4.0 * 250.0), "must be windowed, not the whole recording"


def test_windowed_tfa_returns_expected_keys():
    rng = np.random.default_rng(1)
    n = int(250.0 * 20)
    data = rng.normal(0, 1e-6, size=(2, n))
    info = mne.create_info(["ch0", "ch1"], 250.0, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    out = windowed_tfa(raw, picks=["ch0", "ch1"], window_s=4.0)
    for band in BANDS:
        assert f"tfa_{band}_mean" in out
        assert f"tfa_{band}_iqr" in out
    assert "tfa_aperiodic_offset" in out
    assert "tfa_aperiodic_slope" in out


def test_epoch_locked_tfa_drops_epochs_that_run_past_recording_end():
    rng = np.random.default_rng(2)
    n = int(250.0 * 5.0)  # 5-second recording
    data = rng.normal(0, 1e-6, size=(1, n))
    info = mne.create_info(["ch0"], 250.0, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    # onset at 4.0s + 3.0s duration would run to 7.0s, past the 5s recording -> dropped
    out = epoch_locked_tfa(raw, picks=["ch0"], onsets_s=np.array([0.5, 4.0]),
                            duration_s=3.0, prefix="sternberg_encoding_")
    # only the 0.5s-onset epoch survives; mean equals that single epoch's area exactly
    single = multitaper_band_areas(data[0, int(0.5 * 250):int(0.5 * 250) + 750], sfreq=250.0)
    for band in BANDS:
        assert out[f"sternberg_encoding_tfa_{band}_mean"] == pytest.approx(single[band])
        assert out[f"sternberg_encoding_tfa_{band}_iqr"] == pytest.approx(0.0)
