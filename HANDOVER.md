# Handover

This project is closed as of Phase 4 (2026-08-11). Verdict: **NULL** — see
`pearl/reports/phase4_final_report.md` for the client-facing summary.

## Repo map

```
/                              repo root
  phase_0.md … phase_4.md      the five phase specs — READ THE RELEVANT ONE
                                before touching any phase's code; each encodes
                                decisions not visible in the code itself
  report.md                    running engineering status report, phase by phase
  CLAUDE.md                    codebase guidance for AI coding agents (architecture,
                                conventions, commands)
  README.md                    reproduction instructions
  INSTALL.md, RUNBOOK.md        (under pearl/) install + scoring instructions
  docs/superpowers/plans/       full implementation-plan record, one per phase
  PROJECT.md, top-level src/,
  results/, data/bids/,
  freesurfer/                  SUPERSEDED (earlier T1-MRI plan) — ignore
  pearl/                       ALL ACTIVE CODE
    src/
      pearl_audit/              Phase 0: label reconciliation, confound survey
      pearl_preproc/            Phase 1: download, preprocessing, QC
      pearl_features/           Phase 2: confound gate, PSR/PSWT + baseline features
      pearl_models/             Phase 3/4: CV harness, primary analysis, delivery,
                                 control diagnostic, inference/API
    config/                     frozen YAML configs, one per phase's pipeline
    tests/                      pytest, run from pearl/
    reports/                    every phase's written deliverable (verdict-first)
    data/                       GITIGNORED — regenerate via the CLI commands in
                                 README.md, or copy from an existing run
    Dockerfile                  containerized inference path
```

## How each phase's code relates

Three sibling packages (`pearl_audit`, `pearl_preproc`, `pearl_features`),
one per data-handling phase, each label-blind except one sanctioned
reporting module per package (enforced by dedicated tests, not convention).
`pearl_models` (Phase 3/4) is the one package allowed to touch labels — it's
the only phase that fits anything against the primary target. Each later
package reads only the non-label outputs of the earlier ones (feature CSVs,
QC metrics, run IDs) — see `CLAUDE.md` for the full architecture.

## Where every reported number comes from

See `pearl/reports/provenance_chain.md` for the full traced chain:
`participants.tsv` hash → Phase 1 `run_id` → Phase 2 `run_id` → Phase 3
`run_id` → shipped model hash. Every sidecar and `_meta.json` along the way
carries the links.

## Frozen decisions and why

| Decision | Frozen in | Reason |
|---|---|---|
| Primary target: `binary_risk_vs_none` | `analysis_plan_frozen.md` (original) | Best-balanced, largest-contrast framing; never changed despite N moving |
| Exclusion unit: (subject, task), not subject | Amendment 1 | Rest-based primary target shouldn't be penalised by a noisy MSIT run |
| CV: 5-fold × 10 repeats, pooled OOF | Amendment 2 | Reduces estimate variance without changing what's estimated |
| Model class: L2 logistic regression primary | Amendment 2 | Declared before any result existed; tree ensembles/GBMs/NNs excluded as primary |
| Stopping rule: 3 feature families max | original frozen plan | Prevents post-hoc family-shopping |
| Control diagnostic target: sex only | `phase_4.md` §0a, enforced in code | Prevents drift toward re-testing the primary target |

Every one of these is an *append-only* amendment to `analysis_plan_frozen.md`
— the original frozen text is never edited, only added to.

## Deferred items (§6 of phase_4.md) — sizing for a Phase 5 conversation

| Item | Rough size | Why deferred |
|---|---|---|
| Option C reprocessing (fix reference-order bug, re-evaluate ICA `n_components`) + full Phase 1–3 re-run | Multi-day: ~46 GB re-download at whatever bandwidth is available, then re-running Phases 1–3's pipelines (each already measured at minutes-to-an-hour scale per phase, but the download dominates) | Confound gate found no current evidence it's needed; deferred pending a better connection |
| Richer MSIT feature engineering (multitaper time-frequency area, per-condition splitting, feature selection) to close the benchmark gap | A few days of feature-engineering + re-running the secondary/benchmark analyses (not the primary) | Out of this engagement's declared feature-family budget; primary result doesn't depend on it |
| Sternberg task ingestion + analysis | Comparable to Phase 1's rest+MSIT effort (a new preprocessing + feature-extraction pass) — now bandwidth-affordable under the streaming design, previously it wasn't | Never in scope; Phase 1 explicitly proved the streaming approach makes it newly affordable, without adding it |
| Recovering the 15 QC-excluded subjects | Not generally possible — they failed fixed, label-blind QC thresholds decided before any label was read; "recovering" them would mean loosening thresholds after seeing the effect, which is exactly what label-blind QC exists to prevent | N/A — not a sizing question, a methodology one |

Each of these is real, definable work — say so explicitly if a Phase 5 is
discussed, rather than assuming any of it was already included.

## Data retention

- **On disk now:** ~18 GB of derivatives (Phase 1 continuous EEG + ICA
  solutions, Phase 2 features, Phase 3 models) under `pearl/data/derivatives/`,
  gitignored, not backed up by git.
- **Can be deleted:** raw EEG — already deleted per Phase 1's streaming
  design (download → process → verify → delete, never all raw on disk at
  once). One subject's raw (`sub-52`) was deliberately retained for
  debugging/smoke-testing; safe to delete once no longer needed.
- **Must be kept** to reproduce every reported number: the full
  `pearl/data/derivatives/` tree, `data/labels/participants_labels.tsv`,
  and everything already tracked in git (`pearl/reports/`, `pearl/config/`,
  all code).

## Phase 5 (2026-08-11/12) — closing-the-gap attempt, added after this document was first written

Client-authorized second attempt, explicitly separate from and never
superseding the Phase 1-4 null above. Four stages, each checkpointed
before the next began — specs at repo root (`phase_5.md` = Stage 1,
`phase_5_stage2.md`, `phase_5_stage3.md`, `phase_5_stage4.md`), results in
`pearl/reports/phase5_final_report.md` (start there).

**Headline: the primary result flipped from NULL (original, AUC 0.474) to
a marginal, fragile POSITIVE (AUC 0.651, p=0.041) after fixing two real
preprocessing bugs.** Read `pearl/reports/phase5_stage3_checkpoint.md`
before citing this number anywhere — it documents four independent reasons
this is not yet a validated finding (marginal p-value, chance-crossing CI,
high sensitivity to a 5-subject cohort change, no corroboration from
related comparisons), and corrects stale narrative text that shipped
unmodified in the original Phase 3 report/model-card code (written
assuming a null result, never adapted to a positive one).

**Both the original null and Phase 5's result must be reported together to
any stakeholder** — the original Phase 1-4 derivative trees, reports, and
model are preserved byte-for-byte at `*_frozen/`-suffixed paths; Phase 5's
outputs live under `phase5_stage*`/`*_stage3`-prefixed paths. Nothing was
overwritten.

**Deferred sizing for whoever continues (per `phase5_stage3_checkpoint.md` §5):**

| Item | Rough size | Why deferred |
|---|---|---|
| Single-variable re-run (reference-order fix alone, ICA fix alone) | A few hours: no new download, re-run of the already-built pipeline twice more with one change isolated each time | Stage 1 changed both at once; Stage 3's positive result can't be attributed to either specifically without this |
| Independent replication on a new, larger sample | Out of scope for this dataset entirely — would need new data collection or a different cohort | The 5-subject swap within the same 79-subject dataset that flipped the result is not independent replication |
| Track B Sternberg features (encoding/retrieval TFA) against the primary target | New, separately-declared scope | Extracted in Stage 2 but never validated against anything — no benchmark exists for Sternberg specifically |
| Re-containerization for Stage 3's model | A few hours, low risk if done carefully | Explicitly deferred in Stage 4 — the existing container still serves the original frozen Phase 3 model, which is what `INSTALL.md`/`RUNBOOK.md` currently document |

**Known unfixed code gap** (not a data problem, a process risk for any
future re-run): several `pearl_preproc`/`pearl_features`/`pearl_models`
report-writing functions use hardcoded output paths shared with the
original Phase 1-4 artifacts, and some hardcode narrative text describing
a specific expected result. Re-running them silently overwrites the
original files in place and can produce factually wrong prose if the new
result differs from what the text assumed. Worked around manually
(archive-before-running, rename-after) at every stage of Phase 5 — not
fixed in the code itself. Fix properly before any Phase 6.

## If you resume this project

Read, in this order:

1. **`report.md`** — the running engineering status report for Phases 0-4.
   Start here for "what happened and why," not the code.
2. **`pearl/reports/phase5_final_report.md`** — if Phase 5 is relevant to
   what you're picking up, read this before `report.md`'s Phase 3/4
   sections, since it changes what the primary result actually is.
3. **The relevant `phase_N.md`** for whatever you're picking up — each spec
   encodes hard-won decisions (bug root causes, config choices, exclusion
   rules) that aren't visible in the code alone.
4. **`pearl/reports/provenance_chain.md`** — before trusting any number,
   confirm you're looking at the run that actually produced it. (Note:
   this predates Phase 5 and does not yet cover the Stage 3 model —
   `data/derivatives/models_stage3/model_card_corrected.md` has Phase 5's
   provenance in the meantime.)
