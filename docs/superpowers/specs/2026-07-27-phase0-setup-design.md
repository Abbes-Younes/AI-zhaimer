# Phase 0 — Project Setup Design

## Context

AI-zhaimer classifies subjects into genetic Alzheimer's-risk groups (APOE/PICALM
status) from T1-weighted structural MRI processed through FreeSurfer. Full project
scope and the 8-phase roadmap are defined in `PROJECT.md`. This document scopes
**Phase 0 only** — setup that every later phase depends on. Each phase in this
project is designed and implemented separately; later phases are out of scope here.

The repo currently contains only `PROJECT.md` and `classification.pdf` (the source
of subject IDs and genetic group labels, confirmed to match PROJECT.md's group
table: N=31, A+P-=26, A+P+=22, total 79). An unrelated PDF (`download-167-197.pdf`,
an audio signal processing thesis excerpt) was mistakenly placed in the repo root
and is being left alone/ignored — not part of this project.

MRI data location is still unknown and FreeSurfer/Python environments are not yet
installed. The user is on Windows 11, which cannot run FreeSurfer natively.

## Goals

Stand up the repo structure, environment, and labels file so Phase 1 (data
acquisition) can start without any setup blockers.

## Components

### 1. Repo scaffolding & version control

Directory structure (per PROJECT.md §5):

```
AI-zhaimer/
├── PROJECT.md
├── docs/superpowers/specs/       (design docs, this file)
├── data/
│   ├── bids/                     (gitignored — raw NIfTI, populated in Phase 1)
│   └── labels/
│       └── participants_labels.tsv
├── reference/
│   └── classification.pdf        (moved here)
├── freesurfer/
│   ├── subjects/                 (gitignored — FreeSurfer SUBJECTS_DIR output)
│   └── run_recon_all.sh
├── src/
│   ├── extract_features.py
│   ├── build_dataset.py
│   ├── eda.py
│   ├── models/
│   │   ├── train.py
│   │   └── evaluate.py
│   └── interpret.py
├── notebooks/
├── results/
│   ├── features/
│   ├── models/
│   └── figures/
├── environment.yml
└── README.md
```

Phase 0 creates the directory skeleton (with `.gitkeep` placeholders where empty)
and moves `classification.pdf` into `reference/`. Script files under `src/` and
`freesurfer/` are stubbed as empty placeholders — implementation is later phases'
work, not Phase 0.

`.gitignore` excludes: `data/bids/`, `freesurfer/subjects/`, conda/venv artifacts,
`__pycache__/`, Jupyter checkpoints, and OS cruft. `download-167-197.pdf` is left
untouched in the repo root and untracked (not added to git).

### 2. Labels transcription

`data/labels/participants_labels.tsv`, one row per subject (79 rows), columns:

| column | values | meaning |
|---|---|---|
| `subject_id` | `sub-01` … `sub-80` (79 of 80 IDs; no `sub-69`) | BIDS subject ID |
| `group` | `N` / `A+P-` / `A+P+` | genetic group from classification.pdf |
| `task1_risk_vs_norisk` | 0 / 1 | N=0, A+P-∪A+P+=1 |
| `task2_high_vs_lownormal` | 0 / 1 | N∪A+P-=0, A+P+=1 |
| `task3_multiclass` | 0 / 1 / 2 | N=0, A+P-=1, A+P+=2 |

Values are transcribed directly from the subject-ID lists already extracted from
`classification.pdf` (read during brainstorming). Validation check: row count is
79 and group counts are exactly 31/26/22 before this file is considered done.

### 3. Python environment

`environment.yml` (conda/mamba), pinning: `python=3.11`, `nibabel`, `nilearn`,
`scikit-learn`, `pandas`, `numpy`, `statsmodels`, `matplotlib`, `seaborn`. No
version upper bounds beyond what's needed for compatibility — this is a research
project, not a shipped package.

### 4. FreeSurfer via WSL2

FreeSurfer does not run natively on Windows. Setup: install Ubuntu under WSL2,
install FreeSurfer inside it, configure `SUBJECTS_DIR` (pointing at a path under
`freesurfer/subjects/`, accessible from both WSL2 and Windows via `/mnt/d/...`),
place the FreeSurfer license file, and verify with `recon-all --version`. No
actual `recon-all` subject runs happen in Phase 0 — that's Phase 2.

## Exit criteria (all must hold before moving to Phase 1)

- [ ] Repo scaffolded per the structure above, committed to git
- [ ] `classification.pdf` moved to `reference/`
- [ ] `data/labels/participants_labels.tsv` has 79 rows with correct group counts
      (31 N / 26 A+P- / 22 A+P+) and all 5 label columns populated correctly
- [ ] `environment.yml` created and the conda env builds cleanly
- [ ] WSL2 + Ubuntu installed, FreeSurfer installed inside it, `SUBJECTS_DIR`
      configured, `recon-all --version` succeeds

## Out of scope for Phase 0

- Locating/mounting the actual BIDS MRI dataset (Phase 1)
- Any `recon-all` subject processing (Phase 2)
- Feature extraction, modeling, or evaluation code logic (Phases 3–7)
