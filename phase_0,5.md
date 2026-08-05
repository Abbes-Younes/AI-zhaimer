# Phase 0.5 — Remediation, Close-out & Phase 1 Download Manifest

**Agent instructions. Read this whole file before writing any code.**

Phase 0 ran end to end and produced a `PROCEED_WITH_CONDITIONS` verdict, but three
of its outputs are not trustworthy and one of its founding assumptions was wrong.
This phase makes Phase 0 defensible and ends by producing — **but not executing** —
an explicit download manifest for Phase 1.

**You will not download a single raw EEG file in this phase.** The 50 MB byte budget
from `Plan.md` still holds, with one narrow exception granted in Task 6.

---

## Why this phase exists

The broken task-extraction bug is not cosmetic. It is upstream of the EEG inventory,
which is upstream of `effective_n.csv`, which is upstream of the Phase 1 download
plan — and the disk budget is genuinely tight:

```
D: free                    ~115 GB
reserve (non-negotiable)    -20 GB
                          =  95 GB usable
raw EEG (measured)          -75.87 GB
                          =  19 GB left for ALL derivatives
```

19 GB is not obviously enough for preprocessed derivatives of 128-channel EEG across
three tasks. The "Full EEG modality fits" conclusion in the current report is
therefore **premature**, not wrong — it accounts for the raw download and nothing
else. Task 6 replaces it with a real budget model.

---

## Priority order

| P | Tasks | Why |
|---|---|---|
| **P0** | 1, 2, 6 | Blocks Phase 1 — cannot download safely without these |
| **P1** | 3, 4, 5, 7 | Correctness and trustworthiness of the audit |
| **P2** | 8, 9 | Hygiene, but do them — they prevent the same class of bug |

---

## Task 1 — Replace the task regex with a real BIDS entity parser (P0)

**Do not patch the regex.** `re.match(r"task-(\w+)", fname)` failed because it
anchors at the start of the filename; a looser regex would work today and break on
the next entity you meet (`acq-`, `run-`, `ses-`, `split-`).

Write `parse_bids_entities(path: str) -> dict` in a new `src/pearl_audit/bids.py`:

- take the filename stem, split on `_`
- every `key-value` chunk becomes an entity; the final chunk without a `-` is the
  suffix (`eeg`, `bold`, `T1w`)
- return `{"sub": ..., "task": ..., "run": ..., "suffix": ..., "ext": ...}` with
  `None` for absent entities
- it must be pure, side-effect free, and never raise on a malformed name — return
  `{}` and let the caller decide

**Regression fixtures — take real paths from the existing `size_survey.csv`**, not
invented ones. At minimum cover:

```
sub-80_task-msit_eeg.eeg
sub-80_task-msit_eeg.vhdr
sub-80_task-msit_eeg.vmrk
sub-01_task-rest_eeg.json
dataset_description.json          -> {} (no entities)
participants.tsv                  -> {} (no entities)
```

Then rewire `size_survey.py` to use it. **Print the set of distinct `task` values
found and assert it is non-empty** before writing the CSV — the original bug survived
because nothing checked that the column had content.

You do not know the real task labels. Read them from the data (`rest`, `msit`,
`sternberg` are the likely names but confirm), and record the observed set in
`config/audit.yaml` under `observed_tasks`.

---

## Task 2 — Reframe the cohort: 192 genetic, 79 imaging (P0)

The current reconciliation treats 113 subjects as failed matches. They are not
discrepancies — they are the genetic-only portion of the cohort. `participants.tsv`
holds all 192 genotyped participants; only 79 have neuroimaging.

Replace the boolean `match` column with a three-valued `status`:

| status | meaning |
|---|---|
| `RECONCILED` | in client list, derived group == client group |
| `MISMATCH` | in client list, derived group != client group |
| `GENETIC_COHORT_ONLY` | in `participants.tsv`, not in client list, no imaging expected |
| `MISSING_FROM_TSV` | in client list, absent from `participants.tsv` |

The stop-gate counts `MISMATCH` and `MISSING_FROM_TSV` only.

Emit a new `data/derivatives/phase0/cohort_definition.csv` defining the **analysis
cohort** explicitly: subject, in_client_list, in_participants_tsv, has_any_eeg,
final_include flag. Everything downstream — confounds, effective N, Phase 1 —
filters on `final_include`, and nothing re-derives cohort membership on its own.

**Verify and state in the report whether the existing confound tests ran on the 79 or
on all 192.** If they ran on 192, they are invalid and must be re-run. Add an
assertion that the confound input frame has exactly `len(analysis_cohort)` rows.

Reframe the sub-69 finding accordingly: it is not an anomaly requiring explanation,
it is simply not one of the 192 genotyped participants. Say that plainly and close
the question.

---

## Task 3 — Persist config, and delete every heuristic fallback (P1)

Two `Plan.md` §3 requirements were computed and thrown away.

**3a. Genotype column mapping.** `identify_genotype_columns()` resolves
`APOE_haplotype` / `PICALM_rs3851179` and discards them. Write the resolved mapping
into `config/audit.yaml` immediately after fetch.

Then **remove the string-matching fallback in the downstream modules entirely.** If
`config/audit.yaml` has no resolved mapping, downstream must raise, not guess. A
silent fallback that picks the wrong genotype column mislabels the entire dataset
and everything after it looks fine.

**3b. Dataset version.** `dataset_description.json` has no `DatasetVersion` field, so
build a composite provenance record instead and write it to config:

```yaml
provenance:
  accession: ds004796
  version_source: "DOI"          # or "CHANGES" if that file carries one
  version_string: "v1.0.0"
  fetch_date: "<ISO date>"
  participants_tsv_sha256: "<hash>"     # the real fingerprint
  s3_listing_date: "<ISO date>"
```

The `participants.tsv` hash is what actually pins the audit to a specific state of
the data. Treat it as the authoritative version identifier and print it in the report
header. Note in the report that OpenNeuro has published multiple revisions of this
dataset, so a re-run producing a different hash invalidates prior artifacts.

---

## Task 4 — Make runs atomic and stamped (P1)

The reconciliation CSV and the report disagree because they came from different runs.
Fix the mechanism, not the artifacts:

- generate a `run_id` (UTC timestamp + short git SHA) at the start of `run-all`
- write all artifacts to `data/derivatives/phase0/.tmp-<run_id>/`, then swap into
  place only after every step succeeds
- stamp `run_id` into a header comment or a `_meta.json` beside the CSVs
- **`report.py` must assert all its input artifacts share one `run_id` and refuse to
  render otherwise**

This alone would have caught the inconsistency the audit found.

---

## Task 5 — Rebuild the EEG inventory and effective-N table (P1, unblocked by Task 1)

With entity parsing fixed, regenerate:

**`eeg_inventory.csv`** — one row per analysis-cohort subject, with `has_<task>`
boolean columns and `bytes_<task>` for each observed task.

**`effective_n.csv`** — the artifact `Plan.md` calls the single most useful output:
rows = task, columns = group (N, A+P−, A+P+), cells = count of subjects with that
task present, plus a total column.

Then verify — do not assume — the documented missingness: Sternberg absent for
`sub-51`, resting-state absent for `sub-55`. Report agreement or disagreement
explicitly, and list any additional gaps.

Cross-tabulate missingness against group and compute whether it is plausibly random
(Fisher's exact on missing × group). Flag prominently if gaps concentrate in
A+P+, the smallest group at 22 — that asymmetry drives CV design in Phase 3.

---

## Task 6 — Phase 1 download manifest and real disk budget (P0)

This is the deliverable that gates Phase 1.

**6a. Fetch EEG sidecar JSONs only.** You need `SamplingFrequency`, `EEGChannelCount`
and `RecordingDuration` to model derivative sizes. Fetch `*_eeg.json` sidecars —
these are kilobyte-scale. Log them against the byte budget as usual; this is the one
exception referred to at the top, and it does not extend to `.eeg`, `.vhdr`, or
`.vmrk` files.

**6b. Model the derivative footprint.** For each candidate scope, estimate:

```
preprocessed_bytes ≈ n_subjects × n_channels × duration_s × target_sfreq × 4 bytes
```

Use float32 and the target sampling rate you intend for Phase 1 (250 Hz is the
sensible default for alpha-band work; state the assumption). Add epoched output and
ICA solutions on top. Present the estimate with its assumptions visible so the number
can be challenged.

**6c. Produce three costed scopes** in `reports/phase1_download_plan.md`:

| Scope | Raw GB | Est. derivatives GB | Total | Fits in 95 GB? |
|---|---|---|---|---|
| A — full EEG (all tasks) | 75.87 | ? | ? | ? |
| B — rest + MSIT | ? | ? | ? | ? |
| C — rest(eyes-closed) + MSIT only | ? | ? | ? | ? |

Recommend one. My prior is that **Scope B or C is correct** — the published
benchmark on this dataset came from MSIT, and eyes-closed rest is where the alpha
rhythm the PSWT approach depends on is strongest. Sternberg can be fetched later if
the pipeline works. But let the measured numbers decide, and say so if they point
elsewhere.

**6d. Emit `data/derivatives/phase0/phase1_manifest.csv`** — the explicit list of
S3 keys to fetch for the recommended scope, with per-file bytes and a running total.
Phase 1 will consume this file directly; it should require no re-derivation.

**Then stop.** Do not download. The manifest goes to the human for approval — with
19 GB of headroom under the full-EEG scope, an unapproved download is the one
mistake in this project that is genuinely expensive to undo.

---

## Task 7 — Report fixes (P1)

- fix the sub-69 rendering: `report.py` reads `.status`, `reconcile_groups.py` emits
  `present_in_tsv` — reconcile the key names and add a test that asserts the rendered
  line matches the verdict
- add the missing **Open Questions & Assumptions** section to the Markdown version
- provenance header shows the Task 3b record, never `None`
- add a **Cohort Definition** section leading with the 192-vs-79 framing
- add the effective-N table and the Phase 1 scope recommendation
- re-assert: every number in prose traces to a CSV under the same `run_id`

---

## Task 8 — Confound analysis gaps (P2)

- **Confidence intervals**, as `Plan.md` required: bootstrap (≥2000 resamples) CIs
  for ε² on Kruskal–Wallis and Cramér's V on chi-square/Fisher. At n=79 the CIs will
  be wide — that is the finding, and it belongs in the report.
- **Education is a 3-level ordinal code**, not continuous. Test it as categorical
  (chi-square/Fisher) *and* for monotone trend (Spearman or Jonckheere–Terpstra).
  Report both.
- **Expand the variable set.** The schema has 87 columns. Screen the demographic,
  lifestyle and health variables (BMI, smoking, SES, EHI, BDI, blood panel) against
  group, with FDR correction across the screen. Anything that separates groups is
  either a confound to control or a feature worth knowing about.
- Keep the `clear` / `watch` / `blocking` verdicts, and for every non-clear variable
  state the Phase 3 mitigation without implementing it.

---

## Task 9 — Tests and version control (P2)

Add tests exactly where the bugs were, since that is where they will recur:

- `parse_bids_entities` on real filenames from the listing, including malformed input
- size survey produces a non-empty `task` column (guard against the original bug)
- effective-N computation on a synthetic fixture with known missingness
- report rendering: sub-69 line matches verdict; `run_id` mismatch raises
- `cohort_definition` filtering: confound input has exactly 79 rows
- downstream raises when `config/audit.yaml` has no genotype mapping

Then commit. `pearl/` and `Plan.md` are untracked, which means Task 4's git-SHA
stamping cannot work and the audit has no provenance. Commit the tree, add
`data/`, `logs/`, `reports/*.html`, `.venv/`, `.cache/` to `.gitignore`, and fix the
`D:\pearl\` path drift in `pearl/README.md` to match the real root at
`D:\younes\AI-zhaimer\pearl\`.

---

## Definition of done

- [ ] `task` column populated for every subject-level file; observed task set recorded
- [ ] `effective_n.csv` non-empty, with per-task per-group counts
- [ ] sub-51 / sub-55 missingness verified against the listing, not assumed
- [ ] `cohort_definition.csv` exists; confound tests confirmed to run on 79 rows
- [ ] `config/audit.yaml` carries the genotype mapping and the provenance record
- [ ] every heuristic column-matching fallback deleted; missing config raises
- [ ] all artifacts from one `run_id`; report refuses to render on mismatch
- [ ] `reports/phase1_download_plan.md` costs three scopes and recommends one
- [ ] `phase1_manifest.csv` generated, **nothing downloaded**
- [ ] report verdict re-issued, leading with the 192-vs-79 framing
- [ ] `pytest` green, including tests at all four former bug sites
- [ ] `pearl/` and `Plan.md` committed
- [ ] cumulative downloaded bytes still under 50 MB

---

## Stop and escalate if

- the confound tests turn out to have run on all 192 rows and re-running on 79
  changes any verdict from `clear`
- the sub-51 / sub-55 missingness disagrees with the dataset's own documentation
- Scope C does not fit the budget, or the derivative estimate exceeds 19 GB under
  the full-EEG scope
- any `MISMATCH` appears after the Task 2 status refactor

Each of these changes the shape of Phase 1. Report and wait rather than
choosing a workaround.