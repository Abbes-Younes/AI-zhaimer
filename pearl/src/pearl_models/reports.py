"""Markdown/HTML report writers for Phase 3 (phase_3.md §1, §2, §5)."""
from __future__ import annotations

from pathlib import Path


def _interpret_positive_controls(eo_result: dict, sex_result: dict, eo_floor: float,
                                  sex_floor: float) -> tuple[str, str]:
    """phase_3.md §1c interpretation table. Returns (verdict, sentence)."""
    eo_high = eo_result["auc"] >= eo_floor
    sex_high = sex_result["auc"] >= sex_floor

    if not eo_high:
        return ("STOP", ("Positive control 1a (eyes-open vs eyes-closed) came back below "
                          f"the {eo_floor:.2f} floor. The pipeline is not measuring what it "
                          "claims. Do not run or report the primary analysis."))
    if sex_high:
        return ("PROCEED", ("Both controls high: the pipeline works, and a null on genotype "
                             "would be a real null — reportable, valuable."))
    return ("PROCEED_WITH_CAVEAT", (
        "1a high, 1b near chance: the features work (alpha waveform shape is measured "
        "correctly and generalises within subject) but do not generalise across subjects "
        "for a genuinely detectable cross-subject target (sex). Any primary-analysis null "
        "must be reported with this caveat, not as an uncaveated finding about genotype."))


def render_positive_controls(eo_result: dict, sex_result: dict,
                              eo_floor: float = 0.80, sex_floor: float = 0.65) -> str:
    verdict, sentence = _interpret_positive_controls(eo_result, sex_result, eo_floor, sex_floor)
    lines = [
        f"# Phase 3 Positive Controls — VERDICT: {verdict}",
        "",
        sentence,
        "",
        "## §1a — Eyes-open vs eyes-closed (within-subject, strong control)",
        "",
        f"- AUC: **{eo_result['auc']:.3f}** (floor: {eo_floor:.2f})",
        f"- 95% bootstrap CI: [{eo_result['ci'][0]:.3f}, {eo_result['ci'][1]:.3f}]",
        f"- Permutation p-value: {eo_result['p_value']:.4f}",
        f"- Subjects used: {eo_result['n_subjects_used']} (dropped: {eo_result.get('n_dropped', 0)})",
        f"- Verdict: **{eo_result['verdict'].upper()}**",
        "",
        "## §1b — Sex classification (cross-subject, subject-level control)",
        "",
        f"- AUC: **{sex_result['auc']:.3f}** (floor: {sex_floor:.2f})",
        f"- 95% bootstrap CI: [{sex_result['ci'][0]:.3f}, {sex_result['ci'][1]:.3f}]",
        f"- Permutation p-value: {sex_result['p_value']:.4f}",
        f"- Subjects used: {sex_result['n_subjects_used']}",
        f"- Verdict: **{sex_result['verdict'].upper()}**",
        "",
        "## §1c — Interpretation table applied",
        "",
        "| 1a | 1b | Primary null means |",
        "|---|---|---|",
        "| high | ≥ ~0.65 | pipeline works; a null on genotype is a **real null** — reportable, valuable |",
        "| high | ≈ chance | features work but don't generalise across subjects; report the primary null with that caveat |",
        "| low | any | **pipeline is broken.** Stop. Do not run or report the primary analysis |",
        "",
    ]
    return "\n".join(lines)


def write_positive_controls(eo_result: dict, sex_result: dict, out_path: Path,
                             eo_floor: float = 0.80, sex_floor: float = 0.65) -> None:
    text = render_positive_controls(eo_result, sex_result, eo_floor, sex_floor)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
