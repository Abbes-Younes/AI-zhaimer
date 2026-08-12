"""Track B orchestration gating logic (phase_5_stage2.md §4)."""
from __future__ import annotations

import pandas as pd

import pearl_features.tfa_pipeline as tfa_pipeline_mod
from pearl_features.tfa_pipeline import run


def test_run_gates_columns_by_task_inclusion(tmp_path, monkeypatch):
    monkeypatch.setattr(tfa_pipeline_mod, "compute_msit_tfa",
                         lambda subject: {"msit_tfa_alpha_mean": 0.5})
    monkeypatch.setattr(tfa_pipeline_mod, "compute_sternberg_tfa",
                         lambda subject: {"sternberg_encoding_tfa_alpha_mean": 0.3})

    result = run(
        msit_included={"sub-01"}, sternberg_included={"sub-02"},
        run_id="testrun", out_dir=tmp_path)

    df = pd.read_csv(tmp_path / "features_tfa.csv", index_col=0)
    assert set(df.index) == {"sub-01", "sub-02"}  # union of msit/sternberg included
    assert pd.notna(df.loc["sub-01", "msit_tfa_alpha_mean"])
    assert pd.isna(df.loc["sub-01", "sternberg_encoding_tfa_alpha_mean"])
    assert pd.notna(df.loc["sub-02", "sternberg_encoding_tfa_alpha_mean"])
    assert pd.isna(df.loc["sub-02", "msit_tfa_alpha_mean"])
    assert result["n_subjects"] == 2
    assert (tmp_path / "features_tfa_meta.json").exists()


def test_run_handles_missing_derivative_gracefully(tmp_path, monkeypatch):
    def raise_missing(subject):
        raise FileNotFoundError(subject)
    monkeypatch.setattr(tfa_pipeline_mod, "compute_msit_tfa", raise_missing)
    monkeypatch.setattr(tfa_pipeline_mod, "compute_sternberg_tfa", raise_missing)

    result = run(msit_included={"sub-01"}, sternberg_included=set(),
                 run_id="testrun", out_dir=tmp_path)
    assert result["n_subjects"] == 0
