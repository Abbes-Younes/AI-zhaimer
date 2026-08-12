# Phase 5 Stage 4 — Delivery

**Agent instructions.** Stage 3 (`phase_5_stage3.md`) produces the one
primary-target result Phase 5 is entitled to report. This stage packages
and communicates it — it does not reopen or re-touch the primary analysis.

## 0. Scope, deliberately smaller than Phase 4's original Task D

`pearl_models.pipeline.run()` (reused unchanged in Stage 3) already trains
and versions a final calibrated model, writes a model card, and provenance
JSON as part of its own orchestration — that is not separate work here.
What Phase 4 additionally did (Task A control-diagnostic ladder, Task D
containerization) is **not automatically repeated**:

- **Control diagnostic ladder**: only re-run if Stage 3's positive control
  1b (sex classification) lands ambiguously the way the original did
  (1a high, 1b at chance) — otherwise it adds nothing new to interpret.
- **Re-containerization**: explicitly deferred. The existing
  `Dockerfile`/`INSTALL.md`/`RUNBOOK.md` from Phase 4 continue to serve the
  **original, frozen Phase 3 model** — safer than modifying a tested
  container path under time pressure, and not required to report Phase 5's
  results honestly. Stated here as a known deferred item, not silently
  skipped.

## 1. What this stage actually produces

- [ ] `reports/phase5_stage3_results.md` (written as part of Stage 3, verdict-first)
- [ ] Stage 3's versioned model/model card/provenance saved under
      `data/derivatives/models_stage3/`, clearly labeled, coexisting with
      the untouched original at `data/derivatives/models_phase3to4_frozen/`
      (and the still-live, restored `data/derivatives/models/` = original)
- [ ] `reports/phase5_final_report.md`: non-specialist, verdict-first,
      covering all of Phase 5 (Stages 1-3) the way
      `reports/phase4_final_report.md` covered the original engagement —
      what was asked (close the gap to SOTA), what was found at each stage,
      the final number, honestly positioned
- [ ] `HANDOVER.md` updated with a short Phase 5 section: what changed,
      where the new artifacts live, what's still deferred (Option-C-style
      re-download was already done in Stage 1; re-containerization is the
      new deferred item)
- [ ] `pytest` green, everything committed

## 2. Non-goals

- No new modeling, no touching Stage 3's frozen numbers
- No claim that Stage 3's model supersedes or replaces the original —
  both are versioned, both are real, the final report states which is
  which and why
