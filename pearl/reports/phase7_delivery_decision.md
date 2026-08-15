# Phase 7 — Delivery Decision: What Ships

**Date:** 2026-08-15 · **Status:** FINAL

---

## The decision

| Question | Decision |
|---|---|
| Which preprocessing pipeline ships? | **Phase 5 corrected** (reference-order fix + explained-variance ICA) |
| Which model ships as a scoring artefact? | **None.** No model is delivered for prediction. |
| Is a model bundled at all? | Yes — the Stage 3 model, as a **frozen reference artefact** for reproduction only, marked not-validated |
| What happens to the Phase 3 frozen tree? | **Untouched, byte-for-byte** |

## Why

### The pipeline: ship the corrected one

The two Phase 5 fixes are correct on their own merits, independent of what they
did or didn't do to the result:

- **Reference-order** — the average reference was computed *before* bad-channel
  interpolation, letting a bad channel contaminate every other channel. Fixing
  the order is unambiguously correct signal processing.
- **ICA `n_components`** — a fixed 30 components caused excess ICLabel removal on
  high-bad-channel subjects; explained-variance selection scaled to each
  subject's post-interpolation rank is better justified
  (`reports/phase5_ica_component_evaluation.md`).

Both are now the permanent default in `config/preproc.yaml`. Anyone running new
data through this pipeline should get the corrected version. Shipping the
known-buggy Phase 3 preprocessing as the live path would be a defect.

### The model: ship none for scoring

**The model does not detect its target.** That is not a hedge, it is the
finding:

- the only positive result it ever produced (AUC 0.651, p=0.041) was **retracted**
  after failing resampling and attribution checks (`phase5_stage3_validation.md`);
- the null was then shown to be **real rather than a measurement artifact** — the
  same features detect sex (AUC 0.688, p=0.019) on the identical cohort and
  protocol while detecting nothing for genotype (AUC 0.506, p=0.48)
  (`phase6_bounded_null.md`).

A scoring endpoint implies the number means something. It does not. Presenting
it as actionable would be the single most damaging thing this engagement could
ship, because it would convert a rigorous negative result into a false positive
in someone else's hands.

### But the model is still bundled — as a reference artefact

Deleting it would make the reported numbers unreproducible. So the Stage 3 model
ships **with its model card, marked not-validated**, purely so a reader can
regenerate the figures in the reports. Its purpose is provenance, not
prediction.

## How this is enforced in code

Not by documentation alone — documentation gets skimmed:

1. **`delivery._DISCLAIMER`** now opens with `THIS MODEL WAS NOT VALIDATED AND
   DOES NOT DETECT ITS TARGET`, states the output carries no demonstrated
   predictive meaning, and cites the two reports. It is a **single definition**,
   imported by `inference.py` rather than duplicated.
   *This mattered:* `inference.py` — the path the container and API actually
   serve — previously carried its **own copy** of the old, weaker wording, so
   strengthening the disclaimer in `delivery.py` alone would have left the
   shipped surface unchanged. That duplication is now removed.
2. **Machine-readable flags** on every scored and cannot-score response:
   `"actionable": false` and `"not_validated": true`. A consumer that ignores
   prose still cannot claim it wasn't told.
3. **Tests pin all of the above** (`tests/test_delivery_not_validated.py`),
   including a guard against regressing to the pre-Phase-7 "research score"
   framing, which implied the number meant something merely non-clinical.

## What was explicitly *not* done

- **The Phase 3 frozen tree is untouched.** `data/derivatives/models_phase3to4_frozen/`
  and every `*_frozen` path remain byte-for-byte as delivered. Both the original
  null and the Phase 5 episode remain independently reproducible.
- **The scoring code path was hard-disabled in meaning, not deleted.**
  `score_subject` / `score_bids_subject` / the `/score` endpoint still execute,
  because deleting them would break reproduction of the reported numbers — but
  every response now carries the not-validated disclaimer and the
  `actionable: false` flag. The capability is preserved for reproduction and
  neutered for prediction.

## Correction to an earlier claim

An earlier draft of this phase's notes stated that the `/score` endpoint had a
path-matching bug (`"\score"` with a backslash, never matching). **That is
false.** The code reads `"/score"` correctly. The claim originated in an
automated code survey and was repeated without verification; it is recorded here
so it does not propagate.

## Cross-references

- `reports/phase7_stop_decision.md` — why no further analysis runs
- `reports/phase6_bounded_null.md` — why the null is bounded
- `reports/phase5_stage3_validation.md` — why 0.651 was retracted
- `data/derivatives/models_stage3/model_card_corrected.md` — the bundled artefact
