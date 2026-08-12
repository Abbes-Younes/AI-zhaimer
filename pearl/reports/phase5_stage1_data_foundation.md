# Phase 5 Stage 1 — Data Foundation: Checkpoint Report

**Verdict: PROCEED to Stage 2 scoping.** No `phase_5.md` §4 stop condition
fired. This is a checkpoint, not a decision to start Stage 2 — Stage 2
(feature engineering, modeling) is scoped in a separate, follow-up spec, per
`phase_5.md`'s own explicit staging rule.

The frozen Phase 3 NULL result (`reports/phase3_results.md`, AUC 0.474,
tag `v1.0-phase3-null`) is unchanged, unedited, and not superseded by
anything in this report. Everything below describes a **new, parallel**
dataset version, evaluated on its own terms.

---

## 1. What changed

### 1a. Reference-order fix (§0a)

`process_subject_task` reordered so bad-channel detection/interpolation now
runs on the original FCz-referenced signal, with average referencing moved
to after interpolation — the original order let a bad channel's noise
contaminate the average reference (and the bad-channel-detection statistics
themselves) before it was identified as bad. Implemented, tested
(`tests/test_preproc_reference_order.py`), smoke-tested on real data before
the full re-run.

### 1b. ICA `n_components` re-evaluation (§0b)

Evaluated `n_components=30` (fixed) against `n_components=0.99`
(explained-variance selection) on the 10 subjects with the most interpolated
channels. Result: `0.99` lowered the mean ICA-removed fraction from 0.260 to
0.212 (~19% relative), improving 7/10 subjects, with the largest gains on
the highest-bad-channel-count subjects — consistent with the fixed-30
decomposition not scaling to actual post-interpolation signal rank.
**Decision: adopted `n_components=0.99`.** Full evidence:
`reports/phase5_ica_component_evaluation.md`.

### 1c. Sternberg task ingestion (§0c)

Manifest extended to rest+msit+sternberg (Scope A, previously rejected in
Phase 0.5 on a co-resident-storage assumption that Phase 1's proven
streaming design invalidates). Measured budget: **25.08 GB** derivative
total vs. the 30 GB gate — pass. `config/preproc.yaml` sampling rate for
`task-sternberg` set to 250 Hz (task condition, same reasoning as MSIT).
Full figures: `reports/phase5_budget_actual.md`.

### 1d. Two corrupted raw headers found and fixed (not in the original §0
list — discovered during the full re-run)

`sub-29` and `sub-57`'s sternberg `.vhdr`/`.vmrk` files carry genuine
upstream typos (a dropped character, a stray extra dot) in their
`DataFile`/`MarkerFile` fields — verified against the correctly-named
canonical sibling files already present on disk. Extended
`pearl_preproc.triplets.validate_triplet`'s existing header-discrepancy
tolerance (previously scoped to one pattern, the sub-52 stale-pre-BIDS-name
case) with a second, narrowly-verified rule: both declared filenames must be
a small (edit-distance ≤2) typo of the canonical sibling names, or it still
raises. Original raw files untouched; the repair applies only to a
temp header copy MNE reads. Regression tests added
(`tests/test_preproc_triplets.py`), including one confirming the existing
"reject an unrelated/wrong pairing" safety test still holds.

---

## 2. Full re-run (§1)

Ran `pearl_preproc.cli run-all` for all three tasks under the corrected
reference order and `n_components=0.99`, under new `run_id`s
(`20260811T124718Z-01eb64b` / `20260811T223003Z-01eb64b`, plus a small
managed follow-up `20260812T004819Z-01eb64b` for the sub-29/sub-57 fix).

**The original Phase 1–3 derivative tree was archived, not overwritten**,
before this run started: `data/derivatives/preproc_phase1to3_frozen/`
(verified: 79 subjects, 157 sidecars, original `run_id
20260808T234509Z-a3b8888` — matches `report.md` exactly). `PREPROC_DIR` is a
single mutable path in the current architecture (not run_id-namespaced), so
this archival step was necessary to honor the plan's "original tree never
modified or deleted" constraint — worth carrying forward as an explicit step
for any future re-run, since nothing in the code enforces it automatically.
The same precaution was applied to `data/derivatives/phase2/` and
`data/derivatives/features/` (archived to `*_phase1to4_frozen/`) before the
Phase 2 re-run in §3 below, for the same reason.

**A related, more serious gotcha was caught before committing anything**:
several `reports/*.md` paths are hardcoded, phase-scoped, and shared by the
same code this stage re-invokes. Running the existing `pearl_preproc.cli
run-all` and `pearl_features.cli` entry points for Stage 1 silently
overwrote three files in place: `reports/phase1_budget_actual.md` (Phase 1's
own historical budget record — Stage 1's real figures already have their own
report, `reports/phase5_budget_actual.md`), `reports/phase2_confound_gate.md`
(Phase 2's original gate result, referenced by `report.md` and by Phase 3's
declared QC-only reference line), and — most seriously —
**`reports/analysis_plan_frozen.md`, the one document `CLAUDE.md` says must
never be edited in place**: the run silently regenerated it from its
un-amended base template, dropping the already-committed Amendment 1 and
Amendment 2 blocks from the working tree. All three were still only
uncommitted working-tree diffs (never pushed to a commit), so nothing was
lost from git history — but this was caught and fixed *before* this report
or any commit, not after. Fix: `analysis_plan_frozen.md` and
`phase1_budget_actual.md` were restored to their committed originals
untouched; `phase2_confound_gate.md`'s original was likewise restored, and
its Stage 1 replacement content saved separately as
`reports/phase5_stage1_confound_gate.md` (§3 below). **This is a real,
unfixed code gap** — none of these write paths currently check whether
they're running inside a Stage-1-style parallel re-run before overwriting a
phase-scoped report — worth fixing in the code (not just worked around
manually) before any future re-run of this kind.

### Phase 1 subject-level QC (all 3 tasks, `report_qc.py`'s own gate)

| | Original (rest+msit only) | Stage 1 (rest+msit+sternberg) |
|---|---|---|
| Subjects excluded | 23 | 22 |
| Subjects surviving | 56 | 57 |
| Verdict | ESCALATE (<70 survive) | ESCALATE (<70 survive) |

Both escalate on the same subject-level threshold, as expected — this
is the same gate that fired in the original Phase 1 run and was resolved
then (and is resolved the same way here, see §3) by using the per-task
cohort rule for the actual rest-based primary target, not the
all-tasks-considered subject-level count.

---

## 3. Phase 2 re-run + confound gate re-check (§1, Task 6)

Ran `pearl_features.cli` against the new preprocessing.

### Confound gate — VERDICT: PROCEED

| | Original | Stage 1 |
|---|---|---|
| QC-only classifier AUC | 0.545 | **0.509** |
| 95% CI | [0.435, 0.800] | [0.416, 0.769] |
| Permutation p | 0.35 | 0.4845 |

Comfortably clear of the 0.65 stop threshold — no evidence the corrected
preprocessing introduced group-identifiable structure. Full report:
`reports/phase5_stage1_confound_gate.md` (Phase 2's original result is
preserved, unedited, at `reports/phase2_confound_gate.md` — see the note in
§2 above on why this is a separate file rather than an in-place update).

### New cohort N vs. original 64

**New N = 64 — identical count, but not the identical subject set.**

- Dropped (survived originally, not now): `sub-07, sub-23, sub-44, sub-49,
  sub-72`
- Added (excluded originally, survives now): `sub-02, sub-09, sub-12,
  sub-45, sub-70`

This is a real, honest finding, not a discrepancy to explain away: the
reference-order and ICA fixes changed per-subject bad-channel/artifact
metrics enough to shift which specific subjects clear the same fixed
thresholds, while the total happened to land on the same number. Per-group
(genotype) breakdown was not computed here — that requires the label join,
which stays out of scope for a label-blind Stage 1 checkpoint; it belongs
in Stage 2's scoping once modeling is actually authorized.

---

## 4. §4 stop conditions — reviewed, none fired

| Condition | Status |
|---|---|
| Re-run confound gate QC-only AUC > 0.65 | Clear (0.509) |
| Sternberg-inclusive budget exceeds available disk/bandwidth | Clear (25.08 GB measured vs. 30 GB gate) |
| New surviving cohort smaller than original 64 | Clear (64 = 64, though not the same 64 — see §3) |
| More than a handful of Sternberg triplets fail validation | Clear (2 found, both a verified typo pattern, both fixed) |

---

## 5. Recommendation for Stage 2 scoping

**N did not grow, and the specific surviving cohort changed by 5 subjects
in each direction.** This is a materially different, but not larger, dataset
than the one Phase 3 evaluated. Two honest framings for whoever scopes
Stage 2:

1. **Proceed to Stage 2 as planned.** The confound gate passed more cleanly
   than before (0.509 vs. 0.545), the reference-order bug is a genuine,
   independently-justified correctness fix regardless of its effect on N,
   and Sternberg is now available as a third feature source Phase 3 never
   had. A same-size-but-different cohort is a legitimate basis for a second,
   clearly-labeled attempt — it is not the same data re-analyzed, so this
   does not read as "keep re-trying until N looks better."
2. **Flag for the record:** since N didn't grow, the power argument for
   expecting a materially different result from Phase 3 rests entirely on
   the preprocessing-quality fixes and the new Sternberg feature source, not
   on sample size. Stage 2's scope should say explicitly which of those it's
   testing (or both), so a second null is as interpretable as Phase 3's was.

No code should be pre-built against assumptions about what Stage 2 will find
— this report exists to hand a real decision to whoever scopes Stage 2, not
to make it here.

---

## 6. Definition of done — all satisfied

- [x] Reference-order fix implemented and tested
- [x] ICA `n_components` evaluated with real comparison numbers; decision
      documented (`0.99`, evidence-based)
- [x] Sternberg added to the manifest, budget re-measured before downloading
- [x] Full three-task Phase 1 re-run under new `run_id`s; original tree
      archived, untouched
- [x] Phase 2 feature extraction re-run on the new preprocessing
- [x] Phase 2 confound gate re-run and passed (PROCEED, AUC 0.509)
- [x] New cohort N reported and compared honestly to the original 64
- [x] `pytest` green (257 passed)
- [x] This checkpoint written

---

## 7. Artifacts

| Artifact | Path |
|---|---|
| ICA evaluation | `reports/phase5_ica_component_evaluation.md` |
| Budget report | `reports/phase5_budget_actual.md` |
| Confound gate report (Stage 1) | `reports/phase5_stage1_confound_gate.md` |
| Confound gate report (original, preserved unedited) | `reports/phase2_confound_gate.md` |
| New Phase 1 QC report | `reports/phase1_qc.html` (regenerated in place) |
| Original Phase 1–3 derivatives | `data/derivatives/preproc_phase1to3_frozen/` |
| Original Phase 2–4 features | `data/derivatives/phase2_phase1to4_frozen/`, `data/derivatives/features_phase1to4_frozen/` |
| New Stage 1 preprocessing | `data/derivatives/preproc/` |
| New Stage 1 features | `data/derivatives/features/` |
