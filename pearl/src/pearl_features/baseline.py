"""§7 — baseline feature set (required, not optional): the reference the
pitch-synchronous features must beat, and how the published ~0.58 gets
reproduced.
"""
from __future__ import annotations

import numpy as np
from mne.time_frequency import psd_array_welch

_BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 45)}


def band_power(psd: np.ndarray, freqs: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs < band[1])
    return float(np.trapezoid(psd[mask], freqs[mask])) if mask.any() else 0.0


def relative_band_powers(raw, picks: list[str]) -> dict[str, float]:
    data = raw.get_data(picks=picks)
    sfreq = raw.info["sfreq"]
    psd, freqs = psd_array_welch(data, sfreq, fmin=1, fmax=45, n_fft=int(sfreq * 4), verbose=False)
    mean_psd = psd.mean(axis=0)
    total = band_power(mean_psd, freqs, (1, 45))
    return {name: (band_power(mean_psd, freqs, band) / total if total > 0 else 0.0)
            for name, band in _BANDS.items()}


def aperiodic_fit(psd: np.ndarray, freqs: np.ndarray) -> tuple[float, float]:
    """Offset/slope of a 1/f (log-log linear) fit over 1-45 Hz, excluding the
    canonical alpha band peak (8-13 Hz) from the fit so the periodic
    component does not bias the aperiodic estimate -- the standard FOOOF/
    specparam heuristic done manually with scipy/numpy to avoid a heavyweight
    dependency."""
    mask = ((freqs >= 1) & (freqs < 8)) | ((freqs >= 13) & (freqs <= 45))
    log_f = np.log10(freqs[mask])
    log_p = np.log10(np.clip(psd[mask], 1e-20, None))
    slope, offset = np.polyfit(log_f, log_p, 1)
    return float(offset), float(slope)


def compute_subject_baseline(raw, roi_channels: list[str], iaf_hz: float,
                              alpha_peak_height_db: float, prefix: str = "") -> dict[str, float]:
    picks = [ch for ch in roi_channels if ch in raw.ch_names]
    powers = relative_band_powers(raw, picks)
    data = raw.get_data(picks=picks).mean(axis=0)
    psd, freqs = psd_array_welch(data[np.newaxis, :], raw.info["sfreq"], fmin=1, fmax=45,
                                  n_fft=int(raw.info["sfreq"] * 4), verbose=False)
    offset, slope = aperiodic_fit(psd[0], freqs)
    out = {
        f"{prefix}band_power_delta": powers["delta"], f"{prefix}band_power_theta": powers["theta"],
        f"{prefix}band_power_alpha": powers["alpha"], f"{prefix}band_power_beta": powers["beta"],
        f"{prefix}band_power_gamma": powers["gamma"],
        f"{prefix}aperiodic_offset": offset, f"{prefix}aperiodic_slope": slope,
    }
    if not prefix:
        out["iaf_hz"] = iaf_hz
        out["alpha_peak_height_db"] = alpha_peak_height_db
    return out
