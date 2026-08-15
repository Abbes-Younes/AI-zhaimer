# Phase 6 — Representation Rebuild: The Final Attempt

**Agent instructions. Read this whole file before writing any code.**

This is the last attempt on this cohort. It is structured so that it produces a
defensible answer whether it succeeds or fails, and so that it cannot damage the
validated null already reported.

**The governing rule of this phase: you get exactly one look at the primary
target, and only if Gate 1 passes.** Everything before that gate runs against
control targets that carry no genotype information.

---

## 0. Why this is a legitimate attempt and not a fifth bite

The primary target has already been examined four times (Phase 3; Phase 5
both-fixes; reference-order-alone; ICA-alone). A fifth unstructured look would
be indefensible. Three properties make this one different, and all three are
mandatory:

1. **The null is banked.** The Phase 3/5 result stands as reported. Phase 6
   cannot retract, revise, or replace it. If Phase 6 finds nothing, the
   delivered conclusion is unchanged. If Phase 6 finds something, it is reported
   as a *subsequent, separately pre-registered analysis* with the full look
   history attached.
2. **The hypothesis is different.** Phases 3/5 tested *the pitch-synchronous
   feature family*. Phase 6 tests *whether any representation of this EEG
   carries subject-level information at all*, and only then whether that
   information relates to genotype. That is a different question, not a retry.
3. **The kill switch is external to the target.** Gate 1 (§2) is decided
   entirely on a control target. Genotype is never consulted to decide whether
   to continue.

**Precondition before any code:** fix the sex-control misdescription in the
LaTeX final report. It currently frames a *failed positive control* as a
*passed negative control* ("correctly failing to detect signal that should not
be present"). Sex was a positive control with a declared floor of 0.65 and it
failed. Correct that sentence, and reconcile the three control numbers against
the Phase 3 report (0.849/0.465/0.490 here vs 0.830/0.486/0.459 there) — state
which preprocessing each came from. Phase 6's entire rationale rests on that
failure being read correctly.

---

## 1. Pre-registration — write and commit before touching data

Create `reports/phase6_preregistration.md`, commit it, and do not amend it after
any result. It must state, in advance:

- **Gate 1 target and threshold** (§2): sex, pooled CV AUC ≥ 0.65 with the lower
  CI bound above 0.50, on the frozen 64-subject rest cohort.
- **The representation ladder** (§3), in full, in order, with every family
  declared up front. No family may be added later.
- **Gate 1 selection rule:** the single best-performing representation on the
  *sex* control is carried forward. Selection is made on the control, never on
  genotype.
- **Gate 2** (§5): exactly one genotype analysis, using the carried-forward
  representation, with the identical Phase 3 CV protocol.
- **The look history** that will appear in every Phase 6 report: this is
  genotype look #5, following four prior looks, and the reported p-value is
  interpreted in that light.
- **Expected outcome, stated honestly in advance:** the most likely result is
  that Gate 1 fails and the project ends with the null unchanged. That is a
  successful execution of this phase, not a wasted one.

---

## 2. GATE 1 — can any representation decode sex from this cohort?

This is the whole phase in one test.

Sex is reliably decodable from resting EEG in adequately powered samples. Your
current representation scored 0.486 on it. Until that changes, genotype work is
not merely unlikely to succeed — it is uninterpretable, because a null cannot be
distinguished from a representation that discards all between-subject
information.

**Protocol:** identical CV machinery to Phase 3 (L2 logistic regression, 5-fold
× 10 repeats, group-stratified, pooled out-of-fold AUC, 1000-permutation test,
2000-resample bootstrap CI), same frozen 64-subject rest cohort, target = sex.

**Pass:** AUC ≥ 0.65 **and** bootstrap lower bound > 0.50.

**Fail:** anything less. On failure, **stop**. Do not run Gate 2. Write the
result up per §6 and close the project.

Run every ladder rung in §3 against this gate before looking at genotype once.

Secondary control, run alongside for interpretation: age (continuous → tertile
split or regression AUC equivalent). Age is also robustly encoded in resting
EEG. Two passing controls is much stronger evidence that the representation
works than one.

---

## 3. The representation ladder — declare all rungs, run all rungs

The diagnosis from Phase 3–5 is that **aggregation destroyed the signal**: 15
ROI channels averaged into one, thousands of cycles collapsed to a median, 18
numbers per subject. Each rung below restores a different discarded axis.

### Rung 1 — Riemannian tangent-space covariance features *(highest prior)*

Compute per-subject spatial covariance matrices from the alpha band and the
broadband eyes-closed signal, then map to the tangent space at the Riemannian
mean and use the vectorised tangent-space coordinates as features.

This is the strongest available approach for small-sample cross-subject EEG
classification, and it is the direct answer to the aggregation problem: it
retains the full spatial covariance structure instead of averaging it away. If
any representation decodes sex here, this is the one.

Implementation notes: shrinkage-regularised covariance estimation (Ledoit-Wolf)
is mandatory at n=64; restrict to the frozen ROI channel set first, then a wider
montage as a separate rung entry if the ROI version passes. Tangent-space
projection is fitted **inside the training fold only** — the Riemannian mean is
a fitted parameter and leaking it is a real and easy mistake.

### Rung 2 — Aperiodic/periodic separation, per channel

Fit the spectral parameterisation (aperiodic exponent + offset, periodic peak
frequency/power/bandwidth) **per channel**, not ROI-averaged. The aperiodic
exponent is among the more reliably subject-discriminative EEG measures and the
current pipeline collapses it to a single averaged number.

Dimensionality: with 127 channels this needs in-fold reduction (PCA or
supervised selection) — inside the fold, never before.

### Rung 3 — Distributional cycle aggregation

Keep the existing PSWT cycle features but replace median+IQR with a
distributional summary: deciles, skew, kurtosis of the per-cycle distribution.
Tests directly whether the median collapse discarded the information, holding
the feature family constant.

### Rung 4 — Alpha-band connectivity

Imaginary coherence or phase-lag index across the ROI (volume-conduction-robust
measures only — plain coherence will encode reference and montage artefacts).
Connectivity is a between-channel property that per-channel averaging cannot
represent at all.

### Rung 5 — Concatenation of whichever rungs individually clear 0.60 on sex

Declared now so it is not a post-hoc addition. If no rung reaches 0.60, this
rung is skipped rather than run on the best-of-a-bad-set.

**Report every rung's sex AUC**, including failures, in the Gate 1 report.
Reporting only the winner is the same error as feature-family shopping.

---

## 4. Sternberg — optional new data, decided by Gate 1

Sternberg was never downloaded (~29 GB raw; trivial under the Phase 1 streaming
design, peak disk ~1.4 GB). It is the only genuinely unexamined data available,
and the published benchmark's own authors found task EEG outperforms rest.

**Do not acquire it before Gate 1 resolves.** If Gate 1 fails on rest, adding a
task will not rescue a representation that cannot decode sex. If Gate 1 passes,
Sternberg becomes a declared secondary analysis in Gate 2 — pre-registered in
§1 as such, or not run at all.

Preprocessing must use the **Phase 5 corrected pipeline** (reference-order fix +
explained-variance ICA), which is now the permanent default. Re-derive QC and
the per-task cohort with the same frozen thresholds; do not reuse the rest
cohort's exclusion list.

---

## 5. GATE 2 — the single genotype look

Reached **only** if Gate 1 passes.

- Target: `binary_risk_vs_none` — unchanged, still frozen. No target shopping.
- Features: the single representation that won Gate 1 on the control. Chosen
  before genotype is consulted.
- Protocol: identical to Phase 3, including the four reference lines (chance,
  QC-only, nuisance-only, benchmark 0.58) and the full-pipeline permutation test.
- **One run.** No variants, no combinations, no second model class.

### 5a. Mandatory validation, pre-declared

Phase 5's 0.651 looked real and wasn't. Any Gate 2 positive is subjected to the
same checks *before* it is described as a finding anywhere, including verbally:

- **Resampling stability:** ≥150 subject-level bootstrap resamples and ≥175
  leave-*k*-out draws (k=2–8). Pre-declared pass condition: bootstrap **median**
  above the nuisance-only line, and **under 10%** of resamples below chance.
  Phase 5 failed exactly here (median 0.565 vs nuisance 0.557; 24% below chance).
- **Nuisance separation:** the features+nuisance model must exceed nuisance-only
  by a margin whose CI excludes zero.
- **Permutation null centred at 0.5.**

A Gate 2 result that clears p<0.05 but fails stability is reported as **not
validated**, exactly as Phase 5 was. Write that sentence into the
pre-registration so it is a commitment, not a judgement call made under
pressure.

### 5b. Interpreting the p-value honestly

This is genotype look #5. Report the nominal p, and alongside it state the look
history explicitly. A nominal p=0.04 on the fifth look is weak evidence and the
report must say so in those words. Given power of 27% for the benchmark effect
and an MDE (d=0.596) exceeding any plausible true effect, **a marginal positive
here is more likely to be winner's curse than signal** — that is not pessimism,
it is what the Phase 5 power analysis already established.

---

## 6. Reporting

Two reports, both verdict-first:

**`reports/phase6_gate1_representation.md`** — every rung's control AUC (sex and
age), the winner or the failure, and the go/no-go. This is a real deliverable
even if Gate 1 fails: "no representation of this cohort's resting EEG decodes a
target known to be decodable" is a substantive, citable finding about the
dataset, and it converts the genotype null from *inconclusive* to *bounded by a
demonstrated cohort limitation*.

**`reports/phase6_final.md`** — only if Gate 2 ran. Includes the look history,
the stability results, and the §5a verdict. Must state whether the delivered
conclusion changed from the Phase 5 report, and if it did not, say so plainly in
the first paragraph.

Update the LaTeX client report with a Phase 6 section in either case, and fix
the §0 misdescription regardless of outcome.

---

## 7. Tests

- tangent-space projection is fitted inside the fold — assert the Riemannian
  mean differs between folds
- covariance estimation is shrinkage-regularised; assert conditioning
- no genotype label is importable from any Gate 1 module (same label-blindness
  test pattern as Phases 1–2, extended to `pearl_repr`)
- Gate 2 module raises unless a Gate 1 pass artefact with a recorded winner
  exists on disk
- ladder rung count matches the pre-registration; adding a rung fails a test
- stability harness reproduces the Phase 5 numbers when pointed at Phase 5
  inputs (validates the harness against a known answer)
- seeded runs bit-reproducible

---

## 8. Definition of done

- [ ] LaTeX report's sex-control misdescription corrected; control numbers
      reconciled across reports
- [ ] `phase6_preregistration.md` written and committed before any data touched
- [ ] All declared ladder rungs run against sex **and** age; all reported
- [ ] Gate 1 verdict issued
- [ ] If Gate 1 failed: Gate 2 not run, project closed, null unchanged
- [ ] If Gate 1 passed: Gate 2 run exactly once, with §5a validation
- [ ] Look history stated in every Phase 6 report
- [ ] Client-facing report updated either way
- [ ] `pytest` green; everything under one `run_id`

---

## 9. Stop and escalate if

- **Gate 1 fails** — this is the expected outcome and it is a clean stop, not an
  escalation to work around
- any Gate 1 rung is evaluated against genotype
- a rung not in the pre-registration is proposed
- a Gate 2 positive fails the §5a stability criteria and anyone suggests
  reporting it anyway
- the tangent-space or spectral-parameterisation fit is found to have been
  performed outside the fold

---

## 10. The honest expectation

The most probable outcome of this phase is that Gate 1 fails, and the project
closes with the validated null intact plus one additional, genuinely useful
finding: that this cohort's resting EEG does not support subject-level decoding
of *any* target at n=64 with these recordings. That upgrades the deliverable —
it turns "we found nothing" into "we established what this dataset can and
cannot support, and bounded the null."

The second most probable outcome is Gate 1 passing and Gate 2 returning another
null, which would be the strongest possible version of the original finding: a
representation demonstrably capable of subject-level decoding, applied to
genotype, finding nothing.

The least probable outcome is a validated positive. Build for the first two.