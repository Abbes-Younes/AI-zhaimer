"""§6 — feature definitions. Feature extraction stays label-blind."""
from __future__ import annotations

import numpy as np
import yaml

from pearl_features.paths import FEATURES_YAML


class FeaturesConfigError(Exception):
    pass


def load_features_config(path=None) -> dict:
    p = path or FEATURES_YAML
    if not p.exists():
        raise FeaturesConfigError(f"{p} not found.")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    required = ["roi_channels", "harmonics", "aggregation", "dimensionality_budget", "feature_list"]
    for key in required:
        if key not in cfg:
            raise FeaturesConfigError(f"config/features.yaml missing required section '{key}'.")
    return cfg


def fifth_harmonic_index(iaf_hz: float, n_harmonics: int, cycle_freq_hz: float,
                          mains_hz: float = 50.0) -> int:
    """The harmonic index (1-based) whose frequency k*cycle_freq_hz is nearest
    mains_hz. Excluded from the harmonic profile by index, uniformly, per
    subject (phase_2.md §6b) -- never by shifting the profile."""
    candidates = np.arange(1, n_harmonics + 1)
    freqs = candidates * cycle_freq_hz
    return int(candidates[np.argmin(np.abs(freqs - mains_hz))])


def harmonic_amplitude_profile(psr_matrix: np.ndarray, n_harmonics: int,
                                exclude_index: int | None) -> np.ndarray:
    """Per-cycle DFT magnitude of harmonics 1..n_harmonics, normalised to the
    fundamental. exclude_index (1-based) -> NaN column."""
    spectra = np.abs(np.fft.fft(psr_matrix, axis=1))
    profile = spectra[:, 1:n_harmonics + 1] / spectra[:, 1:2]
    if exclude_index is not None:
        profile[:, exclude_index - 1] = np.nan
    return profile


def aggregate_cycles(values: np.ndarray, n_subsample: int, seed: int) -> dict:
    """§6d: fix the cycle count via seeded subsampling, then median/IQR."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < n_subsample:
        raise ValueError(f"only {len(values)} cycles available, need >= {n_subsample} "
                          f"(fixed cycle count, §6d) — this subject should be excluded "
                          f"from feature extraction, not silently under-sampled.")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(values), size=n_subsample, replace=False)
    sample = values[idx]
    q75, q25 = np.percentile(sample, [75, 25])
    return {"median": float(np.median(sample)), "iqr": float(q75 - q25)}


def aggregate_channels(per_channel: dict[str, dict]) -> dict:
    """Median/IQR across ROI channels of each channel's cycle-aggregated median."""
    medians = np.array([v["median"] for v in per_channel.values() if not np.isnan(v["median"])])
    if len(medians) == 0:
        return {"median": float("nan"), "iqr": float("nan")}
    q75, q25 = np.percentile(medians, [75, 25])
    return {"median": float(np.median(medians)), "iqr": float(q75 - q25)}


def waveform_asymmetry(cycle: np.ndarray) -> tuple[float, float]:
    """Rise-decay time ratio and peak-trough sharpness ratio on a broadband cycle."""
    peak_idx = int(np.argmax(cycle))
    trough_idx = int(np.argmin(cycle))
    rise_time = peak_idx if peak_idx > 0 else 1
    decay_time = (len(cycle) - peak_idx) if peak_idx < len(cycle) else 1
    rise_decay_ratio = rise_time / decay_time

    def _sharpness(idx):
        lo, hi = max(0, idx - 1), min(len(cycle) - 1, idx + 1)
        return abs(cycle[hi] - cycle[lo])

    peak_sharp = _sharpness(peak_idx)
    trough_sharp = _sharpness(trough_idx)
    sharpness_ratio = peak_sharp / trough_sharp if trough_sharp > 1e-12 else np.nan
    return rise_decay_ratio, sharpness_ratio


def compute_channel_features(broadband_channel: np.ndarray, iaf_hz: float, sfreq: float,
                              cfg: dict) -> dict:
    from pearl_features.cycles import (
        CycleValidityConfig, extract_valid_cycles, narrowband_copy,
        phase_locked_boundaries, positive_slope_zero_crossings,
    )
    from pearl_features.psr import build_psr_matrix
    from pearl_features.pswt import decompose, demultiplex, harmonic_estimate, inter_harmonic_residual

    nb = narrowband_copy(broadband_channel, sfreq, iaf_hz, cfg["narrowband"]["half_width_hz"])
    crossings = positive_slope_zero_crossings(nb, sfreq)
    boundaries = phase_locked_boundaries(crossings, sfreq)
    validity_cfg = CycleValidityConfig(**cfg["cycle_validity"])
    valid_cycles, cycle_stats = extract_valid_cycles(broadband_channel, boundaries, sfreq,
                                                       iaf_hz, validity_cfg)

    n_sub = cfg["aggregation"]["cycle_subsample_n"]
    if cycle_stats["n_valid"] < n_sub:
        # Below the fixed cycle-count floor this channel will be dropped by
        # compute_subject_features regardless — skip PSR/PSWT construction
        # entirely rather than crashing on an (near-)empty cycle list (PSR's
        # mode-of-lengths and the P>=40 assertion both assume a non-trivial
        # sample).
        return {
            "profile": np.zeros((0, cfg["harmonics"]["n_harmonics"])), "excl_idx": None,
            "cycle_stats": cycle_stats, "detail_energy": np.zeros(0), "hi_ratio": np.zeros(0),
            "period_variability": np.zeros(0), "rise_decay_ratio": np.zeros(0),
            "sharpness_ratio": np.zeros(0),
        }

    psr_matrix = build_psr_matrix(valid_cycles)
    cycle_freq_hz = 1.0 / cycle_stats["median_period_s"]
    excl_idx = fifth_harmonic_index(iaf_hz, cfg["harmonics"]["n_harmonics"], cycle_freq_hz,
                                     cfg["harmonics"]["mains_hz"])

    profile = harmonic_amplitude_profile(psr_matrix, cfg["harmonics"]["n_harmonics"], excl_idx)

    sub = demultiplex(psr_matrix)
    decomp = decompose(sub, wavelet=cfg["pswt"]["wavelet"])
    h_est = harmonic_estimate(decomp, wavelet=cfg["pswt"]["wavelet"])
    residual = inter_harmonic_residual(psr_matrix, h_est)
    detail_energy = np.sum(residual ** 2, axis=1)
    harmonic_energy = np.sum(h_est ** 2, axis=1)
    hi_ratio = np.divide(harmonic_energy, detail_energy,
                          out=np.full_like(harmonic_energy, np.nan), where=detail_energy > 1e-12)

    periods_s = np.array([len(c) for c in valid_cycles]) / sfreq
    period_variability = np.abs(periods_s - np.median(periods_s)) / np.median(periods_s)

    asym = np.array([waveform_asymmetry(c) for c in valid_cycles])

    return {
        "profile": profile, "excl_idx": excl_idx, "cycle_stats": cycle_stats,
        "detail_energy": detail_energy, "hi_ratio": hi_ratio,
        "period_variability": period_variability,
        "rise_decay_ratio": asym[:, 0], "sharpness_ratio": asym[:, 1],
    }


def compute_subject_features(subject: str, cfg: dict, iaf_hz: float,
                              raw=None) -> tuple[dict[str, float], dict]:
    """Orchestrates one subject across cfg['roi_channels']. iaf_hz is passed
    in explicitly (read by the caller from the Phase 1 sidecar — see
    pipeline.py — to keep this function free of file I/O beyond the channel
    loop, which simplifies testing). Returns (feature_dict, meta) where meta
    carries the per-channel excluded harmonic index and cycle stats for
    cycle_stats.csv.

    `raw`, if given, is an already-loaded/cropped mne.io.Raw to extract
    features from directly (used by Phase 3's eyes-open positive control,
    pearl_models.positive_controls) instead of loading the eyes-closed
    window internally — default behaviour (raw=None) is unchanged."""
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments

    if raw is None:
        raw = load_eyes_closed_continuous(subject)
    raw, _, usable_s = reject_artifact_segments(raw, cfg)
    sfreq = raw.info["sfreq"]
    ch_names = [ch for ch in cfg["roi_channels"] if ch in raw.ch_names]
    data = raw.get_data(picks=ch_names)

    n_sub = cfg["aggregation"]["cycle_subsample_n"]
    seed = cfg["aggregation"]["seed"]
    n_h = cfg["harmonics"]["n_harmonics"]

    per_channel_h = {h: {} for h in range(1, n_h + 1)}
    per_channel_hi, per_channel_cc, per_channel_pv = {}, {}, {}
    per_channel_rd, per_channel_pt = {}, {}
    excl_indices, cycle_stats_by_channel = {}, {}
    dropped_channels = []

    for ch_idx, ch in enumerate(ch_names):
        r = compute_channel_features(data[ch_idx], iaf_hz, sfreq, cfg)
        # A channel with fewer valid cycles than the fixed subsample floor is
        # dropped from this subject's ROI average rather than failing the
        # whole subject — §6d's fixed-count rule controls per-subject
        # estimator variance; one noisy occipital site among the ROI's 15
        # should not veto an otherwise usable subject.
        if r["cycle_stats"]["n_valid"] < n_sub:
            dropped_channels.append(ch)
            continue
        excl_indices[ch] = r["excl_idx"]
        cycle_stats_by_channel[ch] = r["cycle_stats"]
        for h in range(1, n_h + 1):
            if h == r["excl_idx"]:
                # this harmonic column is all-NaN by design (§6b, the
                # per-subject 50Hz-nearest index) — mark it NaN directly
                # rather than passing an all-NaN column through
                # aggregate_cycles, which raises on "too few real cycles"
                # without distinguishing that from "intentionally excluded".
                per_channel_h[h][ch] = {"median": float("nan"), "iqr": float("nan")}
            else:
                per_channel_h[h][ch] = aggregate_cycles(r["profile"][:, h - 1], n_sub, seed)
        per_channel_hi[ch] = aggregate_cycles(r["hi_ratio"], n_sub, seed)
        per_channel_cc[ch] = aggregate_cycles(r["detail_energy"], n_sub, seed)
        per_channel_pv[ch] = aggregate_cycles(r["period_variability"], n_sub, seed)
        per_channel_rd[ch] = aggregate_cycles(r["rise_decay_ratio"], n_sub, seed)
        per_channel_pt[ch] = aggregate_cycles(r["sharpness_ratio"], n_sub, seed)

    if len(dropped_channels) > len(ch_names) / 2:
        raise ValueError(
            f"{subject}: {len(dropped_channels)}/{len(ch_names)} ROI channels had fewer than "
            f"{n_sub} valid cycles ({dropped_channels}) — too few surviving channels to trust "
            f"a ROI average; excluding this subject rather than averaging over a minority.")

    out = {}
    for h in range(1, n_h + 1):
        agg = aggregate_channels(per_channel_h[h])
        out[f"harmonic_amplitude_profile_h{h}_median"] = agg["median"]
        out[f"harmonic_amplitude_profile_h{h}_iqr"] = agg["iqr"]
    for name, per_ch in [("harmonic_to_interharmonic_ratio", per_channel_hi),
                          ("cycle_to_cycle_variability", per_channel_cc),
                          ("period_variability", per_channel_pv),
                          ("rise_decay_ratio", per_channel_rd),
                          ("peak_trough_sharpness_ratio", per_channel_pt)]:
        agg = aggregate_channels(per_ch)
        out[f"{name}_median"] = agg["median"]
        out[f"{name}_iqr"] = agg["iqr"]

    meta = {
        "usable_duration_s": usable_s,
        "excluded_harmonic_index": max(set(excl_indices.values()), key=list(excl_indices.values()).count),
        "cycle_stats_by_channel": cycle_stats_by_channel,
        "dropped_channels": dropped_channels,
    }
    return out, meta
