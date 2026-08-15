# Phase 7 — Consolidation, Repositioning & Final Delivery

**Agent instructions. Read this whole file before writing any code.**

The research question is answered. Phase 6 Stage A bounded the null, established
the cohort's detection ceiling, and did so without adding a genotype look. This
phase closes the engagement properly.

**No new analysis of any kind runs in this phase.** No new features, no new
targets, no Stage B, no fifth genotype look. Every number that will be delivered
already exists on disk. Phase 7 is packaging, repositioning, and handover.

---

## 0. Task A — record the stop decision formally

Write `reports/phase7_stop_decision.md` and commit it. This exists so the
decision is not casually revisited by a future reader (or a future you) who
sees "Stage B: specified but not run" in the handover and assumes it was merely
unfinished.

State, with the numbers:

- **Decision:** Stage B (representation rebuild) will not be run. The genotype
  investigation is closed at four looks.
- **Grounds, in order:**
  1. MDE at 80% power is AUC 0.693; all three passing sex controls (0.688,
     0.696, 0.652) sit at or below that floor. The cohort can just barely
     resolve one of the most robustly encoded traits in resting EEG. There is
     no headroom for a subtler one.
  2. Power against the published 0.58 benchmark is 20%. At four prior looks, a
     marginal Stage B positive is more likely to be a false one than a real one
     — the Phase 5 episode is the worked example.
  3. The covariance rank confound recorded in `phase6_bounded_null.md` §8:
     effective rank (16–50 of 127) tracks `n_ica_removed`, an existing declared
     nuisance variable. Stage B's most likely failure mode is not a null but a
     *misleading positive* attributable to cleaning aggressiveness, costing a
     further validation cycle to eliminate.
  4. Marginal evidentiary gain is small: three independent significant control
     results already establish that the representation carries subject-level
     information.
- **What would change this:** a new cohort, or an independent genotyped EEG
  dataset. Not more work on these 64 subjects.

Cross-reference it from `HANDOVER.md` so Stage B's entry reads "declined, with
reasons" rather than "pending".

---

## 1. Task B — reposition the deliverable

This is the most important task in the phase, and it is a writing task, not a
code one.

The contracted deliverable was a "deployable pipeline or tool." What exists is a
classifier that does not classify. Shipping that as a predictor would be
dishonest; shipping nothing would understate what was built. The correct framing
is already true and needs only to be stated:

> **The deliverable is a validated, reproducible EEG analysis pipeline and the
> bounded null it produced — not a predictor.**

Concretely, the pipeline is: BIDS ingestion → label-blind preprocessing with two
independently-justified fixes → PSR/PSWT and spectral feature extraction →
a pre-registered CV/permutation/bootstrap evaluation harness → provenance-traced
reporting. That is reusable infrastructure with demonstrated correctness, and it
is what a future cohort would be run through.

Apply this framing consistently in:

- `model_card.md` — must lead with "this model does not detect its target"
  before any performance number appears. Intended use becomes *reference
  implementation and reproducibility artefact*, not scoring.
- The container's emitted JSON — the disclaimer already implemented must be
  strengthened from "research score" to an explicit statement that the model
  was not validated and its output carries no demonstrated predictive meaning.
- `RUNBOOK.md` — reframe "how to score a subject" as "how to reproduce the
  reported analysis on a subject."
- The client report (§4).

Do not soften this to make the deliverable sound better. The rigour *is* the
product; undercutting it to sell a null classifier destroys the only thing of
value here.

---

## 2. Task C — decide and document which model ships

Currently the container serves the **frozen Phase 3 model**, trained on
preprocessing that contains two bugs now known to be real and since fixed. That
is a genuine deliverable defect and it needs an explicit decision, not a default.

Recommended resolution:

- **Ship the Phase 5 corrected-preprocessing pipeline**, because the two fixes
  (reference-order, explained-variance ICA) are correct on their own merits and
  are now the permanent default. A future user running new data should get the
  correct pipeline.
- **Ship no model as a scoring artefact.** Per Task B, the container's purpose
  is reproduction, not prediction. Bundle the Stage 3 model as a *frozen
  reference artefact* with its model card, clearly marked not-validated, so the
  reported numbers can be reproduced — and remove or hard-disable any code path
  that presents a score as actionable.
- Keep the Phase 3 frozen tree byte-for-byte as it is. Nothing gets overwritten.

Write the decision and its rationale into `reports/phase7_delivery_decision.md`,
then re-containerise per §3.

---

## 3. Task D — fix the overwrite risk before anything else runs

`HANDOVER.md` records this as a known unfixed code gap, worked around manually at
every Phase 5 stage. It is the single highest-risk item left in the codebase:
report-writing functions in `pearl_preproc`, `pearl_features` and `pearl_models`
use **hardcoded output paths** shared with the original Phase 1–4 artefacts, and
some **hardcode narrative text** describing an expected result.

A future re-run silently overwrites the original deliverables in place and can
emit factually wrong prose — for example, null-assuming narrative shipping
unmodified alongside a positive result, which already happened once and had to
be corrected in `phase5_stage3_checkpoint.md`.

Fix properly:

- All report writers take an output path as a parameter, defaulting to a
  run-scoped directory (`reports/<run_id>/`), never a fixed filename.
- **Refuse to overwrite an existing report** unless an explicit
  `--allow-overwrite` flag is passed; archive-before-write otherwise.
- Delete every hardcoded result-describing sentence. Narrative text is generated
  from the computed numbers or it is not generated at all. If a template needs a
  verdict word, it reads it from the result object.
- Add tests: a report writer pointed at an existing file raises; no report
  module contains a hardcoded verdict string (grep-style assertion).

Do this **first**, before Tasks E and F regenerate anything.

---

## 4. Task E — the consolidated client report

Three separate reports currently tell three chapters of one story, and no
document tells the whole thing. The client should receive one artefact.

Rewrite the LaTeX report as
`reports/final_report_v2.{tex,pdf}` with this structure:

1. **What was asked, what was delivered** — one paragraph each.
2. **Headline, in plain language.** Resting-state EEG did not distinguish the
   genetic risk groups in this cohort, and this is now a *bounded* null: the
   same features detect a real subject-level trait (sex) on the identical
   cohort and protocol.
3. **The three acts, told honestly and in order:**
   - the original null (AUC 0.474)
   - the Phase 5 near-miss (0.651, p=0.041) and why it did not survive
     validation — resampling median on the nuisance line, 24% of resamples
     below chance, neither fix reproducing significance alone
   - the Phase 6 bound, with the control matrix and the power ceiling
4. **Why the near-miss episode is the strongest evidence of rigour in the
   engagement.** A team that reported 0.651 and stopped would have shipped a
   false finding. Say this directly; it is the clearest demonstration of value
   in the whole project.
5. **The detection ceiling.** MDE 0.693 at 80% power, 20% power against the
   benchmark, age unusable as a control because the cohort spans 50–63 years.
   These are findings *about the dataset* and they are useful to anyone else who
   attempts this.
6. **What was built** — per Task B's framing.
7. **What this does and does not license.** It does not say APOE/PICALM status is
   invisible in EEG. It says these representations, on this cohort, at this
   sample size, did not detect it — and quantifies how large an effect would
   have had to be to show up.
8. **What a definitive answer would require** — a new, adequately powered cohort
   sized from the power analysis on record.
9. Deliverables index, limitations, known defects annex.

**Corrections that must land in this version:** the sex-control misdescription
from the previous LaTeX draft (a *failed positive control* described as a passed
negative control), and the three control numbers reconciled across reports with
their preprocessing stated.

Ask whether the client needs a **French version**; their original classification
document was in French and this is the document they will actually read.

---

## 5. Task F — provenance, hygiene, reproducibility

- Extend `provenance_chain.md` to cover Phase 5 and Phase 6. It currently stops
  before the Stage 3 model, with Phase 5's provenance living only in a model
  card. One chain, `participants.tsv` hash → every run_id → every shipped
  artefact.
- Merge outstanding branches; tag the delivered state.
- Pin dependencies.
- **Clean-clone test, run for real:** fresh clone, fresh venv, install, `pytest`.
  No manual steps beyond the README.
- Container rebuilds and its smoke test passes with the Task C decision applied
  and the Task B disclaimer present in the output JSON.

---

## 6. Task G — final handover

Update `HANDOVER.md`:

- Stage B moves from "specified but not run" to **"declined — see
  `phase7_stop_decision.md`"**.
- Add Phase 6 Stage A and Phase 7 to the reading order.
- Update the "if you resume" list — the first document should now be the
  consolidated client report, then the stop decision, then the provenance chain.
- Data retention: confirm what must survive to reproduce every delivered number,
  and what can go.
- Out-of-scope register, each with rough sizing and its current status:
  Stage B (declined, with reasons), Sternberg against the primary target
  (never validated), Option C's remaining questions, independent replication
  (requires new data collection).

---

## 7. Optional — the publishable artefact

Worth raising with the client, not worth doing unasked.

A pre-registered, fully provenance-traced bounded null on a public dataset, with
a characterised detection ceiling and an honest account of a near-miss that
failed validation, is a legitimate short paper or preprint. Negative results on
public neuroimaging datasets are publishable and useful — the power ceiling
alone would save the next team the same months.

If the client has any research or credibility interest, this converts a
commercially disappointing outcome into a citable one. Scope it separately;
do not begin it inside this phase.

---

## 8. Definition of done

- [ ] `phase7_stop_decision.md` written, committed, cross-referenced from HANDOVER
- [ ] Overwrite risk fixed in code, with tests; no hardcoded verdict strings remain
- [ ] Model card, container JSON, and RUNBOOK repositioned per Task B
- [ ] `phase7_delivery_decision.md` written; container serves the decided artefact
- [ ] `final_report_v2` complete, three-act structure, corrections landed
- [ ] French version produced or explicitly declined by the client
- [ ] `provenance_chain.md` covers Phases 5 and 6
- [ ] Clean-clone test passes; dependencies pinned; state tagged
- [ ] `HANDOVER.md` updated, Stage B marked declined
- [ ] `pytest` green

---

## 9. Stop and escalate if

- anyone proposes running Stage B, a fifth genotype look, or any new target
  during this phase
- the clean-clone test fails in a way the README doesn't cover
- the container emits a score without the not-validated disclaimer
- a report writer is found still hardcoding an output path after Task D

---

## 10. Closing note for whoever reads this last

This project answered its question. The answer was "no," and the reason it is
worth having is that the pipeline which produced it was built so that a "yes"
would have been believable — pre-registered, label-blind, provenance-traced, and
willing to kill its own best result when that result failed validation.

The bounded null, the detection ceiling, and the two preprocessing fixes are the
deliverables. Package them as such.