# Runbook

## Scoring a subject

**Bare metal:**

```bash
cd pearl
pearl-models score --subject sub-XX --bids-dir data/raw --model-dir data/derivatives/models
```

**Docker:**

```bash
docker run --rm \
  -v "$(pwd)/pearl/data:/app/data" \
  pearl-models:latest \
  score --subject sub-XX --bids-dir /app/data/raw --model-dir /app/data/derivatives/models
```

**Thin API:**

```bash
python -m pearl_models.api                    # starts on :8000
curl -X POST localhost:8000/score \
  -H 'Content-Type: application/json' \
  -d '{"subject": "sub-XX", "bids_dir": "data/raw", "model_dir": "data/derivatives/models"}'
```

All three call the exact same code path (`pearl_models.inference.score_bids_subject`):
Phase 1 preprocessing → Phase 2 feature extraction → out-of-distribution
check → calibrated score. `--bids-dir`/`bids_dir` must contain the subject's
raw BrainVision triplet at `<bids-dir>/<subject>/eeg/<subject>_task-rest_eeg.{vhdr,eeg,vmrk}`
— the same layout `pearl_preproc` uses throughout this project (a fully
generic arbitrary-BIDS-layout reader was out of scope for this phase).

## Reading the output

```json
{
  "status": "scored",
  "probability": 0.62,
  "disclaimer": "research pipeline output — a research score, not a risk assessment, screening result, or diagnosis",
  "run_id": "20260810T152236Z-d8ab867",
  "git_sha": "82c2eeb"
}
```

- `status: "scored"` — the subject's QC metrics fell inside the training
  cohort's observed range. `probability` is a **calibrated** probability
  (Platt/sigmoid scaling), not a raw model score — but recall the shipped
  model's own cross-validated performance (AUC 0.474, `model_card.md`) does
  not exceed chance. **A probability near 0.5 or far from it carries the
  same weight: none, beyond curiosity** — the model has not demonstrated
  predictive validity in Phase 3.
- `status: "cannot_score"` — the subject's preprocessing QC metrics
  (bad-channel count, ICA components removed, or artifact fraction) fell
  outside the training cohort's range. The `reason` field names which metric
  and by how much.

## What to do when out-of-distribution refusal fires

This is not an error to work around. It means the new recording's data
quality differs enough from the 64-subject training cohort that the model's
calibration cannot be trusted to extrapolate. Options, in order of
preference:

1. **Re-run preprocessing** if the QC metrics look like a preprocessing
   artifact (e.g. an unusually high bad-channel count from a bad electrode
   day) rather than a genuine property of the recording.
2. **Accept the refusal.** The tool is deliberately conservative here — see
   `model_card.md`'s Out-of-scope section. Do not lower the training-range
   thresholds to force a score.
3. If this happens systematically across many new subjects, that is a sign
   the training cohort's QC range is too narrow for the intended deployment
   population — a scope question for a future phase, not something to patch
   around per-subject.

## Disk / bandwidth for reprocessing from raw

See `INSTALL.md`'s Disk and bandwidth section and `report.md` §2.4 (Phase 1
measured budget: 17.73 GB derivative total, 1.41 GB peak raw-on-disk,
streaming download/delete per subject).

## End-to-end smoke test (Task D verification record — passed, 2026-08-11)

Run for real against `sub-52` (raw BrainVision files retained on disk from
Phase 1's header-repair debugging — see `report.md` §2.3), inside the built
container:

```bash
docker build -t pearl-models:phase4 -f pearl/Dockerfile .
docker run --rm --entrypoint pearl-models \
  -v "$(pwd)/pearl/data:/app/data" \
  pearl-models:phase4 \
  score --subject sub-52 --bids-dir /app/data/raw --model-dir /app/data/derivatives/models
```

(On Windows + Git Bash specifically, prefix with `MSYS_NO_PATHCONV=1` —
Git Bash otherwise silently rewrites the `/app/...` container paths into
Windows paths before they reach `docker run`.)

**Result: exit code 0.**

```json
{
  "status": "scored",
  "probability": 0.551,
  "disclaimer": "research pipeline output — a research score, not a risk assessment, screening result, or diagnosis",
  "run_id": "20260811T034144Z-d15637c",
  "git_sha": "d15637c"
}
```

Two real bugs were found and fixed by running this for real rather than
just writing the Dockerfile:

1. **`mne-icalabel`'s ICLabel backend requires `torch` or `onnxruntime`**,
   present on the dev host by accident and never declared as a project
   dependency — the container (correctly reflecting only what
   `pyproject.toml` declares) failed with `ImportError` on the first ICA
   step. Fixed by declaring `onnxruntime==1.27.0` (chosen over `torch`: same
   result, far lighter, no torchvision/torchaudio).
2. **The ICLabel-fallback path had a latent crash** (`IndexError` on a
   degenerate PSD with no bin ≥20 Hz) that had never been exercised before —
   fixed defensively, with a regression test, independent of bug 1's fix.
3. **The shipped model from Task 11 predated Task B's h1-column fix** and
   expected 20 features where the pipeline now emits 18 — `ValueError`
   at `predict_proba`. Fixed by retraining the *deployment artifact only*
   (not the frozen CV evaluation number, which is unchanged) on the
   corrected 18-feature set.
