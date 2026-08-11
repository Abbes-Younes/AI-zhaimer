# PEARL-Neuro EEG Classification — Final Report

**Prepared:** 2026-08-11
**Language note:** this report is in English. The client's classification
document (`reference/classification.pdf`) was written in French — **please
let us know if a French version of this report would be useful**; it has
not been assumed either way.

---

## Verdict, up front

**Resting-state EEG waveform-shape features did not distinguish the two
genetic Alzheimer's-risk groups in this cohort.** This is a **negative
result for the method as tested** (not an inconclusive one — see §4): a
follow-up diagnostic confirmed that other EEG features *do* carry
detectable subject-level information in this same cohort, so the null is
specific to the pitch-synchronous waveform-shape approach, not a sign that
nothing in this dataset is measurable.

---

## 1. What was asked, what was delivered

**Asked:** build and validate a pipeline that predicts genetic
Alzheimer's-risk group (APOE ε4 + PICALM status) from resting-state and
task EEG, using a novel pitch-synchronous waveform-shape feature family,
compared against a conventional spectral baseline — and deliver it as a
usable, deployable tool.

**Delivered:** the full pipeline (download → preprocessing → confound gate
→ feature extraction → model → calibrated, containerized scoring tool),
run end to end on the real dataset (OpenNeuro `ds004796`), with every
design decision, threshold, and stopping rule fixed *before* the number
that would have been tempting to chase. The headline result is a null, and
the engagement's deliverable is a rigorously validated null plus a
correctly-positioned research tool — not a positive finding, because there
isn't one to report honestly.

## 2. Headline finding

Primary analysis: L2-penalised logistic regression, PSWT waveform-shape
features, resting-state EEG, N=64 (39 at-risk / 25 no-risk), nested
cross-validation (5-fold × 10 repeats, pooled out-of-fold predictions).

**AUC = 0.474** (95% CI [0.266, 0.702]), **permutation p = 0.577**.

In plain language: a model given only chance-level information would score
about this well roughly 58% of the time. The feature family does not
separate the two groups in this cohort, and this is not a borderline or
marginal result — the point estimate sits at essentially the coin-flip
line.

## 3. Why this is a trustworthy result, not a failed one

A null result is only worth reporting if the pipeline that produced it can
be trusted. This one can, on several independent grounds — most published
work in this space does fewer of them:

- **Labels independently verified against source genotypes**, 79/79
  subjects reconciled before any analysis began (Phase 0).
- **No demographic confounds**: age, sex, socioeconomic status, and
  depression score were checked against group membership before any
  feature existed.
- **A confound gate ran before any feature was computed**: a classifier
  given only preprocessing/QC metadata (no EEG signal at all) scored AUC
  0.545 — statistically indistinguishable from chance — confirming that
  preprocessing artefacts could not be driving a downstream result.
- **Label-blind preprocessing and feature extraction**: every QC threshold
  and cycle-detection parameter was fixed before group labels were ever
  read by the feature-extraction code, enforced by automated tests, not
  just convention.
- **A pre-registered analysis plan**, frozen before any feature existed,
  amended twice in writing (never silently) as new information came in —
  every amendment is a permanent, dated, appended record, never an edit to
  the original.
- **The permutation null was verified to sit at chance** (mean permuted
  AUC 0.492, essentially indistinguishable from the observed 0.474) — this
  rules out a leaking cross-validation design as an alternative explanation
  for the null.
- **Positive controls were run** before the primary hypothesis was tested
  at all (see §4) — both to confirm the pipeline measures what it claims,
  and to resolve exactly how much weight the null carries.

## 4. The positive-control finding that resolves the ambiguity

Two controls were run first, against targets known (or suspected) to be
detectable, never against the genotype target itself:

- **Eyes-open vs. eyes-closed** (does the pipeline measure real alpha
  brainwave suppression?): **AUC 0.830** — a strong pass. The pipeline
  correctly measures what it is designed to measure.
- **Sex classification** (a target generally detectable from resting EEG in
  larger studies): **AUC 0.486** — at chance, on this feature family alone.

That second result was ambiguous on its own: it could mean "nothing in this
64-subject cohort is detectable at subject level" (making the genotype null
*inconclusive*) or "this specific feature family doesn't carry subject-level
information, even though the cohort does" (making the genotype null a
*real, informative negative*). A dedicated follow-up diagnostic (never
touching the genotype target — enforced in code, not just procedure)
resolved this: **conventional spectral EEG features scored AUC 0.693
(p=0.013) for sex classification in this same cohort — a real, statistically
significant subject-level signal.** The pitch-synchronous waveform-shape
family specifically does not carry it (AUC 0.556, not significant), even
when combined with the spectral features that do. This is what makes the
headline finding a **negative result for the method as applied**, not a
statement that nothing is measurable in this data.

## 5. What this result does and does not license

**It does not say** that APOE/PICALM genetic status is invisible in EEG, or
that no EEG feature could ever detect it. **It says** that this specific
method — pitch-synchronous waveform-shape features, on resting-state EEG,
at this sample size — did not detect it, in a cohort where a comparison
feature family did carry other subject-level information. That is a
narrower, more useful claim than either "EEG can't do this" or "the study
failed."

## 6. What would be needed to answer the question properly

- **A larger cohort.** At 39 vs 25, this study is underpowered to reliably
  distinguish a true AUC of 0.65 from the published reference point of
  0.58 — a known limitation stated in the analysis plan before any result
  existed, not raised after the fact.
- **Task-state EEG with richer feature engineering.** The published
  benchmark (0.58) came from task EEG with a considerably richer
  spectral-feature pipeline (multitaper time-frequency features, per-block
  condition splitting, statistical feature selection) than this project's
  comparison baseline. Our own reproduction attempt of that benchmark, on
  our simpler feature set, landed at chance — a characterized gap in
  feature richness, investigated and confirmed not to be a pipeline bug,
  but real work to close if task-state EEG is pursued.
- **The deferred Phase 1 reprocessing** (fixing a reference-order
  imperfection and re-evaluating an ICA decomposition parameter) — both
  identified early, deliberately deferred pending a larger data-transfer
  budget (~46 GB), and confirmed by the confound gate to show no current
  evidence of being necessary — but not definitively ruled out.
- **The Sternberg memory task**, which the streaming download design used
  throughout this project makes newly affordable, and which was not
  analysed in this engagement.

None of the above is included in the current engagement scope — see the
handover document for sizing.

## 7. Deliverables index

| Artefact | Location | Contents |
|---|---|---|
| This report | `reports/phase4_final_report.md` (+ `.html`) | client-facing summary |
| Full technical results | `reports/phase3_results.md` | primary analysis, all reference lines, secondary comparisons |
| Confound gate | `reports/phase2_confound_gate.md` | QC-only classifier, AUC 0.545 |
| Positive controls | `reports/phase3_positive_controls.md` | eyes-open/closed, sex classification |
| Ambiguity-resolving diagnostic | `reports/phase4_control_diagnostic.md` | the 3-rung ladder behind §4 above |
| Benchmark investigation | `reports/phase3_benchmark_reproduction.md` | why the published 0.58 wasn't reproduced, and why that's not a pipeline bug |
| Frozen analysis plan + amendments | `reports/analysis_plan_frozen.md` | every locked-in decision, dated |
| Provenance chain | `reports/provenance_chain.md` | data hash → shipped model, traceable |
| Feature dictionary | `data/derivatives/features/feature_dictionary.md` | every feature column, defined, including two documented defects (§8) |
| Shipped tool | `Dockerfile`, `INSTALL.md`, `RUNBOOK.md` | containerized, CLI + API, verified end-to-end |
| Model card | `data/derivatives/models/model_card.md` | intended use, performance, explicit out-of-scope uses |
| Full engineering record | `report.md`, `docs/superpowers/plans/` | phase-by-phase implementation history |
| Handover | `HANDOVER.md` | repo map, deferred-work sizing, how to resume |

## 8. Known defects annex

Two feature-definition issues were found during Phase 3's stability
analysis and corrected before this report was written:

- **A tautologically constant feature pair** (`harmonic_amplitude_profile_
  h1_median`/`h1_iqr`) was declared among the original 20 PSWT features but
  carried zero information by mathematical construction (harmonic 1
  normalised to itself is always exactly 1.0). Removed; the effective
  feature count was always 18, and removing two exactly-constant columns
  cannot change the reported result (confirmed: both had 0% selection
  frequency in the model).
- **One feature pair correlates with recording duration** rather than
  anything neurophysiological, among the small subset of subjects where it
  isn't missing by design. Flagged in the feature dictionary as a usability
  caveat; not used to change any reported number.

Full detail: `data/derivatives/features/feature_dictionary.md`'s "Known
defects" section.

## Limitations (consolidated)

See `reports/phase3_results.md` §7 for the full list: statistical power at
this sample size, the width of the QC-only confound-gate confidence
interval, the rest-vs-task benchmark framing mismatch, the two deferred
Phase 1 preprocessing questions, and uneven attrition in the smallest
genetic subgroup during quality control. None of these were discovered
after the result — every one was stated in writing before the primary
analysis ran.
