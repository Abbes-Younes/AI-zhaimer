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

## If you resume this project

Read, in this order:

1. **`report.md`** — the running engineering status report. Start here for
   "what happened and why," not the code.
2. **The relevant `phase_N.md`** for whatever you're picking up — each spec
   encodes hard-won decisions (bug root causes, config choices, exclusion
   rules) that aren't visible in the code alone.
3. **`pearl/reports/provenance_chain.md`** — before trusting any number,
   confirm you're looking at the run that actually produced it.
