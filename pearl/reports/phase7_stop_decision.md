# Phase 7 — Stop Decision: Stage B Declined

**Date:** 2026-08-15 · **Status:** FINAL — this decision is recorded so it is not
casually revisited.

---

## Decision

**The representation rebuild (`phase_6.md` Stage B) will not be run. The genotype
investigation is closed at four looks.**

This is a **deliberate decline with stated grounds**, not unfinished work. A
reader encountering "Stage B: specified but not run" elsewhere in this repository
should read that as *declined*, and should read this document before proposing to
revisit it.

## Grounds, in order of weight

### 1. There is no headroom in this cohort

The minimum detectable effect at 80% power is **AUC 0.693**
(`reports/phase6_power_analysis.txt`). All three representations that
successfully passed the sex control sit **at or below that floor**:

| Representation | Sex AUC | vs. MDE 0.693 |
|---|---|---|
| `baseline_rest_msit` | 0.696 | +0.003 |
| `baseline_rest` | 0.688 | −0.005 |
| `baseline_all` | 0.652 | −0.041 |

Sex is among the most robustly encoded subject-level traits in resting EEG, and
this cohort can only *just* resolve it. Genotype risk group is a substantially
subtler effect. There is no reason to expect a representation change to buy the
sensitivity that sample size does not provide.

### 2. A marginal Stage B positive would more likely be false than real

Power against the published 0.58 benchmark is **20%** — a real effect of exactly
that size would be missed four times in five. Combined with four prior genotype
looks, the probability that a marginal Stage B "positive" is a false positive
exceeds the probability that it is a true one.

**This is not hypothetical; it is the documented Phase 5 episode.** Stage 3
produced AUC 0.651, p=0.041 — nominally significant, above the published
benchmark, and entirely convincing on first inspection. Validation
(`reports/phase5_stage3_validation.md`) showed:

- bootstrap resampling median **0.565**, essentially on the nuisance-only line (0.557);
- **24%** of resamples below chance;
- neither underlying preprocessing fix reproducing significance in isolation
  (0.583 p=0.234; 0.602 p=0.174).

Stage B would re-roll that same die, with more researcher degrees of freedom
(five representation families) and the same underpowered cohort.

### 3. Stage B's most likely failure mode is a *misleading positive*, not a null

Recorded in `reports/phase6_bounded_null.md` §8: channel-space covariance in this
dataset is severely and *variably* rank-deficient. ICA removes **4–47 components
per subject**, giving an effective rank of roughly **16–50 of 127 channels**, and
that rank **tracks `n_ica_removed`** — an existing, declared nuisance variable
(`pearl_models.nuisance.NUISANCE_COLUMNS`).

A covariance-based representation could therefore decode *preprocessing
aggressiveness* rather than neurophysiology. The expensive outcome is not Stage B
returning nothing; it is Stage B returning something that then costs a further
full validation cycle to attribute and eliminate.

### 4. The marginal evidentiary gain is small

Stage B's stated purpose was to establish that some representation of this cohort
retains subject-level information. **That is already established**, by three
independent significant control results on representations that already exist
(p = 0.019, 0.007, 0.029). The bounded null in
`reports/phase6_bounded_null.md` does not depend on Stage B being run.

### 5. Cost

≈10 person-days of engineering plus 1.5–3 days of compute, for the marginal gain
described above.

## What would change this decision

**A new cohort, or an independent genotyped EEG dataset.** Specifically:

- a sample sized from the power analysis on record (`reports/phase6_power_analysis.txt`)
  rather than the 79 available here;
- or an independent public dataset with APOE/PICALM genotyping at comparable
  scale, which — as verified during Phase 5 — does not currently appear to exist.

**Not** more work on these 64 subjects. No representation change, feature family,
model class, or preprocessing variant applied to this cohort would alter the
conclusion, because the binding constraint is sample size, not method.

## Look history

The genotype target has been examined **four** times:

1. Phase 3 primary analysis (AUC 0.474, p=0.577)
2. Phase 5 Stage 3, both preprocessing fixes (0.651, p=0.041 — did not survive validation)
3. Phase 5 isolation run, reference-order fix alone (0.583, p=0.234)
4. Phase 5 isolation run, ICA fix alone (0.602, p=0.174)

Phase 6 Stage A added **zero** further looks (control targets only). Phase 7 adds
none. Any future genotype analysis would be look #5 and must be pre-registered
before running, per `phase_6.md` §1.

## Cross-references

- `reports/phase6_bounded_null.md` — the bounded null and control matrix
- `reports/phase6_power_analysis.txt` — detection ceiling
- `reports/phase5_stage3_validation.md` — why the 0.651 result was retracted
- `HANDOVER.md` — Stage B entry, marked declined and pointing here
