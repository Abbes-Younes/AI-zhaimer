"""QC threshold logic (phase_1.md §6): known pass/warn/fail fixtures."""
from __future__ import annotations

from pathlib import Path

from pearl_preproc.config import load_preproc_config
from pearl_preproc.qc import classify_sidecar, freeze_exclusions

CFG = load_preproc_config()


def _sidecar(subject="sub-01", task="task-msit", **over):
    base = {
        "ParticipantID": subject,
        "TaskName": task,
        "Sources": [{"path": f"{subject}/eeg/{subject}_task-{task}_eeg.vhdr"}],
        "BadChannels": {"n": 1, "names": ["Fp1"], "occipital_bads": 0},
        "ICA": {"n_components": 30, "excluded_components": [],
                "excluded_labels": [], "labeling": "ICLabel"},
        "Duration": {"s": 600.0, "n_samples_final": 150000},
        "LineNoisePower": {"before_index": 3.0, "after_index": 1.1},
        "LineNoiseRemoval": {"method": "narrow_notch_fir"},
        "ArtifactAnnotation": {"fraction": 0.02},
        "IAF": {"iaf_hz": 10.1, "peak_height_db": 6.0, "present": True},
    }
    base.update(over)
    return base


def test_clean_sidecar_passes():
    row = classify_sidecar(_sidecar(), CFG, {})
    assert row["verdict"] == "pass"


def test_line_noise_removal_failure():
    ok = classify_sidecar(_sidecar(LineNoisePower={"before_index": 4.0, "after_index": 1.1}),
                          CFG, {})
    assert ok["verdict"] == "pass"   # spike removed
    no_spike = classify_sidecar(_sidecar(LineNoisePower={"before_index": 1.1, "after_index": 1.1}),
                                CFG, {})
    assert no_spike["verdict"] == "pass"  # nothing to remove
    failed = classify_sidecar(_sidecar(LineNoisePower={"before_index": 4.0, "after_index": 2.5}),
                              CFG, {})
    assert failed["verdict"] == "fail"   # real spike survived treatment


def test_many_bad_channels_fails():
    row = classify_sidecar(_sidecar(BadChannels={
        "n": 9, "names": [f"C{i}" for i in range(9)], "occipital_bads": 0}), CFG, {})
    assert row["verdict"] == "fail"
    assert "bad channels" in row["flags"]


def test_occipital_bads_warn_and_fail():
    w = classify_sidecar(_sidecar(BadChannels={
        "n": 4, "names": ["O1", "O2", "Oz", "POz"], "occipital_bads": 4}), CFG, {})
    assert w["verdict"] == "warn"
    f = classify_sidecar(_sidecar(BadChannels={
        "n": 5, "names": ["O1", "O2", "Oz", "POz", "PO7"], "occipital_bads": 5}), CFG, {})
    assert f["verdict"] == "fail"


def test_ica_removed_thresholds():
    ok = classify_sidecar(_sidecar(ICA={
        "n_components": 30, "excluded_components": list(range(5)),
        "excluded_labels": ["eye blink"] * 5, "labeling": "ICLabel"}), CFG, {})
    assert ok["verdict"] == "pass"
    warn = classify_sidecar(_sidecar(ICA={
        "n_components": 30, "excluded_components": list(range(8)),
        "excluded_labels": ["eye blink"] * 8, "labeling": "ICLabel"}), CFG, {})
    assert warn["verdict"] == "warn"
    # Client decision 2026-08-06: ICA removal is warn-only — no fraction fails.
    high = classify_sidecar(_sidecar(ICA={
        "n_components": 30, "excluded_components": list(range(13)),
        "excluded_labels": ["eye blink"] * 13, "labeling": "ICLabel"}), CFG, {})
    assert high["verdict"] == "warn"
    assert "ICA removed" in high["flags"]


def test_artifact_fraction_thresholds():
    w = classify_sidecar(_sidecar(ArtifactAnnotation={"fraction": 0.25}), CFG, {})
    assert w["verdict"] == "warn"
    f = classify_sidecar(_sidecar(ArtifactAnnotation={"fraction": 0.5}), CFG, {})
    assert f["verdict"] == "fail"


def test_rest_without_alpha_fails():
    row = classify_sidecar(_sidecar(task="task-rest", IAF={
        "iaf_hz": 9.0, "peak_height_db": 1.0, "present": False}), CFG, {})
    assert row["verdict"] == "fail"
    assert "alpha" in row["flags"]


def test_rest_without_alpha_fails_bare_task_spelling():
    # Real sidecars say TaskName="rest", not "task-rest" (the config spelling).
    row = classify_sidecar(_sidecar(task="rest", IAF={
        "iaf_hz": 9.0, "peak_height_db": 1.0, "present": False}), CFG, {})
    assert row["verdict"] == "fail"
    assert "alpha" in row["flags"]


def test_fifth_harmonic_collision_flag():
    hit = classify_sidecar(_sidecar(IAF={
        "iaf_hz": 9.9, "peak_height_db": 6.0, "present": True}), CFG, {})
    assert hit["fifth_harmonic_collision"] is True   # 5×9.9 = 49.5 Hz
    miss = classify_sidecar(_sidecar(IAF={
        "iaf_hz": 11.5, "peak_height_db": 6.0, "present": True}), CFG, {})
    assert miss["fifth_harmonic_collision"] is False


def test_truncation_fails():
    expected = {("sub-01", "task-msit"): 600.0}
    row = classify_sidecar(_sidecar(Duration={"s": 200.0, "n_samples_final": 50000}),
                           CFG, expected)
    assert row["verdict"] == "fail"
    assert "truncated" in row["flags"]


def test_freeze_exclusions_occipital_rule_fires_with_bare_task_name(tmp_path, monkeypatch):
    # Regression: freeze_exclusions used to compare the bare "rest" TaskName
    # against config's "task-rest" key and never match, so this rule never
    # fired despite 124 tests passing (the old fixture default used
    # "task-msit", the config spelling, not the real sidecar spelling).
    import pearl_preproc.qc as qc_mod
    monkeypatch.setattr(qc_mod, "QC_DIR", tmp_path)
    row = classify_sidecar(_sidecar("sub-09", "rest", BadChannels={
        "n": 5, "names": ["O1", "O2", "Oz", "POz", "PO7"], "occipital_bads": 5}), CFG, {})
    excluded = freeze_exclusions([row], CFG)
    assert {e["subject"] for e in excluded} == {"sub-09"}
    assert any("occipital" in e["reason"] for e in excluded)


def test_freeze_exclusions_archives_previous_list(tmp_path, monkeypatch):
    import pearl_preproc.qc as qc_mod
    monkeypatch.setattr(qc_mod, "QC_DIR", tmp_path)
    rows1 = [classify_sidecar(_sidecar("sub-02", "rest", IAF={
        "iaf_hz": 8.5, "peak_height_db": 0.5, "present": False}), CFG, {})]
    freeze_exclusions(rows1, CFG)
    rows2 = [classify_sidecar(_sidecar("sub-03", "rest", IAF={
        "iaf_hz": 8.5, "peak_height_db": 0.5, "present": False}), CFG, {})]
    freeze_exclusions(rows2, CFG)
    archives = list(tmp_path.glob("excluded_subjects.*.csv"))
    assert len(archives) == 1
    assert "sub-02" in archives[0].read_text()


def test_freeze_exclusions_picks_fail_subjects(tmp_path, monkeypatch):
    import pearl_preproc.qc as qc_mod
    monkeypatch.setattr(qc_mod, "QC_DIR", tmp_path)
    rows = [
        classify_sidecar(_sidecar("sub-01", "task-msit"), CFG, {}),          # pass
        classify_sidecar(_sidecar("sub-02", "task-rest",
                                  IAF={"iaf_hz": 8.5, "peak_height_db": 0.5,
                                       "present": False}), CFG, {}),          # fail
        classify_sidecar(_sidecar("sub-02", "task-msit"), CFG, {}),
    ]
    excluded = freeze_exclusions(rows, CFG)
    subjects = {e["subject"] for e in excluded}
    assert subjects == {"sub-02"}
    assert any("alpha" in e["reason"] for e in excluded)
    assert (tmp_path / "excluded_subjects.csv").exists()
