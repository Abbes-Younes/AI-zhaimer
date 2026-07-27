# AI-zhaimer

Predicting genetic Alzheimer's-risk group from T1-weighted structural MRI.

## 1. Project Goal

Classify subjects into genetic risk groups derived from APOE (ε4 allele) and PICALM
status, using features extracted from structural MRI (T1w) via FreeSurfer.

## 2. Cohort & Labels

Total N = 79 subjects, defined in `classification.pdf` (see `/reference/` once copied
into repo).

| Group  | Genetic definition                                  | N  |
|--------|------------------------------------------------------|----|
| N      | APOE ε3/ε3 (neutral), no PICALM risk                  | 31 |
| A+P-   | APOE ε4 carrier, no PICALM risk (simple risk)         | 26 |
| A+P+   | APOE ε4 carrier + PICALM risk (incl. 2x ε4/ε4 homoz.) | 22 |

Subject IDs per group are listed in `classification.pdf` and should be transcribed
into a `participants_labels.tsv` (or merged into the BIDS `participants.tsv`) early on.

### Classification tasks

1. **Binary — risk vs. no risk**: N (0) vs. A+P- + A+P+ combined (1)
2. **Binary — high vs. low/normal risk**: N + A+P- (0) vs. A+P+ (1)
3. **Multiclass (3-class)**: N (0) / A+P- (1) / A+P+ (2)

N=79 is small — model choice, validation strategy, and honest uncertainty reporting
matter more here than raw model complexity.

## 3. Data

- Format: raw NIfTI (`.nii`/`.nii.gz`), organized in BIDS.
- Modality: T1-weighted structural MRI (assume no `dwi/` or `func/` unless found).
- **Status: data not yet located/gathered.** First engineering task is finding/mounting
  the actual BIDS dataset and confirming subject ID overlap with the 79 labeled subjects.

## 4. Pipeline Overview

```
raw BIDS T1w
      │
      ▼
FreeSurfer recon-all (per subject)
      │
      ▼
Feature extraction (cortical thickness, surface area,
subcortical volumes — aseg/aparc stats)
      │
      ▼
Feature matrix (subjects × features) + labels + confounds (age, sex, site, ICV)
      │
      ▼
QC & exploratory analysis
      │
      ▼
Modeling (nested CV, regularized linear baselines)
      │
      ▼
Evaluation + interpretation (which regions drive group separation)
```

## 5. Repo Structure (proposed)

```
AI-zhaimer/
├── PLAN.md                     (this file)
├── data/
│   ├── bids/                   (raw NIfTI, BIDS layout — likely gitignored/symlinked)
│   └── labels/
│       └── participants_labels.tsv
├── reference/
│   └── classification.pdf      (group/label definitions, copied from project)
├── freesurfer/
│   ├── subjects/                (FreeSurfer SUBJECTS_DIR output)
│   └── run_recon_all.sh
├── src/
│   ├── extract_features.py     (aseg/aparc stats -> tidy feature table via nibabel/nilearn)
│   ├── build_dataset.py        (merge features + labels + confounds)
│   ├── eda.py                  (class balance, distributions, confound checks)
│   ├── models/
│   │   ├── train.py            (nested CV, logistic regression/SVM w/ L1/L2)
│   │   └── evaluate.py         (AUC/F1/accuracy + CIs, permutation testing)
│   └── interpret.py            (feature importance -> brain region mapping)
├── notebooks/                  (exploratory work)
├── results/
│   ├── features/
│   ├── models/
│   └── figures/
├── environment.yml / requirements.txt
└── README.md
```

## 6. Step-by-Step Plan

### Phase 0 — Setup
- [ ] Init repo, environment (Python: nibabel, nilearn, scikit-learn, pandas,
      statsmodels; FreeSurfer installed & `SUBJECTS_DIR` configured)
- [ ] Copy `classification.pdf` into `reference/`, transcribe subject IDs + labels
      into `data/labels/participants_labels.tsv`

### Phase 1 — Data acquisition
- [ ] Locate/mount the BIDS T1w dataset
- [ ] Confirm subject ID overlap between BIDS dataset and the 79 labeled subjects
      (flag missing/extra subjects)
- [ ] Basic image QC (motion, coverage, artifacts) before committing to full recon-all runs

### Phase 2 — FreeSurfer processing
- [ ] Run `recon-all` per subject (this is the long pole — hours/subject; consider
      parallelizing / running a small pilot batch first)
- [ ] QC FreeSurfer outputs (surface reconstruction quality — Euler number, visual spot checks)
- [ ] Extract aseg (subcortical volumes) and aparc (cortical thickness, surface area,
      parcellation stats) into tidy tables

### Phase 3 — Dataset assembly
- [ ] Merge imaging features + labels + confounds (age, sex, site if multi-site, ICV
      for volume normalization)
- [ ] Handle missing data / excluded subjects
- [ ] Final feature matrix: subjects × features, versioned in `results/features/`

### Phase 4 — Exploratory analysis
- [ ] Class balance per task
- [ ] Feature distributions by group
- [ ] Check for confound leakage (e.g., age differing systematically across groups)

### Phase 5 — Modeling
- [ ] Baselines: L1/L2-regularized logistic regression, linear SVM
- [ ] Nested cross-validation (outer loop for evaluation, inner loop for hyperparameter
      selection) — critical given N=79
- [ ] Run for all three task definitions separately
- [ ] Optionally: compare against a simple ICV/age/sex-only model to establish a
      confound-only baseline

### Phase 6 — Evaluation
- [ ] Accuracy, AUC, F1 with confidence intervals (bootstrap given small N)
- [ ] Permutation testing for statistical significance vs. chance
- [ ] Compare performance across the three task formulations

### Phase 7 — Interpretation
- [ ] Feature importance / model coefficients
- [ ] Map back to brain regions (which cortical/subcortical measures drive separation)
- [ ] Sanity-check against known APOE/PICALM neuroimaging literature

## 7. Key Risks / Watch-outs

- **Small N (79)**: high variance in performance estimates — nested CV + reporting
  CIs is not optional here.
- **Class imbalance**: especially task 2 (22 vs. 57).
- **Confound leakage**: age/sex/site can correlate with genetic group by cohort
  design — must be checked and possibly regressed out or included as covariates.
- **FreeSurfer runtime**: recon-all is slow; plan compute/time budget accordingly.
- **Multiple comparisons**: running 3 task formulations + region-wise interpretation
  increases risk of spurious findings — correct for this in reporting.

## 8. Next Immediate Action

Once this repo is initialized in Claude Code: locate the actual BIDS dataset, confirm
subject ID coverage against the 79 labeled subjects, and stand up the FreeSurfer
environment before writing any modeling code.