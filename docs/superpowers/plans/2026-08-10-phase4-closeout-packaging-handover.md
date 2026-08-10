# Phase 4 — Diagnostic Closeout, Packaging & Handover — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the sex-control ambiguity (without touching the primary verdict), fix two documented feature defects, merge/tag/pin/prove reproducibility, containerize the tool, and produce the client-facing final report + handover pack.

**Architecture:** One new module (`pearl_models/control_diagnostic.py`) for Task A, small edits to `pearl_features` for Task B, a `Dockerfile` + thin `pearl_models/api.py` (Flask, stdlib-adjacent) for Task D, and documentation-only deliverables for Tasks C/E/F.

**Tech Stack:** Same stack as Phases 1–3, plus Docker for packaging, Flask (or `http.server`-based minimal API if Flask isn't already a dependency — check before adding) for the thin API.

## Global Constraints

- **The primary verdict is frozen: NULL, AUC 0.474.** Nothing in this phase may re-run the primary analysis or be presented as changing it.
- **Task A's diagnostic module must raise if pointed at `binary_risk_vs_none`** — enforced in code, not just documentation. This is the load-bearing safety property of the whole phase.
- **All three diagnostic rungs are declared in config before any run**, and all three outcomes are reported regardless of where the ladder stops.
- Dropping the two constant `h1` columns does not require re-running the primary CV (L2 logistic regression's output is invariant to removing constant columns) — state this, don't re-verify it empirically.
- Dependencies pinned exactly (`==`), not floored (`>=`), before the clean-clone reproducibility claim is made.
- Container output must always include the research-artefact disclaimer — never omit it to "look more finished."
- `pytest` green, everything under one `run_id`, by the end.

---

## Task A: Control diagnostic ladder (§0)

**Files:**
- Create: `pearl/config/control_diagnostic.yaml` — declares all 3 rungs before any run
- Create: `pearl/src/pearl_models/control_diagnostic.py`
- Test: `pearl/tests/test_models_control_diagnostic.py`

**Interfaces:**
- Produces: `control_diagnostic.ALLOWED_TARGETS = {"sex"}` — the only targets this module may run against.
- Produces: `control_diagnostic.run_rung(rung_name: str, target: str, X, y, groups, cfg) -> dict` — raises `ValueError` immediately if `target not in ALLOWED_TARGETS` (checked first, before touching `cv.py` at all). Otherwise delegates to `pearl_models.primary.run_one_analysis` (reused, not reimplemented) and tags the result with `rung_name`.
- Produces: `control_diagnostic.run_rung1_baseline(cfg) -> dict`, `run_rung2_pswt_plus_baseline(cfg) -> dict` — reuse `pearl_models.data.load_baseline_features`/`load_pswt_features`/`load_nuisance` (for `sex`), same pattern as `pearl_models.primary`/`pearl_models.positive_controls.run_sex_control`.
- Produces: `control_diagnostic.compute_per_channel_band_power(subject: str, qc_row: dict) -> dict` — fresh computation, all 127 channels (not the 15-channel occipital-parietal ROI), reusing `pearl_features.baseline.relative_band_powers`/`aperiodic_fit` with `roi_channels=raw.ch_names` (all channels) instead of the declared ROI.
- Produces: `control_diagnostic.run_rung3_per_channel(cfg) -> dict` — orchestrates the fresh per-channel extraction across the 64-subject cohort, then the same CV call.
- Produces: `control_diagnostic.run_ladder(cfg) -> dict` — runs all three rungs **unconditionally** (§0c: "report all three outcomes regardless of where you stop reading" — the code always computes all three; only the report's prose stops elaborating after the first pass), returns `{"rung1": {...}, "rung2": {...}, "rung3": {...}, "stopped_at": str | None}` where `stopped_at` names the first rung whose AUC clearly exceeds chance (say, CI lower bound > 0.55), or `None` if all three are at chance.

- [ ] **Step 1: Write `config/control_diagnostic.yaml`** declaring all three rungs, the allowed target, and the "clearly above chance" threshold (CI lower bound), before writing any code that runs them:

```yaml
# pearl/config/control_diagnostic.yaml — phase_4.md §0. Declared before any run.
target: sex   # the ONLY sanctioned target for this module — see control_diagnostic.py's hard guard
rungs:
  - name: rung1_baseline
    description: "16 spectral baseline features (features_baseline.csv, rest-task columns)"
  - name: rung2_pswt_plus_baseline
    description: "PSWT (18, post-Task-B) + baseline spectral combined"
  - name: rung3_per_channel
    description: "Per-channel (127ch) band power + 1/f, fresh computation, no ROI averaging"
clearly_above_chance_ci_low: 0.55
```

- [ ] **Step 2: Write the failing guard test first**

```python
# pearl/tests/test_models_control_diagnostic.py
import numpy as np
import pytest

from pearl_models.control_diagnostic import run_rung, ALLOWED_TARGETS


def test_run_rung_raises_on_primary_target():
    X = np.zeros((10, 3)); y = np.zeros(10, dtype=int); groups = np.arange(10)
    cfg = {"cv": {"n_splits": 2, "n_repeats": 1, "inner_n_splits": 2, "seed": 1,
                  "c_grid": [1.0], "n_permutations": 2, "n_bootstrap": 2,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
           "reference_lines": {}}
    with pytest.raises(ValueError, match="binary_risk_vs_none"):
        run_rung("rung1", "binary_risk_vs_none", X, y, groups, cfg)


def test_run_rung_allows_sex():
    X = np.random.default_rng(0).normal(size=(10, 3))
    y = np.array([0,1]*5); groups = np.arange(10)
    cfg = {"cv": {"n_splits": 2, "n_repeats": 1, "inner_n_splits": 2, "seed": 1,
                  "c_grid": [1.0], "n_permutations": 2, "n_bootstrap": 2,
                  "permutation_n_repeats": 1, "bootstrap_n_repeats": 1},
           "reference_lines": {}}
    result = run_rung("rung1", "sex", X, y, groups, cfg)
    assert result["rung"] == "rung1"
    assert "binary_risk_vs_none" not in ALLOWED_TARGETS
```

- [ ] **Step 3: Run to verify it fails**, then implement `control_diagnostic.py`'s `ALLOWED_TARGETS` and `run_rung`:

```python
# pearl/src/pearl_models/control_diagnostic.py
"""§0 — the one remaining diagnostic. Runs ONLY against positive-control
targets (sex), never the primary target. It cannot change the primary
verdict (frozen: NULL, AUC 0.474); its only output is which sentence the
final report is entitled to write (§0d)."""
from __future__ import annotations

ALLOWED_TARGETS = {"sex"}


def run_rung(rung_name: str, target: str, X, y, groups, cfg: dict) -> dict:
    if target not in ALLOWED_TARGETS:
        raise ValueError(
            f"control_diagnostic refuses to run against target={target!r}. "
            f"Only {ALLOWED_TARGETS} are sanctioned (phase_4.md §0a) — running "
            f"this against binary_risk_vs_none would invalidate the entire "
            f"Phase 3 result.")
    from pearl_models.primary import run_one_analysis
    result = run_one_analysis(rung_name, X, y, groups, cfg, seed=cfg["cv"]["seed"])
    result["rung"] = rung_name
    return result
```

- [ ] **Step 4: Implement `run_rung1_baseline`, `run_rung2_pswt_plus_baseline`**, following `pearl_models.positive_controls.run_sex_control`'s exact join pattern (baseline/pswt features inner-joined with `nuisance[["sex"]]`, dropna on sex). Test against real data with a light cfg (small `n_permutations`/`n_bootstrap`) before running for real.

- [ ] **Step 5: Implement `compute_per_channel_band_power` and `run_rung3_per_channel`.** Load each subject's rest continuous derivative via `pearl_features.epoching.load_eyes_closed_continuous`, apply the same artifact rejection (`reject_artifact_segments`) as the declared pipeline, call `pearl_features.baseline.relative_band_powers(raw, picks=raw.ch_names)` and `aperiodic_fit` on the full 127-channel set (not `cfg["roi_channels"]`), per subject, per channel — assemble a `(64, 127*7)` matrix (5 band powers + 2 aperiodic params × 127 channels) or, more tractably, average within each of a small number of anatomical zones (frontal/central/parietal/occipital/temporal) to keep the feature count sane; document whichever choice is made and why in the diagnostic report. Run this rung last (§0c — it's the only one requiring new computation).

- [ ] **Step 6: Implement `run_ladder`** — runs all three unconditionally, determines `stopped_at` from the CI-lower-bound threshold in `config/control_diagnostic.yaml`.

- [ ] **Step 7: Run the real ladder** (background, monitor — rung 3's fresh 127-channel extraction across 64 subjects is the expensive step). Record all three AUCs regardless of outcome.

- [ ] **Step 8: Write `reports/phase4_control_diagnostic.md`** (extend `pearl_models/reports.py`) — verdict-first, all three rungs' numbers, the §0d decision table reproduced with the outcome marked, and the exact sentence the final report is now entitled to use.

- [ ] **Step 9: Run full `pytest -q`, commit.**

---

## Task B: Document and fix the two feature-definition defects (§1)

**Files:**
- Modify: `pearl/config/features.yaml` — remove `harmonic_amplitude_profile_h1_median`/`h1_iqr` from `feature_list`
- Modify: `pearl/src/pearl_features/features.py` — `compute_subject_features` stops emitting `h1_median`/`h1_iqr` keys (loop from `h=2` for the profile-median/iqr aggregation, or explicitly `continue` at `h==1`)
- Modify: `pearl/data/derivatives/features/feature_dictionary.md` — 18 declared features, h5 flagged
- Test: `pearl/tests/test_features_extraction.py` (extend) — regression tests per §1's requirement

**Interfaces:**
- Produces: `features.assert_no_constant_features(df) -> None` (raises `AssertionError` naming the offending column(s) — std == 0 across the cohort).
- Produces: `features.assert_missingness_below_threshold(df, threshold: float = 0.5) -> dict` — returns `{column: missing_frac}` for every column exceeding `threshold`; does not raise (missingness is allowed if flagged in the dictionary — this is a reporting function, not a gate, since `h5` is a known, documented exception).

- [ ] **Step 1: Write the two failing regression tests**

```python
# append to pearl/tests/test_features_extraction.py
import pandas as pd
from pearl_features.features import assert_no_constant_features, assert_missingness_below_threshold


def test_assert_no_constant_features_catches_zero_variance_column():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.0, 1.0, 1.0]})
    with pytest.raises(AssertionError, match="b"):
        assert_no_constant_features(df)


def test_assert_no_constant_features_passes_when_none_constant():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
    assert_no_constant_features(df)  # no raise


def test_assert_missingness_below_threshold_flags_high_missingness_column():
    df = pd.DataFrame({"a": [1.0, None, None, None], "b": [1.0, 2.0, 3.0, 4.0]})
    flagged = assert_missingness_below_threshold(df, threshold=0.5)
    assert "a" in flagged and "b" not in flagged
```

- [ ] **Step 2: Run to verify they fail**, then implement in `features.py`:

```python
def assert_no_constant_features(df) -> None:
    constant_cols = [c for c in df.columns if df[c].dropna().nunique() <= 1]
    assert not constant_cols, f"constant (zero-variance) declared features: {constant_cols}"


def assert_missingness_below_threshold(df, threshold: float = 0.5) -> dict:
    fracs = df.isna().mean()
    return {c: float(f) for c, f in fracs.items() if f > threshold}
```

- [ ] **Step 3: Run real regression check against the actual `features_pswt.csv`** to confirm it currently fails on `h1` (constant) and flags `h5` (missingness):

```bash
cd pearl && PYTHONPATH=src python -c "
from pearl_features.features import assert_no_constant_features, assert_missingness_below_threshold
from pearl_models.data import load_pswt_features
df = load_pswt_features()
try:
    assert_no_constant_features(df)
    print('no constant features (unexpected before the fix)')
except AssertionError as e:
    print('EXPECTED before fix:', e)
print('missingness flags:', assert_missingness_below_threshold(df))
"
```

- [ ] **Step 4: Remove `h1_median`/`h1_iqr` from `compute_subject_features`'s emitted output** (in the `for h in range(1, n_h + 1):` loop in `pearl/src/pearl_features/features.py`, skip `h == 1` when writing `out[...]`), and from `config/features.yaml`'s `feature_list` (now 18 entries). Update the file-level comment block explaining the 20→18 count and why (tautological constant, phase_4.md §1).

- [ ] **Step 5: Regenerate `features_pswt.csv` by dropping the two columns** (no DSP re-run needed — they were always trivially 1.0/0.0):

```bash
cd pearl && PYTHONPATH=src python -c "
import pandas as pd
df = pd.read_csv('data/derivatives/features/features_pswt.csv', index_col='subject')
df = df.drop(columns=['harmonic_amplitude_profile_h1_median', 'harmonic_amplitude_profile_h1_iqr'])
df.to_csv('data/derivatives/features/features_pswt.csv')
print(df.shape)
"
```

- [ ] **Step 6: Re-run the two regression checks from Step 3** — `assert_no_constant_features` must now pass; `assert_missingness_below_threshold` must still flag `h5_median`/`h5_iqr`.

- [ ] **Step 7: Update `feature_dictionary.md`**: 18 declared PSWT features (removed row for h1, note why), `h5_*` rows annotated "flagged: NaN for 53/64 subjects by design (§6b); correlates with recording duration (r=0.81/0.96) among the non-missing subset — usability caveat, not removed, since it is legitimately the excluded-harmonic-index design working as intended, just poorly suited to be a *declared* feature. Design lesson for any future phase: the 50Hz exclusion should apply at the harmonic-profile level (varying which bin is NaN'd per subject, as already done) rather than leaving a mostly-empty column in the fixed declared set."

- [ ] **Step 8: State in `reports/phase4_final_report.md`'s defects annex** (written in Task E) that Phase 3's primary analysis ran with **18 informative features**, not 20 — and that this does not require re-running the primary CV, since removing two exactly-constant columns cannot change an L2 logistic regression's fit or output (standardization of a zero-variance column already produced a zero/undefined-but-inert contribution; the model already assigned it ~0 weight, confirmed by Phase 3's feature-stability table showing 0% selection frequency for both).

- [ ] **Step 9: Run full `pytest -q`, commit.**

---

## Task C: Merge, hygiene, clean-clone reproducibility (§2)

- [ ] **Step 1:** Confirm `phase3-modeling-validation-delivery` is already merged to `master` (it is, per the prior session) — this step is a no-op verification, not a re-merge.
- [ ] **Step 2: Tag the commit that produced the reported Phase 3 number.**

```bash
cd /d/younes/AI-zhaimer
git log --oneline | grep -i "phase3: write reports/phase3_results.md"
git tag -a v1.0-phase3-null <that-commit-sha> -m "State that produced the reported Phase 3 primary result: NULL, AUC 0.474"
```

- [ ] **Step 3: Pin dependency versions in `pearl/pyproject.toml`.** Replace every `>=` floor with the exact installed version (`pip freeze` inside the working environment, cross-referenced against `pyproject.toml`'s current list — `mne`, `mne-icalabel`, `scikit-learn`, `PyWavelets`, `tabulate`, `pandas`, `numpy`, `scipy`, `pyyaml`, `requests`, `jinja2`, `pytest`, `pytest-cov`).

- [ ] **Step 4: Clean-clone test, run for real.**

```bash
cd /d/younes && git clone AI-zhaimer AI-zhaimer-clean-clone-test
cd AI-zhaimer-clean-clone-test/pearl
python -m venv .venv-clonetest
.venv-clonetest/Scripts/python -m pip install -e ".[dev]"
.venv-clonetest/Scripts/python -m pytest tests/ -q
```

Record the exact result (pass/fail, any manual step needed) in `reports/provenance_chain.md`'s reproducibility section. If it fails, fix the root cause (missing doc step, uncommitted config, etc.) in the real repo, not in the clone, then re-clone and re-test. Delete the clone directory when done.

- [ ] **Step 5: Verify tracked-file hygiene.** `git ls-files | grep -E '^phase_[0-9]'` must list all five phase specs; `git status --ignored` must show `pearl/data/`, `pearl/.venv/`, `pearl/.cache/` as ignored, not tracked.

- [ ] **Step 6: Write `reports/provenance_chain.md`** — one page: `participants_tsv_sha256` (from `pearl/reports/analysis_plan_frozen.md`'s Amendment blocks / `pearl_preproc.paths.participants_tsv_sha256()`) → Phase 1 `run_id` (`20260808T234509Z-a3b8888`) → Phase 2 `run_id` (`20260809T222134Z-84a0543`) → Phase 3 `run_id` (`20260810T152236Z-d8ab867`) → shipped model hash (`sha256` of `model_final.joblib`). Each arrow states which artifact records the link (e.g. every Phase 1 sidecar JSON carries `participants_tsv_sha256`; `model_card.md` carries the Phase 3 `run_id`).

- [ ] **Step 7: Commit** (pins, tag already pushed as a git tag not a commit, provenance doc).

---

## Task D: Package the tool (§3)

**Files:**
- Create: `pearl/Dockerfile`
- Create: `pearl/src/pearl_models/inference.py` — the single inference path both CLI and API call
- Create: `pearl/src/pearl_models/api.py` — thin HTTP API
- Modify: `pearl/pyproject.toml` — add API dependency if needed (check for an existing lightweight option before adding Flask; `http.server` + manual JSON handling is acceptable if it keeps the dependency list smaller, given this is a one-endpoint tool)
- Create: `pearl/INSTALL.md`, `pearl/RUNBOOK.md`
- Test: `pearl/tests/test_models_inference.py`

**Interfaces:**
- Produces: `inference.score_bids_subject(bids_dir: Path, subject: str, model_path: Path) -> dict` — runs Phase 1 preprocessing → Phase 2 feature extraction → Phase 3 scoring (`pearl_models.delivery.score_subject`) → returns the JSON-serializable result dict including `status`, `probability` or `reason`, `disclaimer`, and a provenance block (`run_id`, `git_sha`, `model_card_reference`).
- Produces: `api.py` exposes one `POST /score` endpoint accepting a subject ID + BIDS path, calling `inference.score_bids_subject`, returning its dict as JSON.
- Produces: CLI: extend `pearl_models/cli.py` with a `score` subcommand calling the same `inference.score_bids_subject`.

- [ ] **Step 1: Write the failing test for `score_bids_subject`'s output shape** (mock the three pipeline stages so the test doesn't require running full DSP — matches this repo's established pattern of mocking expensive sub-stages in orchestration tests):

```python
# pearl/tests/test_models_inference.py
from unittest.mock import patch

from pearl_models.inference import score_bids_subject


def test_score_bids_subject_includes_disclaimer_and_status():
    with patch("pearl_models.inference._preprocess_subject") as mock_pp, \
         patch("pearl_models.inference._extract_features") as mock_feat, \
         patch("pearl_models.inference._load_model") as mock_model:
        mock_pp.return_value = {"n_bad_channels": 2, "n_ica_removed": 10, "artifact_frac": 0.05}
        mock_feat.return_value = [[0.1] * 18]
        mock_model.return_value = ({"training_qc_ranges": {"n_bad_channels": (0, 10),
                                                            "n_ica_removed": (0, 30),
                                                            "artifact_frac": (0, 0.5)}}, object())
        result = score_bids_subject("fake_bids_dir", "sub-01", "fake_model_path")
    assert "disclaimer" in result
    assert "research" in result["disclaimer"].lower()
    assert result["status"] in {"scored", "cannot_score"}
```

- [ ] **Step 2: Run to verify it fails**, then implement `inference.py` wiring `pearl_preproc`, `pearl_features`, and `pearl_models.delivery` together behind the three patchable helper functions (`_preprocess_subject`, `_extract_features`, `_load_model`) the test mocks, plus the real `score_bids_subject` orchestration and disclaimer.

- [ ] **Step 3: Run tests, verify pass.**

- [ ] **Step 4: Write the CLI `score` subcommand and `api.py`.** Keep `api.py` minimal — a single-route server is enough; do not pull in a full framework unless something in the existing dependency tree already provides one.

- [ ] **Step 5: Write the `Dockerfile`.**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pearl/pyproject.toml pearl/README.md /app/
COPY pearl/src /app/src
COPY pearl/config /app/config
RUN pip install --no-cache-dir -e .
ENTRYPOINT ["pearl-models"]
CMD ["--help"]
```

- [ ] **Step 6: Build the image and run the end-to-end smoke test inside it** against one held-back subject's raw files (pick a subject already excluded from the training cohort at QC, so scoring it is itself a demonstration of the OOD-refusal or normal-scoring path without touching the frozen 64-subject analysis).

```bash
cd /d/younes/AI-zhaimer
docker build -t pearl-models:phase4 -f pearl/Dockerfile .
docker run --rm pearl-models:phase4 pearl-models score --subject sub-XX --bids-dir /data/bids
```

Assert the output JSON has the disclaimer and a valid `status`. Record the actual command and output in `RUNBOOK.md`.

- [ ] **Step 7: Write `INSTALL.md`** (install steps, Docker and bare-metal) **and `RUNBOOK.md`** (how to score a subject, how to interpret output, what OOD refusal means and what to do when it fires, disk/bandwidth requirements for reprocessing from raw — reuse Phase 1's measured 17.73 GB / streaming-download numbers from `report.md`).

- [ ] **Step 8: Run full `pytest -q`, commit.**

---

## Task E: Client deliverable (§4)

**Files:**
- Create: `pearl/reports/phase4_final_report.md` (+ `.html` via the same `_markdown_to_self_contained_html` helper already in `pearl_models/reports.py`)

- [ ] **Step 1:** Write the 8-section report per phase_4.md §4's exact structure, in plain language, non-specialist readable. Pull real numbers from `reports/phase3_results.md`, `reports/phase4_control_diagnostic.md` (§0d wording), and `reports/phase2_confound_gate.md`. Do not invent numbers not already established.
- [ ] **Step 2:** Ask the user (this plan cannot decide it) whether a French version is needed, per §4's explicit instruction — flag this as an open question in the report's own header rather than silently deciding either way.
- [ ] **Step 3:** Render the HTML variant, commit both.

---

## Task F: Handover pack (§5, §6)

**Files:**
- Create: `pearl/HANDOVER.md`

- [ ] **Step 1:** Write the repo map, phase-to-code mapping, "where every reported number comes from" table (reuse `provenance_chain.md`), frozen-decisions list with reasons, deferred-items list with rough sizing (§6's four out-of-scope items, each with a size estimate — e.g. Option C reprocessing ≈ multi-day given the 46GB re-download + full Phase 1-3 re-run; richer MSIT feature engineering ≈ a few days; Sternberg ingestion ≈ comparable to Phase 1's rest+MSIT effort; recovering excluded subjects ≈ not generally possible, they failed fixed QC thresholds).
- [ ] **Step 2:** Data retention section: what's on disk (17.73 GB derivatives), what can be deleted (raw, already deleted per Phase 1's streaming design), what must be kept (everything under `pearl/data/derivatives/`, `pearl/reports/`, `pearl/config/`) to reproduce the reported numbers.
- [ ] **Step 3:** "If you resume this project" — first three things to read, in order: `report.md`, the relevant `phase_N.md`, `reports/provenance_chain.md`.
- [ ] **Step 4:** Commit.

---

## Final: Definition of Done sweep (§7) and stop-condition review (§8)

- [ ] Walk every checkbox in phase_4.md §7 against the real artifact.
- [ ] Confirm none of §8's stop conditions fired (diagnostic never touched the primary target; clean-clone passed; container disclaimer present; no one revised the primary verdict).
- [ ] Full `pytest -q` green, single `run_id` referenced consistently across new artifacts.
- [ ] Final commit and report to the user.
