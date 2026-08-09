"""§4 — the PSR matrix. DFT-based cycle resampling (chapter §5.2.2), not
filter-based resampling — filter-based resampling introduces edge effects at
cycle boundaries, which is exactly where the reconstruction downstream lives.
"""
from __future__ import annotations

from collections import Counter

import numpy as np


def mode_period(cycles: list[np.ndarray]) -> int:
    if not cycles:
        raise ValueError("mode_period called with zero cycles — nothing to build a PSR matrix from.")
    lengths = [len(c) for c in cycles]
    return Counter(lengths).most_common(1)[0][0]


def dft_resample(cycle: np.ndarray, target_len: int) -> np.ndarray:
    """DFT of size Q_i=len(cycle); truncate or zero-extend to target_len=P;
    IDFT scaled by P/Q_i. Nyquist bin zeroed when P or Q_i is odd -- 'odd'
    here means the resampled length has no single unambiguous Nyquist bin, so
    it is zeroed defensively regardless of which of P/Q_i is odd."""
    q = len(cycle)
    p = target_len
    spectrum = np.fft.fft(cycle.astype(np.float64))

    if p == q:
        out_spectrum = spectrum.copy()
    elif p > q:
        # zero-extend: keep low frequencies at both ends of the spectrum
        out_spectrum = np.zeros(p, dtype=complex)
        half = q // 2
        out_spectrum[:half + 1] = spectrum[:half + 1]
        out_spectrum[-(q - half - 1):] = spectrum[half + 1:]
    else:
        # truncate: keep low frequencies at both ends
        out_spectrum = np.zeros(p, dtype=complex)
        half = p // 2
        out_spectrum[:half + 1] = spectrum[:half + 1]
        if p - half - 1 > 0:
            out_spectrum[-(p - half - 1):] = spectrum[-(p - half - 1):]

    if p % 2 == 0 or q % 2 == 0:
        nyquist_bin = p // 2
        out_spectrum[nyquist_bin] = 0.0

    resampled = np.fft.ifft(out_spectrum) * (p / q)
    return np.real(resampled)


def build_psr_matrix(cycles: list[np.ndarray], target_period: int | None = None) -> np.ndarray:
    p = target_period if target_period is not None else mode_period(cycles)
    assert p >= 40, (
        f"PSR target period P={p} < 40 — the harmonic representation in §6 is "
        f"too coarse below this; the resampling step (or upstream sampling "
        f"rate) needs revisiting before proceeding (phase_2.md §4/§11).")
    return np.stack([dft_resample(c, p) for c in cycles], axis=0)
