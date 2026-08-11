"""Per-(subject, task) preprocessing pipeline (phase_1.md §2).

Label-blind by construction: this module neither imports nor receives any
group/risk information, and every threshold comes from config/preproc.yaml.

Pipeline: read BrainVision → montage → average reference → statistical bad
channels → interpolate → 0.5 Hz zero-phase FIR high-pass → anti-alias +
resample to the task's target rate (500 rest / 250 msit, from config) →
line-noise removal (spectral interpolation if available, else ≤1 Hz notch) →
ICA (fit on a 1 Hz high-passed copy, applied to the 0.5 Hz data; ICLabel
exclusion at a fixed probability threshold) → save continuous derivative +
ICA solution + full provenance sidecar.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

from . import montage as montage_mod
from .config import target_sfreq
from .paths import (
    PREPROC_DIR,
    RAW_DIR,
    get_run_id,
    git_sha,
    participants_tsv_sha256,
    sha256_file,
)
from .triplets import validate_triplet

PIPELINE_VERSION = "1.0.0"

_ARTIFACT_CLASSES = ["brain", "muscle artifact", "eye blink", "heart beat",
                     "line noise", "channel noise", "other"]


class PreprocessError(Exception):
    """Preprocessing failed for a (subject, task) recording."""


def _excluded_classes_idx(cfg: dict) -> list[int]:
    classes = cfg.get("ica", {}).get("excluded_classes",
                                     ["muscle artifact", "eye blink",
                                      "heart beat", "line noise", "channel noise"])
    return [i for i, c in enumerate(_ARTIFACT_CLASSES) if c in classes]


# ---------------------------------------------------------------------------
# Filter spec (canonical, recorded verbatim in the sidecar)
# ---------------------------------------------------------------------------

def filter_spec(cfg: dict) -> dict:
    """The exact filter configuration applied — round-trips into sidecars."""
    return {
        "high_pass": dict(cfg["filters"]["high_pass"]),
        "anti_alias_factor": cfg["filters"]["anti_alias_factor"],
        "ica_fit_high_pass_hz": cfg["filters"]["ica_fit_high_pass_hz"],
    }


# ---------------------------------------------------------------------------
# Bad channel detection (fixed statistical criteria, config thresholds)
# ---------------------------------------------------------------------------

def detect_bad_channels(raw: mne.io.BaseRaw, cfg: dict,
                        occipital_set: set[str]) -> tuple[list[str], int]:
    """Return (bad_names, n_occipital_bads) from flat/high-var/low-corr rules."""
    bcfg = cfg.get("bad_channels", {})
    flat_thr = float(bcfg.get("flat_std_v", 1e-8))
    var_z = float(bcfg.get("variance_z_threshold", 4.0))
    corr_thr = float(bcfg.get("neighbor_corr_threshold", 0.4))
    n_nb = int(bcfg.get("n_neighbors", 3))

    data = raw.get_data()
    std = np.std(data, axis=1)
    bads = set(np.where(std < flat_thr)[0].tolist())

    logvar = np.log(np.var(data, axis=1) + 1e-30)
    med = np.median(logvar)
    mad = np.median(np.abs(logvar - med)) * 1.4826 + 1e-30
    z = (logvar - med) / mad
    bads |= set(np.where(np.abs(z) > var_z)[0].tolist())

    pos = raw.get_montage().get_positions()["ch_pos"]
    ch_pos = np.array([pos[c] for c in raw.ch_names])
    for idx in range(raw.info["nchan"]):
        if idx in bads:
            continue
        d = np.linalg.norm(ch_pos - ch_pos[idx], axis=1)
        d[idx] = np.inf
        nb = np.argsort(d)[:n_nb]
        corr = np.corrcoef(data[idx], data[nb].mean(axis=0))[0, 1]
        if corr < corr_thr:
            bads.add(idx)

    names = [raw.ch_names[i] for i in sorted(bads)]
    occ_bads = sum(1 for n in names if n in occipital_set)
    return names, occ_bads


# ---------------------------------------------------------------------------
# Line-noise index (narrow 50 Hz peak vs local baseline, for QC before/after)
# ---------------------------------------------------------------------------

def _line_noise_index(raw: mne.io.BaseRaw, f_center: float = 50.0,
                      half: float = 0.5, duration_s: float = 60.0) -> float:
    """Ratio of power at [f_center±half] to the [44,46]∪[54,56] baseline.

    ≈1.0 means no line-noise spike; ≫1 means a real 50 Hz peak. Broad-band
    muscle power is common in the 45-55 Hz band, which is exactly why the
    metric is narrow and baseline-relative rather than raw band power.
    """
    import mne.time_frequency as tf
    crop = raw.copy().crop(tmax=min(duration_s, raw.times[-1]))
    data = crop.get_data()
    sfreq = crop.info["sfreq"]
    psds, freqs = tf.psd_array_welch(
        data, sfreq, fmin=44.0, fmax=56.0, n_fft=int(sfreq * 4),
        n_overlap=int(sfreq * 2), verbose="ERROR")
    psd = np.mean(psds, axis=0)
    peak_mask = (freqs >= f_center - half) & (freqs <= f_center + half)
    base_mask = ((freqs >= 44.0) & (freqs <= 46.0)) | \
                ((freqs >= 54.0) & (freqs <= 56.0))
    peak = float(np.mean(psd[peak_mask]))
    base = float(np.mean(psd[base_mask]))
    return peak / max(base, 1e-30)


# ---------------------------------------------------------------------------
# ICA exclusion (ICLabel with fixed threshold; conservative fallback)
# ---------------------------------------------------------------------------

def _ica_labels_fallback(raw, ica, exclude_threshold: float,
                         frontal: tuple[str, ...]) -> tuple[list[int], list[str]]:
    """ICLabel-equivalent: frontal-correlation EOG + high-frequency muscle.

    Used only if mne_icalabel is not importable. Thresholds are the same fixed
    config values applied uniformly. Recorded as 'ICLabel-equivalent' in the
    sidecar so Phase 2 can tell the difference.
    """
    sources = ica.get_sources(raw).get_data()
    excluded, labels = [], []
    for idx in range(sources.shape[0]):
        src = sources[idx]
        eog_r = max(
            abs(float(np.corrcoef(src, raw.get_data(picks=[ch])[0])[0, 1]))
            for ch in frontal if ch in raw.ch_names
        ) if frontal else 0.0
        freqs, psd = mne.time_frequency.psd_array_welch(
            src[None, :], ica.info["sfreq"], fmin=1, fmax=45,
            n_fft=int(ica.info["sfreq"] * 2), verbose="ERROR")
        above_20 = np.where(freqs >= 20)[0]
        if len(above_20) == 0 or above_20[0] == 0:
            # Degenerate PSD (e.g. very short source segment coarsens
            # frequency resolution below what fmin/fmax would suggest) --
            # no usable low/high split, so this fallback criterion can't
            # fire for this component. Found via the real container smoke
            # test (phase_4.md Task D): this fallback path had never
            # actually been exercised before (onnxruntime/torch were always
            # present on the dev host by accident), so this crash was
            # latent and untested.
            muscle_ratio = 0.0
        else:
            idx20 = above_20[0]
            muscle_ratio = float(np.mean(psd[0, idx20:]) / np.mean(psd[0, :idx20]))
        if eog_r > exclude_threshold:
            excluded.append(idx); labels.append("eye blink")
        elif muscle_ratio > 3.0:  # fixed conservative muscle criterion
            excluded.append(idx); labels.append("muscle artifact")
    return excluded, labels


def fit_and_exclude_ica(raw: mne.io.BaseRaw, cfg: dict,
                        excluded_classes_idx: list[int]) -> tuple[mne.preprocessing.ICA, list[int], list[str], str]:
    """Fit ICA on a 1 Hz HP copy; exclude artifact components; return
    (ica, excluded_components, labels, labeling_method)."""
    import mne.preprocessing as pp

    ica_cfg = cfg.get("ica", {})
    _n_comp_raw = ica_cfg.get("n_components", 30)
    # MNE's ICA accepts n_components as an int (fixed component count) or a
    # float in (0, 1) (explained-variance-ratio selection) -- forcing
    # int(...) here used to silently truncate e.g. 0.99 -> 0 (phase_5.md
    # §0b's ICA n_components re-evaluation needs the float form to work).
    n_comp = float(_n_comp_raw) if isinstance(_n_comp_raw, float) else int(_n_comp_raw)
    threshold = float(ica_cfg.get("exclude_threshold", 0.8))
    method = ica_cfg.get("method", "infomax")
    rs = int(ica_cfg.get("random_state", 42))

    # ICLabel was designed for extended infomax decompositions; that is the
    # default pairing. fit_params are recorded in the sidecar for audit.
    if method == "infomax":
        fit_params = {"extended": True}
    elif method == "fastica":
        fit_params = {"max_iter": 500}
    else:
        fit_params = None

    hp = float(cfg["filters"]["ica_fit_high_pass_hz"])
    # ICLabel is trained on 1-100 Hz bandpassed data; band-limit the fit copy
    # (the applied data keeps its full bandwidth).
    fit_raw = raw.copy().filter(l_freq=hp, h_freq=100.0, method="fir",
                                fir_design="firwin", phase="zero", verbose="ERROR")
    ica = pp.ICA(n_components=n_comp, method=method, random_state=rs,
                 fit_params=fit_params)
    ica.fit(fit_raw, verbose="ERROR")

    excluded, labels = [], []
    labeling = "ICLabel"
    try:
        from mne_icalabel.iclabel import iclabel_label_components
        probs = iclabel_label_components(fit_raw, ica, inplace=False)
        for comp in range(probs.shape[0]):
            p_art = float(np.max([probs[comp, i] for i in excluded_classes_idx]))
            if p_art > threshold:
                excluded.append(int(comp))
                labels.append(str(_ARTIFACT_CLASSES[int(np.argmax(probs[comp]))]))
    except ImportError:
        labeling = "ICLabel-equivalent"
        excluded, labels = _ica_labels_fallback(
            raw, ica, threshold, ("Fp1", "Fp2", "AFp1", "AFp2"))

    if excluded:
        ica.apply(raw, exclude=excluded, verbose="ERROR")
    return ica, excluded, labels, labeling


# ---------------------------------------------------------------------------
# Eyes-closed rest window (remediation 2026-08-09 — see reports/phase1_qc.html
# escalation and phase_1.md §8)
#
# The PEARL-Neuro rest recording is ONE file: 4 min eyes-open ending at
# marker `S 10`, then 6 min eyes-closed starting at the next `S  1` and
# ending at `S 11` (data/raw_meta/task-rest_eeg.json). `S 2`/`S 4` are
# sub-markers that are inconsistently present and must never be required.
# Surveyed across all 77 rest derivatives on disk: covers every marker
# pattern observed (missing S2/S4, missing S11, leading "New Segment/",
# recording starting at S10, trailing S1 after S11, and an anomalously
# large S10->S1 gap on 3 subjects).
# ---------------------------------------------------------------------------

def eyes_closed_window(annotations, tmax: float,
                       max_start_gap_s: float = 60.0,
                       min_duration_s: float = 120.0) -> tuple[float, float] | None:
    """Resolve the eyes-closed block from BrainVision stimulus annotations.

    Returns (start_s, end_s) or None if no usable window can be resolved
    (no `S 10` marker at all, or the resolved window is degenerately short).
    """
    desc = [str(d).split("/")[-1].strip() for d in annotations.description]
    onset = [float(o) for o in annotations.onset]

    i10 = next((i for i, d in enumerate(desc) if d == "S 10"), None)
    if i10 is None:
        return None
    t10 = onset[i10]

    start = t10
    for j in range(i10 + 1, len(desc)):
        if desc[j] == "S  1":
            if onset[j] - t10 <= max_start_gap_s:
                start = onset[j]
            # else: the marker is unreliably far away — fall back to S 10
            break

    end = tmax
    for j in range(i10 + 1, len(desc)):
        if desc[j] == "S 11" and onset[j] > start:
            end = onset[j]
            break

    if end - start < min_duration_s:
        return None
    return (start, end)


def eyes_open_window(annotations, tmax: float, min_duration_s: float = 60.0) -> tuple[float, float] | None:
    """Resolve the eyes-open block: recording start up to the first `S 10`
    marker (phase_3.md §1a positive control). Returns None if there is no
    `S 10` marker, or the resulting window is shorter than min_duration_s."""
    desc = [str(d).split("/")[-1].strip() for d in annotations.description]
    onset = [float(o) for o in annotations.onset]

    i10 = next((i for i, d in enumerate(desc) if d == "S 10"), None)
    if i10 is None:
        return None
    t10 = onset[i10]

    if t10 < min_duration_s:
        return None
    return (0.0, t10)


def select_iaf_excerpt(raw: mne.io.BaseRaw, cfg: dict, task: str):
    """Pick the excerpt IAF is estimated on; return (excerpt_raw, window_info).

    For tasks requiring alpha (rest), use the eyes-closed block when the
    markers resolve one. Otherwise fall back to the original blind
    crop(tmax=120) — unchanged behaviour for MSIT and for any rest recording
    whose markers don't resolve.
    """
    iaf_cfg = cfg.get("iaf", {})
    require_tasks = set(iaf_cfg.get("require_for_tasks", []))
    task_key = task if task.startswith("task-") else f"task-{task}"

    window = None
    if task_key in require_tasks:
        window = eyes_closed_window(
            raw.annotations, raw.times[-1],
            max_start_gap_s=float(iaf_cfg.get("eyes_closed_max_start_gap_s", 60.0)),
            min_duration_s=float(iaf_cfg.get("eyes_closed_min_duration_s", 120.0)))

    if window is not None:
        start, end = window
        excerpt = raw.copy().crop(tmin=start, tmax=min(end, raw.times[-1]))
        info = {"method": "eyes_closed", "tmin_s": round(start, 2),
               "tmax_s": round(min(end, raw.times[-1]), 2)}
    else:
        tmax = min(120.0, raw.times[-1])
        excerpt = raw.copy().crop(tmax=tmax)
        info = {"method": "blind_crop", "tmin_s": 0.0, "tmax_s": round(tmax, 2)}
    return excerpt, info


# ---------------------------------------------------------------------------
# IAF estimation (synthetic-10-Hz-testable, pure numpy)
# ---------------------------------------------------------------------------

def estimate_iaf(data: np.ndarray, sfreq: float, band_hz: tuple[float, float],
                 min_prominence_db: float) -> dict:
    """IAF from a (n_ch, n_times) excerpt over the given channels.

    Welch PSD → average spectrum → log-power peak within band_hz; 1/f baseline
    fitted over [2,6]∪[16,30] Hz in log-log space; peak height in dB.
    """
    import mne.time_frequency as tf
    fmin, fmax = band_hz
    psds, freqs = tf.psd_array_welch(
        data, sfreq, fmin=2.0, fmax=min(30.0, sfreq / 2 - 1),
        n_fft=int(sfreq * 4), n_overlap=int(sfreq * 2), verbose="ERROR")
    psd = np.mean(psds, axis=0)
    log_psd, log_f = np.log10(psd), np.log10(freqs)

    in_band = (freqs >= fmin) & (freqs <= fmax)
    idx_iaf = int(np.argmax(log_psd[in_band]))
    iaf = float(freqs[in_band][idx_iaf])

    base = ~in_band & (freqs >= 2.0) & (freqs <= 30.0)
    if base.sum() < 5:
        return {"iaf_hz": iaf, "peak_height_db": 0.0, "present": False}
    slope, intercept = np.polyfit(log_f[base], log_psd[base], 1)
    baseline_db = 10.0 * (slope * np.log10(iaf) + intercept)
    peak_db = 10.0 * log_psd[in_band][idx_iaf]
    height_db = float(peak_db - baseline_db)
    return {"iaf_hz": round(iaf, 2), "peak_height_db": round(height_db, 2),
            "present": bool(height_db >= min_prominence_db)}


def artifact_fraction(raw: mne.io.BaseRaw, peak_v: float,
                      window_s: float = 1.0) -> float:
    """Fraction of fixed windows where ANY channel's PTP exceeds peak_v.

    A direct, deterministic measure. MNE's ``annotate_amplitude`` flags on
    consecutive-sample *differences* (``abs(a[i+1]-a[i])``), which both misses
    blinks/movement (their per-sample slope is far below the peak threshold)
    and mislabels quiet resting signal as BAD_flat — measured 49% "artifact"
    on sub-01 rest whose peak-to-peak is exceeded by only 0.4% of samples.
    Windowed peak-to-peak is what "how much of the recording is artifact"
    actually means, and it is deterministic across MNE versions.
    """
    data = raw.get_data()
    sfreq = float(raw.info["sfreq"])
    win = max(1, int(round(sfreq * window_s)))
    n_win = data.shape[1] // win
    if n_win == 0:
        return 0.0
    x = data[:, :n_win * win].reshape(data.shape[0], n_win, win)
    ptp = x.max(axis=2) - x.min(axis=2)
    return float((ptp > peak_v).any(axis=0).mean())


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def raw_paths_for(subject: str, task: str) -> dict[str, Path]:
    base = RAW_DIR / subject / "eeg"
    return {
        "vhdr": base / f"{subject}_task-{task}_eeg.vhdr",
        "eeg": base / f"{subject}_task-{task}_eeg.eeg",
        "vmrk": base / f"{subject}_task-{task}_eeg.vmrk",
        "events": base / f"{subject}_task-{task}_events.tsv",
    }


def derivative_exists(subject: str, task: str) -> bool:
    """A valid derivative = preproc fif + sidecar + ica fif all present."""
    d = PREPROC_DIR / subject / "eeg"
    stem = f"{subject}_task-{task}"
    return all((d / f"{stem}_desc-preproc_eeg.fif").exists()
               and (d / f"{stem}_desc-preproc_eeg.json").exists()
               and (d / f"{stem}_desc-ica_components.fif").exists()
               for _ in [0])


def _write_header_repair(vhdr_path: Path, triplet: dict) -> tuple[Path, list[Path]]:
    """Write a temp .vhdr/.vmrk pair with DataFile/MarkerFile corrected to the
    canonical BIDS siblings, so MNE can read a header that still names a
    stale pre-BIDS recording (validate_triplet's `header_discrepancy`).
    Original files are never modified. Caller deletes the returned paths."""
    eeg_name = Path(triplet["eeg"]).name
    vmrk_name = Path(triplet["vmrk"]).name
    repaired_vhdr = vhdr_path.parent / f"{vhdr_path.stem}._header_repair.vhdr"
    repaired_vmrk = vhdr_path.parent / f"{vhdr_path.stem}._header_repair.vmrk"

    vhdr_text = vhdr_path.read_text(encoding="latin-1")
    vhdr_text = re.sub(r"^DataFile=.+$", f"DataFile={eeg_name}", vhdr_text, flags=re.M)
    vhdr_text = re.sub(r"^MarkerFile=.+$", f"MarkerFile={vmrk_name}", vhdr_text, flags=re.M)
    repaired_vhdr.write_text(vhdr_text, encoding="latin-1")

    vmrk_text = Path(triplet["vmrk"]).read_text(encoding="latin-1")
    vmrk_text = re.sub(r"^DataFile=.+$", f"DataFile={eeg_name}", vmrk_text, flags=re.M)
    repaired_vmrk.write_text(vmrk_text, encoding="latin-1")

    return repaired_vhdr, [repaired_vhdr, repaired_vmrk]


def resolve_output_dir(subject: str, output_dir: Path | None, run_id_active: bool,
                       existing_fif: Path | None, overwrite_existing: bool = False,
                       live_dir: Path | None = None) -> Path:
    """Guard against silently overwriting a live derivative (phase_5.md
    Stage 1 incident, 2026-08-11): a direct, non-orchestrated call to
    process_subject_task against a subject that already has a derivative on
    the live PREPROC_DIR path used to overwrite it unconditionally, with no
    protection. The orchestrated pipeline (pearl_preproc.pipeline) never
    hits this -- it checks derivative_exists() and skips subjects that
    already have one. This guard targets exactly the case that skip logic
    doesn't cover.

    - `output_dir` given -> always honoured (safe by construction, e.g. a
      scratch directory for experimentation).
    - `output_dir` is None and no existing derivative -> live_dir, no guard needed.
    - `output_dir` is None, an existing derivative is present, and a
      pipeline run_id is active -> live_dir (the orchestrated pipeline's own
      reprocessing path; trusted).
    - `output_dir` is None, an existing derivative is present, no run_id
      active, and overwrite_existing is not explicitly True -> raise.
    """
    if output_dir is not None:
        return output_dir
    if live_dir is None:
        live_dir = PREPROC_DIR
    if existing_fif is not None and existing_fif.exists() and not run_id_active and not overwrite_existing:
        raise PreprocessError(
            f"{existing_fif} already exists and this call is not running under an "
            f"active pipeline run_id -- refusing to overwrite it silently. If this is "
            f"deliberate ad-hoc reprocessing of a real subject, pass "
            f"overwrite_existing=True explicitly. If this is experimentation/comparison "
            f"work, pass output_dir=<scratch path> instead so the live derivative tree "
            f"is never touched.")
    return live_dir


def process_subject_task(subject: str, task: str, cfg: dict,
                         output_dir: Path | None = None,
                         overwrite_existing: bool = False) -> dict:
    """Run the full pipeline for one (subject, task); return the QC metrics.

    `output_dir`, if given, redirects the derivative write to that directory
    instead of the live PREPROC_DIR -- use this for any ad-hoc experimentation
    or comparison work (phase_5.md Stage 1) so the live tree is never at risk.
    `overwrite_existing` explicitly acknowledges an intentional overwrite of
    an existing live derivative outside a pipeline run -- see
    resolve_output_dir's docstring.
    """
    paths = raw_paths_for(subject, task)
    if not paths["vhdr"].exists():
        raise PreprocessError(f"{paths['vhdr']} missing — run download first")

    # Fail fast on the overwrite guard before doing any expensive work —
    # the write-time check below is the authoritative one (state can't have
    # changed in between for a single synchronous call), this is purely to
    # avoid burning minutes of preprocessing on a call that's doomed to be
    # refused at the end anyway.
    _live_dir = PREPROC_DIR / subject / "eeg"
    resolve_output_dir(
        subject, output_dir, run_id_active=get_run_id() is not None,
        existing_fif=_live_dir / f"{subject}_task-{task}_desc-preproc_eeg.fif",
        overwrite_existing=overwrite_existing, live_dir=_live_dir)

    # 1. Triplet validation (orphaned .vhdr = silent corruption). A stale
    #    pre-BIDS DataFile/MarkerFile name that still resolves to a
    #    consistent canonical sibling (sub-52) is tolerated but not silent —
    #    read_vhdr points MNE at a repaired temp copy; the originals are
    #    untouched and still what Sources[].sha256 hashes below.
    triplet = validate_triplet(paths["vhdr"])
    read_vhdr, repair_paths = (
        _write_header_repair(paths["vhdr"], triplet) if triplet["header_discrepancy"]
        else (paths["vhdr"], []))
    try:
        native_sfreq = mne.io.read_raw_brainvision(
            read_vhdr, preload=False, verbose="ERROR").info["sfreq"]

        # 2. Read + montage (reference NOT set yet — see step 5)
        raw = mne.io.read_raw_brainvision(read_vhdr, preload=True, verbose="ERROR")
        raw.set_montage(montage_mod.build_montage(read_vhdr))
    finally:
        for p in repair_paths:
            p.unlink(missing_ok=True)
    original_ref = _vhdr_reference(paths["vhdr"])

    # 3. High-pass 0.5 Hz (zero-phase FIR — waveform-shape safe). Done BEFORE
    #    bad-channel detection: the raw data is DC-coupled (hardware low-cutoff
    #    DC), so per-channel DC drift would otherwise dominate variance and
    #    correlation measures and mass-flag healthy channels.
    hp = cfg["filters"]["high_pass"]
    raw.filter(l_freq=hp["l_freq_hz"], h_freq=None, method=hp.get("method", "fir"),
               phase=hp.get("phase", "zero"), fir_design=hp.get("fir_design", "firwin"),
               verbose="ERROR")

    # 4. Bad channels → interpolate (occipital concentration = exclusion flag).
    #    Runs BEFORE referencing (phase_5.md §0a fix): detection/interpolation
    #    must happen on the original FCz-referenced data, not the average
    #    reference, so a bad channel cannot contaminate the reference signal
    #    used to detect it or any other channel.
    occ = set(cfg.get("qc", {}).get("occipital_channels", []))
    bad_names, occ_bads = detect_bad_channels(raw, cfg, occ)
    if bad_names:
        raw.info["bads"] = bad_names
        raw.interpolate_bads(reset_bads=True, verbose="ERROR")

    # 5. Average reference, now over the clean (post-interpolation) channel
    #    set (moved down from step 2 — phase_5.md §0a).
    raw.set_eeg_reference("average", projection=bool(cfg.get("reference", {}).get("projection", True)))
    raw.apply_proj()

    # 6. Anti-alias + resample to the task's target rate (from config)
    target = target_sfreq(cfg, task)
    anti_alias = float(cfg["filters"]["anti_alias_factor"]) * target / 2
    if anti_alias < native_sfreq / 2:
        raw.filter(l_freq=None, h_freq=anti_alias, method="fir", phase="zero",
                   fir_design="firwin", verbose="ERROR")
    raw.resample(target, npad="auto", verbose="ERROR")

    # 7. Line-noise removal (zap_line if available, else ≤1 Hz FIR notch)
    ln_cfg = cfg["line_noise"]
    ln_before = _line_noise_index(raw)
    ln_method = "narrow_notch_fir"
    try:
        from mne.preprocessing import zap_line  # noqa: F401
        zap_line(raw, freqs=ln_cfg["freqs_hz"])
        ln_method = "zap_line"
    except ImportError:
        raw.notch_filter(freqs=ln_cfg["freqs_hz"],
                         notch_widths=ln_cfg["notch_width_hz"],
                         method="fir", phase="zero", verbose="ERROR")
    ln_after = _line_noise_index(raw)

    # 8. ICA (fit on 1 Hz copy, apply to 0.5 Hz data)
    excluded_idx = _excluded_classes_idx(cfg)
    ica, excluded, labels, labeling = fit_and_exclude_ica(raw, cfg, excluded_idx)

    # 9. QC facts computed on the final signal
    iaf_cfg = cfg.get("iaf", {})
    occ_picks = mne.pick_channels(raw.ch_names, include=iaf_cfg.get("channels", []))
    excerpt, iaf_window = select_iaf_excerpt(raw, cfg, task)
    iaf = estimate_iaf(excerpt.get_data(picks=occ_picks), target,
                       tuple(iaf_cfg.get("band_hz", [7, 13])),
                       float(iaf_cfg.get("min_peak_prominence_db", 3.0)))
    art_cfg = cfg.get("artifact_annotation", {})
    artifact_frac = artifact_fraction(
        raw, float(art_cfg.get("peak_v", 1.5e-4)),
        float(art_cfg.get("window_s", 1.0)))

    # 10. Write derivative + ICA solution + provenance sidecar
    stem = f"{subject}_task-{task}"
    live_dir = PREPROC_DIR / subject / "eeg"
    existing_fif = live_dir / f"{stem}_desc-preproc_eeg.fif"
    out_dir = resolve_output_dir(
        subject, output_dir, run_id_active=get_run_id() is not None,
        existing_fif=existing_fif, overwrite_existing=overwrite_existing,
        live_dir=live_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fif_path = out_dir / f"{stem}_desc-preproc_eeg.fif"
    ica_path = out_dir / f"{stem}_desc-ica_components.fif"
    json_path = out_dir / f"{stem}_desc-preproc_eeg.json"

    raw.save(fif_path, fmt="single", overwrite=True, verbose="ERROR")
    ica.save(ica_path, overwrite=True, verbose="ERROR")

    ica_fit_hp = float(cfg["filters"]["ica_fit_high_pass_hz"])
    sidecar = {
        "ParticipantID": subject,
        "TaskName": task,
        "SamplingFrequency": target,
        "PowerLineFrequency": 50,
        "SoftwareFilters": {**filter_spec(cfg),
                            "ica_fit_bandpass_hz": [ica_fit_hp, 100.0]},
        "Resampling": {"from_hz": native_sfreq, "to_hz": target},
        "Reference": {"scheme": "average", "original": original_ref,
                      "applied": True},
        "LineNoiseRemoval": {"method": ln_method,
                             "freqs_hz": ln_cfg["freqs_hz"],
                             "notch_width_hz": ln_cfg["notch_width_hz"]},
        "ICA": {"method": ica.method, "fit_params": ica.fit_params,
                "n_components": int(ica.n_components_),
                "labeling": labeling,
                "threshold": float(cfg["ica"]["exclude_threshold"]),
                "excluded_components": excluded, "excluded_labels": labels},
        "BadChannels": {"n": len(bad_names), "names": bad_names,
                        "occipital_bads": occ_bads, "interpolated": True},
        "ArtifactAnnotation": {
            "method": "windowed_ptp",
            "peak_v": cfg["artifact_annotation"]["peak_v"],
            "window_s": cfg["artifact_annotation"]["window_s"],
            "fraction": round(artifact_frac, 4)},
        "IAF": iaf,
        "IAFWindow": iaf_window,
        "LineNoisePower": {"before_index": round(ln_before, 3),
                           "after_index": round(ln_after, 3)},
        "Duration": {"s": round(raw.times[-1], 1),
                     "n_samples_final": int(raw.n_times)},
        "Sources": [
            {"path": str(p.relative_to(RAW_DIR.parent)), "sha256": sha256_file(p)}
            for p in [paths["vhdr"], paths["eeg"], paths["vmrk"]]
            if p.exists()],
        "SourceHeaderRepair": ({
            "applied": True,
            "reason": "vhdr/vmrk DataFile+MarkerFile carry a pre-BIDS recording stem",
            "declared_datafile": triplet["declared_datafile"],
        } if triplet["header_discrepancy"] else {"applied": False}),
        "Provenance": {
            "run_id": get_run_id() or "unmanaged",
            "git_sha": git_sha(),
            "pipeline_version": PIPELINE_VERSION,
            "mne_version": mne.__version__,
            "participants_tsv_sha256": participants_tsv_sha256(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    json_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")

    return {
        "subject": subject, "task": task,
        "duration_s": round(raw.times[-1], 1),
        "n_samples_final": int(raw.n_times),
        "bad_channels": bad_names, "n_bad_channels": len(bad_names),
        "occipital_bads": occ_bads,
        "ica_removed": excluded, "ica_removed_labels": labels,
        "n_ica_removed": len(excluded),
        "line_noise_index_before": round(ln_before, 3),
        "line_noise_index_after": round(ln_after, 3),
        "line_noise_method": ln_method,
        "iaf_hz": iaf["iaf_hz"], "alpha_peak_height_db": iaf["peak_height_db"],
        "alpha_present": iaf["present"],
        "artifact_frac": round(artifact_frac, 4),
        "fif_path": str(fif_path), "sidecar_path": str(json_path),
        "ica_path": str(ica_path),
    }


def _vhdr_reference(vhdr_path: Path) -> str:
    text = vhdr_path.read_text(encoding="latin-1")
    m = re.search(r"Reference Channel Name\s*=\s*(.+)", text)
    return m.group(1).strip() if m else "unknown"


# ---------------------------------------------------------------------------
# Backfill: re-derive IAF/QC on existing derivatives, no re-download.
#
# Rewrites ONLY the IAF + IAFWindow blocks (and a Backfill audit trail) of
# each existing sidecar. Never touches the .fif — the true blind-crop(120s)
# original is preserved on first backfill so the change is auditable, not a
# silent retune (phase_1.md §2a).
# ---------------------------------------------------------------------------

def backfill_iaf(cfg: dict, subjects: list[str] | None = None) -> dict:
    iaf_cfg = cfg.get("iaf", {})
    occ_channels = iaf_cfg.get("channels", [])
    band = tuple(iaf_cfg.get("band_hz", [7, 13]))
    min_prom = float(iaf_cfg.get("min_peak_prominence_db", 3.0))
    run_id = get_run_id() or "unmanaged"

    results = []
    for subj_dir in sorted(PREPROC_DIR.glob("sub-*/eeg")):
        subject = subj_dir.parent.name
        if subjects and subject not in subjects:
            continue
        for json_path in sorted(subj_dir.glob("*_desc-preproc_eeg.json")):
            sidecar = json.loads(json_path.read_text(encoding="utf-8"))
            task = sidecar.get("TaskName", "")
            fif_path = subj_dir / f"{subject}_task-{task}_desc-preproc_eeg.fif"
            if not fif_path.exists():
                continue

            raw = mne.io.read_raw_fif(fif_path, preload=False, verbose="ERROR")
            occ_picks = mne.pick_channels(raw.ch_names, include=occ_channels)
            excerpt, iaf_window = select_iaf_excerpt(raw, cfg, task)
            new_iaf = estimate_iaf(excerpt.get_data(picks=occ_picks),
                                   raw.info["sfreq"], band, min_prom)

            prior_iaf = sidecar.get("IAF")
            prior_window = sidecar.get("IAFWindow")
            history = sidecar.setdefault("Backfill", [])
            history.append({
                "kind": "iaf_rederive", "run_id": run_id,
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": "eyes-closed carve-out was never implemented; IAF was "
                          "estimated on a blind crop(tmax=120) inside the "
                          "eyes-open block",
                "before": {"IAF": prior_iaf, "IAFWindow": prior_window},
            })
            sidecar["IAF"] = new_iaf
            sidecar["IAFWindow"] = iaf_window

            tmp_path = json_path.with_suffix(f".json.tmp-{run_id}")
            tmp_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
            tmp_path.replace(json_path)

            results.append({
                "subject": subject, "task": task,
                "iaf_before": prior_iaf, "iaf_after": new_iaf,
                "window": iaf_window,
            })
    return {"n_rewritten": len(results), "results": results}
