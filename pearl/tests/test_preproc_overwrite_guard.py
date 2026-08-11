"""Safeguard added after a real incident (phase_5.md Stage 1, 2026-08-11):
process_subject_task always wrote unconditionally (overwrite=True) to the
live PREPROC_DIR with no protection, and an ad-hoc validation call
overwrote a frozen-cohort subject's derivative in place. The normal
orchestrated pipeline (pearl_preproc.pipeline) never hits this because it
checks derivative_exists() and skips subjects that already have one --
this guard targets exactly the case that pipeline skip doesn't cover: a
direct, non-orchestrated call against a subject that already has a
derivative on the live path.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pearl_preproc.preprocess import PreprocessError, resolve_output_dir


def test_resolve_output_dir_returns_scratch_dir_when_given(tmp_path):
    out = resolve_output_dir(subject="sub-99", output_dir=tmp_path, run_id_active=False,
                             existing_fif=None, overwrite_existing=False)
    assert out == tmp_path


def test_resolve_output_dir_allows_live_path_when_no_existing_derivative(tmp_path):
    live_dir = tmp_path / "live"
    out = resolve_output_dir(subject="sub-99", output_dir=None, run_id_active=False,
                             existing_fif=None, live_dir=live_dir)
    assert out == live_dir


def test_resolve_output_dir_allows_live_path_under_an_active_run_id(tmp_path):
    live_dir = tmp_path / "live"
    fake_existing = tmp_path / "already-there.fif"
    fake_existing.touch()
    out = resolve_output_dir(subject="sub-99", output_dir=None, run_id_active=True,
                             existing_fif=fake_existing, live_dir=live_dir)
    assert out == live_dir


def test_resolve_output_dir_refuses_ad_hoc_overwrite_of_existing_derivative(tmp_path):
    live_dir = tmp_path / "live"
    fake_existing = tmp_path / "already-there.fif"
    fake_existing.touch()
    with pytest.raises(PreprocessError, match="overwrite_existing"):
        resolve_output_dir(subject="sub-52", output_dir=None, run_id_active=False,
                           existing_fif=fake_existing, live_dir=live_dir)


def test_resolve_output_dir_allows_explicit_overwrite_acknowledgement(tmp_path):
    live_dir = tmp_path / "live"
    fake_existing = tmp_path / "already-there.fif"
    fake_existing.touch()
    out = resolve_output_dir(subject="sub-52", output_dir=None, run_id_active=False,
                             existing_fif=fake_existing, overwrite_existing=True, live_dir=live_dir)
    assert out == live_dir
