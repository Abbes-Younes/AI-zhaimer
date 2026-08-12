# Phase 5 Stage 2 — Feature Engineering: Checkpoint Report

**Verdict: Stage 2 complete. No claim toward the primary target was made or
authorized here.** Track A shipped cleanly. Track B's one-shot benchmark
diagnostic came back `not_significant` — a real, reportable finding, not a
blocker. Whether/how Stage 3 (modeling) proceeds is a decision for whoever
reads this, not decided in this document, per `phase_5_stage2.md`'s own
staging rule.

---

## 1. Track A — Sternberg feature extraction

Applied the existing, unchanged PSWT/baseline definitions to Sternberg
derivatives. Mechanical coverage, no new feature family.

- `features_baseline.csv`: 58/64 subjects gained `sternberg_*` columns
  (band powers, aperiodic offset/slope) — limited by the pipeline's
  pre-existing rest-anchored iteration (a subject needs valid rest to be
  visited at all; this constraint predates Stage 2, unchanged here).
- Verified against real data: existing rest/MSIT/PSWT values for all 64
  subjects are byte-for-byte unchanged (diff max abs = 0.0) after the
  Sternberg columns were added.
- `reports/phase5_stage1_data_foundation.md`'s companion commit:
  `06b641b`.

## 2. Track B — richer multitaper TFA features + benchmark diagnostic

### What was built

- `pearl_features/tfa.py`: multitaper time-frequency-area features.
  Whole-recording windowed for MSIT (no reliable per-condition split found
  in real event markers — investigated and documented in
  `reports/phase5_stage2_plan_frozen.md` §3a, not assumed away). Trial/probe
  -locked for Sternberg encoding (`S 4`, verified fixed 3.02–3.03s duration
  across 5 real subjects) and retrieval (`S 12`, verified minimum
  0.41–0.61s gap across the same 5 subjects) periods — a genuine structural
  distinction in the classic Sternberg paradigm, not a demand-level label
  this dataset doesn't support.
- `pearl_features/tfa_pipeline.py`: orchestration, writes
  `features_tfa.csv` as a separate file (76 subjects: 72 MSIT, 69
  Sternberg) — never merged into `features_baseline.csv`, per the
  non-goal that Track B is a separately-budgeted family, not a
  replacement.
- `pearl_features/benchmark_diagnostic.py`: sanctioned, label-touching,
  hardcoded to evaluate `msit_tfa_*` against the published-benchmark
  reproduction question only — added to
  `test_features_labelblind.py`'s `SANCTIONED` set, locked by a
  signature-shape test (no parameter can redirect it to a different
  feature set or to `binary_risk_vs_none`).

### Two real bugs caught by real-data validation before trusting anything

1. **Silent zero due to missing normalization.** Absolute multitaper PSD
   magnitude in raw EEG units (~1e-12) rounded to 0.000000 at any
   reasonable print precision — not a computation bug, but a real design
   gap (the frozen plan said to reuse `relative_band_powers`'s
   total-power-normalized convention; the first implementation didn't).
2. **A 700x performance bug.** The aperiodic 1/f fit re-ran multitaper PSD
   on the *entire, un-windowed* recording (~600s, 152,185 samples)
   separately from the windowed band-area computation. DPSS taper cost
   grows very steeply with segment length: measured at **1589 seconds for
   one subject**. At 76 subjects this would have taken days. Fixed by
   reusing the windowed PSD batch's mean for the aperiodic fit too — same
   band values, **2.28 seconds per subject** after the fix. Locked in with
   a regression test asserting `psd_array_multitaper` is called exactly
   once per `windowed_tfa`/`epoch_locked_tfa` call.

A third, smaller design bug was caught before committing: the first
orchestration iterated `rest_included` (66 subjects), which needlessly
restricted MSIT feature computation to subjects who *also* had valid rest
data — inconsistent with the frozen plan's own stated intent to mirror
`phase3_benchmark_reproduction.md`'s MSIT-anchored population. Fixed to
iterate `msit_included | sternberg_included` directly (72/69 subjects,
independent of rest status).

### Benchmark diagnostic result — VERDICT: NOT_SIGNIFICANT

| | Value |
|---|---|
| Richer features (`msit_tfa_*`) | AUC 0.546, CI [0.459, 0.805], p=0.315 |
| Prior simple baseline | AUC 0.459 |
| Published benchmark | AUC 0.58 |

The point estimate moved up but is not statistically distinguishable from
the prior baseline or from chance. Full detail, including the finding that
FDR feature selection barely narrowed the 12-candidate set (mean 11.36
selected), is in `reports/phase5_stage2_benchmark_diagnostic.md`. **No
iteration followed this result** — per the frozen plan and `phase_3.md`
§10's rule against a second attempt after seeing a number.

---

## 3. Definition of done — all satisfied

- [x] Track A: Sternberg baseline features extracted for every
      Sternberg-included subject; PSWT unchanged (rest-only)
- [x] Track A: existing rest/MSIT feature values unchanged (regression-tested)
- [x] `reports/phase5_stage2_plan_frozen.md` written and frozen before any
      Track B feature was computed
- [x] Track B implemented with the condition-splitting question resolved
      from real data, both ways (MSIT: dropped; Sternberg: retained)
- [x] `benchmark_diagnostic` sanctioned, code-enforced, added to the
      label-blindness `SANCTIONED` set
- [x] Benchmark diagnostic run once; result reported regardless of outcome
- [x] No genotype-label result reported anywhere outside the one sanctioned,
      narrowly-scoped diagnostic
- [x] `pytest` green (273 passed); every existing Phase 1/2 test still passes
- [x] This checkpoint written

---

## 4. What this means for Stage 3 — options, not a decision

Per `phase_5_stage2.md`: Stage 3 (modeling) gets its own follow-up spec,
scoped from here, not pre-built against assumptions. Given what's actually
known now:

1. **The richer-feature lever did not pan out on the one thing it was
   tested against.** Track B's `msit_tfa_*` family does not show a
   validated improvement over the prior simple baseline on benchmark
   reproduction. If Stage 3 is scoped, it should not cite "Track B closes
   the benchmark gap" as justification — this diagnostic doesn't support
   that.
2. **Sternberg's encoding/retrieval TFA features are extracted but
   undiagnosed** — no published number exists to validate them against, so
   they carry the same epistemic status the original PSWT family had
   before Phase 3's positive controls: built, but not yet tested against
   anything. If Stage 3 wants to use them, that's new ground, not a
   continuation of a validated result.
3. **Stage 1's rest cohort is available (N=64, different subject set than
   the original) and untouched by Stage 2** — Stage 3's most defensible
   starting point, if it proceeds, is likely re-running Phase 3's exact
   original methodology (same declared model class, same CV, same
   reference lines) on Stage 1's corrected preprocessing, testing whether
   the reference-order/ICA fixes alone change anything — a cleaner,
   single-variable question than combining it with Track B's undiagnosed
   Sternberg features in the same attempt.
4. **A legitimate alternative is: stop here.** Two independent diagnostics
   (Phase 2's original confound gate, re-passed more cleanly in Stage 1;
   this stage's benchmark diagnostic) have not found evidence that richer
   engineering closes the gap to the published benchmark. Continuing to
   Stage 3 is a real, definable next step, not an obligation this report
   creates.

---

## 5. Artifacts

| Artifact | Path |
|---|---|
| Track B frozen plan | `reports/phase5_stage2_plan_frozen.md` |
| Benchmark diagnostic result | `reports/phase5_stage2_benchmark_diagnostic.md` |
| Sternberg baseline features | `data/derivatives/features/features_baseline.csv` (in place) |
| Track B TFA features | `data/derivatives/features/features_tfa.csv` (new, separate) |
| Track B run metadata | `data/derivatives/features/features_tfa_meta.json` |
