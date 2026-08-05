"""Tests for the CLI entry point and end-to-end pipeline."""
from __future__ import annotations

import pytest
from pathlib import Path

from pearl_audit.cli import cmd_run_all
from pearl_audit.paths import PROJECT_ROOT, ensure_scaffold


class TestCLI:
    """Smoke tests for the CLI — these don't hit the network."""

    def test_scaffold(self):
        """ensure_scaffold should not raise."""
        ensure_scaffold()

    def test_project_root_exists(self):
        assert PROJECT_ROOT.exists()

    def test_config_files_exist(self):
        from pearl_audit.paths import CLIENT_GROUPS_YAML, AUDIT_YAML
        assert CLIENT_GROUPS_YAML.exists()
        assert AUDIT_YAML.exists()
