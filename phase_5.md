# Phase 5 — Closing the Gap to SOTA: Data Foundation (Stage 1)

**Agent instructions. Read this whole file before writing any code.**

Phase 4 closed the project with a rigorous, frozen null (AUC 0.474) and a
correctly-positioned tool. The client has now asked for a genuine attempt to
close the gap to the published state of the art (AUC ≈ 0.58, Li et al. 2025,
same dataset) and, if possible, exceed it. This is **new, explicitly
authorized scope** — not a re-run or revision of Phase 3. The frozen NULL
result in `reports/phase3_results.md` is never edited, never superseded,
never treated as wrong. Phase 5 is a separate, additional, clearly-labeled
effort answering a different question: *can a more thorough attempt, using
what Phases 1–4 revealed, do better on this data?*

**This file covers Stage 1 only: the data foundation** (reference-order fix,
ICA `n_components` re-evaluation, Sternberg task ingestion, full Phase 1→2
re-run, confound-gate re-check). Stages 2–4 (feature engineering, versioned
modeling, delivery) are scoped in a follow-up spec once Stage 1's actual
outcome (does N grow? does anything measurably change?) is known — do not
pre-build Stage 2+ code against assumptions about Stage 1's result.

**Non-goals for this phase.** No feature extraction beyond what Phase 2
already does (re-run unchanged, on the corrected preprocessing). No
modeling. No touching `reports/phase3_results.md`, `reports/
phase4_final_report.md`, or any Phase 3/4 artifact. No claim, anywhere,
that this new preprocessing run "corrects" or "improves on" Phase
1–3 — it produces a **new, parallel dataset version**, evaluated on its own
terms, alongside the untouched original.

---

## 0. What's actually changing, and why

Two specific, previously-deferred issues, both named explicitly in
`phase_1.md` §2.6 and `phase_2.md` §0c/§0d, and confirmed by Phase 2's
confound gate to show *no current evidence of being necessary* — but never
definitively ruled out, because ruling them out requires the raw
re-download that wasn't affordable until now:

### 0a. Reference-order bug

`pearl_preproc.preprocess.process_subject_task` currently computes the
average reference (`raw.set_eeg_reference("average", ...)`, line ~454)
**before** bad-channel detection and interpolation (line ~468–471). This
means every bad channel's noise is mixed into the average-reference signal
before it's identified as bad — contaminating every other channel's
referenced signal, and *also* contaminating the bad-channel-detection
statistics themselves (a channel's variance/correlation-to-neighbours is
computed on already-contaminated data).

**Fix:** reorder so bad-channel detection and interpolation happen on data
still in its original hardware reference (`FCz`, confirmed via
`_vhdr_reference`), and average-referencing happens only after
interpolation, over the now-clean channel set:

```
1. Read raw + montage                              (unchanged)
2. High-pass 0.5 Hz zero-phase FIR                  (unchanged — still needed
                                                      before bad-channel
                                                      detection per phase_1.md
                                                      §2, DC-coupling reason)
3. Detect bad channels + interpolate                (MOVED UP — now runs on
                                                      FCz-referenced data,
                                                      not average-referenced)
4. Set average reference over the clean channel set  (MOVED DOWN)
5. Anti-alias + resample                            (unchanged)
6. ...rest of the pipeline unchanged
```

Everything else in `process_subject_task` — line-noise removal, ICA, IAF
estimation, artifact annotation — stays exactly as Phase 1 specified.

### 0b. ICA `n_components` re-evaluation

`config/preproc.yaml`'s `ica.n_components: 30` is currently fixed regardless
of how many channels survive bad-channel interpolation per subject.
ICLabel is trained on near-full-rank decompositions; forcing exactly 30
components on a 127-channel montage (of which a variable number are
interpolated, hence not independent contributors of new variance) is a
plausible cause of the 40–77% ICA removal rates observed in Phase 1.

**Evaluation procedure (not a predetermined fix — decide from evidence):**

1. Run ICA with `n_components=30` (current, unchanged) and with
   `n_components` set to explained-variance-based selection
   (`n_components=0.99`, i.e. enough components to explain 99% of variance)
   on a representative subset of subjects (at least the 10 subjects with the
   most interpolated channels — the cases most likely to be affected).
2. Compare, for each subject: number of components fit, ICA-removed
   fraction, and the QC verdict that would result.
3. **Choose the configuration whose removal-rate distribution is closer to
   the fixed conservative expectation** (a handful of clearly-artifactual
   components, not a third-to-most of the decomposition) — write the
   comparison numbers into the amendment, and pick based on them, not on
   which number looks nicer.
4. If neither configuration meaningfully changes the removal-rate
   distribution, say so plainly and keep `n_components=30` (the existing,
   already-justified default) rather than changing it without evidence.

### 0c. Sternberg task ingestion

A third task, same hardware/reference/sampling setup as rest and MSIT
(`data/raw_meta/task-sternberg_eeg.json`: 1000 Hz native, `FCz` reference,
50 Hz mains) — Phase 1 explicitly proved the streaming download design
makes this affordable (`phase_1.md` §0d) without ever using it.

- Extend `pearl_audit.download_plan`'s manifest generation to the existing
  `A_full_eeg` scope (already coded, already includes `sternberg` in
  `_observed_tasks()`'s fallback list — verify this against the live
  OpenNeuro listing rather than assuming the fallback is accurate) — or a
  new scope that is rest+msit+sternberg specifically if `A_full_eeg`
  differs from that. Emit a fresh `phase1_manifest.csv` covering all three
  tasks, re-run the budget report
  (`pearl_preproc.budget`) with the added task before downloading anything,
  same discipline as Phase 1 §0.
- Add `task-sternberg` sampling rate to `config/preproc.yaml`'s
  `sampling_rates_hz` — Sternberg is a task (not the alpha-focused rest
  recording), so unless there's a specific reason otherwise, follow Phase
  1's own precedent: MSIT (also a task, no cycle-level shape analysis
  needed) uses 250 Hz. Use 250 Hz for Sternberg for the same stated reason,
  and record it explicitly rather than silently copying the number.
- `raw_paths_for`/`process_subject_task` already take `task` as a parameter
  — verify no rest/MSIT-specific assumption is hardcoded before assuming
  Sternberg "just works" through the existing pipeline.

---

## 1. Full re-run, new run_id, confound gate re-check

- Re-run Phase 1 (`pearl_preproc.cli run-all`) for all three tasks under
  the corrected reference order and (if changed) ICA settings, producing a
  **new derivative tree under a new `run_id`**. Do not overwrite or delete
  the original Phase 1–3 derivative tree — both must coexist, addressable
  by `run_id`, exactly as the atomic-staging convention already guarantees.
- Re-run Phase 2 feature extraction (`pearl_features.cli`) on the new
  preprocessing, unchanged in method (same PSR/PSWT/baseline definitions) —
  Stage 1 changes *inputs* to Phase 2, not Phase 2 itself.
- **Re-run the Phase 2 confound gate on the new preprocessing before
  trusting anything downstream of it.** A changed preprocessing pipeline is
  not entitled to inherit the original run's clean gate pass — it must
  clear the same QC-only-classifier bar again, on its own data. If it
  doesn't (QC-only AUC > 0.65), this is the same stop condition Phase 2
  defined, and it applies here with the same force.
- Freeze the new cohort (per-task exclusion rule, unchanged from Amendment
  1) and report the resulting N against the original 64 — growth, shrinkage,
  or no change are all legitimate outcomes; report whichever actually
  happened.

---

## 2. Tests

- Regression test: the reference-order fix produces a materially different
  average-reference signal than the old order, on a synthetic multi-channel
  fixture with one injected bad channel (assert the average reference
  differs when the bad channel is included pre-interpolation vs.
  post-interpolation).
- ICA `n_components` comparison is captured in a reproducible script/report,
  not just an interactive session — findings must be re-derivable.
- Sternberg triplet validation reuses `pearl_preproc.triplets.validate_triplet`
  unchanged — add a regression test confirming it accepts a Sternberg
  triplet with no task-specific special-casing required.
- Full existing Phase 1/2 test suites re-run against the new code paths
  (the reference-order fix touches `process_subject_task` directly) —
  every existing Phase 1 test must still pass; if any test encoded the old
  (buggy) ordering as expected behaviour, fix the test, not the code.

---

## 3. Definition of done (Stage 1)

- [ ] Reference-order fix implemented and tested
- [ ] ICA `n_components` evaluated with real comparison numbers recorded;
      decision made from evidence, documented either way
- [ ] Sternberg added to the manifest, budget re-measured before downloading
- [ ] Full three-task Phase 1 re-run under a new `run_id`, original tree
      untouched
- [ ] Phase 2 feature extraction re-run on the new preprocessing
- [ ] Phase 2 confound gate re-run and passed (or stopped, per §4) on the
      new preprocessing
- [ ] New cohort N reported and compared honestly to the original 64
- [ ] `pytest` green; every Phase 1/2 regression test still passes
- [ ] A short written record (`reports/phase5_stage1_data_foundation.md`)
      of what changed, what was measured, and the resulting N — the
      checkpoint the plan requires before Stage 2 is scoped

---

## 4. Stop and escalate if

- the re-run confound gate's QC-only AUC exceeds 0.65 (same threshold,
  same meaning as Phase 2 §11) — the new preprocessing must not be trusted
  for any downstream feature work until this is resolved
- the measured Sternberg-inclusive budget exceeds the disk/bandwidth
  available (re-measure, don't assume Phase 1's estimate still holds)
- the reference-order fix or ICA re-evaluation produces a **smaller**
  surviving cohort than the original 64 — report and wait rather than
  silently accepting a worse dataset than the one already frozen
- more than a handful of Sternberg triplets are incomplete or fail
  validation in a way retry doesn't fix

Report and wait. This stage exists to inform Stage 2's scope, not to be
rushed through on the way to it.
