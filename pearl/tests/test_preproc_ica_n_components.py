"""phase_5.md §0b: n_components must support both int (fixed component
count) and float in (0, 1) (explained-variance-ratio selection, MNE's own
convention) -- the ICA n_components re-evaluation needs to compare both.
Found via a real blocker: the existing code forced int(n_components),
silently truncating 0.99 -> 0.
"""
from __future__ import annotations

import mne
import numpy as np

from pearl_preproc.preprocess import fit_and_exclude_ica, _excluded_classes_idx


def _tiny_raw(n_seconds=60, sfreq=250.0, seed=0):
    # Real 10-20 channel names + a standard montage -- ICLabel's topography
    # features require real electrode positions, unlike everything else in
    # this pipeline's other synthetic fixtures.
    montage = mne.channels.make_standard_montage("standard_1020")
    ch_names = montage.ch_names[:20]
    rng = np.random.default_rng(seed)
    n_samples = int(n_seconds * sfreq)
    n_sources = 5
    t = np.arange(n_samples) / sfreq
    sources = np.stack([np.sin(2 * np.pi * (5 + i) * t) + rng.normal(0, 0.3, n_samples)
                        for i in range(n_sources)])
    mixing = rng.normal(size=(len(ch_names), n_sources))
    data = (mixing @ sources) * 1e-6
    info = mne.create_info(ch_names, sfreq, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.set_montage(montage)
    return raw


def _cfg(n_components):
    return {
        "ica": {"n_components": n_components, "method": "infomax",
                "random_state": 42, "exclude_threshold": 0.8,
                "excluded_classes": ["muscle artifact", "eye blink"]},
        "filters": {"ica_fit_high_pass_hz": 1.0},
    }


def test_fit_and_exclude_ica_accepts_integer_n_components():
    raw = _tiny_raw()
    cfg = _cfg(5)
    ica, excluded, labels, method = fit_and_exclude_ica(raw, cfg, _excluded_classes_idx(cfg))
    assert ica.n_components_ == 5


def test_fit_and_exclude_ica_accepts_float_explained_variance_n_components():
    raw = _tiny_raw()
    cfg = _cfg(0.99)
    ica, excluded, labels, method = fit_and_exclude_ica(raw, cfg, _excluded_classes_idx(cfg))
    assert 0 < ica.n_components_ <= 20
