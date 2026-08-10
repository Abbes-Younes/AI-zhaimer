# Phase 3 — Modelling, Validation & Delivery

**Agent instructions. Read this whole file before writing any code.**

Phase 2 closed clean: gate passed, 64-subject cohort frozen, 20 PSWT + 16
baseline features extracted, nothing fitted to labels. Phase 3 is the only
phase in this project that touches the primary target, and it gets exactly one
honest attempt at it.

**Read §0 and §1 before §3.** Two things must happen before the primary model
is fit, and both become impossible to do credibly afterwards.

---

## 0. Amendment 2 — write, commit, then stop touching the plan

These are estimator-variance and reporting decisions, not hypothesis changes.
Make them **now**, before any label is joined to any feature, and record them as
`Amendment 2` in `reports/analysis_plan_frozen.md` with today's date and the
reason for each.

### 0a. Fix the CV variance problem

The frozen plan specifies 5-fold × 3 repeats. On N=64 that means test folds of
~13 subjects, and an AUC computed on 13 subjects is extremely noisy. Two
changes, neither of which alters the estimator:

- **Raise to 5-fold × 10 repeats.** More repeats reduce the variance of the
  same estimate; it is not a different analysis and it cannot be tuned toward a
  result because it happens before any result exists.
- **Pool out-of-fold predictions, don't average per-fold AUCs.** Collect
  out-of-fold predicted probabilities for every subject across a repeat,
  compute one AUC over all 64, then average across repeats. Averaging tiny
  per-fold AUCs is both higher-variance and biased.

Report both the pooled AUC and the spread across repeats.

### 0b. Declare the model class before you see anything

With 64 subjects and 20 features, tree ensembles will overfit and their CV
estimates will be unstable. Declare:

- **Primary:** L2-penalised logistic regression, `C` tuned in the inner loop
  only, features standardised inside the fold.
- **Secondary:** linear SVM.
- **Not permitted as primary:** random forest, gradient boosting, any neural
  network. If one is run at all, it is exploratory and labelled as such — it
  cannot become the headline number.

### 0c. Declare the reference lines

A raw AUC means nothing on its own. Every results table in this phase carries
four rows, always:

| Reference | Value | Source |
|---|---|---|
| Chance | 0.500 | — |
| QC-only (preprocessing metadata) | 0.545 | Phase 2 gate |
| Nuisance-only (age, sex, SES, BDI, education) | compute in §2 | new |
| Published benchmark | 0.58 (MSIT task, not rest) | Li et al. 2025 |

**A feature model that does not beat the nuisance-only line has not
demonstrated anything about EEG.** That is the comparison that matters most and
it is the one most often omitted.

### 0d. Keep the QC-only line in view — the gate was weaker than it reads

The gate's 0.545 came with a 95% CI of [0.435, **0.800**]. That is a clean pass
on the decision rule and it is also a wide interval that does not exclude
substantial contamination. Treat the gate as "no evidence of contamination,"
never as "contamination excluded." Practically: QC-only stays as a permanent
reference row, and `artifact_frac` — borderline on the full cohort
(p_fdr=0.011), non-significant on N=64 (p_fdr=0.056), which may be power loss
rather than absence — **joins the declared nuisance set** alongside bad-channel
count and ICA components removed.

### 0e. Declare the comparison set and its correction

Primary comparison, stated now: **PSWT features on resting-state, vs the
nuisance-only line, on `binary_risk_vs_none`.** One test.

Secondary, corrected with Holm across the declared set: baseline features on
rest; PSWT+baseline combined on rest; baseline features on MSIT.

Everything else is exploratory and reported as such. The stopping rule from the
frozen plan stands: no additional feature families without a written amendment.

### 0f. State the achievable precision, now

At 39 vs 25, the 95% CI on an AUC estimate will be roughly ±0.13–0.15 wide. A
true AUC of 0.70 will produce an interval of about [0.56, 0.84]. Write this into
the amendment before results exist, so that a wide interval afterwards reads as
a known property of the sample size rather than a disappointment.

---

## 1. Positive controls — run these before the hypothesis

This is the most important addition in this phase. If the primary analysis
returns a null, you need to know whether it is a null about genotype or a null
about your pipeline. That distinction cannot be established after the fact.

Run the **exact same CV machinery** on targets that are known to be detectable:

### 1a. Eyes-open vs eyes-closed (the strong control)

Extract the Phase 2 PSWT features from the eyes-*open* segment of the same rest
recordings — the pipeline already resolves both windows from the markers — and
classify eyes-open vs eyes-closed **within subject**.

Alpha is dramatically suppressed by eye opening (Berger blocking; it was the
root cause of the Phase 1 escalation). If your alpha-derived waveform-shape
features cannot separate these two conditions with a high AUC, **the feature
pipeline is not measuring alpha waveform shape and the primary analysis is
meaningless.** Expect a high value here. Set a floor of 0.80 and treat failure
as a stop condition.

Note this is a within-subject comparison, so the CV structure differs — group
by subject so both conditions from one subject never straddle a fold.

### 1b. Sex classification (the subject-level control)

Classify sex from the same subject-level feature matrix, same CV machinery,
same 64 subjects. Sex differences in resting EEG are well documented and this is
a genuine subject-level cross-subject problem — structurally identical to the
primary analysis, but with a target that should be detectable.

An AUC near chance here alongside a high 1a result would tell you the pipeline
measures the signal fine but the subject-level generalisation is where it
breaks — which is diagnostic information the primary result alone cannot give.

### 1c. Interpretation table — write it before running

| 1a | 1b | Primary null means |
|---|---|---|
| high | ≥ ~0.65 | pipeline works; a null on genotype is a **real null** — reportable, valuable |
| high | ≈ chance | features work but don't generalise across subjects; report the primary null with that caveat |
| low | any | **pipeline is broken.** Stop. Do not run or report the primary analysis |

Write `reports/phase3_positive_controls.md`, verdict-first, before §3 runs.

---

## 2. Benchmark reproduction and the nuisance line

### 2a. Reproduce ~0.58 on MSIT

The published 0.58 came from **task-state MSIT** with spectral features, and the
source paper found task EEG outperforms rest for this problem. You have baseline
spectral features on MSIT. Run them.

This is a pipeline-validation test, not a result. If MSIT + spectral features
lands anywhere near 0.58, your preprocessing and CV machinery are comparable to
published work and the comparison is meaningful. If it lands at chance, your
pipeline differs from theirs in some way you need to understand before quoting
their number as a target at all.

Record the outcome either way in `reports/phase3_benchmark_reproduction.md`.
Note the framing caveat prominently: because the benchmark is task-based and the
primary target is rest-based, **0.58 is if anything an optimistic bar for the
primary analysis**.

### 2b. Compute the nuisance-only line

Fit the primary CV machinery on nuisance variables alone: age, sex, SES, BDI,
education, bad-channel count, ICA components removed, `artifact_frac`. Record
the AUC and CI. This becomes the row in §0c that every feature model is measured
against.

---

## 3. The primary analysis

One run, per the declared plan. No iteration.

- Target: `binary_risk_vs_none`, 39 vs 25
- Features: `features_pswt.csv`
- Model: L2 logistic regression, nested CV, standardisation and any feature
  selection **inside the inner fold only**
- 5-fold × 10 repeats, subject-level stratified group folds, out-of-fold pooling
- ≥1000-permutation test in which **the entire pipeline is re-run per
  permutation**, including scaling and selection — permuting only at the
  classifier step gives an optimistic null
- 2000-resample bootstrap CI on the pooled AUC
- Report against all four reference lines

Then the secondary set from §0e, Holm-corrected. Then stop.

### 3a. Covariate handling — three models, all reported

1. **Features only** (primary claim)
2. **Features + nuisance** (does EEG add anything on top?)
3. **Nuisance only** (§2b)

The claim you are entitled to make is the gap between 1 and 3, and whether 2
improves on 3. Nothing else.

### 3b. Feature stability, not feature importance

At N=64, a single coefficient ranking is noise. Report **selection/sign
stability across folds and repeats** — how often each feature is retained and
whether its coefficient keeps its sign. Features stable in >80% of folds are
worth discussing; the rest are not. Do not build a narrative on a
single-fit importance plot.

---

## 4. Leakage tripwire

Any AUC above ~0.85 is a bug until proven otherwise. Checklist, in order:

1. Did any subject appear in both train and test in any fold?
2. Was scaling, imputation, or selection fitted outside the fold?
3. Did a cycle-level or epoch-level row leak into a subject-level matrix?
4. Is a feature a proxy for acquisition order, file size, duration, or
   subject ID?
5. Does the permutation null sit at 0.5? If the permuted AUC is elevated, the CV
   structure itself is leaking.

Run check 5 regardless of the result — it is the cheapest structural test you
have and it validates the whole design.

---

## 5. Write the null-result report before you know the result

Draft `reports/phase3_results.md` **now**, with the numbers left as
placeholders, in a form that reads correctly whether the result is positive or
null. A null here is a legitimate, publishable-quality finding given a clean
gate and passing positive controls — but only if it is written as one, not as an
apology bolted onto a failed experiment.

The report structure, verdict-first:

1. Verdict and the primary number with CI
2. All four reference lines
3. Positive control outcomes
4. Benchmark reproduction outcome
5. Secondary comparisons, corrected
6. Feature stability
7. Limitations — power (§0f), the QC-only CI width (§0d), the rest-vs-task
   benchmark mismatch, the deferred reference-order and ICA issues from Phase 1,
   A_P_plus attrition
8. What would be needed to answer the question properly (larger n, task EEG,
   the Option C reprocessing)

---

## 6. Delivery — the shipped pipeline

The client asked for a deployable tool. Build it, and position it correctly.

- **Train the shipped model on all 64 subjects** after evaluation is complete
  and frozen. Version the artefact with `run_id`, git SHA, feature config hash,
  and the `participants_tsv_sha256` fingerprint from Phase 0.5.
- **The reported performance is the cross-validated number, never a number
  computed on the training data.** Make that explicit in the artefact metadata
  and in the tool's own output.
- **Calibrate** (Platt or isotonic, fitted inside CV) and ship calibrated
  probabilities with an uncertainty band, not a hard label.
- **Inference path:** BIDS EEG in → Phase 1 preprocessing → Phase 2 features →
  calibrated probability out. Containerised, CLI + thin API, with the same
  provenance sidecar discipline.
- **Refuse to score out-of-distribution input.** If a new recording's QC metrics
  fall outside the training cohort's range, the tool returns "cannot score" with
  the reason. A model this weak must not silently extrapolate.
- **Positioning, in the tool's own output and not only the docs:** this is a
  research pipeline. Output is a research score, not a risk assessment,
  screening result, or diagnosis. Bake the disclaimer into the JSON the tool
  emits.

---

## 7. Outputs

```
reports/
  phase3_positive_controls.md
  phase3_benchmark_reproduction.md
  phase3_results.md            # + .html, self-contained, verdict-first
  analysis_plan_frozen.md      # Amendment 2 appended
data/derivatives/models/
  cv_predictions.csv           # out-of-fold probabilities, all repeats
  cv_metrics.csv               # every model × every reference line
  feature_stability.csv
  model_final.joblib + model_card.md
  _meta.json
```

`model_card.md` states: intended use, training cohort and its exclusions,
CV-estimated performance with CI, known limitations, and explicit
out-of-scope uses.

---

## 8. Tests

- no subject appears in train and test within any fold (assert, every repeat)
- scaler and selector fitted inside the fold — verify by asserting a fold's
  scaler mean differs from the full-data mean
- permutation harness re-runs the full pipeline, not just the classifier
- out-of-fold pooling covers every subject exactly once per repeat
- seeded runs are bit-reproducible
- positive-control targets are never joined into the primary feature matrix
- shipped model refuses out-of-range QC input
- model card generation fails if any required field is empty

---

## 9. Definition of done

- [ ] Amendment 2 written and committed **before** any label join
- [ ] Positive controls run and reported; §1c interpretation applied
- [ ] Benchmark reproduction attempted and recorded either way
- [ ] Nuisance-only line computed
- [ ] Primary analysis run once, against all four reference lines
- [ ] Secondary set run, Holm-corrected
- [ ] Permutation null verified to sit at chance
- [ ] Feature stability reported instead of single-fit importance
- [ ] `phase3_results.md` verdict-first, limitations section complete
- [ ] Shipped model trained on all 64, calibrated, versioned, with model card
- [ ] Out-of-distribution refusal implemented and tested
- [ ] `pytest` green; everything under one `run_id`

---

## 10. Stop and escalate if

- **positive control 1a comes back below 0.80** — the pipeline isn't measuring
  what it claims; do not run the primary analysis
- the permutation null is not centred on 0.5 — structural leakage in the CV
- primary AUC exceeds 0.85 and the §4 checklist doesn't explain it
- benchmark reproduction on MSIT lands at chance — your pipeline and the
  published one differ in a way that invalidates the comparison
- you find yourself wanting to try a fourth feature family, a different target,
  or a different model class after seeing a result

That last one is the one to watch. Everything in this phase is designed so that
a null is a real, defensible finding. The only thing that can turn it into a
worthless one is a second attempt.