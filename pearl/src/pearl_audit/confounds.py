"""Confound analysis with statistical tests (§7 + phase_0,5.md Task 8)."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from .paths import (
    CLIENT_GROUPS_YAML,
    RAW_META_DIR,
    artifact_dir,
    load_audit_yaml,
)

RNG_SEED = 20260805
N_BOOTSTRAP = 2000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_participants() -> pd.DataFrame:
    tsv = RAW_META_DIR / "participants.tsv"
    if not tsv.exists():
        raise FileNotFoundError(f"{tsv} not found — run fetch_metadata first")
    return pd.read_csv(tsv, sep="\t")


def _load_groups() -> dict[str, list[str]]:
    with open(CLIENT_GROUPS_YAML, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return {k: v["subjects"] for k, v in cfg["groups"].items()}


def _load_cohort() -> pd.DataFrame:
    csv_path = artifact_dir() / "cohort_definition.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found — run reconcile_groups first")
    return pd.read_csv(csv_path)


def _resolve_column(var: str, col_map: dict) -> str:
    """Resolve a variable's column strictly from config/audit.yaml (Task 3a)."""
    col = col_map.get(var)
    if not col:
        raise ValueError(
            f"config/audit.yaml has no resolved column for {var!r}. "
            f"Run fetch_metadata first; refusing to guess."
        )
    return col


def _get_col_mapping() -> dict:
    return load_audit_yaml().get("columns", {})


def _verdict(p: float, effect_size: float) -> str:
    """Assign a plain verdict based on p-value and effect size."""
    if p < 0.05 and abs(effect_size) >= 0.5:
        return "blocking"
    elif p < 0.10 or abs(effect_size) >= 0.3:
        return "watch"
    else:
        return "clear"


def _mitigation(variable: str, verdict: str) -> str:
    """State the required mitigation for Phase 3."""
    if verdict == "blocking":
        return f"Must include {variable} as covariate or use matched subsampling"
    elif verdict == "watch":
        return f"Consider including {variable} as covariate in Phase 3 models"
    return ""


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals (phase_0,5.md Task 8)
# ---------------------------------------------------------------------------

def _bootstrap_ci(stat_fn, group_data: list[np.ndarray], n_resamples: int = N_BOOTSTRAP) -> tuple[float, float]:
    """Stratified bootstrap CI (2.5th–97.5th percentile) for an effect size.

    Resamples within each group (preserving group sizes), recomputes the
    statistic each time. At n=79 the CIs will be wide — that is the finding.
    """
    rng = np.random.default_rng(RNG_SEED)
    estimates = []
    sizes = [len(g) for g in group_data]
    for _ in range(n_resamples):
        resampled = [
            g[rng.integers(0, len(g), size=len(g))] if len(g) else g
            for g in group_data
        ]
        try:
            estimates.append(stat_fn(resampled))
        except Exception:
            continue
    if len(estimates) < 50:
        return (np.nan, np.nan)
    lo, hi = np.percentile(estimates, [2.5, 97.5])
    return (round(float(lo), 4), round(float(hi), 4))


def _kw_eta2(resampled: list[np.ndarray]) -> float:
    """ε² for Kruskal-Wallis computed on a resampled dataset."""
    stat, _ = stats.kruskal(*resampled)
    n = sum(len(g) for g in resampled)
    k = len(resampled)
    return (stat - k + 1) / (n - k) if n > k else 0.0


def _cramers_v_from_table(table: np.ndarray) -> float:
    """Cramér's V from a contingency table (rows = groups, cols = levels)."""
    table = np.asarray(table, dtype=float)
    total = table.sum()
    if total == 0:
        return 0.0
    row_sums = table.sum(axis=1, keepdims=True)
    col_sums = table.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        expected = np.outer(row_sums, col_sums) / total
        mask = expected > 0
        chi2 = float(np.sum((table[mask] - expected[mask]) ** 2 / expected[mask]))
    k = min(table.shape) - 1
    if k <= 0:
        return 0.0
    return float(np.sqrt(max(chi2 / (total * k), 0.0)))


def _rank_biserial_from_table(table: np.ndarray) -> float:
    """Rank-biserial correlation from a 2x2 contingency table."""
    a, b, c, d = np.asarray(table, dtype=float).ravel()
    n = a + b + c + d
    if n == 0:
        return 0.0
    return (a * d - b * c) / np.sqrt((a + b) * (a + c) * (b + d) * (c + d))


def _bootstrap_categorical_ci(levels: list[int], data_groups: list[np.ndarray],
                              effect_fn, n_resamples: int = N_BOOTSTRAP) -> tuple[float, float]:
    """Stratified bootstrap CI for a categorical effect size."""
    rng = np.random.default_rng(RNG_SEED)
    estimates = []
    for _ in range(n_resamples):
        table = np.zeros((len(data_groups), len(levels)), dtype=float)
        for gi, g in enumerate(data_groups):
            idx = rng.integers(0, len(g), size=len(g))
            sample = g[idx]
            for li, level in enumerate(levels):
                table[gi, li] = np.sum(sample == level)
        try:
            estimates.append(effect_fn(table))
        except Exception:
            continue
    if len(estimates) < 50:
        return (np.nan, np.nan)
    lo, hi = np.percentile(estimates, [2.5, 97.5])
    return (round(float(lo), 4), round(float(hi), 4))


# ---------------------------------------------------------------------------
# Analysis per variable
# ---------------------------------------------------------------------------

def _analyse_continuous(df: pd.DataFrame, var: str, groups: dict[str, list[str]],
                        group_col: str) -> dict | None:
    """Kruskal–Wallis test for a continuous variable across groups, with CI."""
    data_groups = []
    labels = []
    for gname, subjects in groups.items():
        vals = df[df[group_col].isin(subjects)][var].dropna()
        if len(vals) < 3:
            return None
        data_groups.append(vals.values.astype(float))
        labels.append(gname)

    if len(data_groups) < 2:
        return None

    stat, p = stats.kruskal(*data_groups)

    n = sum(len(g) for g in data_groups)
    k = len(data_groups)
    eta_sq = (stat - k + 1) / (n - k) if n > k else 0.0

    ci_lo, ci_hi = _bootstrap_ci(_kw_eta2, data_groups)

    descriptives = {}
    for gname, vals in zip(labels, data_groups):
        descriptives[gname] = {
            "n": len(vals),
            "mean": round(float(np.mean(vals)), 3),
            "std": round(float(np.std(vals, ddof=1)), 3),
            "median": round(float(np.median(vals)), 3),
        }

    v = _verdict(p, eta_sq)
    return {
        "variable": var,
        "type": "continuous",
        "test": "Kruskal-Wallis",
        "statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "effect_size": round(float(eta_sq), 4),
        "effect_ci_low": ci_lo,
        "effect_ci_high": ci_hi,
        "effect_measure": "eta-squared",
        "verdict": v,
        "mitigation": _mitigation(var, v),
        "descriptives": descriptives,
    }


def _analyse_categorical(df: pd.DataFrame, var: str, groups: dict[str, list[str]],
                         group_col: str) -> dict | None:
    """Chi-square or Fisher's exact test for a categorical variable, with CI."""
    data_groups = []
    labels = []
    for gname, subjects in groups.items():
        vals = df[df[group_col].isin(subjects)][var].dropna()
        if len(vals) < 3:
            return None
        data_groups.append(vals.values.astype(float))
        labels.append(gname)

    if len(data_groups) < 2:
        return None

    all_levels = sorted({int(v) for g in data_groups for v in g})
    table = np.array([
        [int(np.sum(g == level)) for level in all_levels] for g in data_groups
    ], dtype=float)

    row_sums = table.sum(axis=1)
    col_sums = table.sum(axis=0)
    total = table.sum()
    expected = np.outer(row_sums, col_sums) / total if total else np.zeros_like(table)
    min_expected = expected[expected > 0].min() if (expected > 0).any() else 0.0

    if min_expected < 5 or table.size < 20:
        if table.shape == (2, 2):
            _, p = stats.fisher_exact(table.astype(int))
            test_name = "Fisher's exact"
            effect = _rank_biserial_from_table(table)
            effect_measure = "rank-biserial r"
            ci_lo, ci_hi = _bootstrap_categorical_ci(all_levels, data_groups, _rank_biserial_from_table)
        else:
            stat, p, _, _ = stats.chi2_contingency(table, correction=False)
            test_name = "chi-square (low expected counts)"
            effect = np.sqrt(stat / total) if total > 0 else 0.0
            effect_measure = "Cramers V"
            ci_lo, ci_hi = _bootstrap_categorical_ci(all_levels, data_groups, _cramers_v_from_table)
    else:
        stat, p, _, _ = stats.chi2_contingency(table, correction=False)
        test_name = "chi-square"
        effect = np.sqrt(stat / total) if total > 0 else 0.0
        effect_measure = "Cramers V"
        ci_lo, ci_hi = _bootstrap_categorical_ci(all_levels, data_groups, _cramers_v_from_table)

    descriptives = {}
    for gname, g in zip(labels, data_groups):
        counts = {int(level): int(np.sum(g == level)) for level in all_levels}
        total_g = sum(counts.values())
        descriptives[gname] = {str(k): {"count": v, "pct": round(100 * v / total_g, 1)}
                               for k, v in counts.items()}

    v = _verdict(p, effect)
    return {
        "variable": var,
        "type": "categorical",
        "test": test_name,
        "statistic": None,
        "p_value": round(float(p), 6),
        "effect_size": round(float(effect), 4),
        "effect_ci_low": ci_lo,
        "effect_ci_high": ci_hi,
        "effect_measure": effect_measure,
        "verdict": v,
        "mitigation": _mitigation(var, v),
        "descriptives": descriptives,
    }


def _analyse_education_trend(df: pd.DataFrame, education_col: str,
                             groups: dict[str, list[str]], group_col: str) -> dict | None:
    """Monotone trend of education (3-level ordinal) across groups (Task 8).

    Spearman correlation between education level and an ordinal group code
    (N=0, A_P_minus=1, A_P_plus=2) — reported alongside the categorical test.
    """
    group_order = {"N": 0, "A_P_minus": 1, "A_P_plus": 2}
    pairs = []
    for gname, subjects in groups.items():
        code = group_order.get(gname)
        if code is None:
            continue
        vals = df[df[group_col].isin(subjects)][education_col].dropna()
        for v in vals:
            pairs.append((code, float(v)))
    if len(pairs) < 10:
        return None
    codes, educ = zip(*pairs)
    rho, p = stats.spearmanr(codes, educ)
    return {
        "variable": education_col,
        "type": "ordinal-trend",
        "test": "Spearman (education × group order)",
        "statistic": round(float(rho), 4),
        "p_value": round(float(p), 6),
        "effect_size": round(float(rho), 4),
        "effect_ci_low": None,
        "effect_ci_high": None,
        "effect_measure": "Spearman rho",
        "verdict": _verdict(p, abs(rho)),
        "mitigation": _mitigation(education_col, _verdict(p, abs(rho))),
        "descriptives": {},
    }


def _bh_fdr(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR-corrected q-values (Task 8)."""
    n = len(p_values)
    if n == 0:
        return []
    order = np.argsort(p_values)
    ranked = np.array(p_values)[order]
    q = np.full(n, np.nan)
    running = 1.0
    for i in range(n - 1, -1, -1):
        running = min(running, ranked[i] * n / (i + 1))
        q[i] = running
    q_by_orig = np.empty(n)
    q_by_orig[order] = q
    return [round(float(x), 4) for x in q_by_orig]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run() -> dict:
    """Execute the full confound analysis (§7 + Task 8)."""
    df = _load_participants()
    groups = _load_groups()
    cohort = _load_cohort()
    col_map = _get_col_mapping()

    # Strictly resolve the subject column (Task 3a — no guessing)
    subj_col = _resolve_column("subject_id", col_map)
    if subj_col not in df.columns:
        raise ValueError(f"Resolved subject column {subj_col!r} not in participants.tsv")
    df["_subject_id"] = df[subj_col].apply(_normalise_subj_id)

    # Restrict to the analysis cohort (Task 2) and assert the row count.
    analysis_subjects = set(cohort.loc[cohort["final_include"], "subject"])
    df = df[df["_subject_id"].isin(analysis_subjects)].copy()
    assert len(df) == len(analysis_subjects), (
        f"Confound input has {len(df)} rows but analysis cohort has {len(analysis_subjects)}"
    )

    # Resolve candidate confound columns strictly from config (Task 3a/8).
    # The screen-variable list is persisted by fetch_metadata; guessing here
    # would silently change the screen between runs.
    screen = load_audit_yaml().get("screen_variables", {})
    if not screen.get("continuous") and not screen.get("categorical"):
        raise ValueError(
            "config/audit.yaml has no screen_variables record. Run fetch_metadata "
            "first; refusing to guess the confound screen."
        )

    continuous_vars = [c for c in screen.get("continuous", []) if c in df.columns]
    categorical_vars = [c for c in screen.get("categorical", []) if c in df.columns]

    education_col = col_map.get("education")

    # Three target framings
    targets = {
        "multiclass_3": groups,
        "binary_risk_vs_none": {
            "no_risk": groups.get("N", []),
            "risk": groups.get("A_P_minus", []) + groups.get("A_P_plus", []),
        },
        "binary_high_vs_rest": {
            "rest": groups.get("N", []) + groups.get("A_P_minus", []),
            "high": groups.get("A_P_plus", []),
        },
    }

    all_results = {}
    for framing_name, framing_groups in targets.items():
        results = []
        for var in continuous_vars:
            r = _analyse_continuous(df, var, framing_groups, "_subject_id")
            if r:
                r["framing"] = framing_name
                results.append(r)
        for var in categorical_vars:
            r = _analyse_categorical(df, var, framing_groups, "_subject_id")
            if r:
                r["framing"] = framing_name
                results.append(r)
            # Education also gets a monotone-trend test (Task 8)
            if education_col and var == education_col:
                t = _analyse_education_trend(df, var, framing_groups, "_subject_id")
                if t:
                    t["framing"] = framing_name
                    results.append(t)

        # FDR correction across the screen within this framing
        ps = [r["p_value"] for r in results if r["p_value"] is not None]
        qs = _bh_fdr(ps)
        q_iter = iter(qs)
        for r in results:
            if r["p_value"] is not None:
                r["fdr_q"] = next(q_iter)

        all_results[framing_name] = results

    # Write CSV
    csv_path = artifact_dir() / "confound_report.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    flat_rows = []
    for framing, results in all_results.items():
        for r in results:
            row = {k: v for k, v in r.items() if k != "descriptives"}
            flat_rows.append(row)

    if flat_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=flat_rows[0].keys())
            writer.writeheader()
            writer.writerows(flat_rows)

    summary = {
        "continuous_vars_tested": continuous_vars,
        "categorical_vars_tested": categorical_vars,
        "framing_results": all_results,
        "n_subjects_analysed": len(df),
        "csv_path": str(csv_path),
    }

    return summary


def _normalise_subj_id(val) -> str:
    """Normalise a subject ID to sub-XX format."""
    s = str(val).strip()
    if s.startswith("sub-"):
        return s
    try:
        num = int(s)
        return f"sub-{num:02d}"
    except ValueError:
        pass
    import re
    m = re.search(r"(\d+)", s)
    if m:
        return f"sub-{int(m.group(1)):02d}"
    return s
