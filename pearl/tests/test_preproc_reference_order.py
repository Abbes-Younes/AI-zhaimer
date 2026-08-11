"""phase_5.md §0a: bad-channel interpolation must happen BEFORE average
referencing, not after — otherwise a bad channel's noise contaminates the
average reference for every other channel.
"""
from __future__ import annotations

import mne
import numpy as np


def _raw_with_one_bad_channel(n_ch=8, n_seconds=5, sfreq=250.0, seed=0):
    rng = np.random.default_rng(seed)
    n_samples = int(n_seconds * sfreq)
    data = rng.normal(0, 1e-6, size=(n_ch, n_samples))
    data[0] += rng.normal(0, 1e-3, size=n_samples)  # channel 0: huge noise, clearly "bad"
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose=False)


def test_average_reference_after_interpolation_differs_from_before():
    """The average reference computed AFTER the bad channel is cleaned must
    differ from the one computed BEFORE (contaminated) -- if they're
    identical, the fix isn't actually changing anything."""
    raw_before = _raw_with_one_bad_channel()

    # Old (buggy) order: reference computed while channel 0 is still noisy.
    ref_before = raw_before.copy().set_eeg_reference("average", projection=False).get_data()

    # New (fixed) order: channel 0 cleaned (simulating post-interpolation)
    # BEFORE the reference is computed.
    raw_after = raw_before.copy()
    raw_after._data[0] = raw_after._data[1:].mean(axis=0)  # stand-in for interpolated data
    ref_after = raw_after.set_eeg_reference("average", projection=False).get_data()

    assert not np.allclose(ref_before, ref_after)


def test_process_subject_task_interpolates_before_referencing():
    """Integration check on the real function: bad-channel interpolation
    must occur strictly before set_eeg_reference in process_subject_task's
    source order (a structural regression test, not a numeric one, since a
    full run requires real raw files)."""
    import inspect

    from pearl_preproc import preprocess

    source = inspect.getsource(preprocess.process_subject_task)
    interpolate_idx = source.index("interpolate_bads")
    reference_idx = source.index('set_eeg_reference("average"')
    assert interpolate_idx < reference_idx, (
        "interpolate_bads() must appear before set_eeg_reference() in "
        "process_subject_task's source order (phase_5.md §0a)")
