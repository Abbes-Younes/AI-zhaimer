# Phase 5 Stage 2 — Benchmark-Reproduction Diagnostic (Track B) — VERDICT: NOT_SIGNIFICANT

**One run, per `reports/phase5_stage2_plan_frozen.md` §4. No retuning after
seeing this number.** `benchmark_diagnostic.run()`'s verdict logic requires
both a higher point estimate AND permutation p < 0.05 against the prior
baseline (same significance-first discipline `phase_4.md` adopted after
catching its own unjustified CI-lower-bound criterion) — it correctly
returns `not_significant` here. **The point estimate moved up (0.459 →
0.546), but not by an amount distinguishable from chance or from the prior
baseline.**

## Result

| | Value |
|---|---|
| Richer features (`msit_tfa_*`, logistic regression) | **AUC 0.546** |
| 95% bootstrap CI | **[0.459, 0.805]** |
| Permutation p-value | **0.315** |
| Richer features (linear SVM, secondary) | AUC 0.464 |
| Permutation null mean | 0.498 (sane — see §Leakage below) |
| Prior simple baseline (`phase3_benchmark_reproduction.md`) | AUC 0.459 |
| Published benchmark (Li et al. 2025, MSIT-ML, different feature family+cohort) | AUC 0.58 |
| Subjects used | 72 (of 76 with any Track B data — 4 dropped for missing genotype label or incomplete `msit_tfa_*`) |
| Features available / mean selected per fold (t-test+FDR) | 12 / 11.36 |

## Why this is reported as "not significantly different," not "improved"

- **The permutation p-value (0.315) is nowhere near the conventional 0.05
  threshold.** The observed 0.546 is well within the range this exact CV
  procedure produces from label-permuted (i.e. genuinely null) data.
- **The 95% CI is wide and its lower bound (0.459) sits exactly on the
  prior baseline's point estimate.** The data do not rule out "no real
  difference from the simple baseline."
- **The CI's lower bound also sits below chance (0.5)** and its upper bound
  (0.805) is very wide — consistent with what §0f of the original frozen
  plan warned about generally: small-N AUC estimates are noisy, and a
  point estimate moving from 0.459 to 0.546 is well within that noise band,
  not necessarily a property of the richer features.
- The **SVM secondary model scored worse** (0.464), close to the prior
  baseline's own SVM result (0.38) — consistent with "no clear signal,"
  not "richer features found a susceptible-to-classifier-choice effect."

**Conclusion: richer multitaper TFA features on MSIT do not measurably
close the gap to the published 0.58 benchmark, on this evidence.** This
mirrors `phase3_benchmark_reproduction.md`'s own AT_CHANCE finding — the
richer feature engineering changed the point estimate but not the
statistical picture.

## A limitation of the richer-feature design itself, visible in this run

**t-test+FDR selection retained a mean of 11.36 of 12 candidate features per
fold** — i.e., selection did almost no narrowing. Two honest readings:

1. With only 12 candidate features (5 bands × {mean, IQR} + 2 aperiodic),
   there may simply not be enough candidates for FDR correction to have
   much room to discriminate — the published method's selection step
   likely operated over a much larger feature space (multiple channels ×
   frequencies, not 10-channel-ROI-averaged summaries).
2. Because selection barely filtered anything, **this diagnostic mostly
   tested "does the full 12-feature richer set beat the full 7-feature
   simple set," not "does published-style feature selection help"** — the
   selection step's contribution to this result is minimal, which weakens
   the claim that this reconstruction faithfully tests the published
   method's mechanism, beyond the richer spectral features themselves.

## Leakage check

Permutation null mean **0.498** — centred at chance, as it should be if the
CV/selection procedure has no structural leakage (same check
`phase3_benchmark_reproduction.md` and `phase3_results.md` §4 both ran).
Clear.

## Scope reminder

This diagnostic evaluates `msit_tfa_*` only, against the published MSIT
benchmark reproduction question — **it says nothing about
`binary_risk_vs_none` as this project's primary target**, and nothing here
authorizes running Track B's richer features against that target. That
would be a separate, explicitly-scoped Stage 3 decision.

## What this means for Stage 3 (recommendation, not a decision made here)

- The richer-feature lever (multitaper TFA, frontocentral ROI,
  per-condition splitting for Sternberg) does not show a validated
  advantage on the one question it was built to answer. That's a real,
  reportable finding — not a reason to iterate on parameters now.
- Sternberg's `sternberg_encoding_tfa_*`/`sternberg_retrieval_tfa_*`
  features were extracted (69 subjects) but were never part of this
  diagnostic — no published number exists to validate them against. If
  Stage 3 considers using them, that's new, undiagnosed territory, not
  something this result speaks to either way.
- If Stage 3 proceeds to modeling at all, it should not lean on "Track B
  reproduces the benchmark better" as justification — this diagnostic does
  not support that claim.
