"""Load and validate config/preproc.yaml (fixed, label-free pipeline config)."""
from __future__ import annotations

from pathlib import Path

import yaml

from .paths import PREPROC_YAML


class PreprocConfigError(Exception):
    """Raised when config/preproc.yaml is missing or malformed."""


def load_preproc_config(path: Path | None = None) -> dict:
    p = path or PREPROC_YAML
    if not p.exists():
        raise PreprocConfigError(f"{p} not found — the Phase 1 pipeline refuses "
                                 f"to run without fixed configuration.")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    required = ["sampling_rates_hz", "ica", "qc", "line_noise", "filters"]
    for key in required:
        if key not in cfg:
            raise PreprocConfigError(f"config/preproc.yaml missing required section '{key}'.")
    return cfg


def target_sfreq(cfg: dict, task: str) -> float:
    """Sampling rate for *task* (task-rest → 500 Hz, task-msit → 250 Hz),
    read from config — never hardcoded."""
    rates = cfg["sampling_rates_hz"]
    key = f"task-{task}" if not task.startswith("task-") else task
    if key not in rates:
        raise PreprocConfigError(
            f"no sampling rate configured for '{key}' in config/preproc.yaml "
            f"(known: {sorted(rates)})")
    return float(rates[key])
