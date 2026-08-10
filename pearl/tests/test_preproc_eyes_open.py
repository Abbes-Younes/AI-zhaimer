"""Eyes-open window resolution (phase_3.md §1a positive control).

Mirrors eyes_closed_window's marker parsing (phase_1.md remediation) but
returns the segment BEFORE the first `S 10` marker instead of after it.
"""
from __future__ import annotations

from types import SimpleNamespace

from pearl_preproc.preprocess import eyes_open_window


def _ann(pairs):
    return SimpleNamespace(
        onset=[p[0] for p in pairs],
        description=[p[1] for p in pairs],
    )


def test_canonical_pattern():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    assert eyes_open_window(ann, tmax=700.0) == (0.0, 246)


def test_recording_starting_at_s10_has_no_eyes_open_segment():
    ann = _ann([(0, "Stimulus/S 10"), (10, "Stimulus/S  1"), (370, "Stimulus/S 11")])
    assert eyes_open_window(ann, tmax=400.0, min_duration_s=60.0) is None


def test_no_s10_at_all_returns_none():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2")])
    assert eyes_open_window(ann, tmax=600.0) is None


def test_short_eyes_open_segment_returns_none():
    ann = _ann([(30, "Stimulus/S 10"), (40, "Stimulus/S  1")])
    assert eyes_open_window(ann, tmax=400.0, min_duration_s=60.0) is None


def test_window_never_inverted_or_empty():
    ann = _ann([(5, "Stimulus/S  1"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    start, end = eyes_open_window(ann, tmax=700.0)
    assert 0.0 <= start < end <= 700.0
