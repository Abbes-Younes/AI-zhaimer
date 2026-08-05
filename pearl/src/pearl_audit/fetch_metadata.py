"""Fetch metadata files from OpenNeuro ds004796 (§3 of Plan.md)."""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .paths import (
    RAW_META_DIR,
    load_audit_yaml,
    record_download,
    require_free_space,
    update_audit_yaml,
    _sha256_file,
)


# ---------------------------------------------------------------------------
# Dataset constants
# ---------------------------------------------------------------------------

ACCESSION = "ds004796"
GRAPHQL_URL = "https://openneuro.org/crn/graphql"
S3_BUCKET_URL = f"https://openneuro.org/{ACCESSION}"

# Files to fetch (§3 of Plan.md)
METADATA_FILES = [
    "participants.tsv",
    "participants.json",
    "dataset_description.json",
    "README",
    "CHANGES",
]

# Glob for task sidecars at dataset root
TASK_SIDECAR_PATTERN = "task-*_eeg.json"


# ---------------------------------------------------------------------------
# AWS CLI route
# ---------------------------------------------------------------------------

def _aws_available() -> bool:
    """Return True if aws CLI is on PATH."""
    return shutil.which("aws") is not None


def _aws_cp(src_s3: str, dest: Path) -> bool:
    """Copy a single S3 object to *dest* using aws CLI.  Return True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "aws", "s3", "cp",
        "--no-sign-request",
        src_s3,
        str(dest),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _aws_ls_recursive() -> str | None:
    """List bucket recursively via aws CLI.  Return stdout or None."""
    cmd = [
        "aws", "s3", "ls",
        "--no-sign-request",
        "--recursive",
        "--summarize",
        f"s3://openneuro.org/{ACCESSION}/",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ---------------------------------------------------------------------------
# GraphQL route (preferred — no credentials needed)
# ---------------------------------------------------------------------------

_FILE_LIST_QUERY = """
query GetFiles($datasetId: ID!, $tag: String!) {
  snapshot(datasetId: $datasetId, tag: $tag) {
    files {
      filename
      size
      directory
      urls
    }
  }
}
"""

def _get_latest_tag() -> str | None:
    """Get the latest snapshot tag via GraphQL."""
    import requests as _requests
    q = '{ dataset(id: "%s") { snapshots { tag } } }' % ACCESSION
    try:
        r = _requests.post(GRAPHQL_URL, json={"query": q}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            snapshots = data.get("data", {}).get("dataset", {}).get("snapshots", [])
            if snapshots:
                return snapshots[0]["tag"]
    except Exception:
        pass
    return None


def _graphql_file_list() -> dict[str, dict] | None:
    """Fetch file listing via GraphQL.  Return {filename: {size, urls}}."""
    import requests as _requests
    tag = _get_latest_tag()
    if not tag:
        return None
    try:
        r = _requests.post(
            GRAPHQL_URL,
            json={"query": _FILE_LIST_QUERY, "variables": {"datasetId": ACCESSION, "tag": tag}},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        files = data.get("data", {}).get("snapshot", {}).get("files", [])
        result = {}
        for f in files:
            if not f.get("directory", False):
                result[f["filename"]] = {
                    "size": f.get("size", 0),
                    "urls": f.get("urls", []),
                }
        return result
    except Exception:
        return None


def _graphql_download(filename: str, dest: Path) -> bool:
    """Download a single file via GraphQL urls field."""
    import requests as _requests
    file_list = _graphql_file_list()
    if not file_list or filename not in file_list:
        return False
    urls = file_list[filename].get("urls", [])
    if not urls:
        return False
    url = urls[0] if isinstance(urls, list) else urls
    try:
        r = _requests.get(url, timeout=60, allow_redirects=True)
        if r.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# HTTPS fallback route (direct S3)
# ---------------------------------------------------------------------------

def _https_get(url: str, dest: Path) -> bool:
    """Download *url* to *dest* over HTTPS.  Return True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pearl-audit/0.1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            dest.write_bytes(data)
            return True
    except Exception:
        return False


def _resolve_https_url(relative: str) -> str:
    """Build the full HTTPS URL for a file in the bucket."""
    return f"https://openneuro.org.s3.amazonaws.com/{ACCESSION}/{relative}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_all_metadata() -> dict:
    """Fetch every metadata file listed in §3.  Return a summary dict.

    Raises
    ------
    RuntimeError
        If neither GraphQL, AWS CLI, nor HTTPS fallback succeeds for a critical file.
    """
    require_free_space()
    use_aws = _aws_available()

    summary = {"method": "graphql", "files": {}}

    for fname in METADATA_FILES:
        dest = RAW_META_DIR / fname

        # Try GraphQL first
        ok = _graphql_download(fname, dest)

        # Fall back to AWS CLI
        if not ok and use_aws:
            s3_url = f"s3://openneuro.org/{ACCESSION}/{fname}"
            ok = _aws_cp(s3_url, dest)

        # Fall back to HTTPS
        if not ok:
            https_url = _resolve_https_url(fname)
            ok = _https_get(https_url, dest)

        if not ok:
            # README and CHANGES are optional (§3: "if present")
            if fname in ("README", "CHANGES"):
                summary["files"][fname] = "not_found"
                continue
            raise RuntimeError(
                f"Failed to fetch {fname} — tried GraphQL, {'AWS CLI + ' if use_aws else ''}"
                f"HTTPS. Cannot proceed."
            )

        nbytes = dest.stat().st_size
        record_download(
            url=f"graphql://{ACCESSION}/{fname}",
            dest=dest,
            nbytes=nbytes,
        )
        summary["files"][fname] = {"bytes": nbytes, "path": str(dest)}

    # Fetch task sidecars (glob at dataset root via listing)
    _fetch_task_sidecars(use_aws, summary)

    return summary


def _fetch_task_sidecars(use_aws: bool, summary: dict) -> None:
    """Fetch task-*_eeg.json sidecar files."""
    # We cannot glob S3 directly; use the recursive listing to find them.
    # If we have aws CLI, we can use `aws s3 ls --recursive` filtered.
    if use_aws:
        cmd = [
            "aws", "s3", "ls",
            "--no-sign-request",
            "--recursive",
            f"s3://openneuro.org/{ACCESSION}/",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    # Format: "2024-01-01 00:00:00   12345 path/to/file"
                    parts = line.strip().split(None, 3)
                    if len(parts) < 4:
                        continue
                    s3_path = parts[3]
                    fname = Path(s3_path).name
                    if fname.startswith("task-") and fname.endswith("_eeg.json"):
                        dest = RAW_META_DIR / fname
                        s3_url = f"s3://openneuro.org/{ACCESSION}/{s3_path}"
                        https_url = _resolve_https_url(s3_path)
                        if _aws_cp(s3_url, dest):
                            nbytes = dest.stat().st_size
                            record_download(
                                url=s3_url, dest=dest, nbytes=nbytes,
                            )
                            summary["files"][fname] = {"bytes": nbytes, "path": str(dest)}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    else:
        # HTTPS: we don't have a listing API, so we try a few known task names.
        # This is a best-effort fallback; the Plan.md acknowledges this limitation.
        known_tasks = ["rest", "msit", "sternberg"]
        for task in known_tasks:
            fname = f"task-{task}_eeg.json"
            url = _resolve_https_url(fname)
            dest = RAW_META_DIR / fname
            if _https_get(url, dest):
                nbytes = dest.stat().st_size
                record_download(url=url, dest=dest, nbytes=nbytes)
                summary["files"][fname] = {"bytes": nbytes, "path": str(dest)}


def resolve_dataset_version() -> str | None:
    """Read dataset_description.json and return the DatasetVersion field."""
    desc_path = RAW_META_DIR / "dataset_description.json"
    if not desc_path.exists():
        return None
    with open(desc_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("DatasetVersion") or data.get("Version")


def _version_from_doi() -> str | None:
    """Extract a version string from the DatasetDOI field, e.g. ``...v1.0.0``."""
    desc_path = RAW_META_DIR / "dataset_description.json"
    if not desc_path.exists():
        return None
    with open(desc_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    doi = data.get("DatasetDOI", "")
    if "v" in doi.split("/")[-1]:
        return "v" + doi.split("/")[-1].split("v", 1)[1]
    return None


def _version_from_changes() -> str | None:
    """Parse a leading version line from CHANGES if present."""
    changes = RAW_META_DIR / "CHANGES"
    if not changes.exists():
        return None
    first = changes.read_text(encoding="utf-8").strip().splitlines()
    if not first:
        return None
    token = first[0].split()[0]
    if token.replace(".", "").isdigit():
        return token
    return None


def write_provenance_record(s3_listing_date: str | None = None) -> None:
    """Build and persist the composite provenance record (phase_0,5.md Task 3b).

    ``dataset_description.json`` carries no ``DatasetVersion`` field, so the
    version string is resolved from the DatasetDOI (authoritative), falling
    back to CHANGES. The participants.tsv SHA-256 is the real fingerprint.
    """
    import datetime as _dt

    doi_version = _version_from_doi()
    changes_version = _version_from_changes()
    version_string = doi_version or changes_version
    if doi_version:
        version_source = "DOI"
    elif changes_version:
        version_source = "CHANGES"
    else:
        version_source = None

    tsv = RAW_META_DIR / "participants.tsv"
    tsv_hash = _sha256_file(tsv) if tsv.exists() else None

    fetch_date = _dt.date.today().isoformat()
    listing_date = s3_listing_date or fetch_date

    def _mutate(cfg):
        cfg.setdefault("provenance", {})
        cfg["provenance"].update({
            "accession": ACCESSION,
            "version_source": version_source,
            "version_string": version_string,
            "fetch_date": fetch_date,
            "participants_tsv_sha256": tsv_hash,
            "s3_listing_date": listing_date,
        })

    update_audit_yaml(_mutate)


def write_columns_to_audit_yaml(col_map: dict) -> None:
    """Persist the resolved genotype column mapping (phase_0,5.md Task 3a)."""
    def _mutate(cfg):
        cfg.setdefault("columns", {})
        cfg["columns"].update({k: v for k, v in col_map.items()})

    update_audit_yaml(_mutate)


# Candidate demographic / lifestyle / health variables for the confound screen
# (phase_0,5.md Task 8). Names must match participants.tsv columns exactly;
# any that are absent from the schema are simply not recorded.
# education is a 3-level ordinal code — tested as categorical + monotone trend
# (Task 8), never as continuous, so it stays out of the continuous list.
SCREEN_CONTINUOUS_CANDIDATES = [
    "age", "BMI", "SES", "EHI", "BDI", "RPM",
    "leukocytes", "hemoglobin", "cholesterol_HDL", "LDL_cholesterol", "triglycerides",
]
SCREEN_CATEGORICAL_CANDIDATES = [
    "sex", "education", "smoking_status", "dementia_history_parents",
]


def write_screen_variables_to_audit_yaml() -> None:
    """Record which screen variables actually exist in participants.tsv.

    Persists the exact resolved column names under ``screen_variables`` so the
    confound screen never has to guess column names downstream.
    """
    import pandas as pd

    tsv = RAW_META_DIR / "participants.tsv"
    if not tsv.exists():
        return
    df = pd.read_csv(tsv, sep="\t")
    cols = set(df.columns)

    continuous = [c for c in SCREEN_CONTINUOUS_CANDIDATES if c in cols]
    categorical = [c for c in SCREEN_CATEGORICAL_CANDIDATES if c in cols]

    def _mutate(cfg):
        cfg["screen_variables"] = {
            "continuous": continuous,
            "categorical": categorical,
        }

    update_audit_yaml(_mutate)


def dump_participants_schema() -> Path:
    """Inspect participants.tsv columns and dtypes, write to reports/participants_schema.txt."""
    from .paths import REPORTS_DIR
    import pandas as pd

    tsv_path = RAW_META_DIR / "participants.tsv"
    if not tsv_path.exists():
        raise FileNotFoundError(f"{tsv_path} not found — fetch failed silently?")

    df = pd.read_csv(tsv_path, sep="\t")
    report_path = REPORTS_DIR / "participants_schema.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("=== participants.tsv schema ===\n")
    lines.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")
    lines.append("\nColumns and dtypes:\n")
    for col in df.columns:
        dtype = df[col].dtype
        nunique = df[col].nunique()
        sample = df[col].dropna().unique()[:5].tolist()
        lines.append(f"  {col:30s}  dtype={str(dtype):10s}  nunique={nunique}  sample={sample}\n")

    report_path.write_text("".join(lines), encoding="utf-8")
    return report_path


def identify_genotype_columns() -> dict:
    """Inspect participants.json + unique values to resolve APOE / PICALM columns.

    Returns a dict suitable for writing into audit.yaml ``columns``.
    """
    import pandas as pd

    tsv_path = RAW_META_DIR / "participants.tsv"
    json_path = RAW_META_DIR / "participants.json"
    df = pd.read_csv(tsv_path, sep="\t")

    # Load sidecar descriptions if available
    descriptions = {}
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as fh:
            sidecar = json.load(fh)
        # sidecar may be a dict of {ColumnName: {Description: ...}}
        for col_name, meta in sidecar.items():
            if isinstance(meta, dict):
                descriptions[col_name] = meta.get("Description", "")

    # Heuristic: look for columns containing 'apoe', 'picalm', 'age', 'sex', 'education'
    col_map = {
        "subject_id": None,
        "apoe": None,
        "picalm": None,
        "age": None,
        "sex": None,
        "education": None,
    }

    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ("participant_id", "subject_id", "sub"):
            col_map["subject_id"] = col
        elif "apoe" in col_lower:
            col_map["apoe"] = col
        elif "picalm" in col_lower:
            col_map["picalm"] = col
        elif col_lower == "age":
            col_map["age"] = col
        elif col_lower in ("sex", "gender"):
            col_map["sex"] = col
        elif "education" in col_lower or "edu" in col_lower:
            col_map["education"] = col

    # Log the raw values for genotype columns so we can design the normaliser
    if col_map["apoe"]:
        apoe_vals = df[col_map["apoe"]].dropna().unique().tolist()
    else:
        apoe_vals = []

    if col_map["picalm"]:
        picalm_vals = df[col_map["picalm"]].dropna().unique().tolist()
    else:
        picalm_vals = []

    return {
        "columns": col_map,
        "apoe_unique_values": sorted(str(v) for v in apoe_vals),
        "picalm_unique_values": sorted(str(v) for v in picalm_vals),
        "descriptions": descriptions,
    }


def run() -> dict:
    """Execute the full metadata-fetch step (§3 + phase_0,5.md Task 3)."""
    summary = fetch_all_metadata()
    version = resolve_dataset_version()
    if version:
        summary["dataset_version"] = version

    schema_path = dump_participants_schema()
    summary["schema_report"] = str(schema_path)

    genotype_info = identify_genotype_columns()
    summary["genotype_info"] = genotype_info

    # phase_0,5.md Task 3a: persist the resolved mapping, never re-derive it.
    if genotype_info.get("columns"):
        write_columns_to_audit_yaml(genotype_info["columns"])

    # phase_0,5.md Task 8: persist the exact confound-screen variable columns.
    write_screen_variables_to_audit_yaml()

    # phase_0,5.md Task 3b: composite provenance record.
    write_provenance_record()
    summary["provenance"] = load_audit_yaml().get("provenance", {})

    return summary
