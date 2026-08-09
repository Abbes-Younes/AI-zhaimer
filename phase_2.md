# Phase 2 — Confound Gate & Pitch-Synchronous Feature Extraction

**Agent instructions. Read this whole file before writing any code.**

Phase 1 closed with `ESCALATE` and did so correctly. Before Phase 2 builds
anything, §0 resolves the scope decision and §1 runs a gate that must pass
before a single feature is computed.

**Non-goals.** No models. No accuracy numbers. No touching the frozen analysis
plan's primary target. Phase 2 ends with a subject-level feature matrix and
nothing fitted to labels.

---

## 0. Scope decision — resolved

**Adopt Option A + the rule change inside Option B. Defer Option C to a
pre-Phase-3 task.** Rationale, and the constraints that come with it:

### 0a. Per-task exclusion is the correct rule, independent of the N it yields

Excluding a subject from a **rest-based primary analysis** because their MSIT
recording was noisy is a category error, not a stricter standard. The frozen
analysis plan's primary target is rest-based; the exclusion unit should be
`(subject, task)`, which it already is at the QC-metrics level — only
`freeze_exclusions` collapses it to the subject.

Adopt it, but be honest in the record: the N it produces (64) was known before
the rule was adopted. Write that sentence into the amendment. A defensible rule
adopted with knowledge of its effect is fine; the same rule adopted silently is
not.

**No QC threshold may be adjusted.** The rule changes the *unit* of exclusion,
not the bar.

### 0b. Amend the frozen plan; do not rewrite it

Append an `Amendment 1` block to `reports/analysis_plan_frozen.md`, dated,
committed, stating:

- exclusion unit changed from subject to (subject, task), with the reason and
  the acknowledgement in §0a
- **primary target unchanged**: `binary_risk_vs_none`. It stays frozen. Changing
  the primary target because N moved is exactly the failure the freeze exists to
  prevent.
- `binary_high_vs_rest` and `multiclass_3` are **demoted to descriptive
  reporting only** — with A_P_plus at 12–14 survivors they cannot support a
  tested claim. Report their descriptive statistics; do not compute a p-value or
  claim a result for them.
- **Power statement, written now:** at roughly 24 vs 40 the study is
  underpowered to reliably distinguish a true AUC of 0.65 from the published
  0.58. State this as a known limitation before results exist, so it cannot be
  read as an excuse afterwards.

### 0c. Option C gets promoted, for a reason Phase 1 didn't have

Phase 1 called the reference-order bug "second-order." §1 may show it isn't.
Average reference computed before bad-channel interpolation means bad channels
contaminate the reference for every other channel — and if bad-channel counts
differ by group (§1a), that contamination is *group-dependent*, which turns a
processing imperfection into a confound. Same argument applies to ICA component
removal rates of 40–77%.

Do not act on this now. Record it, run §1, and let §1's result set Option C's
priority.

### 0d. Fix the uncited benchmark

The `AUC ≈ 0.58` in the frozen plan traces to a 2025 *Sensors* paper by Li et
al. on cross-subject early-AD susceptibility prediction in middle-aged adults
using multitaper spectral analysis, run on this same dataset with task EEG and
an SVM. **Verify the citation independently, add the full reference and DOI to
the repo**, and record which task and which classifier produced the 0.58 — the
comparison is only meaningful if you match the framing. If verification fails,
mark the benchmark as unverified in the plan rather than leaning on it.

---

## 1. THE GATE — preprocessing metadata must not predict group

This runs first and everything downstream is contingent on it.

Phase 1's attrition was uneven: 29% / 15% / 45% across N / A_P_minus / A_P_plus.
That may be chance on small groups, or it may mean **data quality is associated
with group** — in which case a classifier can learn preprocessing artefacts
instead of neurophysiology, and every downstream result is uninterpretable.

### 1a. Association tests

For each preprocessing/QC metric already in `qc_metrics.csv` — bad-channel
count, occipital bad-channel count, ICA components removed, line-noise power
before and after, artifact proportion, usable duration, IAF, alpha peak height —
test association with group across the analysis cohort:

- Kruskal–Wallis (continuous) / Fisher (categorical), bootstrap CIs on effect
  size, Benjamini–Hochberg FDR across the metric set
- run on both the full 79 and the surviving cohort, and report both
- test **exclusion status × group** with Fisher's exact — the attrition question
  directly

### 1b. The decisive test: fit a model on QC metrics alone

Train the frozen plan's CV scheme (subject-level stratified group k-fold,
nested, permutation-tested) on **nothing but the QC metrics** against
`binary_risk_vs_none`.

This is not modelling the hypothesis; it is measuring the contamination floor.
Interpretation:

| QC-only AUC | Meaning | Action |
|---|---|---|
| ≈ 0.50 (CI spans chance) | preprocessing carries no group information | **proceed** |
| 0.55–0.62 | partial contamination | proceed, but every EEG feature model must be reported *alongside* the QC-only baseline, and improvement over it is the only claim you may make |
| > 0.65 | preprocessing predicts group about as well as published EEG features do | **stop and escalate.** Features built on this data cannot be distinguished from artefact detectors. Option C becomes mandatory. |

Write `reports/phase2_confound_gate.md`, verdict-first. This report is a
deliverable whether it passes or fails — a clean pass is a substantive result
that strengthens everything after it.

### 1c. Carry-forward covariates

Whatever the outcome, bad-channel count and ICA-components-removed join SES and
BDI as declared covariates for Phase 3, recorded in the amendment.

---

## 2. Epoching and the eyes-closed window

- Consume the eyes-closed window already resolved in Phase 1
  (`eyes_closed_window`), never re-derive it. Read it from the sidecar.
- Reject artifactual segments by fixed amplitude/gradient criteria from config,
  applied uniformly. **Feature extraction stays label-blind** — same enforced
  test as Phase 1, extended to `pearl_features`.
- Record usable eyes-closed duration per subject. It varies, which matters in §6.
- Do **not** epoch into fixed windows for the cycle analysis. Cycle detection
  runs on the continuous cleaned segment; fixed epoching would sever cycles at
  arbitrary boundaries. Fixed epochs are only for the §7 spectral baseline.

---

## 3. Cycle detection — the chapter's §5.1.2, adapted

The central rule, restated because everything depends on it:

> **Detect cycle boundaries on a narrowband copy. Measure waveform shape on the
> broadband signal.**

Filtering to the alpha band and then measuring harmonic content of the result
measures your filter. Implement as:

1. Take each subject's IAF from the Phase 1 sidecar. Build a narrowband copy at
   IAF ± 2 Hz (zero-phase FIR; record the exact spec).
2. Find positive-slope zero crossings on the narrowband copy. Per the chapter,
   round to the first positive sample after the crossing.
3. Estimate the period, then locate the next boundary as the positive-slope zero
   crossing **closest to** `t_k + P(t_k)` — not the next one after it. This is
   the phase-locking step and it is what keeps boundaries on real structure.
4. Map the resulting boundary indices onto the **broadband** signal. All shape
   measurement happens there.

**Cycle validity filter, defined a priori:** reject cycles whose period falls
outside a fixed multiple of the subject's IAF period (e.g. ±40%), and cycles
with amplitude below a fixed percentile of that channel's distribution. Log the
rejection rate per subject — a subject rejecting most cycles is a QC flag, not
a subject to quietly keep.

Sanity checks that must pass before proceeding: median detected period ≈
1/IAF within tolerance; boundary count ≈ IAF × usable duration; the detector
recovers a known period on a synthetic 10 Hz signal with added noise.

---

## 4. The PSR matrix

Per subject, per channel:

1. Extract each valid cycle `x_i[n]` of length `Q_i`.
2. Choose the target period **`P` = mode of `{Q_i}`** (chapter §5.2.2 — chosen
   so the no-resampling case occurs often).
3. Resample each cycle to length `P` **via the DFT method**, not filter-based
   resampling: DFT of size `Q_i`, truncate or zero-extend to `P`, IDFT scaled by
   `P/Q_i`. Zero the Nyquist bin when `P` or `Q_i` is odd. Filter-based
   resampling introduces edge effects at cycle boundaries, which is precisely
   where your reconstruction lives.
4. Stack into the `R × P` PSR matrix.

At 500 Hz and ~10 Hz alpha, expect `P ≈ 50`. **Assert `P ≥ 40`**; below that the
harmonic representation is too coarse for the features in §6 and the resampling
step needs revisiting.

**Reconstruction test before trusting anything downstream:** on a synthetic
pseudo-periodic signal, PSR construction followed by inverse must reconstruct to
within numerical tolerance. If it doesn't, every feature after this is noise.

---

## 5. PSWT

Implement via the **multiplexed / polyphase structure** (chapter §5.4.2), not
comb wavelets — comb wavelets lose perfect reconstruction for even `P`, and with
`P ≈ 50` you will hit that immediately.

Demultiplex the signal into `P` subsignals (the PSR columns), wavelet-transform
each (Daubechies-8, as in the chapter), keep the lowpass band to reconstruct the
harmonic/periodic estimate, and treat the detail bands as the inter-harmonic
residual.

Perfect-reconstruction test with all subbands included, on synthetic data, is a
required passing test.

---

## 6. Feature definitions

Declare the complete feature list in `config/features.yaml` **before** running
it. Nothing gets added after seeing results.

### 6a. Waveform-shape / pitch-synchronous features (primary)

Per subject, per ROI channel:

- **Harmonic amplitude profile:** median amplitude of harmonics 1..H from the
  per-cycle DFT, normalised to the fundamental
- **Harmonic-to-inter-harmonic energy ratio** from the PSWT decomposition — the
  direct measure of waveform non-sinusoidality
- **Cycle-to-cycle variability:** dispersion of the detail-band energy across
  cycles; the PSWT's own residual is the natural estimator
- **Period variability:** IQR of `{Q_i}` normalised by median period
- **Waveform asymmetry:** rise–decay time ratio and peak–trough sharpness ratio,
  computed on broadband cycles. These converge with the established cycle-by-cycle
  literature and act as an interpretable cross-check on the PSWT features — if
  the two families disagree wildly, suspect the implementation.

### 6b. The 50 Hz harmonic exclusion — mandatory

The 5th harmonic of a 10 Hz rhythm sits on Polish mains. For each subject,
compute which harmonic index falls nearest 50 Hz given their IAF and **exclude
that index from the harmonic profile**, uniformly. Since the excluded index
varies with IAF, exclude it by index-per-subject and mark the feature `NaN`
rather than shifting the profile — a shifted profile would silently encode IAF
into every downstream harmonic feature.

Record the excluded index per subject and verify it does not associate with
group (same test as §1a).

### 6c. Channel ROI

Do **not** compute features on all 127 channels. Define a fixed occipital–
parietal ROI a priori (where alpha lives), listed explicitly in config. Everything
else is dimensionality with no hypothesis behind it.

### 6d. Aggregation policy — read carefully

Features are **subject-level**. Cycles are not samples. A 6-minute eyes-closed
block yields ~3,600 cycles per channel; feeding those to a classifier as rows is
the leakage failure mode that produces AUC 0.95 and means nothing.

Aggregate cycles to subject level with median and IQR (robust to the cycle
outliers a real recording contains). Then aggregate across ROI channels the same
way.

**Fix the cycle count.** Usable duration varies by subject, so estimator variance
varies by subject — and if duration correlates with group, that variance
structure is itself a signal. Subsample a fixed number of cycles per subject
(the minimum across the cohort, or a fixed floor with subjects below it excluded)
using a seeded RNG. Record the seed and the count.

### 6e. Dimensionality budget

With N ≈ 56–64, cap the declared feature set at **≤ 30 features** before any
selection. Any further selection happens **inside** CV folds in Phase 3, never
here. State the count in the feature dictionary.

---

## 7. Baseline feature set (required, not optional)

Compute a conventional feature set in parallel: relative band power
(delta/theta/alpha/beta/gamma), individual alpha frequency, alpha peak height,
1/f slope and offset (aperiodic fit), and Phase 1's multitaper equivalent for
MSIT.

Two reasons this is mandatory: it is how you reproduce the published ~0.58 and
confirm your pipeline is sane, and it is the reference the pitch-synchronous
features must beat to justify their complexity. A novel feature family that
doesn't beat band power is a negative result worth reporting — but you can only
report it if you computed both.

---

## 8. Outputs

```
data/derivatives/features/
  features_pswt.csv          # subjects × features, primary
  features_baseline.csv      # subjects × features, comparison
  feature_dictionary.md      # every column: definition, units, provenance
  cycle_stats.csv            # per subject: cycles detected/valid/used, P, rejection rate
  _meta.json                 # run_id, git SHA, config hashes
```

Same Phase 0.5 conventions: atomic staging, single `run_id`, report refuses to
render on mixed runs. Feature files must **not** contain group labels — the join
happens in Phase 3.

---

## 9. Tests

- cycle detector recovers the period of a synthetic 10 Hz signal with noise, and
  degrades gracefully (not silently) on a signal with no periodicity
- boundaries detected on narrowband are applied to broadband — assert the
  broadband signal is what gets measured (this is the bug that would be
  invisible in results)
- PSR reconstruction round-trip within tolerance
- PSWT perfect reconstruction with all subbands
- DFT resampling: Nyquist bin zeroed for odd `P` or `Q_i`
- `P ≥ 40` assertion fires when violated
- 50 Hz harmonic exclusion picks the right index across a range of IAF values
- fixed cycle subsampling is deterministic under a fixed seed
- feature extraction has no import path to labels
- declared feature count matches `config/features.yaml`

---

## 10. Definition of done

- [ ] Amendment 1 appended to `analysis_plan_frozen.md` and committed
- [ ] Benchmark citation verified and recorded, or marked unverified
- [ ] `reports/phase2_confound_gate.md` written, verdict-first, QC-only AUC reported
- [ ] Per-task exclusion rule applied; new cohort frozen with reasons
- [ ] Cycle detection validated on synthetic and real data; `cycle_stats.csv` complete
- [ ] PSR and PSWT reconstruction tests pass
- [ ] `features_pswt.csv` and `features_baseline.csv` produced, ≤ 30 features each
- [ ] `feature_dictionary.md` complete
- [ ] 50 Hz harmonic exclusion applied and its index tested against group
- [ ] Label blindness test passes for `pearl_features`
- [ ] `pytest` green; committed under one `run_id`

---

## 11. Stop and escalate if

- **QC-only AUC > 0.65** (§1b) — this is the one that stops the project in its
  current form; Option C becomes mandatory before any feature is trusted
- PSR or PSWT reconstruction tests fail — do not proceed with "close enough"
- `P < 40` for a meaningful share of subjects
- cycle rejection rate exceeds ~30% for more than a handful of subjects — the
  cycle validity criteria or the alpha assumption needs revisiting
- surviving N under the per-task rule differs materially from the 64 computed in
  Phase 1
- the harmonic-exclusion index associates with group after FDR correction

Report and wait. §1b in particular is not a number to work around.