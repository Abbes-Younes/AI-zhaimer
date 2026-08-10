# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PEARL-Neuro EEG classification (OpenNeuro `ds004796`): predicting genetic
Alzheimer's-risk group (N / A_P_minus / A_P_plus, from APOE ε4 + PICALM
status) from resting-state and task EEG, using a pitch-synchronous
waveform-shape feature family (PSR/PSWT) compared against a conventional
spectral baseline.

**All active code lives under `pearl/`.** `PROJECT.md` and the top-level
`src/`, `results/`, `data/bids/`, `notebooks/`, `freesurfer/` directories
describe an earlier, superseded plan (T1-weighted MRI + FreeSurfer). They are
empty scaffolding (`.gitkeep` only) and not part of the current project —
don't build against them.

The project runs as a sequence of phases, each with its own spec file at the
repo root (`phase_0.md`, `phase_0,5.md`, `phase_1.md`, `phase_2.md`,
`phase_3.md`) and a corresponding implementation plan under
`docs/superpowers/plans/`. **Read the relevant `phase_N.md` in full before
touching code for that phase** — each one encodes hard-won decisions (bug
root causes, config choices, exclusion rules) that aren't otherwise visible
in the code. `report.md` at the repo root is the running project status
report — read it first to see what's done and what's next; update it when a
phase closes.

## Commands

All commands run from `pearl/`.

```bash
pip install -e ".[dev]"          # installs mne, mne-icalabel, scikit-learn, PyWavelets, etc.
pytest tests/ -q                  # full suite
pytest tests/test_features_cycles.py -v                 # one file
pytest tests/test_features_cycles.py::test_name -v       # one test
python -m pearl_audit.cli run-all      # Phase 0 audit
python -m pearl_preproc.cli run-all    # Phase 1 download+preprocess+QC (resumable, skips completed subjects)
python -m pearl_features.cli           # Phase 2 confound gate + feature pipeline (resumable)
```

Tests use `pythonpath = ["src"]` (set in `pyproject.toml`), so `pearl_audit`,
`pearl_preproc`, `pearl_features` import without an editable install when run
via `pytest` from `pearl/`. Outside pytest (e.g. one-off `python -c`
scripts), set `PYTHONPATH=src` explicitly or use the installed console
scripts above.

**Caches must live on `D:`, never `C:`** (project convention from Phase 0):

```powershell
$env:UV_CACHE_DIR = "D:\younes\AI-zhaimer\pearl\.cache\uv"
$env:PIP_CACHE_DIR = "D:\younes\AI-zhaimer\pearl\.cache\pip"
$env:TMP = "D:\younes\AI-zhaimer\pearl\.cache\tmp"
$env:TEMP = "D:\younes\AI-zhaimer\pearl\.cache\tmp"
$env:XDG_CACHE_HOME = "D:\younes\AI-zhaimer\pearl\.cache"
$env:MPLCONFIGDIR = "D:\younes\AI-zhaimer\pearl\.cache\mpl"
```

## Architecture

Three sibling packages under `pearl/src/`, one per phase, each with its own
`config/*.yaml` (frozen before the run it governs) and its own paths module.
Each later package imports only the non-label bits of the earlier ones
(`paths.py`, `sha256_file`, `git_sha`, run-id helpers) — never their
label-bearing modules.

- **`pearl_audit`** (Phase 0): reconciles the client's group assignment
  against official genotype columns, surveys dataset size, checks
  demographic confounds. Reads `config/client_groups.yaml` and
  `config/audit.yaml`.
- **`pearl_preproc`** (Phase 1): manifest-driven streaming download
  (download → preprocess → verify → delete raw, never the whole raw dataset
  on disk at once) → preprocessing (montage, average reference, filtering,
  bad-channel interpolation, resampling, 50 Hz line-noise removal, ICA) → QC
  → frozen exclusion list → `reports/analysis_plan_frozen.md`. Reads
  `config/preproc.yaml`.
- **`pearl_features`** (Phase 2): confound gate (QC-metrics-only classifier
  used as a contamination-floor diagnostic, *not* a result) → per-cycle
  waveform-shape (PSR/PSWT) and baseline spectral feature extraction. Reads
  `config/features.yaml`.

**Label blindness is a hard, enforced boundary**, not a convention: every
package (except one sanctioned module per package that reads labels
*after* a freeze/gate, purely for reporting) has no import path to
`config/client_groups.yaml`, `cohort_definition.csv`, genotype columns, or
label-bearing modules from earlier packages. This is asserted by dedicated
tests (`test_preproc_labelblind.py`, `test_features_labelblind.py`) that
scan every source file in the package for forbidden tokens/imports — if you
add a module that needs label access, it must be added to that test's
`SANCTIONED` set with a one-line justification, matching the existing
pattern (`report_qc.py` in Phase 1, `confound_gate.py` in Phase 2). Config
YAMLs are scanned too. Don't work around this boundary; it's the main
defense against the project accidentally learning to classify preprocessing
artefacts instead of neurophysiology.

**Frozen documents.** `reports/analysis_plan_frozen.md` (CV scheme, primary
target, metric, benchmark, stopping rule) is written before any feature
exists and is never edited in place — changes are appended as numbered
`Amendment N` blocks with a date and reason, and the original text above them
must stay byte-identical. `config/preproc.yaml` and `config/features.yaml`
are declared fully before the run they govern; don't add config keys
retroactively to explain results already seen.

**Run identity and atomic staging.** Bulk derivative writers use a single
`run_id` (`paths.make_run_id()`) and stage into `.tmp-<run_id>/` before
atomically swapping into place (`paths.finalize_run()` /
`pearl_features.paths.finalize_staged()`), so a crashed or interrupted run
never leaves a partially-written derivative tree, and mixed-`run_id`
artifacts are refused rather than silently combined. `pearl_preproc` and
`pearl_features` pipelines are resumable and idempotent: re-running skips
subjects that already have a valid derivative rather than tracking
in-memory/session state.

**QC/exclusion is metric-first, label-blind, then reported.** Every
preprocessing/QC threshold lives in `config/preproc.yaml` and is applied
uniformly before any label is loaded; `qc_metrics.csv` gets one row per
`(subject, task)` with a `pass`/`warn`/`fail` verdict from those fixed
thresholds alone. Only the QC report modules (`report_qc.py`,
`confound_gate.py`) subsequently join labels — to report per-group attrition
or to test whether QC metrics alone predict group — never to adjust a
threshold. The exclusion *unit* changed between phases (subject-level in
Phase 1's `freeze_exclusions`, per-`(subject, task)` in Phase 2's
`cohort.py`) — see `phase_2.md` §0a for why per-task is correct for a
rest-based primary target; don't re-collapse it without the same reasoning
documented as an amendment.

**Data layout** (all under `pearl/data/derivatives/`, gitignored — nothing
under `pearl/data/` is committed; regenerate via the CLI commands above):
```
phase0/                       Phase 0 audit CSVs, phase1_manifest.csv
preproc/sub-XX/eeg/           Phase 1 continuous derivatives + ICA solutions + provenance sidecars
preproc/qc/                   qc_metrics.csv, excluded_subjects.csv
phase2/                       cohort_per_task.csv
features/                     features_pswt.csv, features_baseline.csv, feature_dictionary.md, cycle_stats.csv
```
Every derivative sidecar JSON carries source-file SHA-256, full processing
spec, `run_id`, and git SHA — a derivative that can't name the raw file and
code version that produced it is treated as not reproducible.

## Working conventions specific to this repo

- Each phase's spec file states explicit **stop-and-escalate conditions**
  (e.g. `phase_2.md` §11: QC-only classifier AUC > 0.65 halts feature work
  entirely). These are hard gates, not warnings to work around — if one
  fires, report and wait rather than continuing or loosening the threshold
  that tripped it.
- Bugs found via real-data smoke tests (not just synthetic unit tests) are
  common in the signal-processing code (cycle detection, PSR/PSWT) — several
  have been found this way already (see `report.md` §6.3). Always validate a
  new DSP function against at least one real subject's derivative before
  considering a task done, even if synthetic tests pass.
- Windows + PowerShell/Git Bash environment; paths in code use `pathlib`
  throughout, not string concatenation.
