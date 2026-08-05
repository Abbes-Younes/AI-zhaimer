"""Genotype parsing and group reconciliation (§5 of Plan.md)."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import yaml

from .paths import (
    CLIENT_GROUPS_YAML,
    RAW_META_DIR,
    artifact_dir,
    load_audit_yaml,
)


# ---------------------------------------------------------------------------
# Load client groups
# ---------------------------------------------------------------------------

def load_client_groups() -> dict:
    """Load config/client_groups.yaml and return the ``groups`` dict."""
    with open(CLIENT_GROUPS_YAML, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return cfg["groups"]


def client_subject_set(groups: dict) -> dict[str, str]:
    """Return {subject_id: group_name} from the client YAML."""
    mapping = {}
    for gname, gdata in groups.items():
        for subj in gdata["subjects"]:
            mapping[subj] = gname
    return mapping


# ---------------------------------------------------------------------------
# Genotype normalisation
# ---------------------------------------------------------------------------

# Mapping from raw APOE string to (allele1, allele2) integers
_APOE_MAP = {
    "e3/e3": (3, 3), "3/3": (3, 3), "33": (3, 3), "E3E3": (3, 3),
    "e3/e4": (3, 4), "3/4": (3, 4), "34": (3, 4), "E3E4": (3, 4),
    "e4/e3": (4, 3), "4/3": (4, 3), "43": (4, 3), "E4E3": (4, 3),
    "e4/e4": (4, 4), "4/4": (4, 4), "44": (4, 4), "E4E4": (4, 4),
    "e2/e3": (2, 3), "2/3": (2, 3), "23": (2, 3), "E2E3": (2, 3),
    "e3/e2": (3, 2), "3/2": (3, 2), "32": (3, 2), "E3E2": (3, 2),
    "e2/e4": (2, 4), "2/4": (2, 4), "24": (2, 4), "E2E4": (2, 4),
    "e4/e2": (4, 2), "4/2": (4, 2), "42": (4, 2), "E4E2": (4, 2),
    "e2/e2": (2, 2), "2/2": (2, 2), "22": (2, 2), "E2E2": (2, 2),
}


def normalise_apoe(raw: str) -> tuple[int, int]:
    """Normalise an APOE genotype string to (allele1, allele2).

    Raises ValueError if the raw value is not recognised.
    """
    if pd.isna(raw) or str(raw).strip() in ("", "NA", "nan", "NaN", "N/A", "n/a"):
        raise ValueError("Missing APOE value")

    s = str(raw).strip().lower()

    # Try direct lookup (case-insensitive)
    for key, val in _APOE_MAP.items():
        if key.lower() == s:
            return val

    # Try splitting on common separators
    for sep in ["/", "-", " ", "_"]:
        parts = s.split(sep)
        if len(parts) == 2:
            try:
                a1, a2 = int(parts[0]), int(parts[1])
                if 1 <= a1 <= 4 and 1 <= a2 <= 4:
                    return (a1, a2)
            except ValueError:
                pass

    # Try two-letter allele notation: e3e4 -> (3, 4)
    m = __import__("re").match(r"^e(\d)e(\d)$", s)
    if m:
        a1, a2 = int(m.group(1)), int(m.group(2))
        if 1 <= a1 <= 4 and 1 <= a2 <= 4:
            return (a1, a2)

    raise ValueError(f"Unrecognised APOE format: {raw!r}")


def is_apoe_e4_carrier(alleles: tuple[int, int]) -> bool:
    """Return True if the subject carries at least one e4 allele."""
    return 4 in alleles


def is_apoe_e4_homozygote(alleles: tuple[int, int]) -> bool:
    """Return True if the subject is e4/e4 homozygous."""
    return alleles == (4, 4)


# PICALM normalisation
_PICALM_MAP = {
    "aa": "AA", "ag": "AG", "ga": "AG", "gg": "GG",
    "AA": "AA", "AG": "AG", "GA": "AG", "GG": "GG",
    "A/A": "AA", "A/G": "AG", "G/A": "AG", "G/G": "GG",
}


def normalise_picalm(raw: str) -> str:
    """Normalise a PICALM genotype to 'AA', 'AG', or 'GG'.

    Raises ValueError if the raw value is not recognised.
    """
    if pd.isna(raw) or str(raw).strip() in ("", "NA", "nan", "NaN", "N/A", "n/a"):
        raise ValueError("Missing PICALM value")

    s = str(raw).strip()

    # Direct lookup
    if s in _PICALM_MAP:
        return _PICALM_MAP[s]

    # Lowercase lookup
    if s.lower() in _PICALM_MAP:
        return _PICALM_MAP[s.lower()]

    raise ValueError(f"Unrecognised PICALM format: {raw!r}")


def is_picalm_risk(raw: str) -> bool:
    """Return True if PICALM is GG (risk allele)."""
    return normalise_picalm(raw) == "GG"


# ---------------------------------------------------------------------------
# Group derivation
# ---------------------------------------------------------------------------

def derive_group(apoe_raw: str, picalm_raw: str) -> str:
    """Derive group name from raw genotype values.

    Rules from client_groups.yaml:
    - N:       APOE e3/e3 + PICALM neutral (AA/AG)
    - A_P_minus: APOE e4 + PICALM neutral (AA/AG)
    - A_P_plus:  APOE e4 + PICALM risk (GG)
    """
    apoe_alleles = normalise_apoe(apoe_raw)
    picalm = normalise_picalm(picalm_raw)

    has_e4 = is_apoe_e4_carrier(apoe_alleles)
    is_e3e3 = apoe_alleles == (3, 3)
    is_risk = picalm == "GG"

    if is_e3e3 and not is_risk:
        return "N"
    elif has_e4 and not is_risk:
        return "A_P_minus"
    elif has_e4 and is_risk:
        return "A_P_plus"
    else:
        raise ValueError(
            f"Cannot derive group: APOE={apoe_raw!r} (alleles={apoe_alleles}), "
            f"PICALM={picalm_raw!r}"
        )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

# Status values (phase_0,5.md Task 2)
RECONCILED = "RECONCILED"          # in client list, derived == client
MISMATCH = "MISMATCH"              # in client list, derived != client
GENETIC_COHORT_ONLY = "GENETIC_COHORT_ONLY"  # in TSV, not in client list (no imaging expected)
MISSING_FROM_TSV = "MISSING_FROM_TSV"        # in client list, absent from participants.tsv


# statuses that count toward the stop-gate
BLOCKING_STATUSES = (MISMATCH, MISSING_FROM_TSV)


def _resolve_columns(df: pd.DataFrame) -> dict:
    """Resolve genotype columns strictly from config/audit.yaml.

    phase_0,5.md Task 3a: every heuristic fallback is deleted. If the mapping
    was not persisted by fetch_metadata, we raise — guessing the wrong
    genotype column would silently mislabel the whole dataset.
    """
    audit_cfg = load_audit_yaml()
    col_map = audit_cfg.get("columns", {})

    subj_col = col_map.get("subject_id")
    apoe_col = col_map.get("apoe")
    picalm_col = col_map.get("picalm")

    missing = []
    if not subj_col:
        missing.append("subject_id")
    if not apoe_col:
        missing.append("apoe")
    if not picalm_col:
        missing.append("picalm")
    if missing:
        raise ValueError(
            "config/audit.yaml has no resolved column mapping for: "
            + ", ".join(missing)
            + ". Run fetch_metadata first; refusing to guess."
        )
    if subj_col not in df.columns or apoe_col not in df.columns or picalm_col not in df.columns:
        raise ValueError(
            f"Resolved columns {subj_col!r}/{apoe_col!r}/{picalm_col!r} not present "
            f"in participants.tsv — the mapping is stale; re-run fetch_metadata."
        )
    return col_map


def _has_any_eeg() -> set[str]:
    """Subjects present in the size survey's EEG rows (from size_survey.csv)."""
    survey_path = artifact_dir() / "size_survey.csv"
    if not survey_path.exists():
        return set()
    survey = pd.read_csv(survey_path)
    eeg = survey[survey.get("modality") == "eeg"]
    return set(eeg["subject"].dropna())


def build_cohort_definition(
    tsv_subjects: set[str],
    client_subjects: set[str],
    eeg_subjects: set[str],
) -> pd.DataFrame:
    """Define the analysis cohort explicitly (phase_0,5.md Task 2).

    One row per subject anywhere in the union of participants.tsv and the
    client list. ``final_include`` = in client list AND in TSV AND has EEG —
    everything downstream filters on this flag.
    """
    all_subjects = sorted(tsv_subjects | client_subjects)
    rows = []
    for subj in all_subjects:
        in_client = subj in client_subjects
        in_tsv = subj in tsv_subjects
        has_eeg = subj in eeg_subjects
        rows.append({
            "subject": subj,
            "in_client_list": in_client,
            "in_participants_tsv": in_tsv,
            "has_any_eeg": has_eeg,
            "final_include": in_client and in_tsv and has_eeg,
        })
    return pd.DataFrame(rows)


def reconcile() -> dict:
    """Run the full reconciliation (§5 + phase_0,5.md Task 2).

    Writes group_reconciliation.csv (with a three-valued ``status`` column)
    and cohort_definition.csv. Returns a summary dict.
    """
    groups = load_client_groups()
    client_map = client_subject_set(groups)

    tsv_path = RAW_META_DIR / "participants.tsv"
    if not tsv_path.exists():
        raise FileNotFoundError(f"{tsv_path} not found — run fetch_metadata first")

    df = pd.read_csv(tsv_path, sep="\t")
    col_map = _resolve_columns(df)
    subj_col, apoe_col, picalm_col = col_map["subject_id"], col_map["apoe"], col_map["picalm"]

    df["_subject_id"] = df[subj_col].apply(lambda x: _normalise_subj_id(x))
    tsv_subjects = set(df["_subject_id"])
    client_subjects = set(client_map.keys())

    rows = []
    mismatches = []
    sub69_info = {"present_in_tsv": False, "status": "absent_from_tsv"}

    for _, row in df.iterrows():
        subj = row["_subject_id"]
        apoe_raw = row[apoe_col]
        picalm_raw = row[picalm_col]

        if subj == "sub-69":
            sub69_info = {
                "present_in_tsv": True,
                "status": "present_in_tsv",
                "apoe_raw": str(apoe_raw),
                "picalm_raw": str(picalm_raw),
            }

        try:
            apoe_norm = normalise_apoe(apoe_raw)
            apoe_str = f"{apoe_norm[0]}/{apoe_norm[1]}"
        except ValueError as e:
            apoe_str = f"ERROR: {e}"

        try:
            picalm_norm = normalise_picalm(picalm_raw)
        except ValueError as e:
            picalm_norm = f"ERROR: {e}"

        try:
            group_derived = derive_group(apoe_raw, picalm_raw)
        except ValueError:
            group_derived = "UNRESOLVABLE"

        group_client = client_map.get(subj, "NOT_IN_CLIENT_LIST")
        if group_client == "NOT_IN_CLIENT_LIST":
            status = GENETIC_COHORT_ONLY
        elif group_derived == group_client:
            status = RECONCILED
        else:
            status = MISMATCH
            mismatches.append(subj)

        rows.append({
            "subject": subj,
            "apoe_raw": str(apoe_raw),
            "picalm_raw": str(picalm_raw),
            "apoe_norm": apoe_str,
            "picalm_norm": picalm_norm,
            "group_derived": group_derived,
            "group_client": group_client,
            "status": status,
        })

    # Client-list subjects absent from participants.tsv
    missing_from_tsv = sorted(client_subjects - tsv_subjects)
    for subj in missing_from_tsv:
        rows.append({
            "subject": subj,
            "apoe_raw": "",
            "picalm_raw": "",
            "apoe_norm": "",
            "picalm_norm": "",
            "group_derived": "",
            "group_client": client_map[subj],
            "status": MISSING_FROM_TSV,
        })

    # Count e4/e4 homozygotes in the A_P_plus group (derived)
    a_p_plus_derived = [r for r in rows if r["group_derived"] == "A_P_plus"]
    e4_homozygotes = 0
    for r in a_p_plus_derived:
        try:
            alleles = normalise_apoe(r["apoe_raw"])
            if is_apoe_e4_homozygote(alleles):
                e4_homozygotes += 1
        except ValueError:
            pass

    # Write reconciliation CSV (staged atomically when inside a managed run)
    csv_path = artifact_dir() / "group_reconciliation.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "subject", "apoe_raw", "picalm_raw", "apoe_norm", "picalm_norm",
            "group_derived", "group_client", "status",
        ])
        writer.writeheader()
        writer.writerows(rows)

    # Write cohort definition CSV
    cohort = build_cohort_definition(tsv_subjects, client_subjects, _has_any_eeg())
    cohort_path = artifact_dir() / "cohort_definition.csv"
    cohort.to_csv(cohort_path, index=False)

    blocking = [r for r in rows if r["status"] in BLOCKING_STATUSES]

    summary = {
        "total_subjects_in_tsv": len(tsv_subjects),
        "total_client_subjects": len(client_subjects),
        "genetic_cohort_only_count": sum(1 for r in rows if r["status"] == GENETIC_COHORT_ONLY),
        "mismatches": [r["subject"] for r in rows if r["status"] == MISMATCH],
        "mismatch_count": len(blocking),
        "missing_from_tsv": missing_from_tsv,
        "sub_69": sub69_info,
        "e4_homozygotes_in_A_P_plus": e4_homozygotes,
        "e4_homozygotes_claim": 2,
        "cohort": cohort.to_dict(orient="records"),
        "analysis_cohort_count": int(cohort["final_include"].sum()),
        "csv_path": str(csv_path),
        "cohort_path": str(cohort_path),
    }

    return summary


def _normalise_subj_id(val) -> str:
    """Normalise a subject ID to sub-XX format."""
    s = str(val).strip()
    # Already correct format
    if s.startswith("sub-"):
        return s
    # Numeric only (e.g., "01" or "1")
    try:
        num = int(s)
        return f"sub-{num:02d}"
    except ValueError:
        pass
    # Try extracting digits
    import re
    m = re.search(r"(\d+)", s)
    if m:
        num = int(m.group(1))
        return f"sub-{num:02d}"
    return s


# Alias for CLI compatibility
run = reconcile
