"""Phase 5 Stage 3 validation, Step 1 (plan: sparkling-launching-torvalds.md).

Runs pearl_models.primary.run_primary_analysis(cfg) unchanged against
whatever is currently in data/derivatives/features/features_pswt.csv --
i.e. against one isolated preprocessing condition at a time (reference-order
fix alone, or ICA n_components fix alone). Reduced precision
(200 permutations / 500 bootstrap resamples vs the frozen 1000/2000) via a
cfg override that is NOT written back to config/models.yaml -- this is
attribution diagnostics, not a new headline number (plan's Step 1, explicit
precision decision).

Run from `pearl/`:
  PYTHONPATH=src python scripts/phase5_stage1_isolation_run.py \
      --label reference_order_only \
      --title "Reference-order fix alone" \
      --condition "reference.compute_order=post_interpolation, ica.n_components=30 (ICA fix reverted)" \
      --out reports/phase5_stage1b_reference_order_only.md
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pearl_models.paths import CONFIG_DIR, REPORTS_DIR, make_run_id, git_sha
from pearl_models.primary import run_primary_analysis

ORIGINAL_PHASE3_AUC = 0.474
STAGE3_BOTH_FIXED_AUC = 0.651
STAGE3_BOTH_FIXED_CI = (0.353, 0.764)
STAGE3_BOTH_FIXED_P = 0.0410


def fmt_ci(ci) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--condition", required=True,
                     help="one-line description of what's isolated in this run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-permutations", type=int, default=200)
    ap.add_argument("--n-bootstrap", type=int, default=500)
    args = ap.parse_args()

    cfg = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    cfg["cv"]["n_permutations"] = args.n_permutations
    cfg["cv"]["n_bootstrap"] = args.n_bootstrap

    result = run_primary_analysis(cfg)
    fo = result["features_only"]
    fn = result["features_plus_nuisance"]
    no = result["nuisance_only"]

    n = fo["n_subjects_used"]
    verdict = "POSITIVE" if (fo["auc"] > no["auc"] and fo["p_value"] < 0.05) else "NOT CORROBORATED"

    lines = []
    lines.append(f"# Phase 5 Stage 3 Validation — Step 1: {args.title}")
    lines.append("")
    lines.append("**DIAGNOSTIC PRECISION, NOT DIRECTLY COMPARABLE STATISTICAL RIGOR** to the "
                  f"0.474/0.651 headline numbers below: {args.n_permutations} permutations / "
                  f"{args.n_bootstrap} bootstrap resamples (vs the frozen config's 1000/2000). "
                  "This is attribution diagnostics only -- isolating which of Stage 1's two "
                  "bundled preprocessing fixes drives the Stage 3 result, not a new deliverable "
                  "number. See `docs/` plan `sparkling-launching-torvalds.md` §Step 1.")
    lines.append("")
    lines.append(f"**Isolated condition:** {args.condition}")
    lines.append("")
    lines.append(f"**Cohort:** n={n} (this run's own QC/exclusion outcome under this isolated "
                  "preprocessing condition -- not necessarily identical to Stage 3's 64-subject "
                  "cohort).")
    lines.append("")
    lines.append(f"## Result: {verdict}")
    lines.append("")
    lines.append(f"- PSWT features only: AUC **{fo['auc']:.3f}**, 95% CI {fmt_ci(fo['ci'])}, "
                  f"permutation p={fo['p_value']:.4f}")
    lines.append(f"- PSWT features + nuisance: AUC {fn['auc']:.3f}, 95% CI {fmt_ci(fn['ci'])}, "
                  f"permutation p={fn['p_value']:.4f}")
    lines.append(f"- Nuisance only (this run's reference line): AUC {no['auc']:.3f}, "
                  f"95% CI {fmt_ci(no['ci'])}, permutation p={no['p_value']:.4f}")
    lines.append("")
    lines.append("## Comparison to the other three data points on the same question")
    lines.append("")
    lines.append("| Condition | AUC | 95% CI | p |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Original Phase 3 (bug present, ICA n_components=30) | {ORIGINAL_PHASE3_AUC:.3f} | — | 0.577 |")
    lines.append(f"| Stage 3 (both fixes applied) | {STAGE3_BOTH_FIXED_AUC:.3f} | "
                  f"{fmt_ci(STAGE3_BOTH_FIXED_CI)} | {STAGE3_BOTH_FIXED_P:.4f} |")
    lines.append(f"| **This run — {args.title}** | **{fo['auc']:.3f}** | {fmt_ci(fo['ci'])} | "
                  f"{fo['p_value']:.4f} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if fo['auc'] >= STAGE3_BOTH_FIXED_AUC - 0.03:
        lines.append(f"This isolated condition alone reproduces Stage 3's both-fixed AUC "
                      f"({STAGE3_BOTH_FIXED_AUC:.3f}) to within 0.03 -- consistent with this fix "
                      "being the primary driver of the verdict flip, with the other fix "
                      "contributing little on its own.")
    elif fo['auc'] <= ORIGINAL_PHASE3_AUC + 0.03:
        lines.append(f"This isolated condition alone stays close to the original Phase 3 AUC "
                      f"({ORIGINAL_PHASE3_AUC:.3f}) -- consistent with this fix contributing "
                      "little on its own; the other fix (or their interaction) is the more "
                      "likely driver of Stage 3's both-fixed result.")
    else:
        lines.append("This isolated condition lands between the original and both-fixed AUCs -- "
                      "consistent with a partial, non-dominant contribution from this fix alone; "
                      "the two fixes likely interact rather than one alone explaining the flip.")
    lines.append("")
    lines.append("Per Step 0's finding (`reports/phase5_stage3_stability.md`), the underlying "
                  "0.651 point estimate itself does not reliably clear its own nuisance-only "
                  "comparison under resampling -- attribution here explains *what moved the "
                  "point estimate*, not whether that point estimate is a reliable effect. Read "
                  "this report alongside Step 0, not as a standalone corroboration.")
    lines.append("")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    meta_dir = REPORTS_DIR.parent / "data" / "derivatives" / "models_stage3"
    meta_dir.mkdir(parents=True, exist_ok=True)
    import json
    (meta_dir / f"isolation_{args.label}_meta.json").write_text(json.dumps({
        "run_id": make_run_id(), "git_sha": git_sha(), "label": args.label,
        "condition": args.condition, "n_subjects_used": n,
        "features_only_auc": fo["auc"], "features_only_p": fo["p_value"],
        "n_permutations": args.n_permutations, "n_bootstrap": args.n_bootstrap,
    }, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE {out_path}")
    print(f"features_only: auc={fo['auc']:.4f} ci={fmt_ci(fo['ci'])} p={fo['p_value']:.4f}")
    print(f"nuisance_only: auc={no['auc']:.4f} ci={fmt_ci(no['ci'])} p={no['p_value']:.4f}")
    print("DONE")


if __name__ == "__main__":
    main()
