# AI-zhaimer / PEARL-Neuro

Predicting genetic Alzheimer's-risk group (APOE ε4 + PICALM status) from
resting-state and task EEG (OpenNeuro `ds004796`), using a pitch-synchronous
waveform-shape feature family (PSR/PSWT) compared against a conventional
spectral baseline.

**All active code lives under `pearl/`.** See `CLAUDE.md` for the full
architecture and working conventions. `PROJECT.md` and the top-level `src/`,
`results/`, `data/bids/`, `freesurfer/` directories describe an earlier,
superseded plan (T1-weighted MRI + FreeSurfer) — empty scaffolding, not part
of the current project.

The project ran as four phases, each with its own spec (`phase_0.md` …
`phase_4.md`) and implementation plan under `docs/superpowers/plans/`.
`report.md` at the repo root is the running project status report —
read it first. `reports/phase4_final_report.md` (once written) is the
client-facing summary.

## Reproduction

```bash
cd pearl
pip install -e ".[dev]"    # exact pinned versions — see pyproject.toml
pytest tests/ -q
```

**Important:** `pytest` requires the pipeline's derivative outputs to
already exist under `pearl/data/derivatives/` and `data/labels/` — these
directories are intentionally gitignored (too large for git, and in
`data/labels/`'s case, label-bearing). A subset of the test suite (models
built on real feature/QC data) will fail with `FileNotFoundError` on a
truly empty clone until one of the following is done:

- **Regenerate from scratch** (requires OpenNeuro network access and ~18 GB
  of disk for the full derivative tree; raw EEG is streamed and deleted
  per-subject, never fully co-resident — see `report.md` for measured
  budgets):
  ```bash
  python -m pearl_audit.cli run-all
  python -m pearl_preproc.cli run-all
  python -m pearl_features.cli
  python -m pearl_models.cli
  ```
- **Or copy an existing `pearl/data/` and `data/labels/` tree** from a prior
  run onto the fresh clone before running `pytest`.

This was verified for real (phase_4.md Task C, 2026-08-11): a fresh
`git clone` + fresh venv + `pip install -e ".[dev]"` + `pytest` fails 4/237
tests without the derivative tree present, and passes 237/237 once it is.
See `reports/provenance_chain.md` for the full trace from data hash to
shipped model.
