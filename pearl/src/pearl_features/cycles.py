"""§3 — cycle detection (thesis chapter §5.1.2, adapted).

Detect cycle boundaries on a narrowband copy. Measure waveform shape on the
broadband signal. Filtering to the alpha band and then measuring harmonic
content of the result measures the filter, not the signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import mne
import numpy as np


def narrowband_copy(data: np.ndarray, sfreq: float, iaf_hz: float,
                     half_width_hz: float = 2.0) -> np.ndarray:
    """Zero-phase FIR bandpass at [iaf_hz - half_width_hz, iaf_hz + half_width_hz].
    Exact spec: mne.filter.filter_data(method="fir", phase="zero", fir_design="firwin")."""
    l_freq = max(0.1, iaf_hz - half_width_hz)
    h_freq = iaf_hz + half_width_hz
    return mne.filter.filter_data(data.astype(np.float64), sfreq, l_freq, h_freq,
                                   method="fir", phase="zero", fir_design="firwin",
                                   verbose=False)


def positive_slope_zero_crossings(signal: np.ndarray, sfreq: float) -> np.ndarray:
    """Indices of positive-slope zero crossings, each rounded to the first
    positive sample after the crossing (phase_2.md §3 step 2)."""
    sign = np.sign(signal)
    sign[sign == 0] = 1  # treat exact zero as positive, avoids double-counting
    crossing_mask = (sign[:-1] < 0) & (sign[1:] >= 0)
    idx = np.nonzero(crossing_mask)[0] + 1  # index of first sample >= 0 after a negative sample
    return idx.astype(np.int64)


def phase_locked_boundaries(crossings: np.ndarray, sfreq: float,
                             smoothing_window: int = 5) -> np.ndarray:
    """§3 step 3: estimate the period from local crossing spacing, then locate
    the next boundary as the crossing closest to t_k + P(t_k) — not merely the
    next one after it.

    P(t_k) is a running median of the last `smoothing_window` accepted gaps
    (falling back to fewer while warming up, and to the gap between the first
    two raw crossings before any boundary has been accepted). A single-gap
    causal estimate is not used: on real, noisy narrowband signal a single bad
    gap (e.g. one missed/spurious crossing) permanently doubles the period
    estimate and the loop locks into half-rate detection from then on — a
    smoothed estimate dilutes one bad sample instead of propagating it."""
    if len(crossings) < 2:
        return crossings.copy()

    boundaries = [int(crossings[0])]
    recent_gaps: list[int] = []
    while True:
        t_k = boundaries[-1]
        if recent_gaps:
            period_samples = np.median(recent_gaps[-smoothing_window:])
        else:
            period_samples = crossings[1] - crossings[0]
        target = t_k + period_samples
        candidates = crossings[crossings > t_k]
        if len(candidates) == 0:
            break
        closest = candidates[np.argmin(np.abs(candidates - target))]
        recent_gaps.append(closest - t_k)
        boundaries.append(int(closest))
        if closest >= crossings[-1]:
            break
    return np.array(boundaries, dtype=np.int64)


@dataclass
class CycleValidityConfig:
    min_period_frac: float = 0.6   # ±40% of 1/iaf_hz
    max_period_frac: float = 1.4
    min_amplitude_percentile: float = 10.0


def extract_valid_cycles(broadband: np.ndarray, boundaries: np.ndarray, sfreq: float,
                          iaf_hz: float, cfg: CycleValidityConfig) -> tuple[list[np.ndarray], dict]:
    """Map narrowband-detected boundaries onto the broadband signal, apply the
    a priori validity filter, and log the rejection rate."""
    if len(boundaries) < 2:
        return [], {"n_detected": 0, "n_valid": 0, "rejection_rate": 1.0, "median_period_s": float("nan")}

    expected_period_s = 1.0 / iaf_hz
    lo = cfg.min_period_frac * expected_period_s
    hi = cfg.max_period_frac * expected_period_s

    raw_cycles = [broadband[boundaries[i]:boundaries[i + 1]] for i in range(len(boundaries) - 1)]
    periods_s = np.diff(boundaries) / sfreq

    in_band = (periods_s >= lo) & (periods_s <= hi)
    amps = np.array([c.max() - c.min() if len(c) else 0.0 for c in raw_cycles])
    amp_thresh = np.percentile(amps, cfg.min_amplitude_percentile) if len(amps) else 0.0
    keep = in_band & (amps >= amp_thresh)

    valid_cycles = [c for c, k in zip(raw_cycles, keep) if k]
    n_detected = len(raw_cycles)
    n_valid = len(valid_cycles)
    stats = {
        "n_detected": n_detected,
        "n_valid": n_valid,
        "rejection_rate": 1.0 - (n_valid / n_detected if n_detected else 0.0),
        "median_period_s": float(np.median(periods_s[keep])) if n_valid else float("nan"),
    }
    return valid_cycles, stats
