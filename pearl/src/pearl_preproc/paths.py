"""Phase 1 paths, run identity and atomic staging (pearl_preproc).

Standalone on purpose: pearl_preproc must have *no* import path to any
label-bearing module (phase_1.md §2a). This module is the only place Phase 1
touches the audit config, and only for the non-label provenance fingerprint
(participants.tsv SHA-256 and dataset version).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR   = PROJECT_ROOT / "config"
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DIR      = DATA_DIR / "raw"                      # transient per-subject raw
RAW_META_DIR = DATA_DIR / "raw_meta"                 # cached url_map etc.
PREPROC_DIR  = DATA_DIR / "derivatives" / "preproc"  # BIDS-Derivatives tree
QC_DIR       = PREPROC_DIR / "qc"
REPORTS_DIR  = PROJECT_ROOT / "reports"
LOGS_DIR     = PROJECT_ROOT / "logs"

AUDIT_YAML      = CONFIG_DIR / "audit.yaml"
PREPROC_YAML    = CONFIG_DIR / "preproc.yaml"
DOWNLOAD_LOG    = LOGS_DIR / "download_log.jsonl"
QUARANTINE_LOG  = LOGS_DIR / "quarantine_log.jsonl"
URL_MAP_CACHE   = RAW_META_DIR / "url_map.json"
MANIFEST_CSV    = DATA_DIR / "derivatives" / "phase0" / "phase1_manifest.csv"
SIZE_SURVEY_CSV = DATA_DIR / "derivatives" / "phase0" / "size_survey.csv"

MIN_FREE_SPACE_GB = 20.0

# Native recording parameters (verified from sub-01 .vhdr probe).
NATIVE_SFREQ_HZ   = 1000.0
N_CHANNELS_NATIVE = 127
BYTES_PER_SAMPLE  = 4  # IEEE_FLOAT_32


class DiskGuardError(Exception):
    """Raised when the drive does not have the required free space."""


class RunIdMismatchError(Exception):
    """Raised when bulk artifacts do not share the current run_id."""


# ---------------------------------------------------------------------------
# Disk guard
# ---------------------------------------------------------------------------

def require_free_space(min_gb: float = MIN_FREE_SPACE_GB) -> float:
    """Raise DiskGuardError if PROJECT_ROOT's drive has < min_gb free."""
    usage = shutil.disk_usage(str(PROJECT_ROOT))
    free_gb = usage.free / (1024 ** 3)
    if free_gb < min_gb:
        raise DiskGuardError(
            f"Only {free_gb:.1f} GB free on {PROJECT_ROOT.drive} — "
            f"need at least {min_gb} GB. Aborting."
        )
    return free_gb


# ---------------------------------------------------------------------------
# Run identity + atomic staging (Phase 0.5 convention, phase_1.md §4)
# ---------------------------------------------------------------------------

_run_id: str | None = None


def set_run_id(run_id: str | None) -> None:
    global _run_id
    _run_id = run_id


def get_run_id() -> str | None:
    return _run_id


def git_sha() -> str:
    try:
        sha = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT.parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return sha or "nogit"
    except Exception:
        return "nogit"


def make_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{git_sha()}"


def staging_dir() -> Path:
    """Staging dir for bulk artifacts: ``preproc/.tmp-<run_id>/`` inside a
    managed run, else the plain preproc dir (unit tests / standalone steps)."""
    if _run_id:
        return PREPROC_DIR / f".tmp-{_run_id}"
    return PREPROC_DIR


def stamp_run_meta() -> None:
    if not _run_id:
        return
    d = staging_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "_meta.json").write_text(
        json.dumps({"run_id": _run_id, "started_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n", encoding="utf-8")


def finalize_run() -> None:
    """Swap staged bulk artifacts into the preproc tree, then stamp _meta.json."""
    if not _run_id:
        return
    tmp = staging_dir()
    PREPROC_DIR.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        for item in tmp.iterdir():
            dest = PREPROC_DIR / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(tmp, ignore_errors=True)
    (PREPROC_DIR / "_meta.json").write_text(
        json.dumps({"run_id": _run_id, "finalized_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Non-label provenance fingerprint from the Phase 0.5 audit config
# ---------------------------------------------------------------------------

def load_audit_provenance() -> dict:
    """Return the non-label provenance block of config/audit.yaml.

    Only the fields Phase 1 sidecars need: accession, version, and the
    participants.tsv SHA-256 fingerprint. No label or group data is read.
    """
    if not AUDIT_YAML.exists():
        return {}
    cfg = yaml.safe_load(AUDIT_YAML.read_text(encoding="utf-8")) or {}
    return cfg.get("provenance", {}) or {}


def participants_tsv_sha256() -> str | None:
    prov = load_audit_provenance()
    return prov.get("participants_tsv_sha256")


# ---------------------------------------------------------------------------
# Small file helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs() -> None:
    for d in [RAW_DIR, RAW_META_DIR, PREPROC_DIR, QC_DIR, REPORTS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
