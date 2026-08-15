# Phase 6 Stage A — Bounding the Null

**Prepared:** 2026-08-15 · **run_id:** `20260815T210714Z-4bb18cc`

---

## Verdict, up front

**The genotype null is now BOUNDED, not merely inconclusive.** The same 9
resting-state spectral features that fail to predict genotype group (AUC 0.506,
p=0.48) **do** predict a control target — sex — on the identical cohort,
preprocessing, and cross-validation protocol (**AUC 0.688, p=0.019**). The
representation demonstrably carries subject-level information. It finds none for
genotype.

**This report adds ZERO new genotype looks.** It evaluates only control targets
and re-cites one already-published genotype number. Phase 5's delivered verdict
(0.651 not validated; do not report as positive) is **unchanged**.

---

## 1. Why this was run

Phase 3's control battery left an ambiguity unresolved since: the PSWT feature
family scored **0.465 on sex** — a *failed positive control* against a declared
floor of 0.65. Sex is reliably decodable from resting EEG in adequately powered
samples, so that failure meant the genotype null could not be distinguished from
a more mundane possibility: *a representation that discards between-subject
information will return a null for any target.*

`phase_6.md` proposed a multi-week "representation rebuild" premised on that
ambiguity. Before committing, we checked whether it was real.

**It was already resolved in the project's own data, and never assembled in one
place.** `reports/phase4_control_diagnostic.md` ran a 3-rung ladder against sex
and found two rungs significant (0.693 p=0.013; 0.685 p=0.024). Only PSWT failed.

That argument was not airtight, for two reasons this report fixes:

1. **Mismatched feature sets** — Phase 4's sex result used 16 columns
   (rest+MSIT); the genotype comparison used 9 (rest-only).
2. **Mismatched preprocessing** — Phase 4 predates Phase 5's two preprocessing
   fixes; the genotype numbers postdate them.

## 2. Method

`pearl_models.positive_controls.run_sex_control` reused **unchanged** (it already
accepts the feature frame as an argument, so it generalises across
representations). Frozen `config/models.yaml` at **full precision** — 5-fold ×
10 repeats, 1000-permutation test, 2000-resample bootstrap CI — because these are
*reported* numbers, not diagnostics. Sex from `participants.tsv` (34/30, no
missing values). All four representations on the same frozen 64-subject rest
cohort and the same Phase-5-corrected preprocessing.

Script: `scripts/phase6_control_matrix.py` (resumable; writes partial results
after each representation). Raw output: `reports/phase6_control_matrix.json`.

## 3. Results — the control matrix

Every cell reported, including the failure. Reporting only the winner would be
the same error as feature-family shopping.

| Representation | Cols | Sex AUC | 95% CI | perm p | Verdict |
|---|---|---|---|---|---|
| `baseline_rest` | 9 | **0.688** | [0.431, 0.816] | **0.0190** | PASS |
| `baseline_rest_msit` | 16 | **0.696** | [0.421, 0.826] | **0.0070** | PASS |
| `baseline_all` (adds Sternberg) | 23 | **0.652** | [0.373, 0.819] | **0.0290** | PASS |
| `pswt` | 18 | 0.465 | [0.272, 0.700] | 0.6194 | **FAIL** |

**Three of four representations decode sex significantly. Only PSWT fails** —
and it fails decisively (p=0.62, essentially chance).

### 3a. Verification

Both pre-declared checks passed:

- **Smoke test** — `pswt` reproduced Phase 5 Stage 3's sex control *bit-exactly*:
  AUC 0.4645 / CI [0.2715, 0.7000] / p=0.6194, against the reported 0.465 /
  [0.272, 0.700] / 0.6194. The harness is deterministic and the on-disk
  derivatives have not drifted.
- **Phase 4 reproduction** — `baseline_rest_msit` landed at 0.696 against Phase
  4's 0.693 on the same 16 columns. A 0.003 difference across a preprocessing
  change; the two Phase 5 fixes did not disturb the sex control.

### 3b. Incidental observation

`baseline_all` (23 cols, adding Sternberg) scores **lower** than
`baseline_rest_msit` (16 cols): 0.652 vs 0.696. Adding the Sternberg block
diluted rather than added signal — the same pattern Phase 4 recorded when PSWT
was combined with baseline (0.556, non-significant, from two individually
significant components). Noted, not interpreted; no follow-up is proposed, since
chasing it would be exactly the feature-shopping this project forbids.

## 4. The bounded null

| Target | Features | AUC | p | Outcome |
|---|---|---|---|---|
| **Sex** (control) | 9 rest-only spectral | **0.688** | **0.019** | Signal detected |
| **Genotype** (primary) | 9 rest-only spectral — *identical* | 0.506 | 0.482 | Nothing |

Genotype source: `reports/phase5_stage3_results.md` §5 — already published, **not
re-run** for this report.

**Interpretation.** Matched on features, cohort, preprocessing, and protocol, this
representation detects a real subject-level trait and detects nothing for
genotype. The genotype null is therefore a statement about **genotype**, not an
artifact of a representation that discards between-subject variance.

**What this does not claim.** It bounds the null *for the representations tested*.
It does not prove no representation could find genotype signal — see §7.

## 5. Power analysis

Full output: `reports/phase6_power_analysis.txt` (script:
`scripts/phase6_power_analysis.py`). n=34 vs 30, α=0.05 two-sided:

| Quantity | Value |
|---|---|
| Minimum detectable AUC at 80% power | **0.693** |
| Minimum detectable AUC at 90% power | 0.720 |
| Power to detect the published benchmark (0.58) | **20%** |
| Power to detect AUC 0.65 | 57% |

**All three passing sex results sit at or near the 80%-power floor** (0.688,
0.696, 0.652 against an MDE of 0.693). This cohort can *just barely* resolve
effects of that size. Sex is among the most robustly encoded subject-level traits
in resting EEG; genotype risk group is far subtler. That is the quantitative case
against further genotype hunting on this cohort.

### 5a. Why `phase_6.md`'s proposed Gate 1 is not achievable here

`phase_6.md` §2 sets the pass rule at *AUC ≥ 0.65 **and** bootstrap lower bound
> 0.50*. Empirically:

| Result | AUC | perm p | CI lower | Clears the gate? |
|---|---|---|---|---|
| `baseline_rest` (this report) | 0.688 | 0.019 | 0.431 | **No** |
| `baseline_rest_msit` (this report) | 0.696 | 0.007 | 0.421 | **No** |
| `baseline_all` (this report) | 0.652 | 0.029 | 0.373 | **No** |
| Phase 4 rung 1 | 0.693 | 0.013 | 0.402 | **No** |
| Phase 4 rung 3 | 0.685 | 0.024 | 0.418 | **No** |

**Every genuinely significant sex result this project has ever produced would
fail that gate** — including one at p=0.007. The cause is measurable: the
cross-validated bootstrap CI runs ~0.39–0.45 wide against an analytic
(Hanley–McNeil) minimum of 0.257, because refitting the model inside every
bootstrap resample adds variance beyond the AUC estimate itself. Clearing a 0.50
lower bound would need AUC ≈ 0.78 — above anything this cohort has produced, and
at the top of the published range for resting-EEG sex decoding.

**Recommendation:** any future gate should use the **permutation test** as the
primary criterion — it correctly detected all five real effects above — with the
AUC floor set from the power analysis. Report the CI honestly; do not make it a
pass/fail threshold it cannot clear.

### 5b. Age is not a usable control in this cohort

`phase_6.md` §2 proposes age as a second control ("age is also robustly encoded
in resting EEG"). True in general, **false here**: this cohort spans only
**50–63 years** (n=64, median 55, range 13 years), with extreme tertiles ~4 years
apart. Published EEG brain-age prediction achieves MAE ≈ 7 years — larger than
the cohort's entire usable separation. An age control would fail for reasons
unrelated to representation quality, and that failure could be misread as
evidence against a representation that is fine. Reported descriptively only;
never used as pass/fail evidence. *"This cohort is too age-homogeneous to support
an age control"* is itself a real bound on the dataset.

## 6. Look history

Per `phase_6.md` §5b, stated explicitly: the genotype target has been examined
**four** times (Phase 3; Phase 5 both-fixes; reference-order-alone; ICA-alone).
**This report adds none.** It evaluates control targets only and cites one
already-published genotype number. Any future genotype analysis would be look #5
and must be pre-registered before running.

## 7. What this changes for delivery

- The delivered verdict is **unchanged**: Phase 5's 0.651 remains not validated.
- The *characterisation* is materially stronger — from "we found nothing" to
  "we established what this dataset can and cannot support, and bounded the
  null," now backed by three independent significant control results.
- A concrete ceiling is on record: this cohort's 80%-power detection floor is
  AUC 0.693, with 20% power against the published benchmark.

## 8. On `phase_6.md`'s Stage B (representation rebuild)

Still available, now specified and sized: **≈10 person-days engineering + 1.5–3
days compute**. Its realistic best outcome is a *further-strengthened bound*, not
a positive finding — `phase_6.md` §10 concedes as much ("the least probable
outcome is a validated positive"). Given 20% power against the benchmark effect
and four prior looks, the most likely route to a "positive" there is a false one.
Decide it as scope, not as hope.

Two findings from the Stage B design review are worth recording regardless:
- **No new dependencies are required** — the SPD/Riemannian math is ~60 lines on
  `numpy` + `scipy.linalg.eigh` with exact algebraic invariants to test against,
  following this project's own precedent (`baseline.aperiodic_fit` is a
  hand-rolled FOOOF heuristic chosen to avoid a heavyweight dependency).
- **A real technical trap**: covariance rank is severely and *variably*
  rank-deficient here (ICA removes 4–47 components per subject; effective rank
  ~16–50 of 127), and rank tracks `n_ica_removed`, an existing declared nuisance
  variable. A covariance representation could decode *cleaning aggressiveness*
  rather than brain signal. Any Stage B must test against
  `n_ica_removed`/`n_bad_channels`/`artifact_frac` before any genotype look.

## 9. Artifacts

| Artifact | Path |
|---|---|
| Control matrix script (resumable) | `scripts/phase6_control_matrix.py` |
| Control matrix raw results | `reports/phase6_control_matrix.json` |
| Power analysis script | `scripts/phase6_power_analysis.py` |
| Power analysis output | `reports/phase6_power_analysis.txt` |
| This report | `reports/phase6_bounded_null.md` |
| Phase 4 ladder (prior evidence) | `reports/phase4_control_diagnostic.md` |
| Genotype reference (not re-run) | `reports/phase5_stage3_results.md` §5 |
