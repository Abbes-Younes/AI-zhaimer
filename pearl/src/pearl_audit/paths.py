"""Central path definitions and disk/budget guards for Phase 0."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Project root — always D:\pearl\ (or D:\younes\AI-zhaimer\pearl in dev)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Canonical paths
# ---------------------------------------------------------------------------

CACHE_DIR      = PROJECT_ROOT / ".cache"
VENV_DIR       = PROJECT_ROOT / ".venv"
CONFIG_DIR     = PROJECT_ROOT / "config"
DATA_DIR       = PROJECT_ROOT / "data"
RAW_META_DIR   = DATA_DIR / "raw_meta"
DERIVATIVES_DIR = DATA_DIR / "derivatives" / "phase0"
REPORTS_DIR    = PROJECT_ROOT / "reports"
LOGS_DIR       = PROJECT_ROOT / "logs"
TESTS_DIR      = PROJECT_ROOT / "tests"

CLIENT_GROUPS_YAML = CONFIG_DIR / "client_groups.yaml"
AUDIT_YAML         = CONFIG_DIR / "audit.yaml"

FETCH_LOG = LOGS_DIR / "fetch_log.jsonl"

# Budget: 50 MB max for Phase 0
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 52,428,800

# Minimum free space on D: in GB
MIN_FREE_SPACE_GB = 20


class DiskGuardError(Exception):
    """Raised when disk constraints are violated."""


class ByteBudgetError(Exception):
    """Raised when cumulative download exceeds the 50 MB budget."""


class RunIdMismatchError(Exception):
    """Raised when report inputs do not all share the current run_id."""


# ---------------------------------------------------------------------------
# Disk-space helper
# ---------------------------------------------------------------------------

def _get_free_gb(path: Path) -> float:
    """Return free space in GB for the drive containing *path*."""
    usage = shutil.disk_usage(str(path))
    return usage.free / (1024 ** 3)


def require_free_space(min_gb: float = MIN_FREE_SPACE_GB) -> float:
    """Ensure PROJECT_ROOT's drive has at least *min_gb* free.  Return free GB."""
    free_gb = _get_free_gb(PROJECT_ROOT)
    if free_gb < min_gb:
        raise DiskGuardError(
            f"Only {free_gb:.1f} GB free on {PROJECT_ROOT.drive} — "
            f"need at least {min_gb} GB. Aborting."
        )
    return free_gb


# ---------------------------------------------------------------------------
# Byte-budget tracker
# ---------------------------------------------------------------------------

_cumulative_bytes: int = 0


def _load_cumulative_bytes() -> int:
    """Sum all ``bytes`` entries already logged in fetch_log.jsonl."""
    total = 0
    if FETCH_LOG.exists():
        with open(FETCH_LOG, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    total += rec.get("bytes", 0)
                except json.JSONDecodeError:
                    pass
    return total


def _ensure_log_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def record_download(url: str, dest: Path, nbytes: int) -> None:
    """Append a download record and enforce the cumulative byte budget.

    Parameters
    ----------
    url : str
        The URL that was fetched.
    dest : Path
        Where the file was written.
    nbytes : int
        Number of bytes written.
    """
    global _cumulative_bytes
    _ensure_log_dir()

    sha256 = _sha256_file(dest)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "dest": str(dest),
        "bytes": nbytes,
        "sha256": sha256,
    }
    with open(FETCH_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    _cumulative_bytes += nbytes
    if _cumulative_bytes > MAX_DOWNLOAD_BYTES:
        raise ByteBudgetError(
            f"Cumulative downloads ({_cumulative_bytes:,} bytes) exceed "
            f"the {MAX_DOWNLOAD_BYTES:,}-byte Phase 0 budget."
        )


def get_cumulative_bytes() -> int:
    """Return cumulative bytes downloaded so far."""
    return _cumulative_bytes


def _sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Run identity + atomic artifact staging (phase_0,5.md Task 4)
# ---------------------------------------------------------------------------

_run_id: str | None = None


def set_run_id(run_id: str | None) -> None:
    """Set the current run identifier (None = unmanaged, write in place)."""
    global _run_id
    _run_id = run_id


def get_run_id() -> str | None:
    """Return the current run identifier, or None outside a managed run."""
    return _run_id


def artifact_dir() -> Path:
    """Directory CSVs should be written to / read from for the current run.

    Inside a managed run this is ``data/derivatives/phase0/.tmp-<run_id>/`` so
    artifacts are only swapped into place once every step has succeeded. Outside
    a managed run (e.g. unit tests) it is the plain derivatives dir.
    """
    if _run_id:
        return DERIVATIVES_DIR / f".tmp-{_run_id}"
    return DERIVATIVES_DIR


def stamp_run_meta() -> None:
    """Write a ``_meta.json`` recording the current run_id into the artifact dir.

    Called at the start of a managed run so that every downstream step — and
    crucially the report — can assert all artifacts share one run_id.
    """
    if not _run_id:
        return
    d = artifact_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "_meta.json").write_text(
        json.dumps({"run_id": _run_id, "started_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n",
        encoding="utf-8",
    )


def finalize_run() -> None:
    """Swap staged artifacts into place and stamp ``_meta.json``.

    Moves every file from ``.tmp-<run_id>/`` into ``DERIVATIVES_DIR``, writes a
    ``_meta.json`` recording the run_id, then removes the staging directory.
    No-op when no run is in progress.
    """
    if not _run_id:
        return
    tmp_dir = artifact_dir()
    DERIVATIVES_DIR.mkdir(parents=True, exist_ok=True)
    if tmp_dir.exists():
        for item in tmp_dir.iterdir():
            dest = DERIVATIVES_DIR / item.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(tmp_dir, ignore_errors=True)
    meta_path = DERIVATIVES_DIR / "_meta.json"
    meta_path.write_text(
        json.dumps({"run_id": _run_id, "finalized_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# audit.yaml helpers
# ---------------------------------------------------------------------------

def load_audit_yaml() -> dict:
    """Load config/audit.yaml as a dict."""
    if not AUDIT_YAML.exists():
        return {}
    with open(AUDIT_YAML, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def update_audit_yaml(mutator) -> None:
    """Load audit.yaml, apply *mutator(cfg)*, and write it back atomically.

    ``mutator`` must edit the dict in place; nothing is written if it raises.
    """
    cfg = load_audit_yaml()
    mutator(cfg)
    tmp = AUDIT_YAML.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, default_flow_style=False, sort_keys=False)
    tmp.replace(AUDIT_YAML)


# ---------------------------------------------------------------------------
# Bootstrap — create every directory the scaffold needs
# ---------------------------------------------------------------------------

def ensure_scaffold() -> None:
    """Create all directories required by the Phase 0 scaffold."""
    for d in [
        CACHE_DIR, VENV_DIR, CONFIG_DIR, DATA_DIR,
        RAW_META_DIR, DERIVATIVES_DIR, REPORTS_DIR, LOGS_DIR, TESTS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)
