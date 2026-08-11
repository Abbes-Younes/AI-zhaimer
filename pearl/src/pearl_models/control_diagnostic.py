"""§0 — the one remaining diagnostic (phase_4.md Task A).

Runs ONLY against positive-control targets (sex), never the primary target.
It cannot change the primary verdict (frozen: NULL, AUC 0.474); its only
output is which of two sentences the final report is entitled to write
(§0d). Any drift toward running this against binary_risk_vs_none
invalidates the entire Phase 3 result -- enforced here, not just in
documentation.
"""
from __future__ import annotations

import numpy as np

ALLOWED_TARGETS = {"sex"}


def run_rung(rung_name: str, target: str, X: np.ndarray, y: np.ndarray, groups: np.ndarray,
             cfg: dict) -> dict:
    if target not in ALLOWED_TARGETS:
        raise ValueError(
            f"control_diagnostic refuses to run against target={target!r}. "
            f"Only {ALLOWED_TARGETS} are sanctioned (phase_4.md §0a) — running "
            f"this against binary_risk_vs_none or any other framing would "
            f"invalidate the entire Phase 3 result.")
    from pearl_models.primary import run_one_analysis
    result = run_one_analysis(rung_name, X, y, groups, cfg, seed=cfg["cv"]["seed"])
    result["rung"] = rung_name
    return result


def run_rung1_baseline(cfg: dict) -> dict:
    from pearl_models.data import load_baseline_features, load_nuisance

    baseline = load_baseline_features()
    rest_cols = [c for c in baseline.columns if not c.startswith("msit_")]
    nuisance = load_nuisance()
    joined = baseline[rest_cols].join(nuisance[["sex"]], how="inner").dropna(subset=["sex"])
    X = joined[rest_cols].to_numpy(dtype=float)
    y = joined["sex"].to_numpy(dtype=int)
    return run_rung("rung1_baseline", "sex", X, y, np.arange(len(y)), cfg)


def run_rung2_pswt_plus_baseline(cfg: dict) -> dict:
    from pearl_models.data import load_pswt_features, load_baseline_features, load_nuisance

    pswt = load_pswt_features()
    baseline = load_baseline_features()
    rest_cols = [c for c in baseline.columns if not c.startswith("msit_")]
    combo_cols = list(pswt.columns) + rest_cols
    nuisance = load_nuisance()
    joined = pswt.join(baseline[rest_cols], how="inner").join(
        nuisance[["sex"]], how="inner").dropna(subset=["sex"])
    X = joined[combo_cols].to_numpy(dtype=float)
    y = joined["sex"].to_numpy(dtype=int)
    return run_rung("rung2_pswt_plus_baseline", "sex", X, y, np.arange(len(y)), cfg)


# Coarse anatomical zones over the 127-channel montage, used to keep rung 3's
# feature count tractable (127 channels x 7 metrics would be 889 columns on
# n=64 -- uninterpretable and degenerate). Zone membership by channel-name
# prefix, covering the standard_1005 naming used throughout this project.
_ZONES = {
    "frontal": ["Fp", "AF", "F"],
    "central": ["FC", "C", "CP"],
    "parietal": ["P", "PO"],
    "occipital": ["O", "I"],
    "temporal": ["FT", "T", "TP"],
}


def _zone_for_channel(ch_name: str) -> str | None:
    # Longest-prefix match first (e.g. "FC1" -> central via "FC", not
    # frontal via "F") by checking multi-letter prefixes before single-letter.
    for zone, prefixes in _ZONES.items():
        for prefix in sorted(prefixes, key=len, reverse=True):
            if ch_name.startswith(prefix) and (len(ch_name) == len(prefix)
                                                or ch_name[len(prefix)].isdigit()
                                                or ch_name[len(prefix)] in "zZ"):
                return zone
    return None


def compute_per_channel_band_power(subject: str, features_cfg: dict) -> dict:
    """Fresh computation: relative band power + 1/f fit, averaged within
    coarse anatomical zones instead of the declared 15-channel occipital-
    parietal ROI (phase_4.md §0c rung 3 -- tests whether ROI averaging
    itself destroyed between-subject variance)."""
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments
    from pearl_features.baseline import relative_band_powers, aperiodic_fit
    from mne.time_frequency import psd_array_welch

    raw = load_eyes_closed_continuous(subject)
    raw, _, _ = reject_artifact_segments(raw, features_cfg)

    zone_channels: dict[str, list[str]] = {z: [] for z in _ZONES}
    for ch in raw.ch_names:
        zone = _zone_for_channel(ch)
        if zone:
            zone_channels[zone].append(ch)

    out = {}
    for zone, chans in zone_channels.items():
        if not chans:
            continue
        picks = [c for c in chans if c in raw.ch_names]
        powers = relative_band_powers(raw, picks)
        data = raw.get_data(picks=picks).mean(axis=0)
        psd, freqs = psd_array_welch(data[np.newaxis, :], raw.info["sfreq"], fmin=1, fmax=45,
                                      n_fft=int(raw.info["sfreq"] * 4), verbose=False)
        offset, slope = aperiodic_fit(psd[0], freqs)
        for band, value in powers.items():
            out[f"{zone}_band_power_{band}"] = value
        out[f"{zone}_aperiodic_offset"] = offset
        out[f"{zone}_aperiodic_slope"] = slope
    return out


def run_rung3_per_channel(cfg: dict, features_cfg: dict) -> dict:
    from pearl_models.data import load_pswt_features, load_nuisance

    subjects = list(load_pswt_features().index)
    nuisance = load_nuisance()

    rows = {}
    for subject in subjects:
        try:
            rows[subject] = compute_per_channel_band_power(subject, features_cfg)
        except (AssertionError, ValueError):
            continue

    import pandas as pd
    df = pd.DataFrame.from_dict(rows, orient="index")
    joined = df.join(nuisance[["sex"]], how="inner").dropna(subset=["sex"])
    feature_cols = list(df.columns)
    X = joined[feature_cols].to_numpy(dtype=float)
    y = joined["sex"].to_numpy(dtype=int)
    return run_rung("rung3_per_channel", "sex", X, y, np.arange(len(y)), cfg)


def run_ladder(cfg: dict, features_cfg: dict, significance_alpha: float = 0.05) -> dict:
    """Runs all three rungs unconditionally (§0c: report all three outcomes
    regardless of where the ladder would stop) and identifies the first rung
    that is "clearly above chance" -- operationalized as the permutation
    p-value, the same significance criterion used everywhere else in this
    project (Phase 2's confound gate, Phase 3's primary/secondary analyses),
    not an ad hoc CI-lower-bound rule."""
    rung1 = run_rung1_baseline(cfg)
    rung2 = run_rung2_pswt_plus_baseline(cfg)
    rung3 = run_rung3_per_channel(cfg, features_cfg)

    stopped_at = None
    for name, result in [("rung1_baseline", rung1), ("rung2_pswt_plus_baseline", rung2),
                          ("rung3_per_channel", rung3)]:
        if result["p_value"] < significance_alpha:
            stopped_at = name
            break

    return {"rung1": rung1, "rung2": rung2, "rung3": rung3, "stopped_at": stopped_at}
