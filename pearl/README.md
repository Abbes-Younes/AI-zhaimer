# PEARL-Neuro Phase 0 Audit

Phase 0 audit toolkit for the PEARL-Neuro EEG classification project (OpenNeuro `ds004796`).

## What is this?

Phase 0 answers five questions before any EEG data is touched:

1. Does the client's 31/26/22 group assignment reconcile with the official genotype columns?
2. What is `sub-69`? (IDs run 01–80, only 79 are assigned to groups.)
3. Which subjects are missing which EEG runs, and is that missingness balanced?
4. Are the groups confounded by age, sex, or education?
5. How many bytes would a Phase 1 EEG-only download actually cost?

## Setup

### Environment variables

All caches and temp files must live on `D:` to avoid filling the `C:` drive. The
real project root is `D:\younes\AI-zhaimer\pearl\` (the original `D:\pearl\`
root from `Plan.md` was superseded):

```powershell
$env:UV_CACHE_DIR = "D:\younes\AI-zhaimer\pearl\.cache\uv"
$env:PIP_CACHE_DIR = "D:\younes\AI-zhaimer\pearl\.cache\pip"
$env:TMP = "D:\younes\AI-zhaimer\pearl\.cache\tmp"
$env:TEMP = "D:\younes\AI-zhaimer\pearl\.cache\tmp"
$env:XDG_CACHE_HOME = "D:\younes\AI-zhaimer\pearl\.cache"
$env:MPLCONFIGDIR = "D:\younes\AI-zhaimer\pearl\.cache\mpl"
```

### Install

```bash
pip install -e ".[dev]"
```

### Run

```bash
python -m pearl_audit.cli run-all
```

### Tests

```bash
pytest tests/ -v
```

## Project structure

```
pearl/
├── config/
│   ├── client_groups.yaml    # Client's group assignment (the claim under test)
│   └── audit.yaml            # Thresholds, dataset accession, resolved columns
├── src/pearl_audit/
│   ├── paths.py              # Single source of truth for all paths + guards
│   ├── fetch_metadata.py     # §3: HTTPS fallback for OpenNeuro metadata
│   ├── size_survey.py        # §4: Recursive listing, zero downloaded bytes
│   ├── reconcile_groups.py   # §5: Genotype parsing + group reconciliation
│   ├── inventory.py          # §6: EEG run inventory + effective N
│   ├── confounds.py          # §7: Statistical tests for confound analysis
│   ├── report.py             # §8: Self-contained HTML + Markdown report
│   └── cli.py                # `python -m pearl_audit.cli run-all`
├── data/
│   ├── raw_meta/             # participants.tsv, *.json sidecars
│   └── derivatives/phase0/   # Generated CSVs
├── reports/
│   ├── phase0_audit.html     # Self-contained HTML report
│   └── phase0_audit.md       # Markdown version
├── logs/
│   └── fetch_log.jsonl       # Every network fetch logged with SHA-256
└── tests/
    ├── test_paths.py
    ├── test_reconcile_groups.py
    └── test_cli.py
```

## Hard constraints

- **No raw EEG download** — Phase 0 downloads metadata only (< 50 MB)
- **No C: drive writes** — everything on D:
- **No invented data** — if a column isn't found, we stop and report
- **Everything logged** — every fetch records URL, bytes, SHA-256

## License

Internal project — not for distribution.
