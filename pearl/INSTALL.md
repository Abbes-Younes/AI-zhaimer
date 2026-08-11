# Install

## Option A — Docker (recommended for scoring)

```bash
# from the repo root (D:\younes\AI-zhaimer or your clone root)
docker build -t pearl-models:latest -f pearl/Dockerfile .
```

The image bakes in the code and pinned dependencies (`pearl/pyproject.toml`)
but **not** the data — `pearl/data/` is intentionally not versioned (too
large) and must be mounted at run time. See `RUNBOOK.md` for how to score a
subject and what each mount needs to contain.

## Option B — bare metal

```bash
cd pearl
pip install -e ".[dev]"        # exact pinned versions, see pyproject.toml
pytest tests/ -q                 # requires pearl/data/ + data/labels/ present — see README.md
```

Requires Python 3.11 (the pinned dependency versions were tested against
this; other 3.10+ interpreters may work but are unverified). Network access
to OpenNeuro is only needed if regenerating derivatives from raw (see
`README.md`'s Reproduction section).

## Disk and bandwidth

- Full derivative tree (Phases 1–3 outputs, no raw EEG retained): **~18 GB**
  measured (`report.md` §2.4's 17.73 GB Phase 1 figure + Phase 2/3 outputs).
- Raw EEG is streamed per-subject during Phase 1 and deleted after each
  subject's derivative is verified — peak raw-on-disk was measured at
  1.41 GB, never the full ~46 GB raw dataset at once.
- Scoring a single new subject through the shipped model needs only that
  subject's raw BrainVision triplet (~590 MB) plus the already-shipped
  model artifacts (`model_final.joblib`, `provenance.json`, a few KB).

## Verifying the install

```bash
cd pearl
python -c "import pearl_audit, pearl_preproc, pearl_features, pearl_models; print('ok')"
pearl-models --help
```
