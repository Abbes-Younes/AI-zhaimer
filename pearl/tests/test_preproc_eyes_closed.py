"""Eyes-closed rest window resolution (phase_1.md remediation, 2026-08-09).

The PEARL-Neuro rest recording is ONE file: 4 min eyes-open ending at marker
`S 10`, then 6 min eyes-closed starting at the next `S 1` and ending at
`S 11` (data/raw_meta/task-rest_eeg.json). Sub-markers `S 2`/`S 4` are
inconsistently present across subjects and must never be required.
"""
from __future__ import annotations

from types import SimpleNamespace

from pearl_preproc.preprocess import eyes_closed_window


def _ann(pairs):
    """Build a fake mne.Annotations-like object from [(onset, desc), ...]."""
    return SimpleNamespace(
        onset=[p[0] for p in pairs],
        description=[p[1] for p in pairs],
    )


def test_canonical_pattern():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (260.1, "Stimulus/S  4"), (620, "Stimulus/S 11")])
    w = eyes_closed_window(ann, tmax=700.0)
    assert w == (260, 620)


def test_no_s4():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    assert eyes_closed_window(ann, tmax=700.0) == (260, 620)


def test_no_s2_no_s4():
    ann = _ann([(5, "Stimulus/S  1"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    assert eyes_closed_window(ann, tmax=700.0) == (260, 620)


def test_missing_s11_falls_back_to_end_of_recording():
    # sub-19, sub-30: no S 11 at all
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (260.1, "Stimulus/S  4")])
    assert eyes_closed_window(ann, tmax=617.7) == (260, 617.7)


def test_leading_new_segment_annotation_ignored():
    ann = _ann([(0, "New Segment/"), (5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"),
                (246, "Stimulus/S 10"), (260, "Stimulus/S  1"), (260.1, "Stimulus/S  4")])
    assert eyes_closed_window(ann, tmax=617.7) == (260, 617.7)


def test_recording_starting_at_s10():
    # sub-22, sub-25
    ann = _ann([(0, "Stimulus/S 10"), (10, "Stimulus/S  1"), (370, "Stimulus/S 11")])
    assert eyes_closed_window(ann, tmax=400.0) == (10, 370)


def test_trailing_s1_after_s11_ignored():
    # sub-78
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (260.1, "Stimulus/S  4"),
                (620, "Stimulus/S 11"), (621, "Stimulus/S  1")])
    assert eyes_closed_window(ann, tmax=700.0) == (260, 620)


def test_late_s1_beyond_max_gap_falls_back_to_s10():
    # sub-07, sub-34, sub-60: S10 -> S1 gap far larger than the normal 8-48s
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246.5, "Stimulus/S 10"),
                (702.1, "Stimulus/S  1"), (702.2, "Stimulus/S  4")])
    w = eyes_closed_window(ann, tmax=726.1, max_start_gap_s=60.0)
    assert w == (246.5, 726.1)


def test_no_s10_at_all_returns_none():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2")])
    assert eyes_closed_window(ann, tmax=600.0) is None


def test_first_s1_after_s10_wins_not_second():
    ann = _ann([(5, "Stimulus/S  1"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (300, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    assert eyes_closed_window(ann, tmax=700.0) == (260, 620)


def test_window_never_inverted_or_empty():
    ann = _ann([(5, "Stimulus/S  1"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    start, end = eyes_closed_window(ann, tmax=700.0)
    assert 0 <= start < end <= 700.0


def test_degenerate_window_below_min_duration_returns_none():
    # S 10 fires right before the recording ends, no reachable S 1/S 11
    ann = _ann([(5, "Stimulus/S  1"), (690, "Stimulus/S 10")])
    assert eyes_closed_window(ann, tmax=700.0, min_duration_s=60.0) is None
