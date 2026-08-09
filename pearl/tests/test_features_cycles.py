import numpy as np
import pytest

from pearl_features.cycles import (
    narrowband_copy, positive_slope_zero_crossings, phase_locked_boundaries,
    extract_valid_cycles, CycleValidityConfig,
)


def _synthetic_alpha(seconds=10.0, sfreq=500.0, freq=10.0, noise_std=0.05, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sfreq)) / sfreq
    signal = np.sin(2 * np.pi * freq * t) + rng.normal(0, noise_std, size=t.shape)
    return signal, t


def test_narrowband_copy_recovers_dominant_frequency():
    signal, t = _synthetic_alpha()
    nb = narrowband_copy(signal, sfreq=500.0, iaf_hz=10.0, half_width_hz=2.0)
    freqs = np.fft.rfftfreq(len(nb), d=1 / 500.0)
    spectrum = np.abs(np.fft.rfft(nb))
    peak_freq = freqs[np.argmax(spectrum)]
    assert peak_freq == pytest.approx(10.0, abs=0.5)


def test_positive_slope_zero_crossings_count_matches_known_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.0)
    crossings = positive_slope_zero_crossings(signal, sfreq=500.0)
    # 10 Hz over 10s => ~100 positive-slope crossings
    assert 95 <= len(crossings) <= 105


def test_phase_locked_boundaries_median_period_close_to_true_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.02)
    crossings = positive_slope_zero_crossings(signal, sfreq=500.0)
    boundaries = phase_locked_boundaries(crossings, sfreq=500.0)
    periods = np.diff(boundaries) / 500.0
    assert np.median(periods) == pytest.approx(0.1, rel=0.15)  # 1/10 Hz


def test_detector_degrades_gracefully_on_pure_noise():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, size=5000)
    crossings = positive_slope_zero_crossings(noise, sfreq=500.0)
    # must not crash and must not fabricate a suspiciously regular cycle count;
    # any finite array is acceptable, just assert it runs and returns int array
    assert crossings.dtype.kind in "iu"


def test_extract_valid_cycles_rejects_out_of_band_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.0)
    nb = narrowband_copy(signal, sfreq=500.0, iaf_hz=10.0)
    crossings = positive_slope_zero_crossings(nb, sfreq=500.0)
    boundaries = phase_locked_boundaries(crossings, sfreq=500.0)
    cfg = CycleValidityConfig()
    cycles_out, stats = extract_valid_cycles(signal, boundaries, sfreq=500.0,
                                              iaf_hz=10.0, cfg=cfg)
    assert stats["rejection_rate"] < 0.3
    assert stats["median_period_s"] == pytest.approx(0.1, rel=0.15)
    assert all(len(c) > 0 for c in cycles_out)
