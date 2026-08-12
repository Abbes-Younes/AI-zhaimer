# Phase 5 Stage 3 — Versioned Modeling

**Agent instructions. Read this whole file, `phase_5.md`, and
`reports/phase5_stage2_feature_engineering.md` before writing any code.**

Stage 2 closed with `reports/phase5_stage2_benchmark_diagnostic.md`'s
`NOT_SIGNIFICANT` finding: Track B's richer MSIT features did not show a
validated improvement over the prior simple baseline. Per that report's
own §4 recommendation #3, Stage 3 tests **one variable at a time**: does
Stage 1's corrected preprocessing (reference-order fix, evidence-based ICA
`n_components`) change the primary genotype-classification result, using
the *exact same* modeling methodology Phase 3 already declared and ran?
Not a new analysis design — the same one, on new inputs.

**This is the only phase in Phase 5 that touches the primary target.** It
gets one honest attempt, exactly as `phase_3.md` did.

## 0. What's adopted unchanged from `phase_3.md`

Every declared decision in `reports/analysis_plan_frozen.md` (base +
Amendment 1 + Amendment 2) and `config/models.yaml` carries forward
**verbatim, unedited**: primary target (`binary_risk_vs_none`), CV scheme
(5-fold × 10 repeats, pooled OOF), model class (L2 logistic regression
primary, linear SVM secondary), the four reference lines, the Holm-corrected
secondary set, the permutation/bootstrap procedure, the leakage checklist.
`pearl_models.pipeline.run()` already implements this exact orchestration
end-to-end (positive controls → benchmark reproduction → nuisance-only →
primary + secondary → leakage → results report → delivery) — Stage 3 reuses
it directly, pointed at Stage 1's corrected preprocessing tree and Stage
1/2's regenerated `features_pswt.csv`/`features_baseline.csv`
(Sternberg-extended, but the primary comparison set is unchanged: PSWT
rest-only vs. nuisance-only, same as before).

**What's different: the inputs, not the method.** New preprocessing
(Stage 1) → new `qc_metrics.csv` → new rest cohort (N=64, five subjects
swapped vs. the original) → PSWT/baseline features re-extracted on that
cohort (already done in Stage 2 Track A). Everything downstream of that is
identical machinery.

## 0a. Track B is explicitly excluded from this run

`features_tfa.csv` (Track B's richer MSIT/Sternberg features) is **not**
part of this analysis. It did not clear its own benchmark-reproduction
diagnostic (`NOT_SIGNIFICANT`), and including it here would conflate two
variables (data quality + a new, undiagnosed feature family) in one attempt
— exactly what `reports/phase5_stage2_feature_engineering.md` §4 warned
against. If a future stage wants to test Track B against the primary
target, that is new, separately-declared scope, not folded in here.

## 0b. The original Phase 3/4 artifacts are never touched

`pearl_models.pipeline.run()` writes to fixed paths that are identical to
the original frozen Phase 3/4 outputs (`reports/phase3_*.md(+html)`,
`data/derivatives/models/*`). Per the same discipline established in Stage
1/2: **the original `data/derivatives/models/` was archived to
`data/derivatives/models_phase3to4_frozen/` before this stage ran anything.**
After the run, its freshly-written outputs are copied to
`phase5_stage3_*`-prefixed paths, and the original `reports/phase3_*.md`
files (git-tracked, untouched in the working tree beforehand) are restored
via `git restore`. Both dataset versions coexist afterward, clearly
labeled, exactly as `phase_5.md`'s top-level non-goals require.

## 1. Stop and escalate if

Identical triggers to `phase_3.md` §10, now applied to Stage 3's own run:

- positive control 1a (eyes-open vs eyes-closed) comes back below 0.80
- the permutation null is not centred on 0.5
- primary AUC exceeds 0.85 and the leakage checklist doesn't explain it
- benchmark reproduction on MSIT lands at chance (informational this time —
  Stage 2 already characterized this gap; still recorded)
- **the temptation to try a fourth feature family, a different target, or
  a different model class after seeing this result** — the same warning
  `phase_3.md` closes on, applying with the same force to this second
  attempt

## 2. Definition of done

- [ ] Original `data/derivatives/models/` archived before running anything
- [ ] `pearl_models.pipeline.run()` executed once under a new `run_id`
- [ ] Outputs copied to `phase5_stage3_*`-prefixed paths; originals restored
- [ ] Verdict-first results report,
      `reports/phase5_stage3_results.md`, comparing this run's primary
      number against Phase 3's original 0.474 explicitly
- [ ] `pytest` green
- [ ] Checkpoint written informing Stage 4's scope (or a decision to stop)
