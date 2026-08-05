"""Recursive bucket listing and size survey without downloading (§4 + phase_0,5.md Task 1)."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import requests

from .bids import parse_bids_entities
from .paths import (
    artifact_dir,
    require_free_space,
    update_audit_yaml,
)

ACCESSION = "ds004796"
DISK_BUDGET_GB = 115
RESERVE_GB = 20

# OpenNeuro GraphQL API endpoint
GRAPHQL_URL = "https://openneuro.org/crn/graphql"

# GraphQL query to get all files recursively
GRAPHQL_QUERY = """
query GetDatasetFiles($datasetId: ID!, $tag: String!, $tree: String) {
  snapshot(datasetId: $datasetId, tag: $tag) {
    files(tree: $tree, recursive: true) {
      id
      filename
      size
      directory
      annexed
      urls
    }
  }
}
"""


def _get_latest_tag(dataset_id: str) -> str:
    """Get the latest snapshot tag for a dataset."""
    query = """
    query GetSnapshots($datasetId: ID!) {
      dataset(id: $datasetId) {
        snapshots {
          tag
          created
        }
      }
    }
    """
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": {"datasetId": dataset_id}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    snapshots = data.get("data", {}).get("dataset", {}).get("snapshots", [])
    if not snapshots:
        raise ValueError(f"No snapshots found for {dataset_id}")
    # Return the most recent snapshot
    return snapshots[0]["tag"]


def _list_bucket_graphql() -> list[dict] | None:
    """Use OpenNeuro GraphQL API to list all files.  Return parsed rows."""
    try:
        tag = _get_latest_tag(ACCESSION)
    except Exception:
        return None

    rows = []
    try:
        resp = requests.post(
            GRAPHQL_URL,
            json={
                "query": GRAPHQL_QUERY,
                "variables": {"datasetId": ACCESSION, "tag": tag},
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        files = data.get("data", {}).get("snapshot", {}).get("files", [])

        for f in files:
            if f.get("directory", False):
                continue  # Skip directories
            rows.append({
                "rel_path": f["filename"],
                "bytes": f.get("size", 0),
                "annexed": f.get("annexed", False),
            })
    except Exception:
        return None

    return rows


def _list_bucket_aws() -> list[dict] | None:
    """Use ``aws s3 ls --recursive`` to list every object.  Return parsed rows."""
    import shutil
    import subprocess

    if not shutil.which("aws"):
        return None

    s3_prefix = f"s3://openneuro.org/{ACCESSION}/"
    cmd = [
        "aws", "s3", "ls",
        "--no-sign-request",
        "--recursive",
        s3_prefix,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    rows = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            nbytes = int(parts[2])
        except ValueError:
            continue
        s3_path = parts[3]
        rel_path = s3_path[len(ACCESSION) + 1:]
        rows.append({"rel_path": rel_path, "bytes": nbytes})
    return rows


def _parse_listing(rows: list[dict]) -> list[dict]:
    """Enrich each row with modality, subject, task (via BIDS entity parser)."""
    enriched = []
    for row in rows:
        rel = row["rel_path"]
        parts = Path(rel).parts
        entities = parse_bids_entities(rel)

        modality = "root"
        subject = None
        task = None

        if len(parts) >= 2:
            # First component is usually "sub-XX/"
            if parts[0].startswith("sub-"):
                subject = parts[0]
            # Second component may be "eeg/", "anat/", "func/", "beh/"
            if len(parts) >= 3 and parts[1] in ("eeg", "anat", "func", "beh"):
                modality = parts[1]

        if entities:
            if entities.get("sub") and not subject:
                subject = f"sub-{entities['sub']}"
            task = entities.get("task")

        enriched.append({
            "path": rel,
            "bytes": row.get("bytes", 0),
            "modality": modality,
            "subject": subject,
            "task": task,
        })
    return enriched


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate_by_modality(rows: list[dict]) -> dict[str, int]:
    agg = defaultdict(int)
    for r in rows:
        agg[r["modality"]] += r["bytes"]
    return dict(agg)


def _aggregate_by_task(rows: list[dict]) -> dict[str, int]:
    agg = defaultdict(int)
    for r in rows:
        if r["task"]:
            agg[r["task"]] += r["bytes"]
    return dict(agg)


def _eeg_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["modality"] == "eeg"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run() -> dict:
    """Execute the size survey (§4).  Write size_survey.csv and return summary."""
    require_free_space()

    # Try GraphQL API first, then fall back to AWS CLI
    raw = _list_bucket_graphql()
    if raw is None:
        raw = _list_bucket_aws()
    if raw is None:
        raise RuntimeError(
            "Both GraphQL API and AWS CLI failed. "
            "Cannot perform size survey without a bucket listing."
        )

    rows = _parse_listing(raw)

    # phase_0,5.md Task 1: the original bug survived because nothing checked
    # that the task column had content. Assert it here, loudly.
    subject_rows = [r for r in rows if r["subject"] and r["modality"] == "eeg"]
    observed_tasks = sorted({r["task"] for r in subject_rows if r["task"]})
    print(f"  Observed EEG tasks: {observed_tasks}")
    if not observed_tasks:
        raise RuntimeError(
            "BIDS entity parsing produced an empty task set for subject-level "
            "EEG files — the listing may be unexpected or the parser is broken. "
            "Refusing to write size_survey.csv."
        )

    # Record the observed task set into config (phase_0,5.md Task 1)
    def _mutate(cfg):
        cfg["observed_tasks"] = observed_tasks
    update_audit_yaml(_mutate)

    # Write per-file CSV (staged atomically when inside a managed run)
    csv_path = artifact_dir() / "size_survey.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "modality", "subject", "task"])
        writer.writeheader()
        writer.writerows(rows)

    # Aggregations
    by_modality = _aggregate_by_modality(rows)
    by_task = _aggregate_by_task(rows)
    eeg = _eeg_rows(rows)
    eeg_total = sum(r["bytes"] for r in eeg)

    # Phase 1 download plan
    usable_gb = DISK_BUDGET_GB - RESERVE_GB
    eeg_gb = eeg_total / (1024 ** 3)
    fits_eeg = eeg_gb <= usable_gb

    # Subset: eyes-closed rest + MSIT only
    rest_msit = [r for r in eeg if r["task"] in ("rest", "msit")]
    rest_msit_total = sum(r["bytes"] for r in rest_msit)
    rest_msit_gb = rest_msit_total / (1024 ** 3)
    fits_subset = rest_msit_gb <= usable_gb

    summary = {
        "total_files": len(rows),
        "total_bytes": sum(r["bytes"] for r in rows),
        "by_modality": by_modality,
        "by_task_eeg": by_task,
        "eeg_total_bytes": eeg_total,
        "eeg_total_gb": round(eeg_gb, 2),
        "rest_msit_total_gb": round(rest_msit_gb, 2),
        "fits_eeg_in_budget": fits_eeg,
        "fits_subset_in_budget": fits_subset,
        "usable_budget_gb": usable_gb,
        "recommendation": (
            "Full EEG modality fits within budget"
            if fits_eeg
            else "Subset (rest + MSIT) recommended — full EEG exceeds budget"
        ),
        "csv_path": str(csv_path),
    }

    # Write summary table
    summary_path = artifact_dir() / "size_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write("=== Size Survey Summary ===\n\n")
        fh.write(f"Total files: {summary['total_files']}\n")
        fh.write(f"Total bytes: {summary['total_bytes']:,}\n\n")
        fh.write("By modality:\n")
        for mod, nbytes in sorted(by_modality.items()):
            fh.write(f"  {mod:15s}  {nbytes:>15,} bytes  ({nbytes / 1024**3:.2f} GB)\n")
        fh.write(f"\nEEG total:     {eeg_total:>15,} bytes  ({eeg_gb:.2f} GB)\n")
        fh.write(f"Rest+MSIT:     {rest_msit_total:>15,} bytes  ({rest_msit_gb:.2f} GB)\n")
        fh.write(f"\nUsable budget: {usable_gb} GB\n")
        fh.write(f"Fits full EEG: {fits_eeg}\n")
        fh.write(f"Fits subset:   {fits_subset}\n")
        fh.write(f"\nRecommendation: {summary['recommendation']}\n")

    summary["summary_path"] = str(summary_path)
    summary["observed_tasks"] = observed_tasks
    return summary
