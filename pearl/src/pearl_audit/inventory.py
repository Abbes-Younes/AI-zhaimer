"""EEG run inventory, effective-N and missingness analysis (§6 + phase_0,5.md Task 5)."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from .paths import (
    CLIENT_GROUPS_YAML,
    artifact_dir,
    load_audit_yaml,
)


def _load_size_survey() -> pd.DataFrame:
    """Load size_survey.csv (produced by size_survey.py)."""
    csv_path = artifact_dir() / "size_survey.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found — run size_survey first")
    return pd.read_csv(csv_path)


def _load_client_groups() -> dict[str, list[str]]:
    """Load client group subjects as {group_name: [subject_list]}."""
    with open(CLIENT_GROUPS_YAML, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return {k: v["subjects"] for k, v in cfg["groups"].items()}


def _load_cohort() -> pd.DataFrame:
    """Load cohort_definition.csv (produced by reconcile_groups)."""
    csv_path = artifact_dir() / "cohort_definition.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found — run reconcile_groups first")
    return pd.read_csv(csv_path)


def build_inventory(df: pd.DataFrame, cohort: pd.DataFrame) -> pd.DataFrame:
    """Build per-subject EEG task inventory from size_survey rows.

    One row per analysis-cohort subject (``final_include``), with boolean
    ``has_<task>`` columns and ``bytes_<task>`` size columns.
    """
    eeg = df[df["modality"] == "eeg"].copy()
    if eeg.empty:
        raise ValueError("No EEG rows in size_survey.csv")

    tasks = sorted(eeg["task"].dropna().unique())
    cohort_subjects = set(cohort.loc[cohort["final_include"], "subject"])
    subjects = sorted(s for s in eeg["subject"].dropna().unique() if s in cohort_subjects)

    rows = []
    for subj in subjects:
        row = {"subject": subj}
        subj_eeg = eeg[eeg["subject"] == subj]
        for task in tasks:
            task_files = subj_eeg[subj_eeg["task"] == task]
            has_file = len(task_files) > 0
            row[f"has_{task}"] = has_file
            row[f"bytes_{task}"] = int(task_files["bytes"].sum()) if has_file else 0
        row["total_eeg_bytes"] = int(subj_eeg["bytes"].sum())
        rows.append(row)

    return pd.DataFrame(rows)


def compute_effective_n(inventory: pd.DataFrame, groups: dict[str, list[str]]) -> pd.DataFrame:
    """Compute effective N — wide table: rows = task, columns = group + total.

    Returns a DataFrame with columns ``task``, one column per group name, and
    ``total``; each cell counts subjects with that task present.
    """
    tasks = [c.replace("has_", "") for c in inventory.columns if c.startswith("has_")]
    rows = []
    for task in tasks:
        row = {"task": task}
        for gname, subjects in groups.items():
            group_inv = inventory[inventory["subject"].isin(subjects)]
            row[gname] = int(group_inv[f"has_{task}"].sum())
        row["total"] = int(inventory[f"has_{task}"].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def missingness_by_group(inventory: pd.DataFrame, groups: dict[str, list[str]]) -> pd.DataFrame:
    """Detailed missingness per task per group, with a Fisher's exact p-value.

    The Fisher test answers: is missingness plausibly random across groups?
    A 2×k table of (missing, present) × group is used when k>2.
    """
    tasks = [c.replace("has_", "") for c in inventory.columns if c.startswith("has_")]
    group_names = list(groups.keys())

    rows = []
    for task in tasks:
        has = f"has_{task}"
        table = []
        used_groups = []
        for gname in group_names:
            group_inv = inventory[inventory["subject"].isin(groups[gname])]
            if group_inv.empty:
                continue  # group has no subjects in this inventory — nothing to test
            n_missing = int((~group_inv[has]).sum())
            n_present = int(group_inv[has].sum())
            table.append([n_missing, n_present])
            used_groups.append(gname)
        arr = np.array(table, dtype=int)

        # Fisher's exact for 2×2; chi-square with correction for larger tables.
        # Guard against degenerate tables (zero row/column sums) — report NaN.
        if arr.shape[0] < 2 or arr.sum() == 0 or np.any(arr.sum(axis=1) == 0) or np.any(arr.sum(axis=0) == 0):
            for gname in group_names:
                group_inv = inventory[inventory["subject"].isin(groups[gname])]
                n_missing = int((~group_inv[has]).sum())
                n_present = int(group_inv[has].sum())
                missing_subs = group_inv.loc[~group_inv[has], "subject"].tolist()
                rows.append({
                    "task": task, "group": gname,
                    "n_total": n_missing + n_present,
                    "n_have_data": n_present, "n_missing": n_missing,
                    "missing_subjects": ", ".join(missing_subs) if missing_subs else "",
                    "missingness_test": "n/a (degenerate table)", "missingness_p": float("nan"),
                })
            continue
        elif arr.shape[0] == 2:
            _, p = stats.fisher_exact(arr)
            test_name = "Fisher's exact"
        else:
            _, p, _, _ = stats.chi2_contingency(arr, correction=False)
            test_name = "chi-square (missing × group)"

        for i, gname in enumerate(used_groups):
            n_missing, n_present = int(arr[i][0]), int(arr[i][1])
            group_inv = inventory[inventory["subject"].isin(groups[gname])]
            missing_subs = group_inv.loc[~group_inv[has], "subject"].tolist()
            rows.append({
                "task": task,
                "group": gname,
                "n_total": n_missing + n_present,
                "n_have_data": n_present,
                "n_missing": n_missing,
                "missing_subjects": ", ".join(missing_subs) if missing_subs else "",
                "missingness_test": test_name,
                "missingness_p": round(float(p), 6),
            })
    return pd.DataFrame(rows)


def run() -> dict:
    """Execute the EEG inventory analysis (§6 + Task 5)."""
    size_df = _load_size_survey()
    cohort = _load_cohort()
    groups = _load_client_groups()

    # Build inventory (analysis-cohort subjects only)
    inventory = build_inventory(size_df, cohort)
    inv_path = artifact_dir() / "eeg_inventory.csv"
    inventory.to_csv(inv_path, index=False)

    # Effective N — wide table
    effective_n = compute_effective_n(inventory, groups)
    en_path = artifact_dir() / "effective_n.csv"
    effective_n.to_csv(en_path, index=False)

    # Missingness details + Fisher's exact per task
    missing = missingness_by_group(inventory, groups)
    miss_path = artifact_dir() / "missingness.csv"
    missing.to_csv(miss_path, index=False)

    # Verify the documented missingness (sub-51 sternberg, sub-55 rest)
    known_missing = {
        "sub-51": {"task": "sternberg", "documented": True},
        "sub-55": {"task": "rest", "documented": True},
    }
    verified = {}
    for subj, spec in known_missing.items():
        row = inventory[inventory["subject"] == subj]
        if row.empty:
            verified[subj] = {"documented_missing": spec["task"], "actually_missing": None,
                              "in_analysis_cohort": False}
            continue
        has_col = f"has_{spec['task']}"
        actually_missing = not bool(row.iloc[0][has_col]) if has_col in row.columns else None
        verified[subj] = {
            "documented_missing": spec["task"],
            "actually_missing": actually_missing,
            "in_analysis_cohort": True,
        }

    # Does missingness concentrate in A_P_plus (the smallest group)?
    eeg_cols = [c for c in inventory.columns if c.startswith("has_")]
    task_names = [c.replace("has_", "") for c in eeg_cols]
    a_pp = groups.get("A_P_plus", [])
    concentration = {}
    for task in task_names:
        miss_rows = missing[(missing["task"] == task) & (missing["group"] == "A_P_plus")]
        if not miss_rows.empty:
            concentration[task] = {
                "a_p_plus_missing": int(miss_rows.iloc[0]["n_missing"]),
                "a_p_plus_n": int(miss_rows.iloc[0]["n_total"]),
                "p": float(miss_rows.iloc[0]["missingness_p"]),
            }

    summary = {
        "total_subjects_in_inventory": len(inventory),
        "tasks_found": task_names,
        "effective_n_table": effective_n.to_dict(orient="records"),
        "missingness_table": missing.to_dict(orient="records"),
        "verified_known_missing": verified,
        "missingness_concentration_a_pp": concentration,
        "inventory_csv": str(inv_path),
        "effective_n_csv": str(en_path),
        "missingness_csv": str(miss_path),
    }

    return summary
