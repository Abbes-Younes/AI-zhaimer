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
