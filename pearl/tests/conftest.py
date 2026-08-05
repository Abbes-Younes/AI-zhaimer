"""Shared fixtures for pearl_audit tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
