# Project Status vs. `Plan.md` (Phase 0 Audit)

**Date:** 2026-08-05
**Scope:** State of the AI-zhaimer project compared against the Phase 0 plan in `Plan.md` (PEARL-Neuro EEG classification project, OpenNeuro `ds004796`), plus the root-repo roadmap in `PROJECT.md`.

---

## TL;DR

**`Plan.md` (Phase 0 audit) is ~85% implemented and has been executed end-to-end** — all artifacts exist, `pytest` is green (56 passed), and the audit verdict is **PROCEED_WITH_CONDITIONS**. However:

- There are **two real bugs** (task extraction in the size survey, report rendering of the sub-69 line) that make parts of the deliverable unreliable.
- Several **§3 requirements were silently skipped** — the dataset version and the resolved genotype column mapping were never written into `config/audit.yaml`.
- The plan's central premise about the dataset ("IDs run 01–80") turned out to be **wrong** — the real `participants.tsv` has **192 subjects (IDs up to sub-200)**, 113 of whom are not in the client's list.
- `pearl/` and `Plan.md` are **not committed to git yet**.

---

## Headline findings vs. the five questions Plan.md asks

| # | Question | Status |
|---|---|---|
| 1 | Do the 31/26/22 groups reconcile with genotypes? | ✅ **Yes — 0 mismatches** across all 79 client subjects |
| 2 | What is sub-69? | ⚠️ **Absent from `participants.tsv` entirely** (confirmed: `grep -c 'sub-69'` = 0). The report verdict states this correctly, but the report's own discrepancy line renders "sub-69: unknown" due to a rendering bug |
| 3 | Missing EEG runs / balanced? | ❌ **Not actually computed.** Task extraction regex fails on `sub-XX_task-*.eeg` filenames → the EEG inventory has **no per-task columns** and `effective_n.csv` (the plan's "single most useful artefact") is **empty**. The sub-51/sub-55 verification silently no-ops |
| 4 | Confounded by age/sex/education? | ✅ **All CLEAR** across all 3 framings (12 tests) — but effect sizes have **no confidence intervals** (plan required them) |
| 5 | Phase 1 download cost? | ✅ **EEG = 75.87 GB**, fits the 95 GB usable budget → "Full EEG modality fits" is correct. But the "Rest+MSIT = 0.0 GB" subset figure is **bogus** (same task-extraction bug) |

---

## Section-by-section vs. Plan.md

### §1 Environment setup — ⚠️ Partially met

- `.venv` and `.cache` exist under `pearl/`.
- Byte-budget guard (50 MB) and disk-space guard (20 GB) are implemented and unit-tested in `pearl/src/pearl_audit/paths.py`.
- **Gap:** `config/audit.yaml` still shows `version: null`, `fetch_date: null`, and all `columns: null`. The plan's "verification gate" results were never persisted into config.

### §2 Repository scaffold — ✅ Complete

- Full `pearl/` tree matches the plan structure (`config/`, `src/pearl_audit/` with all 9 modules, `data/`, `reports/`, `logs/`, `tests/`).
- `config/client_groups.yaml` is transcribed verbatim, with a test asserting the three lists are disjoint, sum to 79, and exclude `sub-69`.
- **Note:** the plan says the root should be `D:\pearl\`, but the code lives at `D:\younes\AI-zhaimer\pearl\`. `paths.py` derives the root from `__file__` so this works, but `pearl/README.md`'s env-var examples still point at `D:\pearl\.cache\...` (doc drift).

### §3 Fetch metadata — ⚠️ Fetched OK, two requirements skipped

- All 5 metadata files fetched via the GraphQL route and logged with URL, bytes, and SHA-256 in `logs/fetch_log.jsonl`. 7 runs logged on 2026-08-02, ~491 KB cumulative — far under the 50 MB cap. **No raw EEG was ever downloaded.**
- `reports/participants_schema.txt` produced (192 rows × 87 columns).
- **Skipped #1:** the dataset version was never recorded. `dataset_description.json` has no `DatasetVersion` field (only a DOI embedding `v1.0.0`), so `resolve_dataset_version()` returned `None` and `config/audit.yaml` was never updated. The report header says "Dataset version: None".
- **Skipped #2:** the resolved column mapping (APOE → `APOE_haplotype`, PICALM → `PICALM_rs3851179`, etc.) was never written into `config/audit.yaml`. `identify_genotype_columns()` computes the mapping and discards it; downstream modules fall back to string-matching heuristics instead of a persisted, audited mapping.

### §4 Size survey — ⚠️ Runs, but task parsing is broken

- Produces `data/derivatives/phase0/size_survey.csv` (2,638 files, 257.9 GB total: EEG 75.87 GB, func 164.32 GB, root ~0.02 GB).
- **Bug:** `_parse_listing` extracts the task with `re.match(r"task-(\w+)", fname)`, which only matches filenames *starting* with `task-`. Real EEG files are named `sub-80_task-msit_eeg.eeg`, so the `task` field is empty for every subject-level file.
- **Consequences:** the rest+MSIT subtotal is **0 bytes** (should be tens of GB), and the per-task breakdown that §4 requires is absent. The "Fits subset" flag is therefore meaningless.

### §5 Group reconciliation — ⚠️ Core logic correct, artifact inconsistencies

- 0 mismatches across all 79 client subjects; the "2 e4/e4 homozygotes" claim holds (sub-33, sub-41).
- Stop-gate (≤2 mismatches) passed.
- **Issue:** the reconciliation CSV marks `match=False` for all 113 "extra" subjects (they're `NOT_IN_CLIENT_LIST`), yet the generated report displays them as "YES" — the on-disk CSV and the report are inconsistent (stale artifacts from different runs).
- The discrepancy summary line "Missing from TSV: none" contradicts the verdict that sub-69 is absent (sub-69 isn't in the client list, so the code never counts it as missing from the TSV).

### §6 EEG inventory & effective N — ❌ Broken output (most important gap)

- `data/derivatives/phase0/eeg_inventory.csv` contains only `subject, total_eeg_bytes` — **no `has_<task>` columns** (because the size-survey `task` column is empty).
- `data/derivatives/phase0/effective_n.csv` is **empty** — the plan calls this "the single most useful artefact of Phase 0."
- The plan's requirement to verify (not trust) the documented missingness — sub-51 missing Sternberg, sub-55 missing rest — **silently no-ops** because the `has_sternberg` / `has_rest` columns don't exist.

### §7 Confound analysis — ✅ Runs, with gaps

- 12 tests (3 framings × 4 variables: age, education, sex, dementia_history_parents). All verdicts **CLEAR**; `dementia_history_parents` was correctly picked up from the schema.
- **Gaps vs. plan:** effect sizes reported **without confidence intervals** (plan explicitly required "effect size with a confidence interval"); `education` treated as continuous (Kruskal–Wallis) though it is a 3-level code; only 4 variables tested though the schema has many more (BMI, smoking, SES, EHI, BDI, blood panel, etc.).

### §8 Report — ⚠️ Generated, with rendering bugs

- Both `reports/phase0_audit.html` (self-contained) and `reports/phase0_audit.md` exist; verdict leads.
- **Bug:** the sub-69 line renders `unknown` because `report.py` reads `.status` from the reconciliation summary, but `reconcile_groups.py` emits a `present_in_tsv` key.
- The Markdown version is missing the "Open Questions & Assumptions" section required by §8.
- Provenance table shows "Version: None / Fetch date: None" (see §3).

### §9 Tests — ✅ 56 passed

- Coverage: `client_groups.yaml` consistency, genotype normaliser, disk guard, byte budget, reconciliation on a synthetic fixture, CLI basics.
- **Gap:** no tests for the size-survey task parsing, EEG inventory / effective-N computation, or report rendering — exactly where the bugs are.

### §10 Definition of Done — 6 of 9 effectively met

- ✅ `run-all` has executed clean (7 runs on 2026-08-02)
- ✅ Nothing written to `C:` (guards in place; work happened on `D:`)
- ✅ Total downloaded bytes < 50 MB, logged with hashes (~491 KB cumulative)
- ✅ No raw EEG file fetched
- ⚠️ All CSVs exist, but `effective_n.csv` is **empty** — the deliverable table is missing
- ✅ `reports/phase0_audit.html` opens standalone and leads with a verdict
- ✅ `pytest` green (56 passed)
- ✅ `README.md` documents setup and re-run (though with the `D:\pearl` path drift)
- ⚠️ Stop-gates: the sub-51/sub-55 verification was skipped rather than passed or reported

---

## Root repo (PROJECT.md track) state

- **Committed (5 commits):** repo scaffold, `data/labels/participants_labels.tsv` (79 rows, 31/26/22 ✓), `environment.yml`, Phase 0 setup plan; `reference/classification.pdf` is in place.
- **Not started:** `data/bids/` (Phase 1), real FreeSurfer `recon-all` (`freesurfer/run_recon_all.sh` is an exit-1 stub — Phase 2), WSL2 + FreeSurfer install verification (requires user-side actions).
- **Not committed:** `Plan.md` and the entire `pearl/` tree are untracked.

---

## The one big thing to flag to the client

The plan assumed IDs run 01–80. The dataset's `participants.tsv` actually contains the **full 192-subject genetic cohort** (sub-01…sub-200 with gaps), and only the 79 in the client list have EEG/fMRI. The dataset README confirms this: *"Full cohort: 192 healthy middle-aged individuals… Cohort subgroup: 79… Neuroimaging data."*

So **sub-69 is not a numbering mystery — it is simply not one of the 192 rows at all.** The report's verdict captures this ("sub-69 is absent from participants.tsv"), but it should state the 192-vs-79 framing explicitly rather than framing sub-69 as "an anomaly that must be documented."

---

## Gap list (candidate fixes)

1. **Fix task extraction** in `size_survey.py` so `sub-XX_task-<task>_*.eeg` filenames populate the `task` column → unlocks the rest+MSIT subtotal and the EEG inventory.
2. **Populate `config/audit.yaml`**: write the dataset version (from DOI/CHANGES if no `DatasetVersion` field) and the resolved genotype column mapping after fetch.
3. **Recompute the EEG inventory / effective-N table** and verify the sub-51 / sub-55 missingness claims against the listing.
4. **Fix report rendering**: sub-69 line (`status` vs `present_in_tsv`), re-generate so CSV and report agree, add the Open Questions section.
5. **Add tests** for task parsing, inventory/effective-N, and report generation.
6. **Add confidence intervals** to confound effect sizes.
7. **Commit `pearl/` and `Plan.md`** (or decide explicitly to keep them untracked).

---

## Reproduction

```bash
cd pearl
pip install -e ".[dev]"     # or conda env from ../environment.yml
python -m pearl_audit.cli run-all
pytest tests/ -q            # 56 passed as of 2026-08-05
```
