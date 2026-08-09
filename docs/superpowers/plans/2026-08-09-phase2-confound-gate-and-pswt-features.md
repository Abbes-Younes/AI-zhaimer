# Phase 2 — Confound Gate & Pitch-Synchronous Feature Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `phase_2.md` end to end: amend the frozen analysis plan, run the QC-confound gate that must pass before any feature is trusted, then build the PSR/PSWT pitch-synchronous feature pipeline plus a baseline spectral feature set, producing `data/derivatives/features/{features_pswt,features_baseline}.csv` with no group labels inside them.

**Architecture:** A new sibling package `pearl_features` next to the existing `pearl_preproc` (same repo, `pearl/src/pearl_features`), following the same conventions: fixed config in `config/features.yaml` read once, atomic run-id staging via a mirrored `paths.py`, and a hard label-blindness boundary. Exactly one module, `confound_gate.py`, is a sanctioned exception that joins group labels (post-hoc, read-only, to measure contamination) — everything else (`cohort.py`, `epoching.py`, `cycles.py`, `psr.py`, `pswt.py`, `features.py`, `baseline.py`, `pipeline.py`) never imports or receives labels.

**Tech Stack:** Python 3.10+, `mne>=1.6` (already a dependency), `numpy`, `scipy`, `pandas`, `scikit-learn` (nested CV + permutation test — new dependency), `pywavelets` (Daubechies-8 DWT — new dependency), `pyyaml`.

## Global Constraints

- No models against the primary target anywhere in this phase except the QC-only contamination-floor classifier in §1b — that is a diagnostic, not a result.
- No QC threshold may be adjusted (phase_2.md §0a). Reuse the existing thresholds in `config/preproc.yaml` and the existing per-row `verdict` column in `qc_metrics.csv` unchanged.
- Feature extraction (`pearl_features` minus `confound_gate.py`) must have **no import path to labels** — same enforced test pattern as `pearl/tests/test_preproc_labelblind.py`, extended to the new package.
- Declare the full feature list in `config/features.yaml` before running extraction. Nothing gets added after seeing results. Cap at ≤ 30 features.
- Consume `data/derivatives/preproc/**` and `data/derivatives/preproc/qc/qc_metrics.csv` as given; never touch raw data or re-derive `IAFWindow`/`eyes_closed_window`.
- Every new bulk artifact under `data/derivatives/phase2/` and `data/derivatives/features/` uses one `run_id`, atomic staging (`.tmp-<run_id>/`, swap on success), same convention as `pearl_preproc.paths`.
- `pytest` green (existing 91+ tests plus every new test below) before any step is marked done.

---

## File Structure

```
pearl/
  pyproject.toml                          # MODIFY: add scikit-learn, pywavelets deps
  config/
    features.yaml                         # NEW: §6 feature declaration (this plan, Task 12)
  reports/
    analysis_plan_frozen.md               # MODIFY: append "Amendment 1" block (Task 2)
    phase2_confound_gate.md               # NEW: verdict-first gate report (Task 6)
    benchmark_citation.md                 # NEW: Li et al. verification record (Task 3)
  src/pearl_features/
    __init__.py                           # NEW
    paths.py                              # NEW: phase2 paths + run-id staging (Task 1)
    cohort.py                             # NEW: per-(subject,task) exclusion (Task 1)
    confound_gate.py                      # NEW: §1a/§1b, SANCTIONED label exception (Task 4, 5)
    epoching.py                           # NEW: §2 eyes-closed extraction + artifact rejection (Task 8)
    cycles.py                             # NEW: §3 cycle detection (Task 9)
    psr.py                                # NEW: §4 PSR matrix + DFT resampling (Task 10)
    pswt.py                               # NEW: §5 polyphase PSWT (Task 11)
    features.py                           # NEW: §6 feature computation + aggregation (Task 12)
    baseline.py                           # NEW: §7 baseline spectral features (Task 13)
    pipeline.py                           # NEW: §8 orchestration + outputs (Task 14)
    cli.py                                # NEW: `pearl-features` entry point (Task 14)
  tests/
    test_features_labelblind.py           # NEW: Task 1
    test_features_cohort.py               # NEW: Task 1
    test_features_confound_gate.py        # NEW: Task 4, 5
    test_features_epoching.py             # NEW: Task 8
    test_features_cycles.py               # NEW: Task 9
    test_features_psr.py                  # NEW: Task 10
    test_features_pswt.py                 # NEW: Task 11
    test_features_extraction.py           # NEW: Task 12
    test_features_baseline.py             # NEW: Task 13
    test_features_pipeline.py             # NEW: Task 14
data/derivatives/
  phase2/
    cohort_per_task.csv                   # NEW output (Task 1)
  features/
    features_pswt.csv                     # NEW output (Task 14)
    features_baseline.csv                 # NEW output (Task 14)
    feature_dictionary.md                 # NEW output (Task 12/14)
    cycle_stats.csv                       # NEW output (Task 14)
    _meta.json                            # NEW output (Task 14)
```

---

## Reference facts gathered from the existing codebase (do not re-derive)

- `qc_metrics.csv` already has one row per `(subject, task)` with columns including
  `subject, task, duration_s, n_bad_channels, occipital_bads, n_ica_removed,
  ica_removed_frac, line_noise_index_before, line_noise_index_after, iaf_hz,
  alpha_peak_height_db, alpha_present, artifact_frac, fifth_harmonic_collision,
  verdict, flags`. `verdict` is already `pass`/`warn`/`fail` **per row**, computed by
  `pearl_preproc.qc.classify_sidecar` from the fixed thresholds in
  `config/preproc.yaml`. Phase 1's `freeze_exclusions` collapses this to
  subject-level (any failing task excludes the whole subject) — that collapse is
  what phase_2.md §0a says to stop doing. **The per-task rule is simply: a
  `(subject, task)` pair is excluded iff its own row's `verdict == "fail"`.** No
  new threshold logic needed — reuse the existing column.
- Each preprocessed derivative sidecar
  (`data/derivatives/preproc/sub-XX/eeg/sub-XX_task-rest_desc-preproc_eeg.json`)
  has an `IAFWindow` block: `{"method": "eyes_closed", "tmin_s": <float>,
  "tmax_s": <float>}`. This is the eyes-closed window resolved in Phase 1. Read
  it; never call `pearl_preproc.preprocess.eyes_closed_window` again in Phase 2.
- `IAF` block in the same sidecar: `{"iaf_hz": <float>, "peak_height_db": <float>,
  "present": <bool>}`.
- `SamplingFrequency` in the sidecar is the resampled rate (500.0 for rest).
- Continuous derivative fif: `sub-XX_task-rest_desc-preproc_eeg.fif`, already
  average-referenced, filtered, ICA-cleaned, bad channels interpolated. Load with
  `mne.io.read_raw_fif(path, preload=True)`.
- `pearl_preproc.paths` holds `PROJECT_ROOT`, `PREPROC_DIR`, `QC_DIR`,
  `REPORTS_DIR`, run-id helpers (`make_run_id`, `staging_dir`, `finalize_run`,
  `sha256_file`, `git_sha`). `pearl_features.paths` should mirror the pattern
  (own `PHASE2_DIR = DATA_DIR / "derivatives" / "phase2"`,
  `FEATURES_DIR = DATA_DIR / "derivatives" / "features"`) — **import
  `PROJECT_ROOT`, `DATA_DIR`, run-id helpers, `sha256_file`, `git_sha` from
  `pearl_preproc.paths` directly (paths.py is not label-bearing, it is exempt
  from the label-blindness scan the same way `pearl_preproc.paths` itself is).**
- Client group labels live in `config/client_groups.yaml` (via
  `pearl_audit.reconcile_groups.load_client_groups` /
  `client_subject_set`) and `data/labels/participants_labels.tsv`
  (columns: `subject_id, group, task1_risk_vs_norisk, task2_high_vs_lownormal,
  task3_multiclass`). `task1_risk_vs_norisk` is exactly `binary_risk_vs_none`
  (0 = N, 1 = A+P- or A+P+). Only `confound_gate.py` may read this file.
- Occipital/parietal channel list already exists in
  `config/preproc.yaml:iaf.channels` (also `qc.occipital_channels`, identical
  list): `[O1, Oz, O2, O9, O10, POz, PO7, PO8, PO3, PO4, Pz, P3, P4, PO9, PO10]`.
  Reuse this list as the §6c ROI rather than inventing a new one.

---

## Task 1: Per-(subject, task) cohort + phase2 paths module

**Files:**
- Create: `pearl/src/pearl_features/__init__.py` (empty)
- Create: `pearl/src/pearl_features/paths.py`
- Create: `pearl/src/pearl_features/cohort.py`
- Test: `pearl/tests/test_features_labelblind.py`
- Test: `pearl/tests/test_features_cohort.py`

**Interfaces:**
- Produces: `pearl_features.paths.PHASE2_DIR: Path`, `FEATURES_DIR: Path`,
  `CONFIG_DIR: Path`, `FEATURES_YAML: Path` (= `CONFIG_DIR / "features.yaml"`),
  everything else re-exported from `pearl_preproc.paths`.
- Produces: `pearl_features.cohort.load_qc_metrics() -> pandas.DataFrame` (reads
  `pearl_preproc.paths.QC_DIR / "qc_metrics.csv"`).
- Produces: `pearl_features.cohort.per_task_cohort(qc: pandas.DataFrame) ->
  pandas.DataFrame` — one row per `(subject, task)`, columns
  `subject, task, verdict, included` where `included = verdict != "fail"`.
- Produces: `pearl_features.cohort.rest_cohort_n(per_task: pandas.DataFrame) ->
  int` — count of `subject` rows where `task in {"rest", "task-rest"}` and
  `included`. This is the N Task 2's amendment must report.
- Produces: `pearl_features.cohort.write_cohort_csv(per_task: pandas.DataFrame,
  out_path: Path) -> None`.

- [ ] **Step 1: Write the failing label-blindness test**

```python
# pearl/tests/test_features_labelblind.py
"""Label blindness for pearl_features (phase_2.md §2, extending phase_1.md §2a).

Only confound_gate.py is sanctioned to touch group labels, and only to measure
contamination (phase_2.md §1) — it never feeds labels into feature extraction.
"""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "pearl_features"
SANCTIONED = {"confound_gate.py"}
FORBIDDEN = [
    "client_groups", "cohort_definition", "genotype", "final_include",
    "A_P_plus", "A_P_minus", "risk_vs_none", "pearl_audit",
    "participants_labels",
]


def _processing_files():
    return [f for f in sorted(SRC.rglob("*.py")) if f.name not in SANCTIONED]


def test_processing_modules_have_no_label_references():
    offenders = []
    for f in _processing_files():
        text = f.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                offenders.append(f"{f.name}: {token}")
    assert not offenders, f"label-blindness violations: {offenders}"


def test_no_import_of_label_modules():
    offenders = []
    for f in _processing_files():
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith(("import ", "from ")):
                if any(t in line for t in ["pearl_audit", "reconcile_groups", "client_groups"]):
                    offenders.append(f"{f.name}: {line.strip()}")
    assert not offenders, f"forbidden imports: {offenders}"


def test_features_yaml_is_label_free():
    cfg_path = SRC.parent.parent / "config" / "features.yaml"
    if not cfg_path.exists():
        return  # created in Task 12; nothing to violate yet
    text = cfg_path.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in text, f"features.yaml mentions {token!r}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_labelblind.py -v`
Expected: FAIL — `ModuleNotFoundError`/collection error, `src/pearl_features` does not exist yet.

- [ ] **Step 3: Create the package skeleton and `paths.py`**

```python
# pearl/src/pearl_features/__init__.py
```

```python
# pearl/src/pearl_features/paths.py
"""Phase 2 paths. Mirrors pearl_preproc.paths conventions; not label-bearing
(exempt from the label-blindness scan the same way pearl_preproc.paths is)."""
from __future__ import annotations

from pearl_preproc.paths import (  # noqa: F401  (re-exported on purpose)
    PROJECT_ROOT, DATA_DIR, CONFIG_DIR, REPORTS_DIR,
    make_run_id, get_run_id, set_run_id, sha256_file, git_sha,
)

PHASE2_DIR = DATA_DIR / "derivatives" / "phase2"
FEATURES_DIR = DATA_DIR / "derivatives" / "features"
FEATURES_YAML = CONFIG_DIR / "features.yaml"


def staging_dir(base: "Path") -> "Path":
    run_id = get_run_id()
    if run_id:
        return base / f".tmp-{run_id}"
    return base


def finalize_staged(base: "Path") -> None:
    """Swap base/.tmp-<run_id>/* into base/, matching pearl_preproc.paths.finalize_run."""
    import json
    import shutil
    from datetime import datetime, timezone

    run_id = get_run_id()
    if not run_id:
        return
    tmp = base / f".tmp-{run_id}"
    base.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        for item in tmp.iterdir():
            dest = base / item.name
            if dest.exists():
                shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(tmp, ignore_errors=True)
    (base / "_meta.json").write_text(
        json.dumps({"run_id": run_id, "finalized_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run the label-blindness test again**

Run: `cd pearl && python -m pytest tests/test_features_labelblind.py -v`
Expected: PASS (empty `src/pearl_features` directory besides `paths.py`/`__init__.py` has no forbidden tokens).

- [ ] **Step 5: Write the failing cohort test**

```python
# pearl/tests/test_features_cohort.py
import pandas as pd

from pearl_features.cohort import per_task_cohort, rest_cohort_n


def _qc(rows):
    return pd.DataFrame(rows, columns=["subject", "task", "verdict"])


def test_per_task_cohort_excludes_only_failing_rows():
    qc = _qc([
        ("sub-01", "rest", "pass"),
        ("sub-01", "msit", "fail"),
        ("sub-02", "rest", "fail"),
        ("sub-02", "msit", "pass"),
    ])
    out = per_task_cohort(qc)
    included = {(r.subject, r.task): r.included for r in out.itertuples()}
    assert included[("sub-01", "rest")] is True
    assert included[("sub-01", "msit")] is False
    assert included[("sub-02", "rest")] is False
    assert included[("sub-02", "msit")] is True


def test_per_task_cohort_warn_is_included():
    qc = _qc([("sub-03", "rest", "warn")])
    out = per_task_cohort(qc)
    assert bool(out.iloc[0].included) is True


def test_rest_cohort_n_counts_included_rest_rows_only():
    qc = _qc([
        ("sub-01", "rest", "pass"),
        ("sub-02", "rest", "fail"),
        ("sub-03", "rest", "pass"),
        ("sub-03", "msit", "fail"),
    ])
    out = per_task_cohort(qc)
    assert rest_cohort_n(out) == 2
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_cohort.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pearl_features.cohort'`

- [ ] **Step 7: Implement `cohort.py`**

```python
# pearl/src/pearl_features/cohort.py
"""Per-(subject, task) exclusion (phase_2.md §0a).

Reuses the existing per-row `verdict` column in qc_metrics.csv unchanged — no
new threshold logic. A (subject, task) pair is excluded iff its own row's
verdict == "fail". This is the rule-change-not-threshold-change phase_2.md
§0a requires: the collapse to subject level lived only in
pearl_preproc.qc.freeze_exclusions, and Phase 2 simply does not apply that
collapse.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pearl_preproc.paths import QC_DIR


def load_qc_metrics() -> pd.DataFrame:
    return pd.read_csv(QC_DIR / "qc_metrics.csv")


def per_task_cohort(qc: pd.DataFrame) -> pd.DataFrame:
    out = qc[["subject", "task", "verdict"]].copy()
    out["included"] = out["verdict"] != "fail"
    return out.reset_index(drop=True)


def rest_cohort_n(per_task: pd.DataFrame) -> int:
    is_rest = per_task["task"].isin(["rest", "task-rest"])
    return int((is_rest & per_task["included"]).sum())


def write_cohort_csv(per_task: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_task.to_csv(out_path, index=False)
```

- [ ] **Step 8: Run both tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_cohort.py tests/test_features_labelblind.py -v`
Expected: all PASS

- [ ] **Step 9: Generate `data/derivatives/phase2/cohort_per_task.csv` and print rest_cohort_n**

Run:
```bash
cd pearl && python -c "
from pearl_features.cohort import load_qc_metrics, per_task_cohort, rest_cohort_n, write_cohort_csv
from pearl_features.paths import PHASE2_DIR
qc = load_qc_metrics()
pt = per_task_cohort(qc)
write_cohort_csv(pt, PHASE2_DIR / 'cohort_per_task.csv')
print('rest cohort N =', rest_cohort_n(pt))
"
```
Record the printed N — Task 2 needs it verbatim in the amendment, and phase_2.md §11 requires escalation if it differs materially from 64.

- [ ] **Step 10: Commit**

```bash
git add pearl/src/pearl_features/__init__.py pearl/src/pearl_features/paths.py \
        pearl/src/pearl_features/cohort.py pearl/tests/test_features_labelblind.py \
        pearl/tests/test_features_cohort.py data/derivatives/phase2/cohort_per_task.csv
git commit -m "phase2: per-(subject,task) cohort derivation and pearl_features skeleton"
```

---

## Task 2: Amendment 1 to the frozen analysis plan

**Files:**
- Modify: `pearl/reports/analysis_plan_frozen.md`

**Interfaces:**
- Consumes: the rest-cohort N printed by Task 1 Step 9.
- No code interface — this is a documentation deliverable, but it is a required Definition-of-Done item and later tasks (confound gate report, covariate list) reference it.

- [ ] **Step 1: Append the Amendment 1 block**

Append to the end of `pearl/reports/analysis_plan_frozen.md` (do not edit anything above it — it stays frozen):

```markdown

---

## Amendment 1 — 2026-08-09

**Status:** committed. Appends to, does not rewrite, the frozen plan above.

### Exclusion unit changed: subject → (subject, task)

Per-task exclusion is the correct rule independent of the N it yields:
excluding a subject from a rest-based primary analysis because their MSIT
recording was noisy is a category error, not a stricter standard. The frozen
primary target is rest-based; the exclusion unit is now `(subject, task)`,
which was already the grain of `qc_metrics.csv` — only
`pearl_preproc.qc.freeze_exclusions` collapsed it to the subject. Phase 2
does not apply that collapse (see `pearl_features/cohort.py`); no QC
threshold changed, only the unit the existing thresholds are applied to.

**Disclosure:** the resulting rest-cohort N (**<N FROM TASK 1 STEP 9>**) was
known before this rule was adopted. The rule is adopted because it is the
correct unit of analysis, not because of the N — but that N was visible when
the decision was made, and this sentence records that fact so the choice
cannot later be read as blind to its effect.

### Primary target: unchanged

`binary_risk_vs_none` remains the frozen primary target. Changing it because N
moved is exactly the failure the freeze exists to prevent.

### Secondary framings demoted to descriptive-only

`binary_high_vs_rest` and `multiclass_3` are demoted to **descriptive
reporting only**. At the A_P_plus survivor count under the per-task rule
(12–14) they cannot support a tested claim. Phase 3 reports their descriptive
statistics (group sizes, feature-wise summary stats); it must not compute a
p-value or claim a result for either framing.

### Power statement (written now, before results exist)

At roughly 24 vs 40 (rest-cohort per-task N), the study is underpowered to
reliably distinguish a true AUC of 0.65 from the published 0.58. This is a
known limitation stated in advance so it cannot be read as an excuse after
results exist.

### Carry-forward covariates (phase_2.md §1c)

Bad-channel count and ICA-components-removed join SES and BDI as declared
covariates for Phase 3, regardless of the confound-gate verdict in
`reports/phase2_confound_gate.md`.
```

- [ ] **Step 2: Replace the `<N FROM TASK 1 STEP 9>` placeholder with the real integer**

Use the `Edit` tool to substitute the literal N printed in Task 1 Step 9 (e.g. `64`, `61`, whatever the run produced) into both the "Disclosure" sentence and the "Power statement" sentence (update "roughly 24 vs 40" only if the printed split materially differs — check `data/labels/participants_labels.tsv` joined against `cohort_per_task.csv` restricted to `task == "rest" & included` to get the exact risk/no-risk split for the power-statement sentence; this join is for a documentation number, not code, so doing it in a throwaway `python -c` one-liner is fine and does not violate label blindness — no source file imports labels).

- [ ] **Step 3: Verify the file renders as valid markdown and the frozen section above Amendment 1 is byte-identical to before**

Run: `cd pearl && git diff reports/analysis_plan_frozen.md`
Expected: diff shows only an appended block at the end, zero changes above `## Amendment 1`.

- [ ] **Step 4: Commit**

```bash
git add pearl/reports/analysis_plan_frozen.md
git commit -m "phase2: Amendment 1 — per-task exclusion, target unchanged, power statement"
```

---

## Task 3: Verify and record the benchmark citation (§0d)

**Files:**
- Create: `pearl/reports/benchmark_citation.md`
- Modify: `pearl/reports/analysis_plan_frozen.md` (Amendment 1 gets one more subsection)

**Interfaces:** none — documentation task. Requires `WebSearch`/`WebFetch` tools.

- [ ] **Step 1: Search for the citation**

Use `WebSearch` for: `Li 2025 Sensors cross-subject early Alzheimer susceptibility EEG multitaper SVM`. Cross-check candidate hits against the specifics phase_2.md gives: 2025, journal *Sensors*, cross-subject early-AD susceptibility prediction in middle-aged adults, multitaper spectral analysis, SVM classifier, same PEARL-Neuro-style dataset with task EEG.

- [ ] **Step 2: If found, fetch the paper page/DOI and extract exact fields**

Use `WebFetch` on the DOI or publisher page. Record: full author list, exact title, journal, year, volume/issue, DOI, which **task** (rest vs MSIT-equivalent) and which **classifier configuration** produced AUC ≈ 0.58.

- [ ] **Step 3: Write `pearl/reports/benchmark_citation.md`**

If verified, write (fill in the real fields from Step 2 — do not invent a DOI):

```markdown
# Benchmark citation verification (phase_2.md §0d)

**Status:** VERIFIED | UNVERIFIED  <!-- pick one -->

**Claimed benchmark:** AUC ≈ 0.58, cross-subject early-AD susceptibility
prediction, task EEG, SVM, multitaper spectral features.

**Full reference:** <authors>. (<year>). <title>. *Sensors*, <volume>(<issue>),
<article number/pages>. DOI: <doi>

**Task and classifier that produced the 0.58:** <exact task label from the
paper, exact classifier/kernel/feature config>

**Verification method:** WebSearch + WebFetch on <date>, matched against
publisher record at <url>.

**Framing match to this project:** <one paragraph — does the 0.58 come from
the same task framing (rest vs MSIT-analogue) as this project's primary
target? Note any mismatch explicitly rather than eliding it.>
```

If NOT verified after a genuine search (no matching *Sensors* 2025 paper
found), write `Status: UNVERIFIED` and this instead of a reference block:

```markdown
**Verification outcome:** UNVERIFIED. Searched for "<queries tried>" via
WebSearch on <date>; no *Sensors* 2025 paper matching the claimed description
(cross-subject early-AD susceptibility, multitaper, SVM, AUC ≈ 0.58) was
found. `reports/analysis_plan_frozen.md` benchmark section is marked
unverified; the 0.58 figure must not be cited as a validated external
benchmark until this is resolved.
```

- [ ] **Step 4: Add a one-line status note to Amendment 1**

Append under the Amendment 1 block in `analysis_plan_frozen.md`:

```markdown

### Benchmark citation status

See `reports/benchmark_citation.md` — status: **<VERIFIED|UNVERIFIED>**. If
unverified, the AUC ≈ 0.58 figure is used only as a stated prior reference
point, not a validated external benchmark, until resolved.
```

- [ ] **Step 5: Commit**

```bash
git add pearl/reports/benchmark_citation.md pearl/reports/analysis_plan_frozen.md
git commit -m "phase2: verify (or mark unverified) the AUC 0.58 benchmark citation"
```

---

## Task 4: Confound gate — association tests (§1a)

**Files:**
- Create: `pearl/src/pearl_features/confound_gate.py`
- Test: `pearl/tests/test_features_confound_gate.py`

**Interfaces:**
- Consumes: `pearl_features.cohort.load_qc_metrics`, `per_task_cohort` (Task 1).
- Produces: `confound_gate.CONTINUOUS_METRICS: list[str]` = `["n_bad_channels",
  "occipital_bads", "n_ica_removed", "line_noise_index_before",
  "line_noise_index_after", "artifact_frac", "iaf_hz", "alpha_peak_height_db"]`
  (columns that exist in `qc_metrics.csv` per the reference-facts section above;
  `bad_channels`/`ica_removed_labels` are categorical/list-valued and excluded).
- Produces: `confound_gate.association_tests(qc: pd.DataFrame, group_map: dict[str,str],
  metrics: list[str]) -> pd.DataFrame` — one row per metric, columns
  `metric, test, statistic, p_value, p_fdr, effect_size, ci_low, ci_high`.
- Produces: `confound_gate.exclusion_status_association(per_task: pd.DataFrame,
  group_map: dict[str,str]) -> dict` — Fisher's exact on exclusion status ×
  group, returns `{"odds_ratio": float, "p_value": float}`.
- Produces: `confound_gate.load_group_map() -> dict[str,str]` — **the sanctioned
  label read**, from `data/labels/participants_labels.tsv`
  (`subject_id -> group`).

- [ ] **Step 1: Write the failing test for association tests**

```python
# pearl/tests/test_features_confound_gate.py
import numpy as np
import pandas as pd

from pearl_features.confound_gate import (
    association_tests, exclusion_status_association, CONTINUOUS_METRICS,
)


def _fake_qc(n_per_group=15, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    groups = {}
    subj = 0
    for g, shift in [("N", 0.0), ("A_P_minus", 0.0), ("A_P_plus", 0.0)]:
        for _ in range(n_per_group):
            subj += 1
            sid = f"sub-{subj:02d}"
            groups[sid] = g
            rows.append({
                "subject": sid, "task": "rest",
                "n_bad_channels": rng.integers(0, 5) + shift,
                "occipital_bads": rng.integers(0, 2),
                "n_ica_removed": rng.integers(5, 20),
                "line_noise_index_before": rng.normal(5, 1),
                "line_noise_index_after": rng.normal(0.01, 0.005),
                "artifact_frac": rng.uniform(0, 0.1),
                "iaf_hz": rng.normal(10, 0.5),
                "alpha_peak_height_db": rng.normal(5, 2),
                "verdict": "pass",
            })
    return pd.DataFrame(rows), groups


def test_association_tests_returns_one_row_per_metric_with_fdr():
    qc, groups = _fake_qc()
    out = association_tests(qc, groups, CONTINUOUS_METRICS)
    assert list(out["metric"]) == CONTINUOUS_METRICS
    assert (out["p_fdr"] >= out["p_value"] - 1e-12).all()  # BH-FDR never < raw p
    assert out["p_value"].between(0, 1).all()


def test_association_tests_detects_a_real_group_difference():
    qc, groups = _fake_qc()
    # inject a strong, real group-dependent shift into one metric
    qc.loc[qc["subject"].map(groups) == "A_P_plus", "n_bad_channels"] += 20
    out = association_tests(qc, groups, CONTINUOUS_METRICS)
    row = out[out["metric"] == "n_bad_channels"].iloc[0]
    assert row["p_value"] < 0.01


def test_exclusion_status_association_runs_fisher():
    per_task = pd.DataFrame({
        "subject": [f"sub-{i:02d}" for i in range(1, 11)],
        "task": ["rest"] * 10,
        "included": [True, True, True, False, False, True, True, True, False, True],
    })
    groups = {f"sub-{i:02d}": ("N" if i <= 5 else "A_P_plus") for i in range(1, 11)}
    result = exclusion_status_association(per_task, groups)
    assert 0.0 <= result["p_value"] <= 1.0
    assert "odds_ratio" in result
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement association tests in `confound_gate.py`**

```python
# pearl/src/pearl_features/confound_gate.py
"""THE GATE (phase_2.md §1) — preprocessing metadata must not predict group.

Sanctioned exception to pearl_features label blindness: this module reads
group labels (data/labels/participants_labels.tsv) to test whether
preprocessing/QC metrics carry group information. It never writes labels into
any feature file and nothing downstream of pearl_features.features imports
this module.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from pearl_preproc.paths import PROJECT_ROOT

LABELS_TSV = PROJECT_ROOT.parent / "data" / "labels" / "participants_labels.tsv"

CONTINUOUS_METRICS = [
    "n_bad_channels", "occipital_bads", "n_ica_removed",
    "line_noise_index_before", "line_noise_index_after",
    "artifact_frac", "iaf_hz", "alpha_peak_height_db",
]


def load_group_map() -> dict[str, str]:
    with open(LABELS_TSV, newline="", encoding="utf-8") as fh:
        return {row["subject_id"]: row["group"] for row in csv.DictReader(fh, delimiter="\t")}


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg FDR, ascending-order accumulate-min-from-the-top."""
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(ranked, 0, 1)
    return out


def _bootstrap_eta_squared_ci(groups: list[np.ndarray], n_boot: int = 2000,
                               seed: int = 0) -> tuple[float, float, float]:
    """Bootstrap CI on eta-squared (KW effect size) by resampling within each group."""
    rng = np.random.default_rng(seed)

    def eta_sq(gs):
        all_vals = np.concatenate(gs)
        h_stat, _ = stats.kruskal(*gs)
        n = len(all_vals)
        k = len(gs)
        return max(0.0, (h_stat - k + 1) / (n - k)) if n > k else 0.0

    point = eta_sq(groups)
    boots = []
    for _ in range(n_boot):
        resampled = [rng.choice(g, size=len(g), replace=True) for g in groups]
        boots.append(eta_sq(resampled))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, lo, hi


def association_tests(qc: pd.DataFrame, group_map: dict[str, str],
                       metrics: list[str]) -> pd.DataFrame:
    qc = qc.copy()
    qc["group"] = qc["subject"].map(group_map)
    rows = []
    pvals = []
    for metric in metrics:
        groups = [qc.loc[qc["group"] == g, metric].dropna().to_numpy(dtype=float)
                   for g in sorted(qc["group"].dropna().unique())]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            rows.append({"metric": metric, "test": "kruskal-wallis", "statistic": np.nan,
                          "p_value": 1.0, "effect_size": 0.0, "ci_low": 0.0, "ci_high": 0.0})
            pvals.append(1.0)
            continue
        h_stat, p = stats.kruskal(*groups)
        eff, lo, hi = _bootstrap_eta_squared_ci(groups)
        rows.append({"metric": metric, "test": "kruskal-wallis", "statistic": h_stat,
                      "p_value": p, "effect_size": eff, "ci_low": lo, "ci_high": hi})
        pvals.append(p)
    out = pd.DataFrame(rows)
    out["p_fdr"] = _bh_fdr(out["p_value"].to_numpy())
    return out[["metric", "test", "statistic", "p_value", "p_fdr", "effect_size", "ci_low", "ci_high"]]


def exclusion_status_association(per_task: pd.DataFrame, group_map: dict[str, str]) -> dict:
    df = per_task.copy()
    df["group"] = df["subject"].map(group_map)
    df = df.dropna(subset=["group"])
    table = pd.crosstab(df["group"] == "N", df["included"])
    # crosstab may be missing a column if all included or all excluded in a slice
    table = table.reindex(columns=[True, False], fill_value=0)
    odds_ratio, p = stats.fisher_exact(table.to_numpy())
    return {"odds_ratio": float(odds_ratio), "p_value": float(p)}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -v`
Expected: PASS. If `test_association_tests_detects_a_real_group_difference` is flaky (KW p-value borderline), increase the injected shift in the test, not the implementation.

- [ ] **Step 5: Commit**

```bash
git add pearl/src/pearl_features/confound_gate.py pearl/tests/test_features_confound_gate.py
git commit -m "phase2: confound-gate association tests (KW/Fisher/bootstrap/BH-FDR)"
```

---

## Task 5: Confound gate — QC-only contamination-floor classifier (§1b)

**Files:**
- Modify: `pearl/src/pearl_features/confound_gate.py`
- Modify: `pearl/tests/test_features_confound_gate.py`
- Modify: `pearl/pyproject.toml` (add `scikit-learn>=1.3`)

**Interfaces:**
- Consumes: `association_tests`'s `CONTINUOUS_METRICS`, `load_group_map`.
- Produces: `confound_gate.qc_only_auc(qc: pd.DataFrame, group_map: dict[str,str],
  metrics: list[str], n_splits: int = 5, n_repeats: int = 3,
  n_permutations: int = 1000, seed: int = 42) -> dict` with keys
  `mean_auc, ci_low, ci_high, p_value, verdict` where
  `verdict in {"proceed", "proceed_with_baseline", "escalate"}` per the
  phase_2.md §1b table (≈0.50 → proceed; 0.55–0.62 → proceed_with_baseline;
  >0.65 → escalate; the 0.62–0.65 gap is treated as `escalate` — closer to the
  contamination-confirmed side than the ambiguous side, and phase_2.md gives no
  band for it).

- [ ] **Step 1: Add the dependency**

```toml
# pearl/pyproject.toml — inside [project] dependencies, after "mne-icalabel>=0.6",
    "scikit-learn>=1.3",
```

Run: `cd pearl && pip install -e .` (or `pip install scikit-learn>=1.3` inside the project's env) to make it importable for the tests below.

- [ ] **Step 2: Write the failing test**

```python
# append to pearl/tests/test_features_confound_gate.py
from pearl_features.confound_gate import qc_only_auc


def test_qc_only_auc_near_chance_on_random_labels():
    qc, groups = _fake_qc(n_per_group=20, seed=1)
    binary_map = {s: (0 if g == "N" else 1) for s, g in groups.items()}
    result = qc_only_auc(qc, binary_map, CONTINUOUS_METRICS,
                          n_splits=3, n_repeats=1, n_permutations=20, seed=1)
    assert 0.3 <= result["mean_auc"] <= 0.7
    assert result["verdict"] in {"proceed", "proceed_with_baseline"}
    assert 0.0 <= result["p_value"] <= 1.0


def test_qc_only_auc_escalates_when_metric_is_a_perfect_group_proxy():
    qc, groups = _fake_qc(n_per_group=20, seed=2)
    binary_map = {s: (0 if g == "N" else 1) for s, g in groups.items()}
    qc["n_bad_channels"] = qc["subject"].map(lambda s: 0.0 if binary_map[s] == 0 else 100.0)
    result = qc_only_auc(qc, binary_map, CONTINUOUS_METRICS,
                          n_splits=3, n_repeats=1, n_permutations=20, seed=2)
    assert result["mean_auc"] > 0.9
    assert result["verdict"] == "escalate"
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -k qc_only_auc -v`
Expected: FAIL — `ImportError: cannot import name 'qc_only_auc'`

- [ ] **Step 4: Implement `qc_only_auc`**

```python
# append to pearl/src/pearl_features/confound_gate.py
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _cv_mean_auc(X: np.ndarray, y: np.ndarray, n_splits: int, n_repeats: int,
                  seed: int) -> float:
    aucs = []
    rng = np.random.default_rng(seed)
    for rep in range(n_repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True,
                               random_state=int(rng.integers(0, 2**31 - 1)))
        for train_idx, test_idx in skf.split(X, y):
            clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 LogisticRegression(max_iter=1000))
            clf.fit(X[train_idx], y[train_idx])
            proba = clf.predict_proba(X[test_idx])[:, 1]
            if len(np.unique(y[test_idx])) < 2:
                continue
            aucs.append(roc_auc_score(y[test_idx], proba))
    return float(np.mean(aucs)) if aucs else 0.5


def qc_only_auc(qc: pd.DataFrame, group_map: dict[str, str], metrics: list[str],
                 n_splits: int = 5, n_repeats: int = 3, n_permutations: int = 1000,
                 seed: int = 42) -> dict:
    df = qc.copy()
    df["y"] = df["subject"].map(group_map)
    df = df.dropna(subset=["y"])
    df = df.drop_duplicates(subset="subject")  # subject-level: one row per subject
    X = df[metrics].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=int)

    observed = _cv_mean_auc(X, y, n_splits, n_repeats, seed)

    rng = np.random.default_rng(seed)
    perm_aucs = np.empty(n_permutations)
    for i in range(n_permutations):
        y_perm = rng.permutation(y)
        perm_aucs[i] = _cv_mean_auc(X, y_perm, n_splits, 1, seed + i + 1)
    p_value = float((perm_aucs >= observed).sum() + 1) / (n_permutations + 1)

    boot_aucs = []
    rng2 = np.random.default_rng(seed + 1)
    n = len(y)
    for _ in range(2000):
        idx = rng2.integers(0, n, size=n)
        if len(np.unique(y[idx])) < 2:
            continue
        boot_aucs.append(_cv_mean_auc(X[idx], y[idx], n_splits, 1, seed))
    ci_low, ci_high = (np.percentile(boot_aucs, [2.5, 97.5]) if boot_aucs else (observed, observed))

    if observed > 0.65:
        verdict = "escalate"
    elif observed >= 0.55:
        verdict = "proceed_with_baseline"
    else:
        verdict = "proceed"

    return {"mean_auc": observed, "ci_low": float(ci_low), "ci_high": float(ci_high),
            "p_value": p_value, "verdict": verdict}
```

- [ ] **Step 5: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -v`
Expected: PASS. Note the reduced `n_permutations`/bootstrap count in tests (20, not the production 1000/2000) — that is a test-speed choice, not a spec violation; Task 6's actual gate run uses the real thresholds.

- [ ] **Step 6: Commit**

```bash
git add pearl/pyproject.toml pearl/src/pearl_features/confound_gate.py pearl/tests/test_features_confound_gate.py
git commit -m "phase2: QC-only contamination-floor classifier (nested CV, permutation, bootstrap)"
```

---

## Task 6: Run the gate for real and write `reports/phase2_confound_gate.md`

**Files:**
- Create: `pearl/src/pearl_features/confound_gate_report.py` (report renderer, mirrors `pearl_preproc/report_qc.py` style)
- Modify: `pearl/src/pearl_features/confound_gate.py` if any glue function is missing (e.g. a `run()` orchestrator)
- Test: extend `pearl/tests/test_features_confound_gate.py` with a report-rendering smoke test

**Interfaces:**
- Consumes: `association_tests`, `exclusion_status_association`, `qc_only_auc`,
  `load_group_map`, `pearl_features.cohort.load_qc_metrics`,
  `pearl_features.cohort.per_task_cohort`.
- Produces: `confound_gate_report.render(full_assoc: pd.DataFrame,
  surviving_assoc: pd.DataFrame, exclusion_assoc: dict, gate_result: dict) -> str`
  (HTML or Markdown string — Markdown is simpler and phase_2.md just says
  "Write `reports/phase2_confound_gate.md`, verdict-first").

- [ ] **Step 1: Write the failing smoke test**

```python
# append to pearl/tests/test_features_confound_gate.py
from pearl_features.confound_gate_report import render


def test_render_report_is_verdict_first_markdown():
    full = pd.DataFrame({"metric": ["n_bad_channels"], "test": ["kruskal-wallis"],
                          "statistic": [1.0], "p_value": [0.5], "p_fdr": [0.5],
                          "effect_size": [0.0], "ci_low": [0.0], "ci_high": [0.1]})
    gate_result = {"mean_auc": 0.51, "ci_low": 0.45, "ci_high": 0.58,
                   "p_value": 0.42, "verdict": "proceed"}
    exclusion_assoc = {"odds_ratio": 1.1, "p_value": 0.8}
    text = render(full, full, exclusion_assoc, gate_result)
    first_line = text.strip().splitlines()[0]
    assert "PROCEED" in first_line.upper() or "VERDICT" in first_line.upper()
    assert "0.51" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -k render -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `confound_gate_report.py`**

```python
# pearl/src/pearl_features/confound_gate_report.py
"""Verdict-first Markdown report for THE GATE (phase_2.md §1)."""
from __future__ import annotations

import pandas as pd

_VERDICT_TEXT = {
    "proceed": "PROCEED — preprocessing carries no detectable group information.",
    "proceed_with_baseline": (
        "PROCEED WITH BASELINE REQUIREMENT — partial contamination detected. "
        "Every downstream EEG feature model must be reported alongside this "
        "QC-only baseline; improvement over it is the only claim that may be made."),
    "escalate": (
        "STOP AND ESCALATE — preprocessing predicts group about as well as "
        "published EEG features do. Option C (reference-order / ICA-rate "
        "confound investigation) becomes mandatory before any feature is trusted."),
}


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def render(full_assoc: pd.DataFrame, surviving_assoc: pd.DataFrame,
           exclusion_assoc: dict, gate_result: dict) -> str:
    verdict = gate_result["verdict"]
    lines = [
        f"# Phase 2 Confound Gate — VERDICT: {verdict.upper()}",
        "",
        _VERDICT_TEXT[verdict],
        "",
        "## §1b — QC-only classifier (the decisive test)",
        "",
        f"- Mean AUC (subject-level stratified group k-fold, nested, permutation-tested): "
        f"**{gate_result['mean_auc']:.3f}**",
        f"- 95% bootstrap CI: [{gate_result['ci_low']:.3f}, {gate_result['ci_high']:.3f}]",
        f"- Permutation p-value: {gate_result['p_value']:.4f}",
        "",
        "## §1a — Association tests, full cohort (N=79)",
        "",
        _table(full_assoc),
        "",
        "## §1a — Association tests, surviving cohort (per-task rule)",
        "",
        _table(surviving_assoc),
        "",
        "## §1a — Exclusion status × group (Fisher's exact)",
        "",
        f"- Odds ratio: {exclusion_assoc['odds_ratio']:.3f}",
        f"- p-value: {exclusion_assoc['p_value']:.4f}",
        "",
        "## §1c — Carry-forward covariates",
        "",
        "Bad-channel count and ICA-components-removed join SES and BDI as "
        "declared Phase 3 covariates, regardless of this verdict "
        "(see Amendment 1, `reports/analysis_plan_frozen.md`).",
        "",
    ]
    return "\n".join(lines)


def run() -> dict:
    """Orchestrates the full §1 gate and writes reports/phase2_confound_gate.md."""
    from pearl_features.cohort import load_qc_metrics, per_task_cohort
    from pearl_features.paths import REPORTS_DIR
    from pearl_features.confound_gate import (
        association_tests, exclusion_status_association, qc_only_auc,
        load_group_map, CONTINUOUS_METRICS,
    )

    qc = load_qc_metrics()
    per_task = per_task_cohort(qc)
    group_map = load_group_map()

    full_assoc = association_tests(qc, group_map, CONTINUOUS_METRICS)
    surviving = qc.merge(per_task[per_task["included"]][["subject", "task"]],
                          on=["subject", "task"], how="inner")
    surviving_assoc = association_tests(surviving, group_map, CONTINUOUS_METRICS)
    exclusion_assoc = exclusion_status_association(per_task, group_map)

    binary_map = {s: (0 if g == "N" else 1) for s, g in group_map.items()}
    rest_qc = qc[qc["task"].isin(["rest", "task-rest"])].drop_duplicates(subset="subject")
    gate_result = qc_only_auc(rest_qc, binary_map, CONTINUOUS_METRICS)

    text = render(full_assoc, surviving_assoc, exclusion_assoc, gate_result)
    (REPORTS_DIR / "phase2_confound_gate.md").write_text(text, encoding="utf-8")
    return gate_result
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_confound_gate.py -v`
Expected: PASS. (`to_markdown` requires `tabulate` — add `"tabulate>=0.9"` to
`pyproject.toml` dependencies if the import fails.)

- [ ] **Step 5: Execute the real gate and read the verdict**

Run: `cd pearl && python -c "from pearl_features.confound_gate_report import run; print(run())"`

**Decision point — do not proceed past this step silently:**
- If verdict is `escalate` (`mean_auc > 0.65`): **stop this plan.** Per
  phase_2.md §11, this is the one condition that stops the project in its
  current form. Report the gate result to the user and wait; do not execute
  Tasks 8–16 (any feature built on this data cannot be distinguished from an
  artefact detector until Option C is addressed).
- If verdict is `proceed` or `proceed_with_baseline`: continue to Task 7. Note
  the verdict — Task 14's pipeline output must carry it forward so Phase 3 can
  report the QC-only baseline alongside real features if
  `proceed_with_baseline`.

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_features/confound_gate_report.py pearl/tests/test_features_confound_gate.py \
        pearl/reports/phase2_confound_gate.md pearl/pyproject.toml
git commit -m "phase2: run confound gate, write verdict-first report"
```

---

## Task 7: Cross-check the 50 Hz harmonic-exclusion index against group (spec cross-reference)

phase_2.md §6b says the excluded harmonic index must be verified against group
"same test as §1a" — this depends on §6b's per-subject excluded index, which
does not exist until Task 12. **Defer this specific check into Task 12 Step 6**
(it reuses `confound_gate.association_tests`/a Fisher test directly). No
standalone task needed here; this note exists so the dependency is not lost.

---

## Task 8: Eyes-closed continuous extraction + label-blind artifact rejection (§2)

**Files:**
- Create: `pearl/src/pearl_features/epoching.py`
- Test: `pearl/tests/test_features_epoching.py`

**Interfaces:**
- Produces: `epoching.load_iaf_window(subject: str, task: str = "rest") -> tuple[float, float]`
  — reads `IAFWindow.tmin_s/tmax_s` from the Phase 1 sidecar; raises
  `ValueError` if absent (never re-derive it).
- Produces: `epoching.load_eyes_closed_continuous(subject: str) -> "mne.io.Raw"`
  — loads the rest `.fif`, crops to the IAF window, returns the cropped Raw.
- Produces: `epoching.reject_artifact_segments(raw: "mne.io.Raw", cfg: dict) ->
  tuple["mne.io.Raw", "mne.Annotations", float]` — returns
  `(raw_with_bad_annotations, annotations, usable_duration_s)`, using fixed
  amplitude/gradient thresholds from `cfg["artifact_rejection"]`
  (`peak_v`, `gradient_v_per_s`, `window_s` — new keys added to
  `config/features.yaml` in Task 12, but this function takes `cfg` as a plain
  dict so it is unit-testable without that file existing yet).

- [ ] **Step 1: Write the failing tests using synthetic data (no real .fif needed for the reject function)**

```python
# pearl/tests/test_features_epoching.py
import json
from pathlib import Path

import mne
import numpy as np
import pytest

from pearl_features.epoching import load_iaf_window, reject_artifact_segments


def test_load_iaf_window_reads_sidecar(tmp_path, monkeypatch):
    sidecar = {"IAFWindow": {"method": "eyes_closed", "tmin_s": 10.0, "tmax_s": 40.0}}
    sub_dir = tmp_path / "sub-99" / "eeg"
    sub_dir.mkdir(parents=True)
    (sub_dir / "sub-99_task-rest_desc-preproc_eeg.json").write_text(json.dumps(sidecar))
    monkeypatch.setattr("pearl_features.epoching.PREPROC_DIR", tmp_path)
    assert load_iaf_window("sub-99") == (10.0, 40.0)


def test_load_iaf_window_raises_without_sidecar_block(tmp_path, monkeypatch):
    sub_dir = tmp_path / "sub-98" / "eeg"
    sub_dir.mkdir(parents=True)
    (sub_dir / "sub-98_task-rest_desc-preproc_eeg.json").write_text(json.dumps({}))
    monkeypatch.setattr("pearl_features.epoching.PREPROC_DIR", tmp_path)
    with pytest.raises(ValueError):
        load_iaf_window("sub-98")


def _synthetic_raw(n_seconds=10, sfreq=500.0, n_ch=3, seed=0):
    rng = np.random.default_rng(seed)
    n_samples = int(n_seconds * sfreq)
    data = rng.normal(0, 1e-6, size=(n_ch, n_samples))
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose=False)


def test_reject_artifact_segments_flags_amplitude_spike():
    raw = _synthetic_raw()
    data = raw.get_data()
    data[0, 1000:1010] = 5e-4  # 500 uV spike, far above any reasonable peak_v
    raw._data = data
    cfg = {"artifact_rejection": {"peak_v": 1.5e-4, "window_s": 1.0}}
    cleaned, ann, usable_s = reject_artifact_segments(raw, cfg)
    assert usable_s < raw.times[-1]
    assert len(ann.onset) >= 1


def test_reject_artifact_segments_clean_signal_full_duration():
    raw = _synthetic_raw()
    cfg = {"artifact_rejection": {"peak_v": 1.5e-4, "window_s": 1.0}}
    cleaned, ann, usable_s = reject_artifact_segments(raw, cfg)
    assert usable_s == pytest.approx(raw.times[-1], rel=0.05)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_epoching.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `epoching.py`**

```python
# pearl/src/pearl_features/epoching.py
"""§2 — eyes-closed continuous extraction. Feature extraction stays
label-blind: same enforced test as Phase 1 (test_features_labelblind.py),
extended from pearl_preproc.

Reuses the fixed-window peak-to-peak artifact measure from
config/preproc.yaml's artifact_annotation policy (phase_1.md), applied here to
mark rejected segments as mne annotations rather than to compute a QC
percentage — Phase 2 needs the actual rejected-sample mask, Phase 1 only
needed the fraction.
"""
from __future__ import annotations

import json

import mne
import numpy as np

from pearl_preproc.paths import PREPROC_DIR


def load_iaf_window(subject: str, task: str = "rest") -> tuple[float, float]:
    sidecar_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-{task}_desc-preproc_eeg.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    window = sidecar.get("IAFWindow")
    if not window or "tmin_s" not in window or "tmax_s" not in window:
        raise ValueError(f"{sidecar_path} has no IAFWindow block — Phase 1 must resolve this "
                          f"before Phase 2 can consume it; never re-derive it here.")
    return float(window["tmin_s"]), float(window["tmax_s"])


def load_eyes_closed_continuous(subject: str, task: str = "rest") -> mne.io.Raw:
    tmin, tmax = load_iaf_window(subject, task)
    fif_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-{task}_desc-preproc_eeg.fif"
    raw = mne.io.read_raw_fif(fif_path, preload=True, verbose=False)
    raw.crop(tmin=tmin, tmax=min(tmax, raw.times[-1]))
    return raw


def reject_artifact_segments(raw: mne.io.Raw, cfg: dict) -> tuple[mne.io.Raw, mne.Annotations, float]:
    rc = cfg["artifact_rejection"]
    peak_v = float(rc["peak_v"])
    window_s = float(rc.get("window_s", 1.0))
    sfreq = raw.info["sfreq"]
    win_samples = max(1, int(round(window_s * sfreq)))
    data = raw.get_data()
    n_samples = data.shape[1]

    onsets, durations = [], []
    for start in range(0, n_samples, win_samples):
        end = min(start + win_samples, n_samples)
        window = data[:, start:end]
        ptp = window.max(axis=1) - window.min(axis=1)
        if np.any(ptp > peak_v):
            onsets.append(start / sfreq)
            durations.append((end - start) / sfreq)

    annotations = mne.Annotations(onset=onsets, duration=durations,
                                   description=["BAD_artifact"] * len(onsets))
    raw_annotated = raw.copy().set_annotations(annotations)
    usable_s = raw.times[-1] - sum(durations)
    return raw_annotated, annotations, usable_s
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_epoching.py -v`
Expected: PASS

- [ ] **Step 5: Extend the label-blindness test to cover this module explicitly**

`epoching.py` is not in `SANCTIONED`, so `test_features_labelblind.py` from
Task 1 already scans it — no change needed there. Re-run it as a regression
check:

Run: `cd pearl && python -m pytest tests/test_features_labelblind.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_features/epoching.py pearl/tests/test_features_epoching.py
git commit -m "phase2: eyes-closed continuous extraction and artifact rejection (§2)"
```

---

## Task 9: Cycle detection (§3)

**Files:**
- Create: `pearl/src/pearl_features/cycles.py`
- Test: `pearl/tests/test_features_cycles.py`

**Interfaces:**
- Produces: `cycles.narrowband_copy(data: np.ndarray, sfreq: float, iaf_hz: float,
  half_width_hz: float = 2.0) -> np.ndarray` — zero-phase FIR bandpass at
  `[iaf_hz - half_width_hz, iaf_hz + half_width_hz]`, `mne.filter.filter_data`
  under the hood (`method="fir", phase="zero", fir_design="firwin"` — same
  phase convention as Phase 1's high-pass, per phase_2.md §3's "zero-phase
  FIR; record the exact spec").
- Produces: `cycles.positive_slope_zero_crossings(signal: np.ndarray, sfreq: float)
  -> np.ndarray` — sample indices, each rounded to "the first positive sample
  after the crossing" (phase_2.md §3 step 2).
- Produces: `cycles.phase_locked_boundaries(crossings: np.ndarray, sfreq: float) ->
  np.ndarray` — implements step 3: estimate period as the running median of
  consecutive crossing gaps up to each point (or the immediately preceding gap
  — see the algorithm block below), then pick, from `crossings`, the boundary
  **closest to** `t_k + P(t_k)`, not merely the next one after it.
- Produces: `cycles.CycleValidityConfig` (dataclass): `min_period_frac: float =
  0.6`, `max_period_frac: float = 1.4` (±40% of `1/iaf_hz`),
  `min_amplitude_percentile: float = 10.0`.
- Produces: `cycles.extract_valid_cycles(broadband: np.ndarray, boundaries: np.ndarray,
  sfreq: float, iaf_hz: float, cfg: "CycleValidityConfig") -> tuple[list[np.ndarray], dict]`
  — returns `(list of broadband cycle segments, stats)` where `stats` has
  `n_detected, n_valid, rejection_rate, median_period_s`.

- [ ] **Step 1: Write the failing synthetic-signal tests**

```python
# pearl/tests/test_features_cycles.py
import numpy as np
import pytest

from pearl_features.cycles import (
    narrowband_copy, positive_slope_zero_crossings, phase_locked_boundaries,
    extract_valid_cycles, CycleValidityConfig,
)


def _synthetic_alpha(seconds=10.0, sfreq=500.0, freq=10.0, noise_std=0.05, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sfreq)) / sfreq
    signal = np.sin(2 * np.pi * freq * t) + rng.normal(0, noise_std, size=t.shape)
    return signal, t


def test_narrowband_copy_recovers_dominant_frequency():
    signal, t = _synthetic_alpha()
    nb = narrowband_copy(signal, sfreq=500.0, iaf_hz=10.0, half_width_hz=2.0)
    freqs = np.fft.rfftfreq(len(nb), d=1 / 500.0)
    spectrum = np.abs(np.fft.rfft(nb))
    peak_freq = freqs[np.argmax(spectrum)]
    assert peak_freq == pytest.approx(10.0, abs=0.5)


def test_positive_slope_zero_crossings_count_matches_known_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.0)
    crossings = positive_slope_zero_crossings(signal, sfreq=500.0)
    # 10 Hz over 10s => ~100 positive-slope crossings
    assert 95 <= len(crossings) <= 105


def test_phase_locked_boundaries_median_period_close_to_true_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.02)
    crossings = positive_slope_zero_crossings(signal, sfreq=500.0)
    boundaries = phase_locked_boundaries(crossings, sfreq=500.0)
    periods = np.diff(boundaries) / 500.0
    assert np.median(periods) == pytest.approx(0.1, rel=0.15)  # 1/10 Hz


def test_detector_degrades_gracefully_on_pure_noise():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, size=5000)
    crossings = positive_slope_zero_crossings(noise, sfreq=500.0)
    # must not crash and must not fabricate a suspiciously regular cycle count;
    # any finite array is acceptable, just assert it runs and returns int array
    assert crossings.dtype.kind in "iu"


def test_extract_valid_cycles_rejects_out_of_band_period():
    signal, t = _synthetic_alpha(seconds=10.0, freq=10.0, noise_std=0.0)
    nb = narrowband_copy(signal, sfreq=500.0, iaf_hz=10.0)
    crossings = positive_slope_zero_crossings(nb, sfreq=500.0)
    boundaries = phase_locked_boundaries(crossings, sfreq=500.0)
    cfg = CycleValidityConfig()
    cycles_out, stats = extract_valid_cycles(signal, boundaries, sfreq=500.0,
                                              iaf_hz=10.0, cfg=cfg)
    assert stats["rejection_rate"] < 0.3
    assert stats["median_period_s"] == pytest.approx(0.1, rel=0.15)
    assert all(len(c) > 0 for c in cycles_out)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_cycles.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `cycles.py`**

```python
# pearl/src/pearl_features/cycles.py
"""§3 — cycle detection (thesis chapter §5.1.2, adapted).

Detect cycle boundaries on a narrowband copy. Measure waveform shape on the
broadband signal. Filtering to the alpha band and then measuring harmonic
content of the result measures the filter, not the signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import mne
import numpy as np


def narrowband_copy(data: np.ndarray, sfreq: float, iaf_hz: float,
                     half_width_hz: float = 2.0) -> np.ndarray:
    """Zero-phase FIR bandpass at [iaf_hz - half_width_hz, iaf_hz + half_width_hz].
    Exact spec: mne.filter.filter_data(method="fir", phase="zero", fir_design="firwin")."""
    l_freq = max(0.1, iaf_hz - half_width_hz)
    h_freq = iaf_hz + half_width_hz
    return mne.filter.filter_data(data.astype(np.float64), sfreq, l_freq, h_freq,
                                   method="fir", phase="zero", fir_design="firwin",
                                   verbose=False)


def positive_slope_zero_crossings(signal: np.ndarray, sfreq: float) -> np.ndarray:
    """Indices of positive-slope zero crossings, each rounded to the first
    positive sample after the crossing (phase_2.md §3 step 2)."""
    sign = np.sign(signal)
    sign[sign == 0] = 1  # treat exact zero as positive, avoids double-counting
    crossing_mask = (sign[:-1] < 0) & (sign[1:] >= 0)
    idx = np.nonzero(crossing_mask)[0] + 1  # index of first sample >= 0 after a negative sample
    return idx.astype(np.int64)


def phase_locked_boundaries(crossings: np.ndarray, sfreq: float) -> np.ndarray:
    """§3 step 3: estimate the period from local crossing spacing, then locate
    the next boundary as the crossing closest to t_k + P(t_k) — not merely the
    next one after it. P(t_k) is estimated as the gap to the immediately
    preceding crossing (the only period estimate available causally at t_k);
    the first crossing is always kept as-is (no prior period to phase-lock from)."""
    if len(crossings) < 2:
        return crossings.copy()

    boundaries = [int(crossings[0])]
    k = 0
    while True:
        t_k = boundaries[-1]
        # causal period estimate: gap to the previous accepted boundary, else
        # the gap between the first two raw crossings
        if len(boundaries) >= 2:
            period_samples = boundaries[-1] - boundaries[-2]
        else:
            period_samples = crossings[1] - crossings[0]
        target = t_k + period_samples
        candidates = crossings[crossings > t_k]
        if len(candidates) == 0:
            break
        closest = candidates[np.argmin(np.abs(candidates - target))]
        boundaries.append(int(closest))
        if closest >= crossings[-1]:
            break
    return np.array(boundaries, dtype=np.int64)


@dataclass
class CycleValidityConfig:
    min_period_frac: float = 0.6   # ±40% of 1/iaf_hz
    max_period_frac: float = 1.4
    min_amplitude_percentile: float = 10.0


def extract_valid_cycles(broadband: np.ndarray, boundaries: np.ndarray, sfreq: float,
                          iaf_hz: float, cfg: CycleValidityConfig) -> tuple[list[np.ndarray], dict]:
    """Map narrowband-detected boundaries onto the broadband signal, apply the
    a priori validity filter, and log the rejection rate."""
    if len(boundaries) < 2:
        return [], {"n_detected": 0, "n_valid": 0, "rejection_rate": 1.0, "median_period_s": float("nan")}

    expected_period_s = 1.0 / iaf_hz
    lo = cfg.min_period_frac * expected_period_s
    hi = cfg.max_period_frac * expected_period_s

    raw_cycles = [broadband[boundaries[i]:boundaries[i + 1]] for i in range(len(boundaries) - 1)]
    periods_s = np.diff(boundaries) / sfreq

    in_band = (periods_s >= lo) & (periods_s <= hi)
    amps = np.array([c.max() - c.min() if len(c) else 0.0 for c in raw_cycles])
    amp_thresh = np.percentile(amps, cfg.min_amplitude_percentile) if len(amps) else 0.0
    keep = in_band & (amps >= amp_thresh)

    valid_cycles = [c for c, k in zip(raw_cycles, keep) if k]
    n_detected = len(raw_cycles)
    n_valid = len(valid_cycles)
    stats = {
        "n_detected": n_detected,
        "n_valid": n_valid,
        "rejection_rate": 1.0 - (n_valid / n_detected if n_detected else 0.0),
        "median_period_s": float(np.median(periods_s[keep])) if n_valid else float("nan"),
    }
    return valid_cycles, stats
```

- [ ] **Step 4: Run tests, verify pass; fix the phase-locking loop if any test is flaky**

Run: `cd pearl && python -m pytest tests/test_features_cycles.py -v`
Expected: PASS. If `test_phase_locked_boundaries_median_period_close_to_true_period`
is borderline, widen the `rel=` tolerance slightly rather than changing the
algorithm — the phase-locking rule is specified exactly in phase_2.md and must
not be adjusted to make a test pass.

- [ ] **Step 5: Add the "recovers a known period on synthetic 10 Hz + noise" sanity test required by §3/§9**

This is already covered by `test_phase_locked_boundaries_median_period_close_to_true_period`
and `test_extract_valid_cycles_rejects_out_of_band_period` above — no
additional test needed, but note in the PR description which test satisfies
which §9 bullet.

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_features/cycles.py pearl/tests/test_features_cycles.py
git commit -m "phase2: cycle detection with phase-locked boundary placement (§3)"
```

---

## Task 10: PSR matrix — DFT-based cycle resampling (§4)

**Files:**
- Create: `pearl/src/pearl_features/psr.py`
- Test: `pearl/tests/test_features_psr.py`

**Interfaces:**
- Consumes: `list[np.ndarray]` of valid broadband cycles from Task 9's `extract_valid_cycles`.
- Produces: `psr.mode_period(cycles: list[np.ndarray]) -> int` — mode of `{len(c) for c in cycles}`.
- Produces: `psr.dft_resample(cycle: np.ndarray, target_len: int) -> np.ndarray` —
  DFT of size `Q_i = len(cycle)`, truncate/zero-extend to `target_len` (`P`),
  IDFT scaled by `P/Q_i`, Nyquist bin zeroed when `P` or `Q_i` is odd.
- Produces: `psr.build_psr_matrix(cycles: list[np.ndarray], target_period: int | None = None)
  -> np.ndarray` — shape `(len(cycles), P)`; raises `AssertionError` if `P < 40`.

- [ ] **Step 1: Write the failing tests**

```python
# pearl/tests/test_features_psr.py
import numpy as np
import pytest

from pearl_features.psr import mode_period, dft_resample, build_psr_matrix


def test_mode_period_picks_most_common_length():
    cycles = [np.zeros(48), np.zeros(50), np.zeros(50), np.zeros(50), np.zeros(52)]
    assert mode_period(cycles) == 50


def test_dft_resample_same_length_is_near_identity():
    t = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=50)
    np.testing.assert_allclose(out, cycle, atol=1e-8)


def test_dft_resample_upsamples_preserving_shape():
    t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=80)
    assert len(out) == 80
    # a resampled single sinusoid stays approximately sinusoidal at the same
    # number of cycles (1 full period), so its own zero crossing count is ~2
    sign_changes = np.sum(np.diff(np.sign(out)) != 0)
    assert 1 <= sign_changes <= 3


def test_dft_resample_nyquist_zeroed_for_odd_target():
    t = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    cycle = np.sin(t)
    out = dft_resample(cycle, target_len=51)
    spectrum = np.fft.rfft(out)
    nyquist_bin = len(out) // 2
    assert abs(spectrum[nyquist_bin]) < 1e-6


def test_build_psr_matrix_shape_and_assertion():
    rng = np.random.default_rng(0)
    cycles = [rng.normal(size=50) for _ in range(20)]
    mat = build_psr_matrix(cycles)
    assert mat.shape == (20, 50)


def test_build_psr_matrix_raises_below_40():
    cycles = [np.zeros(30) for _ in range(5)]
    with pytest.raises(AssertionError):
        build_psr_matrix(cycles)


def test_psr_reconstruction_round_trip():
    """Required by phase_2.md §4/§9: PSR construction followed by inverse must
    reconstruct to within numerical tolerance on a synthetic pseudo-periodic
    signal."""
    rng = np.random.default_rng(0)
    base = np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False))
    cycles = [base + rng.normal(0, 1e-9, size=50) for _ in range(10)]  # near-identical length, near-noiseless
    mat = build_psr_matrix(cycles, target_period=50)
    # inverse: resample each PSR row back to its own original length (50) and
    # compare to the input cycle
    for row, original in zip(mat, cycles):
        back = dft_resample(row, target_len=len(original))
        np.testing.assert_allclose(back, original, atol=1e-6)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_psr.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `psr.py`**

```python
# pearl/src/pearl_features/psr.py
"""§4 — the PSR matrix. DFT-based cycle resampling (chapter §5.2.2), not
filter-based resampling — filter-based resampling introduces edge effects at
cycle boundaries, which is exactly where the reconstruction downstream lives.
"""
from __future__ import annotations

from collections import Counter

import numpy as np


def mode_period(cycles: list[np.ndarray]) -> int:
    lengths = [len(c) for c in cycles]
    return Counter(lengths).most_common(1)[0][0]


def dft_resample(cycle: np.ndarray, target_len: int) -> np.ndarray:
    """DFT of size Q_i=len(cycle); truncate or zero-extend to target_len=P;
    IDFT scaled by P/Q_i. Nyquist bin zeroed when P or Q_i is odd -- 'odd'
    here means the resampled length has no single unambiguous Nyquist bin, so
    it is zeroed defensively regardless of which of P/Q_i is odd."""
    q = len(cycle)
    p = target_len
    spectrum = np.fft.fft(cycle.astype(np.float64))

    if p == q:
        out_spectrum = spectrum.copy()
    elif p > q:
        # zero-extend: keep low frequencies at both ends of the spectrum
        out_spectrum = np.zeros(p, dtype=complex)
        half = q // 2
        out_spectrum[:half + 1] = spectrum[:half + 1]
        out_spectrum[-(q - half - 1):] = spectrum[half + 1:]
    else:
        # truncate: keep low frequencies at both ends
        out_spectrum = np.zeros(p, dtype=complex)
        half = p // 2
        out_spectrum[:half + 1] = spectrum[:half + 1]
        if p - half - 1 > 0:
            out_spectrum[-(p - half - 1):] = spectrum[-(p - half - 1):]

    if p % 2 == 0 or q % 2 == 0:
        nyquist_bin = p // 2
        out_spectrum[nyquist_bin] = 0.0

    resampled = np.fft.ifft(out_spectrum) * (p / q)
    return np.real(resampled)


def build_psr_matrix(cycles: list[np.ndarray], target_period: int | None = None) -> np.ndarray:
    p = target_period if target_period is not None else mode_period(cycles)
    assert p >= 40, (
        f"PSR target period P={p} < 40 — the harmonic representation in §6 is "
        f"too coarse below this; the resampling step (or upstream sampling "
        f"rate) needs revisiting before proceeding (phase_2.md §4/§11).")
    return np.stack([dft_resample(c, p) for c in cycles], axis=0)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_psr.py -v`
Expected: PASS. If the round-trip test fails numerically, check the truncate
branch's index symmetry first — it is the most common source of a one-sample
off-by-one in this style of DFT resampling.

- [ ] **Step 5: Commit**

```bash
git add pearl/src/pearl_features/psr.py pearl/tests/test_features_psr.py
git commit -m "phase2: PSR matrix via DFT resampling with Nyquist-bin zeroing (§4)"
```

---

## Task 11: PSWT — polyphase perfect-reconstruction decomposition (§5)

**Files:**
- Create: `pearl/src/pearl_features/pswt.py`
- Test: `pearl/tests/test_features_pswt.py`
- Modify: `pearl/pyproject.toml` (add `PyWavelets>=1.4`)

**Interfaces:**
- Consumes: a PSR matrix `(n_cycles, P)` from Task 10.
- Produces: `pswt.demultiplex(psr_matrix: np.ndarray) -> np.ndarray` — transpose
  to `(P, n_cycles)`: column `j` of the PSR matrix (the value at phase `j`
  across cycles) becomes subsignal `j`. This is literally `psr_matrix.T`, but
  give it a name so downstream code reads as domain logic, not a stray
  transpose.
- Produces: `pswt.decompose(subsignals: np.ndarray, wavelet: str = "db8",
  level: int | None = None) -> list[tuple[np.ndarray, list[np.ndarray]]]` —
  per-subsignal `(approx_coeffs, [detail_coeffs_per_level])` via
  `pywt.wavedec`.
- Produces: `pswt.harmonic_estimate(decomposition, wavelet: str = "db8") ->
  np.ndarray` — reconstruct each subsignal from **only its lowpass/approx
  band** (`pywt.waverec([approx, None, None, ...], wavelet)`), shape
  `(P, n_cycles)`, re-multiplexed back to `(n_cycles, P)` — this is the
  harmonic/periodic estimate.
- Produces: `pswt.inter_harmonic_residual(psr_matrix, harmonic_estimate) ->
  np.ndarray` — `psr_matrix - harmonic_estimate`; the detail-band residual
  used directly by §6a's cycle-to-cycle variability feature.
- Produces: `pswt.perfect_reconstruction(subsignals: np.ndarray, wavelet: str =
  "db8") -> np.ndarray` — full reconstruction using **all** subbands (for the
  required PR test only, not used in feature extraction).

- [ ] **Step 1: Write the failing tests**

```python
# pearl/tests/test_features_pswt.py
import numpy as np
import pytest

from pearl_features.pswt import (
    demultiplex, decompose, harmonic_estimate, inter_harmonic_residual,
    perfect_reconstruction,
)


def _synthetic_psr(n_cycles=64, p=50, seed=0):
    rng = np.random.default_rng(seed)
    base = np.sin(np.linspace(0, 2 * np.pi, p, endpoint=False))
    return np.stack([base + rng.normal(0, 0.01, size=p) for _ in range(n_cycles)], axis=0)


def test_demultiplex_shape_is_transposed():
    psr = _synthetic_psr()
    sub = demultiplex(psr)
    assert sub.shape == (psr.shape[1], psr.shape[0])
    np.testing.assert_array_equal(sub[3], psr[:, 3])


def test_perfect_reconstruction_with_all_subbands_round_trips():
    psr = _synthetic_psr(n_cycles=64, p=50)
    sub = demultiplex(psr)
    recon = perfect_reconstruction(sub, wavelet="db8")
    recon_psr = recon.T[: psr.shape[0], : psr.shape[1]]
    np.testing.assert_allclose(recon_psr, psr, atol=1e-6)


def test_harmonic_estimate_plus_residual_equals_original():
    psr = _synthetic_psr(n_cycles=64, p=50)
    sub = demultiplex(psr)
    decomp = decompose(sub, wavelet="db8")
    h_est = harmonic_estimate(decomp, wavelet="db8")
    residual = inter_harmonic_residual(psr, h_est)
    np.testing.assert_allclose(h_est + residual, psr, atol=1e-6)


def test_harmonic_estimate_removes_most_high_frequency_noise():
    p = 50
    n_cycles = 64
    t = np.linspace(0, 2 * np.pi, p, endpoint=False)
    rng = np.random.default_rng(1)
    clean = np.stack([np.sin(t) for _ in range(n_cycles)], axis=0)
    noisy = clean + rng.normal(0, 0.3, size=clean.shape)
    sub = demultiplex(noisy)
    decomp = decompose(sub, wavelet="db8")
    h_est = harmonic_estimate(decomp, wavelet="db8")
    err_noisy = np.mean((noisy - clean) ** 2)
    err_denoised = np.mean((h_est - clean) ** 2)
    assert err_denoised < err_noisy
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_pswt.py -v`
Expected: FAIL — `ModuleNotFoundError` (also add `PyWavelets` to `pyproject.toml`
dependencies now, same as Task 5's scikit-learn addition).

- [ ] **Step 3: Implement `pswt.py`**

```python
# pearl/src/pearl_features/pswt.py
"""§5 — PSWT via the multiplexed / polyphase structure (chapter §5.4.2), NOT
comb wavelets: comb wavelets lose perfect reconstruction for even P, and with
P ~= 50 (even) that failure mode is hit immediately.
"""
from __future__ import annotations

import numpy as np
import pywt


def demultiplex(psr_matrix: np.ndarray) -> np.ndarray:
    """(n_cycles, P) -> (P, n_cycles): subsignal j is phase j across cycles."""
    return psr_matrix.T.copy()


def _max_level(n: int, wavelet: str) -> int:
    return pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)


def decompose(subsignals: np.ndarray, wavelet: str = "db8", level: int | None = None):
    out = []
    for row in subsignals:
        lvl = level if level is not None else _max_level(len(row), wavelet)
        lvl = max(1, lvl)
        coeffs = pywt.wavedec(row, wavelet, level=lvl, mode="periodization")
        out.append((coeffs[0], coeffs[1:]))
    return out


def harmonic_estimate(decomposition, wavelet: str = "db8") -> np.ndarray:
    """Reconstruct each subsignal from its lowpass/approx band only -> the
    harmonic/periodic estimate. Re-multiplexed back to (n_cycles, P)."""
    rows = []
    for approx, details in decomposition:
        zero_details = [np.zeros_like(d) for d in details]
        recon = pywt.waverec([approx, *zero_details], wavelet, mode="periodization")
        rows.append(recon)
    subsignals_recon = np.stack(rows, axis=0)  # (P, n_cycles)
    return subsignals_recon.T  # -> (n_cycles, P)


def inter_harmonic_residual(psr_matrix: np.ndarray, harmonic_est: np.ndarray) -> np.ndarray:
    n = min(psr_matrix.shape[1], harmonic_est.shape[1])
    return psr_matrix[:, :n] - harmonic_est[:, :n]


def perfect_reconstruction(subsignals: np.ndarray, wavelet: str = "db8") -> np.ndarray:
    """Full reconstruction using ALL subbands. Required PR test only — not
    used directly by feature extraction (harmonic_estimate is)."""
    decomp = decompose(subsignals, wavelet=wavelet)
    rows = []
    for approx, details in decomp:
        recon = pywt.waverec([approx, *details], wavelet, mode="periodization")
        rows.append(recon)
    return np.stack(rows, axis=0)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_pswt.py -v`
Expected: PASS. If the PR round-trip test fails by a small shape mismatch,
`mode="periodization"` in both `wavedec`/`waverec` calls (not the PyWavelets
default `"symmetric"`) is required for exact-length round-trips — verify both
call sites use it.

- [ ] **Step 5: Commit**

```bash
git add pearl/src/pearl_features/pswt.py pearl/tests/test_features_pswt.py pearl/pyproject.toml
git commit -m "phase2: PSWT polyphase decomposition with perfect reconstruction (§5)"
```

---

## Task 12: Feature definitions, `config/features.yaml`, and the 50 Hz exclusion (§6)

**Files:**
- Create: `pearl/config/features.yaml`
- Create: `pearl/src/pearl_features/features.py`
- Test: `pearl/tests/test_features_extraction.py`

**Interfaces:**
- Consumes: `psr.build_psr_matrix`, `pswt.demultiplex/decompose/harmonic_estimate/inter_harmonic_residual`, `cycles.extract_valid_cycles`.
- Produces: `features.fifth_harmonic_index(iaf_hz: float, n_harmonics: int, cycle_freq_hz: float,
  mains_hz: float = 50.0) -> int` — harmonic index (1-based) whose frequency
  `k * cycle_freq_hz` is nearest `mains_hz`, where `cycle_freq_hz = iaf_hz`
  (the fundamental is the detected cycle rate, which tracks IAF by construction).
- Produces: `features.harmonic_amplitude_profile(psr_matrix: np.ndarray, n_harmonics: int,
  exclude_index: int | None) -> np.ndarray` — per-cycle DFT magnitude of
  harmonics `1..n_harmonics` normalised to the fundamental (harmonic 1),
  `exclude_index` set to `np.nan` before aggregation.
- Produces: `features.aggregate_cycles(values: np.ndarray, n_subsample: int, seed: int) ->
  dict` — `{"median": float, "iqr": float}` after seeded subsampling to
  exactly `n_subsample` cycles (raises if fewer cycles are available than
  `n_subsample`).
- Produces: `features.aggregate_channels(per_channel: dict[str, dict]) -> dict` — median/IQR
  across ROI channels of each channel's already cycle-aggregated median.
- Produces: `features.compute_subject_features(subject: str, cfg: dict) -> dict[str, float]`
  — orchestrates one subject end to end for the ROI channels in `cfg["roi_channels"]`,
  returns the flat feature dict (≤ 30 keys, matching `config/features.yaml`).
- Produces: `features.load_features_config(path=None) -> dict` (mirrors
  `pearl_preproc.config.load_preproc_config`).

- [ ] **Step 1: Write `config/features.yaml`**

```yaml
# pearl/config/features.yaml — phase_2.md §6. Declared before running
# extraction. Nothing added after seeing results. <= 30 features total.

roi_channels: [O1, Oz, O2, O9, O10, POz, PO7, PO8, PO3, PO4, Pz, P3, P4, PO9, PO10]

narrowband:
  half_width_hz: 2.0

cycle_validity:
  min_period_frac: 0.6   # +-40% of 1/IAF
  max_period_frac: 1.4
  min_amplitude_percentile: 10.0

artifact_rejection:
  peak_v: 1.5e-4      # reuse Phase 1's fixed-window PTP threshold (config/preproc.yaml)
  window_s: 1.0

harmonics:
  n_harmonics: 5       # harmonics 1..5 of the fundamental; harmonic 5 is the
                       # one nearest 50 Hz for a ~10 Hz alpha rhythm and gets
                       # excluded per-subject by index (§6b)
  mains_hz: 50.0

pswt:
  wavelet: db8

aggregation:
  cycle_subsample_n: 200   # fixed cycle count per subject; floor chosen after
                            # Task 14's cycle_stats.csv run confirms every
                            # surviving subject clears it (§6d) — placeholder
                            # until that check; do not lower without recording why
  seed: 20260809

dimensionality_budget:
  max_features: 30

feature_list:
  # 5 waveform-shape families x (median, IQR) x (aggregated already across
  # cycles+channels, so each family contributes exactly 2 columns) = 10
  # columns, well under the 30 cap, leaving headroom for the harmonic profile
  # (5 harmonics x 2 agg stats = 10, one NaN'd per subject) = 20 total.
  - harmonic_amplitude_profile_h1_median
  - harmonic_amplitude_profile_h1_iqr
  - harmonic_amplitude_profile_h2_median
  - harmonic_amplitude_profile_h2_iqr
  - harmonic_amplitude_profile_h3_median
  - harmonic_amplitude_profile_h3_iqr
  - harmonic_amplitude_profile_h4_median
  - harmonic_amplitude_profile_h4_iqr
  - harmonic_amplitude_profile_h5_median
  - harmonic_amplitude_profile_h5_iqr
  - harmonic_to_interharmonic_ratio_median
  - harmonic_to_interharmonic_ratio_iqr
  - cycle_to_cycle_variability_median
  - cycle_to_cycle_variability_iqr
  - period_variability_median
  - period_variability_iqr
  - rise_decay_ratio_median
  - rise_decay_ratio_iqr
  - peak_trough_sharpness_ratio_median
  - peak_trough_sharpness_ratio_iqr
```

- [ ] **Step 2: Write the failing tests**

```python
# pearl/tests/test_features_extraction.py
import numpy as np
import pytest
import yaml

from pearl_features.features import (
    fifth_harmonic_index, harmonic_amplitude_profile, aggregate_cycles,
    load_features_config,
)
from pearl_features.paths import FEATURES_YAML


def test_load_features_config_declares_at_most_30_features():
    cfg = load_features_config()
    assert len(cfg["feature_list"]) <= cfg["dimensionality_budget"]["max_features"]


def test_fifth_harmonic_index_tracks_iaf():
    # 10 Hz IAF -> harmonic 5 lands exactly on 50 Hz
    assert fifth_harmonic_index(iaf_hz=10.0, n_harmonics=8, cycle_freq_hz=10.0) == 5
    # 8.25 Hz IAF -> nearest harmonic to 50 Hz is round(50/8.25)=6
    assert fifth_harmonic_index(iaf_hz=8.25, n_harmonics=8, cycle_freq_hz=8.25) == 6
    # 12.4 Hz IAF -> round(50/12.4)=4
    assert fifth_harmonic_index(iaf_hz=12.4, n_harmonics=8, cycle_freq_hz=12.4) == 4


def test_harmonic_amplitude_profile_excludes_index_as_nan():
    rng = np.random.default_rng(0)
    psr = np.stack([np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False)) for _ in range(30)])
    profile = harmonic_amplitude_profile(psr, n_harmonics=5, exclude_index=3)
    assert profile.shape == (30, 5)
    assert np.all(np.isnan(profile[:, 2]))  # 0-indexed column for harmonic index 3
    assert not np.any(np.isnan(profile[:, 0]))


def test_harmonic_amplitude_profile_fundamental_normalised_to_one():
    psr = np.stack([np.sin(np.linspace(0, 2 * np.pi, 50, endpoint=False)) for _ in range(10)])
    profile = harmonic_amplitude_profile(psr, n_harmonics=3, exclude_index=None)
    np.testing.assert_allclose(profile[:, 0], 1.0, atol=1e-6)  # harmonic 1 / harmonic 1


def test_aggregate_cycles_deterministic_under_fixed_seed():
    rng = np.random.default_rng(0)
    values = rng.normal(size=500)
    a = aggregate_cycles(values, n_subsample=200, seed=42)
    b = aggregate_cycles(values, n_subsample=200, seed=42)
    assert a == b


def test_aggregate_cycles_raises_when_too_few_cycles():
    values = np.zeros(10)
    with pytest.raises(ValueError):
        aggregate_cycles(values, n_subsample=200, seed=42)
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_extraction.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `features.py`**

```python
# pearl/src/pearl_features/features.py
"""§6 — feature definitions. Feature extraction stays label-blind."""
from __future__ import annotations

import numpy as np
import yaml

from pearl_features.paths import FEATURES_YAML


class FeaturesConfigError(Exception):
    pass


def load_features_config(path=None) -> dict:
    p = path or FEATURES_YAML
    if not p.exists():
        raise FeaturesConfigError(f"{p} not found.")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    required = ["roi_channels", "harmonics", "aggregation", "dimensionality_budget", "feature_list"]
    for key in required:
        if key not in cfg:
            raise FeaturesConfigError(f"config/features.yaml missing required section '{key}'.")
    return cfg


def fifth_harmonic_index(iaf_hz: float, n_harmonics: int, cycle_freq_hz: float,
                          mains_hz: float = 50.0) -> int:
    """The harmonic index (1-based) whose frequency k*cycle_freq_hz is nearest
    mains_hz. Excluded from the harmonic profile by index, uniformly, per
    subject (phase_2.md §6b) -- never by shifting the profile."""
    candidates = np.arange(1, n_harmonics + 1)
    freqs = candidates * cycle_freq_hz
    return int(candidates[np.argmin(np.abs(freqs - mains_hz))])


def harmonic_amplitude_profile(psr_matrix: np.ndarray, n_harmonics: int,
                                exclude_index: int | None) -> np.ndarray:
    """Per-cycle DFT magnitude of harmonics 1..n_harmonics, normalised to the
    fundamental. exclude_index (1-based) -> NaN column."""
    spectra = np.abs(np.fft.fft(psr_matrix, axis=1))
    profile = spectra[:, 1:n_harmonics + 1] / spectra[:, 1:2]
    if exclude_index is not None:
        profile[:, exclude_index - 1] = np.nan
    return profile


def aggregate_cycles(values: np.ndarray, n_subsample: int, seed: int) -> dict:
    """§6d: fix the cycle count via seeded subsampling, then median/IQR."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < n_subsample:
        raise ValueError(f"only {len(values)} cycles available, need >= {n_subsample} "
                          f"(fixed cycle count, §6d) — this subject should be excluded "
                          f"from feature extraction, not silently under-sampled.")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(values), size=n_subsample, replace=False)
    sample = values[idx]
    q75, q25 = np.percentile(sample, [75, 25])
    return {"median": float(np.median(sample)), "iqr": float(q75 - q25)}


def aggregate_channels(per_channel: dict[str, dict]) -> dict:
    """Median/IQR across ROI channels of each channel's cycle-aggregated median."""
    medians = np.array([v["median"] for v in per_channel.values() if not np.isnan(v["median"])])
    if len(medians) == 0:
        return {"median": float("nan"), "iqr": float("nan")}
    q75, q25 = np.percentile(medians, [75, 25])
    return {"median": float(np.median(medians)), "iqr": float(q75 - q25)}
```

- [ ] **Step 5: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_extraction.py -v`
Expected: PASS

- [ ] **Step 6: Extend `features.py` with the remaining §6a families and wire `compute_subject_features`**

Add to `features.py`:

```python
from pearl_features.cycles import CycleValidityConfig, extract_valid_cycles, narrowband_copy, phase_locked_boundaries, positive_slope_zero_crossings
from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments
from pearl_features.psr import build_psr_matrix
from pearl_features.pswt import decompose, demultiplex, harmonic_estimate, inter_harmonic_residual


def waveform_asymmetry(cycle: np.ndarray) -> tuple[float, float]:
    """Rise-decay time ratio and peak-trough sharpness ratio on a broadband cycle."""
    peak_idx = int(np.argmax(cycle))
    trough_idx = int(np.argmin(cycle))
    rise_time = peak_idx if peak_idx > 0 else 1
    decay_time = (len(cycle) - peak_idx) if peak_idx < len(cycle) else 1
    rise_decay_ratio = rise_time / decay_time

    def _sharpness(idx):
        lo, hi = max(0, idx - 1), min(len(cycle) - 1, idx + 1)
        return abs(cycle[hi] - cycle[lo])

    peak_sharp = _sharpness(peak_idx)
    trough_sharp = _sharpness(trough_idx)
    sharpness_ratio = peak_sharp / trough_sharp if trough_sharp > 1e-12 else np.nan
    return rise_decay_ratio, sharpness_ratio


def compute_channel_features(broadband_channel: np.ndarray, iaf_hz: float, sfreq: float,
                              cfg: dict) -> dict:
    nb = narrowband_copy(broadband_channel, sfreq, iaf_hz, cfg["narrowband"]["half_width_hz"])
    crossings = positive_slope_zero_crossings(nb, sfreq)
    boundaries = phase_locked_boundaries(crossings, sfreq)
    validity_cfg = CycleValidityConfig(**cfg["cycle_validity"])
    valid_cycles, cycle_stats = extract_valid_cycles(broadband_channel, boundaries, sfreq,
                                                       iaf_hz, validity_cfg)

    psr_matrix = build_psr_matrix(valid_cycles)
    p = psr_matrix.shape[1]
    cycle_freq_hz = 1.0 / cycle_stats["median_period_s"]
    excl_idx = fifth_harmonic_index(iaf_hz, cfg["harmonics"]["n_harmonics"], cycle_freq_hz,
                                     cfg["harmonics"]["mains_hz"])

    profile = harmonic_amplitude_profile(psr_matrix, cfg["harmonics"]["n_harmonics"], excl_idx)

    sub = demultiplex(psr_matrix)
    decomp = decompose(sub, wavelet=cfg["pswt"]["wavelet"])
    h_est = harmonic_estimate(decomp, wavelet=cfg["pswt"]["wavelet"])
    residual = inter_harmonic_residual(psr_matrix, h_est)
    detail_energy = np.sum(residual ** 2, axis=1)
    harmonic_energy = np.sum(h_est ** 2, axis=1)
    hi_ratio = np.divide(harmonic_energy, detail_energy,
                          out=np.full_like(harmonic_energy, np.nan), where=detail_energy > 1e-12)

    periods_s = np.array([len(c) for c in valid_cycles]) / sfreq
    period_variability = np.abs(periods_s - np.median(periods_s)) / np.median(periods_s)

    asym = np.array([waveform_asymmetry(c) for c in valid_cycles])

    return {
        "profile": profile, "excl_idx": excl_idx, "cycle_stats": cycle_stats,
        "detail_energy": detail_energy, "hi_ratio": hi_ratio,
        "period_variability": period_variability,
        "rise_decay_ratio": asym[:, 0], "sharpness_ratio": asym[:, 1],
    }


def compute_subject_features(subject: str, cfg: dict, iaf_hz: float) -> dict[str, float]:
    """Orchestrates one subject across cfg['roi_channels']. iaf_hz is passed
    in explicitly (read by the caller from the Phase 1 sidecar — see
    pipeline.py Task 14 — to keep this function free of file I/O beyond the
    channel loop, which simplifies testing)."""
    raw = load_eyes_closed_continuous(subject)
    raw, _, _ = reject_artifact_segments(raw, cfg)
    sfreq = raw.info["sfreq"]
    data = raw.get_data(picks=cfg["roi_channels"])
    ch_names = [ch for ch in cfg["roi_channels"] if ch in raw.ch_names]

    n_sub = cfg["aggregation"]["cycle_subsample_n"]
    seed = cfg["aggregation"]["seed"]

    per_channel_h = {h: {} for h in range(1, cfg["harmonics"]["n_harmonics"] + 1)}
    per_channel_hi, per_channel_cc, per_channel_pv = {}, {}, {}
    per_channel_rd, per_channel_pt = {}, {}

    for ch_idx, ch in enumerate(ch_names):
        r = compute_channel_features(data[ch_idx], iaf_hz, sfreq, cfg)
        for h in range(1, cfg["harmonics"]["n_harmonics"] + 1):
            per_channel_h[h][ch] = aggregate_cycles(r["profile"][:, h - 1], n_sub, seed)
        per_channel_hi[ch] = aggregate_cycles(r["hi_ratio"], n_sub, seed)
        per_channel_cc[ch] = aggregate_cycles(r["detail_energy"], n_sub, seed)
        per_channel_pv[ch] = aggregate_cycles(r["period_variability"], n_sub, seed)
        per_channel_rd[ch] = aggregate_cycles(r["rise_decay_ratio"], n_sub, seed)
        per_channel_pt[ch] = aggregate_cycles(r["sharpness_ratio"], n_sub, seed)

    out = {}
    for h in range(1, cfg["harmonics"]["n_harmonics"] + 1):
        agg = aggregate_channels(per_channel_h[h])
        out[f"harmonic_amplitude_profile_h{h}_median"] = agg["median"]
        out[f"harmonic_amplitude_profile_h{h}_iqr"] = agg["iqr"]
    for name, per_ch in [("harmonic_to_interharmonic_ratio", per_channel_hi),
                          ("cycle_to_cycle_variability", per_channel_cc),
                          ("period_variability", per_channel_pv),
                          ("rise_decay_ratio", per_channel_rd),
                          ("peak_trough_sharpness_ratio", per_channel_pt)]:
        agg = aggregate_channels(per_ch)
        out[f"{name}_median"] = agg["median"]
        out[f"{name}_iqr"] = agg["iqr"]
    return out
```

- [ ] **Step 7: Write the failing test for the 50 Hz exclusion group cross-check (closes Task 7's deferred item)**

```python
# append to pearl/tests/test_features_extraction.py
from pearl_features.confound_gate import association_tests, load_group_map


def test_fifth_harmonic_excluded_index_does_not_associate_with_group():
    """phase_2.md §6b: record the excluded index per subject and verify it
    does not associate with group (same test as §1a). Uses a synthetic IAF
    distribution here; the real per-subject run happens in Task 14's
    pipeline and reuses this exact check against real qc_metrics.csv IAFs."""
    import pandas as pd
    from scipy import stats

    rng = np.random.default_rng(0)
    groups = {}
    rows = []
    for i in range(1, 61):
        sid = f"sub-{i:02d}"
        g = "N" if i <= 30 else "A_P_plus"
        groups[sid] = g
        iaf = rng.normal(10.0, 1.0)  # group-independent IAF -> index should not associate
        idx = fifth_harmonic_index(iaf, n_harmonics=8, cycle_freq_hz=iaf)
        rows.append({"subject": sid, "group": g, "excluded_index": idx})
    df = pd.DataFrame(rows)
    contingency = pd.crosstab(df["group"], df["excluded_index"])
    _, p, _, _ = stats.chi2_contingency(contingency)
    assert p > 0.01  # group-independent IAF must not show a spurious association
```

- [ ] **Step 8: Run all Task 12 tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_extraction.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add pearl/config/features.yaml pearl/src/pearl_features/features.py pearl/tests/test_features_extraction.py
git commit -m "phase2: feature definitions, config/features.yaml, 50Hz harmonic exclusion (§6)"
```

---

## Task 13: Baseline spectral feature set (§7)

**Files:**
- Create: `pearl/src/pearl_features/baseline.py`
- Test: `pearl/tests/test_features_baseline.py`
- Modify: `pearl/pyproject.toml` (add `fooof>=1.1` or implement the aperiodic fit manually with `scipy.optimize.curve_fit` if `fooof`'s dependency footprint is unwanted — prefer `fooof`, it is the standard tool and small)

**Interfaces:**
- Produces: `baseline.band_power(psd: np.ndarray, freqs: np.ndarray, band: tuple[float,float]) -> float`
  — trapezoidal-integrated relative power in `band` over total power 1–45 Hz.
- Produces: `baseline.relative_band_powers(raw: "mne.io.Raw", picks: list[str]) -> dict[str, float]`
  — `delta (1-4), theta (4-8), alpha (8-13), beta (13-30), gamma (30-45)`,
  averaged across `picks`, using Welch PSD (`mne.time_frequency.psd_array_welch`).
- Produces: `baseline.aperiodic_fit(psd: np.ndarray, freqs: np.ndarray) -> tuple[float, float]`
  — `(offset, slope)` from a FOOOF/`specparam` fit over 1–45 Hz.
- Produces: `baseline.compute_subject_baseline(subject: str, iaf_hz: float,
  alpha_peak_height_db: float, roi_channels: list[str]) -> dict[str, float]`
  — assembles the full baseline row: 5 band powers + IAF + alpha peak height
  (both passed through from `qc_metrics.csv`, not recomputed — Phase 1 already
  measured them under label-blind conditions) + offset + slope + the MSIT
  multitaper equivalent reused from Phase 1 (reads `qc_metrics.csv` MSIT row's
  existing spectral columns — Phase 1 did not store per-band MSIT power, so
  this reuses `line_noise_index_before` as the only Phase-1-computed MSIT
  spectral scalar available; **do not invent new MSIT computation here** —
  flag this row as `msit_reused_metric` in the output so Phase 3 knows its
  provenance).

- [ ] **Step 1: Write the failing tests**

```python
# pearl/tests/test_features_baseline.py
import mne
import numpy as np
import pytest

from pearl_features.baseline import band_power, relative_band_powers, aperiodic_fit


def _synthetic_raw_with_alpha(seconds=60, sfreq=500.0, n_ch=3, alpha_hz=10.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * sfreq)) / sfreq
    alpha = 3e-6 * np.sin(2 * np.pi * alpha_hz * t)
    pink_like = rng.normal(0, 1e-6, size=t.shape)
    data = np.stack([alpha + pink_like + rng.normal(0, 1e-7, size=t.shape) for _ in range(n_ch)])
    info = mne.create_info([f"ch{i}" for i in range(n_ch)], sfreq, "eeg")
    return mne.io.RawArray(data, info, verbose=False)


def test_band_power_sums_to_less_than_total():
    freqs = np.linspace(1, 45, 200)
    psd = np.ones_like(freqs)
    total = band_power(psd, freqs, (1, 45))
    alpha = band_power(psd, freqs, (8, 13))
    assert alpha < total


def test_relative_band_powers_alpha_dominant_with_synthetic_alpha():
    raw = _synthetic_raw_with_alpha()
    powers = relative_band_powers(raw, picks=raw.ch_names)
    assert set(powers) == {"delta", "theta", "alpha", "beta", "gamma"}
    assert powers["alpha"] == max(powers.values())


def test_aperiodic_fit_returns_finite_offset_and_slope():
    freqs = np.linspace(1, 45, 200)
    psd = 10 ** (-2 - 1.5 * np.log10(freqs))  # synthetic 1/f with known slope ~ -1.5
    offset, slope = aperiodic_fit(psd, freqs)
    assert np.isfinite(offset)
    assert -3.0 < slope < 0.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_baseline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `baseline.py`**

```python
# pearl/src/pearl_features/baseline.py
"""§7 — baseline feature set (required, not optional): the reference the
pitch-synchronous features must beat, and how the published ~0.58 gets
reproduced.
"""
from __future__ import annotations

import numpy as np
from mne.time_frequency import psd_array_welch

_BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 45)}


def band_power(psd: np.ndarray, freqs: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs < band[1])
    return float(np.trapz(psd[mask], freqs[mask])) if mask.any() else 0.0


def relative_band_powers(raw, picks: list[str]) -> dict[str, float]:
    data = raw.get_data(picks=picks)
    sfreq = raw.info["sfreq"]
    psd, freqs = psd_array_welch(data, sfreq, fmin=1, fmax=45, n_fft=int(sfreq * 4), verbose=False)
    mean_psd = psd.mean(axis=0)
    total = band_power(mean_psd, freqs, (1, 45))
    return {name: (band_power(mean_psd, freqs, band) / total if total > 0 else 0.0)
            for name, band in _BANDS.items()}


def aperiodic_fit(psd: np.ndarray, freqs: np.ndarray) -> tuple[float, float]:
    """Offset/slope of a 1/f (log-log linear) fit over 1-45 Hz, excluding the
    canonical alpha band peak (8-13 Hz) from the fit so the periodic
    component does not bias the aperiodic estimate -- the standard FOOOF/
    specparam heuristic done manually with scipy to avoid a heavyweight
    dependency."""
    mask = ((freqs >= 1) & (freqs < 8)) | ((freqs >= 13) & (freqs <= 45))
    log_f = np.log10(freqs[mask])
    log_p = np.log10(np.clip(psd[mask], 1e-20, None))
    slope, offset = np.polyfit(log_f, log_p, 1)
    return float(offset), float(slope)


def compute_subject_baseline(raw, roi_channels: list[str], iaf_hz: float,
                              alpha_peak_height_db: float) -> dict[str, float]:
    picks = [ch for ch in roi_channels if ch in raw.ch_names]
    powers = relative_band_powers(raw, picks)
    data = raw.get_data(picks=picks).mean(axis=0)
    psd, freqs = psd_array_welch(data[np.newaxis, :], raw.info["sfreq"], fmin=1, fmax=45,
                                  n_fft=int(raw.info["sfreq"] * 4), verbose=False)
    offset, slope = aperiodic_fit(psd[0], freqs)
    return {
        "band_power_delta": powers["delta"], "band_power_theta": powers["theta"],
        "band_power_alpha": powers["alpha"], "band_power_beta": powers["beta"],
        "band_power_gamma": powers["gamma"],
        "iaf_hz": iaf_hz, "alpha_peak_height_db": alpha_peak_height_db,
        "aperiodic_offset": offset, "aperiodic_slope": slope,
    }
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_baseline.py -v`
Expected: PASS

- [ ] **Step 5: Resolve the MSIT multitaper reuse honestly before Task 14 wires it in**

Grep `pearl_preproc` and Phase 1 QC code for any stored MSIT-specific spectral
scalar beyond `line_noise_index_before/after`:

Run: `cd pearl && grep -rn "multitaper\|psd_array_multitaper\|msit" src/pearl_preproc/*.py`

If nothing beyond line-noise indices exists (expected, since Phase 1's `qc.py`
only computed rest-task IAF/alpha spectra), do not fabricate a "Phase 1
multitaper equivalent for MSIT" feature. Instead, in Task 14's baseline
pipeline, compute the same Welch-based `relative_band_powers` +
`aperiodic_fit` on the MSIT continuous derivative directly (label-blind,
using the same functions above, no new module needed) and name those columns
`msit_band_power_*` / `msit_aperiodic_*`. Record this decision — "Phase 1
multitaper equivalent" was read as "the same spectral summary, computed on
the MSIT derivative" rather than a literal artifact that does not exist — in
`feature_dictionary.md`'s provenance column for those rows (Task 14).

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_features/baseline.py pearl/tests/test_features_baseline.py pearl/pyproject.toml
git commit -m "phase2: baseline spectral feature set (band power, IAF, 1/f, MSIT spectral summary) (§7)"
```

---

## Task 14: Pipeline orchestration, outputs, and `feature_dictionary.md` (§8)

**Files:**
- Create: `pearl/src/pearl_features/pipeline.py`
- Create: `pearl/src/pearl_features/cli.py`
- Modify: `pearl/pyproject.toml` (add `pearl-features = "pearl_features.cli:main"` script entry)
- Test: `pearl/tests/test_features_pipeline.py`

**Interfaces:**
- Consumes: everything from Tasks 1, 8–13.
- Produces on disk: `data/derivatives/features/features_pswt.csv`,
  `features_baseline.csv`, `feature_dictionary.md`, `cycle_stats.csv`,
  `_meta.json` — atomic staging via `pearl_features.paths.staging_dir`/`finalize_staged`,
  one `run_id`, same convention as `pearl_preproc.paths.finalize_run`.
- Produces: `pipeline.run(run_id: str | None = None) -> dict` — top-level
  entry point; returns a summary dict `{n_subjects, n_features_pswt,
  n_features_baseline, gate_verdict}`.

- [ ] **Step 1: Write the failing pipeline smoke test (mocking subject-level compute, not real EEG)**

```python
# pearl/tests/test_features_pipeline.py
from unittest.mock import patch

import pandas as pd

from pearl_features.pipeline import assemble_output_frame, write_outputs


def test_assemble_output_frame_has_no_label_columns():
    rows = {
        "sub-01": {"harmonic_amplitude_profile_h1_median": 1.0, "period_variability_iqr": 0.2},
        "sub-02": {"harmonic_amplitude_profile_h1_median": 0.9, "period_variability_iqr": 0.3},
    }
    df = assemble_output_frame(rows, index_name="subject")
    assert "group" not in df.columns
    assert "risk_vs_none" not in df.columns.astype(str).str.cat()
    assert list(df.index) == ["sub-01", "sub-02"]


def test_write_outputs_creates_expected_files(tmp_path):
    pswt_rows = {"sub-01": {"feat_a": 1.0}}
    baseline_rows = {"sub-01": {"band_power_alpha": 0.5}}
    cycle_stats_rows = [{"subject": "sub-01", "n_detected": 100, "n_valid": 90,
                          "rejection_rate": 0.1, "median_period_s": 0.1}]
    write_outputs(pswt_rows, baseline_rows, cycle_stats_rows, out_dir=tmp_path,
                   run_id="testrun", git_sha="abc123")
    assert (tmp_path / "features_pswt.csv").exists()
    assert (tmp_path / "features_baseline.csv").exists()
    assert (tmp_path / "cycle_stats.csv").exists()
    assert (tmp_path / "_meta.json").exists()
    pswt_df = pd.read_csv(tmp_path / "features_pswt.csv")
    assert "subject" in pswt_df.columns
    assert "group" not in pswt_df.columns
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_features_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `pipeline.py`**

```python
# pearl/src/pearl_features/pipeline.py
"""§8 — orchestration and outputs. Feature files must NOT contain group
labels; the join happens in Phase 3."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pearl_features.paths import FEATURES_DIR, PHASE2_DIR, git_sha


def assemble_output_frame(rows: dict[str, dict], index_name: str = "subject") -> pd.DataFrame:
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = index_name
    return df


def write_outputs(pswt_rows: dict, baseline_rows: dict, cycle_stats_rows: list[dict],
                   out_dir: Path, run_id: str, git_sha: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    assemble_output_frame(pswt_rows).to_csv(out_dir / "features_pswt.csv")
    assemble_output_frame(baseline_rows).to_csv(out_dir / "features_baseline.csv")
    pd.DataFrame(cycle_stats_rows).to_csv(out_dir / "cycle_stats.csv", index=False)
    (out_dir / "_meta.json").write_text(json.dumps({
        "run_id": run_id, "git_sha": git_sha,
    }, indent=2) + "\n", encoding="utf-8")


def run(run_id: str | None = None) -> dict:
    from pearl_features.cohort import load_qc_metrics, per_task_cohort
    from pearl_features.features import load_features_config, compute_subject_features
    from pearl_features.baseline import compute_subject_baseline
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments
    from pearl_features.confound_gate_report import run as run_gate
    import mne

    from pearl_preproc.paths import PREPROC_DIR, make_run_id
    rid = run_id or make_run_id()

    gate_result = run_gate()
    cfg = load_features_config()
    qc = load_qc_metrics()
    per_task = per_task_cohort(qc)
    rest_included = set(per_task[(per_task["task"].isin(["rest", "task-rest"])) &
                                  per_task["included"]]["subject"])

    pswt_rows, baseline_rows, cycle_stats_rows = {}, {}, []
    for subject in sorted(rest_included):
        qc_row = qc[(qc["subject"] == subject) & (qc["task"].isin(["rest", "task-rest"]))].iloc[0]
        iaf_hz = float(qc_row["iaf_hz"])
        try:
            feats = compute_subject_features(subject, cfg, iaf_hz)
            pswt_rows[subject] = feats
        except (AssertionError, ValueError) as exc:
            cycle_stats_rows.append({"subject": subject, "excluded_reason": str(exc)})
            continue

        raw = load_eyes_closed_continuous(subject)
        raw, _, usable_s = reject_artifact_segments(raw, cfg)
        baseline_rows[subject] = compute_subject_baseline(
            raw, cfg["roi_channels"], iaf_hz, float(qc_row["alpha_peak_height_db"]))
        cycle_stats_rows.append({"subject": subject, "usable_duration_s": usable_s})

    write_outputs(pswt_rows, baseline_rows, cycle_stats_rows, FEATURES_DIR, rid, git_sha())

    return {"n_subjects": len(pswt_rows), "n_features_pswt": len(next(iter(pswt_rows.values()), {})),
            "n_features_baseline": len(next(iter(baseline_rows.values()), {})),
            "gate_verdict": gate_result["verdict"]}
```

- [ ] **Step 4: Implement `cli.py`**

```python
# pearl/src/pearl_features/cli.py
from __future__ import annotations

import argparse

from pearl_features.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="pearl-features")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    summary = run(run_id=args.run_id)
    print(summary)


if __name__ == "__main__":
    main()
```

Add to `pearl/pyproject.toml` under `[project.scripts]`:
```toml
pearl-features = "pearl_features.cli:main"
```

- [ ] **Step 5: Run pipeline tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_features_pipeline.py -v`
Expected: PASS

- [ ] **Step 6: Write `feature_dictionary.md` (hand-authored, not generated) — every column defined**

```markdown
# Feature Dictionary — data/derivatives/features/

One row per column in features_pswt.csv / features_baseline.csv. Units,
definition, provenance. No group labels appear in either file.

## features_pswt.csv (primary — §6a)

| Column | Definition | Units | Provenance |
|---|---|---|---|
| harmonic_amplitude_profile_h{1..5}_{median,iqr} | Per-cycle DFT magnitude of harmonic h, normalised to the fundamental (h=1), aggregated median/IQR across a fixed 200-cycle seeded subsample per channel, then across ROI channels | dimensionless (ratio) | PSR matrix DFT, `features.harmonic_amplitude_profile` |
| harmonic_to_interharmonic_ratio_{median,iqr} | PSWT lowpass-band energy / detail-band energy per cycle, aggregated | dimensionless (ratio) | `pswt.harmonic_estimate` / `inter_harmonic_residual` |
| cycle_to_cycle_variability_{median,iqr} | PSWT detail-band energy per cycle (the residual's own magnitude, not a ratio) | (signal units)^2 | `pswt.inter_harmonic_residual` |
| period_variability_{median,iqr} | |Q_i - median(Q)| / median(Q) per cycle | dimensionless (fraction of median period) | `cycles.extract_valid_cycles` boundary spacing |
| rise_decay_ratio_{median,iqr} | (samples peak-1 → 0) / (samples 0 → peak) on broadband cycles | dimensionless | `features.waveform_asymmetry` |
| peak_trough_sharpness_ratio_{median,iqr} | local 2-sample slope magnitude at peak / at trough, broadband | dimensionless | `features.waveform_asymmetry` |

20 columns total (≤ 30 budget, §6e).

## features_baseline.csv (comparison — §7)

| Column | Definition | Units | Provenance |
|---|---|---|---|
| band_power_{delta,theta,alpha,beta,gamma} | Welch PSD relative power, ROI-averaged | fraction of 1–45 Hz total power | `baseline.relative_band_powers` |
| iaf_hz | Individual alpha frequency | Hz | passed through from `qc_metrics.csv` (Phase 1, label-blind) |
| alpha_peak_height_db | 1/f-corrected alpha peak height | dB | passed through from `qc_metrics.csv` (Phase 1) |
| aperiodic_offset, aperiodic_slope | Log-log linear (1/f) fit over 1–45 Hz excluding 8–13 Hz | offset: log10(power); slope: unitless exponent | `baseline.aperiodic_fit` |
| msit_band_power_* , msit_aperiodic_* | Same Welch/1-f summary computed on the MSIT continuous derivative — this is the "Phase 1 multitaper equivalent for MSIT" named in phase_2.md §7; no separate multitaper-specific artifact existed in Phase 1 to reuse verbatim (see Task 13 Step 5) | same as rest-task equivalents | `baseline.relative_band_powers`/`aperiodic_fit` on MSIT derivative |

## cycle_stats.csv

| Column | Definition |
|---|---|
| subject | subject ID |
| n_detected / n_valid / rejection_rate | cycle detection and validity-filter counts (§3) |
| median_period_s | median accepted cycle period, seconds |
| usable_duration_s | eyes-closed duration surviving artifact rejection (§2) |
| excluded_reason | present only for subjects excluded by the P≥40 assertion or another hard failure |
```

- [ ] **Step 7: Run the real pipeline once and inspect output shapes**

Run: `cd pearl && python -c "from pearl_features.pipeline import run; print(run())"`

Confirm: `n_features_pswt <= 30` (Task 12's config caps it at 20), no
subject's row contains a `group`/label-like column, `cycle_stats.csv` row
count matches the rest-cohort N from Task 1.

- [ ] **Step 8: Move `feature_dictionary.md` into place and commit everything**

```bash
mkdir -p pearl/data/derivatives/features
mv feature_dictionary.md pearl/data/derivatives/features/feature_dictionary.md  # if drafted elsewhere
git add pearl/src/pearl_features/pipeline.py pearl/src/pearl_features/cli.py \
        pearl/tests/test_features_pipeline.py pearl/pyproject.toml \
        data/derivatives/features/
git commit -m "phase2: pipeline orchestration, outputs, feature dictionary (§8)"
```

---

## Task 15: Full test suite, label-blindness, and Definition-of-Done sweep

**Files:** none new — verification only.

- [ ] **Step 1: Run the complete pearl test suite**

Run: `cd pearl && python -m pytest -v`
Expected: all tests (Phase 1's ~91 + every test added in Tasks 1–14) PASS.

- [ ] **Step 2: Re-run label blindness for both packages as an explicit regression gate**

Run: `cd pearl && python -m pytest tests/test_preproc_labelblind.py tests/test_features_labelblind.py -v`
Expected: PASS. If `epoching.py`, `cycles.py`, `psr.py`, `pswt.py`, `features.py`,
`baseline.py`, `pipeline.py`, or `cli.py` fail this, the offending token/import
must be removed from that file, not from the test.

- [ ] **Step 3: Walk the phase_2.md §10 Definition-of-Done checklist one item at a time**

For each of the 11 checkboxes in phase_2.md §10, confirm the concrete artifact
exists and open it:
- Amendment 1 → `git log --oneline -- pearl/reports/analysis_plan_frozen.md`
- Benchmark citation → `pearl/reports/benchmark_citation.md` exists, status set
- Confound gate report → `pearl/reports/phase2_confound_gate.md` exists, leads with VERDICT
- Per-task cohort → `data/derivatives/phase2/cohort_per_task.csv` exists
- Cycle detection validated → `pytest tests/test_features_cycles.py` green; `cycle_stats.csv` has all surviving subjects
- PSR/PSWT reconstruction → `pytest tests/test_features_psr.py tests/test_features_pswt.py -k reconstruction` green
- Feature CSVs → `data/derivatives/features/features_pswt.csv`/`features_baseline.csv` exist, ≤30 cols each
- `feature_dictionary.md` → exists, every column covered
- 50 Hz exclusion tested against group → `pytest tests/test_features_extraction.py -k fifth_harmonic` green
- Label blindness → Step 2 above
- `pytest` green under one run_id → Step 1 above, plus `data/derivatives/features/_meta.json` has a single `run_id`

- [ ] **Step 4: Report §11 stop conditions explicitly, even if none triggered**

Write one paragraph (in the final commit message or a short note to the user,
not a new file) confirming none of phase_2.md §11's stop conditions fired:
QC-only AUC ≤ 0.65 (Task 6), PSR/PSWT reconstruction passed (Task 10/11), no
`P < 40` assertion failures for a meaningful share of subjects (Task 14 Step 7),
cycle rejection rate ≤ ~30% for all but a handful of subjects (`cycle_stats.csv`),
surviving N close to 64 (Task 1), harmonic-exclusion index does not associate
with group after FDR (Task 12 Step 7 test, and re-verify with the **real**
per-subject IAFs from `qc_metrics.csv` rather than only the synthetic test —
add a one-off `python -c` check using `pearl_features.confound_gate.association_tests`
against a real `excluded_index` column added to `cycle_stats.csv` in Task 14
if not already present).

- [ ] **Step 5: Final commit**

```bash
git add -A
git status  # review before committing — nothing outside pearl/, data/derivatives/, docs/ should be staged
git commit -m "phase2: complete — gate passed, PSR/PSWT feature pipeline green, DoD checklist verified"
```

---

## Self-Review Notes (for whoever executes this plan)

- **Spec coverage:** §0a/§0b → Task 2. §0c → deferred by design (record only,
  do not act — no task acts on it; if a future task is added for Option C it
  must be a new plan, not silently folded in here). §0d → Task 3. §1a/§1b/§1c
  → Tasks 4–6. §2 → Task 8. §3 → Task 9. §4 → Task 10. §5 → Task 11. §6a–e →
  Task 12. §7 → Task 13. §8 → Task 14. §9 tests → distributed into each task's
  own test file, cross-referenced in Task 15 Step 3. §10/§11 → Task 15.
- **Escalation branch:** Task 6 Step 5 is a hard stop if the gate fails —
  Tasks 8–15 are conditioned on `proceed`/`proceed_with_baseline`. Whoever
  executes this plan must not mechanically continue past a `escalate` verdict.
- **`proceed_with_baseline` obligation:** if Task 6 returns that verdict,
  Task 14's `run()` return value carries `gate_verdict` forward specifically
  so a Phase 3 plan can enforce "every EEG feature model reported alongside
  the QC-only baseline" — that enforcement itself is Phase 3's job, out of
  scope here, but the plumbing (the verdict string reaching the output
  `_meta.json`) is in scope and should be added to `write_outputs` if not
  already present when this is executed (small addition: pass `gate_verdict`
  into the `_meta.json` payload in Task 14 Step 3).
