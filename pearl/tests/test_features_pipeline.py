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
                   run_id="testrun", git_sha_value="abc123", gate_verdict="proceed")
    assert (tmp_path / "features_pswt.csv").exists()
    assert (tmp_path / "features_baseline.csv").exists()
    assert (tmp_path / "cycle_stats.csv").exists()
    assert (tmp_path / "_meta.json").exists()
    pswt_df = pd.read_csv(tmp_path / "features_pswt.csv")
    assert "subject" in pswt_df.columns
    assert "group" not in pswt_df.columns
