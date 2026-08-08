"""report_qc.py boolean-comparison robustness (remediation 2026-08-09).

_is_false/_is_true must accept real Python bools AND the "True"/"False"
strings a CSV round-trip produces — the report currently only ever sees CSV
strings, but comparing against the literal string is fragile the moment a
caller passes rows straight from qc.build_qc_table() instead of a re-read CSV.
"""
from __future__ import annotations

from pearl_preproc.report_qc import _is_false, _is_true


def test_is_false_accepts_bool_and_string():
    assert _is_false(False) is True
    assert _is_false("False") is True
    assert _is_false("false") is True
    assert _is_false(True) is False
    assert _is_false("True") is False


def test_is_true_accepts_bool_and_string():
    assert _is_true(True) is True
    assert _is_true("True") is True
    assert _is_true("true") is True
    assert _is_true(False) is False
    assert _is_true("False") is False
