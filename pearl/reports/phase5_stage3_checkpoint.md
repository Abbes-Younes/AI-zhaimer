# Phase 5 Stage 3 — Checkpoint: VERDICT POSITIVE (marginal), read with real caution

**Headline number: AUC 0.651** (95% CI [0.353, 0.764], permutation p=0.041,
n=64: 38 at-risk / 26 no-risk) on `binary_risk_vs_none`, using PSWT rest
features on Stage 1's corrected preprocessing. Per the pre-declared verdict
rule (`features_only` beats `nuisance_only` at p<0.05), this is technically
**POSITIVE** — a reversal of Phase 3's original **NULL** (AUC 0.474, p=0.577).

**This is not being reported as "the gap is closed" or "signal confirmed."**
It is reported as: a marginal, fragile positive result that emerged from
fixing real preprocessing bugs, on a cohort that changed by only 5 subjects,
that needs independent scrutiny before anyone treats it as a validated
finding. The reasons for that caution are below, not buried in an appendix.

Full raw output (verdict-first per its own template): `reports/phase5_stage3_results.md`.
**That auto-generated report contains stale narrative text inherited
unmodified from the original Phase 3 report-writing code** — written when
the actual result was null, describing THAT result, not this one. Do not
read its prose as accurate; the tables/numbers are real computed values,
independently checked here.

---

## 1. What actually changed, and what didn't

**Same exact methodology as Phase 3** (`phase_3.md`, `config/models.yaml`,
`reports/analysis_plan_frozen.md` unedited): same primary target, same CV
scheme (5×10, pooled OOF), same model class (L2 logistic regression), same
four reference lines, same permutation/bootstrap procedure, same stopping
rule. **What changed is the input data**: Stage 1's corrected preprocessing
(reference-order fix + evidence-based ICA `n_components`) produced a
different 64-subject cohort (5 subjects swapped in each direction vs. the
original 64) and different feature values for every subject.

**Important limitation this report is not hiding**: Stage 1 changed *two*
things at once (reference order and ICA `n_components`). This result cannot
attribute the flip to either one specifically — that would require a third,
single-variable re-run, which was out of this stage's scope.

## 2. Corrections to the auto-generated report's stale text

`pearl_models/reports.py` and `pearl_models/delivery.py` hardcode narrative
prose that was accurate for Phase 3's original null result and were never
adapted to describe a different verdict. Specifically wrong in the raw
output, corrected here:

- **"Deferred Phase 1 issues... neither has been resolved"** — false for
  this run. The reference-order bug and the ICA `n_components` question
  were both addressed in Stage 1 (`reports/phase5_stage1_data_foundation.md`).
  That is the whole premise of this stage's test.
- **`model_card.md`'s "does not exceed chance or... nuisance-only"** —
  false for this run. 0.651 exceeds both chance (0.500) and nuisance-only
  (0.557). A corrected model card is written separately (§5).
- **The leakage checklist's h5-duration-confound note** cites the
  *original* cohort's numbers (r=0.81/0.96, "primary result already
  null... no significant finding driven by this artifact") as a
  reassurance — that reassurance does not automatically transfer to a
  positive result on a different cohort. Independently re-checked below.

## 3. Independent scrutiny before trusting this number

### 3a. The h5-duration confound, re-checked on this cohort

Re-ran the correlation fresh, not trusted from stale text: on this Stage
1/2 cohort, `harmonic_amplitude_profile_h5_median`/`h5_iqr` correlate with
`usable_duration_s` at **r=0.385 (p=0.307)** and **r=0.346 (p=0.362)**,
n=9 non-missing (down from 11 in the original cohort). Materially weaker
and not significant, versus the original's r=0.81/0.96 — but n=9 has very
low power to rule anything out either way. **Not evidence the positive
result is an h5-duration artifact, but not strong evidence it isn't
either**, given the small subset size.

### 3b. "100% feature selection frequency" is not informative here

Every one of the 18 non-constant PSWT features shows `selection_frequency
= 1.0` in `feature_stability.csv`. Under L2-penalized logistic regression,
coefficients are shrunk toward zero but essentially never become *exactly*
zero (unlike L1/Lasso) — so a coefficient magnitude threshold
(`|coef| > 1e-8`) will read as "selected" for nearly every feature, nearly
always. This is expected L2 behavior, not evidence that all 18 features are
equally, meaningfully predictive, and it means h5's 100% figure does not
single it out as unusually important relative to the other 17.

### 3c. Structural leakage checks — clean

- Permutation null centred at **0.489** (within the ±0.05 tolerance of
  0.5) — the CV design is not structurally leaking.
- No subject appears in both train and test in any fold (re-derived and
  checked directly, `leakage.check_no_subject_leakage`).
- Scaling/imputation/selection are fit inside the training fold only
  (structurally guaranteed by `cv.run_outer_fold` — no fit-on-full-data
  code path exists).

### 3d. Why this should still be read with real skepticism

- **p=0.041 is barely under the conventional 0.05 threshold** — not a
  strong, robust result by any reasonable standard.
- **The 95% CI [0.353, 0.764] is wide and its lower bound sits below
  chance (0.5)**. A bootstrap CI and a permutation p-value test different
  things and are not strictly contradictory, but a CI this wide, straddling
  chance, is the signature of a noisy small-N estimate, not a confidently
  located effect.
- **Swapping 5 of 64 subjects (Stage 1's cohort change) moved the point
  estimate from 0.474 to 0.651** — a swing of 0.177 AUC from less than 8%
  of the cohort changing. That is a strong signal that this specific
  number is sensitive to exactly which subjects happen to be in the sample,
  which is the opposite of a robust finding.
- **`features_plus_nuisance` (0.638, p=0.058) does NOT clear p<0.05** —
  adding EEG features to nuisance does not itself reach significance,
  even though `features_only` alone barely does. A genuinely robust EEG
  effect would be expected to show up more consistently across these
  related comparisons, not only in the single most favorably-framed one.
- **None of the three Holm-corrected secondary comparisons survive
  correction** (`baseline_rest` p_holm=0.963, `pswt_plus_baseline_rest`
  p_holm=0.264, `baseline_msit` p_holm=0.963) — the positive result is
  isolated to the one primary comparison, not corroborated by related
  analyses on the same corrected data.

## 4. Positive controls (unchanged pattern from Phase 3)

| Control | AUC | Verdict |
|---|---|---|
| 1a — eyes-open vs eyes-closed | 0.849 | PASS (floor 0.80) |
| 1b — sex classification | 0.465 | FAIL (floor 0.65, chance-level) |

Same pattern as the original run (0.830 / 0.486): the pipeline measures
real alpha waveform-shape signal (1a), but a genuinely detectable
cross-subject target (sex) still lands at chance. This caveat from
`phase_3.md` §1c applies with the same force here: **a primary finding —
positive or null — cannot fully rule out that this feature pipeline simply
does not generalise well across subjects for any target**, genotype
included. A positive genotype result alongside a chance-level sex result is
an unresolved asymmetry, not a detail to skip past.

## 5. What this checkpoint recommends

**This is not strong enough evidence to report as "Phase 5 found the
signal Phase 3 missed."** It is strong enough to say: fixing two real,
independently-justified preprocessing bugs changed this project's answer to
its central question, on this cohort, at the edge of conventional
significance, with several markers of fragility. Both things are true and
both belong in the record.

Recommended next steps for whoever owns this project, in priority order:
1. **Do not ship or publicize AUC 0.651 as a validated result.** Treat it as
   a preliminary, hypothesis-generating signal.
2. **A single-variable re-run** (reference-order fix alone, ICA fix alone)
   would clarify whether one specific correction — or their combination —
   drives the change, and whether the effect is stable across that
   decomposition.
3. **Independent replication is the real test**: does this result hold on
   a genuinely new, larger sample, not just a 5-subject-different draw from
   the same 79?
4. Both the frozen original (NULL, 0.474) and this new result (POSITIVE,
   0.651, with caveats) should be reported together to any stakeholder —
   presenting only one would be misleading in either direction.
