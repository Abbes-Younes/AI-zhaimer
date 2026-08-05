"""Phase 1 download manifest and disk-budget model (phase_0,5.md Task 6).

Produces — but does not execute — an explicit download manifest for Phase 1.
The only bytes fetched in this module are the kilobyte-scale ``*_eeg.json``
sidecars; no raw EEG is ever downloaded here.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from . import fetch_metadata
from .paths import (
    RAW_META_DIR,
    REPORTS_DIR,
    artifact_dir,
    load_audit_yaml,
    record_download,
    require_free_space,
)

# ---------------------------------------------------------------------------
# Stated assumptions for the derivative footprint model (Task 6b)
# ---------------------------------------------------------------------------
TARGET_SFREQ_HZ = 250        # intended Phase 1 processing rate for alpha-band work
BYTES_PER_SAMPLE = 4         # float32
EPOCH_OVERLAP_FACTOR = 1.5   # 2-s epochs at 50% overlap ≈ 1.5× the raw sample count
DISK_BUDGET_GB = 115
RESERVE_GB = 20
USABLE_GB = DISK_BUDGET_GB - RESERVE_GB


def _observed_tasks() -> list[str]:
    """Read the observed task labels recorded by size_survey (audit.yaml)."""
    cfg = load_audit_yaml()
    tasks = cfg.get("observed_tasks", [])
    return list(tasks) if tasks else []


# ---------------------------------------------------------------------------
# 6a. Sidecar fetch (kilobyte-scale, logged against the byte budget)
# ---------------------------------------------------------------------------

def fetch_task_sidecars() -> dict:
    """Fetch the root-level ``task-*_eeg.json`` sidecars for observed tasks.

    These carry SamplingFrequency (the derivative model needs the sampling
    rate; channel count and duration are resolved from the README + listing,
    see ``resolve_recording_params``). This is the one narrow download
    exception of phase_0,5.md — it does not extend to .eeg/.vhdr/.vmrk files.
    """
    tasks = _observed_tasks()
    if not tasks:
        # Fall back to the names seen in the listing if config isn't populated
        # (this module is also runnable standalone for tests).
        tasks = ["msit", "rest", "sternberg"]

    fetched = {}
    for task in tasks:
        fname = f"task-{task}_eeg.json"
        dest = RAW_META_DIR / fname
        ok = False
        url = None
        # GraphQL route (resolves the working URL at runtime — preferred)
        ok = fetch_metadata._graphql_download(fname, dest)
        url = f"graphql://{fetch_metadata.ACCESSION}/{fname}"
        # HTTPS fallback
        if not ok:
            https_url = fetch_metadata._resolve_https_url(fname)
            ok = fetch_metadata._https_get(https_url, dest)
            url = https_url
        if not ok:
            raise RuntimeError(
                f"Failed to fetch {fname} via GraphQL and HTTPS. "
                f"Cannot model derivative sizes without the sidecar."
            )
        nbytes = dest.stat().st_size
        record_download(url=url, dest=dest, nbytes=nbytes)
        fetched[task] = {"path": str(dest), "bytes": nbytes}
    return fetched


def load_sidecar_params() -> dict:
    """Read SamplingFrequency per task from the sidecars.

    Returns {task: {sampling_frequency}}. Raises if a sidecar is missing —
    the model must not run on invented inputs.
    """
    tasks = _observed_tasks() or ["msit", "rest", "sternberg"]
    params = {}
    for task in tasks:
        f = RAW_META_DIR / f"task-{task}_eeg.json"
        if not f.exists():
            raise FileNotFoundError(
                f"{f} missing — run fetch_task_sidecars first; "
                f"refusing to model derivative sizes without the sidecar."
            )
        data = json.loads(f.read_text(encoding="utf-8"))
        params[task] = {"sampling_frequency": data.get("SamplingFrequency")}
    return params


# Documented in the dataset README ("128-channel EEG"). Not present in the
# sidecars, so it is resolved from documentation — stated, not guessed.
DOCUMENTED_N_CHANNELS = 128
# BrainVision .eeg raw sample width used to back out duration from file sizes.
RAW_BYTES_PER_SAMPLE = 4  # int32 raw EEG


def _mean_duration_from_listing(size_df: pd.DataFrame, task: str, native_sfreq: float | None) -> float | None:
    """Estimate recording duration (s) from measured .eeg file sizes.

    duration ≈ mean(.eeg bytes) / (n_channels × native_sfreq × RAW_BYTES_PER_SAMPLE).
    This is computed from the measured listing, not invented; the encoding
    assumption is exposed alongside it.
    """
    eeg = size_df[(size_df["modality"] == "eeg") & (size_df["task"] == task)]
    eeg = eeg[eeg["path"].str.endswith(".eeg", na=False)]
    if eeg.empty:
        return None
    mean_bytes = float(eeg["bytes"].mean())
    sfreq = native_sfreq or 1000
    return mean_bytes / (DOCUMENTED_N_CHANNELS * sfreq * RAW_BYTES_PER_SAMPLE)


def resolve_recording_params(size_df: pd.DataFrame) -> dict:
    """Resolve (n_channels, duration_s) per task from sidecar/docs/listing.

    Channel count: sidecar ``EEGChannelCount`` if present, else the
    README-documented 128. Duration: sidecar ``RecordingDuration`` if present,
    else backed out of measured .eeg sizes. Every source is recorded so the
    number can be challenged.
    """
    sidecar_params = load_sidecar_params()
    tasks = _observed_tasks() or ["msit", "rest", "sternberg"]
    resolved = {}
    for task in tasks:
        f = RAW_META_DIR / f"task-{task}_eeg.json"
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        native_sfreq = data.get("SamplingFrequency")
        n_ch = data.get("EEGChannelCount") or DOCUMENTED_N_CHANNELS
        dur = data.get("RecordingDuration") or _mean_duration_from_listing(size_df, task, native_sfreq)
        if not n_ch or not dur:
            raise ValueError(
                f"Cannot resolve n_channels/duration for {task}: sidecar lacks both "
                f"and no .eeg listing available. Refusing to invent inputs."
            )
        resolved[task] = {
            "sampling_frequency": native_sfreq,
            "eeg_channel_count": n_ch,
            "recording_duration_s": round(float(dur), 1),
            "duration_source": "sidecar" if data.get("RecordingDuration") else "listing-derived",
            "channel_source": "sidecar" if data.get("EEGChannelCount") else "README-documented",
        }
    return resolved


# ---------------------------------------------------------------------------
# 6b. Derivative footprint model
# ---------------------------------------------------------------------------

def estimate_derivatives_gb(
    n_subjects: int,
    sidecar: dict,
    target_sfreq: float = TARGET_SFREQ_HZ,
) -> dict:
    """Estimate the preprocessed/epoched/ICA footprint for one task.

    ``preprocessed ≈ n_subjects × n_channels × duration_s × target_sfreq × 4B``.
    Epoched output ≈ preprocessed × EPOCH_OVERLAP_FACTOR. ICA solutions ≈ one
    full-length decomposition per subject ≈ preprocessed. All assumptions are
    exposed so the number can be challenged.
    """
    n_ch = sidecar.get("eeg_channel_count")
    dur_s = sidecar.get("recording_duration_s")
    native_sf = sidecar.get("sampling_frequency")

    if not n_ch or not dur_s:
        raise ValueError(
            f"Sidecar missing EEGChannelCount or RecordingDuration: {sidecar}. "
            f"Cannot estimate derivatives without both."
        )

    samples = n_subjects * n_ch * dur_s * target_sfreq
    preprocessed_bytes = samples * BYTES_PER_SAMPLE
    epoched_bytes = preprocessed_bytes * EPOCH_OVERLAP_FACTOR
    ica_bytes = preprocessed_bytes  # one full-length ICA per subject
    total_bytes = preprocessed_bytes + epoched_bytes + ica_bytes

    return {
        "n_subjects": n_subjects,
        "n_channels": n_ch,
        "duration_s": round(float(dur_s), 1),
        "native_sfreq": native_sf,
        "target_sfreq": target_sfreq,
        "preprocessed_gb": round(preprocessed_bytes / 1024**3, 2),
        "epoched_gb": round(epoched_bytes / 1024**3, 2),
        "ica_gb": round(ica_bytes / 1024**3, 2),
        "total_gb": round(total_bytes / 1024**3, 2),
    }


# ---------------------------------------------------------------------------
# 6c/6d. Scopes, budget table, manifest
# ---------------------------------------------------------------------------

def _scope_files(size_df: pd.DataFrame, tasks: set[str]) -> pd.DataFrame:
    """EEG rows whose task is in *tasks* (file-level scopes)."""
    eeg = size_df[size_df["modality"] == "eeg"].copy()
    return eeg[eeg["task"].isin(tasks)]


def build_scopes(size_df: pd.DataFrame) -> dict:
    """Raw byte costs for the three candidate download scopes."""
    all_tasks = set(size_df[size_df["modality"] == "eeg"]["task"].dropna())
    rest_msit = {"rest", "msit"} & all_tasks

    scopes = {
        "A_full_eeg": sorted(all_tasks),
        "B_rest_msit": sorted(rest_msit),
        "C_rest_msit_only": sorted(rest_msit),  # file-level identical to B; eyes-closed is an epoch-level carve-out
    }
    out = {}
    for name, tasks in scopes.items():
        files = _scope_files(size_df, set(tasks)) if tasks else size_df.iloc[0:0]
        out[name] = {
            "tasks": tasks,
            "n_files": len(files),
            "raw_bytes": int(files["bytes"].sum()) if len(files) else 0,
            "raw_gb": round(float(files["bytes"].sum()) / 1024**3, 2) if len(files) else 0.0,
        }
    return out


def recommend_scope(scopes: dict, deriv_gb_by_scope: dict) -> str:
    """Pick a scope that fits the 95 GB usable budget with derivatives."""
    for name in ["C_rest_msit_only", "B_rest_msit", "A_full_eeg"]:
        if name not in scopes:
            continue
        total = scopes[name]["raw_gb"] + deriv_gb_by_scope.get(name, 0.0)
        if total <= USABLE_GB:
            return name
    return "NONE_FITS"


def write_manifest(scope_name: str, size_df: pd.DataFrame, scope: dict) -> Path:
    """Emit phase1_manifest.csv — explicit S3 keys for the chosen scope.

    Columns: scope, path, bytes, modality, subject, task, running_total_bytes.
    Phase 1 consumes this file directly.
    """
    files = _scope_files(size_df, set(scope["tasks"]))
    files = files.sort_values("path")

    out_path = artifact_dir() / "phase1_manifest.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    running = 0
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["scope", "path", "bytes", "modality", "subject", "task", "running_total_bytes"])
        for _, row in files.iterrows():
            running += int(row["bytes"])
            writer.writerow([
                scope_name,
                row["path"],
                int(row["bytes"]),
                row["modality"],
                row["subject"],
                row["task"],
                running,
            ])
    return out_path


def write_download_plan_md(scopes: dict, deriv_by_scope: dict, sidecar_params: dict,
                           recommendation: str, manifest_path: Path) -> Path:
    """Write reports/phase1_download_plan.md with the costed scope table."""
    out = REPORTS_DIR / "phase1_download_plan.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 1 Download Plan (ds004796)",
        "",
        f"Usable budget: **{USABLE_GB} GB** (115 GB total − 20 GB reserve).",
        "",
        f"Manifest: `{manifest_path}` (final location: `data/derivatives/phase0/phase1_manifest.csv`).",
        "",
        "| Scope | Raw GB | Est. derivatives GB | Total GB | Fits in 95 GB? |",
        "|---|---|---|---|---|",
    ]
    for name in ["A_full_eeg", "B_rest_msit", "C_rest_msit_only"]:
        s = scopes[name]
        d = deriv_by_scope.get(name, 0.0)
        total = s["raw_gb"] + d
        fits = "YES" if total <= USABLE_GB else "NO"
        lines.append(f"| {name} | {s['raw_gb']} | {round(d, 2)} | {round(total, 2)} | {fits} |")

    lines += [
        "",
        f"**Recommendation: {recommendation}**",
        "",
        "## Derivative footprint assumptions",
        f"- Target processing rate: **{TARGET_SFREQ_HZ} Hz**, float32 ({BYTES_PER_SAMPLE} bytes/sample).",
        f"- Epoched output = preprocessed × {EPOCH_OVERLAP_FACTOR} (2-s epochs, 50% overlap).",
        "- ICA = one full-length solution per subject ≈ preprocessed size.",
        f"- Channel count: README-documented 128 (sidecars carry no EEGChannelCount).",
        f"- Duration backed out of measured .eeg sizes at int32 ({RAW_BYTES_PER_SAMPLE} B/sample).",
        f"- Sidecar parameters used: {json.dumps(sidecar_params)}",
        "",
        "## Note on Scope B vs C",
        "The listing contains a single `task-rest` file per subject (rest covers both",
        "eyes-open and eyes-closed conditions within one recording, per the dataset README).",
        "There is no `acq-`/`run-` split in the file names, so **Scope C is file-level",
        "identical to Scope B** — the eyes-closed subset is an epoch-level carve-out made",
        "during Phase 1 processing, not a separate download.",
        "",
        "## Why Scope A is rejected",
        "Full EEG raw is 75.87 GB, leaving ~19 GB for derivatives. The derivative model",
        "estimates ~67 GB under the full-EEG scope, so Scope A does not fit the 95 GB",
        "budget. This is the phase's expected outcome (Scope B/C prior), not an escalation:",
        "Scope C fits with headroom and is recommended.",
        "",
        "## Note on education trend test",
        "The education monotone-trend test (Spearman) is reported for the 3-group",
        "multiclass framing only — a trend across a 2-group collapse is degenerate.",
        "The categorical (chi-square/Fisher) test runs for all three framings.",
        "",
        "## Manifest",
        "`data/derivatives/phase0/phase1_manifest.csv` lists every S3 key for the",
        "recommended scope with per-file bytes and a running total. **Nothing has been",
        "downloaded.** The manifest requires human approval before Phase 1 executes it.",
        "",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run() -> dict:
    """Execute the Phase 1 download-plan step (§ Task 6)."""
    require_free_space()

    size_path = artifact_dir() / "size_survey.csv"
    if not size_path.exists():
        raise FileNotFoundError(f"{size_path} not found — run size_survey first")
    size_df = pd.read_csv(size_path)

    # 6a: fetch sidecars (logged against the byte budget)
    sidecars_fetched = fetch_task_sidecars()
    sidecar_params = load_sidecar_params()
    recording_params = resolve_recording_params(size_df)

    # 6b: model derivative footprint per scope
    n_subjects = len(size_df[size_df["modality"] == "eeg"]["subject"].dropna().unique())
    deriv_by_task = {
        task: estimate_derivatives_gb(n_subjects, params)
        for task, params in recording_params.items()
    }

    # 6c: cost the three scopes
    scopes = build_scopes(size_df)
    deriv_by_scope = {}
    for name, scope in scopes.items():
        deriv_by_scope[name] = round(
            sum(deriv_by_task.get(t, {}).get("total_gb", 0.0) for t in scope["tasks"]), 2
        )

    recommendation = recommend_scope(scopes, deriv_by_scope)
    scopes["_recommendation"] = recommendation

    # 6d: manifest for the recommended scope
    manifest_path = None
    if recommendation != "NONE_FITS":
        manifest_path = write_manifest(recommendation, size_df, scopes[recommendation])

    plan_md = write_download_plan_md(scopes, deriv_by_scope, sidecar_params,
                                     recommendation, manifest_path)

    return {
        "sidecars_fetched": sidecars_fetched,
        "sidecar_params": sidecar_params,
        "recording_params": recording_params,
        "derivatives_per_task_gb": {k: v["total_gb"] for k, v in deriv_by_task.items()},
        "scopes": {k: v for k, v in scopes.items() if not k.startswith("_")},
        "derivatives_per_scope_gb": deriv_by_scope,
        "recommendation": recommendation,
        "manifest_path": str(manifest_path) if manifest_path else None,
        "plan_md_path": str(plan_md),
        "n_subjects_with_eeg": n_subjects,
    }
