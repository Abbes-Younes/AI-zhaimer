import mne
import numpy as np
import pytest

from pearl_features.baseline import band_power, relative_band_powers, aperiodic_fit


def _synthetic_raw_with_alpha(seconds=60, sfreq=500.0, n_ch=3, alpha_hz=10.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sfreq)) / sfreq
    alpha = 3e-6 * np.sin(2 * np.pi * alpha_hz * t)
    pink_like = rng.normal(0, 1e-6, size=t.shape)
    data = np.stack([alpha + pink_like + rng.normal(0, 1e-7, size=t.shape) for _ in range(n_ch)])
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose=False)


def test_band_power_sums_to_less_than_total():
    freqs = np.linspace(1, 45, 200)
    psd = np.ones_like(freqs)
    total = band_power(psd, freqs, (1, 45))
    alpha = band_power(psd, freqs, (8, 13))
    assert alpha < total


def test_relative_band_powers_alpha_dominant_with_synthetic_alpha():
    raw = _synthetic_raw_with_alpha()
    powers = relative_band_powers(raw, picks=raw.ch_names)
    assert set(powers) == {"delta", "theta", "alpha", "beta", "gamma"}
    assert powers["alpha"] == max(powers.values())


def test_aperiodic_fit_returns_finite_offset_and_slope():
    freqs = np.linspace(1, 45, 200)
    psd = 10 ** (-2 - 1.5 * np.log10(freqs))  # synthetic 1/f with known slope ~ -1.5
    offset, slope = aperiodic_fit(psd, freqs)
    assert np.isfinite(offset)
    assert -3.0 < slope < 0.0
