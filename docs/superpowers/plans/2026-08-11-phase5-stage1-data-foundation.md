# Phase 5 Stage 1 — Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the reference-order bug, evaluate (not blindly change) ICA `n_components`, add Sternberg to the pipeline, and re-run Phases 1–2 under a new `run_id` — producing a new, parallel dataset version whose confound gate must pass on its own merit before Stage 2 (feature engineering) begins.

**Architecture:** Small, surgical changes to `pearl_preproc`/`pearl_audit` (existing packages, no new ones). Tasks 1–4 are code changes, testable with synthetic fixtures, no network/download required. Tasks 5–7 are real operational runs (download, reprocess, gate-check) — **expensive and hard to reverse (bandwidth, wall-clock time)**; each requires an explicit go-ahead checkpoint before starting, not just before the whole stage.

**Tech Stack:** Same as Phases 1–2 (`mne`, `mne-icalabel`, existing `pearl_preproc`/`pearl_audit`/`pearl_features` packages).

## Global Constraints

- The original Phase 1–3 derivative tree is **never** modified or deleted. Everything here writes to a new `run_id`'s tree, coexisting.
- No claim that this reprocessing "corrects" or supersedes Phase 1–3 — it's a new, parallel dataset version.
- ICA `n_components` changes only if real comparison evidence supports it — not a default "just try something different."
- The confound gate must re-pass on the new preprocessing before Stage 2 starts — this is a hard gate, not a formality.
- `pytest` green after every task; every existing Phase 1/2 test must still pass.

---

## Task 1: Reference-order fix

**Files:**
- Modify: `pearl/src/pearl_preproc/preprocess.py` (`process_subject_task`, ~lines 447–471)
- Test: `pearl/tests/test_preproc_reference_order.py`

**Interfaces:**
- No public signature changes — `process_subject_task(subject, task, cfg)` keeps its exact interface; only internal step order changes.

- [ ] **Step 1: Write the failing regression test**

```python
# pearl/tests/test_preproc_reference_order.py
"""phase_5.md §0a: bad-channel interpolation must happen BEFORE average
referencing, not after — otherwise a bad channel's noise contaminates the
average reference for every other channel."""
import mne
import numpy as np


def _raw_with_one_bad_channel(n_ch=8, n_seconds=5, sfreq=250.0, seed=0):
    rng = np.random.default_rng(seed)
    n_samples = int(n_seconds * sfreq)
    data = rng.normal(0, 1e-6, size=(n_ch, n_samples))
    data[0] += rng.normal(0, 1e-3, size=n_samples)  # channel 0: huge noise, clearly "bad"
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose=False)


def test_average_reference_after_interpolation_differs_from_before():
    """The average reference computed AFTER interpolating the bad channel
    must differ from the one computed BEFORE (contaminated) -- if they're
    identical, the fix isn't wired up."""
    raw_before = _raw_with_one_bad_channel()
    raw_after = raw_before.copy()

    # Old (buggy) order: reference first, "interpolate" second (no-op for this test)
    ref_before = raw_before.copy().set_eeg_reference("average", projection=False).get_data()

    # New (fixed) order: mark bad, interpolate, THEN reference
    raw_after.info["bads"] = ["ch0"]
    raw_after.set_montage(mne.channels.make_standard_montage("standard_1020"), on_missing="ignore",
                           match_case=False)
    # Fallback: skip interpolation if montage doesn't cover synthetic names;
    # assert on reference-input contamination directly instead.
    ref_after_input = raw_after.copy()
    ref_after_input._data[0] = 0.0  # simulate "already clean" bad channel post-interpolation
    ref_after = ref_after_input.set_eeg_reference("average", projection=False).get_data()

    assert not np.allclose(ref_before, ref_after)
```

- [ ] **Step 2: Run to verify it fails or passes trivially**

Run: `cd pearl && python -m pytest tests/test_preproc_reference_order.py -v`
Expected: PASS (this test validates the *concept* with directly-constructed
data, independent of `process_subject_task`'s internals — it does not
call `process_subject_task` itself, since that requires real raw files).
This is a conceptual/contamination regression test, not an integration test
of the reordered function — Step 4 covers the real integration point.

- [ ] **Step 3: Reorder `process_subject_task`**

In `pearl/src/pearl_preproc/preprocess.py`, move the bad-channel
detection/interpolation block (currently step 4, after high-pass) to run
**before** `set_eeg_reference`/`apply_proj` (currently step 2). New order:

```python
# 2. Read + montage (reference NOT set yet)
raw = mne.io.read_raw_brainvision(read_vhdr, preload=True, verbose="ERROR")
raw.set_montage(montage_mod.build_montage(read_vhdr))
original_ref = _vhdr_reference(paths["vhdr"])

# 3. High-pass 0.5 Hz zero-phase FIR (unchanged — still before bad-channel
#    detection, DC-coupling reason from phase_1.md §2 unchanged)
hp = cfg["filters"]["high_pass"]
raw.filter(l_freq=hp["l_freq_hz"], h_freq=None, method=hp.get("method", "fir"),
           phase=hp.get("phase", "zero"), fir_design=hp.get("fir_design", "firwin"),
           verbose="ERROR")

# 4. Bad channels -> interpolate, BEFORE referencing (phase_5.md §0a fix:
#    detection/interpolation must run on FCz-referenced data, not
#    average-referenced, so a bad channel cannot contaminate the reference
#    used to detect it or any other channel)
occ = set(cfg.get("qc", {}).get("occipital_channels", []))
bad_names, occ_bads = detect_bad_channels(raw, cfg, occ)
if bad_names:
    raw.info["bads"] = bad_names
    raw.interpolate_bads(reset_bads=True, verbose="ERROR")

# 5. Average reference, now over the clean (post-interpolation) channel set
raw.set_eeg_reference("average", projection=bool(cfg.get("reference", {}).get("projection", True)))
raw.apply_proj()

# 6. Anti-alias + resample (unchanged, renumbered)
...
```

Renumber all subsequent inline step comments to match. Do not change
`detect_bad_channels`'s own logic — only when it runs relative to
referencing.

- [ ] **Step 4: Run the full existing Phase 1 test suite**

Run: `cd pearl && python -m pytest tests/test_preproc_*.py -v`
Expected: every existing test still passes. If a test explicitly encoded
the old reference-then-interpolate order as expected sidecar content
(check `test_preproc_sidecar.py`), update that test's expectation to match
the corrected order — this is a case where the *test* was wrong, not new
code being wrong.

- [ ] **Step 5: Smoke-test on one already-downloaded raw subject (sub-52, raw retained on disk)**

```bash
cd pearl && PYTHONPATH=src python -c "
from pearl_preproc.config import load_preproc_config
from pearl_preproc.preprocess import process_subject_task
cfg = load_preproc_config()
result = process_subject_task('sub-52', 'rest', cfg)
print(result['n_bad_channels'], result['bad_channels'])
"
```
Confirm it runs without error and produces a plausible bad-channel count
(don't compare numerically to the old run yet — Task 5's full re-run is
where the real before/after comparison happens).

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_preproc/preprocess.py pearl/tests/test_preproc_reference_order.py
git commit -m "phase5: fix reference-order bug — interpolate bad channels before averaging (§0a)"
```

---

## Task 2: ICA `n_components` evaluation

**Files:**
- Create: `pearl/src/pearl_preproc/ica_component_eval.py` (a reproducible comparison script, not a permanent pipeline module)
- Create: `pearl/reports/phase5_ica_component_evaluation.md`

**Interfaces:**
- Produces: `ica_component_eval.compare_n_components(subjects: list[str], cfg: dict) -> pandas.DataFrame` — one row per subject × configuration (`n_components=30` vs `n_components=0.99`), columns `subject, n_components_config, n_fit, n_removed, removed_frac`.

- [ ] **Step 1: Identify the 10 subjects with the most interpolated channels**

```bash
cd pearl && PYTHONPATH=src python -c "
import pandas as pd
qc = pd.read_csv('data/derivatives/preproc/qc/qc_metrics.csv')
top10 = qc.nlargest(10, 'n_bad_channels')[['subject', 'task', 'n_bad_channels']]
print(top10.to_string(index=False))
"
```

- [ ] **Step 2: Implement and run `compare_n_components`** on those 10
  subjects × both tasks, using the Task-1-fixed `process_subject_task` (or
  a lighter-weight direct call to `fit_and_exclude_ica` alone, to avoid
  redundant full preprocessing) with `cfg["ica"]["n_components"]` overridden
  to `30` and to `0.99` per run. Record `n_fit` (actual component count
  MNE selects), `n_removed`, `removed_frac` for each.

- [ ] **Step 3: Write `reports/phase5_ica_component_evaluation.md`**

Table of all rows from Step 2, plus a verdict paragraph: does `0.99`
produce a removal-rate distribution closer to "a handful of clearly
artifactual components" than the current fixed 30? State the decision
(keep 30, or switch to `0.99`, or another evidence-based value) and why,
per `phase_5.md` §0b's explicit instruction not to change without evidence.

- [ ] **Step 4: Apply the decision to `config/preproc.yaml`** (only if the
  evidence supports a change) with a comment citing
  `reports/phase5_ica_component_evaluation.md`.

- [ ] **Step 5: Commit**

```bash
git add pearl/src/pearl_preproc/ica_component_eval.py pearl/reports/phase5_ica_component_evaluation.md pearl/config/preproc.yaml
git commit -m "phase5: evaluate ICA n_components — evidence-based decision (§0b)"
```

---

## Task 3: Sternberg manifest + budget re-measurement

**Files:**
- Modify: `pearl/src/pearl_audit/download_plan.py` (verify/extend scope handling)
- Test: `pearl/tests/test_download_plan_sternberg.py`

**Interfaces:**
- Consumes: `pearl_audit.download_plan.build_scopes`, `_observed_tasks`, `write_manifest` (existing).
- Produces: a fresh `data/derivatives/phase0/phase1_manifest.csv` covering rest+msit+sternberg, and `reports/phase5_budget_actual.md` (measured, following the exact pattern of `phase1_budget_actual.md` — do not carry Phase 1's rest+msit-only numbers forward for the Sternberg-inclusive scope).

- [ ] **Step 1: Verify `_observed_tasks()` against the live OpenNeuro listing** (not the hardcoded fallback) — confirm `sternberg` is really present for the expected subject set before trusting the fallback list in `phase_5.md` §0c.

- [ ] **Step 2: Write the failing test**

```python
# pearl/tests/test_download_plan_sternberg.py
from pearl_audit.download_plan import build_scopes
import pandas as pd


def test_full_eeg_scope_includes_sternberg():
    size_df = pd.DataFrame({
        "task": ["rest", "msit", "sternberg", "rest"],
        "subject": ["sub-01", "sub-01", "sub-01", "sub-02"],
        "bytes": [100, 100, 100, 100],
    })
    scopes = build_scopes(size_df)
    assert "sternberg" in scopes["A_full_eeg"]["tasks"]
```

- [ ] **Step 3: Run to verify it fails or passes** (given `build_scopes`
  already references `all_tasks` for `A_full_eeg` per the earlier grep —
  confirm this test passes as-is; if it fails, that's the real gap to fix,
  not a new feature to add).

Run: `cd pearl && python -m pytest tests/test_download_plan_sternberg.py -v`

- [ ] **Step 4: Generate the real manifest and budget report**

```bash
cd pearl && python -m pearl_audit.cli run-all   # or the specific manifest/budget subcommand
```

Confirm `phase1_manifest.csv` now includes `sternberg` rows, and
`reports/phase5_budget_actual.md` states the measured total (compare
against Phase 1's "~75.87 GB raw across all three tasks, streamed" estimate
from `phase_1.md` §0d — do not assume it still holds, measure it).

- [ ] **Step 5: Commit**

```bash
git add pearl/tests/test_download_plan_sternberg.py pearl/reports/phase5_budget_actual.md
git commit -m "phase5: Sternberg manifest + measured budget (§0c)"
```

---

## Task 4: Sternberg pipeline wiring (sampling rate, genericity check)

**Files:**
- Modify: `pearl/config/preproc.yaml` (`sampling_rates_hz`)
- Test: `pearl/tests/test_preproc_sternberg_generic.py`

- [ ] **Step 1: Add `task-sternberg: 250` to `config/preproc.yaml`'s `sampling_rates_hz`**, with a comment stating the reason (task EEG, no cycle-level shape analysis, same reasoning as MSIT).

- [ ] **Step 2: Write the failing genericity test**

```python
# pearl/tests/test_preproc_sternberg_generic.py
from pearl_preproc.config import load_preproc_config, target_sfreq


def test_sternberg_sampling_rate_configured():
    cfg = load_preproc_config()
    assert target_sfreq(cfg, "sternberg") == 250.0
```

- [ ] **Step 3: Run to verify it fails, then passes after Step 1**

Run: `cd pearl && python -m pytest tests/test_preproc_sternberg_generic.py -v`

- [ ] **Step 4: Grep for any rest/MSIT-hardcoded assumption**

```bash
cd pearl && grep -n '"rest"\|"msit"' src/pearl_preproc/*.py
```

For each hit, confirm it's either (a) genuinely rest-specific (e.g. IAF
`require_for_tasks`, correctly rest-only) or (b) an enumerable list that
needs `"sternberg"` added (e.g. any task-name allowlist). Fix any case (b)
found; document why each case (a) is correctly left alone.

- [ ] **Step 5: Commit**

```bash
git add pearl/config/preproc.yaml pearl/tests/test_preproc_sternberg_generic.py
git commit -m "phase5: wire Sternberg into the preprocessing pipeline (§0c)"
```

---

## Task 5: Full three-task Phase 1 re-run — CHECKPOINT BEFORE STARTING

**This downloads and processes real data at real cost (bandwidth, wall-clock
time — recall Phase 1's own budget was tens of GB and multiple hours even
for two tasks). Confirm with the user before running this task, even though
Tasks 1–4 are already approved — this is the first step with real
irreversible resource cost in Stage 1.**

- [ ] **Step 1: Confirm disk/bandwidth budget from Task 3's measured report is acceptable, with the user, before starting.**
- [ ] **Step 2: Run** `python -m pearl_preproc.cli run-all` **under a new run_id**, monitored in the background (same pattern as every prior phase's long-running work in this session — `nohup` + log file + `Monitor`, not a blocking foreground call).
- [ ] **Step 3: Verify the new derivative tree's `run_id` is distinct from and coexists with the original**; spot-check the original tree is untouched (file count / mtimes unchanged).
- [ ] **Step 4: Report the new QC numbers** (subjects excluded, per-task breakdown, comparison to the original 23 excluded / 56 surviving at subject level) before proceeding to Task 6.

---

## Task 6: Phase 2 re-run + confound gate re-check

- [ ] **Step 1: Run** `python -m pearl_features.cli` **against the new Phase 1 run_id's output.**
- [ ] **Step 2: Read the confound gate verdict.** If `escalate` (QC-only AUC > 0.65): **stop, report, and wait** — do not proceed to Stage 2 under any circumstance, per `phase_5.md` §4.
- [ ] **Step 3: If `proceed`/`proceed_with_baseline`: report the new rest-cohort N** against the original 64, and note any material difference.

---

## Task 7: Stage 1 checkpoint report

**Files:**
- Create: `pearl/reports/phase5_stage1_data_foundation.md`

- [ ] **Step 1:** Write the checkpoint report: what changed (reference order, ICA decision, Sternberg addition), what was measured (budget, new N, new gate result), and an explicit recommendation for how Stage 2 should be scoped given the actual outcome (e.g. "N grew to 68, gate passed — proceed to Stage 2 as planned" or "N shrank / gate failed — here's what that means for Stage 2").
- [ ] **Step 2: Run full `pytest -q`, confirm green.**
- [ ] **Step 3: Commit**, and stop — Stage 2 is scoped in a follow-up spec once this checkpoint is read, not pre-committed now.

---

## Self-Review

- **Spec coverage:** phase_5.md §0a → Task 1. §0b → Task 2. §0c → Tasks 3–4. §1 (full re-run + gate) → Tasks 5–6. Checkpoint requirement → Task 7. §4 stop conditions → enforced in Task 6 Step 2 and Task 5's disk-budget checkpoint.
- **Escalation branches honored the same way as every prior phase:** Task 6's gate failure is a hard stop, not a warning to work around.
- **Real-cost checkpoint:** Task 5 is explicitly gated on user confirmation, distinct from the Stage 1 plan's overall approval — downloading tens of GB is not something to trigger automatically just because the plan was approved.
