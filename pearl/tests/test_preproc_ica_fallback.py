"""ICLabel fallback regression (phase_4.md Task D): found via the real
Docker container smoke test, which was the first time this fallback path
(used only when neither torch nor onnxruntime is importable) ever actually
ran -- it crashed with IndexError on a degenerate PSD. Untested dead code
until this container run exercised it for real.
"""
from __future__ import annotations

import mne
import numpy as np

from pearl_preproc.preprocess import _ica_labels_fallback


def _tiny_raw_and_ica(n_seconds=2, sfreq=500.0, n_ch=4, seed=0):
    rng = np.random.default_rng(seed)
    n_samples = int(n_seconds * sfreq)
    data = rng.normal(0, 1e-6, size=(n_ch, n_samples))
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    ica = mne.preprocessing.ICA(n_components=3, random_state=42, max_iter=200)
    ica.fit(raw, verbose=False)
    return raw, ica


def test_ica_labels_fallback_does_not_crash_on_short_segment():
    """A short source segment can coarsen frequency resolution enough that
    no PSD bin lands >= 20 Hz within [1, 45] Hz -- must not raise IndexError."""
    raw, ica = _tiny_raw_and_ica(n_seconds=2)
    excluded, labels = _ica_labels_fallback(raw, ica, exclude_threshold=0.8, frontal=())
    assert isinstance(excluded, list)
    assert isinstance(labels, list)


def test_ica_labels_fallback_normal_length_still_works():
    raw, ica = _tiny_raw_and_ica(n_seconds=30)
    excluded, labels = _ica_labels_fallback(raw, ica, exclude_threshold=0.8, frontal=())
    assert isinstance(excluded, list)
    assert len(excluded) == len(labels)
