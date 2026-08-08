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
