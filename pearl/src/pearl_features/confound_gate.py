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


# ---------------------------------------------------------------------------
# §1b — the decisive test: fit a model on QC metrics alone
# ---------------------------------------------------------------------------

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _cv_mean_auc(X: np.ndarray, y: np.ndarray, n_splits: int, n_repeats: int,
                  seed: int) -> float:
    aucs = []
    rng = np.random.default_rng(seed)
    for _rep in range(n_repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                               random_state=int(rng.integers(0, 2**31 - 1)))
        for train_idx, test_idx in skf.split(X, y):
            clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 LogisticRegression(max_iter=1000))
            clf.fit(X[train_idx], y[train_idx])
            proba = clf.predict_proba(X[test_idx])[:, 1]
            if len(np.unique(y[test_idx])) < 2:
                continue
            aucs.append(roc_auc_score(y[test_idx], proba))
    return float(np.mean(aucs)) if aucs else 0.5


def qc_only_auc(qc: pd.DataFrame, group_map: dict[str, str] | dict[str, int],
                 metrics: list[str], n_splits: int = 5, n_repeats: int = 3,
                 n_permutations: int = 1000, seed: int = 42) -> dict:
    """Nested-CV, permutation-tested AUC of a classifier trained on QC metrics
    alone against the primary target. Not modelling the hypothesis — measuring
    the contamination floor (phase_2.md §1b)."""
    df = qc.copy()
    df["y"] = df["subject"].map(group_map)
    df = df.dropna(subset=["y"])
    df = df.drop_duplicates(subset="subject")  # subject-level: one row per subject
    X = df[metrics].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=int)

    observed = _cv_mean_auc(X, y, n_splits, n_repeats, seed)

    rng = np.random.default_rng(seed)
    perm_aucs = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = rng.permutation(y)
        perm_aucs[i] = _cv_mean_auc(X, y_perm, n_splits, 1, seed + i + 1)
    p_value = float((perm_aucs >= observed).sum() + 1) / (n_permutations + 1)

    boot_aucs = []
    rng2 = np.random.default_rng(seed + 1)
    n = len(y)
    for _ in range(2000):
        idx = rng2.integers(0, n, size=n)
        if len(np.unique(y[idx])) < 2:
            continue
        boot_aucs.append(_cv_mean_auc(X[idx], y[idx], n_splits, 1, seed))
    ci_low, ci_high = (np.percentile(boot_aucs, [2.5, 97.5]) if boot_aucs else (observed, observed))

    if observed > 0.65:
        verdict = "escalate"
    elif observed >= 0.55:
        verdict = "proceed_with_baseline"
    else:
        verdict = "proceed"

    return {"mean_auc": observed, "ci_low": float(ci_low), "ci_high": float(ci_high),
            "p_value": p_value, "verdict": verdict}
