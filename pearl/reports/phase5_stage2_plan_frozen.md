# Phase 5 Stage 2 Plan (FROZEN)

**Status: FROZEN.** Written before any Track B feature is computed, per
`phase_5_stage2.md` §0. Do not change after Track B features exist without
a written amendment appended below this line (original text stays
byte-identical, same discipline as `analysis_plan_frozen.md`).

This document does not amend, and is not amended by,
`reports/analysis_plan_frozen.md` — see `phase_5_stage2.md` §0a for why this
stage gets its own frozen plan rather than reopening the original.

---

## 1. Family budget

One new feature family for Stage 2: **multitaper time-frequency-area (TFA)**,
declared in full below. Track A's Sternberg extension (existing PSWT/baseline
definitions, unchanged, applied to new data) does not count against this
budget. If this family does not clear the benchmark-reproduction bar in §4,
it is reported as a null finding for that question and no second new family
is attempted in this stage without a written amendment to this document.

## 2. What "richer" means here, concretely

Per `reports/phase3_benchmark_reproduction.md`'s characterized gap: this
project's current baseline is a single relative-band-power number per band
(Welch PSD, whole-recording-averaged), where the published benchmark used
multitaper time-frequency-area features. **This project does not have
access to the published paper's exact algorithmic implementation** — the
design below is a good-faith, principled reconstruction of "multitaper +
time-frequency area," not a claimed byte-exact replication. That
distinction is stated here explicitly and must be repeated in the
diagnostic report (§4), not silently implied as precise reproduction.

### 2a. Multitaper PSD estimation

`mne.time_frequency.psd_array_multitaper`, DPSS tapers, time-bandwidth
product **4.0** (MNE's own conventional default — not tuned for this
dataset, chosen before seeing any result). Same five bands as the existing
baseline (`delta, theta, alpha, beta, gamma`, 1–45 Hz), same trapezoid-area
integration already used by `baseline.band_power`.

### 2b. ROI: frontocentral, not occipital-parietal

The current baseline (and PSWT) family uses the occipital-parietal ROI
(`config/features.yaml`'s `roi_channels`), appropriate for the alpha-driven
rest analysis but anatomically wrong for MSIT/Sternberg's cognitive-control
and working-memory signal, which `phase3_benchmark_reproduction.md` already
flagged and one-off-tested. Track B reuses that exact prior diagnostic
channel set for traceability, not a newly invented list:

```
Fz, FC1, FC2, Cz, F3, F4, FC5, FC6, C3, C4
```

### 2c. Where "time" comes from: multiple independent PSD estimates per
subject per scope, not a single whole-recording number

Rather than one PSD per subject per task (the current convention), Track B
computes **one multitaper PSD per short window or per trial-locked epoch**
(scope-dependent, §3), extracts band-area from each, and reports **mean and
IQR of that area distribution** as two features per band — the IQR is
genuinely new information (temporal/trial variability), not obtainable from
a single-shot PSD. `aperiodic_offset`/`aperiodic_slope` are still computed
once per scope on the concatenated/whole-scope signal (a 1/f fit needs a
wide, stable frequency range; doing it per-window would be noise-dominated),
matching the existing baseline convention.

## 3. Per-condition splitting — investigated on real data, decided from evidence

Per `phase_5_stage2.md` §0b.2's explicit instruction: verified against the
real `task-msit_events.tsv` / `task-sternberg_events.tsv` structure
(`sub-01` MSIT probe file, `sub-29`/`sub-57` Sternberg raw retained on disk)
before assuming anything.

### 3a. MSIT — no reliable demand-level split found; dropped

MSIT events contain `S 10` markers demarcating 4 roughly-equal ~110–160s
blocks, and two roughly-balanced stimulus codes (`S 4`: 82 occurrences,
`S 5`: 84, out of 166 stimuli in the `sub-01` probe recording) that plausibly
correspond to a trial-level manipulation. **Neither the block structure nor
the stimulus-code split is labeled anywhere in the available BIDS metadata**
(`task-msit_eeg.json` carries no per-block or per-code condition field) as
corresponding to the published paper's specific "low-demand"/"high-demand"
condition. Guessing which block or code is which would be fabricating a
label this dataset does not provide. **Per `phase_5_stage2.md`'s own
instruction, this is dropped**: MSIT Track B features are computed on the
**whole recording**, windowed (4-second non-overlapping windows, matching
the existing `n_fft = sfreq × 4` convention), not split by condition.

### 3b. Sternberg — encoding vs. retrieval split retained (structural, not demand-level)

Sternberg's markers cleanly separate two well-documented, distinct cognitive
phases of the classic Sternberg paradigm — this is retained, but explicitly
labeled as **encoding vs. retrieval**, never as "low-demand"/"high-demand"
(no set-size/load-level label was recoverable from the event markers alone;
see §3c).

- **Encoding**: `S 4` marks memory-set presentation onset. Verified
  fixed-duration across both subjects with raw retained on disk (`sub-29`:
  24/24 trials, gap to next marker 3.02–3.03s; `sub-57`: same, 3.02–3.03s).
  Window: **[0, 3.0s]** from each `S 4`. A trial is skipped (not
  zero-padded or truncated) if its actual gap to the next marker is < 3.0s,
  logged in the diagnostic's provenance, not silently included.
- **Retrieval**: `S 12` marks each probe/recognition-item onset (144 probes
  per recording in both checked subjects). Gap to the following response
  marker (`S 1`/`S 2`) has minimum 0.45s (`sub-29`) / 0.55s (`sub-57`).
  Window: **[0, 0.4s]** from each `S 12` — conservatively below the smallest
  observed gap so no probe-locked window is contaminated by the following
  response or next probe. This captures early retrieval-onset processing
  only, not the full decision period up to response — a real, stated
  limitation, not a hidden one. A probe is skipped under the same rule as
  encoding trials if its actual gap is < 0.4s.

### 3c. What was explicitly not attempted

Set-size/load-level (the classic Sternberg manipulated variable) was
investigated as a candidate signal — the number of probes between
consecutive `S 4` markers varies considerably within a recording (`sub-29`:
3, 3, 3, 3, 3, 6, 6, 9, 6, 6, 3, 3, 3, 15, 3, ...), which is consistent with
a genuine varying set-size design, but **there is no codebook or task
protocol document in this dataset's BIDS metadata that maps a given probe
count to a specific set size**, and the pattern is irregular enough (an
isolated 15-probe block, for instance) that guessing a mapping risks
fabricating a variable rather than measuring one. Not used. If a future
stage obtains the original task protocol/stimulus script, this is worth
revisiting — noted here so it isn't silently forgotten.

## 4. Benchmark-reproduction validation — scope and procedure

Per `phase_5_stage2.md` §0c: `pearl_features.benchmark_diagnostic`, a
sanctioned label-touching module, code-enforced to run only this question.

- **Feature set evaluated: `msit_tfa_*` only** (12 features: 5 bands ×
  {mean, iqr} + aperiodic offset/slope). This mirrors
  `phase3_benchmark_reproduction.md`'s exact scope (MSIT baseline features
  vs. the published 0.58) so the two numbers are comparable — same
  question, richer features, nothing else changed. Sternberg's
  `sternberg_encoding_tfa_*`/`sternberg_retrieval_tfa_*` features are
  extracted for future use but are **not** part of this diagnostic — no
  published Sternberg-specific benchmark number exists in
  `reports/benchmark_citation.md` to validate against, and inventing a
  target would be exactly the fabrication this plan avoids elsewhere.
- **Selection**: two-sided Welch's t-test per feature between
  `binary_risk_vs_none` groups, Benjamini-Hochberg FDR correction, fit
  **inside the training fold only** — computed fresh per fold, never on the
  full sample.
- **CV, permutation test, bootstrap CI, classifier**: identical machinery to
  `phase3_benchmark_reproduction.md` (subject-level stratified group k-fold,
  ≥1000 permutations re-running the full pipeline including selection, 2000
  resample bootstrap CI, logistic regression primary / linear SVM
  secondary) — changing the CV machinery alongside the features would
  confound which change explains any difference in the result.
- **One run. Report the result — better, unchanged, or worse than 0.459 —
  in `reports/phase5_stage2_benchmark_diagnostic.md`, verdict-first. No
  retuning bandwidth, window length, or ROI after seeing this number.**

## 5. Data contract

- MSIT/Sternberg continuous derivatives from Stage 1's re-run
  (`data/derivatives/preproc/sub-XX/eeg/*_desc-preproc_eeg.fif`) — the same
  63-subject preprocessing Track A already reads, never raw data.
- Raw `*_events.tsv` files, read once for epoch-boundary extraction only
  (onset timestamps), never for any other purpose — this does not reopen
  Phase 1's "raw data must never be revisited" contract for anything beyond
  locating trial boundaries already present in the BIDS-standard events
  file shipped with each recording.

---

## Amendment 1 — verified before any Track B code was written

The data-contract line above assumed raw `events.tsv` would need reading.
Checked before implementing: `mne.io.read_raw_brainvision`'s `.vmrk` parse
is preserved as `raw.annotations` on the already-saved preprocessed `.fif`
derivative (confirmed on `sub-01`'s Sternberg derivative: 389 annotations,
descriptions `Stimulus/S {1,2,3,4,10,11,12}`, onsets in the derivative's own
time base). **Track B reads epoch boundaries from
`raw.annotations` on the existing Stage 1 `.fif` derivatives — raw data is
never reopened for any of the 79 subjects beyond the two already retained
for other debugging.** This is a strictly narrower data footprint than
originally declared, not a broadening; recorded here so the actual data
source is traceable to what was verified.
