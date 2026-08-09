"""THE GATE (phase_2.md §1) — preprocessing metadata must not predict group.

Sanctioned exception to pearl_features label blindness: this module reads
group labels (data/labels/participants_labels.tsv) to test whether
preprocessing/QC metrics carry group information. It never writes labels into
any feature file and nothing downstream of pearl_features.features imports
this module.
"""
from __future__ import annotations

import csv

import numpy as np
import pandas as pd
from scipy import stats

from pearl_preproc.paths import PROJECT_ROOT

LABELS_TSV = PROJECT_ROOT.parent / "data" / "labels" / "participants_labels.tsv"

CONTINUOUS_METRICS = [
    "n_bad_channels", "occipital_bads", "n_ica_removed",
    "line_noise_index_before", "line_noise_index_after",
    "artifact_frac", "iaf_hz", "alpha_peak_height_db",
]


def load_group_map() -> dict[str, str]:
    with open(LABELS_TSV, newline="", encoding="utf-8") as fh:
        return {row["subject_id"]: row["group"] for row in csv.DictReader(fh, delimiter="\t")}


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR, ascending-order accumulate-min-from-the-top."""
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(ranked, 0, 1)
    return out


def _bootstrap_eta_squared_ci(groups: list[np.ndarray], n_boot: int = 2000,
                               seed: int = 0) -> tuple[float, float, float]:
    """Bootstrap CI on eta-squared (KW effect size) by resampling within each group."""
    rng = np.random.default_rng(seed)

    def eta_sq(gs):
        all_vals = np.concatenate(gs)
        h_stat, _ = stats.kruskal(*gs)
        n = len(all_vals)
        k = len(gs)
        return max(0.0, (h_stat - k + 1) / (n - k)) if n > k else 0.0

    point = eta_sq(groups)
    boots = []
    for _ in range(n_boot):
        resampled = [rng.choice(g, size=len(g), replace=True) for g in groups]
        boots.append(eta_sq(resampled))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, lo, hi


def association_tests(qc: pd.DataFrame, group_map: dict[str, str],
                       metrics: list[str]) -> pd.DataFrame:
    qc = qc.copy()
    qc["group"] = qc["subject"].map(group_map)
    rows = []
    pvals = []
    for metric in metrics:
        groups = [qc.loc[qc["group"] == g, metric].dropna().to_numpy(dtype=float)
                   for g in sorted(qc["group"].dropna().unique())]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            rows.append({"metric": metric, "test": "kruskal-wallis", "statistic": np.nan,
                          "p_value": 1.0, "effect_size": 0.0, "ci_low": 0.0, "ci_high": 0.0})
            pvals.append(1.0)
            continue
        h_stat, p = stats.kruskal(*groups)
        eff, lo, hi = _bootstrap_eta_squared_ci(groups)
        rows.append({"metric": metric, "test": "kruskal-wallis", "statistic": h_stat,
                      "p_value": p, "effect_size": eff, "ci_low": lo, "ci_high": hi})
        pvals.append(p)
    out = pd.DataFrame(rows)
    out["p_fdr"] = _bh_fdr(out["p_value"].to_numpy())
    return out[["metric", "test", "statistic", "p_value", "p_fdr", "effect_size", "ci_low", "ci_high"]]


def exclusion_status_association(per_task: pd.DataFrame, group_map: dict[str, str]) -> dict:
    df = per_task.copy()
    df["group"] = df["subject"].map(group_map)
    df = df.dropna(subset=["group"])
    table = pd.crosstab(df["group"] == "N", df["included"])
    table = table.reindex(columns=[True, False], fill_value=0)
    odds_ratio, p = stats.fisher_exact(table.to_numpy())
    return {"odds_ratio": float(odds_ratio), "p_value": float(p)}
