"""§2 — eyes-closed continuous extraction. Feature extraction stays
label-blind: same enforced test as Phase 1 (test_features_labelblind.py),
extended from pearl_preproc.

Reuses the fixed-window peak-to-peak artifact measure from
config/preproc.yaml's artifact_annotation policy (phase_1.md), applied here to
mark rejected segments as mne annotations rather than to compute a QC
percentage — Phase 2 needs the actual rejected-sample mask, Phase 1 only
needed the fraction.
"""
from __future__ import annotations

import json

import mne
import numpy as np

from pearl_preproc.paths import PREPROC_DIR


def load_iaf_window(subject: str, task: str = "rest") -> tuple[float, float]:
    sidecar_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-{task}_desc-preproc_eeg.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    window = sidecar.get("IAFWindow")
    if not window or "tmin_s" not in window or "tmax_s" not in window:
        raise ValueError(f"{sidecar_path} has no IAFWindow block — Phase 1 must resolve this "
                          f"before Phase 2 can consume it; never re-derive it here.")
    return float(window["tmin_s"]), float(window["tmax_s"])


def load_eyes_closed_continuous(subject: str, task: str = "rest") -> mne.io.Raw:
    tmin, tmax = load_iaf_window(subject, task)
    fif_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-{task}_desc-preproc_eeg.fif"
    raw = mne.io.read_raw_fif(fif_path, preload=True, verbose=False)
    raw.crop(tmin=tmin, tmax=min(tmax, raw.times[-1]))
    return raw


def reject_artifact_segments(raw: mne.io.Raw, cfg: dict) -> tuple[mne.io.Raw, mne.Annotations, float]:
    rc = cfg["artifact_rejection"]
    peak_v = float(rc["peak_v"])
    window_s = float(rc.get("window_s", 1.0))
    sfreq = raw.info["sfreq"]
    win_samples = max(1, int(round(window_s * sfreq)))
    data = raw.get_data()
    n_samples = data.shape[1]

    onsets, durations = [], []
    for start in range(0, n_samples, win_samples):
        end = min(start + win_samples, n_samples)
        window = data[:, start:end]
        ptp = window.max(axis=1) - window.min(axis=1)
        if np.any(ptp > peak_v):
            onsets.append(start / sfreq)
            durations.append((end - start) / sfreq)

    annotations = mne.Annotations(onset=onsets, duration=durations,
                                   description=["BAD_artifact"] * len(onsets))
    raw_annotated = raw.copy().set_annotations(annotations)
    usable_s = raw.times[-1] - sum(durations)
    return raw_annotated, annotations, usable_s
