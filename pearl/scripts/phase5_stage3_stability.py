"""Phase 5 Stage 3 validation, Step 0 (plan: sparkling-launching-torvalds.md).

Characterizes how much the Stage 3 primary AUC (0.651) wobbles under small
perturbations of the 64-subject sample -- leave-k-out and subject-level
bootstrap resampling, reusing pearl_models.cv.pooled_repeated_cv unchanged.
This measures the VARIANCE of an already-computed result; it does not try
any new feature, model, or preprocessing choice, so it does not touch this
project's anti-p-hacking discipline (see plan's Step 0 rationale).

Run from `pearl/`: PYTHONPATH=src python scripts/phase5_stage3_stability.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pearl_models import cv
from pearl_models.data import load_pswt_features, load_labels
from pearl_models.paths import CONFIG_DIR, REPORTS_DIR, make_run_id, git_sha

NUISANCE_ONLY_AUC = 0.5572874493927126  # reports/phase5_stage3_results.md §2
CHANCE = 0.5
LEAVE_K_VALUES = [2, 3, 4, 5, 6, 7, 8]
REPS_PER_K = 25          # -> 175 leave-k-out resamples total
N_BOOTSTRAP = 150
CV_N_REPEATS = 1          # lighter than Stage 3's 10 -- this is a variance
                           # characterization, not the headline estimate itself


def _load_matrix() -> tuple[np.ndarray, np.ndarray, list[str]]:
    pswt = load_pswt_features()
    labels = load_labels().set_index("subject_id")
    joined = pswt.join(labels[["risk_vs_none"]], how="inner")
    feature_cols = list(pswt.columns)
    X = joined[feature_cols].to_numpy(dtype=float)
    y = joined["risk_vs_none"].to_numpy(dtype=int)
    subjects = list(joined.index)
    return X, y, subjects


def _safe_auc(X, y, groups, cfg, seed) -> float | None:
    """`groups` must reflect ORIGINAL subject identity, not row position --
    critical for bootstrap resampling, where the same subject can appear as
    multiple duplicate rows. Passing np.arange(len(y)) there (an earlier
    version of this script did) treats each duplicate as an independent
    "subject", letting the same real subject's rows land in both train and
    test -- a real leakage bug, caught by the bootstrap AUCs (median 0.787)
    being implausibly higher than leave-k-out's (median 0.625, which never
    duplicates and so was never at risk)."""
    if len(np.unique(y)) < 2:
        return None
    # StratifiedGroupKFold needs at least n_splits members per class
    counts = np.bincount(y)
    if counts.min() < cfg["cv"]["n_splits"]:
        return None
    try:
        result = cv.pooled_repeated_cv(X, y, groups, cfg, seed=seed,
                                        n_repeats=CV_N_REPEATS)
        return result["mean_pooled_auc"]
    except Exception:
        return None


def main() -> None:
    t0 = time.time()
    cfg = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    X, y, subjects = _load_matrix()
    n = len(y)
    print(f"loaded {n} subjects ({int((y==1).sum())} at-risk / {int((y==0).sum())} no-risk)")

    rng = np.random.default_rng(20260813)
    rows = []

    # Leave-k-out -- no duplication, so row-position groups are equivalent
    # to subject identity; kept explicit for clarity/consistency with the
    # bootstrap branch below.
    for k in LEAVE_K_VALUES:
        for rep in range(REPS_PER_K):
            drop_idx = rng.choice(n, size=k, replace=False)
            keep_mask = np.ones(n, dtype=bool)
            keep_mask[drop_idx] = False
            groups = np.arange(n)[keep_mask]
            auc = _safe_auc(X[keep_mask], y[keep_mask], groups, cfg,
                             seed=int(rng.integers(0, 2**31 - 1)))
            if auc is not None:
                rows.append({"method": "leave_k_out", "k": k, "n_used": n - k, "auc": auc})

    # Subject-level bootstrap (with replacement, full n). groups=idx (the
    # ORIGINAL subject index each resampled row came from) so
    # StratifiedGroupKFold keeps every duplicate of the same subject in the
    # same fold -- without this, resampled duplicates of one subject could
    # land in both train and test, which is leakage, not signal.
    for rep in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, size=n)
        auc = _safe_auc(X[idx], y[idx], idx, cfg, seed=int(rng.integers(0, 2**31 - 1)))
        if auc is not None:
            rows.append({"method": "bootstrap", "k": 0, "n_used": n, "auc": auc})

    df = pd.DataFrame(rows)
    out_dir = REPORTS_DIR
    df.to_csv(out_dir / "phase5_stage3_stability_resamples.csv", index=False)

    def pct(sub, q):
        return float(np.percentile(sub["auc"], q)) if len(sub) else float("nan")

    summary_rows = []
    for method in ["leave_k_out", "bootstrap"]:
        sub = df[df["method"] == method]
        if not len(sub):
            continue
        frac_above_nuisance = float((sub["auc"] > NUISANCE_ONLY_AUC).mean())
        frac_below_chance = float((sub["auc"] < CHANCE).mean())
        summary_rows.append({
            "method": method, "n_resamples": len(sub),
            "p5": pct(sub, 5), "p50": pct(sub, 50), "p95": pct(sub, 95),
            "frac_above_nuisance_only": frac_above_nuisance,
            "frac_below_chance": frac_below_chance,
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_dir / "phase5_stage3_stability_summary.csv", index=False)

    elapsed = time.time() - t0
    print(summary.to_string(index=False))
    print(f"took {elapsed:.1f}s")

    meta_dir = out_dir.parent / "data" / "derivatives" / "models_stage3"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "stability_meta.json").write_text(json.dumps({
        "run_id": make_run_id(), "git_sha": git_sha(),
        "n_resamples_total": len(df), "elapsed_s": elapsed,
        "cv_n_repeats_per_resample": CV_N_REPEATS,
    }, indent=2) + "\n", encoding="utf-8")

    print("DONE")


if __name__ == "__main__":
    main()
