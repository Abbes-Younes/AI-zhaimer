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
    """Structural check: bad-channel interpolation must occur strictly
    before set_eeg_reference in apply_reference_and_interpolation's default
    (post_interpolation) source order -- process_subject_task itself just
    calls this function (phase_5.md §0a fix; extracted for direct testing
    by the phase5_stage3_validation attribution diagnostic,
    sparkling-launching-torvalds.md §1)."""
    import inspect

    from pearl_preproc import preprocess

    source = inspect.getsource(preprocess.apply_reference_and_interpolation)
    interpolate_idx = source.index("interpolate_bads")
    reference_idx = source.index('set_eeg_reference("average"')
    assert interpolate_idx < reference_idx, (
        "interpolate_bads() must appear before set_eeg_reference() in "
        "apply_reference_and_interpolation's default source order (phase_5.md §0a)")


def _montaged_raw_with_one_bad_channel(seed=0):
    """detect_bad_channels needs real channel positions (neighbor-correlation
    rule), unlike the plain fixture above -- use real 10-20 names with a
    standard montage attached."""
    ch_names = ["Fz", "Cz", "Pz", "F3", "F4", "C3", "C4", "O1"]
    rng = np.random.default_rng(seed)
    n_samples = int(5 * 250.0)
    data = rng.normal(0, 1e-6, size=(len(ch_names), n_samples))
    data[0] += rng.normal(0, 1e-3, size=n_samples)  # Fz: huge noise, clearly "bad"
    info = mne.create_info(ch_names, 250.0, "eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.set_montage(mne.channels.make_standard_montage("standard_1020"))
    return raw


def test_apply_reference_and_interpolation_default_matches_post_interpolation_fix():
    """Runtime behavior check, not just source position: the default config
    (no compute_order key, or explicit "post_interpolation") must produce a
    DIFFERENT referenced signal than "pre_interpolation" on a raw with one
    bad channel -- proving the config actually controls behavior, the same
    property test_average_reference_after_interpolation_differs_from_before
    established conceptually above."""
    from pearl_preproc.preprocess import apply_reference_and_interpolation

    cfg_fixed = {"reference": {"projection": False, "compute_order": "post_interpolation"},
                 "bad_channels": {}}
    cfg_bug = {"reference": {"projection": False, "compute_order": "pre_interpolation"},
               "bad_channels": {}}

    raw_fixed = _montaged_raw_with_one_bad_channel()
    raw_bug = raw_fixed.copy()

    apply_reference_and_interpolation(raw_fixed, cfg_fixed, occ=set())
    apply_reference_and_interpolation(raw_bug, cfg_bug, occ=set())

    assert not np.allclose(raw_fixed.get_data(), raw_bug.get_data())


def test_apply_reference_and_interpolation_defaults_to_post_interpolation():
    """No compute_order key at all -> must behave like "post_interpolation"
    (the safe default), never silently fall back to the bug."""
    from pearl_preproc.preprocess import apply_reference_and_interpolation

    cfg_no_key = {"reference": {"projection": False}, "bad_channels": {}}
    cfg_explicit = {"reference": {"projection": False, "compute_order": "post_interpolation"},
                     "bad_channels": {}}

    raw_a = _montaged_raw_with_one_bad_channel()
    raw_b = raw_a.copy()

    apply_reference_and_interpolation(raw_a, cfg_no_key, occ=set())
    apply_reference_and_interpolation(raw_b, cfg_explicit, occ=set())

    assert np.allclose(raw_a.get_data(), raw_b.get_data())
