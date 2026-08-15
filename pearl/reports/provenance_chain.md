# Provenance Chain

One page tracing the reported Phase 3 primary number (NULL, AUC 0.474) back
to the raw data it was computed from. Anyone should be able to verify the
reported number came from the data claimed by following this chain.

```
participants.tsv (OpenNeuro ds004796)
  sha256: 909d8736a138a2d37506bf25ba62020bc38741c62cb261eea902a716dba8ab13
  |
  v  reconciled 79/79 against client_groups.yaml genotypes (Phase 0)
  v  fingerprint carried into every downstream sidecar/run
  |
Phase 1 preprocessing  --  run_id 20260808T234509Z-a3b8888
  pearl/data/derivatives/preproc/_meta.json
  every sub-XX/eeg/*_desc-preproc_eeg.json sidecar carries this run_id
  + the participants_tsv_sha256 above + source-file sha256 + git sha
  |
  v  qc_metrics.csv, excluded_subjects.csv (23 excluded, subject-level)
  |
Phase 2 confound gate + PSWT/baseline extraction  --  run_id 20260809T222134Z-84a0543
  pearl/data/derivatives/features/_meta.json  (gate_verdict: proceed)
  cohort_per_task.csv  -->  64-subject rest cohort (per-task exclusion rule,
                              Amendment 1)
  |
  v  features_pswt.csv (18 cols post-Phase-4-Task-B), features_baseline.csv
  |
Phase 3 primary analysis + delivery  --  run_id 20260810T152236Z-d8ab867
  pearl/data/derivatives/models/_meta.json  (primary_verdict: NULL)
  cv_metrics.csv, cv_predictions.csv  -->  AUC 0.474, CI [0.266, 0.702],
                                             permutation p=0.577
  |
  v  trained on all 64 subjects, evaluation frozen at the above CV number
  |
Shipped model
  pearl/data/derivatives/models/model_final.joblib
  sha256: b7c343f056ce3582413f887e192713022f9f6582e95edd25b36348e138c4660e
  model_card.md carries: run_id, git_sha, cv_estimated_auc + CI,
  participants_tsv_sha256, feature_config_hash, training_qc_ranges
```

## Where each link is recorded

| Link | Recorded in |
|---|---|
| `participants.tsv` → Phase 1 | every Phase 1 sidecar's `Provenance.participants_tsv_sha256` |
| Phase 1 → Phase 2 | `pearl_features` consumes `qc_metrics.csv`/`excluded_subjects.csv` directly; `pearl/data/derivatives/features/_meta.json` records its own `run_id` + `git_sha` |
| Phase 2 → Phase 3 | `pearl_models.data` reads `features_pswt.csv`/`features_baseline.csv` from the Phase 2 `run_id`'s output tree directly (single tree, no copy) |
| Phase 3 → shipped model | `model_card.md`'s Provenance section: `run_id`, `git_sha`, `cv_estimated_auc`/`cv_estimated_ci` (the CV number, never a training-data number), `feature_config_hash` (sha256 of `config/features.yaml`), `participants_tsv_sha256` |
| Amendment history | `reports/analysis_plan_frozen.md` — Amendment 1 (per-task cohort, N=64), Amendment 2 (CV variance fix, declared model class, reference lines) — both appended, original frozen text untouched |
| Tagged state | git tag `v1.0-phase3-null` on commit `d8ab867` — the exact commit that produced the reported Phase 3 number |

## Clean-clone reproducibility (phase_4.md Task C, verified 2026-08-11)

A fresh `git clone` + fresh venv + `pip install -e ".[dev]"` (pinned exact
versions, see `pyproject.toml`) + `pytest` was run for real:

- **Without** `pearl/data/` and `data/labels/` present (both gitignored):
  **4/237 tests fail** with `FileNotFoundError` — every failure is a test
  that reads a real derivative CSV (`features_pswt.csv`,
  `features_baseline.csv`, `qc_metrics.csv`, `participants.tsv`). This is
  expected, not a bug: those trees are intentionally not tracked in git
  (too large, and `data/labels/` is label-bearing).
- **With** the derivative tree copied in from an existing run (or
  regenerated via the four CLI commands in `README.md`): **237/237 pass.**

No other manual step was needed. See `README.md`'s Reproduction section for
the exact commands.

---

## Phase 5 and Phase 6 provenance (added 2026-08-15, phase_7.md Task F)

The chain above stops before the Stage 3 model. This section completes it, so
one document covers `participants.tsv` hash → every run_id → every delivered
artefact.

### Phase 5 — the retracted positive result

| Step | run_id | git_sha | Artefact |
|---|---|---|---|
| Stage 1/2 features + Stage 3 model | `20260812T100816Z-22821fd` | `22821fd` | `data/derivatives/models_stage3/_meta.json` |
| Stage 3 delivery provenance | `20260812T161100Z-22821fd` | `22821fd` | `data/derivatives/models_stage3/provenance.json`, `model_card_corrected.md` |
| Step 0 — stability characterisation | `20260812T170442Z-756da01` | `756da01` | `data/derivatives/models_stage3/stability_meta.json`, `reports/phase5_stage3_stability{,_resamples,_summary}.{md,csv}` |
| Step 1a — reference-order fix alone | `20260813T071253Z-4bb18cc` | `4bb18cc` | `.../isolation_reference_order_only_meta.json`, `reports/phase5_stage1b_reference_order_only.md` |
| Step 1b — ICA fix alone | `20260813T173645Z-4bb18cc` | `4bb18cc` | `.../isolation_ica_only_meta.json`, `reports/phase5_stage1c_ica_only.md` |
| Confirm-restore (full precision) | `20260813T200402Z-4bb18cc` | `4bb18cc` | `.../confirm_restore_meta.json` |

**Reproducibility note.** The confirm-restore run regenerated the Stage 3
headline exactly (AUC 0.6509, CI [0.353, 0.764], p=0.0410) after the production
derivative tree was restored, establishing that the isolation diagnostics did not
perturb the delivered state.

**Isolation-condition derivatives were deleted** after their conclusions were
recorded (two ~26 GB preprocessed trees, removed to relieve a full disk). Either
condition is exactly reproducible by setting `config/preproc.yaml`'s
`reference.compute_order` / `ica.n_components` to the documented isolated values
and re-running `pearl_preproc.cli run-all`. The derived feature CSVs are retained
at `data/derivatives/features_stage1{a,b}_*_TEMP/`.

### Phase 6 — the bounded null

| Step | run_id | git_sha | Artefact |
|---|---|---|---|
| Control matrix (4 representations × sex) | `20260815T210714Z-4bb18cc` | `4bb18cc` | `reports/phase6_control_matrix.json`, `reports/phase6_bounded_null.md` |
| Power analysis / detection ceiling | deterministic, seedless | `4bb18cc` | `reports/phase6_power_analysis.txt`, `scripts/phase6_power_analysis.py` |

**Verification on record.** The `pswt` cell of the control matrix reproduced the
Phase 5 Stage 3 sex control *bit-exactly* (AUC 0.4645, CI [0.2715, 0.7000],
p=0.6194), confirming the CV harness is deterministic and the on-disk
derivatives had not drifted between phases. The power analysis re-runs to
byte-identical output.

### Phase 7 — delivered state

| Item | Value |
|---|---|
| Tag | `v1.0-bounded-null` |
| Client report | `reports/final_report_v2.{tex,pdf}` |
| Stop decision | `reports/phase7_stop_decision.md` |
| Delivery decision | `reports/phase7_delivery_decision.md` |
| Container image | `pearl-models:phase7` (built from `pearl/Dockerfile`, repo root as context) |
| Test suite at delivery | 289 passing |

### Integrity defect found and corrected during Phase 7

`write_analysis_plan()` rewrote `reports/analysis_plan_frozen.md` from a static
template on every pipeline run, which **destroyed both appended amendments (131
lines)** during the Phase 5 isolation re-runs. Recovered from git; the frozen
plan is now write-once and all other report writers archive any prior version
before overwriting (`pearl_preproc.paths.guarded_write`). Amendment history in
the chain above is therefore intact and verified against commit `4bb18cc`.
