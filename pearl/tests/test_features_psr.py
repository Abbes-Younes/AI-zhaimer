import numpy as np
import pytest

from pearl_features.psr import mode_period, dft_resample, build_psr_matrix


def test_mode_period_picks_most_common_length():
    cycles = [np.zeros(48), np.zeros(50), np.zeros(50), np.zeros(50), np.zeros(52)]
    assert mode_period(cycles) == 50


def test_dft_resample_same_length_is_near_identity():
    t = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=50)
    np.testing.assert_allclose(out, cycle, atol=1e-8)


def test_dft_resample_upsamples_preserving_shape():
    t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=80)
    assert len(out) == 80
    # a resampled single sinusoid stays approximately sinusoidal at the same
    # number of cycles (1 full period), so its own zero crossing count is ~2
    sign_changes = np.sum(np.diff(np.sign(out)) != 0)
    assert 1 <= sign_changes <= 3


def test_dft_resample_nyquist_zeroed_for_odd_target():
    t = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=51)
    spectrum = np.fft.rfft(out)
    nyquist_bin = len(out) // 2
    assert abs(spectrum[nyquist_bin]) < 1e-6


def test_build_psr_matrix_shape_and_assertion():
    rng = np.random.default_rng(0)
    cycles = [rng.normal(size=50) for _ in range(20)]
    mat = build_psr_matrix(cycles)
    assert mat.shape == (20, 50)


def test_build_psr_matrix_raises_below_40():
    cycles = [np.zeros(30) for _ in range(5)]
    with pytest.raises(AssertionError):
        build_psr_matrix(cycles)


def test_psr_reconstruction_round_trip():
    """Required by phase_2.md §4/§9: PSR construction followed by inverse must
    reconstruct to within numerical tolerance on a synthetic pseudo-periodic
    signal."""
    rng = np.random.default_rng(0)
    base = np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False))
    cycles = [base + rng.normal(0, 1e-9, size=50) for _ in range(10)]  # near-identical length, near-noiseless
    mat = build_psr_matrix(cycles, target_period=50)
    # inverse: resample each PSR row back to its own original length (50) and
    # compare to the input cycle
    for row, original in zip(mat, cycles):
        back = dft_resample(row, target_len=len(original))
        np.testing.assert_allclose(back, original, atol=1e-6)
