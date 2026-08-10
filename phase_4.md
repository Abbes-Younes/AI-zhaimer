# Phase 4 — Diagnostic Closeout, Packaging & Handover

**Agent instructions. Read this whole file before writing any code.**

Phase 3 delivered a clean null and shipped a correctly-positioned artefact. The
engineering question is effectively answered. Phase 4 does four things and then
the project is finished:

1. resolves the **one ambiguity that changes how the null must be worded**
2. documents two feature-definition defects found during Phase 3
3. packages the tool and proves it reproduces from a clean clone
4. produces the client-facing deliverable and handover pack

**Non-goals.** No new feature families. No re-running the primary analysis. No
attempt to improve AUC. The primary verdict is frozen: `NULL`, AUC 0.474.
Nothing in this phase can change it, and nothing in this phase may be presented
as changing it.

---

## 0. Task A — the one remaining diagnostic

### 0a. Why this is legitimate and not a second attempt

Phase 3's §10 stop list names "wanting to try a fourth feature family after
seeing a result" as the failure mode to avoid. This task is not that, and the
distinction must be stated in the code, the config, and the report:

> This diagnostic runs against a **positive control target (sex)**, never
> against the primary target. It cannot change the primary verdict. Its only
> output is which of two sentences the final report is entitled to write.

Any drift toward running these diagnostics on `binary_risk_vs_none` invalidates
the entire Phase 3 result. Enforce it: the diagnostic module must raise if the
target is anything other than the declared control targets.

### 0b. The ambiguity to resolve

Positive control 1a passed strongly (0.830) — the features measure real alpha
waveform shape. Control 1b (sex) came back at chance (0.486). Sex is generally
reported as detectable from resting EEG, though typically with larger samples
and much richer feature sets than 20 ROI-averaged waveform-shape features, so a
chance result here is not by itself alarming. It is, however, **ambiguous**, and
the ambiguity propagates directly into what the null means:

- If **nothing** in this dataset predicts sex, the limitation is cohort-level —
  sample size, preprocessing, or subject-level aggregation — and the genotype
  null is **inconclusive**.
- If **something** predicts sex but the PSWT features don't, the limitation is
  specific to that feature family, and the genotype null is a **real null for
  the pitch-synchronous approach on resting alpha** — a far more informative and
  more defensible statement.

That is a materially different paragraph in the client report, and it costs
about a day to settle.

### 0c. The ladder — run in order, stop at the first pass

Same CV machinery, same 64-subject cohort, target = sex throughout.

| Rung | Features | Interpretation if it passes (AUC clearly > chance) |
|---|---|---|
| 1 | `features_baseline.csv` (16 spectral) | spectral features generalise across subjects; PSWT family specifically does not |
| 2 | PSWT + baseline combined | combination carries subject-level signal |
| 3 | Per-channel (not ROI-averaged) band power, all 127 channels, computed fresh from the Phase 1 derivatives | ROI averaging is what destroyed between-subject variance |

Rung 3 is the only one requiring new computation, and it is deliberately last —
it tests the aggregation hypothesis directly. Cap it there. If all three land at
chance, the answer is "nothing in this cohort predicts sex at subject level,"
and you stop.

Declare all three rungs in config **before running any of them**, and report all
three outcomes regardless of where you stop reading. Reporting only the rung
that worked is the same sin as trying a fourth feature family.

### 0d. The decision table — write it before running

| Outcome | Final report says |
|---|---|
| Any rung clearly above chance | "The pitch-synchronous feature family did not detect genotype group, on a cohort where other EEG features do carry subject-level information. This is a negative result for the method as applied here." |
| All three at chance | "No subject-level EEG signal of any kind was detectable in this cohort at n=64, including a target known to be detectable in larger samples. The genotype result is therefore **inconclusive**, not negative." |

Write `reports/phase4_control_diagnostic.md`, verdict-first, with the decision
table reproduced and the outcome marked.

---

## 1. Task B — document the two feature-definition defects

Phase 3's stability analysis surfaced two real problems in the Phase 2 feature
set. Neither changes the null, both belong in the record.

**`harmonic_amplitude_profile_h1_median` / `h1_iqr` are tautologically
constant.** Harmonic 1 normalised to the fundamental is exactly 1.0 for every
cycle. The declared feature count was 20; the effective count was 18. Fix the
definition in `config/features.yaml` (drop them, or normalise to total harmonic
energy instead), regenerate the feature dictionary, and state clearly that the
Phase 3 analysis ran with 18 informative features — **without re-running the
primary analysis**, since dropping two constant columns cannot change an L2
logistic regression's output.

**`harmonic_amplitude_profile_h5_*` correlates with recording duration**
(r=0.81, 0.96 on the subset where non-missing) and is NaN for 53 of 64 subjects
by design — the 50 Hz exclusion doing its job. A feature present for 11 subjects
and correlated with duration is not usable. Mark it as such in the dictionary,
and record the design lesson: the 50 Hz harmonic exclusion should have been
applied at the *profile* level rather than leaving a mostly-empty column in the
declared set.

Both go into an annex of `reports/phase4_final_report.md` under known defects.
Add regression tests asserting no declared feature is constant across the cohort
and that no feature exceeds a stated missingness threshold without being flagged.

---

## 2. Task C — merge, hygiene, clean-clone reproducibility

- Merge `phase3-modeling-validation-delivery` to `master`. Tag the merge commit
  `v1.0-phase3-null` so the state that produced the reported number is
  permanently addressable.
- **Clean-clone test, run for real:** fresh clone into an empty directory, fresh
  venv, `pip install -e ".[dev]"`, `pytest`. Everything must pass with no
  manual steps beyond what the README documents. Record the result.
- Verify all phase specs (`phase_0.md` … `phase_4.md`), reports, and configs are
  tracked. Confirm `data/`, `.venv/`, `.cache/` remain ignored.
- Pin dependency versions in `pyproject.toml`. A reproducibility claim that
  floats on `mne>=1.6` is not a reproducibility claim.
- Produce `reports/provenance_chain.md`: one page tracing
  `participants_tsv_sha256` → Phase 1 `run_id` → Phase 2 `run_id` → Phase 3
  `run_id` → shipped model hash. Anyone should be able to verify the reported
  number came from the data claimed.

---

## 3. Task D — package the tool

The contracted deliverable was a deployable pipeline. It exists; make it
installable and runnable by someone who is not you.

- **Containerise.** A Dockerfile that builds the environment and exposes the
  inference path: BIDS EEG in → Phase 1 preprocessing → Phase 2 features →
  calibrated score with uncertainty and the OOD refusal → JSON out.
- **CLI + thin API**, both hitting the same code path, both returning the
  provenance sidecar and the research-artefact disclaimer already implemented in
  Phase 3.
- **End-to-end smoke test** on one held-back subject's raw files, run inside the
  container, asserting the output JSON schema and the disclaimer's presence.
- **`INSTALL.md` and `RUNBOOK.md`:** how to install, how to score a subject, how
  to interpret the output, what the OOD refusal means, what to do when it fires,
  and the disk/bandwidth requirements for reprocessing from raw.

Do not soften the positioning to make the tool more marketable. The model card
already says it isn't fit for prediction; the container must say the same thing.

---

## 4. Task E — the client deliverable

`reports/phase4_final_report.md` (+ self-contained `.html`) is the artefact the
client actually reads. It is not the Phase 3 results report with a new title.

Structure, verdict-first:

1. **What was asked and what was delivered** — one paragraph each.
2. **Headline finding.** The null, with CI and permutation p, in plain language.
   Say directly that resting-state EEG waveform-shape features did not
   distinguish the genetic risk groups in this cohort.
3. **Why this is a trustworthy result, not a failed one.** This is the section
   that justifies the engagement, and it is entirely earned: labels
   independently verified against the source genotypes (79/79); no demographic
   confounds; a confound gate run before any feature existed; label-blind
   preprocessing and feature extraction; a pre-registered analysis plan frozen
   before features; permutation null verified at chance; positive controls run.
   Most published work of this shape does fewer of these things.
4. **The caveat from Task A**, worded per §0d.
5. **What the result does and does not license.** It does not say APOE/PICALM
   status is invisible in EEG. It says this method, on this cohort, at this
   sample size, did not detect it.
6. **What would be needed to answer the question properly** — larger cohort,
   task-state EEG with richer feature engineering (the benchmark gap in Phase 3
   §8.3 is informative here), the deferred Option C reprocessing, and Sternberg
   which is now affordable under the streaming design.
7. **Deliverables index** — every artefact, where it lives, what it contains.
8. **Known defects annex** (Task B) and limitations.

Keep it readable by a non-specialist. The client's classification document was
written in French; ask whether they need a French version before assuming
English is fine.

---

## 5. Task F — handover pack

- `HANDOVER.md`: repo map, how each phase's code relates, where every reported
  number comes from, which decisions were frozen and why, and the full list of
  deferred items with the cost of each.
- Data retention: state what is on disk (17.73 GB derivatives), what can be
  deleted, and what must be kept to reproduce the reported numbers.
- A short "if you resume this project" section — the first three things a future
  developer should read, in order.

---

## 6. Explicitly out of scope — quote separately

None of the following belong in this phase, and none should be absorbed into
the current engagement:

- **Option C reprocessing** (~46 GB re-download, fixing reference order and ICA
  `n_components`), plus the full re-run of Phases 1–3 that follows it
- **Richer MSIT feature engineering** to close the benchmark gap characterised
  in Phase 3 §8.3
- **Sternberg task** ingestion and analysis
- Any attempt to recover the 15 subjects excluded at QC

Each is defensible work. Each is new scope. Say so in the handover, with a rough
size against each, so the conversation about a Phase 5 starts from a written
baseline rather than from an assumption that it was always included.

---

## 7. Definition of done

- [ ] Task A ladder run in declared order, all rungs reported, decision table
      applied
- [ ] Diagnostic module raises if pointed at the primary target
- [ ] h1 / h5 defects documented; constant-feature and missingness tests added
- [ ] Branch merged, tagged, clean-clone `pytest` green with no manual steps
- [ ] Dependencies pinned
- [ ] `reports/provenance_chain.md` traces data hash → shipped model
- [ ] Container builds; end-to-end smoke test passes inside it
- [ ] `INSTALL.md`, `RUNBOOK.md`, `HANDOVER.md` written
- [ ] `phase4_final_report.md` + `.html` complete, verdict-first, non-specialist
      readable
- [ ] Out-of-scope items listed with rough sizing
- [ ] `pytest` green; everything under one `run_id`

---

## 8. Stop and escalate if

- any diagnostic rung is run against `binary_risk_vs_none`
- the clean-clone test fails in a way the README doesn't cover
- the container's output omits the research-artefact disclaimer
- anyone proposes revising the primary verdict on the strength of Task A

The project's value at this point is that its null is trustworthy. Everything in
this phase either protects that or hands it over cleanly.