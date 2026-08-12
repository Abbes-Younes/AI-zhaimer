# PEARL-Neuro EEG Classification — Phase 5 Final Report

**Prepared:** 2026-08-12

---

## Verdict, up front

**Fixing two real, independently-justified preprocessing bugs changed this
project's primary result from a clean null to a marginal, fragile positive
— and that positive result should not be treated as validated evidence of
a real effect.** Both numbers are real, both are reported, together, below.
This is not a "we found it" report. It is a "here is exactly what changed,
how sure we are of it, and what it would take to actually know" report.

| | Original (Phase 3) | Phase 5 (Stage 3, corrected preprocessing) |
|---|---|---|
| AUC | 0.474 | 0.651 |
| 95% CI | [0.266, 0.702] | [0.353, 0.764] |
| Permutation p | 0.577 | 0.041 |
| Verdict | NULL | POSITIVE (marginal — see §4) |
| Cohort | N=64 (39/25) | N=64 (38/26), 5 subjects different |

---

## 1. What was asked, what was done

**Asked:** having delivered a validated null result (Phase 3), make a
genuine second attempt to close the gap to the published benchmark
(AUC≈0.58), using what Phases 1-4 revealed, without compromising the
rigor that made the original null trustworthy.

**Done, across three stages, each reported before the next began:**

- **Stage 1 — Data foundation.** Fixed a real preprocessing bug (the
  average EEG reference was computed *before* bad-channel detection,
  letting bad channels contaminate every other channel's signal before
  being caught). Re-evaluated a previously-fixed ICA setting with real
  comparison data and adopted a better-justified value. Added a third EEG
  task (Sternberg) that a prior budget model had wrongly ruled out
  affordable. Result: the confound gate passed *more* cleanly than before
  (AUC 0.509 vs. the original 0.545), and the corrected cohort landed at
  the same size (N=64) with 5 different subjects.
- **Stage 2 — Feature engineering.** Extended the existing feature set to
  the new Sternberg data (mechanical). Built a richer spectral feature
  family (multitaper time-frequency-area, closer to the published
  benchmark's method) and tested it — carefully, only against the
  benchmark-reproduction question, never against the primary target
  directly. Result: **not significant** (AUC 0.546 vs. the prior 0.459,
  p=0.315) — the richer features did not demonstrably close the benchmark
  gap.
- **Stage 3 — Modeling.** Re-ran Phase 3's exact declared methodology —
  same cross-validation scheme, same model class, same reference lines,
  same stopping rules, nothing tuned or changed — on Stage 1's corrected
  preprocessing. This is the one stage that touches the primary target,
  and it got one honest attempt, exactly as Phase 3 did. Result: the
  headline number above.

## 2. Why the positive result should not be taken at face value

Four independent reasons, none of them hidden in an appendix:

1. **p=0.041 is barely under the conventional 0.05 significance
   threshold.** This is not a strong result by any normal standard.
2. **The 95% confidence interval [0.353, 0.764] is wide and its lower
   bound sits below chance (0.5).** That is the signature of a noisy
   estimate on a small sample, not a confidently located effect.
3. **Swapping only 5 of the 64 subjects (a side effect of the corrected
   preprocessing, not a deliberate choice) moved the point estimate by
   0.177 AUC** — from 0.474 to 0.651. A result this sensitive to which
   specific 5 subjects are in or out of the sample is not a robust one.
4. **The result doesn't corroborate itself.** Adding demographic/QC
   covariates alongside the EEG features (`features_plus_nuisance`)
   scores 0.638 with p=0.058 — just short of significance. None of three
   related secondary comparisons survive the correction for testing
   multiple comparisons. A real, robust effect would be expected to show
   up more than once; this one shows up in exactly the single primary
   comparison and nowhere else.

We also specifically re-checked, on this cohort, a data-quality concern
flagged in a previous phase (certain features correlating with recording
duration rather than genuine brain signal) — that concern is *weaker* on
this cohort than before, but the small subset of affected subjects (9)
means it can't be fully ruled in or out either way.

**Bottom line: two real preprocessing bugs got fixed, and the number moved.
Whether that number reflects genuine biological signal or is an artifact
of exactly which subjects happened to end up in this smaller, sensitive
sample is not yet answerable from this data alone.**

## 3. What was NOT touched or compromised to get here

- The original Phase 3 null result — reports, model, everything — is
  preserved byte-for-byte, unedited, and is not superseded by this report.
  Both results are real and both are reported.
- No statistical setting (permutation count, bootstrap count, CV scheme,
  model class) was changed after seeing any result, at any stage.
- The richer-feature bet (Stage 2) was tested and reported as a null
  before Stage 3 ran — it was not folded into Stage 3's primary analysis,
  which would have conflated two separate questions in one attempt.
- Label blindness was maintained throughout Stages 1-2; only two
  narrowly-scoped, code-enforced modules ever touch group labels, and only
  Stage 3 (the one declared primary-target-touching stage) produces a
  claim about the actual target.

## 4. What would actually answer the question

In priority order, per `reports/phase5_stage3_checkpoint.md`:

1. **A single-variable re-run** — the reference-order fix alone, then the
   ICA setting alone — to see whether one specific correction (or their
   combination) is driving the change, and whether the effect holds up
   when isolated.
2. **Independent replication on a larger, genuinely new sample.** This is
   the actual test. A 5-subject-different draw from the same 79-subject
   dataset is not independent replication.
3. **If Stage 3's result is to be taken further**, both this result and
   the original null must be reported together to any audience — citing
   only one would misrepresent what is actually known.

## 5. Deliverables index

| Artifact | Path |
|---|---|
| Stage 1 checkpoint | `reports/phase5_stage1_data_foundation.md` |
| Stage 2 checkpoint | `reports/phase5_stage2_feature_engineering.md` |
| Stage 3 checkpoint (the accurate account) | `reports/phase5_stage3_checkpoint.md` |
| Stage 3 raw results (caution: stale narrative text, see checkpoint) | `reports/phase5_stage3_results.md` |
| Stage 3 model + corrected model card | `data/derivatives/models_stage3/` |
| Original Phase 3 model, unedited | `data/derivatives/models_phase3to4_frozen/` |
| Original Phase 1-4 derivative trees, unedited | `data/derivatives/*_frozen/` |
| This report | `reports/phase5_final_report.md` |

## 6. If this project continues

See `HANDOVER.md`'s Phase 5 section for sizing of the single-variable
re-run and replication options, and for what's on disk vs. what would need
regenerating.
