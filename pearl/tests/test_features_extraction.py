import numpy as np
import pandas as pd
import pytest
from scipy import stats

from pearl_features.features import (
    fifth_harmonic_index, harmonic_amplitude_profile, aggregate_cycles,
    load_features_config,
)


def test_load_features_config_declares_at_most_30_features():
    cfg = load_features_config()
    assert len(cfg["feature_list"]) <= cfg["dimensionality_budget"]["max_features"]


def test_fifth_harmonic_index_tracks_iaf():
    # 10 Hz IAF -> harmonic 5 lands exactly on 50 Hz
    assert fifth_harmonic_index(iaf_hz=10.0, n_harmonics=8, cycle_freq_hz=10.0) == 5
    # 8.25 Hz IAF -> nearest harmonic to 50 Hz is round(50/8.25)=6
    assert fifth_harmonic_index(iaf_hz=8.25, n_harmonics=8, cycle_freq_hz=8.25) == 6
    # 12.4 Hz IAF -> round(50/12.4)=4
    assert fifth_harmonic_index(iaf_hz=12.4, n_harmonics=8, cycle_freq_hz=12.4) == 4


def test_harmonic_amplitude_profile_excludes_index_as_nan():
    psr = np.stack([np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False)) for _ in range(30)])
    profile = harmonic_amplitude_profile(psr, n_harmonics=5, exclude_index=3)
    assert profile.shape == (30, 5)
    assert np.all(np.isnan(profile[:, 2]))  # 0-indexed column for harmonic index 3
    assert not np.any(np.isnan(profile[:, 0]))


def test_harmonic_amplitude_profile_fundamental_normalised_to_one():
    psr = np.stack([np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False)) for _ in range(10)])
    profile = harmonic_amplitude_profile(psr, n_harmonics=3, exclude_index=None)
    np.testing.assert_allclose(profile[:, 0], 1.0, atol=1e-6)  # harmonic 1 / harmonic 1


def test_aggregate_cycles_deterministic_under_fixed_seed():
    rng = np.random.default_rng(0)
    values = rng.normal(size=500)
    a = aggregate_cycles(values, n_subsample=200, seed=42)
    b = aggregate_cycles(values, n_subsample=200, seed=42)
    assert a == b


def test_aggregate_cycles_raises_when_too_few_cycles():
    values = np.zeros(10)
    with pytest.raises(ValueError):
        aggregate_cycles(values, n_subsample=200, seed=42)


def test_fifth_harmonic_excluded_index_does_not_associate_with_group():
    """phase_2.md §6b: record the excluded index per subject and verify it
    does not associate with group (same test as §1a). Uses a synthetic IAF
    distribution here; the real per-subject run happens in Task 14's
    pipeline and reuses this exact check against real qc_metrics.csv IAFs."""
    rng = np.random.default_rng(0)
    rows = []
    for i in range(1, 61):
        sid = f"sub-{i:02d}"
        g = "N" if i <= 30 else "A_P_plus"
        iaf = rng.normal(10.0, 1.0)  # group-independent IAF -> index should not associate
        idx = fifth_harmonic_index(iaf, n_harmonics=8, cycle_freq_hz=iaf)
        rows.append({"subject": sid, "group": g, "excluded_index": idx})
    df = pd.DataFrame(rows)
    contingency = pd.crosstab(df["group"], df["excluded_index"])
    _, p, _, _ = stats.chi2_contingency(contingency)
    assert p > 0.01  # group-independent IAF must not show a spurious association
