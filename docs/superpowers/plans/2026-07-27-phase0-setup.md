# Phase 0 Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the AI-zhaimer repo — directory scaffolding, subject labels file, Python environment, and FreeSurfer-via-WSL2 — so Phase 1 (data acquisition) can start with zero setup blockers.

**Architecture:** Four independent-but-sequential tasks: (1) repo scaffolding, (2) labels transcription from `classification.pdf`, (3) conda environment, (4) WSL2 + FreeSurfer install. Tasks 1–3 are scriptable and fully verifiable from this session. Task 4 requires the user to perform a few actions on their own machine (admin-elevated WSL install, reboot, FreeSurfer license signup) that cannot be done by an agent — those are called out explicitly as check-in steps.

**Tech Stack:** Git, Bash (Git Bash on Windows), conda/mamba, WSL2 (Ubuntu), FreeSurfer 7.x

## Global Constraints

- Windows 11 host; FreeSurfer must run inside WSL2 (Ubuntu), not natively.
- Environment tool is conda/mamba (user's explicit choice), not venv/pip.
- 79 total subjects: N=31, A+P-=26, A+P+=22 (see `reference/classification.pdf` and `PROJECT.md` §2).
- No `recon-all` subject processing in this plan — that's Phase 2. Task 4 only verifies the toolchain is installed.
- Repo root already has `download-167-197.pdf`, an unrelated stray file — leave it untouched and untracked.

---

### Task 1: Repo scaffolding

**Files:**
- Create: `data/labels/.gitkeep`, `data/bids/.gitkeep`
- Create: `freesurfer/subjects/.gitkeep`, `freesurfer/run_recon_all.sh`
- Create: `src/models/.gitkeep`
- Create: `notebooks/.gitkeep`
- Create: `results/features/.gitkeep`, `results/models/.gitkeep`, `results/figures/.gitkeep`
- Create: `.gitignore`
- Create: `README.md`
- Move: `classification.pdf` → `reference/classification.pdf`

**Interfaces:**
- Produces: the directory layout every later task and every later phase writes into (`data/labels/`, `data/bids/`, `freesurfer/subjects/`, `results/{features,models,figures}/`).

- [ ] **Step 1: Create the directory tree with placeholders**

```bash
mkdir -p "D:/younes/AI-zhaimer/data/bids" \
         "D:/younes/AI-zhaimer/data/labels" \
         "D:/younes/AI-zhaimer/reference" \
         "D:/younes/AI-zhaimer/freesurfer/subjects" \
         "D:/younes/AI-zhaimer/src/models" \
         "D:/younes/AI-zhaimer/notebooks" \
         "D:/younes/AI-zhaimer/results/features" \
         "D:/younes/AI-zhaimer/results/models" \
         "D:/younes/AI-zhaimer/results/figures"

touch "D:/younes/AI-zhaimer/data/bids/.gitkeep" \
      "D:/younes/AI-zhaimer/data/labels/.gitkeep" \
      "D:/younes/AI-zhaimer/freesurfer/subjects/.gitkeep" \
      "D:/younes/AI-zhaimer/src/models/.gitkeep" \
      "D:/younes/AI-zhaimer/notebooks/.gitkeep" \
      "D:/younes/AI-zhaimer/results/features/.gitkeep" \
      "D:/younes/AI-zhaimer/results/models/.gitkeep" \
      "D:/younes/AI-zhaimer/results/figures/.gitkeep"
```

- [ ] **Step 2: Move classification.pdf into reference/**

```bash
mv "D:/younes/AI-zhaimer/classification.pdf" "D:/younes/AI-zhaimer/reference/classification.pdf"
```

- [ ] **Step 3: Create .gitignore**

Write `D:/younes/AI-zhaimer/.gitignore`:

```gitignore
# raw MRI data (large, not versioned)
data/bids/

# FreeSurfer outputs (large, not versioned)
freesurfer/subjects/*
!freesurfer/subjects/.gitkeep

# Python
__pycache__/
*.pyc
.ipynb_checkpoints/
*.egg-info/

# conda
.conda/

# OS
.DS_Store
Thumbs.db

# unrelated stray file, intentionally left untracked
/download-167-197.pdf
```

- [ ] **Step 4: Create run_recon_all.sh stub**

Write `D:/younes/AI-zhaimer/freesurfer/run_recon_all.sh`:

```bash
#!/usr/bin/env bash
# Runs FreeSurfer recon-all for one subject. Implemented in Phase 2.
# Usage: run_recon_all.sh <subject_id> <t1_nifti_path>
set -euo pipefail
echo "Not yet implemented — Phase 2 task." >&2
exit 1
```

```bash
chmod +x "D:/younes/AI-zhaimer/freesurfer/run_recon_all.sh"
```

- [ ] **Step 5: Create README.md**

Write `D:/younes/AI-zhaimer/README.md`:

```markdown
# AI-zhaimer

Predicting genetic Alzheimer's-risk group from T1-weighted structural MRI.
See `PROJECT.md` for the full project goal, cohort definition, and phased plan.
Design docs and implementation plans for each phase live under
`docs/superpowers/`.
```

- [ ] **Step 6: Verify the tree and commit**

```bash
cd "D:/younes/AI-zhaimer"
find data reference freesurfer src notebooks results -type f
```

Expected: lists all the `.gitkeep` files, `reference/classification.pdf`,
`freesurfer/run_recon_all.sh`, and no `classification.pdf` left at repo root.

```bash
git add data reference freesurfer src notebooks results .gitignore README.md
git status
```

Expected: `classification.pdf` shows as renamed to `reference/classification.pdf`;
`download-167-197.pdf` does NOT appear (it's gitignored and was never tracked).

```bash
git commit -m "$(cat <<'EOF'
Scaffold Phase 0 repo structure

Adds the data/reference/freesurfer/src/notebooks/results directory
layout from PROJECT.md, moves classification.pdf into reference/,
and gitignores raw MRI data and FreeSurfer subject outputs.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Labels transcription

**Files:**
- Create: `data/labels/participants_labels.tsv`

**Interfaces:**
- Consumes: subject ID lists per group from `reference/classification.pdf` (already transcribed below — no need to re-read the PDF).
- Produces: `data/labels/participants_labels.tsv` with columns `subject_id, group, task1_risk_vs_norisk, task2_high_vs_lownormal, task3_multiclass`. Every later phase (Phase 3 dataset assembly onward) reads this file as the label source.

- [ ] **Step 1: Write the TSV generation script**

Write `D:/younes/AI-zhaimer/data/labels/generate_labels.py`:

```python
"""One-off script: generates participants_labels.tsv from the subject ID
lists in reference/classification.pdf (transcribed by hand below)."""
import csv
from pathlib import Path

GROUP_N = [f"sub-{i:02d}" for i in range(1, 32)]  # sub-01..sub-31

GROUP_APM = [  # A+P-, "risque simple"
    "sub-38", "sub-47", "sub-53", "sub-57", "sub-58", "sub-59", "sub-60",
    "sub-61", "sub-62", "sub-63", "sub-64", "sub-65", "sub-66", "sub-67",
    "sub-68", "sub-70", "sub-71", "sub-72", "sub-73", "sub-74", "sub-75",
    "sub-76", "sub-77", "sub-78", "sub-79", "sub-80",
]

GROUP_APP = [  # A+P+, "double risque"
    "sub-32", "sub-33", "sub-34", "sub-35", "sub-36", "sub-37", "sub-39",
    "sub-40", "sub-41", "sub-42", "sub-43", "sub-44", "sub-45", "sub-46",
    "sub-48", "sub-49", "sub-50", "sub-51", "sub-52", "sub-54", "sub-55",
    "sub-56",
]

assert len(GROUP_N) == 31
assert len(GROUP_APM) == 26
assert len(GROUP_APP) == 22

ROWS = []
for sid in GROUP_N:
    ROWS.append((sid, "N", 0, 0, 0))
for sid in GROUP_APM:
    ROWS.append((sid, "A+P-", 1, 0, 1))
for sid in GROUP_APP:
    ROWS.append((sid, "A+P+", 1, 1, 2))

ROWS.sort(key=lambda r: int(r[0].split("-")[1]))

out_path = Path(__file__).parent / "participants_labels.tsv"
with out_path.open("w", newline="") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow([
        "subject_id", "group", "task1_risk_vs_norisk",
        "task2_high_vs_lownormal", "task3_multiclass",
    ])
    writer.writerows(ROWS)

print(f"Wrote {len(ROWS)} rows to {out_path}")
```

- [ ] **Step 2: Run it**

```bash
cd "D:/younes/AI-zhaimer" && python data/labels/generate_labels.py
```

Expected output: `Wrote 79 rows to .../participants_labels.tsv`

- [ ] **Step 3: Validate row and group counts**

```bash
cd "D:/younes/AI-zhaimer"
wc -l < data/labels/participants_labels.tsv          # expect 80 (79 rows + header)
grep -c $'\tN\t' data/labels/participants_labels.tsv  # expect 31
grep -c $'\tA+P-\t' data/labels/participants_labels.tsv  # expect 26
grep -c $'\tA+P+\t' data/labels/participants_labels.tsv  # expect 22
grep -c "sub-69" data/labels/participants_labels.tsv  # expect 0 (sub-69 does not exist in the cohort)
```

Expected: `80`, `31`, `26`, `22`, `0` respectively. If any count is wrong, fix
`GROUP_N`/`GROUP_APM`/`GROUP_APP` in `generate_labels.py` and re-run Step 2.

- [ ] **Step 4: Commit**

```bash
cd "D:/younes/AI-zhaimer"
git add data/labels/generate_labels.py data/labels/participants_labels.tsv
git commit -m "$(cat <<'EOF'
Add participants_labels.tsv with 79-subject genetic risk labels

Transcribes subject IDs and APOE/PICALM group assignments from
reference/classification.pdf and pre-computes label encodings for
all 3 classification tasks defined in PROJECT.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Python environment

**Files:**
- Create: `environment.yml`

**Interfaces:**
- Produces: a conda environment named `ai-zhaimer` with `nibabel`, `nilearn`,
  `scikit-learn`, `pandas`, `numpy`, `statsmodels`, `matplotlib`, `seaborn`
  installed — every later phase's Python code (`src/*.py`, notebooks) runs
  inside this environment.

- [ ] **Step 1: Write environment.yml**

Write `D:/younes/AI-zhaimer/environment.yml`:

```yaml
name: ai-zhaimer
channels:
  - conda-forge
dependencies:
  - python=3.11
  - nibabel
  - nilearn
  - scikit-learn
  - pandas
  - numpy
  - statsmodels
  - matplotlib
  - seaborn
  - jupyter
  - pip
```

- [ ] **Step 2: Build the environment**

```bash
cd "D:/younes/AI-zhaimer"
mamba env create -f environment.yml
```

If `mamba` is not installed, fall back to:

```bash
conda env create -f environment.yml
```

Expected: completes without error, ending with something like
`# To activate this environment, use conda activate ai-zhaimer`.

- [ ] **Step 3: Verify the environment**

```bash
conda run -n ai-zhaimer python -c "import nibabel, nilearn, sklearn, pandas, numpy, statsmodels, matplotlib, seaborn; print('OK')"
```

Expected: `OK` printed with no import errors.

- [ ] **Step 4: Commit**

```bash
cd "D:/younes/AI-zhaimer"
git add environment.yml
git commit -m "$(cat <<'EOF'
Add conda environment.yml for the analysis stack

Pins the Python + scientific/neuroimaging packages (nibabel, nilearn,
scikit-learn, pandas, statsmodels) needed from Phase 1 onward.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: FreeSurfer via WSL2

**Files:**
- None created in this repo — this task installs system-level tooling
  (WSL2, Ubuntu, FreeSurfer) outside the git-tracked project.

**Interfaces:**
- Produces: a working `recon-all` command inside WSL2, with `SUBJECTS_DIR`
  pointed at `freesurfer/subjects/` (accessible from WSL2 via `/mnt/d/younes/AI-zhaimer/freesurfer/subjects`). Phase 2 depends on this being callable.

This task requires actions on the user's machine that an agent cannot perform
(admin-elevated install, a reboot, and registering for a free FreeSurfer
license via web form). Each step below says explicitly whether the agent runs
it or the user does.

- [ ] **Step 1 (user, admin PowerShell): Install WSL2 + Ubuntu**

The user opens an **administrator** PowerShell and runs:

```powershell
wsl --install -d Ubuntu
```

This requires a reboot to finish enabling the WSL2 feature. After reboot,
Ubuntu launches once automatically to finish setup and prompts the user to
create a UNIX username/password.

- [ ] **Step 2 (agent, after reboot): Verify WSL2 is up**

```bash
wsl --status
wsl -l -v
```

Expected: `Ubuntu` listed with `VERSION 2` and `STATE Running` (or `Stopped`,
which is fine — it starts on first command).

- [ ] **Step 3 (user, web browser): Get a FreeSurfer license file**

The user registers at the FreeSurfer license page
(https://surfer.nmr.mgh.harvard.edu/registration.html) and receives
`license.txt` by email. Save it to `D:/younes/AI-zhaimer/freesurfer/license.txt`
(this path is `.gitignore`d already via no explicit rule needed — it's a
small text file, but since it's a personal license key, add it explicitly):

```bash
echo "freesurfer/license.txt" >> "D:/younes/AI-zhaimer/.gitignore"
cd "D:/younes/AI-zhaimer" && git add .gitignore && git commit -m "$(cat <<'EOF'
Gitignore the FreeSurfer license file

license.txt is a personal credential tied to the user's registration
and should not be committed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4 (agent, inside WSL2): Install FreeSurfer**

```bash
wsl -d Ubuntu -- bash -lc '
set -e
sudo apt-get update
sudo apt-get install -y wget tcsh perl bc libgomp1
wget -q https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.1/freesurfer-linux-ubuntu22_amd64-7.4.1.tar.gz -O /tmp/freesurfer.tar.gz
sudo tar -C /usr/local -xzf /tmp/freesurfer.tar.gz
rm /tmp/freesurfer.tar.gz
'
```

If the download URL 404s (FreeSurfer versions/paths change), the user checks
the current download link at
https://surfer.nmr.mgh.harvard.edu/fswiki/DownloadAndInstall and provides the
correct URL to substitute above.

- [ ] **Step 5 (agent, inside WSL2): Configure environment and SUBJECTS_DIR**

```bash
wsl -d Ubuntu -- bash -lc '
cat >> ~/.bashrc <<EOF2
export FREESURFER_HOME=/usr/local/freesurfer
source \$FREESURFER_HOME/SetUpFreeSurfer.sh
export SUBJECTS_DIR=/mnt/d/younes/AI-zhaimer/freesurfer/subjects
EOF2
'
```

- [ ] **Step 6 (agent, inside WSL2): Place the license and verify**

```bash
wsl -d Ubuntu -- bash -lc '
cp /mnt/d/younes/AI-zhaimer/freesurfer/license.txt /usr/local/freesurfer/license.txt
source ~/.bashrc
recon-all --version
'
```

Expected: prints a FreeSurfer version string (e.g. `freesurfer-linux-ubuntu22_amd64-7.4.1-...`)
with no license or environment errors.

- [ ] **Step 7: Record the verified setup**

No code changes; this is a manual checklist confirmation. Update the Phase 0
design doc's exit criteria checkboxes in
`docs/superpowers/specs/2026-07-27-phase0-setup-design.md` by marking the
FreeSurfer/WSL2 line done, and commit:

```bash
cd "D:/younes/AI-zhaimer"
git add docs/superpowers/specs/2026-07-27-phase0-setup-design.md
git commit -m "$(cat <<'EOF'
Mark Phase 0 FreeSurfer/WSL2 setup verified

recon-all --version runs successfully inside WSL2 with SUBJECTS_DIR
configured against freesurfer/subjects/.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 0 done-check

After all 4 tasks: repo has scaffolding + labels + environment + working
FreeSurfer-in-WSL2, all committed. This satisfies every exit criterion in
`docs/superpowers/specs/2026-07-27-phase0-setup-design.md`. Phase 1 (locating
the BIDS MRI dataset) can start next as its own brainstorm → plan cycle.
