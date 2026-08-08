"""Download engine tests (phase_1.md §6): idempotence, disk guard, streaming
delete-on-success / retain-on-failure."""
from __future__ import annotations

import json

import pytest

import pearl_preproc.download as dl
import pearl_preproc.pipeline as pipe
import pearl_preproc.preprocess as preproc_mod
from pearl_preproc.paths import PREPROC_DIR, RAW_DIR, DiskGuardError

CFG = {
    "download": {"retries": 1, "stream_chunk_bytes": 1 << 20},
    "ica": {"n_components": 30, "exclude_threshold": 0.8},
    "line_noise": {"notch_width_hz": 1.0, "margin_hz": 0.5},
    "filters": {"high_pass": {"l_freq_hz": 0.5}},
    "artifact_annotation": {"peak_v": 1e-4, "flat_v": 1e-6},
    "iaf": {"band_hz": [7, 13], "channels": ["O1", "Oz", "O2"],
            "min_peak_prominence_db": 3.0, "require_for_tasks": ["task-rest"]},
    "qc": {"bad_channels_fail": 8, "bad_channels_warn": 4,
           "max_occipital_bads_fail": 5, "max_occipital_bads_warn": 3,
           "ica_removed_frac_fail": 0.4, "ica_removed_frac_warn": 0.25,
           "artifact_frac_fail": 0.4, "artifact_frac_warn": 0.2,
           "line_noise_residual_fail_ratio": 0.5, "min_duration_frac": 0.6,
           "occipital_channels": ["O1", "Oz", "O2"]},
    "exclusion": {"max_bad_channels": 10, "max_occipital_bads": 5,
                  "require_alpha": True},
}


def _rows(subject="sub-01", tasks=("msit", "rest")):
    rows = []
    for t in tasks:
        for ext in (".eeg", ".vhdr", ".vmrk"):
            rows.append({"scope": "C_rest_msit_only",
                         "path": f"{subject}/eeg/{subject}_task-{t}_eeg{ext}",
                         "bytes": 100 if ext == ".eeg" else 20,
                         "modality": "eeg", "subject": subject, "task": t})
    return rows


def test_download_idempotent_second_run_zero_bytes(tmp_path, monkeypatch):
    """Second invocation must download zero bytes (§1, §6)."""
    monkeypatch.setattr(dl, "RAW_DIR", tmp_path)
    rows = _rows()
    url_map = {r["path"]: f"https://example/{r['path']}" for r in rows}
    # pre-stage everything with the correct sizes
    for r in rows:
        dest = tmp_path / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * r["bytes"])

    calls = []
    monkeypatch.setattr(dl, "download_one", lambda *a, **k: calls.append(a) or {})
    s1 = dl.download_subject("sub-01", rows, url_map, CFG, log_fn=lambda r: None)
    s2 = dl.download_subject("sub-01", rows, url_map, CFG, log_fn=lambda r: None)
    assert s1["skipped"] == len(rows) and s1["downloaded"] == 0
    assert s2["skipped"] == len(rows) and s2["downloaded"] == 0
    assert calls == []  # nothing fetched on either run


def test_size_mismatch_retried_then_quarantined(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "RAW_DIR", tmp_path)
    rows = _rows("sub-09", ("msit",))
    url_map = {r["path"]: f"https://example/{r['path']}" for r in rows}
    attempts = {"n": 0}

    def _bad_download(url, dest, expected, **kw):
        attempts["n"] += 1
        raise dl.DownloadError("size mismatch (simulated)")

    monkeypatch.setattr(dl, "download_one", _bad_download)
    summary = dl.download_subject("sub-09", rows, url_map, CFG, log_fn=lambda r: None)
    assert summary["quarantined"] is True
    # the first file fails once, is retried once, and the subject stops there
    assert attempts["n"] == 2
    assert "size mismatch" in summary["errors"][0]


def test_disk_guard_triggers(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "ensure_dirs", lambda: None)

    def _no_space(*a, **k):
        raise DiskGuardError("Only 1.2 GB free on D: — need at least 20.0 GB")

    monkeypatch.setattr(dl, "require_free_space", _no_space)
    with pytest.raises(DiskGuardError):
        dl.download_all(CFG, subjects=["sub-01"])


def _stub_derivative(subject, task, preproc_dir=PREPROC_DIR):
    d = preproc_dir / subject / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    stem = f"{subject}_task-{task}"
    (d / f"{stem}_desc-preproc_eeg.fif").write_bytes(b"fif")
    (d / f"{stem}_desc-ica_components.fif").write_bytes(b"ica")
    (d / f"{stem}_desc-preproc_eeg.json").write_text(
        json.dumps({"task": task}), encoding="utf-8")
    return d


def test_streaming_deletes_raw_on_success(tmp_path, monkeypatch):
    deriv = tmp_path / "deriv"
    monkeypatch.setattr(pipe, "RAW_DIR", tmp_path)
    monkeypatch.setattr(preproc_mod, "PREPROC_DIR", deriv)
    rows = _rows()
    url_map = {r["path"]: f"https://x/{r['path']}" for r in rows}
    for r in rows:
        dest = tmp_path / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * r["bytes"])
    monkeypatch.setattr(pipe, "download_subject",
                        lambda s, rows, um, cfg, log_fn=None: {
                            "downloaded": 0, "skipped": len(rows),
                            "quarantined": False, "bytes": 0, "errors": []})

    def _ok(subject, task, cfg):
        _stub_derivative(subject, task, deriv)
        return {"subject": subject, "task": task}

    monkeypatch.setattr(pipe, "process_subject_task", _ok)
    summary = pipe.process_subject("sub-01", CFG, url_map, rows, keep_raw=False)
    assert summary["ok"] is True
    assert not (tmp_path / "sub-01").exists()  # raw deleted after success


def test_resume_skips_completed_subjects(tmp_path, monkeypatch):
    deriv = tmp_path / "deriv"
    monkeypatch.setattr(pipe, "RAW_DIR", tmp_path)
    monkeypatch.setattr(preproc_mod, "PREPROC_DIR", deriv)
    rows = _rows()
    url_map = {r["path"]: f"https://x/{r['path']}" for r in rows}
    for t in ("msit", "rest"):
        _stub_derivative("sub-01", t, deriv)
    downloaded = []

    def _fake_dl(subject, rows, um, cfg, log_fn=None):
        downloaded.append(subject)
        return {"downloaded": 1, "skipped": 0, "quarantined": False,
                "bytes": 1, "errors": []}

    monkeypatch.setattr(pipe, "download_subject", _fake_dl)
    summary = pipe.process_subject("sub-01", CFG, url_map, rows, keep_raw=False)
    assert summary["ok"] is True
    assert summary["skipped"] is True
    assert downloaded == []  # valid derivative → zero network, zero compute


def test_streaming_retains_raw_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(pipe, "RAW_DIR", tmp_path)
    monkeypatch.setattr(preproc_mod, "PREPROC_DIR", tmp_path / "deriv")
    rows = _rows()
    url_map = {r["path"]: f"https://x/{r['path']}" for r in rows}
    for r in rows:
        dest = tmp_path / r["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * r["bytes"])
    monkeypatch.setattr(pipe, "download_subject",
                        lambda s, rows, um, cfg, log_fn=None: {
                            "downloaded": 0, "skipped": len(rows),
                            "quarantined": False, "bytes": 0, "errors": []})
    from pearl_preproc.preprocess import PreprocessError
    monkeypatch.setattr(pipe, "process_subject_task",
                        lambda s, t, cfg: (_ for _ in ()).throw(
                            PreprocessError("simulated failure")))
    summary = pipe.process_subject("sub-01", CFG, url_map, rows, keep_raw=False)
    assert summary["ok"] is False
    assert summary["raw_retained"] is True
    assert (tmp_path / "sub-01").exists()  # raw retained for re-processing
