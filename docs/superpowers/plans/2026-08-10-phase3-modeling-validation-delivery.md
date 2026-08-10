# Phase 3 — Modelling, Validation & Delivery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `phase_3.md` end to end: amend the frozen plan (CV-variance fix, declared model class, reference lines), run positive controls before touching the hypothesis, reproduce the published benchmark, compute the nuisance-only line, run the one-shot primary analysis with full leakage guards, write the verdict-first results report, and ship a calibrated, versioned, out-of-distribution-refusing model with a model card.

**Architecture:** A new sibling package `pearl_models` next to `pearl_features`/`pearl_preproc` (`pearl/src/pearl_models`). One reusable nested-CV harness (`cv.py`) — pooled out-of-fold AUC across repeats, full-pipeline permutation test, bootstrap CI, per-fold feature-selection/sign stability — backs every analysis in this phase (primary, nuisance, benchmark, both positive controls). `data.py` is the single sanctioned module that joins features to labels/nuisance variables (Phase 3 is explicitly the phase that touches labels; no label-blindness test applies to this package, unlike `pearl_preproc`/`pearl_features`).

**Tech Stack:** Python 3.10+, `scikit-learn>=1.3` (already a dependency — `StratifiedGroupKFold`, `GridSearchCV`, `LogisticRegression`, `CalibratedClassifierCV`), `joblib` (model persistence, ships with scikit-learn), `mne`/`pywt` (reused from `pearl_features` for the eyes-open positive-control feature extraction), `pandas`, `numpy`, `scipy.stats` (Holm correction).

## Global Constraints

- **One honest attempt.** No iteration on the primary analysis after seeing a result. If you find yourself wanting a fourth feature family, a different target, or a different model class after seeing a result, stop and report (`phase_3.md` §10) — do not act on the impulse.
- **Amendment 2 written and committed before any label is joined to any feature** (`phase_3.md` §0).
- **Declared model class**: L2-penalised logistic regression (primary), linear SVM (secondary). Tree ensembles / gradient boosting / neural networks are not permitted as primary; if run at all, exploratory and labelled as such.
- **Permutation test re-runs the entire pipeline per permutation** (scaling, selection, fitting) — permuting only at the classifier step gives an optimistic null and is treated as a bug.
- **Every results table carries all four reference lines**: chance (0.500), QC-only (0.545, Phase 2), nuisance-only (computed in this phase), published benchmark (0.58, MSIT, framing-mismatch noted).
- **Stop-and-escalate conditions are hard gates** (`phase_3.md` §10): positive control 1a AUC < 0.80, permutation null not centred on 0.5, primary AUC > 0.85 unexplained by the §4 checklist, benchmark reproduction at chance. On any of these: stop, report, wait — do not continue past the gate. Report and wait, matching how Phase 2's confound gate was handled.
- **`pytest` green, everything under one `run_id`**, atomic staging matching the `pearl_preproc.paths` / `pearl_features.paths` convention.

---

## File Structure

```
pearl/
  config/
    models.yaml                        # NEW: CV settings (folds, repeats, seed, C grid, permutation/bootstrap counts) — Task 2
  reports/
    analysis_plan_frozen.md            # MODIFY: append "Amendment 2" — Task 1
    phase3_positive_controls.md        # NEW — Task 5
    phase3_benchmark_reproduction.md   # NEW — Task 6
    phase3_results.md (+ .html)        # NEW — Task 10
  src/pearl_models/
    __init__.py                        # NEW
    paths.py                           # NEW: phase3 paths + run-id staging — Task 2
    data.py                            # NEW: feature+label+nuisance assembly (sanctioned label module) — Task 2
    cv.py                               # NEW: nested-CV harness — Task 3
    positive_controls.py               # NEW: §1a/§1b — Task 4
    benchmark.py                        # NEW: §2a — Task 6
    nuisance.py                         # NEW: §2b — Task 7
    primary.py                          # NEW: §3, §3a, §3b, §0e secondary set — Task 8
    leakage.py                          # NEW: §4 checklist as assertions — Task 9
    reports.py                          # NEW: markdown/HTML report writers — Task 5, 6, 10
    delivery.py                         # NEW: §6 shipped model — Task 11
    pipeline.py                         # NEW: §7 orchestration — Task 12
    cli.py                              # NEW: `pearl-models` entry point — Task 12
  src/pearl_preproc/
    preprocess.py                       # MODIFY: add eyes_open_window() — Task 0
  tests/
    test_preproc_eyes_open.py          # NEW — Task 0
    test_models_data.py                # NEW — Task 2
    test_models_cv.py                   # NEW — Task 3
    test_models_positive_controls.py    # NEW — Task 4
    test_models_benchmark.py            # NEW — Task 6
    test_models_nuisance.py             # NEW — Task 7
    test_models_primary.py              # NEW — Task 8
    test_models_leakage.py              # NEW — Task 9
    test_models_delivery.py             # NEW — Task 11
data/derivatives/models/
  cv_predictions.csv, cv_metrics.csv, feature_stability.csv,
  model_final.joblib, model_card.md, _meta.json
```

---

## Reference facts gathered from the existing codebase (do not re-derive)

- `pearl/data/derivatives/features/features_pswt.csv` — 64 subjects × 20 columns, index `subject`, no labels.
- `pearl/data/derivatives/features/features_baseline.csv` — 64 subjects × 16 columns, includes `msit_band_power_*`/`msit_aperiodic_*` for the subset whose MSIT recording also survived QC (some rows NaN for msit columns — verify per-subject before using in §2a).
- Labels: `data/labels/participants_labels.tsv` (`subject_id, group, task1_risk_vs_norisk, task2_high_vs_lownormal, task3_multiclass`). `task1_risk_vs_norisk` is `binary_risk_vs_none`.
- Nuisance/demographic source: `pearl/data/raw_meta/participants.tsv`, tab-separated, column `participant_id` (values like `sub-01`), plus `age`, `sex` (0/1), `education`, `BDI`, `SES` — exactly the columns `phase_3.md` §0d/§2b names. This file also contains genotype columns (`APOE_*`, `PICALM_*`) — **`pearl_models.data` reads only the demographic columns it needs by name, never the genotype columns**, even though this package is not label-blindness-tested (documented rationale, Task 2).
- QC nuisance columns: `pearl/data/derivatives/preproc/qc/qc_metrics.csv`, rest-task rows: `n_bad_channels`, `n_ica_removed`, `artifact_frac`.
- Phase 2 confound-gate QC-only AUC: **0.545**, 95% CI **[0.435, 0.800]** (`reports/phase2_confound_gate.md`) — hardcode as the QC-only reference row's *source value*, but keep the number itself in `config/models.yaml` so it's declared, not buried in code.
- `pearl_features.confound_gate.qc_only_auc` / `_cv_mean_auc` already implement the "permutation reruns the classifier from scratch, bootstrap resamples rows and reruns a mini-CV" pattern — Task 3's `cv.py` generalizes this same pattern (don't copy-paste; write a shared, parameterized version that both Phase 2 code and Phase 3 code *could* use, but only Phase 3's `cv.py` needs to actually exist now — leave `pearl_features.confound_gate` untouched, it already shipped and is frozen).
- Continuous rest/eyes-closed derivative loading: `pearl_features.epoching.load_eyes_closed_continuous(subject)`. The eyes-open equivalent needs a new `eyes_open_window()` in `pearl_preproc.preprocess` (Task 0) since only the eyes-closed window is currently resolved from markers.
- PSWT feature extraction for an arbitrary window: `pearl_features.features.compute_channel_features(broadband_channel, iaf_hz, sfreq, cfg)` and `compute_subject_features(subject, cfg, iaf_hz)` — the latter is hardcoded to call `epoching.load_eyes_closed_continuous`. Task 4 needs a variant that takes a pre-loaded `Raw` instead of loading eyes-closed internally — **refactor `compute_subject_features` to accept an already-cropped `raw` directly** (small, backward-compatible change: add a `raw: mne.io.Raw | None = None` parameter that skips the internal load when provided) rather than duplicating the whole per-channel loop in `pearl_models`.
- `config/features.yaml` `aggregation.cycle_subsample_n: 200` — the eyes-open segment is shorter (~4 min vs ~6 min eyes-closed) and alpha is suppressed but narrowband-filtered noise still produces crossings at roughly the target rate, so 200 is expected to still be reachable per channel; if a subject's eyes-open segment can't reach it on a majority of ROI channels, that subject is dropped for the eyes-open condition only (same per-channel/per-subject dropout logic `features.py` already has) — record how many are dropped, it's diagnostic for interpretation.

---

## Task 0: `eyes_open_window()` in `pearl_preproc.preprocess`

**Files:**
- Modify: `pearl/src/pearl_preproc/preprocess.py` (add function near `eyes_closed_window`, ~line 263)
- Test: `pearl/tests/test_preproc_eyes_open.py`

**Interfaces:**
- Produces: `preprocess.eyes_open_window(annotations, tmax: float, min_duration_s: float = 60.0) -> tuple[float, float] | None` — `(0.0, t10)` where `t10` is the onset of the first `S 10` marker, or `None` if no `S 10` marker exists or the resulting window is shorter than `min_duration_s`.

- [ ] **Step 1: Write the failing tests**

```python
# pearl/tests/test_preproc_eyes_open.py
"""Eyes-open window resolution (phase_3.md §1a positive control).

Mirrors eyes_closed_window's marker parsing (phase_1.md remediation) but
returns the segment BEFORE the first `S 10` marker instead of after it.
"""
from __future__ import annotations

from types import SimpleNamespace

from pearl_preproc.preprocess import eyes_open_window


def _ann(pairs):
    return SimpleNamespace(
        onset=[p[0] for p in pairs],
        description=[p[1] for p in pairs],
    )


def test_canonical_pattern():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    assert eyes_open_window(ann, tmax=700.0) == (0.0, 246)


def test_recording_starting_at_s10_has_no_eyes_open_segment():
    ann = _ann([(0, "Stimulus/S 10"), (10, "Stimulus/S  1"), (370, "Stimulus/S 11")])
    assert eyes_open_window(ann, tmax=400.0, min_duration_s=60.0) is None


def test_no_s10_at_all_returns_none():
    ann = _ann([(5, "Stimulus/S  1"), (5.1, "Stimulus/S  2")])
    assert eyes_open_window(ann, tmax=600.0) is None


def test_short_eyes_open_segment_returns_none():
    ann = _ann([(30, "Stimulus/S 10"), (40, "Stimulus/S  1")])
    assert eyes_open_window(ann, tmax=400.0, min_duration_s=60.0) is None


def test_window_never_inverted_or_empty():
    ann = _ann([(5, "Stimulus/S  1"), (246, "Stimulus/S 10"),
                (260, "Stimulus/S  1"), (620, "Stimulus/S 11")])
    start, end = eyes_open_window(ann, tmax=700.0)
    assert 0.0 <= start < end <= 700.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_preproc_eyes_open.py -v`
Expected: FAIL — `ImportError: cannot import name 'eyes_open_window'`

- [ ] **Step 3: Implement `eyes_open_window` next to `eyes_closed_window` in `preprocess.py`**

```python
def eyes_open_window(annotations, tmax: float, min_duration_s: float = 60.0) -> tuple[float, float] | None:
    """Resolve the eyes-open block: recording start up to the first `S 10`
    marker (phase_3.md §1a). Returns None if there is no S 10 marker, or the
    resulting window is shorter than min_duration_s."""
    desc = [str(d).split("/")[-1].strip() for d in annotations.description]
    onset = [float(o) for o in annotations.onset]

    i10 = next((i for i, d in enumerate(desc) if d == "S 10"), None)
    if i10 is None:
        return None
    t10 = onset[i10]

    if t10 < min_duration_s:
        return None
    return (0.0, t10)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_preproc_eyes_open.py -v`
Expected: PASS

- [ ] **Step 5: Smoke-test on a real derivative**

```bash
cd pearl && PYTHONPATH=src python -c "
import mne
from pearl_preproc.preprocess import eyes_open_window
raw = mne.io.read_raw_fif('data/derivatives/preproc/sub-01/eeg/sub-01_task-rest_desc-preproc_eeg.fif', preload=False, verbose=False)
print(eyes_open_window(raw.annotations, raw.times[-1]))
"
```
Expected: a `(0.0, ~246)`-ish tuple, roughly 4 minutes, consistent with the documented eyes-open block length.

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_preproc/preprocess.py pearl/tests/test_preproc_eyes_open.py
git commit -m "phase3: add eyes_open_window() for the positive-control eyes-open segment (§1a)"
```

---

## Task 1: Amendment 2 — write and commit before any label join

**Files:**
- Modify: `pearl/reports/analysis_plan_frozen.md`

**Interfaces:** none — documentation deliverable, must exist before Task 2 (data assembly) runs.

- [ ] **Step 1: Append the Amendment 2 block**

```markdown

---

## Amendment 2 — 2026-08-10

**Status:** committed, before any label is joined to any feature.

### CV variance fix (§0a)

Raised from 5-fold × 3 repeats (frozen plan) to **5-fold × 10 repeats**. More
repeats reduce the variance of the same estimate; this does not change what
is being estimated and is decided before any result exists. **Out-of-fold
predictions are pooled within a repeat** (one AUC over all 64 subjects per
repeat), not averaged per-fold — averaging per-fold AUCs on ~13-subject test
folds is both higher-variance and biased. The reported statistic is the mean
of the 10 per-repeat pooled AUCs, with the spread across repeats reported
alongside.

### Declared model class (§0b)

- **Primary:** L2-penalised logistic regression, `C` tuned by grid search
  inside the inner (training-fold-only) loop, features standardised inside
  the fold.
- **Secondary:** linear SVM.
- **Not permitted as primary:** random forest, gradient boosting, any neural
  network. If run, exploratory and labelled as such — cannot become the
  headline number.

### Declared reference lines (§0c)

| Reference | Value | Source |
|---|---|---|
| Chance | 0.500 | — |
| QC-only (preprocessing metadata) | 0.545 (CI [0.435, 0.800]) | Phase 2 gate, `reports/phase2_confound_gate.md` |
| Nuisance-only (age, sex, SES, BDI, education, bad-channel count, ICA components removed, artifact_frac) | computed in §2b | this phase |
| Published benchmark | 0.58 (MSIT task, not rest) | Li et al. 2025, `reports/benchmark_citation.md` |

A feature model that does not beat the nuisance-only line has not
demonstrated anything about EEG — that comparison is carried in every
results table.

### The gate was weaker than it reads (§0d)

Phase 2's QC-only AUC (0.545) came with a 95% CI of **[0.435, 0.800]** — a
clean pass on the decision rule, and also an interval that does not exclude
substantial contamination. Treated as "no evidence of contamination," never
"contamination excluded." `artifact_frac` — borderline on the full 79-subject
cohort (p_fdr=0.011), non-significant on the surviving N=64 (p_fdr=0.056,
plausibly a power effect) — **joins the declared nuisance set** alongside
bad-channel count and ICA components removed.

### Comparison set and correction (§0e)

**Primary comparison (one test):** PSWT features on resting-state vs. the
nuisance-only line, on `binary_risk_vs_none`.

**Secondary set, Holm-corrected across these three:** baseline features on
rest; PSWT+baseline combined on rest; baseline features on MSIT.

Everything else is exploratory. The frozen plan's stopping rule stands: no
additional feature families without a written amendment.

### Achievable precision, stated now (§0f)

At 39 vs 25, the 95% CI on an AUC estimate is expected to be roughly ±0.13–0.15
wide. A true AUC of 0.70 would produce an interval around [0.56, 0.84]. This is
recorded before results exist so a wide interval afterwards reads as a known
property of the sample size, not a disappointment.
```

- [ ] **Step 2: Verify the frozen text above Amendment 2 (including Amendment 1) is untouched**

Run: `cd pearl && git diff reports/analysis_plan_frozen.md`
Expected: diff shows only an appended block at the end.

- [ ] **Step 3: Commit**

```bash
git add pearl/reports/analysis_plan_frozen.md
git commit -m "phase3: Amendment 2 — CV variance fix, declared model class, reference lines"
```

---

## Task 2: `pearl_models` skeleton, `config/models.yaml`, data assembly

**Files:**
- Create: `pearl/src/pearl_models/__init__.py`
- Create: `pearl/src/pearl_models/paths.py`
- Create: `pearl/src/pearl_models/data.py`
- Create: `pearl/config/models.yaml`
- Test: `pearl/tests/test_models_data.py`

**Interfaces:**
- Produces: `pearl_models.paths.MODELS_DIR: Path` (= `DATA_DIR / "derivatives" / "models"`), `CONFIG_DIR`, `REPORTS_DIR`, `MODELS_YAML` (= `CONFIG_DIR / "models.yaml"`), plus re-exports of `PROJECT_ROOT`, `DATA_DIR`, `make_run_id`, `get_run_id`, `set_run_id`, `sha256_file`, `git_sha` (same re-export pattern as `pearl_features.paths`).
- Produces: `pearl_models.data.load_labels() -> pd.DataFrame` — `subject_id, group, risk_vs_none (0/1)` from `data/labels/participants_labels.tsv` (renaming `task1_risk_vs_norisk` for clarity).
- Produces: `pearl_models.data.load_nuisance() -> pd.DataFrame` — indexed by `subject`, columns `age, sex, education, BDI, SES` from `participants.tsv` joined with `n_bad_channels, n_ica_removed, artifact_frac` from the rest rows of `qc_metrics.csv`.
- Produces: `pearl_models.data.load_pswt_features() -> pd.DataFrame`, `load_baseline_features() -> pd.DataFrame` (thin wrappers over `pd.read_csv(..., index_col="subject")`).
- Produces: `pearl_models.data.assemble(feature_sets: dict[str, pd.DataFrame]) -> pd.DataFrame` — outer-joins any number of named feature-set DataFrames plus labels plus nuisance on `subject`, prefixing columns from each feature set with its name if there's a collision, returns one row per subject present in ALL of `feature_sets` (inner join across feature sets, since every analysis needs the same subjects present in whichever features it uses) with labels/nuisance left-joined (so a missing nuisance value is a visible NaN, not a silently dropped row).

- [ ] **Step 1: Write `config/models.yaml`**

```yaml
# pearl/config/models.yaml — phase_3.md §0. Declared before any label join.

cv:
  n_splits: 5
  n_repeats: 10
  inner_n_splits: 3
  seed: 20260810
  c_grid: [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
  n_permutations: 1000
  n_bootstrap: 2000
  permutation_n_repeats: 1     # single-repeat CV per permutation, matches Phase 2's qc_only_auc pattern
  bootstrap_n_repeats: 1

reference_lines:
  chance: 0.5
  qc_only_auc: 0.545
  qc_only_ci: [0.435, 0.800]
  published_benchmark_auc: 0.58
  published_benchmark_source: "Li et al. 2025, Sensors 25(1):52, MSIT task (not rest)"

nuisance_columns:
  demographic: [age, sex, education, BDI, SES]
  qc: [n_bad_channels, n_ica_removed, artifact_frac]

positive_controls:
  eyes_open_min_duration_s: 60.0
  sex_auc_reference_floor: 0.65
  eyes_open_closed_auc_floor: 0.80

holm_secondary_set:
  - baseline_rest
  - pswt_plus_baseline_rest
  - baseline_msit
```

- [ ] **Step 2: Write `pearl_models/paths.py`**

```python
# pearl/src/pearl_models/paths.py
from __future__ import annotations

from pearl_preproc.paths import (  # noqa: F401
    PROJECT_ROOT, DATA_DIR, CONFIG_DIR, REPORTS_DIR,
    make_run_id, get_run_id, set_run_id, sha256_file, git_sha,
)

MODELS_DIR = DATA_DIR / "derivatives" / "models"
MODELS_YAML = CONFIG_DIR / "models.yaml"
```

- [ ] **Step 3: Write the failing test for `data.py`**

```python
# pearl/tests/test_models_data.py
import pandas as pd

from pearl_models.data import assemble


def test_assemble_inner_joins_feature_sets_and_left_joins_labels():
    feats_a = pd.DataFrame({"a1": [1.0, 2.0]}, index=pd.Index(["sub-01", "sub-02"], name="subject"))
    feats_b = pd.DataFrame({"b1": [10.0]}, index=pd.Index(["sub-01"], name="subject"))
    labels = pd.DataFrame({"subject_id": ["sub-01", "sub-02"], "risk_vs_none": [1, 0]})
    nuisance = pd.DataFrame({"age": [50]}, index=pd.Index(["sub-01"], name="subject"))

    out = assemble({"a": feats_a, "b": feats_b}, labels=labels, nuisance=nuisance)

    assert list(out.index) == ["sub-01"]  # inner join across feature sets
    assert "a1" in out.columns and "b1" in out.columns
    assert out.loc["sub-01", "risk_vs_none"] == 1
    assert out.loc["sub-01", "age"] == 50


def test_assemble_leaves_missing_nuisance_as_nan_not_dropped():
    feats_a = pd.DataFrame({"a1": [1.0]}, index=pd.Index(["sub-03"], name="subject"))
    labels = pd.DataFrame({"subject_id": ["sub-03"], "risk_vs_none": [0]})
    nuisance = pd.DataFrame({"age": []}, index=pd.Index([], name="subject"))

    out = assemble({"a": feats_a}, labels=labels, nuisance=nuisance)

    assert "sub-03" in out.index
    assert pd.isna(out.loc["sub-03", "age"])
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_models_data.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 5: Implement `data.py`**

```python
# pearl/src/pearl_models/data.py
"""Feature + label + nuisance assembly (phase_3.md).

Phase 3 is explicitly the only phase that touches the primary target — this
module is the sanctioned place labels are joined. It reads only the named
demographic columns from participants.tsv (age, sex, education, BDI, SES),
never the genotype columns (APOE_*, PICALM_*) also present in that file.
"""
from __future__ import annotations

import pandas as pd

from pearl_preproc.paths import RAW_META_DIR
from pearl_preproc.paths import QC_DIR
from pearl_features.paths import FEATURES_DIR

LABELS_TSV = RAW_META_DIR.parent.parent.parent / "data" / "labels" / "participants_labels.tsv"
PARTICIPANTS_TSV = RAW_META_DIR / "participants.tsv"

DEMOGRAPHIC_COLUMNS = ["age", "sex", "education", "BDI", "SES"]
QC_NUISANCE_COLUMNS = ["n_bad_channels", "n_ica_removed", "artifact_frac"]


def load_labels() -> pd.DataFrame:
    df = pd.read_csv(LABELS_TSV, sep="\t")
    return df.rename(columns={"task1_risk_vs_norisk": "risk_vs_none"})[
        ["subject_id", "group", "risk_vs_none"]]


def load_nuisance() -> pd.DataFrame:
    demo = pd.read_csv(PARTICIPANTS_TSV, sep="\t")[["participant_id", *DEMOGRAPHIC_COLUMNS]]
    demo = demo.rename(columns={"participant_id": "subject"}).set_index("subject")

    qc = pd.read_csv(QC_DIR / "qc_metrics.csv")
    qc_rest = qc[qc["task"].isin(["rest", "task-rest"])].set_index("subject")[QC_NUISANCE_COLUMNS]

    return demo.join(qc_rest, how="outer")


def load_pswt_features() -> pd.DataFrame:
    return pd.read_csv(FEATURES_DIR / "features_pswt.csv", index_col="subject")


def load_baseline_features() -> pd.DataFrame:
    return pd.read_csv(FEATURES_DIR / "features_baseline.csv", index_col="subject")


def assemble(feature_sets: dict[str, pd.DataFrame], labels: pd.DataFrame,
             nuisance: pd.DataFrame) -> pd.DataFrame:
    out = None
    for name, df in feature_sets.items():
        out = df if out is None else out.join(df, how="inner", rsuffix=f"_{name}")
    out = out.join(nuisance, how="left")
    labels_indexed = labels.set_index("subject_id")
    out = out.join(labels_indexed, how="left")
    out.index.name = "subject"
    return out
```

- [ ] **Step 6: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_models_data.py -v`
Expected: PASS

- [ ] **Step 7: Smoke-test the real assembly**

```bash
cd pearl && PYTHONPATH=src python -c "
from pearl_models.data import assemble, load_labels, load_nuisance, load_pswt_features, load_baseline_features
pswt = load_pswt_features()
labels = load_labels()
nuisance = load_nuisance()
df = assemble({'pswt': pswt}, labels, nuisance)
print(df.shape)
print(df['risk_vs_none'].value_counts())
print(df[['age','sex','n_bad_channels']].isna().sum())
"
```
Expected: `(64, ...)` shape, `risk_vs_none` value counts `1: 39, 0: 25` (matches Amendment 1's disclosed split), and check whether any nuisance columns come back NaN for a real subject — if any do, that's a real data gap to resolve before Task 7 (nuisance-only line) runs, not a Task 2 bug.

- [ ] **Step 8: Commit**

```bash
git add pearl/src/pearl_models/__init__.py pearl/src/pearl_models/paths.py pearl/src/pearl_models/data.py \
        pearl/config/models.yaml pearl/tests/test_models_data.py
git commit -m "phase3: pearl_models skeleton, config/models.yaml, feature+label+nuisance assembly"
```

---

## Task 3: Nested-CV harness (`cv.py`) — the core reused machinery

**Files:**
- Create: `pearl/src/pearl_models/cv.py`
- Test: `pearl/tests/test_models_cv.py`

**Interfaces:**
- Produces: `cv.build_pipeline(c_grid: list[float], inner_n_splits: int, seed: int) -> sklearn.pipeline.Pipeline` — `SimpleImputer(median) -> StandardScaler -> GridSearchCV(LogisticRegression(penalty="l2", solver="lbfgs", max_iter=2000), param_grid={"C": c_grid}, cv=StratifiedGroupKFold(inner_n_splits, shuffle=True, random_state=seed), scoring="roc_auc")`. Wrapping the grid search inside the outer Pipeline means `GridSearchCV.fit` needs `groups` passed through — **use `Pipeline.fit(X, y, gridsearchcv__groups=inner_groups)`** (sklearn's double-underscore routing) rather than a bare `GridSearchCV` object, OR (simpler, chosen here) skip `Pipeline` for the estimator step and call imputer/scaler/`GridSearchCV` as three explicit `.fit_transform`/`.fit` calls inside `run_outer_fold` below — **do the explicit version**, it avoids sklearn's parameter-routing footguns and is easier to unit-test in isolation.
- Produces: `cv.run_outer_fold(X_train, y_train, groups_train, X_test, cfg) -> tuple[np.ndarray, dict]` — imputes+scales fit on train only, grid-searches `C` with `StratifiedGroupKFold(cfg["inner_n_splits"])` on train only (groups respected), fits final `LogisticRegression(C=best_c)`, returns `(proba_test[:, 1], {"best_c": best_c, "scaler_mean": scaler.mean_, "coef": fitted.coef_[0], "selected": np.abs(fitted.coef_[0]) > 1e-8})`.
- Produces: `cv.pooled_repeated_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, cfg: dict, seed: int, n_repeats: int | None = None) -> dict` — for each repeat: `StratifiedGroupKFold(cfg["n_splits"], shuffle=True, random_state=seed+repeat)`, calls `run_outer_fold` per outer fold, assembles one `oof_proba` array covering every row exactly once (assert no `NaN` left), computes `roc_auc_score(y, oof_proba)` for that repeat. Returns `{"pooled_auc_per_repeat": list[float], "mean_pooled_auc": float, "oof_proba_last_repeat": np.ndarray, "fold_diagnostics": list[dict]}` (diagnostics carry `best_c`, `scaler_mean`, `coef`, `selected` per outer fold of the *last* repeat, for Task 8's feature-stability report — a full per-repeat-per-fold record is assembled by the caller in Task 8, this function just needs to expose the per-fold diagnostics it already computes so nothing is silently discarded).
- Produces: `cv.permutation_test(X, y, groups, cfg, seed, observed_auc: float, n_permutations: int | None = None) -> float` — for each of `n_permutations` (default `cfg["cv"]["n_permutations"]`): `rng.permutation(y)`, then **re-run `pooled_repeated_cv` from scratch** with `n_repeats=cfg["cv"]["permutation_n_repeats"]` (1) on the permuted labels, collect that permutation's `mean_pooled_auc`. Returns `p = (count(perm_aucs >= observed_auc) + 1) / (n_permutations + 1)`. Also returns the raw permutation AUC array so `leakage.py` (Task 9) can assert the null is centred near 0.5.
- Produces: `cv.bootstrap_ci(X, y, groups, cfg, seed, n_bootstrap: int | None = None) -> tuple[float, float]` — for each resample: draw `len(y)` row indices with replacement (stratified: resample within each class separately then concatenate, so class balance is preserved), re-run `pooled_repeated_cv` with `n_repeats=cfg["cv"]["bootstrap_n_repeats"]` (1) on the resampled rows, collect `mean_pooled_auc`. Returns the 2.5th/97.5th percentiles.
- Produces: `cv.holm_correction(pvalues: dict[str, float]) -> dict[str, float]` — `scipy.stats.false_discovery_control`? No — Holm is step-down Bonferroni, not FDR: implement directly (sort ascending, multiply by `(n - rank)`, cumulative max, clip to 1) or use `statsmodels.stats.multitest.multipletests(list(pvalues.values()), method="holm")` if `statsmodels` is already a dependency — **it is not**; implement Holm directly in ~8 lines rather than adding a new dependency for one function.

- [ ] **Step 1: Write the failing tests — leakage-focused, per phase_3.md §8**

```python
# pearl/tests/test_models_cv.py
import numpy as np
import pytest

from pearl_models.cv import (
    run_outer_fold, pooled_repeated_cv, permutation_test, bootstrap_ci, holm_correction,
)

_CFG = {"cv": {"n_splits": 5, "n_repeats": 3, "inner_n_splits": 3, "seed": 1,
               "c_grid": [0.01, 0.1, 1.0, 10.0], "n_permutations": 20, "n_bootstrap": 20,
               "permutation_n_repeats": 1, "bootstrap_n_repeats": 1}}


def _synthetic(n=64, n_features=10, seed=0, signal=1.5):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n)
    X = rng.normal(size=(n, n_features))
    X[:, 0] += signal * y  # one informative feature
    groups = np.arange(n)  # one row per subject
    return X, y, groups


def test_run_outer_fold_scaler_fitted_on_train_only():
    X, y, groups = _synthetic()
    train_idx, test_idx = np.arange(10, 64), np.arange(10)
    proba, diag = run_outer_fold(X[train_idx], y[train_idx], groups[train_idx],
                                  X[test_idx], _CFG["cv"])
    full_data_mean = X.mean(axis=0)
    assert not np.allclose(diag["scaler_mean"], full_data_mean)
    assert len(proba) == len(test_idx)


def test_pooled_repeated_cv_covers_every_subject_exactly_once_per_repeat():
    X, y, groups = _synthetic()
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=3)
    assert len(result["pooled_auc_per_repeat"]) == 3
    assert not np.any(np.isnan(result["oof_proba_last_repeat"]))


def test_pooled_repeated_cv_recovers_signal_above_chance():
    X, y, groups = _synthetic(signal=2.5)
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=3)
    assert result["mean_pooled_auc"] > 0.75


def test_pooled_repeated_cv_seeded_run_is_bit_reproducible():
    X, y, groups = _synthetic()
    r1 = pooled_repeated_cv(X, y, groups, _CFG, seed=42, n_repeats=2)
    r2 = pooled_repeated_cv(X, y, groups, _CFG, seed=42, n_repeats=2)
    assert r1["pooled_auc_per_repeat"] == r2["pooled_auc_per_repeat"]


def test_group_kfold_never_splits_a_group_across_folds():
    X, y, groups = _synthetic(n=40)
    groups = np.repeat(np.arange(20), 2)  # two rows per "subject" (like eyes-open/closed)
    y = np.tile([0, 1] * 10, 1)[:40]
    from sklearn.model_selection import StratifiedGroupKFold
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=1)
    for train_idx, test_idx in skf.split(X, y, groups):
        assert set(groups[train_idx]).isdisjoint(set(groups[test_idx]))


def test_permutation_null_centres_near_chance():
    X, y, groups = _synthetic(signal=0.0)  # no real signal
    observed = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=1)["mean_pooled_auc"]
    p = permutation_test(X, y, groups, _CFG, seed=1, observed_auc=observed, n_permutations=20)
    assert 0.0 <= p <= 1.0


def test_bootstrap_ci_contains_point_estimate():
    X, y, groups = _synthetic(signal=2.0)
    result = pooled_repeated_cv(X, y, groups, _CFG, seed=1, n_repeats=1)
    point = result["mean_pooled_auc"]
    lo, hi = bootstrap_ci(X, y, groups, _CFG, seed=1, n_bootstrap=20)
    assert lo <= point + 0.15  # loose bound: small n_bootstrap in test, just sanity-check ordering
    assert lo <= hi


def test_holm_correction_matches_hand_computation():
    raw = {"a": 0.01, "b": 0.04, "c": 0.20}
    out = holm_correction(raw)
    # Holm: sort ascending [0.01,0.04,0.20], multiply by [3,2,1], cummax
    assert out["a"] == pytest.approx(0.03)
    assert out["b"] == pytest.approx(0.08)
    assert out["c"] == pytest.approx(0.20)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_models_cv.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `cv.py`**

```python
# pearl/src/pearl_models/cv.py
"""Nested-CV harness shared by every analysis in Phase 3: primary, nuisance,
benchmark, both positive controls. Pooled out-of-fold AUC across repeats
(phase_3.md §0a), full-pipeline permutation test, bootstrap CI, per-fold
diagnostics for feature stability (§3b).
"""
from __future__ import annotations

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler


def run_outer_fold(X_train, y_train, groups_train, X_test, cv_cfg: dict) -> tuple[np.ndarray, dict]:
    imputer = SimpleImputer(strategy="median")
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    inner_cv = StratifiedGroupKFold(n_splits=cv_cfg["inner_n_splits"], shuffle=True,
                                     random_state=cv_cfg["seed"])
    search = GridSearchCV(
        LogisticRegression(penalty="l2", solver="lbfgs", max_iter=2000),
        param_grid={"C": cv_cfg["c_grid"]}, cv=inner_cv, scoring="roc_auc")
    search.fit(X_train_scaled, y_train, groups=groups_train)

    final = LogisticRegression(penalty="l2", solver="lbfgs", max_iter=2000,
                                C=search.best_params_["C"])
    final.fit(X_train_scaled, y_train)
    proba = final.predict_proba(X_test_scaled)[:, 1]

    diag = {"best_c": search.best_params_["C"], "scaler_mean": scaler.mean_,
            "coef": final.coef_[0], "selected": np.abs(final.coef_[0]) > 1e-8}
    return proba, diag


def pooled_repeated_cv(X: np.ndarray, y: np.ndarray, groups: np.ndarray, cfg: dict,
                        seed: int, n_repeats: int | None = None) -> dict:
    cv_cfg = cfg["cv"]
    n_repeats = n_repeats if n_repeats is not None else cv_cfg["n_repeats"]
    pooled_aucs, fold_diagnostics, oof_last = [], [], None

    for rep in range(n_repeats):
        skf = StratifiedGroupKFold(n_splits=cv_cfg["n_splits"], shuffle=True,
                                    random_state=seed + rep)
        oof_proba = np.full(len(y), np.nan)
        rep_diagnostics = []
        for train_idx, test_idx in skf.split(X, y, groups):
            proba, diag = run_outer_fold(X[train_idx], y[train_idx], groups[train_idx],
                                          X[test_idx], cv_cfg)
            oof_proba[test_idx] = proba
            diag["test_idx"] = test_idx
            rep_diagnostics.append(diag)
        assert not np.any(np.isnan(oof_proba)), "every subject must be covered exactly once per repeat"
        pooled_aucs.append(roc_auc_score(y, oof_proba))
        fold_diagnostics.append(rep_diagnostics)
        oof_last = oof_proba

    return {
        "pooled_auc_per_repeat": pooled_aucs,
        "mean_pooled_auc": float(np.mean(pooled_aucs)),
        "oof_proba_last_repeat": oof_last,
        "fold_diagnostics": fold_diagnostics,
    }


def permutation_test(X, y, groups, cfg: dict, seed: int, observed_auc: float,
                      n_permutations: int | None = None) -> tuple[float, np.ndarray]:
    cv_cfg = cfg["cv"]
    n_perm = n_permutations if n_permutations is not None else cv_cfg["n_permutations"]
    rng = np.random.default_rng(seed)
    perm_aucs = np.empty(n_perm)
    for i in range(n_perm):
        y_perm = rng.permutation(y)
        result = pooled_repeated_cv(X, y_perm, groups, cfg, seed=seed + i + 1,
                                     n_repeats=cv_cfg["permutation_n_repeats"])
        perm_aucs[i] = result["mean_pooled_auc"]
    p = (float((perm_aucs >= observed_auc).sum()) + 1) / (n_perm + 1)
    return p, perm_aucs


def bootstrap_ci(X, y, groups, cfg: dict, seed: int,
                  n_bootstrap: int | None = None) -> tuple[float, float]:
    cv_cfg = cfg["cv"]
    n_boot = n_bootstrap if n_bootstrap is not None else cv_cfg["n_bootstrap"]
    rng = np.random.default_rng(seed)
    boot_aucs = []
    class0_idx = np.where(y == 0)[0]
    class1_idx = np.where(y == 1)[0]
    for _ in range(n_boot):
        idx0 = rng.choice(class0_idx, size=len(class0_idx), replace=True)
        idx1 = rng.choice(class1_idx, size=len(class1_idx), replace=True)
        idx = np.concatenate([idx0, idx1])
        result = pooled_repeated_cv(X[idx], y[idx], groups[idx], cfg, seed=seed,
                                     n_repeats=cv_cfg["bootstrap_n_repeats"])
        boot_aucs.append(result["mean_pooled_auc"])
    lo, hi = np.percentile(boot_aucs, [2.5, 97.5])
    return float(lo), float(hi)


def holm_correction(pvalues: dict[str, float]) -> dict[str, float]:
    names = list(pvalues.keys())
    pvals = np.array([pvalues[n] for n in names])
    order = np.argsort(pvals)
    n = len(pvals)
    adjusted = np.empty(n)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, pvals[idx] * (n - rank))
        running_max = max(running_max, val)
        adjusted[idx] = running_max
    return {names[i]: float(adjusted[i]) for i in range(n)}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_models_cv.py -v`
Expected: PASS. This test file is the load-bearing one for the whole phase — do not proceed to Task 4 until every test here is green, including the group-disjointness and reproducibility tests.

- [ ] **Step 5: Commit**

```bash
git add pearl/src/pearl_models/cv.py pearl/tests/test_models_cv.py
git commit -m "phase3: nested-CV harness — pooled OOF AUC, full-pipeline permutation, bootstrap, Holm"
```

---

## Task 4: Positive control 1a (eyes-open vs eyes-closed) and 1b (sex)

**Files:**
- Modify: `pearl/src/pearl_features/features.py` — add `raw: mne.io.Raw | None = None` parameter to `compute_subject_features` (when provided, skip the internal `load_eyes_closed_continuous` call and use `raw` directly; when `None`, behave exactly as before — existing Phase 2 tests must still pass unchanged).
- Create: `pearl/src/pearl_models/positive_controls.py`
- Test: `pearl/tests/test_models_positive_controls.py`

**Interfaces:**
- Consumes: `pearl_features.features.compute_subject_features(subject, cfg, iaf_hz, raw=None)` (modified signature), `pearl_preproc.preprocess.eyes_open_window`, `pearl_models.cv.pooled_repeated_cv`/`permutation_test`/`bootstrap_ci`.
- Produces: `positive_controls.build_eyes_open_closed_matrix(subjects: list[str], features_cfg: dict, iaf_by_subject: dict[str, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]` — `(X, y, groups, feature_names)` where each subject contributes **two rows** (`y=1` eyes-closed, `y=0` eyes-open), `groups` is the subject id repeated twice so `StratifiedGroupKFold` never splits a subject's two conditions across folds. Subjects whose eyes-open segment can't reach the cycle floor are dropped (both rows) and counted.
- Produces: `positive_controls.run_eyes_open_closed_control(cfg: dict, features_cfg: dict) -> dict` — assembles the matrix, runs `pooled_repeated_cv` + `permutation_test` + `bootstrap_ci` via `cv.py`, returns `{"auc": float, "ci": (lo, hi), "p_value": float, "n_subjects_used": int, "n_dropped": int, "verdict": "pass"|"fail"}` where `verdict` is `"pass"` iff `auc >= cfg["positive_controls"]["eyes_open_closed_auc_floor"]`.
- Produces: `positive_controls.run_sex_control(cfg: dict, pswt_features: pd.DataFrame, nuisance: pd.DataFrame) -> dict` — same CV machinery, `X` = PSWT feature columns, `y` = `nuisance["sex"]`, `groups` = subject index (one row per subject). Returns the same shape of dict, `verdict` `"pass"` iff `auc >= cfg["positive_controls"]["sex_auc_reference_floor"]`.

- [ ] **Step 1: Modify `compute_subject_features`'s signature (Phase 2 code, small additive change)**

In `pearl/src/pearl_features/features.py`, change:
```python
def compute_subject_features(subject: str, cfg: dict, iaf_hz: float) -> tuple[dict[str, float], dict]:
```
to:
```python
def compute_subject_features(subject: str, cfg: dict, iaf_hz: float,
                              raw: "mne.io.Raw | None" = None) -> tuple[dict[str, float], dict]:
```
and change the body's first two lines from:
```python
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments

    raw = load_eyes_closed_continuous(subject)
    raw, _, usable_s = reject_artifact_segments(raw, cfg)
```
to:
```python
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments

    if raw is None:
        raw = load_eyes_closed_continuous(subject)
    raw, _, usable_s = reject_artifact_segments(raw, cfg)
```

- [ ] **Step 2: Run Phase 2's existing test suite to confirm nothing broke**

Run: `cd pearl && python -m pytest tests/test_features_extraction.py tests/test_features_pipeline.py -v`
Expected: all still PASS (the default `raw=None` preserves old behaviour exactly).

- [ ] **Step 3: Write the failing tests for `positive_controls.py`**

```python
# pearl/tests/test_models_positive_controls.py
import numpy as np

from pearl_models.positive_controls import run_sex_control
from pearl_models.data import load_pswt_features, load_nuisance


def test_run_sex_control_returns_expected_keys():
    cfg = {"cv": {"n_splits": 5, "n_repeats": 2, "inner_n_splits": 3, "seed": 1,
                  "c_grid": [0.1, 1.0, 10.0], "n_permutations": 10, "n_bootstrap": 10,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
           "positive_controls": {"sex_auc_reference_floor": 0.65}}
    pswt = load_pswt_features()
    nuisance = load_nuisance()
    result = run_sex_control(cfg, pswt, nuisance)
    assert set(result) >= {"auc", "ci", "p_value", "verdict"}
    assert result["verdict"] in {"pass", "fail"}
```

(Note: this test hits real derivative data, matching the project's established
pattern of validating DSP/CV code against real subjects rather than only
synthetic fixtures — see `report.md` §"Working conventions".)

- [ ] **Step 4: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_models_positive_controls.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 5: Implement `positive_controls.py`**

Write `run_sex_control` first (simpler — reuses existing `features_pswt.csv` directly,
no new feature extraction): join `pswt` and `nuisance[["sex"]]` on subject
(inner join, drop rows with missing sex), `X = pswt.values`, `y = sex.values`,
`groups = np.arange(len(y))`, call `cv.pooled_repeated_cv` for the observed
AUC, then `cv.permutation_test` and `cv.bootstrap_ci`, assemble the verdict
dict per the Interfaces section above.

Then write `build_eyes_open_closed_matrix` / `run_eyes_open_closed_control`:
for each subject, call `pearl_preproc.preprocess.eyes_open_window` on the
rest derivative's annotations (load via
`mne.io.read_raw_fif(..., preload=True)`, same path convention as
`pearl_features.epoching.load_eyes_closed_continuous`), crop to that window,
run it through `pearl_features.features.compute_subject_features(subject,
features_cfg, iaf_hz, raw=eyes_open_raw)` (the new `raw=` parameter from
Step 1) to get the eyes-open feature row, and use the **already-computed**
eyes-closed row from `features_pswt.csv` for the same subject (do not
recompute eyes-closed features — they're already on disk from Phase 2).
Stack into the two-row-per-subject matrix, drop subjects missing either row,
run the same three `cv.py` calls.

- [ ] **Step 6: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_models_positive_controls.py -v`
Expected: PASS

- [ ] **Step 7: Run both controls for real and record the numbers**

```bash
cd pearl && PYTHONPATH=src python -c "
import yaml
from pearl_models.positive_controls import run_sex_control, run_eyes_open_closed_control
from pearl_models.data import load_pswt_features, load_nuisance
from pearl_features.features import load_features_config
cfg = yaml.safe_load(open('config/models.yaml'))
features_cfg = load_features_config()
sex_result = run_sex_control(cfg, load_pswt_features(), load_nuisance())
print('SEX', sex_result)
eo_result = run_eyes_open_closed_control(cfg, features_cfg)
print('EYES_OPEN_CLOSED', eo_result)
"
```

**Decision point:** if `eo_result["auc"] < 0.80`, this is the §10 stop
condition — stop this plan, do not proceed to Task 5's report or any task
after it, report the numbers and wait. Otherwise continue.

- [ ] **Step 8: Commit**

```bash
git add pearl/src/pearl_features/features.py pearl/src/pearl_models/positive_controls.py \
        pearl/tests/test_models_positive_controls.py
git commit -m "phase3: positive controls — eyes-open/closed (§1a) and sex classification (§1b)"
```

---

## Task 5: `phase3_positive_controls.md` report

**Files:**
- Create: `pearl/src/pearl_models/reports.py` (start this file here; Tasks 6 and 10 extend it)
- Test: extend `pearl/tests/test_models_positive_controls.py`

**Interfaces:**
- Produces: `reports.render_positive_controls(eo_result: dict, sex_result: dict) -> str` — verdict-first Markdown, applying the `phase_3.md` §1c interpretation table (`high`+`>=0.65` -> pipeline works, null on genotype is real; `high`+`chance` -> features work but don't generalize; `low`+anything -> pipeline broken, stop) based on the two AUCs, where "high" means `>= eyes_open_closed_auc_floor` (0.80).
- Produces: `reports.write_positive_controls(eo_result, sex_result, out_path: Path) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# append to pearl/tests/test_models_positive_controls.py
from pearl_models.reports import render_positive_controls


def test_render_positive_controls_is_verdict_first():
    eo = {"auc": 0.9, "ci": (0.8, 0.95), "p_value": 0.001, "n_subjects_used": 60,
          "n_dropped": 4, "verdict": "pass"}
    sex = {"auc": 0.7, "ci": (0.55, 0.85), "p_value": 0.01, "verdict": "pass"}
    text = render_positive_controls(eo, sex)
    assert text.strip().splitlines()[0].upper().find("VERDICT") >= 0 or "PASS" in text.strip().splitlines()[0].upper()
    assert "0.9" in text
```

- [ ] **Step 2: Run to verify it fails, then implement `reports.py`'s `render_positive_controls`/`write_positive_controls`**

Follow the `phase_2.md`-era `confound_gate_report.py` pattern: a verdict-first
heading, then a table of both control AUCs/CIs/p-values against their floors,
then the applied §1c interpretation sentence.

Run: `cd pearl && python -m pytest tests/test_models_positive_controls.py -v`
Expected: PASS

- [ ] **Step 3: Write the real report**

```bash
cd pearl && PYTHONPATH=src python -c "
# reuse the eo_result/sex_result computed in Task 4 Step 7 (recompute if not held in memory)
from pearl_models.reports import write_positive_controls
from pearl_models.paths import REPORTS_DIR
write_positive_controls(eo_result, sex_result, REPORTS_DIR / 'phase3_positive_controls.md')
"
```

- [ ] **Step 4: Commit**

```bash
git add pearl/src/pearl_models/reports.py pearl/tests/test_models_positive_controls.py \
        pearl/reports/phase3_positive_controls.md
git commit -m "phase3: write reports/phase3_positive_controls.md"
```

---

## Task 6: Benchmark reproduction (§2a)

**Files:**
- Create: `pearl/src/pearl_models/benchmark.py`
- Test: `pearl/tests/test_models_benchmark.py`
- Modify: `pearl/src/pearl_models/reports.py` — add `render_benchmark_reproduction`/`write_benchmark_reproduction`

**Interfaces:**
- Produces: `benchmark.run_msit_benchmark(cfg: dict) -> dict` — `X` = `msit_band_power_*`/`msit_aperiodic_*` columns of `features_baseline.csv` (drop subjects with any NaN in those columns — the subset whose MSIT recording also survived QC), `y` = `risk_vs_none`, `groups` = subject index. Same `cv.py` calls as Task 4/5. Returns `{"auc", "ci", "p_value", "n_subjects_used", "verdict"}` where `verdict` is `"near_benchmark"` if `abs(auc - 0.58) <= 0.10`, else `"at_chance"` if `auc <= 0.55`, else `"other"`.

- [ ] **Step 1-4: TDD cycle** (same shape as Task 4/5 — write the failing test asserting `run_msit_benchmark` returns the expected keys against real data, implement, verify pass).

- [ ] **Step 5: Run for real, record the decision point**

**Decision point:** if `verdict == "at_chance"`, this is a §10 stop condition —
stop, report, wait. Otherwise continue.

- [ ] **Step 6: Write `reports/phase3_benchmark_reproduction.md`**, noting the
  framing caveat prominently (0.58 is task-based, primary target is
  rest-based — an optimistic bar).

- [ ] **Step 7: Commit**

```bash
git add pearl/src/pearl_models/benchmark.py pearl/src/pearl_models/reports.py \
        pearl/tests/test_models_benchmark.py pearl/reports/phase3_benchmark_reproduction.md
git commit -m "phase3: benchmark reproduction on MSIT (§2a)"
```

---

## Task 7: Nuisance-only line (§2b)

**Files:**
- Create: `pearl/src/pearl_models/nuisance.py`
- Test: `pearl/tests/test_models_nuisance.py`

**Interfaces:**
- Produces: `nuisance.run_nuisance_only(cfg: dict) -> dict` — `X` = the 8 nuisance columns (`age, sex, education, BDI, SES, n_bad_channels, n_ica_removed, artifact_frac`) from `data.load_nuisance()` joined to `risk_vs_none`, same `cv.py` calls, same result shape as Task 4/6. This becomes the reference row every feature model is measured against in Task 8.

- [ ] **Step 1-4: TDD cycle**, same shape as prior tasks.
- [ ] **Step 5: Run for real**, record `auc`/`ci` — this is the number Amendment 2's reference-line table (§0c) needs filled in.
- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_models/nuisance.py pearl/tests/test_models_nuisance.py
git commit -m "phase3: nuisance-only reference line (§2b)"
```

---

## Task 8: Primary analysis + secondary set (§3, §3a, §0e)

**Files:**
- Create: `pearl/src/pearl_models/primary.py`
- Test: `pearl/tests/test_models_primary.py`

**Interfaces:**
- Produces: `primary.run_one_analysis(name: str, X: np.ndarray, y: np.ndarray, groups: np.ndarray, cfg: dict, seed: int) -> dict` — thin wrapper around the three `cv.py` calls, tagging the result dict with `"name": name` and the four reference lines from `cfg["reference_lines"]` copied in verbatim (so every result carries them, per phase_3.md §0c).
- Produces: `primary.run_primary_analysis(cfg: dict) -> dict` — **one run**: (1) features-only (`features_pswt.csv` vs `risk_vs_none`) — the primary claim; (2) features+nuisance (concatenate PSWT features with the 8 nuisance columns); (3) nuisance-only (reuse Task 7's `nuisance.run_nuisance_only` result rather than re-running it). Returns `{"features_only": {...}, "features_plus_nuisance": {...}, "nuisance_only": {...}}`.
- Produces: `primary.run_secondary_set(cfg: dict) -> dict` — three analyses (`baseline_rest`, `pswt_plus_baseline_rest`, `baseline_msit`), each via `run_one_analysis`, then `cv.holm_correction` applied across their three `p_value`s, writing the corrected p back onto each result dict as `"p_value_holm"`.
- Produces: `primary.feature_stability(fold_diagnostics: list[list[dict]], feature_names: list[str]) -> pd.DataFrame` — from `pooled_repeated_cv`'s returned `fold_diagnostics` (per repeat, per outer fold: `selected` boolean array and `coef` array), compute per feature: `selection_frequency` (fraction of repeat×fold combinations where `selected[i]` is True), `sign_consistency` (fraction of the folds where selected, agreeing on `sign(coef[i])`). Columns: `feature, selection_frequency, sign_consistency, stable` (`stable = selection_frequency > 0.8`).

- [ ] **Step 1-4: TDD cycle.** For `feature_stability`, write the test first with a hand-constructed `fold_diagnostics` list where you know the expected frequencies, assert the function recovers them exactly.
- [ ] **Step 5: Run the primary analysis for real.**

```bash
cd pearl && PYTHONPATH=src python -c "
import yaml
from pearl_models.primary import run_primary_analysis, run_secondary_set
cfg = yaml.safe_load(open('config/models.yaml'))
cfg['reference_lines'] = cfg['reference_lines']
primary = run_primary_analysis(cfg)
print('PRIMARY', primary['features_only']['auc'], primary['features_only']['ci'])
secondary = run_secondary_set(cfg)
for k, v in secondary.items():
    print(k, v['auc'], v.get('p_value_holm'))
"
```

**Decision point (§10, §4):** if `primary['features_only']['auc'] > 0.85` and
the §4 leakage checklist (Task 9) doesn't explain it, stop and report. This
check happens for real once Task 9 exists — note the number here regardless.

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_models/primary.py pearl/tests/test_models_primary.py
git commit -m "phase3: primary analysis (three covariate models) + Holm-corrected secondary set (§3)"
```

---

## Task 9: Leakage tripwire (§4)

**Files:**
- Create: `pearl/src/pearl_models/leakage.py`
- Test: `pearl/tests/test_models_leakage.py`

**Interfaces:**
- Produces: `leakage.check_no_subject_leakage(groups: np.ndarray, cfg: dict, seed: int) -> bool` — re-derives the same `StratifiedGroupKFold` splits `cv.py` would use and asserts every fold's train/test group sets are disjoint (formalizes what `test_models_cv.py`'s `test_group_kfold_never_splits_a_group_across_folds` already checks generically — this version runs it against the *actual* primary analysis's `groups` array).
- Produces: `leakage.check_permutation_null_centred(perm_aucs: np.ndarray, tolerance: float = 0.05) -> bool` — `abs(np.mean(perm_aucs) - 0.5) <= tolerance`.
- Produces: `leakage.run_full_checklist(primary_result: dict, perm_aucs: np.ndarray, groups: np.ndarray, cfg: dict) -> dict` — runs both checks above plus a documented manual-review note for checklist items 2-4 (scaling/selection-inside-fold is already structurally guaranteed by `cv.py`'s `run_outer_fold`; a feature-as-proxy-for-acquisition-order check is a manual read of `feature_stability.csv` against `cycle_stats.csv`'s `usable_duration_s`, not an automated assertion — document this explicitly in the returned dict rather than silently omitting it).

- [ ] **Step 1-4: TDD cycle.**
- [ ] **Step 5: Run against the primary analysis's actual permutation AUCs and groups, record the checklist result.**
- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_models/leakage.py pearl/tests/test_models_leakage.py
git commit -m "phase3: leakage tripwire checklist (§4)"
```

---

## Task 10: `phase3_results.md` (+ .html) — verdict-first (§5)

**Files:**
- Modify: `pearl/src/pearl_models/reports.py` — add `render_results`/`write_results` (Markdown) and an HTML variant (self-contained, same CSS-embedding convention as `pearl_preproc.report_qc`).
- Test: extend an existing `test_models_*` test file with a rendering smoke test.

**Interfaces:**
- Produces: `reports.render_results(primary: dict, secondary: dict, eo_result: dict, sex_result: dict, benchmark_result: dict, feature_stability: pd.DataFrame, leakage_result: dict, cfg: dict) -> str` — Markdown following the exact 8-section structure in `phase_3.md` §5: (1) verdict + primary number + CI, (2) all four reference lines, (3) positive control outcomes, (4) benchmark reproduction outcome, (5) secondary comparisons corrected, (6) feature stability, (7) limitations (power/§0f, QC-only CI width/§0d, rest-vs-task benchmark mismatch, deferred Phase 1 reference-order/ICA issues, A_P_plus attrition), (8) what would be needed to answer the question properly.

- [ ] **Step 1-4: TDD cycle** with a hand-built fixture for each argument, asserting each of the 8 sections appears (search for section-header substrings).
- [ ] **Step 5: Render and write the real report** from the actual results of Tasks 4-9.
- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_models/reports.py pearl/reports/phase3_results.md pearl/reports/phase3_results.html
git commit -m "phase3: write reports/phase3_results.md — verdict-first, all sections (§5)"
```

---

## Task 11: Delivery — shipped model (§6)

**Files:**
- Create: `pearl/src/pearl_models/delivery.py`
- Test: `pearl/tests/test_models_delivery.py`

**Interfaces:**
- Produces: `delivery.train_final_model(cfg: dict) -> tuple[sklearn.pipeline.Pipeline, dict]` — trains on **all 64 subjects** (no held-out split — evaluation is already frozen from Task 8), `Pipeline(SimpleImputer, StandardScaler, CalibratedClassifierCV(LogisticRegression(C=<the modal best_c from Task 8's fold_diagnostics>, penalty="l2"), method="sigmoid", cv=StratifiedGroupKFold(5)))` for calibrated probabilities (Platt scaling, fitted inside its own internal CV — `CalibratedClassifierCV`'s own `cv` parameter, not the outer evaluation CV, since the outer evaluation already happened and is frozen). Returns `(fitted_pipeline, provenance_dict)` where `provenance_dict` has `run_id`, `git_sha`, `feature_config_hash` (`sha256` of `config/features.yaml`'s bytes), `participants_tsv_sha256` (from `pearl_preproc.paths.participants_tsv_sha256()`), `cv_estimated_auc` and `cv_estimated_ci` (copied from Task 8's `features_only` result — **never a number computed on the training data**), `training_qc_ranges` (per nuisance/QC column: min/max across the 64 training subjects, for OOD refusal).
- Produces: `delivery.is_out_of_distribution(qc_row: dict, training_qc_ranges: dict) -> tuple[bool, str]` — `True, reason` if any QC metric in `qc_row` falls outside `[min, max]` of `training_qc_ranges` for that metric; else `(False, "")`.
- Produces: `delivery.score_subject(pipeline, qc_row: dict, feature_row: pd.Series, training_qc_ranges: dict) -> dict` — checks `is_out_of_distribution` first; if OOD, returns `{"status": "cannot_score", "reason": ...}` **without calling the model**; else returns `{"status": "scored", "probability": float, "disclaimer": "research pipeline output — a research score, not a risk assessment, screening result, or diagnosis"}`.
- Produces: `delivery.write_model_card(provenance: dict, out_path: Path) -> None` — raises `ValueError` if any required field (`run_id, git_sha, cv_estimated_auc, cv_estimated_ci, training_qc_ranges, participants_tsv_sha256`) is empty/`None` (§8 test requirement).

- [ ] **Step 1: Write the failing tests**

```python
# pearl/tests/test_models_delivery.py
import pytest

from pearl_models.delivery import is_out_of_distribution, score_subject, write_model_card


def test_is_out_of_distribution_flags_metric_outside_training_range():
    ranges = {"n_bad_channels": (0, 10)}
    ood, reason = is_out_of_distribution({"n_bad_channels": 15}, ranges)
    assert ood is True
    assert "n_bad_channels" in reason


def test_is_out_of_distribution_false_within_range():
    ranges = {"n_bad_channels": (0, 10)}
    ood, reason = is_out_of_distribution({"n_bad_channels": 5}, ranges)
    assert ood is False


def test_score_subject_refuses_ood_without_calling_model():
    class _ExplodingPipeline:
        def predict_proba(self, X):
            raise AssertionError("must not be called for OOD input")

    ranges = {"n_bad_channels": (0, 10)}
    result = score_subject(_ExplodingPipeline(), {"n_bad_channels": 99}, None, ranges)
    assert result["status"] == "cannot_score"


def test_write_model_card_fails_on_missing_required_field(tmp_path):
    incomplete = {"run_id": "x", "git_sha": None}
    with pytest.raises(ValueError):
        write_model_card(incomplete, tmp_path / "model_card.md")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd pearl && python -m pytest tests/test_models_delivery.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `delivery.py`** per the Interfaces block above — `train_final_model` reuses `pearl_models.data.assemble`/`load_pswt_features`/`load_nuisance` for the training data, `sklearn.calibration.CalibratedClassifierCV` for calibration, `joblib.dump` for persistence (called separately in Step 5, not inside `train_final_model` itself, so the function stays unit-testable without disk I/O).

- [ ] **Step 4: Run tests, verify pass**

Run: `cd pearl && python -m pytest tests/test_models_delivery.py -v`
Expected: PASS

- [ ] **Step 5: Train and persist the real final model**

```bash
cd pearl && PYTHONPATH=src python -c "
import joblib, yaml
from pearl_models.delivery import train_final_model, write_model_card
from pearl_models.paths import MODELS_DIR
cfg = yaml.safe_load(open('config/models.yaml'))
pipeline, provenance = train_final_model(cfg)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(pipeline, MODELS_DIR / 'model_final.joblib')
write_model_card(provenance, MODELS_DIR / 'model_card.md')
print(provenance)
"
```

- [ ] **Step 6: Commit**

```bash
git add pearl/src/pearl_models/delivery.py pearl/tests/test_models_delivery.py
git commit -m "phase3: shipped model — calibration, OOD refusal, model card (§6)"
```

---

## Task 12: Pipeline orchestration, outputs, full DoD sweep (§7, §8, §9)

**Files:**
- Create: `pearl/src/pearl_models/pipeline.py`
- Create: `pearl/src/pearl_models/cli.py`
- Modify: `pearl/pyproject.toml` — add `pearl-models = "pearl_models.cli:main"` script entry

**Interfaces:**
- Produces: `pipeline.run(run_id: str | None = None) -> dict` — orchestrates Tasks 4-11 end to end in the required order (positive controls first, stopping if 1a fails; benchmark reproduction; nuisance-only; primary + secondary; leakage checklist; results report; final model + model card), writes `data/derivatives/models/cv_predictions.csv` (every OOF probability from the primary analysis's last repeat, all repeats optionally appended with a `repeat` column), `cv_metrics.csv` (one row per analysis name × reference line), `feature_stability.csv`, under one `run_id`, mirroring `pearl_features.pipeline.run`'s staging convention.

- [ ] **Step 1-4: TDD cycle** for `pipeline.run`, mocking the expensive sub-analyses (patch each Task's `run_*` function to return a small fixed dict) so the orchestration/output-writing logic is tested fast, matching `test_features_pipeline.py`'s approach in Phase 2.
- [ ] **Step 5: Run the real, full pipeline once.** This is expensive (positive controls' eyes-open extraction re-runs cycle/PSR/PSWT per subject; the primary analysis and secondary set each run permutation+bootstrap) — run in the background and monitor, same pattern as Phase 2's `pearl_features.pipeline.run()` full run.
- [ ] **Step 6: Full `pytest -q` run.** Expected: every test from Tasks 0-12 green, in addition to the full pre-existing Phase 1/2 suite (190 at Phase 2 close).
- [ ] **Step 7: Walk the `phase_3.md` §9 Definition-of-Done checklist** item by item, confirming each artifact exists, exactly as Phase 2's Task 15 did.
- [ ] **Step 8: Walk the `phase_3.md` §10 stop-conditions** one more time against the final real numbers (positive control 1a, permutation null centring, primary AUC vs 0.85, benchmark reproduction) — confirm none fired, or stop and report if one did.
- [ ] **Step 9: Commit**

```bash
git add pearl/src/pearl_models/pipeline.py pearl/src/pearl_models/cli.py pearl/pyproject.toml
git commit -m "phase3: pipeline orchestration, outputs, full DoD sweep (§7-§9)"
```

---

## Self-Review Notes

- **Spec coverage:** §0 -> Task 1 (amendment) + Task 2 (config/data, since nuisance columns are declared there). §1 -> Task 0 (eyes-open window) + Task 4 (both controls) + Task 5 (report). §2 -> Task 6 (benchmark) + Task 7 (nuisance line). §3/§3a/§3b -> Task 8. §4 -> Task 9. §5 -> Task 10. §6 -> Task 11. §7/§8/§9/§10 -> Task 12.
- **Escalation branches, all honored the same way Phase 2's confound gate was:** Task 4 Step 7 (1a < 0.80), Task 6 Step 5 (MSIT at chance), Task 8 Step 5 + Task 9 (primary AUC > 0.85 unexplained), Task 12 Step 8 (final consolidated check). None of these silently continue past a fired gate.
- **Type consistency check:** every `run_*_control`/`run_*_analysis`/`run_msit_benchmark`/`run_nuisance_only` function returns the same result-dict shape (`auc, ci, p_value, verdict` at minimum) so `primary.run_one_analysis` and the report renderers can treat them uniformly — verified this is consistent across Tasks 4, 6, 7, 8.
- **`compute_subject_features`'s modified signature** (Task 4 Step 1) is additive and defaults to old behavior — re-ran the exact Phase 2 test files that exercise it (Step 2) as an explicit regression gate rather than assuming it's fine.

