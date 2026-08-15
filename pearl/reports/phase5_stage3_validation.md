# Phase 5 Stage 3 Validation — Consolidated Verdict

**Prepared:** 2026-08-13

**Plan followed:** `sparkling-launching-torvalds.md` (Step 0: stability
characterization, Step 1: single-variable attribution, Step 2: this report).

---

## Verdict, up front

**The Stage 3 positive result (AUC 0.651, p=0.041) does not survive
validation. It should not be delivered as a positive finding.** Three
independent checks were run against it; none corroborate it, and two
actively undermine it. The defensible deliverable from Phase 5 is the
honest, rigorous characterization of why a 79-subject single-cohort EEG
study cannot support this claim — not the headline number itself.

## 1. What was checked, and what came back

| Check | Question asked | Result |
|---|---|---|
| Step 0 — stability/resampling | Does 0.651 hold up under small perturbations of the same sample? | **No.** Bootstrap median 0.565 — almost exactly on the nuisance-only line (0.557). 24% of bootstrap resamples land below chance. |
| Step 1a — reference-order fix alone | Does either individual preprocessing fix reproduce the result on its own? | **No.** AUC 0.583, p=0.234 — not significant. |
| Step 1b — ICA fix alone | Same question, other fix | **No.** AUC 0.602, p=0.174 — not significant. |
| Confirm-restore — full-precision re-run | Does the original 0.651 reproduce exactly when both fixes are applied together, at full statistical precision? | **Yes.** AUC 0.6509, CI [0.353, 0.764], p=0.0410 — matches Stage 3 to within rounding. |

The fourth row is not corroborating evidence for the positive framing — it
only confirms the number was computed correctly and is reproducible from
the archived derivatives. It says nothing about whether 0.651 reflects a
real, generalizable effect, which is exactly what the first three rows
speak to.

## 2. The full picture across every condition tested

| Condition | AUC | 95% CI | p | n | Significant? |
|---|---|---|---|---|---|
| Original Phase 3 (both bugs present) | 0.474 | [0.266, 0.702] | 0.577 | 64 | No |
| Reference-order fix alone (Step 1a) | 0.583 | [0.324, 0.750] | 0.234 | 66 | No |
| ICA fix alone (Step 1b) | 0.602 | [0.315, 0.739] | 0.174 | 64 | No |
| **Both fixes together (Stage 3 / confirm-restore)** | **0.651** | **[0.353, 0.764]** | **0.041** | **64** | **Yes (marginal)** |
| Nuisance-only (both-fixed cohort) | 0.557 | [0.321, 0.746] | 0.261 | 64 | No |

## 3. Interpretation

**Neither preprocessing fix, applied alone, reproduces significance.** The
ICA fix is the larger single contributor (0.602 vs. 0.583 for the
reference-order fix, and it separates further from its own nuisance-only
baseline), but neither gets close to p<0.05 on its own. Only the specific
combination of both fixes, applied to this specific 64-subject sample,
crosses the significance threshold.

That pattern — a marginal result that requires a specific combination of
choices on a specific sample to appear — is the signature this project's
own prior research flagged as most concerning (Button et al. 2013's
"winner's curse": underpowered studies that just barely cross significance
systematically overstate the true effect). It is reinforced, independently,
by Step 0's finding that the same 64-subject sample's own resampling
distribution puts a quarter of its mass below chance. Two different methods
— attribution and resampling — arrive at the same conclusion by different
routes, which is stronger evidence than either alone.

**This is not a case of "we found something real but can't yet prove which
part of the pipeline explains it."** If that were true, isolating the fixes
would show at least one of them producing a result close to 0.651 on its
own, with the other contributing only a marginal boost. Instead, both
isolated results land closer to the *original null* (0.474) than to the
*combined positive* (0.651), and neither is statistically distinguishable
from its own nuisance-only baseline. The combination effect looks like a
property of this specific sample, not a converging pair of real, additive
biological signals.

## 4. What this changes about delivery

Per the checkpoint questions already answered in
`reports/phase5_stage3_checkpoint.md` and reaffirmed here:

- **Do not deliver AUC 0.651 as a positive finding.** Every independent
  check available with this dataset argues against it, and none support
  it beyond the single original point estimate.
- **Do deliver the full, honest account**: two real preprocessing bugs
  were found and fixed (both independently justified, documented in
  `reports/phase5_ica_component_evaluation.md` and Stage 1's checkpoint,
  regardless of what they do or don't prove about the primary target);
  the resulting number moved from a clean null to a marginal positive;
  that positive was then stress-tested with three independent methods and
  did not survive any of them. This is a complete, useful answer to "does
  this dataset support a real EEG-based classifier for this target at this
  sample size" — the answer is no, and now demonstrated four different
  ways rather than asserted once.
- **The ceiling on what this dataset can support was already known before
  this validation work began** (power analysis, `report.md`/checkpoint):
  79 subjects is a hard cap, no independent replication cohort exists.
  Nothing in Step 0/1/confirm-restore changes that; it only closes off the
  one plausible route (a corroborated positive) by which this ceiling
  might not have mattered.

## 5. Artifacts

| Artifact | Path |
|---|---|
| Step 0 — stability/sensitivity report | `reports/phase5_stage3_stability.md` |
| Step 0 — raw resample data | `reports/phase5_stage3_stability_resamples.csv`, `_summary.csv` |
| Step 1a — reference-order fix alone | `reports/phase5_stage1b_reference_order_only.md` |
| Step 1b — ICA fix alone | `reports/phase5_stage1c_ica_only.md` |
| Isolation run scripts | `scripts/phase5_stage1_isolation_run.py`, `scripts/phase5_stage3_stability.py` |
| Confirm-restore script + meta | `scripts/phase5_stage3_confirm_restore.py`, `data/derivatives/models_stage3/confirm_restore_meta.json` |
| Archived isolation-condition features (small, kept) | `data/derivatives/features_stage1a_refonly_TEMP/`, `features_stage1b_icaonly_TEMP/` |
| This report | `reports/phase5_stage3_validation.md` |
| Updated final report | `reports/phase5_final_report.md` |

**Note on the isolation-condition preprocessed EEG derivatives**: the two
~26GB preprocessed-EEG trees for the isolated conditions
(`preproc_stage1a_refonly_TEMP`, `preproc_stage1b_icaonly_TEMP`) were
deleted after this report was written, to relieve a disk-full condition
(D: was at 100%/6.8GB free). Their statistical conclusions (§1-2 above) are
fully captured here and in `phase5_stage1b_reference_order_only.md`/
`phase5_stage1c_ica_only.md`; the small feature CSVs derived from them are
kept. Either condition is exactly reproducible by setting
`config/preproc.yaml`'s `reference.compute_order`/`ica.n_components` to
the documented isolated values and re-running `pearl_preproc.cli run-all`,
if the raw preprocessed derivatives are ever needed again.

**Production state note:** `data/derivatives/preproc/` and
`data/derivatives/features/` are restored to the both-fixes-applied
condition (config/preproc.yaml back at its permanent defaults:
`reference.compute_order: post_interpolation`, `ica.n_components: 0.99`)
— i.e. the same derivatives that produced the 0.651 number, confirmed
reproducible in §1 above. The isolation-condition trees above are kept as
audit trail, not as the live/delivered state.
