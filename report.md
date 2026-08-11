# Project Status Report — AI-zhaimer / PEARL-Neuro (ds004796)

**Last updated:** 2026-08-11 (after Phase 4 close — project complete)
**Latest run:** `run_id 20260810T152236Z-d8ab867` (see `pearl/data/derivatives/models/_meta.json`); shipped model retrained on the corrected 18-feature set during Phase 4 Task D, same reported CV number
**Git:** merged to `master`; tag `v1.0-phase3-null` marks the commit that produced the reported primary result
**Test suite:** 241 passed (`pearl/`, was 228 at Phase 3 close, 190 at Phase 2 close, 144 at Phase 1 close, 91 at Phase 0.5 close)

---

## TL;DR

**The project is complete.** All four phases closed; a containerized,
correctly-positioned research tool is delivered alongside a validated null
result. Start with `pearl/reports/phase4_final_report.md` (client-facing) or
`HANDOVER.md` (if resuming/extending this work).

**Phase 0 / 0.5** are closed: 79/79 subjects reconciled, 0 blocking confounds,
Scope C (rest + MSIT) approved and downloaded.

**Phase 1** ran to completion and its own QC gate fired exactly as designed:
`Verdict: ESCALATE` at the subject level (56/79 survive). Fully investigated,
documented, and resolved by the scope decision in §6.1.

**Phase 2** closed clean: confound gate passed (QC-only AUC 0.545), 64-subject
cohort frozen, 20 PSWT + 16 baseline features extracted (18 PSWT effective —
see Phase 4), nothing fitted to labels.

**Phase 3** (`phase_3.md`) — the only phase that touches the primary
target — closed with **Verdict: NULL.** The primary analysis (PSWT
features on resting-state EEG vs. genetic risk group, N=64) scored
**AUC 0.474** (95% CI [0.266, 0.702], permutation p=0.577) — it does not
beat chance, and does not beat the nuisance-only reference line (0.523).
This is a clean, legitimate null: the positive control that validates the
feature pipeline itself (eyes-open vs eyes-closed) passed strongly
(AUC 0.830), so the pipeline is measuring real alpha waveform shape — but the
second positive control (sex classification, a genuinely detectable
cross-subject target) also landed at chance (AUC 0.486), so this null cannot
fully separate "no real genotype signal" from "features don't generalise
across subjects at all." A calibrated model was still shipped per the
delivery requirement, correctly positioned as a research artifact with
out-of-distribution refusal, not a usable predictor. See §7 for full detail
and §8 for what would be needed to answer the question properly.

**Not yet merged to `master`** — see §8.5 for the pending decision.

---

## 1. Phase 0 / 0.5 — summary (closed, condensed)

Full detail lives in git history (`0a6389d`) and the original `phase0_audit.md`;
kept short here since nothing changed this session.

| # | Question | Answer |
|---|---|---|
| 1 | Do the 31/26/22 client groups reconcile with genotypes? | ✅ 79/79 RECONCILED, 0 MISMATCH |
| 2 | What is sub-69? | ✅ Not one of the 192 genotyped participants — closed |
| 3 | Missing EEG runs / balanced? | ✅ sub-51 no Sternberg, sub-55 no rest, both verified against the listing; Fisher p=0.27, plausibly random |
| 4 | Confounded by demographics? | ✅ No `blocking`; `watch` on SES and BDI (covariates for Phase 2/3); age `clear` |
| 5 | Phase 1 download cost? | ✅ Scope C (rest+MSIT) recommended, 87.4 GB estimated, fit the 95 GB budget |

Verdict: **PROCEED**. Manifest (`phase1_manifest.csv`, 628 S3 keys) approved
and consumed by Phase 1.

---

## 2. Phase 1 — Acquisition, Preprocessing & QC

### 2.1 What was built

`pearl/src/pearl_preproc/` — full pipeline, streaming design (raw never fully
co-resident with derivatives):

- **Download** (`download.py`, `pipeline.py`): manifest-driven, per-subject
  streaming (download → preprocess → verify → delete raw), resumable, disk-guarded.
- **Preprocessing** (`preprocess.py`): BrainVision triplet validation → montage
  (standard_1005 + synthesized O9/O10) → average reference → 0.5 Hz zero-phase
  FIR high-pass → statistical bad-channel detection + interpolation → anti-alias
  + resample (500 Hz rest / 250 Hz MSIT, config-driven) → 50 Hz line-noise
  removal → ICA (extended infomax, 30 components, ICLabel-thresholded exclusion)
  → continuous derivative + ICA solution + full provenance sidecar.
- **QC** (`qc.py`, `report_qc.py`): fixed-threshold, label-blind classification
  per (subject, task) → frozen exclusion list → verdict-first standalone HTML
  report, with per-group exclusion counts computed **only after** the freeze.
- **Analysis plan** (`analysis_plan.py`): writes and freezes
  `reports/analysis_plan_frozen.md` before any feature exists.
- **Label blindness**: enforced and tested (`test_preproc_labelblind.py`) — the
  only sanctioned exception is `report_qc.py`'s post-freeze per-group count,
  exactly as `phase_1.md` §3 specifies.

### 2.2 The escalation, its root cause, and the fix

First full run: **45/79 subjects excluded, N=34** — tripping three of
`phase_1.md` §8's stop conditions at once (>5 excluded, <70 survive, 41% of
rest recordings show no alpha peak).

**Root cause, confirmed empirically, not assumed:** the PEARL-Neuro rest
recording is **one file** containing 4 minutes eyes-open followed by 6 minutes
eyes-closed (`data/raw_meta/task-rest_eeg.json`). Every Phase 0/0.5 planning
document promised an eyes-closed carve-out in Phase 1 processing — **it was
never implemented**. Individual alpha frequency (IAF) was instead estimated on
a blind `crop(tmax=120)` — the first 120 seconds, sitting entirely inside the
eyes-open block, where occipital alpha is Berger-blocked by design. The
pipeline then correctly, mechanically excluded subjects for "no alpha peak" —
a measurement-location bug, not a biological finding.

**Fix applied** (`preprocess.py: eyes_closed_window`, `select_iaf_excerpt`):
resolves the eyes-closed block from BrainVision stimulus markers (`S 10` end
of eyes-open → next `S 1` → `S 11`), handling every marker-pattern variant
found across all 77 rest recordings (missing sub-markers, missing end marker,
anomalous timing gaps, leading `New Segment/` annotations, recordings
starting mid-block). **Backfilled from existing derivatives — zero
re-download** (`backfill-iaf` CLI command rewrites only the `IAF` +
`IAFWindow` sidecar blocks, preserving the original blind-crop estimate under
an auditable `Backfill` history entry). No QC threshold was touched.

**Result:** alpha-driven exclusions dropped from 32 to 4 subjects.
Overall exclusions: **45 → 23. N: 34 → 56.**

### 2.3 Other fixes made during remediation

| Issue | Root cause | Fix |
|---|---|---|
| sub-52 had no rest derivative | **Not a download failure** (my first assumption, corrected by investigation) — its `.vhdr`/`.vmrk` headers still carry a pre-BIDS filename (`DataFile=Q5ER_rest.eeg`) while the sibling files on disk use the canonical BIDS name | `triplets.validate_triplet` now tolerates this **one specific, verified** discrepancy (canonical siblings exist AND the `.vmrk` is self-consistently stale) and repairs a temp header copy for MNE to read; originals never modified. Reprocessed locally, no network. |
| Occipital-bad-channels exclusion rule never fired, since the pipeline's first run | `qc.py freeze_exclusions` compared the bare task name (`"rest"`) against the config key (`"task-rest"`) — always False. Survived 124 tests because the test fixtures used the config spelling, not the real sidecar spelling | Extracted `_task_key()` normalizer, used consistently in both `classify_sidecar` and `freeze_exclusions`. Regression test added using the real spelling. |
| Fragile QC report logic | `report_qc.py` compared booleans against the literal string `"False"` — works only by accident of always reading from CSV | `_is_false`/`_is_true` helpers accept both real bools and CSV strings |
| "Frozen" exclusion list wasn't write-protected | `freeze_exclusions` overwrote `excluded_subjects.csv` unconditionally | Previous version now archived to `excluded_subjects.<timestamp>.csv` before each overwrite |
| Dead config keys | `exclusion.require_alpha` / `exclusion.max_fail_tasks` were never read (verified by grep) — `iaf.require_for_tasks` was already the live source of truth | Deleted; two sources of truth for one rule is worse than one |
| Undeclared runtime dependencies | `pearl/pyproject.toml` listed no `mne`/`mne-icalabel` despite the pipeline hard-requiring both | Declared (`mne>=1.6`, `mne-icalabel>=0.6`); confirmed `boto3` is *not* used — `download.py` uses `requests` against OpenNeuro's HTTPS endpoints |
| `backfill-iaf` ran outside a managed run | Sidecar `Backfill` provenance said `run_id: "unmanaged"` | Wired through `make_run_id`/`set_run_id` like every other mutating command |

Test suite grew **91 → 144** (Phase 0.5 → Phase 1 close), all green.

### 2.4 Final measured numbers

**Budget** (`reports/phase1_budget_actual.md`): **17.73 GB** measured
derivative total vs. the 30 GB gate — comfortable pass (well under the Phase
0.5 estimate of 40.93 GB, which double-counted epochs and ICA copies). Peak
raw on disk during streaming: 1.41 GB. Full-scope (including Sternberg) raw
is now affordable if ever wanted (§6).

**QC** (`reports/phase1_qc.html`, `data/derivatives/preproc/qc/qc_metrics.csv`):

| | Before remediation | After remediation |
|---|---|---|
| (subject, task) rows | 156 | 157 (sub-52 rest recovered) |
| Verdict breakdown | 8 pass / 98 warn / 50 fail | 11 pass / 120 warn / 26 fail |
| Subjects excluded | 45 | **23** |
| Subjects surviving | 34 | **56** |
| Alpha-driven exclusions | 32 | **4** |
| Bad-channel-driven exclusions | ~13 (masked by the occipital-rule bug) | **19** |

Per-group survivors (computed only after the freeze, per §3):

| Group | Total | Excluded | Survive |
|---|---|---|---|
| N | 31 | 9 | 22 |
| A_P_minus | 26 | 4 | 22 |
| A_P_plus | 22 | 10 | **12** |
| **Total** | **79** | **23** | **56** |

A_P_plus — already the smallest group (22) — loses 45% of its subjects.
Reported per §3's requirement to flag uneven attrition; **no threshold was
adjusted in response.**

**Verdict: ESCALATE** (`phase_1.md` §8): fewer than ~70 subjects survive.
The alpha-peak stop condition (§8, "substantial share show no alpha peak")
is now resolved — 4/78 (5%) lack an alpha peak, down from 41%. The
bad-channel-count condition is the one still open.

### 2.5 Definition of Done (`phase_1.md` §7) — all satisfied

- [x] `reports/phase1_budget_actual.md` written from measured durations before any download
- [x] All manifest files downloaded, verified, raw deleted per subject
- [x] Peak disk usage logged (1.41 GB) and under 30 GB
- [x] Continuous derivative exists for every non-excluded (subject, task)
- [x] Every derivative has a complete provenance sidecar
- [x] ICA solutions and excluded-component lists saved (157 files)
- [x] `qc_metrics.csv` complete (157 rows); `excluded_subjects.csv` frozen with reasons (23)
- [x] `reports/phase1_qc.html` opens standalone, leads with a verdict
- [x] Per-group exclusion counts reported (computed after freezing)
- [x] `reports/analysis_plan_frozen.md` written and committed
- [x] Label blindness test passes
- [x] `pytest` green (144); everything committed with `run_id` traceability (`20260808T234509Z-a3b8888`)

### 2.6 Deliberately left open (not bugs — decisions or out of current scope)

- **Estimator refinements not applied.** IAF local-max requirement and
  baseline-band correction were designed and pressure-tested but not shipped:
  on the now-correct eyes-closed data they'd move at most 1 subject (net, possibly
  negative), while the real remaining blocker is bad-channel counts, unrelated
  to alpha. Applying them anyway would be exactly the "tune until N looks
  better" pattern `phase_1.md` §2a exists to prevent.
- **Reference-order imperfection**, known, not fixed: average reference is
  applied before bad-channel detection/interpolation, so bad channels
  contaminate the reference for all other channels before they're caught.
  Second-order (most subjects have 0–3 bad channels of 127) but real. Fixing
  requires reprocessing all 79 subjects from raw — a ~46 GB re-download your
  current connection can't support; deferred by your explicit decision
  (2026-08-08).
- **`ica.n_components: 30` on a 127-channel montage** may be forcing an
  over-broad decomposition (ICLabel is trained on near-full-rank
  decompositions), plausibly explaining the 40–77% component-removal rates
  seen on some subjects. Not verifiable without raw data (ICA removal isn't
  invertible from the cleaned derivative). Same re-download dependency as above.
- **The `AUC ≈ 0.58` benchmark** named in `analysis_plan_frozen.md` as the
  reference point for the primary metric is uncited anywhere in the repo —
  should be traced to the actual PEARL-Neuro publication before it's leaned on.

---

## 3. Artifacts (Phase 1, all under `run_id 20260808T234509Z-a3b8888`)

| Artifact | Path | Content |
|---|---|---|
| Budget report | `pearl/reports/phase1_budget_actual.md` | measured 17.73 GB vs 30 GB gate |
| QC metrics | `pearl/data/derivatives/preproc/qc/qc_metrics.csv` | 157 rows, full per-(subject,task) metrics |
| Excluded subjects | `pearl/data/derivatives/preproc/qc/excluded_subjects.csv` | 23, frozen with reasons; prior versions archived alongside |
| QC report | `pearl/reports/phase1_qc.html` | standalone, verdict-first, per-group breakdown |
| Frozen analysis plan | `pearl/reports/analysis_plan_frozen.md` | CV scheme, primary target, metric, benchmark, stopping rule |
| Derivatives tree | `pearl/data/derivatives/preproc/sub-*/eeg/` | 157 continuous `.fif` + ICA solutions + provenance sidecars (BIDS-Derivatives layout) |
| Dataset description | `pearl/data/derivatives/preproc/dataset_description.json` | GeneratedBy, SourceDatasets, pipeline version |
| Run stamp | `pearl/data/derivatives/preproc/_meta.json` | `run_id 20260808T234509Z-a3b8888` |
| Pipeline config | `pearl/config/preproc.yaml` | every threshold, frozen before the run, label-free |

---

## 4. Reproduction

```bash
cd pearl
pip install -e ".[dev]"        # now correctly declares mne, mne-icalabel
pytest tests/ -q                # 144 passed
python -m pearl_preproc.cli run-all   # resume-skips all 79 (already processed); no re-download
```

Requires Python ≥ 3.10, MNE ≥ 1.6, mne-icalabel ≥ 0.6, network access to
OpenNeuro only if raw is missing. All data/caches on `D:` per the README.

---

## 5. The decision needed before Phase 2 — options, with numbers (historical — resolved, see §6.1)

> **Resolved 2026-08-09.** Adopted Option A + the rule change inside Option B
> (per-task exclusion, N=64), recorded as `Amendment 1` to
> `reports/analysis_plan_frozen.md`. Option C (the reference-order /
> ICA-`n_components` re-download) was deferred again — the confound gate
> (§6.2) found no evidence it's currently needed, so its priority stays low
> pending Phase 3 results. This section is kept verbatim below for the record
> of what was decided and why.

`phase_1.md` §8 reserves this call explicitly: *"fewer than ~70 subjects
survive ... needs re-scoping before features, not after. Report and wait."*
Three options, not mutually exclusive with future work:

**Option A — Accept N=56, proceed to Phase 2 now.**
Fastest path. The frozen primary target (`binary_risk_vs_none`, N vs
A_P_minus+A_P_plus) would run on a smaller-than-planned but still workable
sample. Per-group imbalance (A_P_plus at 12) should be reported as a limitation.

**Option B — Narrow exclusion to rest-only recordings.**
Currently a subject is excluded if *any* task fails QC; 9 of the 23 exclusions
are subjects with a clean rest recording undone only by a noisy MSIT run. The
frozen analysis plan's primary target is rest-based, so this is a legitimate
scope clarification, not a threshold retune. **Raises N to 64** — still under
70, still technically escalates, and the imbalance is worse under this option
(A_P_plus would lose more of its remaining subjects proportionally). Computed,
not applied.

**Option C — Authorize the ~46 GB re-download** to fix the reference-order
bug and re-evaluate the ICA `n_components=30` concern, which together might
recover some of the 19 bad-channel-driven exclusions. Requires a better
connection than the one available 2026-08-08; largest cost, most complete fix.

**My recommendation, if asked:** Option A now (fast, honest, already
defensible) with Option C revisited once you're on a connection that can carry
46 GB — worth doing before Phase 3 modeling regardless, since it also resolves
the ICA over-removal question, not just N.

**What I need from you to start Phase 2:** which option (or combination), and
confirmation of the primary target framing already frozen
(`binary_risk_vs_none`) — or a signal that it needs revisiting given the new N.

---

## 6. Phase 2 — Confound Gate & Pitch-Synchronous Feature Extraction

### 6.1 Scope decision (§0) — resolved

**Adopted: Option A + the rule change inside Option B.** The exclusion unit
changed from *subject* to *(subject, task)* — the grain `qc_metrics.csv`
already carries; only `pearl_preproc.qc.freeze_exclusions` collapsed it to
the subject. `pearl_features/cohort.py` simply doesn't apply that collapse.
**No QC threshold was touched** — same thresholds, different unit.

- Rest-based cohort: **N=64** (39 at-risk / 25 no-risk under
  `binary_risk_vs_none`) — recorded in `Amendment 1` as known before the rule
  was adopted, per the honesty requirement in `phase_2.md` §0a.
- **Primary target unchanged**: `binary_risk_vs_none`, still frozen.
- `binary_high_vs_rest` and `multiclass_3` **demoted to descriptive-only** —
  at 12–14 A_P_plus survivors they can't support a tested claim.
- **Power statement recorded now, before results exist:** at 39 vs 25 the
  study is underpowered to reliably distinguish a true AUC of 0.65 from the
  published 0.58.
- Bad-channel count and ICA-components-removed **join SES and BDI as
  declared Phase 3 covariates**, unconditionally.
- **Option C** (reference-order / ICA-`n_components` re-download) stays
  deferred — recorded, not acted on, and its priority was explicitly handed
  to the confound gate's result (§6.2), which came back clean.
- **Benchmark citation verified**: Li, Z.; Wang, H.; Song, J.; Gong, J.
  (2025). *Sensors*, 25(1), 52. DOI 10.3390/s25010052. Important caveat for
  Phase 3 reporting: the 0.58 comes from **task-state MSIT (low-demand
  condition)**, multitaper/TFAAT features, SVM — not resting-state and not
  PSR/PSWT. Since the source paper itself found task EEG outperforms
  resting-state EEG for this classification problem, 0.58 is, if anything, an
  *optimistic* reference point for this project's rest-based primary target.

Full detail: `pearl/reports/analysis_plan_frozen.md` (Amendment 1),
`pearl/reports/benchmark_citation.md`.

### 6.2 The gate (§1) — VERDICT: PROCEED

Ran before a single feature was computed, per `phase_2.md` §1's requirement.

| Test | Result |
|---|---|
| QC-only nested-CV classifier vs `binary_risk_vs_none` (subject-level stratified group 5-fold × 3 repeats, 1000 permutations, 2000-resample bootstrap) | **mean AUC 0.545**, 95% CI [0.435, 0.800], permutation p=0.35 |
| Verdict per the `phase_2.md` §1b table | **PROCEED** — preprocessing carries no detectable group information |
| Association tests (Kruskal-Wallis + BH-FDR), full N=79 cohort | `artifact_frac` borderline (p_fdr=0.011); all others n.s. after FDR |
| Association tests, N=64 surviving cohort | `artifact_frac` no longer survives FDR (p_fdr=0.056); all others n.s. |
| Exclusion status × group (Fisher's exact) | OR=1.15, p=0.83 — attrition did not land unevenly by group |

`artifact_frac`'s borderline full-cohort association is recorded for Phase 3
but does not change the gate's decision rule (§1b's classifier is the
decisive test, not §1a's per-metric tests) and disappears on the cohort
Phase 3 will actually use. Full report: `pearl/reports/phase2_confound_gate.md`.

### 6.3 Feature pipeline (§2–§8)

New package `pearl/src/pearl_features/` (label-blind except
`confound_gate.py`, the one sanctioned exception, same pattern as Phase 1's
`report_qc.py`):

- **§2 Epoching** (`epoching.py`): consumes Phase 1's `IAFWindow` sidecar
  (never re-derives eyes-closed timing), fixed-threshold artifact rejection.
- **§3 Cycle detection** (`cycles.py`): narrowband copy (IAF±2Hz, zero-phase
  FIR) for boundary detection, broadband signal for all shape measurement,
  positive-slope zero crossings, phase-locked boundary placement.
- **§4 PSR matrix** (`psr.py`): target period P = mode of cycle lengths, DFT
  resampling with Nyquist-bin zeroing (not filter-based — avoids boundary
  edge effects). `P ≥ 40` asserted per subject.
- **§5 PSWT** (`pswt.py`): polyphase/multiplexed decomposition (not comb
  wavelets — those lose perfect reconstruction at even P, and P≈50 hits that
  immediately), Daubechies-8, `mode="periodization"`.
- **§6 Features** (`features.py`, `config/features.yaml`): 20 declared
  waveform-shape features (harmonic amplitude profile ×5, harmonic/
  inter-harmonic ratio, cycle-to-cycle variability, period variability,
  waveform asymmetry — each as median+IQR), fixed 15-channel occipital-
  parietal ROI, fixed 200-cycle seeded subsampling per subject, the
  per-subject 50Hz-nearest harmonic index NaN'd out (verified not associated
  with group: χ² p=0.72 on real data).
- **§7 Baseline** (`baseline.py`): band power (delta/theta/alpha/beta/gamma),
  IAF, alpha peak height, 1/f offset/slope — computed on both rest and MSIT
  derivatives (16 features), the required comparison set the PSWT features
  must beat to justify their complexity.
- **§8 Outputs**: `pearl_features.pipeline.run()` orchestrates gate → cohort →
  per-subject extraction, atomic staging, single `run_id`.

**Run result:** 64/64 surviving subjects produced features (0 excluded), mean
14.5/15 ROI channels retained per subject (worst case 12/15). Feature CSVs
contain no group-label columns anywhere — the join happens in Phase 3.

Three real bugs surfaced only when running on actual EEG (every synthetic
test had passed): a PyWavelets periodization-mode reconstruction rounds an
odd cycle count up by one sample at deeper decomposition levels, desyncing
downstream shapes; the causal single-gap period estimate in phase-locking
could drift and permanently lock into half-rate cycle detection on noisy
real signal; and a channel with too few cycles crashed PSR construction
before the existing "drop this channel" check could run. All three fixed
with regression tests (n=190 now covers them).

### 6.4 §11 stop conditions — reviewed, none fired

QC-only AUC 0.545 (not >0.65); PSR/PSWT reconstruction tests pass; `P ≥ 40`
held for every subject; cycle rejection kept a mean 14.5/15 ROI channels per
subject; surviving N=64 matches the disclosed number exactly; harmonic-
exclusion index does not associate with group. Phase 2 completed without an
escalation.

### 6.5 Artifacts (Phase 2, under `run_id 20260809T222134Z-84a0543`)

| Artifact | Path | Content |
|---|---|---|
| Amendment 1 | `pearl/reports/analysis_plan_frozen.md` | appended, frozen section above it untouched |
| Benchmark citation | `pearl/reports/benchmark_citation.md` | verified, DOI, framing-mismatch caveat |
| Confound gate report | `pearl/reports/phase2_confound_gate.md` | verdict-first, QC-only AUC, association tests, real-data 50Hz-exclusion check |
| Per-task cohort | `pearl/data/derivatives/phase2/cohort_per_task.csv` | one row per (subject, task), included flag + reason |
| Feature config | `pearl/config/features.yaml` | 20 declared features, frozen before extraction |
| PSWT features | `pearl/data/derivatives/features/features_pswt.csv` | 64 subjects × 20 features, no labels |
| Baseline features | `pearl/data/derivatives/features/features_baseline.csv` | 64 subjects × 16 features, no labels |
| Feature dictionary | `pearl/data/derivatives/features/feature_dictionary.md` | every column: definition, units, provenance |
| Cycle stats | `pearl/data/derivatives/features/cycle_stats.csv` | usable duration, dropped channels, excluded harmonic index per subject |
| Run stamp | `pearl/data/derivatives/features/_meta.json` | `run_id`, git SHA, gate verdict |
| Implementation plan | `docs/superpowers/plans/2026-08-09-phase2-confound-gate-and-pswt-features.md` | full task-by-task record |

### 6.6 Reproduction

```bash
cd pearl
pip install -e ".[dev]"        # now also declares scikit-learn, PyWavelets, tabulate
pytest tests/ -q                # 190 passed
python -m pearl_features.cli    # re-runs gate + full feature pipeline; resume-safe
```

---

## 7. Phase 3 — Modelling, Validation & Delivery (historical note superseded, see §8)

> This section described what Phase 3 needed to do before it started; kept
> for the record. Phase 3 is now closed — see §8 for the actual results.

Phase 2 deliberately stopped short of any model: no accuracy numbers, no
touching the frozen primary target. Before Phase 3 modeling started, the plan
was:

1. Confirm the primary target and covariate set: `binary_risk_vs_none`, with
   SES, BDI, bad-channel count, and ICA-components-removed as covariates
   (Amendment 1).
2. Nested CV per the frozen plan: 5-fold × 3 repeats, subject-level,
   ≥1000-permutation test, 2000-resample bootstrap CI.
3. Three feature families, stopping rule already frozen: PSR/PSWT vs.
   baseline spectral. If neither beats ~0.58 at corrected p<0.05, report null.
4. Leakage tripwire: any result >~0.85 is a bug until proven otherwise.
5. Revisit Option C only if Phase 3 results are surprising in a direction the
   gate's clean pass doesn't explain.

(Two of these were revised by Amendment 2 before Phase 3 started — see §8.1.)

---

## 8. Phase 3 — Modelling, Validation & Delivery

### 8.1 Amendment 2 (§0) — written before any label was joined

- **CV variance fix**: 5×3 repeats → **5×10**, with out-of-fold predictions
  pooled per repeat (one AUC over all 64 subjects) then averaged across
  repeats — not per-fold averaging, which is both higher-variance and biased
  on ~13-subject test folds.
- **Declared model class**: L2-penalised logistic regression (primary, `C`
  tuned by grid search inside the inner fold only), linear SVM (secondary).
  Tree ensembles / GBMs / neural nets not permitted as primary.
- **Four reference lines declared**: chance (0.500), QC-only (0.545, Phase 2
  gate), nuisance-only (computed in §8.2), published benchmark (0.58, MSIT,
  not rest).
- **`artifact_frac` added to the nuisance set** per the QC-only gate's wide
  95% CI ([0.435, 0.800]) — "no evidence of contamination," never
  "contamination excluded."
- **Comparison set + correction**: primary = PSWT-on-rest vs. nuisance-only
  (one test). Secondary, Holm-corrected: baseline-rest, PSWT+baseline-rest,
  baseline-MSIT.
- **Power statement recorded in advance**: at 39 vs 25, expected 95% CI width
  ≈ ±0.13–0.15.

Full text: `reports/analysis_plan_frozen.md`, Amendment 2.

### 8.2 Positive controls (§1) — VERDICT: PROCEED_WITH_CAVEAT

Run before the hypothesis, exactly as the phase spec requires, using the same
CV machinery as the primary analysis:

| Control | AUC | 95% CI | p | Floor | Result |
|---|---|---|---|---|---|
| 1a — eyes-open vs eyes-closed (within-subject) | **0.830** | [0.710, 0.898] | 0.005 | 0.80 | **PASS** |
| 1b — sex classification (cross-subject) | **0.486** | [0.301, 0.745] | 0.627 | 0.65 | **FAIL** (chance) |

Interpretation per the pre-registered §1c table: high 1a + chance 1b means
*"features work but don't generalise across subjects; report the primary
null with that caveat."* Not a stop condition (only 1a<0.80 would be) — but
it means any primary null can't fully separate "no real genotype signal"
from "the feature pipeline doesn't generalise across subjects at all."

Full report: `reports/phase3_positive_controls.md`.

### 8.3 Benchmark reproduction (§2a) — VERDICT: AT_CHANCE, investigated

MSIT baseline spectral features vs. `risk_vs_none`: **AUC 0.459** (CI [0.252,
0.721], p=0.55, n=55) — does not approach the published 0.58. This is one of
`phase_3.md` §10's explicit stop-and-escalate conditions, so before
continuing, it was investigated properly rather than waved through:

1. **Data sanity** — no degenerate features, reasonable variance, class
   balance 33/22. No bug.
2. **Univariate signal, two ROIs** — neither the occipital-parietal ROI (used
   in the frozen features) nor a frontocentral ROI (the anatomically
   expected site for MSIT interference effects, computed as a one-off
   diagnostic) shows *any* feature with even marginal label association
   (p>0.16 and p>0.28 respectively; univariate AUCs 0.39–0.61, noise-level
   both times).
3. **Alternate classifier** — linear SVM scores *worse* (0.38) than logistic
   regression (0.459), ruling out classifier choice.

**Conclusion**: not a pipeline bug. This project's 7-feature ROI-averaged
band-power/1-f baseline is simply coarser than the published multitaper
time-frequency-area + per-condition + t-test-FDR-selected feature pipeline
(different cohort too). A characterized feature-engineering gap, confirmed
with you before continuing — it does not affect the primary PSWT-on-rest
analysis (different feature family, different task).

Full report + investigation: `reports/phase3_benchmark_reproduction.md`.

### 8.4 Nuisance-only line (§2b) — AUC 0.523

Age, sex, education, BDI, SES, bad-channel count, ICA-components-removed,
artifact_frac vs. `risk_vs_none`: **AUC 0.523** (CI [0.306, 0.735], p=0.395,
n=64) — chance-level, close to the QC-only line. This is the row every
feature model had to beat to demonstrate anything about EEG.

(A cohort-scope bug was caught and fixed here before trusting the number: the
first implementation used all 79 subjects with any QC/demographic data
instead of the frozen 64-subject rest cohort, giving an incomparable n=79
result. Fixed with a regression test before the real run.)

### 8.5 Primary analysis (§3) — VERDICT: NULL

One run, per the declared plan, against all four reference lines:

| Analysis | AUC | 95% CI | p |
|---|---|---|---|
| **PSWT features only (primary claim)** | **0.474** | [0.266, 0.702] | 0.577 |
| Features + nuisance | 0.517 | [0.305, 0.736] | 0.408 |
| Nuisance only | 0.523 | [0.306, 0.735] | 0.395 |

The PSWT feature model does not beat chance and does not beat nuisance-only —
no signal detected for `binary_risk_vs_none`.

**Secondary set (Holm-corrected)** — all null:

| Analysis | AUC | p (Holm) |
|---|---|---|
| Baseline features, rest | 0.375 | 1.0 |
| PSWT + baseline, rest | 0.513 | 1.0 |
| Baseline features, MSIT | 0.459 | 1.0 |

**Feature stability** (not single-fit importance, per §3b): 18 of 20 PSWT
features were selected in 100% of repeat×fold combinations, but two findings
temper that: `harmonic_amplitude_profile_h1_median`/`h1_iqr` were *never*
selected — they're tautologically constant (harmonic 1 normalised to itself
is exactly 1.0 for every cycle, a Phase 2 feature-definition artifact, not a
modelling failure). And `harmonic_amplitude_profile_h5_*`, despite 100%
selection, correlate strongly (r=0.81, 0.96) with recording duration among
the small subset of subjects where they're non-missing — a transparency
caveat on that pair's "selected" status, not a leakage bug (the leakage
checklist below is clean).

A real bug was caught before this ran: `dropna(how="any")` on the
PSWT+baseline combo matrix silently collapsed the cohort from 64 to 6
subjects, because the PSWT h5 columns are NaN by design for most subjects.
Fixed to let the CV harness's imputer handle it, exactly as the leakage
checklist exists to catch.

### 8.6 Leakage tripwire (§4) — all clear

- No subject appears in both train and test in any fold (re-derived and
  checked directly against the actual CV splits).
- Permutation null centred at **0.492** (within tolerance of 0.5) — closely
  matches the observed AUC of 0.474, confirming the null is structurally
  genuine, not an artifact of a leaking CV design.
- Scaling/imputation/selection fitted inside the fold only: structurally
  guaranteed by `cv.py`, not just asserted.
- No cycle-level rows leak into the subject-level matrix: features are
  aggregated to one row per subject before Phase 3 ever reads them.
- Feature-as-duration-proxy check: see the h5 finding in §8.5.

### 8.7 Results report (§5) — `reports/phase3_results.md`

Verdict-first, all 8 required sections: primary number + CI, all four
reference lines, positive control outcomes, benchmark reproduction outcome,
Holm-corrected secondary comparisons, feature stability, limitations (power,
QC-only CI width, rest-vs-task benchmark mismatch, deferred Phase 1
reference-order/ICA issues, A_P_plus attrition, the h5 duration confound),
and what would be needed to answer the question properly (larger cohort,
task EEG, Option C reprocessing, richer MSIT feature engineering). Also
rendered as self-contained `reports/phase3_results.html`.

### 8.8 Delivery (§6) — shipped, correctly positioned

- **`data/derivatives/models/model_final.joblib`**: trained on all 64
  subjects (evaluation already frozen — this fit is deployment-only, never
  re-evaluated as a performance number), calibrated
  (`CalibratedClassifierCV`, sigmoid).
- **Out-of-distribution refusal**: verified end-to-end — a subject whose QC
  metrics (bad-channel count, ICA-removed count, artifact fraction) fall
  outside the training cohort's observed range is refused with a reason,
  without the model ever being called.
- **`model_card.md`**: states, honestly, that CV-estimated AUC (0.474) does
  not exceed chance or the nuisance-only line — "shipped per project
  delivery requirements, not because it is fit for prediction." Every scored
  output carries the disclaimer: *"research pipeline output — a research
  score, not a risk assessment, screening result, or diagnosis."*
- Full provenance: `run_id`, git SHA, feature-config hash,
  `participants_tsv_sha256`, CV-estimated AUC+CI, training QC ranges.

### 8.9 §10 stop-condition review — all clear except the investigated one

| Condition | Status |
|---|---|
| Positive control 1a < 0.80 | Clear (0.830) |
| Permutation null not centred at 0.5 | Clear (0.492) |
| Primary AUC > 0.85 unexplained | Clear (0.474) |
| Benchmark reproduction at chance | **Fired** — investigated (§8.3), confirmed a characterized feature-richness gap, not a bug; did not affect the primary analysis |
| Temptation to try a 4th family / different target / different model after seeing a result | Not acted on |

### 8.10 Real bugs found during Phase 3 (all fixed, with regression tests)

| Bug | Root cause | Fix |
|---|---|---|
| Nuisance-only line used n=79 instead of the frozen 64-subject cohort | `load_nuisance()` sources from `participants.tsv`/`qc_metrics.csv`, which cover all 79 subjects; not gated through the feature CSVs like everything else | Restricted to `load_pswt_features().index`; regression test added |
| PSWT+baseline secondary analysis silently collapsed to 6 subjects | `dropna(how="any")` on a matrix containing PSWT's intentionally-NaN `h5` columns (53/64 subjects) | Removed the dropna; `cv.py`'s imputer already handles it inside each fold |
| `CalibratedClassifierCV.fit(groups=...)` crashed ("n_splits=5 > number of groups: 1") | sklearn doesn't route a bare `groups=` kwarg to the cv splitter without explicit metadata-routing config | Used plain `StratifiedKFold` for the final full-cohort fit (mathematically equivalent since every subject is a unique row there) |

### 8.11 Artifacts (Phase 3, under `run_id 20260810T152236Z-d8ab867`)

| Artifact | Path | Content |
|---|---|---|
| Amendment 2 | `pearl/reports/analysis_plan_frozen.md` | appended, everything above untouched |
| Positive controls report | `pearl/reports/phase3_positive_controls.md` | verdict-first, both controls, §1c interpretation |
| Benchmark reproduction report | `pearl/reports/phase3_benchmark_reproduction.md` | verdict + full investigation |
| Results report | `pearl/reports/phase3_results.md` (+`.html`) | verdict-first, all 8 required sections |
| Models config | `pearl/config/models.yaml` | CV settings, reference lines, declared before any label join |
| CV predictions | `pearl/data/derivatives/models/cv_predictions.csv` | out-of-fold probabilities, features-only + features+nuisance |
| CV metrics | `pearl/data/derivatives/models/cv_metrics.csv` | every analysis × every reference line |
| Feature stability | `pearl/data/derivatives/models/feature_stability.csv` | selection frequency + sign consistency per feature |
| Shipped model | `pearl/data/derivatives/models/model_final.joblib` | calibrated, trained on all 64 |
| Model card | `pearl/data/derivatives/models/model_card.md` | intended use, CV performance, limitations, OOD ranges |
| Run stamp | `pearl/data/derivatives/models/_meta.json` | `run_id`, git SHA, verdict |
| Implementation plan | `docs/superpowers/plans/2026-08-10-phase3-modeling-validation-delivery.md` | full task-by-task record |

### 8.12 Reproduction

```bash
cd pearl
pip install -e ".[dev]"        # now also declares scikit-learn (already had it), joblib (ships with sklearn)
pytest tests/ -q                # 228 passed
python -m pearl_models.cli      # re-runs the full Phase 3 pipeline; expensive (~1.5-2h at full precision)
```

### 8.13 Status: merged

Merged to `master` (fast-forward, `f5122b0`), tag `v1.0-phase3-null` marks
the commit that produced the reported number (`d8ab867`).

---

## 9. Phase 4 — Diagnostic Closeout, Packaging & Handover (project complete)

Phase 3 left one ambiguity (positive control 1b, sex classification, landed
at chance — did that mean the cohort has no detectable subject-level signal
at all, or that the PSWT feature family specifically doesn't carry it?) and
two documented feature-definition defects. Phase 4 resolved both, packaged
the tool, and produced the client deliverable and handover pack. **The
primary verdict is unchanged and frozen: NULL, AUC 0.474** — nothing in this
phase touched or could touch it.

### 9.1 Task A — control diagnostic ladder (§0): VERDICT resolved

Same CV machinery, same 64-subject cohort, **target = sex only, throughout**
— enforced in code: `pearl_models.control_diagnostic.run_rung` raises
`ValueError` if pointed at any target other than `"sex"`, not just
documented as a rule. All three declared rungs ran regardless of outcome:

| Rung | AUC | 95% CI | permutation p |
|---|---|---|---|
| 1 — baseline spectral (16 features) | 0.693 | [0.402, 0.829] | **0.013** |
| 2 — PSWT + baseline combined | 0.556 | [0.336, 0.764] | 0.265 |
| 3 — per-channel/zone, fresh computation | 0.685 | [0.418, 0.840] | **0.024** |

**Resolved:** rungs 1 and 3 are statistically significant (p<0.05); rung 2
(the combination) is not — adding PSWT features *diluted* rather than added
to a signal that spectral features alone and per-channel features alone
both detect. This resolves the ambiguity in favor of the more informative
reading: *"The pitch-synchronous feature family did not detect genotype
group, on a cohort where other EEG features do carry subject-level
information. This is a negative result for the method as applied here."*
Not "inconclusive" — a real negative result specific to PSWT.

A real self-caught bug preceded this conclusion: the initial "clearly above
chance" criterion was an unjustified CI-lower-bound threshold (>0.55) that
gave the wrong answer (`stopped_at: None`) despite two rungs having
permutation p<0.05. Replaced with the permutation p-value — the same
significance convention used everywhere else in this project — before
trusting the result. Full report: `reports/phase4_control_diagnostic.md`.

### 9.2 Task B — two feature-definition defects fixed (§1)

- **`harmonic_amplitude_profile_h1_median`/`h1_iqr` removed.** Harmonic 1
  normalised to itself is exactly 1.0/0.0 for every cycle, always — a
  tautological constant, not a real feature (confirmed: 0% selection
  frequency in Phase 3's own stability table). Declared PSWT feature count
  20 → **18**. Does not require re-running the primary CV (removing
  exactly-constant columns cannot change an L2 logistic regression's fit).
  `features_pswt.csv` regenerated by dropping the two columns directly.
- **`harmonic_amplitude_profile_h5_*` flagged, not removed.** NaN for 53/64
  subjects by design (the 50Hz-exclusion index working as intended);
  correlates with recording duration (r=0.81, 0.96) among the small
  non-missing subset — a usability caveat recorded in the feature
  dictionary, with a design lesson for any future phase (the exclusion
  should apply at the harmonic-profile level, not leave a mostly-empty
  fixed column).
- Added `assert_no_constant_features`/`assert_missingness_below_threshold`
  as permanent regression tests.

### 9.3 Task C — merge, hygiene, clean-clone reproducibility (§2)

- Tag `v1.0-phase3-null` on `d8ab867` (the exact commit that produced the
  reported Phase 3 number).
- **Dependencies pinned exactly** (`==`, not `>=`) in `pyproject.toml`,
  cross-checked against `pip freeze`.
- **Clean-clone test run for real**, not assumed: fresh `git clone` + fresh
  venv + pinned install + `pytest`. Without `pearl/data/`/`data/labels/`
  present (both intentionally gitignored), 4/237 tests fail with
  `FileNotFoundError` reading real derivative CSVs — expected, documented
  in `README.md`'s new Reproduction section, not a bug. With the derivative
  tree present (copied or regenerated via the four documented CLI
  commands), **237/237 pass**.
- `reports/provenance_chain.md`: one-page trace from
  `participants_tsv_sha256` through every phase `run_id` to the shipped
  model's own sha256.

### 9.4 Task D — packaged the tool (§3), verified for real

`Dockerfile`, `pearl_models.inference.score_bids_subject` (the single code
path both the new CLI `score` subcommand and the new stdlib-only thin API
call), `INSTALL.md`, `RUNBOOK.md`. **Built the image and ran the end-to-end
smoke test for real** against `sub-52` (raw BrainVision files retained on
disk from Phase 1's header-repair debugging — no re-download needed) —
not just written and assumed to work. Result: exit code 0, valid JSON with
the research-artefact disclaimer present, `status: "scored"`.

Three real bugs found only by actually running the container (all fixed,
with regression tests where applicable):

| Bug | Root cause | Fix |
|---|---|---|
| ICA labeling `ImportError` | `mne-icalabel`'s ICLabel backend needs `torch` or `onnxruntime`, present on the dev host by accident, never declared | Declared `onnxruntime==1.27.0` (lighter than `torch`, same result) |
| Latent `IndexError` in the ICLabel fallback path | Degenerate PSD with no bin ≥20 Hz — this fallback had never actually been exercised before this run | Fixed defensively, regression test added |
| Shipped model `ValueError` (20 vs 18 features) | The Task-11 model predated Task B's h1-column fix | Retrained the *deployment artifact only* (frozen CV number unchanged) on the corrected 18-feature set |

### 9.5 Task E — client final report (§4)

`reports/phase4_final_report.md` (+ `.html`) — verdict-first, 8 sections,
written for a non-specialist reader, not a retitled copy of the Phase 3
technical report. States plainly what was asked/delivered, the null with
CI and p-value in plain language, why the result is trustworthy (labels
verified 79/79, no confounds, confound gate before any feature, label-blind
pipeline, frozen plan, permutation null at chance, positive controls run),
the Task A resolution, what the null does/doesn't license, what a proper
answer would need, a deliverables index, and the known-defects annex.
**Flagged the French-translation question in the report's own header**
rather than assuming English is sufficient, per the client's classification
document having been in French.

### 9.6 Task F — handover pack (§5–6)

`HANDOVER.md`: repo map, phase-to-code relationships, frozen-decision table
with reasons, **deferred-item sizing** (Option C reprocessing, richer MSIT
feature engineering, Sternberg ingestion, recovering QC-excluded subjects —
each stated as new scope with a rough size, not assumed included), data
retention (what's on disk, what's deletable, what must be kept), and a
three-step "if you resume this project" reading order.

### 9.7 §10 stop-condition review — all clear

No diagnostic rung ran against `binary_risk_vs_none` (enforced in code).
Clean-clone failures matched exactly what the README documents. The
container's output always includes the disclaimer. No one proposed revising
the primary verdict on Task A's strength — it changed the *wording*
available for the null (negative vs. inconclusive), never the number.

### 9.8 Artifacts (Phase 4)

| Artifact | Path | Content |
|---|---|---|
| Control diagnostic report | `pearl/reports/phase4_control_diagnostic.md` | 3-rung ladder, decision table applied |
| Final client report | `pearl/reports/phase4_final_report.md` (+`.html`) | non-specialist, verdict-first |
| Provenance chain | `pearl/reports/provenance_chain.md` | data hash → shipped model |
| Handover | `HANDOVER.md` | repo map, deferred sizing, resume order |
| Install/Runbook | `pearl/INSTALL.md`, `pearl/RUNBOOK.md` | verified commands, real smoke-test record |
| Container | `pearl/Dockerfile` | builds; smoke-tested |
| Updated feature dictionary | `pearl/data/derivatives/features/feature_dictionary.md` | 18 declared features, defects annex |
| Retrained shipped model | `pearl/data/derivatives/models/model_final.joblib`, `provenance.json` | matches the corrected 18-feature pipeline |
| Tag | `v1.0-phase3-null` | the commit that produced the reported number |

### 9.9 Reproduction

```bash
cd pearl && pip install -e ".[dev]"    # pinned exactly; now also declares onnxruntime
pytest pearl/tests/ -q                  # 241 passed (requires pearl/data/ present — see README.md)
docker build -t pearl-models:latest -f pearl/Dockerfile .   # from repo root, not pearl/
```

### 9.10 Status: project complete, merged

Merged to `master`. This is the final entry in this report unless a Phase 5
is scoped — see `HANDOVER.md` for what that would cost.
