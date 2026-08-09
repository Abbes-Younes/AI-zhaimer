import json

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
