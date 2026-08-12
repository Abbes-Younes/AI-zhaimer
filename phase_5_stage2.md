# Phase 5 Stage 2 — Feature Engineering

**Agent instructions. Read this whole file, and `phase_5.md`, before writing
any code.**

Stage 1 closed clean (`reports/phase5_stage1_data_foundation.md`): confound
gate PROCEEDs on the corrected preprocessing (QC-only AUC 0.509), rest cohort
is N=64 (same size as the original, five subjects swapped in each
direction), Sternberg is preprocessed and sitting on disk unused. No stop
condition fired. This document is the "follow-up spec" `phase_5.md` promised
once Stage 1's actual outcome was known.

**This file covers Stage 2 only: feature engineering.** No modeling of the
primary genotype target happens here — that is Stage 3, scoped in its own
follow-up spec once Stage 2's outcome is known, exactly as Stage 1 handed
off to this document. Do not pre-build Stage 3 code against assumptions
about what Stage 2 finds.

**Non-goals for this stage.**
- No fitting, evaluating, or reporting a model against
  `binary_risk_vs_none` (or any genotype framing). The one place this stage
  touches a label at all is a narrowly-scoped, explicitly diagnostic
  benchmark check (§2c) — never the primary target.
- No touching `reports/analysis_plan_frozen.md`, `reports/phase3_results.md`,
  `reports/phase4_final_report.md`, or any Phase 1–4 artifact. This stage
  writes its own frozen plan (§0) and its own reports.
- No recovering the 15 QC-excluded subjects by loosening thresholds — ruled
  out in `HANDOVER.md`'s deferred-item table as a methodology violation, not
  a sizing question. Not revisited here.
- No claim that richer features "fix" or "supersede" the Phase 2/3 PSWT and
  baseline families. They are declared here as an **additional**, separately
  budgeted family (§0), evaluated on their own terms.

---

## 0. Declarations — write and freeze before computing anything

Per this project's established discipline (`phase_1.md` §5, `phase_2.md`
§0, `phase_3.md` §0): declare design decisions before seeing their effect,
not after. Write these into a new frozen document,
`reports/phase5_stage2_plan_frozen.md`, before any Track B feature is
computed. Track A (§1) does not need this — it applies already-frozen Phase
2 definitions unchanged to new data, not a new decision.

### 0a. Why a new frozen plan, not an amendment to the original

`reports/analysis_plan_frozen.md`'s stopping rule (§6) caps the *original*
Phase 1–4 analysis at three feature families and requires "a written
amendment" for a fourth. Stage 2 is not that analysis — it is a new,
parallel effort on Stage 1's new cohort, exactly as `phase_5.md` frames the
whole of Phase 5. Reopening the original document would blur that
boundary. Instead: **this stage declares its own budget, in its own
document, honestly bounded** — not because the "new dataset" label is a
loophole around the original stopping rule, but because the discipline the
original rule protects (no family-shopping after seeing a result) matters
here too and deserves its own explicit statement, not a borrowed one.

**Stage 2's family budget: one new family, maximum.** The existing PSWT and
baseline-spectral definitions, unchanged, extended to Sternberg (Track A) do
not count against this — same declared features, new data coverage, not a
new family. The one new family is the richer task-EEG spectral family in
§2. If it does not clear its own bar (§2c), Track B is reported as a null
finding and no second new family is attempted without a written amendment to
`reports/phase5_stage2_plan_frozen.md` specifically.

### 0b. Scope of "richer": what Track B actually builds, decided now

Per `reports/benchmark_citation.md` and `reports/phase3_benchmark_reproduction.md`,
the published 0.58 (Li et al. 2025) used, on MSIT low-demand condition:
**multitaper time-frequency area (TFA) spectral features**, computed
**per experimental condition** (not whole-recording-averaged, which is what
this project's current baseline does), with **t-test + FDR feature
selection**, and an SVM classifier. This project's characterized gap
(`phase3_benchmark_reproduction.md`) is exactly these three things — richer
spectral features, per-condition splitting, and selection — not a pipeline
bug.

Track B builds, in this order:
1. **Multitaper time-frequency area features** (`scipy.signal` or `mne`'s
   multitaper PSD, DPSS tapers) per ROI channel, per band, replacing the
   current single relative-band-power number with an actual time-frequency
   area statistic — declare the taper bandwidth product and number of
   tapers now, not after looking at results.
2. **Per-condition splitting for MSIT and Sternberg** — *verify first,
   before assuming it's possible*: check `task-msit_events.tsv` /
   `task-sternberg_events.tsv` for the low/high-demand (MSIT) or
   load-level (Sternberg) condition markers the published paper's task
   design implies. If the condition structure isn't present or isn't
   reliably extractable from this dataset's actual event markers, say so
   plainly and drop per-condition splitting from Track B rather than
   fabricating a split — this is a real possible outcome, not a
   contingency to bury.
3. **t-test + FDR feature selection**, fit **inside the CV fold only** in
   §2c's diagnostic (same inside-the-fold discipline as every other
   selection step in this project, per `phase_3.md` §3a) — never fit on
   the full sample.

Applies to **MSIT and Sternberg only** (task-state data — the published
benchmark and the rationale for richer features are both task-specific; rest
already has its own purpose-built PSWT family and does not need a second
spectral family layered on).

### 0c. What Track B is validated against, and what it is not

Track B is validated **only** against the published benchmark reproduction
question — "does a richer feature family get this pipeline's MSIT
performance closer to the published 0.58 than the current 0.459 baseline
does?" — using the same nested-CV machinery, same permutation test, same
leakage checklist as `phase3_benchmark_reproduction.md`. This unavoidably
requires the genotype label (the benchmark IS a genotype-classification
number), so it is a **sanctioned, narrowly-scoped diagnostic**, structured
exactly like Phase 2's `confound_gate.py` — one specific label-touching
module, justified in code, added to `test_features_labelblind.py`'s
`SANCTIONED` set with a one-line reason, and never used to report a claim
about `binary_risk_vs_none` itself. Track B's result is a yes/no on "does
richer feature engineering close the reproduction gap," not a genotype
prediction result — that distinction must be explicit in the code, the
report, and this document.

**If Track B is later judged worth carrying into Stage 3's primary-target
modeling, that is Stage 3's decision to make explicitly, not something this
stage's diagnostic silently authorizes.**

---

## 1. Track A — Sternberg feature extraction (mechanical, low risk)

Extend `pearl_features.pipeline.run()`'s existing, unchanged PSWT and
baseline definitions to Sternberg derivatives from Stage 1. No new feature
family, no new declared parameters — this is coverage, not engineering.

- `pearl_features.cohort.per_task_cohort` already produces per-task
  inclusion; add a `sternberg_included` set alongside the existing
  `rest_included`/`msit_included`, following the same pattern
  (`pipeline.py` lines ~46–49).
- Sternberg has no eyes-closed window concept (that's rest-only) — baseline
  features on Sternberg follow the same path as the existing MSIT branch
  (`mne_read_msit`-style direct continuous read), not the rest epoching
  path. Generalize `mne_read_msit` to a task-agnostic reader, or add a
  parallel `mne_read_sternberg` — whichever keeps the rest-specific
  eyes-closed logic untouched and task-agnostic logic shared.
- PSWT features stay rest-only (unchanged from Phase 2 — the whole PSWT
  family is built on the rest recording's alpha cycle structure; Sternberg
  contributes to the baseline-spectral family only, same as MSIT does now).
- Output: `features_baseline.csv` gains Sternberg-prefixed columns
  (`sternberg_*`, mirroring the existing `msit_*` prefix convention) for
  every subject with an included Sternberg recording — no new file.

This can start as soon as this spec is committed — no separate checkpoint
needed, unlike Track B below.

---

## 2. Track B — richer task-EEG feature family — CHECKPOINT BEFORE STARTING

**This is real, multi-day engineering work (per `HANDOVER.md`'s own
sizing), not a mechanical extension. Confirm with the user before starting
implementation, even though this document defines the design — matching
`phase_5.md`'s own precedent of gating expensive/judgment-heavy steps
separately from the spec's overall approval.**

- [ ] Write and freeze `reports/phase5_stage2_plan_frozen.md` per §0
      (taper parameters, condition-splitting verification result, selection
      procedure) — before implementing anything in this section.
- [ ] Implement multitaper TFA feature extraction for MSIT and Sternberg
      ROI channels (§0b.1).
- [ ] Verify and implement (or explicitly drop, per §0b.2) per-condition
      splitting.
- [ ] Implement t-test+FDR selection, fold-internal only.
- [ ] Add the sanctioned diagnostic module (§0c) — name it
      `pearl_features.benchmark_diagnostic` to match the existing
      `confound_gate.py` pattern — enforce in code (not just document) that
      it only ever runs against the benchmark-reproduction question, the
      way `pearl_models.control_diagnostic.run_rung` enforces `target ==
      "sex"` in `phase_4.md` §0a. Add to `test_features_labelblind.py`'s
      `SANCTIONED` set with the one-line justification.
- [ ] Run the diagnostic once. Report the result — improved, unchanged, or
      worse relative to `phase3_benchmark_reproduction.md`'s 0.459 — in
      `reports/phase5_stage2_benchmark_diagnostic.md`, verdict-first, same
      structure as the Phase 3 report it's compared against.
- [ ] Stop. No iteration on taper parameters, selection thresholds, or ROI
      definition after seeing this number — that is exactly the pattern
      `phase_3.md` §10 names as the one thing that can turn a real finding
      into a worthless one.

---

## 3. Tests

- Track A: regression test that `sternberg_included` follows the same
  per-task-cohort logic as `rest_included`/`msit_included` (no
  task-specific special-casing beyond the eyes-closed-window exception,
  which is genuinely rest-only).
- Track A: `features_baseline.csv` gains `sternberg_*` columns without
  disturbing existing `rest_*`/`msit_*` columns for subjects unaffected by
  the change (regression-test the existing 64-subject rest/MSIT output is
  byte-for-byte unchanged where Sternberg doesn't apply).
- Track B: multitaper TFA feature values are deterministic given a fixed
  seed and match a hand-computed reference on a synthetic signal with known
  spectral content.
- Track B: the condition-splitting verification step is itself tested
  against the real `task-msit_events.tsv`/`task-sternberg_events.tsv`
  structure, not assumed.
- Track B: `t-test+FDR` selection is fit inside the fold only — assert a
  fold's selected-feature set can differ from the full-sample selection
  (same style as Phase 3's "scaler mean differs from full-data mean" test).
- Track B: `benchmark_diagnostic` raises if pointed at any target other
  than the benchmark-reproduction question (mirrors
  `test_control_diagnostic_target_locked` from Phase 4).
- Full existing Phase 1/2 test suite still green — this stage touches
  `pearl_features` only, `pearl_preproc` is untouched.

---

## 4. Definition of done (Stage 2)

- [ ] Track A: Sternberg baseline features extracted for every
      Sternberg-included subject; PSWT unchanged (rest-only)
- [ ] Track A: existing rest/MSIT feature values for the current 64-subject
      cohort unchanged (regression-tested)
- [ ] `reports/phase5_stage2_plan_frozen.md` written and frozen before any
      Track B feature is computed
- [ ] Track B implemented per §0b, with the condition-splitting question
      resolved from real data (verified, not assumed) either way
- [ ] `benchmark_diagnostic` sanctioned, code-enforced, added to the
      label-blindness test's `SANCTIONED` set
- [ ] Benchmark diagnostic run once; result reported regardless of outcome
      in `reports/phase5_stage2_benchmark_diagnostic.md`
- [ ] No genotype-label result reported anywhere in this stage
- [ ] `pytest` green; every existing Phase 1/2 test still passes
- [ ] A short written record, `reports/phase5_stage2_feature_engineering.md`,
      of what was built, what the benchmark diagnostic found, and an
      explicit recommendation for how Stage 3 should be scoped given the
      actual outcome — the same checkpoint discipline as Stage 1's report

---

## 5. Stop and escalate if

- the condition-splitting verification (§0b.2) finds the dataset cannot
  reliably support it — this changes Track B's design and should be
  reported before continuing, not silently worked around with an
  approximation
- the benchmark diagnostic (§2) requires touching, joining, or even
  glancing at `binary_risk_vs_none` outside `benchmark_diagnostic`'s
  code-enforced boundary — stop, that is the label-blindness boundary
  failing, not a modeling decision
- you find yourself wanting to retune Track B's parameters after seeing the
  benchmark diagnostic's result, or wanting to try a second new family in
  the same stage — this is `phase_3.md` §10's warning applying here with
  the same force; report the null and stop
- Track A's Sternberg extension reveals the same header-repair or
  triplet-validation class of issue seen in Stage 1 for more than a handful
  of subjects — investigate before treating it as routine

Report and wait. This stage exists to inform Stage 3's scope, the same way
Stage 1 informed this one.
