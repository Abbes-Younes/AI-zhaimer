# Phase 0 — Data Audit & Ground-Truth Lock

**Agent instructions. Read this whole file before writing any code.**

You are turning an empty folder into a reproducible Phase 0 deliverable for an EEG
classification project on the PEARL-Neuro dataset (OpenNeuro `ds004796`).

Phase 0 answers five questions and nothing else:

1. Does the client's 31 / 26 / 22 group assignment reconcile with the official
   genotype columns in the dataset's `participants.tsv`?
2. What is `sub-69`? (IDs run 01–80, only 79 are assigned to groups.)
3. Which subjects are missing which EEG runs, and is that missingness balanced
   across groups?
4. Are the groups confounded by age, sex, or education?
5. How many bytes would a Phase 1 EEG-only download actually cost?

If Phase 0 says the groups are irreconcilable or badly confounded, the project
changes shape. **Do not start Phase 1. Do not build a model. Do not touch raw EEG.**

---

## 0. Hard constraints — violating any of these is a failed run

| Constraint | Rule |
|---|---|
| **No raw EEG download** | Phase 0 downloads metadata only. Total bytes written to disk by this phase must stay **under 50 MB**. Enforce it in code. |
| **C: drive is nearly full (7 GB)** | Nothing may be installed or cached on `C:`. See §1. |
| **D: drive has 115 GB** | All code, venv, caches, and data live on `D:`. Abort if free space on `D:` drops below 20 GB. |
| **No invented data** | If a column, file, or field is not found, **stop and report it**. Never fabricate a plausible value, never silently fall back to a guess. |
| **Everything logged** | Every network fetch records URL, byte count, and SHA-256 into `logs/fetch_log.jsonl`. |

The environment is Windows. Use `pathlib`, never hardcode `/`-style paths, and make
every script runnable as `python -m pearl_audit.<module>`.

---

## 1. Environment setup (do this first, verify before proceeding)

Python tooling defaults to `C:` for caches and temp files and will fill it. Redirect
everything to `D:` **before** installing anything.

Create `D:\pearl\` as the project root. Set these for the session (and document them
in the README so they can be re-set):

```
UV_CACHE_DIR      = D:\pearl\.cache\uv
PIP_CACHE_DIR     = D:\pearl\.cache\pip
TMP               = D:\pearl\.cache\tmp
TEMP              = D:\pearl\.cache\tmp
XDG_CACHE_HOME    = D:\pearl\.cache
MPLCONFIGDIR      = D:\pearl\.cache\mpl
AWS_CONFIG_FILE   = D:\pearl\.cache\aws\config
```

Create the venv at `D:\pearl\.venv`. Use `uv` if available, otherwise `python -m venv`.

**Verification gate — print and check before continuing:**
- free space on `C:` and `D:`
- `sys.prefix` resolves under `D:\pearl`
- `tempfile.gettempdir()` resolves under `D:\pearl`

If any of these still point at `C:`, stop and report rather than proceeding.

Dependencies for Phase 0 only (keep it minimal — MNE and friends come in Phase 1):

```
pandas, numpy, scipy, pyyaml, requests, jinja2, pytest
```

`awscli` is optional; §3 gives an HTTPS fallback if it is unavailable.

---

## 2. Repository scaffold

Create exactly this structure at `D:\pearl\`:

```
pearl/
├─ README.md
├─ pyproject.toml
├─ .gitignore                 # ignores data/, logs/, .venv/, .cache/, reports/*.html
├─ config/
│  ├─ client_groups.yaml      # §2.1 — transcribed client spec, the thing under test
│  └─ audit.yaml              # thresholds, dataset accession, expected counts
├─ src/pearl_audit/
│  ├─ __init__.py
│  ├─ paths.py                # single source of truth for all paths + disk guard
│  ├─ fetch_metadata.py       # §3
│  ├─ size_survey.py          # §4
│  ├─ reconcile_groups.py     # §5
│  ├─ inventory.py            # §6
│  ├─ confounds.py            # §7
│  ├─ report.py               # §8
│  └─ cli.py                  # `python -m pearl_audit.cli run-all`
├─ data/
│  ├─ raw_meta/               # participants.tsv, *.json sidecars
│  └─ derivatives/phase0/     # generated CSVs
├─ reports/
├─ logs/
└─ tests/
```

`paths.py` exposes a `require_free_space(min_gb=20)` helper that raises on `D:`, and
a `record_download(url, path, nbytes)` helper writing to `logs/fetch_log.jsonl` and
raising once cumulative bytes exceed 50 MB.

### 2.1 `config/client_groups.yaml`

Transcribe the client's grouping table verbatim. This is the **claim being tested**,
not the ground truth — never edit it to make reconciliation pass.

```yaml
source: "client-supplied classification document (PDF)"
groups:
  N:
    definition: "APOE e3/e3 + PICALM neutral (AA/AG)"
    expected_total: 31
    subjects: [sub-01, sub-02, sub-03, sub-04, sub-05, sub-06, sub-07, sub-08,
               sub-09, sub-10, sub-11, sub-12, sub-13, sub-14, sub-15, sub-16,
               sub-17, sub-18, sub-19, sub-20, sub-21, sub-22, sub-23, sub-24,
               sub-25, sub-26, sub-27, sub-28, sub-29, sub-30, sub-31]
  A_P_minus:
    definition: "APOE e4 + PICALM neutral (AA/AG)"
    expected_total: 26
    subjects: [sub-38, sub-47, sub-53, sub-57, sub-58, sub-59, sub-60, sub-61,
               sub-62, sub-63, sub-64, sub-65, sub-66, sub-67, sub-68, sub-70,
               sub-71, sub-72, sub-73, sub-74, sub-75, sub-76, sub-77, sub-78,
               sub-79, sub-80]
  A_P_plus:
    definition: "APOE e4 + PICALM risk (GG); includes 2 e4/e4 homozygotes"
    expected_total: 22
    subjects: [sub-32, sub-33, sub-34, sub-35, sub-36, sub-37, sub-39, sub-40,
               sub-41, sub-42, sub-43, sub-44, sub-45, sub-46, sub-48, sub-49,
               sub-50, sub-51, sub-52, sub-54, sub-55, sub-56]

targets:
  binary_risk_vs_none:   {class_0: [N], class_1: [A_P_minus, A_P_plus]}
  binary_high_vs_rest:   {class_0: [N, A_P_minus], class_1: [A_P_plus]}
  multiclass_3:          {class_0: [N], class_1: [A_P_minus], class_2: [A_P_plus]}
```

Write a test asserting the three lists are disjoint, contain no duplicates, and sum
to 79. Assert `sub-69` is absent from all three.

---

## 3. Fetch metadata only

Target files from `ds004796`:

- `participants.tsv` and `participants.json`
- `dataset_description.json`
- `README` / `CHANGES` if present
- task sidecars: `task-*_eeg.json` at dataset root

Preferred route (no credentials needed):

```
aws s3 cp --no-sign-request s3://openneuro.org/ds004796/participants.tsv <dest>
```

Fallback if `awscli` is unavailable: fetch the same paths over HTTPS from the
OpenNeuro S3 endpoint. **Resolve the working base URL at runtime and log it** — do
not hardcode a URL pattern from memory. If neither route works, stop and report the
exact error rather than improvising a mirror.

Record the dataset version from `dataset_description.json` into `config/audit.yaml`.
Every downstream artefact must carry that version string. The dataset has been
revised more than once; an audit that doesn't name its version is worthless.

**Immediately after fetching, dump `participants.tsv`'s column names and dtypes to
`reports/participants_schema.txt` and print them.** Do not guess which columns hold
APOE and PICALM genotypes. Inspect `participants.json` for the authoritative
descriptions, then write the resolved mapping into `config/audit.yaml` as:

```yaml
columns:
  subject_id: "<resolved>"
  apoe: "<resolved>"
  picalm: "<resolved>"
  age: "<resolved>"
  sex: "<resolved>"
  education: "<resolved or null>"
```

**Stop-gate:** if the APOE or PICALM columns cannot be identified with confidence,
halt and report the full schema. Do not proceed on a guess — everything downstream
inherits that error.

---

## 4. Size survey (listing only, zero downloaded bytes)

List the bucket recursively and aggregate sizes **without downloading**:

```
aws s3 ls --no-sign-request --recursive --summarize s3://openneuro.org/ds004796/
```

Parse the listing into `data/derivatives/phase0/size_survey.csv` with per-file
`path, bytes, modality, subject, task`, then produce a summary table of total bytes
grouped by:

- modality (`eeg`, `func`, `anat`, `beh`, root metadata)
- task within EEG (`rest`, `msit`, `sternberg`, and whatever the actual task labels
  turn out to be — read them from the paths, don't assume)

Then emit a **Phase 1 download plan**: the byte cost of the EEG-only subset, and of
the narrower `eyes-closed rest + MSIT` subset, each expressed as a percentage of the
115 GB budget with 20 GB held in reserve. Flag explicitly whether the full EEG
modality fits. If it does not, the plan must recommend the task-level subset.

---

## 5. Group reconciliation

Reconstruct group membership from the genotype columns using the client's stated
definitions, then diff against `client_groups.yaml`.

Genotype string formats are unknown until you look — APOE may appear as `e3/e3`,
`33`, `E3E3`, or as two separate allele columns; PICALM as `AA`/`AG`/`GG` or as an
rs-number call. **Inspect the actual unique values first**, write the normalisation
rules into `config/audit.yaml`, and make the normaliser a pure, unit-tested function.

Produce `data/derivatives/phase0/group_reconciliation.csv`:

| subject | apoe_raw | picalm_raw | apoe_norm | picalm_norm | group_derived | group_client | match |
|---|---|---|---|---|---|---|---|

And a discrepancy summary listing:
- subjects in the client list but absent from `participants.tsv`
- subjects in `participants.tsv` but in no client group (expect at least `sub-69`)
- subjects whose derived group differs from the client's assignment
- whether the "2 e4/e4 homozygotes" claim for A+P+ holds

**`sub-69` specifically:** determine whether it is absent from `participants.tsv`
entirely, present but without EEG, or present and simply omitted by the client.
Report which. Do not assume it was excluded for cause.

**Stop-gate:** if more than 2 subjects mismatch, halt and report. A systematic
mismatch means the client's grouping rule differs from the one stated in the PDF,
and every label in the project is suspect until that's resolved.

---

## 6. EEG run inventory

From the §4 listing (still no downloads), build
`data/derivatives/phase0/eeg_inventory.csv` — one row per subject, one boolean
column per EEG task/run, plus file sizes.

The dataset's own documentation reports that Sternberg EEG is missing for `sub-51`
and resting-state EEG is missing for `sub-55`. **Verify this against the listing
rather than trusting it**, and report any additional gaps found.

Then cross-tabulate missingness against group. Note in advance: both `sub-51` and
`sub-55` fall in `A_P_plus`, the smallest group (22). If missingness concentrates in
the smallest class, effective n per task drops asymmetrically and the report must
say so prominently — it changes the CV design in Phase 3.

Output the **effective n per task per group** as a standalone table. That table is
the single most useful artefact of Phase 0.

---

## 7. Confound analysis

For each candidate confound (`age`, `sex`, `education`, and any other demographic or
health column present — family history of dementia is likely available and matters
here):

- descriptive stats per group
- appropriate test: Kruskal–Wallis for continuous, chi-square or Fisher's exact for
  categorical (use Fisher when any expected cell count < 5)
- **effect size with a confidence interval**, not just a p-value — with n=79 the
  p-value alone tells you almost nothing
- repeat for all three target framings from `client_groups.yaml`, since a confound
  can be benign in the 3-class split and severe in a binary collapse

Emit `data/derivatives/phase0/confound_report.csv` and assign each variable a plain
verdict: `clear` / `watch` / `blocking`. Age is the one to watch hardest — individual
alpha frequency tracks age, so an age-imbalanced grouping makes every alpha-derived
feature partly an age detector.

For any variable marked `watch` or `blocking`, the report must state the mitigation
required in Phase 3 (covariate adjustment, matched subsampling, or stratified folds).
State the mitigation; do not implement it in Phase 0.

---

## 8. Report

Generate `reports/phase0_audit.html` — a **self-contained single file** (inline CSS,
no CDN links, tables rendered as HTML not images) so it can be opened or forwarded
as-is. Also write `reports/phase0_audit.md` with the same content.

Structure:

1. **Verdict** — one paragraph at the top: proceed / proceed with conditions / stop,
   and why. Written for someone who reads only this paragraph.
2. Dataset provenance — accession, version, fetch date, byte log summary
3. Group reconciliation, including the `sub-69` finding
4. EEG inventory + effective n per task per group
5. Confound table with verdicts and required mitigations
6. Phase 1 download plan against the 115 GB budget
7. Open questions and assumptions made
8. Reproduction instructions

Every number in the report must trace to a CSV in `data/derivatives/phase0/`. No
figure appears in prose that isn't in a file.

---

## 9. Tests

`pytest` must pass before you declare Phase 0 done:

- `client_groups.yaml` is internally consistent (disjoint, 79 total, no `sub-69`)
- genotype normaliser is correct on hand-written cases covering every raw format
  observed in the data, plus malformed input (raises, not silently returns `None`)
- disk guard raises below the threshold
- byte budget guard raises above 50 MB
- the reconciliation function, given a synthetic fixture, produces a known diff
- report generation runs end to end on the fixture

---

## 10. Definition of done

- [ ] `python -m pearl_audit.cli run-all` executes clean from a fresh venv
- [ ] Nothing was written to `C:`
- [ ] Total downloaded bytes < 50 MB, logged with hashes
- [ ] No raw EEG file was fetched
- [ ] All four CSVs exist in `data/derivatives/phase0/`
- [ ] `reports/phase0_audit.html` opens standalone and leads with a verdict
- [ ] `pytest` green
- [ ] `README.md` documents setup, the `D:` redirection, and how to re-run
- [ ] Every stop-gate either passed or is reported as an open blocker

---

## What to do when something is ambiguous

Stop and report. Phase 0 exists to find problems, so surfacing one is a success, not
a failure. A halted run with a clear question beats a completed run built on a guess
— the entire point of this phase is that the labels are trustworthy before anyone
spends a week on features.