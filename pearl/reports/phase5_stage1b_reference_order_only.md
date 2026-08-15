# Phase 5 Stage 3 Validation — Step 1: Reference-order fix alone

**DIAGNOSTIC PRECISION, NOT DIRECTLY COMPARABLE STATISTICAL RIGOR** to the 0.474/0.651 headline numbers below: 200 permutations / 500 bootstrap resamples (vs the frozen config's 1000/2000). This is attribution diagnostics only -- isolating which of Stage 1's two bundled preprocessing fixes drives the Stage 3 result, not a new deliverable number. See `docs/` plan `sparkling-launching-torvalds.md` §Step 1.

**Isolated condition:** reference.compute_order=post_interpolation (fix applied), ica.n_components=30 (ICA fix reverted to original)

**Cohort:** n=66 (this run's own QC/exclusion outcome under this isolated preprocessing condition -- not necessarily identical to Stage 3's 64-subject cohort).

## Result: NOT CORROBORATED

- PSWT features only: AUC **0.583**, 95% CI [0.324, 0.750], permutation p=0.2338
- PSWT features + nuisance: AUC 0.540, 95% CI [0.341, 0.768], permutation p=0.3731
- Nuisance only (this run's reference line): AUC 0.546, 95% CI [0.330, 0.770], permutation p=0.2687

## Comparison to the other three data points on the same question

| Condition | AUC | 95% CI | p |
|---|---|---|---|
| Original Phase 3 (bug present, ICA n_components=30) | 0.474 | — | 0.577 |
| Stage 3 (both fixes applied) | 0.651 | [0.353, 0.764] | 0.0410 |
| **This run — Reference-order fix alone** | **0.583** | [0.324, 0.750] | 0.2338 |

## Interpretation

This isolated condition lands between the original and both-fixed AUCs -- consistent with a partial, non-dominant contribution from this fix alone; the two fixes likely interact rather than one alone explaining the flip.

Per Step 0's finding (`reports/phase5_stage3_stability.md`), the underlying 0.651 point estimate itself does not reliably clear its own nuisance-only comparison under resampling -- attribution here explains *what moved the point estimate*, not whether that point estimate is a reliable effect. Read this report alongside Step 0, not as a standalone corroboration.

