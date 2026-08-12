"""Track B -- multitaper time-frequency-area (TFA) features (phase_5_stage2.md
§2, frozen design: reports/phase5_stage2_plan_frozen.md). A good-faith,
principled reconstruction of "multitaper time-frequency area" -- this
project does not have the published paper's exact algorithm, and that
distinction must be carried into any report using this module's output.
"""
from __future__ import annotations

import re

import numpy as np
from mne.time_frequency import psd_array_multitaper

BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 45)}
BANDWIDTH_HZ = 4.0

_MARKER_CODE_RE = re.compile(r"S\s*(\d+)\s*$")


def _band_area(psd: np.ndarray, freqs: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs < band[1])
    return float(np.trapezoid(psd[mask], freqs[mask])) if mask.any() else 0.0


def _fit_aperiodic(psd: np.ndarray, freqs: np.ndarray) -> tuple[float, float]:
    """Same 1/f heuristic as baseline.aperiodic_fit, applied to an
    already-computed PSD (never re-runs multitaper on a raw signal -- see
    multitaper_psd_batch's docstring for why that matters)."""
    mask = ((freqs >= 1) & (freqs < 8)) | ((freqs >= 13) & (freqs <= 45))
    log_f = np.log10(freqs[mask])
    log_p = np.log10(np.clip(psd[mask], 1e-20, None))
    slope, offset = np.polyfit(log_f, log_p, 1)
    return float(offset), float(slope)


def multitaper_psd_batch(segments: np.ndarray, sfreq: float) -> tuple[np.ndarray, np.ndarray]:
    """Multitaper PSD over many equal-length segments (shape (n_segments,
    n_samples)) in one call -> (psd (n_segments, n_freqs), freqs).

    DPSS taper computation is an eigenvalue problem whose cost grows very
    steeply with segment length -- calling this on a single ~600s
    whole-recording segment (152185 samples) measured at over 1500 seconds
    per subject; the same call on 147 separate 4-second (1000-sample)
    segments takes ~0.04s combined. **Always window/epoch first, this
    module has no whole-recording multitaper path for that reason** -- the
    aperiodic fit below reuses these same per-window PSDs (averaged) rather
    than a second, longer, separately-computed one."""
    psd, freqs = psd_array_multitaper(
        segments, sfreq, fmin=1, fmax=45, bandwidth=BANDWIDTH_HZ,
        normalization="length", verbose=False)
    if psd.ndim == 1:
        psd = psd[np.newaxis, :]
    return psd, freqs


def band_areas_from_psd_batch(psd: np.ndarray, freqs: np.ndarray) -> list[dict[str, float]]:
    """Per-row relative band areas, normalized by total 1-45 Hz power each
    row (matching baseline.relative_band_powers's convention, frozen plan §2a)."""
    out = []
    for row in psd:
        total = _band_area(row, freqs, (1, 45))
        out.append({name: (_band_area(row, freqs, band) / total if total > 0 else 0.0)
                     for name, band in BANDS.items()})
    return out


def multitaper_band_areas(data: np.ndarray, sfreq: float) -> dict[str, float]:
    """Single-segment convenience wrapper (tests / one-off use only -- see
    multitaper_psd_batch's docstring on why real pipelines must window
    first, not call this repeatedly in a loop)."""
    psd, freqs = multitaper_psd_batch(data[np.newaxis, :], sfreq)
    return band_areas_from_psd_batch(psd, freqs)[0]


def aggregate_tfa_features(window_areas: list[dict[str, float]], aperiodic: tuple[float, float],
                            prefix: str) -> dict[str, float]:
    """mean+IQR per band across a list of per-window/per-epoch area dicts,
    plus the once-per-scope aperiodic offset/slope (frozen plan §2c)."""
    out: dict[str, float] = {}
    for name in BANDS:
        vals = np.array([w[name] for w in window_areas])
        out[f"{prefix}tfa_{name}_mean"] = float(np.mean(vals)) if len(vals) else float("nan")
        out[f"{prefix}tfa_{name}_iqr"] = (
            float(np.percentile(vals, 75) - np.percentile(vals, 25)) if len(vals) else float("nan"))
    out[f"{prefix}tfa_aperiodic_offset"] = aperiodic[0]
    out[f"{prefix}tfa_aperiodic_slope"] = aperiodic[1]
    return out


def windowed_tfa(raw, picks: list[str], window_s: float = 4.0) -> dict[str, float]:
    """Whole-recording, non-overlapping windows -- MSIT (no reliable
    condition split found, frozen plan §3a). One multitaper call over all
    windows; band areas and the aperiodic fit (on the windows' mean PSD)
    both come from that same call -- no separate whole-recording multitaper
    pass (see multitaper_psd_batch)."""
    data = raw.get_data(picks=picks).mean(axis=0)
    sfreq = raw.info["sfreq"]
    win_n = int(window_s * sfreq)
    n_windows = data.shape[0] // win_n
    segments = data[:n_windows * win_n].reshape(n_windows, win_n)
    psd, freqs = multitaper_psd_batch(segments, sfreq)
    areas = band_areas_from_psd_batch(psd, freqs)
    aperiodic = _fit_aperiodic(psd.mean(axis=0), freqs)
    return aggregate_tfa_features(areas, aperiodic, prefix="")


def marker_onsets_with_min_gap(raw, code: int, min_gap_s: float) -> tuple[np.ndarray, int]:
    """Onsets (seconds) of annotation marker `code` (matches 'S <code>' at
    the end of the description, e.g. 'Stimulus/S  4' -> 4) whose gap to the
    immediately following annotation (any type) is >= min_gap_s -- the
    frozen-plan §3b skip rule: a trial whose actual window would overlap the
    next event is dropped, not truncated or zero-padded. Returns
    (onsets, n_skipped)."""
    order = np.argsort(raw.annotations.onset)
    onsets = np.asarray(raw.annotations.onset)[order]
    descs = np.asarray(raw.annotations.description)[order]

    kept: list[float] = []
    skipped = 0
    for i, (onset, desc) in enumerate(zip(onsets, descs)):
        m = _MARKER_CODE_RE.search(str(desc))
        if not m or int(m.group(1)) != code:
            continue
        if i + 1 >= len(onsets) or (onsets[i + 1] - onset) < min_gap_s:
            skipped += 1
            continue
        kept.append(float(onset))
    return np.array(kept), skipped


def epoch_locked_tfa(raw, picks: list[str], onsets_s: np.ndarray, duration_s: float,
                      prefix: str) -> dict[str, float]:
    """Fixed-duration windows locked to pre-filtered event onsets (already
    passed through marker_onsets_with_min_gap) -- Sternberg encoding/
    retrieval (frozen plan §3b). One multitaper call over all epochs; band
    areas and the aperiodic fit (on the epochs' mean PSD) both come from
    that same call."""
    data = raw.get_data(picks=picks).mean(axis=0)
    sfreq = raw.info["sfreq"]
    n_samples = int(duration_s * sfreq)
    total = data.shape[0]

    segments = []
    for onset in onsets_s:
        start = int(round(onset * sfreq))
        end = start + n_samples
        if end > total:
            continue
        segments.append(data[start:end])

    if segments:
        psd, freqs = multitaper_psd_batch(np.stack(segments), sfreq)
        areas = band_areas_from_psd_batch(psd, freqs)
        aperiodic = _fit_aperiodic(psd.mean(axis=0), freqs)
    else:
        areas, aperiodic = [], (float("nan"), float("nan"))
    return aggregate_tfa_features(areas, aperiodic, prefix=prefix)
