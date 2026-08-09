# Phase 2 Analysis Plan (FROZEN)

**Status: FROZEN.** Written before any feature extraction, per phase_1.md §5.
Do not change after features exist. Any change requires a written amendment
signed off by the client.

## 1. Cross-validation scheme

- **Subject-level stratified group k-fold**, k = **5**, repeats = **3**.
- Stratification on the primary target labels; group = subject (no leakage
  across recordings of the same subject).
- **Nested CV** for any hyperparameter selection: the inner loop runs the same
  5-fold scheme on the training fold only; outer-loop scores are reported.
- Random seeds fixed in code (numpy `Generator(seed=...)`) and recorded with
  each run.

## 2. Primary target

- **`binary_risk_vs_none`** (31 at-risk vs 48 control — best balanced, largest
  contrast).
- `A_P_plus` and `A_P_minus` are explicitly **secondary** framings; they are
  reported only as context, and no decision is made from them. Testing all
  three and reporting the best would be p-hacking; the plan names one primary
  target now.

## 3. Primary metric

- **ROC AUC** (subject-level), mean across the k×repeats folds.
- **Permutation test**: ≥ **1000** permutations of the primary labels within
  the CV structure; p = fraction of permutations with mean AUC ≥ observed.
- **Bootstrap CI**: **2000** resamples of subject-level AUCs (stratified by
  group), reported as a 95% percentile interval.

## 4. Benchmark and leakage tripwire

- **Reference point: published AUC ≈ 0.58** on this dataset (prior literature).
- **Tripwire: any result > ~0.85 is treated as a bug until proven otherwise.**
- Debugging checklist (run in order, before believing the result):
  1. Check subject leakage: any subject appearing in both train and test
     (duplicate subject_id, recording-level splits by mistake).
  2. Check label leakage: features computed with group labels in scope
     (thresholds chosen per-group, ICA/epoch counts informed by labels).
  3. Check train/test contamination inside feature pipelines (global scaling,
     PCA or imputation fit on the full sample).
  4. Re-run with labels permuted — AUC must fall to chance; if not, the
     pipeline has a fixed random-state bug or leakage.
  5. Inspect the 10 highest-contribution features per fold for sanity.

## 5. Covariate handling

- **SES and BDI carried as covariates** in every model (Phase 0.5 `watch`
  flags in the 3-class framing).
- Age: confirmed clear in Phase 0.5 but **reported regardless** (not used to
  select features).
- Covariates are never used to exclude subjects post hoc.

## 6. Stopping rule

- **Three feature families maximum**: (1) PSR cycle-shape, (2) PSWT
  harmonic/temporal, (3) spectral/ERP baseline.
- If no family beats the ~0.58 benchmark at permutation p < 0.05 (corrected
  across the three families), the result is **reported as null** — no further
  families are tried without a written amendment.

## 7. Data contract (consumed as given)

- `data/derivatives/preproc/qc/excluded_subjects.csv` — exclusion list, frozen.
- `data/derivatives/preproc/sub-XX/eeg/*_desc-preproc_eeg.fif` + sidecars —
  the only data source; raw data must never be revisited.
- IAF and the 5th-harmonic-collision flag per subject from `qc_metrics.csv`;
  harmonic bins flagged as colliding with the treated line-noise band are
  excluded from PSWT features.

---

## Amendment 1 — 2026-08-09

**Status:** committed. Appends to, does not rewrite, the frozen plan above.

### Exclusion unit changed: subject → (subject, task)

Per-task exclusion is the correct rule independent of the N it yields:
excluding a subject from a rest-based primary analysis because their MSIT
recording was noisy is a category error, not a stricter standard. The frozen
primary target is rest-based; the exclusion unit is now `(subject, task)`,
which was already the grain of `qc_metrics.csv` — only
`pearl_preproc.qc.freeze_exclusions` collapsed it to the subject. Phase 2
does not apply that collapse (see `pearl_features/cohort.py`); no QC
threshold changed, only the unit the existing thresholds are applied to.

**Disclosure:** the resulting rest-cohort N (**64**, split 39 at-risk / 25
no-risk under `binary_risk_vs_none`) was known before this rule was adopted —
it happens to equal the subject-level N of 64 already reported in Phase 1.
The rule is adopted because it is the correct unit of analysis, not because
of the N — but that N was visible when the decision was made, and this
sentence records that fact so the choice cannot later be read as blind to
its effect.

### Primary target: unchanged

`binary_risk_vs_none` remains the frozen primary target. Changing it because N
moved is exactly the failure the freeze exists to prevent.

### Secondary framings demoted to descriptive-only

`binary_high_vs_rest` and `multiclass_3` are demoted to **descriptive
reporting only**. At the A_P_plus survivor count under the per-task rule
(12–14) they cannot support a tested claim. Phase 3 reports their descriptive
statistics (group sizes, feature-wise summary stats); it must not compute a
p-value or claim a result for either framing.

### Power statement (written now, before results exist)

At 39 vs 25 (rest-cohort per-task N, `binary_risk_vs_none`), the study is
underpowered to reliably distinguish a true AUC of 0.65 from the published
0.58. This is a known limitation stated in advance so it cannot be read as an
excuse after results exist.

### Carry-forward covariates (phase_2.md §1c)

Bad-channel count and ICA-components-removed join SES and BDI as declared
covariates for Phase 3, regardless of the confound-gate verdict in
`reports/phase2_confound_gate.md`.

### Benchmark citation status

See `reports/benchmark_citation.md` — status: **VERIFIED**. Li, Z.; Wang, H.;
Song, J.; Gong, J. (2025). *Sensors*, 25(1), 52. DOI: 10.3390/s25010052. The
0.58 AUC comes from **task-state MSIT (low-demand condition), multitaper/TFAAT
features, SVM** — not resting-state and not the PSR/PSWT feature family. Since
the source paper itself found task EEG outperforms resting-state EEG for this
classification problem, 0.58 is, if anything, an optimistic reference point
for this project's rest-based primary target — note this asymmetry when
reporting Phase 3 results against the benchmark, do not present it as a
matched comparison.
