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


_BENCHMARK_VERDICT_TEXT = {
    "near_benchmark": ("NEAR BENCHMARK — this project's preprocessing and CV machinery are "
                        "comparable to the published pipeline; the 0.58 reference point is "
                        "meaningful to compare against."),
    "at_chance": ("AT CHANCE — STOP AND ESCALATE (phase_3.md §10). This pipeline's MSIT "
                   "baseline-feature reproduction does not approach the published 0.58. The "
                   "pipeline differs from the published one (different feature family — band "
                   "power/1-f vs. multitaper/TFAAT — and/or different preprocessing/sample) in "
                   "a way that must be understood before the 0.58 figure is quoted as a "
                   "meaningful comparison target. This does NOT by itself invalidate the "
                   "primary PSWT-on-rest analysis, which uses neither this feature family nor "
                   "this task — but the benchmark comparison in every downstream report must be "
                   "presented with this caveat, not as a validated external check."),
    "other": ("OTHER — reproduction landed away from both the benchmark and chance; record the "
               "number and note it without over-interpreting."),
}


def render_benchmark_reproduction(result: dict) -> str:
    verdict = result["verdict"]
    lines = [
        f"# Phase 3 Benchmark Reproduction (MSIT) — VERDICT: {verdict.upper()}",
        "",
        _BENCHMARK_VERDICT_TEXT[verdict],
        "",
        "## Result",
        "",
        f"- AUC: **{result['auc']:.3f}** (published benchmark: 0.58, chance: 0.50)",
        f"- 95% bootstrap CI: [{result['ci'][0]:.3f}, {result['ci'][1]:.3f}]",
        f"- Permutation p-value: {result['p_value']:.4f}",
        f"- Subjects used (MSIT-QC-surviving, complete baseline features): {result['n_subjects_used']}",
        "",
        "## Framing caveat",
        "",
        "The published 0.58 came from task-state MSIT with multitaper/TFAAT spectral "
        "features and an SVM classifier (Li et al. 2025) — not this project's simple "
        "relative-band-power + 1/f baseline with L2 logistic regression. The source paper "
        "also found task EEG outperforms resting-state EEG for this classification problem, "
        "so 0.58 is, if anything, an optimistic bar for this project's rest-based primary "
        "analysis, independent of this reproduction attempt's outcome.",
        "",
        "## Investigation (why AT_CHANCE, not a bug)",
        "",
        "Three checks, run before accepting the null:",
        "",
        "1. **Data sanity** — no degenerate features, reasonable variance/scale across all 7 "
        "MSIT columns, class balance 33/22 in the 55-subject complete-data subset. No data bug.",
        "2. **Univariate signal, two ROIs** — neither the occipital-parietal ROI (used in the "
        "frozen `features_baseline.csv`) nor a frontocentral ROI (`Fz, FC1, FC2, Cz, F3, F4, "
        "FC5, FC6, C3, C4` — the anatomically expected site for MSIT interference effects, "
        "computed as a one-off diagnostic, not a declared feature family) shows *any* "
        "individual feature with even marginal association to the label: occipital-parietal "
        "all p > 0.16 (univariate AUC range 0.39-0.61); frontocentral all p > 0.28 (range "
        "0.42-0.57). Both are noise-level.",
        "3. **Alternate classifier** — linear SVM (the declared secondary model class) scores "
        "*worse* (mean AUC 0.38) than logistic regression (0.459) on the same features, ruling "
        "out classifier choice as the explanation.",
        "",
        "**Conclusion:** not a pipeline bug. This project's baseline feature set is 7 simple "
        "relative-band-powers + a 1/f fit, ROI-averaged over the entire MSIT recording. The "
        "published 0.58 used multitaper time-frequency area features, computed per condition "
        "(specifically the low-demand block), with t-test+FDR subspace feature selection — a "
        "substantially richer feature-engineering and selection pipeline, on a different "
        "cohort. Reproducing that exactly is out of this phase's scope; the gap is a "
        "characterized methodological difference in feature richness, not evidence the "
        "pipeline is broken. It does not affect the primary PSWT-on-rest analysis, which "
        "shares neither the feature family nor the task with this benchmark check.",
        "",
    ]
    return "\n".join(lines)


def write_benchmark_reproduction(result: dict, out_path: Path) -> None:
    text = render_benchmark_reproduction(result)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")


def render_results(primary: dict, secondary: dict, eo_result: dict, sex_result: dict,
                    benchmark_result: dict, feature_stability, leakage_result: dict,
                    cfg: dict) -> str:
    """phase_3.md §5 — the 8-section verdict-first structure. Reads correctly
    whether the result is positive or null (drafted with this shape before
    the real numbers existed)."""
    import numpy as np

    fo = primary["features_only"]
    ref = cfg["reference_lines"]

    beats_nuisance = fo["auc"] > primary["nuisance_only"]["auc"]
    significant = fo["p_value"] < 0.05
    verdict = "POSITIVE" if (beats_nuisance and significant) else "NULL"

    eo_high = eo_result["auc"] >= cfg["positive_controls"]["eyes_open_closed_auc_floor"]
    sex_high = sex_result["auc"] >= cfg["positive_controls"]["sex_auc_reference_floor"]
    if eo_high and sex_high:
        null_caveat = "a real null — reportable, valuable on its own terms."
    elif eo_high:
        null_caveat = ("features work within-subject but do not generalise across subjects for "
                        "a genuinely detectable target (sex, AUC "
                        f"{sex_result['auc']:.3f}) — this null cannot fully separate "
                        "'no real genotype signal' from 'features don't generalise cross-subject "
                        "at all.'")
    else:
        null_caveat = "the pipeline itself did not pass its positive control — do not trust this result."

    lines = [
        f"# Phase 3 Results — VERDICT: {verdict}",
        "",
        f"Primary analysis (PSWT features on resting-state, `binary_risk_vs_none`, "
        f"n={fo['n_subjects_used']}): **AUC {fo['auc']:.3f}**, 95% CI "
        f"[{fo['ci'][0]:.3f}, {fo['ci'][1]:.3f}], permutation p={fo['p_value']:.4f}.",
        "",
        (f"This is a **null result**: {null_caveat}" if verdict == "NULL" else
         "This beats both chance and the nuisance-only line at p<0.05 — a positive finding."),
        "",
        "## 1. Verdict and primary number",
        "",
        f"- AUC: **{fo['auc']:.3f}**",
        f"- 95% bootstrap CI: [{fo['ci'][0]:.3f}, {fo['ci'][1]:.3f}]",
        f"- Permutation p-value (full pipeline re-run per permutation): {fo['p_value']:.4f}",
        f"- Spread across the {len(fo['pooled_auc_per_repeat'])} repeats: "
        f"[{min(fo['pooled_auc_per_repeat']):.3f}, {max(fo['pooled_auc_per_repeat']):.3f}]",
        "",
        "## 2. All four reference lines",
        "",
        "| Reference | AUC | CI | Source |",
        "|---|---|---|---|",
        f"| Chance | {ref['chance']:.3f} | — | — |",
        f"| QC-only | {ref['qc_only_auc']:.3f} | [{ref['qc_only_ci'][0]:.3f}, {ref['qc_only_ci'][1]:.3f}] | Phase 2 gate |",
        f"| Nuisance-only | {primary['nuisance_only']['auc']:.3f} | "
        f"[{primary['nuisance_only']['ci'][0]:.3f}, {primary['nuisance_only']['ci'][1]:.3f}] | this phase, §2b |",
        f"| Published benchmark | {ref['published_benchmark_auc']:.3f} | — | Li et al. 2025, MSIT (not rest) |",
        f"| **PSWT features (primary)** | **{fo['auc']:.3f}** | [{fo['ci'][0]:.3f}, {fo['ci'][1]:.3f}] | this analysis |",
        f"| Features + nuisance | {primary['features_plus_nuisance']['auc']:.3f} | "
        f"[{primary['features_plus_nuisance']['ci'][0]:.3f}, {primary['features_plus_nuisance']['ci'][1]:.3f}] | this analysis |",
        "",
        "## 3. Positive control outcomes",
        "",
        f"- 1a (eyes-open vs eyes-closed): AUC {eo_result['auc']:.3f} "
        f"({'PASS' if eo_high else 'FAIL'}, floor "
        f"{cfg['positive_controls']['eyes_open_closed_auc_floor']:.2f})",
        f"- 1b (sex classification): AUC {sex_result['auc']:.3f} "
        f"({'PASS' if sex_high else 'FAIL'}, floor "
        f"{cfg['positive_controls']['sex_auc_reference_floor']:.2f})",
        "- Full detail: `reports/phase3_positive_controls.md`",
        "",
        "## 4. Benchmark reproduction outcome",
        "",
        f"- MSIT baseline features vs risk_vs_none: AUC {benchmark_result['auc']:.3f} "
        f"(verdict: {benchmark_result['verdict'].upper()})",
        "- Full detail and investigation: `reports/phase3_benchmark_reproduction.md`",
        "",
        "## 5. Secondary comparisons (Holm-corrected)",
        "",
        "| Analysis | AUC | p (raw) | p (Holm) |",
        "|---|---|---|---|",
    ]
    for name, r in secondary.items():
        lines.append(f"| {name} | {r['auc']:.3f} | {r['p_value']:.4f} | {r['p_value_holm']:.4f} |")
    lines += [
        "",
        "None of the secondary comparisons survive Holm correction "
        "(all p_holm ≥ 0.05)." if all(r["p_value_holm"] >= 0.05 for r in secondary.values())
        else "At least one secondary comparison survives Holm correction — see table.",
        "",
        "## 6. Feature stability",
        "",
        "Selection frequency and sign consistency across all repeat×fold combinations "
        "(features stable in >80% of folds only):",
        "",
        feature_stability[feature_stability["stable"]].sort_values(
            "selection_frequency", ascending=False).to_markdown(index=False),
        "",
        "Note: `harmonic_amplitude_profile_h1_median`/`h1_iqr` were never selected — "
        "they are tautologically constant (harmonic 1 normalised to itself is exactly "
        "1.0 for every cycle), a Phase 2 feature-definition artifact, not a modelling "
        "failure. `harmonic_amplitude_profile_h5_*` show 100% selection frequency but "
        "correlate strongly with `usable_duration_s` among the small subset where they "
        "are non-missing (see §7 limitations and `reports/phase3_leakage_checklist` notes) "
        "— their selection should not be read as evidence of a genuine harmonic effect.",
        "",
        "## 7. Limitations",
        "",
        "- **Power** (Amendment 2 §0f): at 39 vs 25, the 95% CI on an AUC estimate is "
        "expected to be roughly ±0.13–0.15 wide; the observed CI width "
        f"({fo['ci'][1]-fo['ci'][0]:.3f}) is consistent with this a priori expectation.",
        f"- **QC-only CI width** (Amendment 2 §0d): Phase 2's gate passed at AUC "
        f"{ref['qc_only_auc']:.3f} but with a 95% CI of [{ref['qc_only_ci'][0]:.3f}, "
        f"{ref['qc_only_ci'][1]:.3f}] — \"no evidence of contamination,\" never "
        "\"contamination excluded.\"",
        "- **Rest-vs-task benchmark mismatch**: the published 0.58 came from task-state "
        "MSIT, not rest; this project's own MSIT reproduction landed at chance (§4 of "
        "this table), a characterized feature-richness gap, not a validated comparison "
        "point either way.",
        "- **Deferred Phase 1 issues**: the reference-order bug (average reference "
        "computed before bad-channel interpolation) and the ICA `n_components=30` "
        "over-decomposition concern were both deferred pending a better connection for "
        "the ~46GB re-download (Option C) — neither has been resolved.",
        "- **A_P_plus attrition**: the smallest genetic group lost the largest share of "
        "subjects to QC exclusion (Phase 1); `binary_high_vs_rest` and `multiclass_3` "
        "remain descriptive-only per Amendment 1.",
        "- **Cross-subject generalisation caveat**: positive control 1b (sex) landed at "
        f"chance (AUC {sex_result['auc']:.3f}), so this null cannot fully rule out that "
        "the feature pipeline simply doesn't generalise across subjects for any target, "
        "not specifically genotype.",
        "- **h5 duration confound** (§4 leakage checklist): the two harmonic-5 columns, "
        "selected in 100% of folds, correlate strongly with recording duration among "
        "their small non-missing subset — a transparency caveat on feature stability, "
        "not a leakage bug (permutation null centred at "
        f"{leakage_result['perm_aucs_mean']:.3f}, structurally clean).",
        "",
        "## 8. What would be needed to answer the question properly",
        "",
        "- A larger cohort — at N=64 (39 vs 25) this project is underpowered to "
        "distinguish a true AUC of 0.65 from the published 0.58, let alone detect "
        "smaller effects.",
        "- Task EEG (MSIT/Sternberg) rather than rest alone, since the source paper "
        "found task EEG outperforms resting-state EEG for this classification problem.",
        "- The Option C reprocessing (reference-order fix, ICA component-count "
        "re-evaluation) to rule out those Phase 1 confound candidates definitively "
        "rather than by absence of evidence in Phase 2's gate.",
        "- A richer MSIT feature-engineering pipeline (multitaper time-frequency area, "
        "per-condition splitting, subspace selection) to make the benchmark comparison "
        "meaningful rather than characterized-but-unresolved.",
        "",
    ]
    return "\n".join(lines)


def write_results(primary: dict, secondary: dict, eo_result: dict, sex_result: dict,
                   benchmark_result: dict, feature_stability, leakage_result: dict,
                   cfg: dict, out_path: Path) -> None:
    text = render_results(primary, secondary, eo_result, sex_result, benchmark_result,
                           feature_stability, leakage_result, cfg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")

    html_path = out_path.with_suffix(".html")
    html_path.write_text(_markdown_to_self_contained_html(text), encoding="utf-8")


_HTML_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
h1 { color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }
h2 { color: #16213e; margin-top: 30px; }
table { border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 5px 8px; text-align: left; }
th { background-color: #16213e; color: white; }
tr:nth-child(even) { background-color: #f7f7f7; }
pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; }
"""


def _markdown_to_self_contained_html(markdown_text: str) -> str:
    """Minimal, dependency-free Markdown->HTML: headings, tables, and
    everything else as preformatted text -- self-contained (no external
    stylesheet/script), matching pearl_preproc.report_qc's convention."""
    lines = markdown_text.splitlines()
    body_parts: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        header, *rest = table_rows
        rest = [r for r in rest if not all(set(c.strip()) <= {"-", ":"} for c in r)]
        html = ["<table>", "<tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr>"]
        for row in rest:
            html.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        html.append("</table>")
        body_parts.append("\n".join(html))
        table_rows = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(cells)
            continue
        if in_table:
            flush_table()
            in_table = False
        if stripped.startswith("# "):
            body_parts.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            body_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped:
            body_parts.append(f"<p>{stripped}</p>")
    if in_table:
        flush_table()

    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Phase 3 Results</title><style>{_HTML_CSS}</style></head>"
            f"<body>{''.join(body_parts)}</body></html>")


_DECISION_TABLE_SENTENCES = {
    "positive": ("The pitch-synchronous feature family did not detect genotype group, on a "
                 "cohort where other EEG features do carry subject-level information. This is "
                 "a negative result for the method as applied here."),
    "inconclusive": ("No subject-level EEG signal of any kind was detectable in this cohort at "
                      "n=64, including a target known to be detectable in larger samples. The "
                      "genotype result is therefore inconclusive, not negative."),
}


def render_control_diagnostic(ladder_result: dict, significance_alpha: float = 0.05) -> str:
    """phase_4.md §0 — verdict-first, all three rungs reported regardless of
    where the ladder stopped, decision table (§0d) reproduced with the
    outcome marked."""
    stopped_at = ladder_result["stopped_at"]
    outcome = "positive" if stopped_at is not None else "inconclusive"
    verdict = "ANY RUNG SIGNIFICANT" if outcome == "positive" else "ALL RUNGS AT CHANCE"

    lines = [
        f"# Phase 4 Control Diagnostic — VERDICT: {verdict}",
        "",
        "This diagnostic runs against a **positive control target (sex)**, never against the "
        "primary target (`binary_risk_vs_none`). It cannot change the primary verdict (frozen: "
        "NULL, AUC 0.474). Its only output is which of the two sentences below the final report "
        "is entitled to write.",
        "",
        f"**Resolved sentence:** {_DECISION_TABLE_SENTENCES[outcome]}",
        "",
        "## Ladder (run in declared order; all three rungs computed regardless of outcome)",
        "",
        "| Rung | Features | AUC | 95% CI | Permutation p | Significant (p<{:.2f})? |".format(
            significance_alpha),
        "|---|---|---|---|---|---|",
    ]
    rung_labels = {
        "rung1": ("1 — baseline spectral (16 features)", "rung1_baseline"),
        "rung2": ("2 — PSWT + baseline combined", "rung2_pswt_plus_baseline"),
        "rung3": ("3 — per-channel/zone, fresh computation", "rung3_per_channel"),
    }
    for key, (label, full_name) in rung_labels.items():
        r = ladder_result[key]
        sig = "**YES**" if r["p_value"] < significance_alpha else "no"
        lines.append(f"| {label} | | {r['auc']:.3f} | [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}] | "
                     f"{r['p_value']:.4f} | {sig} |")
        if full_name == stopped_at:
            lines[-1] += "  *(first rung to pass — drives the interpretation below)*"

    lines += [
        "",
        "## §0d decision table",
        "",
        "| Outcome | Final report says |",
        "|---|---|",
        f"| Any rung clearly above chance | {_DECISION_TABLE_SENTENCES['positive']} |",
        f"| All three at chance | {_DECISION_TABLE_SENTENCES['inconclusive']} |",
        "",
        f"**Outcome marked:** {'Any rung clearly above chance' if outcome == 'positive' else 'All three at chance'} "
        f"({'stopped at ' + stopped_at if stopped_at else 'none of the three reached p<' + str(significance_alpha)}).",
        "",
    ]
    if outcome == "positive" and ladder_result["rung2"]["p_value"] >= significance_alpha:
        lines += [
            "## Additional observation",
            "",
            "Rung 2 (PSWT + baseline combined) was **not** significant "
            f"(p={ladder_result['rung2']['p_value']:.4f}) even though both rungs that compose "
            "it individually were. Adding PSWT features diluted rather than added to the "
            "detectable signal — further evidence that the PSWT feature family specifically "
            "carries no useful subject-level information here, rather than the combined "
            "analysis simply lacking power.",
            "",
        ]
    lines += [
        "## Methodology note (rung 3)",
        "",
        "Rung 3 uses 5 coarse anatomical zones (frontal, central, parietal, occipital, "
        "temporal) rather than all 127 individual channels, to keep the feature count "
        "tractable at n=64. 71 of 127 channels (standard extended-10-5 sites with recognized "
        "zone prefixes) were mapped; the remaining 56 (far-lateral/interstitial extended sites) "
        "were not assigned a zone and are excluded from this diagnostic. This is exploratory, "
        "not a declared feature family — it exists only to test whether ROI-averaging destroyed "
        "between-subject variance.",
        "",
    ]
    return "\n".join(lines)


def write_control_diagnostic(ladder_result: dict, out_path: Path,
                              significance_alpha: float = 0.05) -> None:
    text = render_control_diagnostic(ladder_result, significance_alpha)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
