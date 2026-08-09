import numpy as np
import pytest

from pearl_features.pswt import (
    demultiplex, decompose, harmonic_estimate, inter_harmonic_residual,
    perfect_reconstruction,
)


def _synthetic_psr(n_cycles=64, p=50, seed=0):
    rng = np.random.default_rng(seed)
    base = np.sin(np.linspace(0, 2 * np.pi, p, endpoint=False))
    return np.stack([base + rng.normal(0, 0.01, size=p) for _ in range(n_cycles)], axis=0)


def test_demultiplex_shape_is_transposed():
    psr = _synthetic_psr()
    sub = demultiplex(psr)
    assert sub.shape == (psr.shape[1], psr.shape[0])
    np.testing.assert_array_equal(sub[3], psr[:, 3])


def test_perfect_reconstruction_with_all_subbands_round_trips():
    psr = _synthetic_psr(n_cycles=64, p=50)
    sub = demultiplex(psr)
    recon = perfect_reconstruction(sub, wavelet="db8")
    recon_psr = recon.T[: psr.shape[0], : psr.shape[1]]
    np.testing.assert_allclose(recon_psr, psr, atol=1e-6)


def test_harmonic_estimate_plus_residual_equals_original():
    psr = _synthetic_psr(n_cycles=64, p=50)
    sub = demultiplex(psr)
    decomp = decompose(sub, wavelet="db8")
    h_est = harmonic_estimate(decomp, wavelet="db8")
    residual = inter_harmonic_residual(psr, h_est)
    np.testing.assert_allclose(h_est + residual, psr, atol=1e-6)


def test_harmonic_estimate_matches_psr_shape_for_odd_cycle_count():
    """Regression: pywt periodization-mode reconstruction rounds an odd-length
    signal up by one sample at deeper decomposition levels (e.g. 305 -> 306).
    n_cycles is frequently odd on real data, so this must not desync the
    residual computation."""
    psr = _synthetic_psr(n_cycles=305, p=59, seed=3)
    sub = demultiplex(psr)
    decomp = decompose(sub, wavelet="db8")
    h_est = harmonic_estimate(decomp, wavelet="db8")
    assert h_est.shape == psr.shape
    residual = inter_harmonic_residual(psr, h_est)
    assert residual.shape == psr.shape


def test_harmonic_estimate_removes_most_high_frequency_noise():
    p = 50
    n_cycles = 64
    t = np.linspace(0, 2 * np.pi, p, endpoint=False)
    rng = np.random.default_rng(1)
    clean = np.stack([np.sin(t) for _ in range(n_cycles)], axis=0)
    noisy = clean + rng.normal(0, 0.3, size=clean.shape)
    sub = demultiplex(noisy)
    decomp = decompose(sub, wavelet="db8")
    h_est = harmonic_estimate(decomp, wavelet="db8")
    err_noisy = np.mean((noisy - clean) ** 2)
    err_denoised = np.mean((h_est - clean) ** 2)
    assert err_denoised < err_noisy
