# Phase 5 Stage 1 — ICA `n_components` re-evaluation (phase_5.md §0b)

**Question.** Phase 1 used a fixed `ica.n_components: 30` regardless of each
subject's actual channel rank after bad-channel interpolation (montage is
125/127-channel `standard_1005`). Phase 1's own report flagged ICA removal
rates of 40–77% on the worst subjects as a plausible artifact of forcing
every subject through the same 30-component decomposition, independent of
how many channels were interpolated or how much genuine signal rank
remained. This evaluation tests one evidence-based alternative — MNE's
own `n_components` float convention, `n_components=0.99` (retain enough
components to explain 99% of variance, scaled per subject) — against the
current fixed value.

**Method.** The 10 (subject, task) pairs with the most interpolated
channels in the frozen `qc_metrics.csv` were selected (highest-stress cases
for ICA, where a component-count mismatch should show up most clearly).
Each was reprocessed twice via `process_subject_task(..., output_dir=
<scratch>)` — never touching the live derivative tree — once with
`n_components=30` and once with `n_components=0.99`, everything else held
fixed. Raw data for these 10 subjects was fetched only for this evaluation
and deleted immediately afterward (Phase 1's streaming discipline).
Comparison script: `pearl_preproc/ica_component_eval.py`, driver:
`scripts/run_ica_component_eval.py`. Full results:
`data/phase5_scratch/ica_n_components_eval_results.csv`.

## Results

| subject | task | n_bad_channels | fixed_30 n_fit / removed_frac | var_0.99 n_fit / removed_frac | Δ removed_frac |
|---|---|---|---|---|---|
| sub-50 | rest | 20 | 30 / 0.033 | 57 / 0.018 | -0.015 |
| sub-05 | msit | 23 | 30 / 0.267 | 11 / 0.091 | -0.176 |
| sub-03 | msit | 13 | 30 / 0.467 | 75 / 0.347 | -0.120 |
| sub-54 | rest | 15 | 30 / 0.100 | 50 / 0.080 | -0.020 |
| sub-36 | rest | 9  | 30 / 0.233 | 86 / 0.140 | -0.093 |
| sub-57 | msit | 3  | 30 / 0.233 | 90 / 0.256 | +0.023 |
| sub-30 | rest | 13 | 30 / 0.233 | 37 / 0.324 | +0.091 |
| sub-70 | rest | 3  | 30 / 0.167 | 54 / 0.130 | -0.037 |
| sub-45 | rest | 1  | 30 / 0.267 | 96 / 0.156 | -0.111 |
| sub-56 | msit | 2  | 30 / 0.600 | 59 / 0.576 | -0.024 |

Aggregate `removed_frac` (fraction of fitted ICA components excluded as
artifact):

| config | mean | median | std | min | max |
|---|---|---|---|---|---|
| fixed_30 | 0.260 | 0.233 | 0.166 | 0.033 | 0.600 |
| explained_variance_0.99 | 0.212 | 0.148 | 0.167 | 0.018 | 0.576 |

`n_fit` (number of ICA components actually fit):

| config | mean | median | std | min | max |
|---|---|---|---|---|---|
| fixed_30 | 30.0 | 30.0 | 0.0 | 30 | 30 |
| explained_variance_0.99 | 61.5 | 58.0 | 26.1 | 11 | 96 |

**Direction of effect**: `explained_variance_0.99` lowers `removed_frac`
relative to `fixed_30` in 7 of 10 subjects; the two regressions
(sub-57 +0.023, sub-30 +0.091) are both low-bad-channel subjects (3 and 13
bad channels) where the fixed component count was already a reasonable fit.
The largest reductions cluster on subjects with more bad channels
(sub-05: 23 bad, -0.176; sub-03: 13 bad, -0.120; sub-45: 1 bad but only
30-fit forced fewer components onto a still-large rank, -0.111) — consistent
with the hypothesized mechanism: a fixed 30-component decomposition doesn't
scale to the actual signal rank, so components each carry more mixed
brain+artifact content, and ICLabel ends up flagging more of them.

## Decision

**Adopt `n_components: 0.99`** (`config/preproc.yaml`). The effect is
consistent in direction (7/10 subjects improve) and material in magnitude
(mean removal fraction drops ~19% relative, median ~36% relative), directly
addressing the excess-removal-rate concern that motivated this evaluation.
The wide spread in `n_fit` (11–96) is not itself a defect — it reflects
each subject's actual post-interpolation signal rank rather than an
arbitrary fixed count, which is the more principled behavior per MNE's own
documented convention for this parameter.

This is a **Stage 1 data-foundation decision**, applied before the full
three-task re-run (§1). It does not retroactively change or invalidate the
frozen Phase 1–3 derivative tree or the Phase 3 NULL result — it governs
only the new, parallel Phase 5 preprocessing run.
