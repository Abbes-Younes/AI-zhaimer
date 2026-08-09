"""§5 — PSWT via the multiplexed / polyphase structure (chapter §5.4.2), NOT
comb wavelets: comb wavelets lose perfect reconstruction for even P, and with
P ~= 50 (even) that failure mode is hit immediately.
"""
from __future__ import annotations

import numpy as np
import pywt


def demultiplex(psr_matrix: np.ndarray) -> np.ndarray:
    """(n_cycles, P) -> (P, n_cycles): subsignal j is phase j across cycles."""
    return psr_matrix.T.copy()


def _max_level(n: int, wavelet: str) -> int:
    return pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)


def decompose(subsignals: np.ndarray, wavelet: str = "db8", level: int | None = None):
    out = []
    for row in subsignals:
        lvl = level if level is not None else _max_level(len(row), wavelet)
        lvl = max(1, lvl)
        coeffs = pywt.wavedec(row, wavelet, level=lvl, mode="periodization")
        out.append((coeffs[0], coeffs[1:]))
    return out


def harmonic_estimate(decomposition, wavelet: str = "db8") -> np.ndarray:
    """Reconstruct each subsignal from its lowpass/approx band only -> the
    harmonic/periodic estimate. Re-multiplexed back to (n_cycles, P)."""
    rows = []
    for approx, details in decomposition:
        zero_details = [np.zeros_like(d) for d in details]
        recon = pywt.waverec([approx, *zero_details], wavelet, mode="periodization")
        rows.append(recon)
    subsignals_recon = np.stack(rows, axis=0)  # (P, n_cycles)
    return subsignals_recon.T  # -> (n_cycles, P)


def inter_harmonic_residual(psr_matrix: np.ndarray, harmonic_est: np.ndarray) -> np.ndarray:
    n = min(psr_matrix.shape[1], harmonic_est.shape[1])
    return psr_matrix[:, :n] - harmonic_est[:, :n]


def perfect_reconstruction(subsignals: np.ndarray, wavelet: str = "db8") -> np.ndarray:
    """Full reconstruction using ALL subbands. Required PR test only — not
    used directly by feature extraction (harmonic_estimate is)."""
    decomp = decompose(subsignals, wavelet=wavelet)
    rows = []
    for approx, details in decomp:
        recon = pywt.waverec([approx, *details], wavelet, mode="periodization")
        rows.append(recon)
    return np.stack(rows, axis=0)
