"""Phase 6 Stage A (plan: sparkling-launching-torvalds.md).

Runs the sex control (pearl_models.positive_controls.run_sex_control, reused
unchanged -- it already takes the feature frame as an argument, so it
generalizes to any representation) against four already-existing
representations of the frozen 64-subject rest cohort, on the current
corrected preprocessing. This adds ZERO new genotype looks: it only touches
control targets (sex) and reports one already-published genotype number
(baseline_rest, from reports/phase5_stage3_results.md Section 5) alongside
them for comparison. Age is reported descriptively only, per the plan --
this cohort spans just 50-63 years, too narrow to support an age control
(published EEG brain-age MAE ~7 years exceeds the cohort's own range).

Run from `pearl/`: PYTHONPATH=src python scripts/phase6_control_matrix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pearl_models.data import load_baseline_features, load_pswt_features, load_nuisance
from pearl_models.paths import CONFIG_DIR, REPORTS_DIR, make_run_id, git_sha
from pearl_models.positive_controls import run_sex_control

# Already-published genotype number this script never re-derives or re-runs --
# reports/phase5_stage3_results.md Section 5, "baseline_rest" row.
GENOTYPE_BASELINE_REST_AUC = 0.506
GENOTYPE_BASELINE_REST_P = 0.4815

# Phase 4 rung 1, for comparison (old, bug-present preprocessing) --
# reports/phase4_control_diagnostic.md.
PHASE4_RUNG1_AUC = 0.693
PHASE4_RUNG1_P = 0.0130
PHASE4_PSWT_SEX_AUC = 0.465


def fmt_ci(ci) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def main() -> None:
    cfg = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    nuisance = load_nuisance()

    baseline = load_baseline_features()
    rest_cols = [c for c in baseline.columns if not c.startswith(("msit_", "sternberg_"))]
    msit_cols = [c for c in baseline.columns if c.startswith("msit_")]

    representations = {
        # 9 rest-only columns -- matches the genotype comparison exactly.
        "baseline_rest": baseline[rest_cols],
        # 16 columns (9 rest + 7 msit) -- faithful match to Phase 4 rung 1.
        "baseline_rest_msit": baseline[rest_cols + msit_cols],
        # full current baseline family (23 cols, adds Sternberg).
        "baseline_all": baseline,
        # PSWT -- re-confirm the 0.465 failure on the same footing.
        "pswt": load_pswt_features(),
    }

    # Incremental/resumable, matching this project's pipeline convention: each
    # representation is a full-precision run (1000 permutations + 2000
    # bootstrap) taking ~10-20 min, and this environment has repeatedly killed
    # long background jobs mid-run. Partial results are written after every
    # representation and re-used on restart, so an interrupted run resumes
    # rather than restarting.
    partial_path = REPORTS_DIR / "phase6_control_matrix_partial.json"
    results = {}
    if partial_path.exists():
        cached = json.loads(partial_path.read_text(encoding="utf-8"))
        results = {k: v for k, v in cached.items()}
        print(f"resuming: {len(results)} representation(s) already done "
              f"({', '.join(results)})", flush=True)

    for name, feats in representations.items():
        if name in results:
            print(f"{name}: SKIP (already computed)", flush=True)
            continue
        print(f"{name}: starting (n_features={feats.shape[1]}) ...", flush=True)
        r = run_sex_control(cfg, feats, nuisance)
        results[name] = {"n_features": int(feats.shape[1]),
                          "n_subjects_used": int(r["n_subjects_used"]),
                          "auc": float(r["auc"]), "ci": [float(c) for c in r["ci"]],
                          "p_value": float(r["p_value"]), "verdict": r["verdict"]}
        partial_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: n_features={feats.shape[1]} n={r['n_subjects_used']} "
              f"auc={r['auc']:.4f} ci={fmt_ci(r['ci'])} p={r['p_value']:.4f} "
              f"verdict={r['verdict']}", flush=True)

    # Age: descriptive only, per plan -- NOT run through the CV harness as a gate.
    cohort = load_pswt_features().index
    age = nuisance.loc[nuisance.index.intersection(cohort), "age"].dropna()
    age_summary = {
        "n": int(len(age)), "min": float(age.min()), "max": float(age.max()),
        "median": float(age.median()), "range_years": float(age.max() - age.min()),
    }
    print(f"age (descriptive only): n={age_summary['n']} "
          f"range=[{age_summary['min']:.0f}, {age_summary['max']:.0f}] "
          f"median={age_summary['median']:.0f}")

    out_dir = REPORTS_DIR
    summary_path = out_dir / "phase6_control_matrix.json"
    summary_path.write_text(json.dumps({
        "run_id": make_run_id(), "git_sha": git_sha(),
        "representations": results,
        "age_descriptive": age_summary,
        "genotype_baseline_rest_reference": {
            "auc": GENOTYPE_BASELINE_REST_AUC, "p_value": GENOTYPE_BASELINE_REST_P,
            "source": "reports/phase5_stage3_results.md Section 5 (already published, not re-run)",
        },
        "phase4_reference": {
            "rung1_baseline_rest_msit_auc": PHASE4_RUNG1_AUC, "rung1_p": PHASE4_RUNG1_P,
            "pswt_sex_auc": PHASE4_PSWT_SEX_AUC,
            "source": "reports/phase4_control_diagnostic.md (old, bug-present preprocessing)",
        },
    }, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE {summary_path}")
    print("DONE")


if __name__ == "__main__":
    main()
