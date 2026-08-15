"""Verdict-first Markdown report for THE GATE (phase_2.md §1)."""
from __future__ import annotations

import pandas as pd
from pearl_preproc.paths import guarded_write

_VERDICT_TEXT = {
    "proceed": "PROCEED — preprocessing carries no detectable group information.",
    "proceed_with_baseline": (
        "PROCEED WITH BASELINE REQUIREMENT — partial contamination detected. "
        "Every downstream EEG feature model must be reported alongside this "
        "QC-only baseline; improvement over it is the only claim that may be made."),
    "escalate": (
        "STOP AND ESCALATE — preprocessing predicts group about as well as "
        "published EEG features do. Option C (reference-order / ICA-rate "
        "confound investigation) becomes mandatory before any feature is trusted."),
}


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def render(full_assoc: pd.DataFrame, surviving_assoc: pd.DataFrame,
           exclusion_assoc: dict, gate_result: dict) -> str:
    verdict = gate_result["verdict"]
    lines = [
        f"# Phase 2 Confound Gate — VERDICT: {verdict.upper()}",
        "",
        _VERDICT_TEXT[verdict],
        "",
        "## §1b — QC-only classifier (the decisive test)",
        "",
        f"- Mean AUC (subject-level stratified group k-fold, nested, permutation-tested): "
        f"**{gate_result['mean_auc']:.3f}**",
        f"- 95% bootstrap CI: [{gate_result['ci_low']:.3f}, {gate_result['ci_high']:.3f}]",
        f"- Permutation p-value: {gate_result['p_value']:.4f}",
        "",
        "## §1a — Association tests, full cohort (N=79)",
        "",
        _table(full_assoc),
        "",
        "## §1a — Association tests, surviving cohort (per-task rule)",
        "",
        _table(surviving_assoc),
        "",
        "## §1a — Exclusion status × group (Fisher's exact)",
        "",
        f"- Odds ratio: {exclusion_assoc['odds_ratio']:.3f}",
        f"- p-value: {exclusion_assoc['p_value']:.4f}",
        "",
        "## §1c — Carry-forward covariates",
        "",
        "Bad-channel count and ICA-components-removed join SES and BDI as "
        "declared Phase 3 covariates, regardless of this verdict "
        "(see Amendment 1, `reports/analysis_plan_frozen.md`).",
        "",
    ]
    return "\n".join(lines)


def run() -> dict:
    """Orchestrates the full §1 gate and writes reports/phase2_confound_gate.md."""
    from pearl_features.cohort import load_qc_metrics, per_task_cohort
    from pearl_features.paths import REPORTS_DIR
    from pearl_features.confound_gate import (
        association_tests, exclusion_status_association, qc_only_auc,
        load_group_map, CONTINUOUS_METRICS,
    )

    qc = load_qc_metrics()
    per_task = per_task_cohort(qc)
    group_map = load_group_map()

    full_assoc = association_tests(qc, group_map, CONTINUOUS_METRICS)
    surviving = qc.merge(per_task[per_task["included"]][["subject", "task"]],
                          on=["subject", "task"], how="inner")
    surviving_assoc = association_tests(surviving, group_map, CONTINUOUS_METRICS)
    exclusion_assoc = exclusion_status_association(per_task, group_map)

    binary_map = {s: (0 if g == "N" else 1) for s, g in group_map.items()}
    rest_qc = qc[qc["task"].isin(["rest", "task-rest"])].drop_duplicates(subset="subject")
    gate_result = qc_only_auc(rest_qc, binary_map, CONTINUOUS_METRICS)

    text = render(full_assoc, surviving_assoc, exclusion_assoc, gate_result)
    guarded_write(REPORTS_DIR / "phase2_confound_gate.md", text, allow_overwrite=True)
    return gate_result
