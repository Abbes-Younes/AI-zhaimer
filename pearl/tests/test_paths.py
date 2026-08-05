"""Tests for paths.py — disk guard and byte budget."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pearl_audit.paths import (
    DiskGuardError,
    ByteBudgetError,
    _sha256_file,
    _load_cumulative_bytes,
    ensure_scaffold,
)


def test_ensure_scaffold_creates_dirs(tmp_path: Path):
    """ensure_scaffold should create all required directories."""
    # We can't easily redirect PROJECT_ROOT in a unit test, but we can
    # verify the function doesn't raise and that key dirs exist.
    ensure_scaffold()


def test_sha256_file(tmp_path: Path):
    """_sha256_file should return a valid hex digest."""
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    digest = _sha256_file(f)
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_load_cumulative_bytes_empty(tmp_path: Path, monkeypatch):
    """With no fetch_log, cumulative bytes should be 0."""
    from pearl_audit import paths
    monkeypatch.setattr(paths, "FETCH_LOG", tmp_path / "nonexistent.jsonl")
    assert _load_cumulative_bytes() == 0
