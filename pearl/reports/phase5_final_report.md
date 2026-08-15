# PEARL-Neuro EEG Classification — Phase 5 Final Report

**Prepared:** 2026-08-12. **Updated 2026-08-13** with Stage 3 validation
results — see the amendment notice below §4.

---

## Verdict, up front

**Fixing two real, independently-justified preprocessing bugs changed this
project's primary result from a clean null to a marginal, fragile positive
— and that positive result has since been validated and does not hold up.
It should not be delivered as a positive finding.** Both numbers are real,
both are reported, together, below; a third round of validation (§4a)
subsequently showed the positive number does not survive stability or
attribution checks. This is not a "we found it" report. It is a "here is
exactly what changed, how sure we are of it, what we checked, and what it
would take to actually know" report.

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
   when isolated. **Done — see §4a below.**
2. **Independent replication on a larger, genuinely new sample.** This is
   the actual test. A 5-subject-different draw from the same 79-subject
   dataset is not independent replication. Not possible within this
   dataset (79-subject hard cap, no independent cohort exists) — see
   `HANDOVER.md`.
3. **If Stage 3's result is to be taken further**, both this result and
   the original null must be reported together to any audience — citing
   only one would misrepresent what is actually known. **Superseded by
   §4a: the result should not be taken further as a positive finding.**

## 4a. Validation outcome (2026-08-13) — the positive result does not hold up

Item 1 above was completed, alongside an additional stability/resampling
check that wasn't originally scoped but was added when the sensitivity
already documented in §2 (item 3) warranted a closer look before any
delivery decision. Full detail: `reports/phase5_stage3_validation.md`.

**Summary of what was found:**

- **Stability check**: resampling the same 64-subject sample repeatedly
  shows the AUC estimate's median (0.565) sits almost exactly on the
  nuisance-only line (0.557), and 24% of resamples fall below chance
  entirely. The 0.651 point estimate looks like a favorable draw, not a
  reliably-located effect.
- **Attribution check**: isolating each of Stage 1's two preprocessing
  fixes shows *neither* reproduces significance alone (reference-order fix
  alone: AUC 0.583, p=0.234; ICA fix alone: AUC 0.602, p=0.174). Only the
  specific combination, on this specific sample, crosses p<0.05 — a
  pattern more consistent with sample-specific coincidence than a real,
  additive effect.
- **Reproducibility check**: the original 0.651 was independently
  reconfirmed at full statistical precision after restoring the production
  derivative tree (AUC 0.6509, p=0.0410) — the number itself was computed
  correctly; it simply doesn't corroborate under any of the checks above.

**Revised bottom line: the positive framing should not be delivered.** The
defensible deliverable is the honest characterization in this report and
`phase5_stage3_validation.md` — what was tried, what changed, why the
positive number looked real at first, and why it does not survive
scrutiny. See `reports/phase5_stage3_validation.md` §4 for the full
delivery recommendation.

## 5. Deliverables index

| Artifact | Path |
|---|---|
| Stage 1 checkpoint | `reports/phase5_stage1_data_foundation.md` |
| Stage 2 checkpoint | `reports/phase5_stage2_feature_engineering.md` |
| Stage 3 checkpoint (the accurate account) | `reports/phase5_stage3_checkpoint.md` |
| Stage 3 raw results (caution: stale narrative text, see checkpoint) | `reports/phase5_stage3_results.md` |
| **Stage 3 validation (final verdict — read this before citing 0.651 anywhere)** | `reports/phase5_stage3_validation.md` |
| Stage 3 model + corrected model card | `data/derivatives/models_stage3/` |
| Original Phase 3 model, unedited | `data/derivatives/models_phase3to4_frozen/` |
| Original Phase 1-4 derivative trees, unedited | `data/derivatives/*_frozen/` |
| This report | `reports/phase5_final_report.md` |

## 6. If this project continues

See `HANDOVER.md`'s Phase 5 section for sizing of the single-variable
re-run and replication options, and for what's on disk vs. what would need
regenerating.
