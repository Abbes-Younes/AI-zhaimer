"""Manifest-driven download engine (phase_1.md §1).

The ``phase1_manifest.csv`` from Phase 0.5 is the contract — this module never
re-derives the file list. URLs are resolved once via OpenNeuro's GraphQL API
(versioned public-S3 URLs; semantically equivalent to ``aws s3 cp
--no-sign-request`` — no AWS CLI is available on this machine, and the versioned
URLs are required for object access) and cached to ``data/raw_meta/url_map.json``
so restarts never re-list the dataset.

Downloaded files are verified against the manifest byte size; a mismatch is
retried once and the subject quarantined if it fails again. Every transfer is
logged to ``logs/download_log.jsonl`` with URL, bytes, SHA-256, duration and
outcome. Re-invocation skips files whose size already matches (idempotent).
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

from .paths import (
    RAW_DIR,
    LOGS_DIR,
    URL_MAP_CACHE,
    MANIFEST_CSV,
    DOWNLOAD_LOG,
    QUARANTINE_LOG,
    require_free_space,
    ensure_dirs,
)

GRAPHQL_URL = "https://openneuro.org/crn/graphql"
ACCESSION = "ds004796"
_FILES_QUERY = """
query GetFiles($datasetId: ID!, $tag: String!) {
  snapshot(datasetId: $datasetId, tag: $tag) {
    files(recursive: true) { filename size directory urls }
  }
}
"""


class DownloadError(Exception):
    """A download failed verification after all retries."""


# ---------------------------------------------------------------------------
# URL map (filename → versioned public-S3 URL), cached for restartability
# ---------------------------------------------------------------------------

def _fetch_url_map(tag: str | None = None) -> dict[str, str]:
    tag = tag or "1.0.0"
    resp = requests.post(GRAPHQL_URL, json={
        "query": _FILES_QUERY,
        "variables": {"datasetId": ACCESSION, "tag": tag},
    }, timeout=180)
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise DownloadError(f"GraphQL errors resolving file URLs: {body['errors']}")
    files = body["data"]["snapshot"]["files"]
    url_map = {}
    for f in files:
        if f.get("directory"):
            continue
        urls = f.get("urls") or []
        if urls:
            url_map[f["filename"]] = urls[0] if isinstance(urls, list) else urls
    return url_map


def load_url_map(force_refresh: bool = False) -> dict[str, str]:
    """Return the cached URL map, fetching + caching it if absent."""
    if not force_refresh and URL_MAP_CACHE.exists():
        return json.loads(URL_MAP_CACHE.read_text(encoding="utf-8"))
    url_map = _fetch_url_map()
    URL_MAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    URL_MAP_CACHE.write_text(json.dumps(url_map), encoding="utf-8")
    return url_map


# ---------------------------------------------------------------------------
# Single-file transfer with size verification
# ---------------------------------------------------------------------------

def download_one(url: str, dest: Path, expected_bytes: int,
                 chunk_bytes: int = 1 << 20, timeout: int = 300) -> dict:
    """Stream *url* to *dest* (temp-then-rename) and verify the byte size.

    Returns {bytes, sha256, duration_ms}. Raises DownloadError on HTTP/verify
    failure. Never leaves a partial file at *dest*.
    """
    tmp = dest.with_suffix(dest.suffix + ".part")
    started = time.perf_counter()
    h = hashlib.sha256()
    total = 0
    try:
        with requests.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_bytes):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    h.update(chunk)
                    total += len(chunk)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise DownloadError(f"GET {url} failed: {exc!r}") from exc

    if total != expected_bytes:
        tmp.unlink(missing_ok=True)
        raise DownloadError(
            f"size mismatch for {dest.name}: got {total:,} bytes, "
            f"manifest says {expected_bytes:,}")
    tmp.replace(dest)
    return {"bytes": total, "sha256": h.hexdigest(),
            "duration_ms": int((time.perf_counter() - started) * 1000)}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log_download(record: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(DOWNLOAD_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _log_quarantine(subject: str, reason: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUARANTINE_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "subject": subject,
            "reason": reason,
        }) + "\n")


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    if not MANIFEST_CSV.exists():
        raise FileNotFoundError(f"{MANIFEST_CSV} missing — run Phase 0.5 first")
    with open(MANIFEST_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def manifest_for_subject(manifest: list[dict], subject: str) -> list[dict]:
    return [r for r in manifest if r["subject"] == subject]


# ---------------------------------------------------------------------------
# Per-subject download (idempotent, verify → retry → quarantine)
# ---------------------------------------------------------------------------

def _dest_for(row: dict) -> Path:
    return RAW_DIR / row["path"]


def _already_ok(row: dict) -> bool:
    dest = _dest_for(row)
    if not dest.exists():
        return False
    return dest.stat().st_size == int(row["bytes"])


def download_subject(subject: str, rows: list[dict], url_map: dict[str, str],
                     cfg: dict, log_fn=_log_download) -> dict:
    """Download one subject's manifest rows; verify sizes; quarantine on failure.

    Returns {subject, downloaded, skipped, quarantined, bytes, errors}.
    """
    summary = {"subject": subject, "downloaded": 0, "skipped": 0,
               "quarantined": False, "bytes": 0, "errors": []}
    retries = int(cfg.get("download", {}).get("retries", 1))
    chunk = int(cfg.get("download", {}).get("stream_chunk_bytes", 1 << 20))

    for row in sorted(rows, key=lambda r: r["path"]):
        dest = _dest_for(row)
        if _already_ok(row):
            summary["skipped"] += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = url_map.get(row["path"])
        if not url:
            summary["errors"].append(f"no URL for {row['path']}")
            continue

        attempt, ok = 0, False
        record = None
        while attempt <= retries and not ok:
            attempt += 1
            try:
                info = download_one(url, dest, int(row["bytes"]), chunk_bytes=chunk)
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "subject": subject, "task": row.get("task"),
                    "filename": row["path"], "url": url,
                    "bytes": info["bytes"], "sha256": info["sha256"],
                    "duration_ms": info["duration_ms"], "outcome": "downloaded",
                }
                ok = True
            except DownloadError as exc:
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "subject": subject, "task": row.get("task"),
                    "filename": row["path"], "url": url,
                    "bytes": 0, "sha256": None, "duration_ms": 0,
                    "outcome": f"retry{attempt}" if attempt <= retries else "failed",
                    "error": str(exc),
                }
        log_fn(record)
        if ok:
            summary["downloaded"] += 1
            summary["bytes"] += record["bytes"]
        else:
            summary["errors"].append(f"{row['path']}: {record.get('error', 'failed')}")
            summary["quarantined"] = True
            _log_quarantine(subject, f"download failure: {row['path']}")
            break  # stop the subject; it cannot be preprocessed reliably

    return summary


# ---------------------------------------------------------------------------
# Bulk orchestration
# ---------------------------------------------------------------------------

def download_all(cfg: dict, subjects: list[str] | None = None,
                 n_workers: int | None = None) -> dict:
    """Download every manifest subject (or the requested subset) in parallel."""
    ensure_dirs()
    require_free_space()
    manifest = load_manifest()
    url_map = load_url_map()

    all_subjects = sorted({r["subject"] for r in manifest})
    todo = subjects or all_subjects
    todo = [s for s in todo if s in set(all_subjects)]
    if not todo:
        return {"subjects": [], "bytes": 0, "downloaded_files": 0,
                "skipped_files": 0, "quarantined": [], "urls": len(url_map)}

    n_workers = n_workers or int(cfg.get("download", {}).get("n_workers", 3))
    totals = {"bytes": 0, "downloaded_files": 0, "skipped_files": 0,
              "quarantined": [], "subjects": []}
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {
            pool.submit(download_subject, s, manifest_for_subject(manifest, s),
                        url_map, cfg): s for s in todo
        }
        for fut in as_completed(futures):
            s = futures[fut]
            summary = fut.result()
            totals["subjects"].append(s)
            totals["bytes"] += summary["bytes"]
            totals["downloaded_files"] += summary["downloaded"]
            totals["skipped_files"] += summary["skipped"]
            if summary["quarantined"]:
                totals["quarantined"].append(s)
    return totals
