# Phase 3 Results — VERDICT: NULL

Primary analysis (PSWT features on resting-state, `binary_risk_vs_none`, n=64): **AUC 0.474**, 95% CI [0.266, 0.702], permutation p=0.5774.

This is a **null result**: features work within-subject but do not generalise across subjects for a genuinely detectable target (sex, AUC 0.486) — this null cannot fully separate 'no real genotype signal' from 'features don't generalise cross-subject at all.'

## 1. Verdict and primary number

- AUC: **0.474**
- 95% bootstrap CI: [0.266, 0.702]
- Permutation p-value (full pipeline re-run per permutation): 0.5774
- Spread across the 10 repeats: [0.369, 0.566]

## 2. All four reference lines

| Reference | AUC | CI | Source |
|---|---|---|---|
| Chance | 0.500 | — | — |
| QC-only | 0.545 | [0.435, 0.800] | Phase 2 gate |
| Nuisance-only | 0.523 | [0.306, 0.735] | this phase, §2b |
| Published benchmark | 0.580 | — | Li et al. 2025, MSIT (not rest) |
| **PSWT features (primary)** | **0.474** | [0.266, 0.702] | this analysis |
| Features + nuisance | 0.517 | [0.305, 0.736] | this analysis |

## 3. Positive control outcomes

- 1a (eyes-open vs eyes-closed): AUC 0.830 (PASS, floor 0.80)
- 1b (sex classification): AUC 0.486 (FAIL, floor 0.65)
- Full detail: `reports/phase3_positive_controls.md`

## 4. Benchmark reproduction outcome

- MSIT baseline features vs risk_vs_none: AUC 0.459 (verdict: AT_CHANCE)
- Full detail and investigation: `reports/phase3_benchmark_reproduction.md`

## 5. Secondary comparisons (Holm-corrected)

| Analysis | AUC | p (raw) | p (Holm) |
|---|---|---|---|
| baseline_rest | 0.375 | 0.8831 | 1.0000 |
| pswt_plus_baseline_rest | 0.513 | 0.4176 | 1.0000 |
| baseline_msit | 0.459 | 0.5804 | 1.0000 |

None of the secondary comparisons survive Holm correction (all p_holm ≥ 0.05).

## 6. Feature stability

Selection frequency and sign consistency across all repeat×fold combinations (features stable in >80% of folds only):

| feature                                |   selection_frequency |   sign_consistency | stable   |
|:---------------------------------------|----------------------:|-------------------:|:---------|
| harmonic_amplitude_profile_h2_median   |                     1 |               0.56 | True     |
| harmonic_amplitude_profile_h2_iqr      |                     1 |               0.7  | True     |
| harmonic_amplitude_profile_h3_median   |                     1 |               0.64 | True     |
| harmonic_amplitude_profile_h3_iqr      |                     1 |               0.88 | True     |
| harmonic_amplitude_profile_h4_median   |                     1 |               0.88 | True     |
| harmonic_amplitude_profile_h4_iqr      |                     1 |               0.86 | True     |
| harmonic_amplitude_profile_h5_median   |                     1 |               0.7  | True     |
| harmonic_amplitude_profile_h5_iqr      |                     1 |               0.6  | True     |
| harmonic_to_interharmonic_ratio_median |                     1 |               0.98 | True     |
| harmonic_to_interharmonic_ratio_iqr    |                     1 |               0.74 | True     |
| cycle_to_cycle_variability_median      |                     1 |               1    | True     |
| cycle_to_cycle_variability_iqr         |                     1 |               0.96 | True     |
| period_variability_median              |                     1 |               0.92 | True     |
| period_variability_iqr                 |                     1 |               0.7  | True     |
| rise_decay_ratio_median                |                     1 |               0.98 | True     |
| rise_decay_ratio_iqr                   |                     1 |               0.6  | True     |
| peak_trough_sharpness_ratio_median     |                     1 |               0.62 | True     |
| peak_trough_sharpness_ratio_iqr        |                     1 |               0.72 | True     |

Note: `harmonic_amplitude_profile_h1_median`/`h1_iqr` were never selected — they are tautologically constant (harmonic 1 normalised to itself is exactly 1.0 for every cycle), a Phase 2 feature-definition artifact, not a modelling failure. `harmonic_amplitude_profile_h5_*` show 100% selection frequency but correlate strongly with `usable_duration_s` among the small subset where they are non-missing (see §7 limitations and `reports/phase3_leakage_checklist` notes) — their selection should not be read as evidence of a genuine harmonic effect.

## 7. Limitations

- **Power** (Amendment 2 §0f): at 39 vs 25, the 95% CI on an AUC estimate is expected to be roughly ±0.13–0.15 wide; the observed CI width (0.436) is consistent with this a priori expectation.
- **QC-only CI width** (Amendment 2 §0d): Phase 2's gate passed at AUC 0.545 but with a 95% CI of [0.435, 0.800] — "no evidence of contamination," never "contamination excluded."
- **Rest-vs-task benchmark mismatch**: the published 0.58 came from task-state MSIT, not rest; this project's own MSIT reproduction landed at chance (§4 of this table), a characterized feature-richness gap, not a validated comparison point either way.
- **Deferred Phase 1 issues**: the reference-order bug (average reference computed before bad-channel interpolation) and the ICA `n_components=30` over-decomposition concern were both deferred pending a better connection for the ~46GB re-download (Option C) — neither has been resolved.
- **A_P_plus attrition**: the smallest genetic group lost the largest share of subjects to QC exclusion (Phase 1); `binary_high_vs_rest` and `multiclass_3` remain descriptive-only per Amendment 1.
- **Cross-subject generalisation caveat**: positive control 1b (sex) landed at chance (AUC 0.486), so this null cannot fully rule out that the feature pipeline simply doesn't generalise across subjects for any target, not specifically genotype.
- **h5 duration confound** (§4 leakage checklist): the two harmonic-5 columns, selected in 100% of folds, correlate strongly with recording duration among their small non-missing subset — a transparency caveat on feature stability, not a leakage bug (permutation null centred at 0.492, structurally clean).

## 8. What would be needed to answer the question properly

- A larger cohort — at N=64 (39 vs 25) this project is underpowered to distinguish a true AUC of 0.65 from the published 0.58, let alone detect smaller effects.
- Task EEG (MSIT/Sternberg) rather than rest alone, since the source paper found task EEG outperforms resting-state EEG for this classification problem.
- The Option C reprocessing (reference-order fix, ICA component-count re-evaluation) to rule out those Phase 1 confound candidates definitively rather than by absence of evidence in Phase 2's gate.
- A richer MSIT feature-engineering pipeline (multitaper time-frequency area, per-condition splitting, subspace selection) to make the benchmark comparison meaningful rather than characterized-but-unresolved.
