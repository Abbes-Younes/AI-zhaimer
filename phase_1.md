# Phase 1 — Acquisition, Preprocessing & QC

**Agent instructions. Read this whole file before writing any code.**

Phase 0.5 closed cleanly: 79/79 reconciled, no blocking confounds, artifacts
atomic and stamped, 91 tests green. Phase 1 turns the approved manifest into a
clean, QC'd, **label-blind** derivatives tree that Phase 2 (PSR/PSWT feature
extraction) can consume without ever revisiting raw data.

**Non-goals for this phase.** No feature extraction. No models. No looking at
group labels. If you find yourself computing a group difference, you have left
Phase 1.

---

## 0. Before anything: the budget is wrong, and fixing it changes the plan

The Phase 0.5 plan costs Scope C at **87.4 GB** (46.47 raw + 40.93 derivatives)
against 95 GB usable — 7.6 GB of headroom on an estimate built from soft
assumptions. That is too tight to start. Two corrections make it comfortable.

### 0a. Raw and derivatives never need to coexist

The 87.4 GB figure assumes the whole raw download sits on disk alongside the
whole derivative tree. It doesn't have to. Process **subject-by-subject**:

```
for each subject in manifest:
    download raw (3 BrainVision files per task)   ~590 MB
    preprocess -> write derivative
    verify derivative
    delete raw
```

Peak raw-on-disk becomes one or two subjects (~1.2 GB with a lookahead buffer),
not 46.47 GB. Keep a `--keep-raw` flag for debugging single subjects, defaulting
off.

### 0b. The derivative estimate double-counts

The Phase 0.5 model assumed `epoched = preprocessed × 1.5` and
`ICA ≈ preprocessed`. Both are avoidable:

- **An ICA *solution* is a mixing/unmixing matrix plus metadata — kilobytes, not
  gigabytes.** Only ICA-*cleaned data* is data-sized, and that is your
  preprocessed output, already counted. Save the solution (`.fif` ICA object),
  not a second copy of the data.
- **Epochs are a cheap, deterministic function of the continuous derivative.**
  Regenerate them in Phase 2 rather than storing them. Epoching policy will
  change once you see features; storing epochs now guarantees a rewrite.

So the derivative tree is essentially *one continuous preprocessed file per
subject per task*, plus small sidecars.

### 0c. Recompute the budget for real

Do not carry my arithmetic forward. Measure it:

```
continuous_bytes ≈ n_channels × duration_s × target_sfreq × 4 bytes (float32)
```

Derive `duration_s` per subject per task from the actual `.eeg` byte sizes in
`size_survey.csv` and the native rate in the sidecars (1000 Hz). Emit
`reports/phase1_budget_actual.md` with the measured figures before downloading
anything, and compare against the Phase 0.5 estimate. **If the measured total
exceeds 30 GB, stop and report** — that would mean the duration model is wrong
and something needs rethinking.

### 0d. Consequence worth noting

Under streaming, raw size stops being the binding constraint. **Sternberg
becomes affordable** — 75.87 GB of raw across all three tasks still only ever
touches disk ~590 MB at a time. Do not add it to this phase; prove the pipeline
on rest + MSIT first. But record in the budget report that Scope A is now
reachable, so the decision can be revisited cheaply in Phase 2.

---

## 1. Download engine

Manifest-driven, resumable, verified, idempotent.

- Read `phase1_manifest.csv` (628 keys). **Never re-derive the file list** —
  the manifest is the contract from Phase 0.5.
- **Verify BrainVision triplets.** Every recording is `.eeg` + `.vhdr` + `.vmrk`.
  A `.vhdr` without its `.eeg` is a silent corruption. Assert all three are
  present per (subject, task) before processing, and that the `.vhdr` `DataFile`
  and `MarkerFile` fields point at files you actually have.
- **Verify sizes against the manifest** after each download; mismatch → retry
  once, then quarantine the subject and continue. Log to
  `logs/download_log.jsonl` with URL, bytes, SHA-256, duration, and outcome.
- **Resumable and restartable.** Bandwidth from Tunis to S3 will drop mid-run.
  A re-invocation must skip completed subjects by checking for a valid
  derivative, not by keeping in-memory state.
- Use `aws s3 cp --no-sign-request`. Parallelise across subjects with a small
  worker count (2–4); more will not help and complicates disk accounting.
- Hard disk guard before each subject: abort if free space on `D:` < 20 GB.

---

## 2. Preprocessing — read this section twice

Standard EEG preprocessing recipes are built for spectral and ERP analysis. This
project's feature family is **waveform shape** (the PSR/PSWT approach), and
several standard steps actively destroy waveform shape. The defaults are wrong
here.

### 2a. Label blindness (enforced, not aspirational)

The preprocessing module **must not import, load, or receive group labels**.
Add a test asserting that `pearl_preproc` has no import path to
`client_groups.yaml`, `cohort_definition.csv`, or the genotype columns. Every
rejection threshold is fixed in config before the run and applied uniformly.

Rationale: any subjective or adaptive cleaning that sees labels can bias epoch
counts per group and manufacture a result. This is the most likely way this
project produces a false positive.

### 2b. Sampling rate: 500 Hz for rest, 250 Hz for MSIT

The Phase 0.5 plan assumed 250 Hz throughout. For the resting-state data that is
too coarse.

Cycle-by-cycle analysis needs enough samples per alpha cycle to locate zero
crossings and to make the DFT-based period resampling in §5.2.2 of the thesis
chapter meaningful. At 250 Hz a 10 Hz cycle is 25 samples — the PSR target
period `P` would be 25, giving ~12 usable harmonic bins and coarse boundary
placement. At 500 Hz you get 50 samples per cycle and boundary precision
improves proportionally.

Use **500 Hz for `task-rest`** (where the alpha work happens) and **250 Hz for
`task-msit`** (spectral/ERP work, no cycle-level shape analysis). Record both in
config; do not hardcode.

### 2c. Line noise is 50 Hz — and it collides with the alpha 5th harmonic

The data is Polish, so mains is 50 Hz. Two consequences:

1. Do not use a 60 Hz default anywhere.
2. **The 5th harmonic of a 10 Hz alpha rhythm sits at exactly 50 Hz.** A wide
   notch filter will carve a hole in the very harmonic series the PSWT features
   measure, and will do so differently for subjects whose individual alpha
   frequency is 9.8 vs 10.4 Hz — i.e. it introduces a subject-dependent artifact
   into a subject-level classifier.

Mitigation, in order of preference: spectral-interpolation line removal
(ZapLine / `mne.preprocessing` equivalents) rather than a notch; failing that, a
narrow (≤1 Hz) notch. **Either way, record each subject's individual alpha
frequency and flag any subject whose 5th harmonic falls within the treated
band.** Phase 2 must be able to exclude that harmonic bin from features. Write
the flag into the QC table.

### 2d. Filtering policy

- High-pass: FIR, zero-phase, **0.5 Hz or lower**. IIR high-pass at higher
  cutoffs visibly distorts waveform asymmetry, which is the signal.
- Low-pass: anti-alias only, ahead of resampling. No aggressive smoothing.
- **Never narrowband-filter the signal you measure shape on.** In Phase 2 the
  pattern is: detect cycle boundaries on an alpha-narrowband copy, then apply
  those boundaries to the broadband signal. Phase 1's job is to preserve a
  broadband signal clean enough for that to work.

Write the full filter specification (type, order, cutoffs, phase, window) into
the derivative sidecar JSON for every file.

### 2e. Reference

Waveform-shape features are strongly reference-dependent. Pick one scheme,
apply it uniformly, document it: **average reference** is the defensible default
for 128 channels. Record the original reference from the sidecars. Do not let
the reference vary by subject.

### 2f. ICA policy

ICA alters waveform morphology, so use it conservatively:

- Fit on a 1 Hz high-passed copy (standard practice — ICA fits poorly on
  0.5 Hz data), then **apply the solution to the 0.5 Hz data**.
- Remove only clearly artifactual components: EOG, ECG, and high-confidence
  muscle. Use automated labelling (ICLabel or equivalent) with a fixed
  probability threshold from config — no per-subject eyeballing, which would
  break label blindness in spirit.
- **Save the ICA solution and the list of excluded components per subject** as
  QC output. If Phase 2 finds shape features behaving oddly, the first
  hypothesis to test is over-aggressive component removal, and you need the
  audit trail to test it.
- Log the count of removed components per subject; an outlier there is a QC flag.

### 2g. Bad channels

Detect by fixed statistical criteria (flat, high-variance, low correlation to
neighbours), interpolate, and **record the count and identity per subject**. A
subject with many interpolated channels in occipital/parietal sites is a
candidate for exclusion, since that is exactly where alpha lives.

---

## 3. QC report — a Phase 1 deliverable in its own right

Emit `reports/phase1_qc.html` (self-contained, verdict-first, same conventions
as the Phase 0 report) plus `derivatives/qc/qc_metrics.csv` with one row per
(subject, task):

| Metric | Why |
|---|---|
| Recording duration, final sample count | catches truncation |
| Bad channels: count + names | exclusion candidate flag |
| ICA components removed: count + labels | over-cleaning detector |
| Line-noise power before/after at 50 Hz | did removal work |
| **Individual alpha frequency (IAF)** | Phase 2 needs it; also a QC signal |
| **Alpha power / 1-f-corrected alpha peak height** | subjects with no alpha peak cannot support cycle analysis |
| Proportion of data marked as artifact | uniformity check |
| 5th-harmonic-collides-with-notch flag | §2c |
| Overall pass / warn / fail | fixed thresholds from config |

Two things this table must support:

- **An exclusion list built on QC grounds only, computed before labels are ever
  joined.** Write it to `derivatives/qc/excluded_subjects.csv` with a reason per
  subject. Phase 2 consumes it as given.
- **A per-group exclusion count computed only *after* the exclusion list is
  frozen**, purely to report whether QC exclusions landed unevenly. If they did,
  that is a finding for the report, not a reason to revise the thresholds.

Expected starting n: 79 for MSIT, 78 for rest (sub-55 has no rest data). Any
further loss is QC attrition and must be explained subject by subject.

---

## 4. Derivatives layout

Follow BIDS-Derivatives so the tree is self-describing:

```
data/derivatives/preproc/
  dataset_description.json      # GeneratedBy, SourceDatasets, version
  sub-XX/eeg/
    sub-XX_task-rest_desc-preproc_eeg.fif
    sub-XX_task-rest_desc-preproc_eeg.json    # full provenance
    sub-XX_task-rest_desc-ica_components.fif
  qc/
    qc_metrics.csv
    excluded_subjects.csv
```

Every sidecar JSON carries: source file SHA-256, filter spec, resample rate,
reference, line-noise method, ICA components removed, bad channels interpolated,
`run_id`, git SHA, and the `participants_tsv_sha256` fingerprint from Phase 0.5.
A derivative that cannot name the raw file and the code version that produced it
is not reproducible.

Keep the Phase 0.5 atomic-staging convention: write to `.tmp-<run_id>/`, swap on
success, refuse to mix `run_id`s.

---

## 5. Freeze the analysis plan before Phase 2 opens

This is the deliverable that protects the whole project. Write
`reports/analysis_plan_frozen.md`, commit it, and **do not change it after
features exist**. It must specify:

- **CV scheme:** subject-level stratified group k-fold, nested for any
  hyperparameter selection. State k and the repeat count.
- **Primary target:** one of the three framings, chosen now, with the others
  explicitly labelled secondary. My recommendation is `binary_risk_vs_none`
  (31 vs 48) — best balanced, largest contrast. Testing all three and reporting
  the best is p-hacking.
- **Primary metric:** ROC AUC, with the permutation-test procedure (≥1000
  permutations of labels within the CV structure) and the bootstrap CI method
  specified in advance.
- **Benchmark:** the published AUC of ~0.58 on this dataset. State it as the
  reference point, and state the leakage tripwire: **any result above ~0.85 is
  treated as a bug until proven otherwise**, and the debugging checklist is
  written now, before the temptation exists.
- **Covariate handling:** SES and BDI carried as covariates per the Phase 0.5
  `watch` flags; age confirmed clear but reported regardless.
- **Stopping rule:** how many feature families get tried before the result is
  reported as null. Write a number down.

A frozen plan written before you see any features is the difference between a
result and a story.

---

## 6. Tests

- BrainVision triplet validation, including a deliberately orphaned `.vhdr`
- manifest-driven download is idempotent: second run downloads zero bytes
- disk guard triggers below threshold; streaming loop deletes raw after success
  and **retains** raw on failure
- **preprocessing module has no import path to labels** (§2a) — assert it
- filter spec round-trips into the sidecar JSON exactly as configured
- IAF estimation on a synthetic 10 Hz signal returns 10 Hz ± tolerance
- QC threshold logic on a synthetic fixture with known pass/warn/fail cases
- resample path: 500 Hz for rest, 250 Hz for MSIT, read from config not hardcoded

---

## 7. Definition of done

- [ ] `reports/phase1_budget_actual.md` written from measured durations **before**
      any bulk download
- [ ] All manifest files downloaded, verified, and raw deleted per subject
- [ ] Peak disk usage logged and under 30 GB
- [ ] Continuous preprocessed derivative exists for every non-excluded
      (subject, task)
- [ ] Every derivative has a complete provenance sidecar
- [ ] ICA solutions and excluded-component lists saved
- [ ] `qc_metrics.csv` complete; `excluded_subjects.csv` frozen with reasons
- [ ] `reports/phase1_qc.html` opens standalone, leads with a verdict
- [ ] Per-group exclusion counts reported (computed after freezing, not before)
- [ ] `reports/analysis_plan_frozen.md` written and committed
- [ ] Label blindness test passes
- [ ] `pytest` green; everything committed with `run_id` traceability

---

## 8. Stop and escalate if

- measured derivative total exceeds 30 GB (§0c) — the duration model is wrong
- more than 5 subjects fail QC, or exclusions concentrate in one group
- fewer than ~70 subjects survive for the primary target framing — the project
  needs re-scoping before features, not after
- a substantial share of subjects show no identifiable alpha peak — the
  pitch-synchronous approach rests on alpha being present, and if it isn't, the
  method choice needs revisiting while it is still cheap to change
- BrainVision triplets are incomplete for any subject in a way retry doesn't fix

Report and wait. Every one of these changes the shape of Phase 2.