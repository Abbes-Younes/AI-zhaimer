"""§8 — orchestration and outputs. Feature files must NOT contain group
labels; the join happens in Phase 3.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pearl_features.paths import FEATURES_DIR, git_sha


def assemble_output_frame(rows: dict[str, dict], index_name: str = "subject") -> pd.DataFrame:
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = index_name
    return df


def write_outputs(pswt_rows: dict, baseline_rows: dict, cycle_stats_rows: list[dict],
                   out_dir: Path, run_id: str, git_sha_value: str,
                   gate_verdict: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    assemble_output_frame(pswt_rows).to_csv(out_dir / "features_pswt.csv")
    assemble_output_frame(baseline_rows).to_csv(out_dir / "features_baseline.csv")
    pd.DataFrame(cycle_stats_rows).to_csv(out_dir / "cycle_stats.csv", index=False)
    (out_dir / "_meta.json").write_text(json.dumps({
        "run_id": run_id, "git_sha": git_sha_value, "gate_verdict": gate_verdict,
    }, indent=2) + "\n", encoding="utf-8")


def run(run_id: str | None = None) -> dict:
    from pearl_features.cohort import load_qc_metrics, per_task_cohort
    from pearl_features.features import load_features_config, compute_subject_features
    from pearl_features.baseline import compute_subject_baseline
    from pearl_features.epoching import load_eyes_closed_continuous, reject_artifact_segments
    from pearl_features.confound_gate_report import run as run_gate
    from pearl_preproc.paths import make_run_id

    rid = run_id or make_run_id()

    gate_result = run_gate()
    cfg = load_features_config()
    qc = load_qc_metrics()
    per_task = per_task_cohort(qc)
    rest_included = set(per_task[(per_task["task"].isin(["rest", "task-rest"])) &
                                  per_task["included"]]["subject"])
    msit_included = set(per_task[(per_task["task"].isin(["msit", "task-msit"])) &
                                  per_task["included"]]["subject"])

    pswt_rows, baseline_rows, cycle_stats_rows = {}, {}, []
    for subject in sorted(rest_included):
        qc_row = qc[(qc["subject"] == subject) & (qc["task"].isin(["rest", "task-rest"]))].iloc[0]
        iaf_hz = float(qc_row["iaf_hz"])
        try:
            feats, meta = compute_subject_features(subject, cfg, iaf_hz)
        except (AssertionError, ValueError) as exc:
            cycle_stats_rows.append({"subject": subject, "excluded_reason": str(exc)})
            continue

        pswt_rows[subject] = feats

        raw = load_eyes_closed_continuous(subject)
        raw, _, usable_s = reject_artifact_segments(raw, cfg)
        baseline = compute_subject_baseline(
            raw, cfg["roi_channels"], iaf_hz, float(qc_row["alpha_peak_height_db"]))

        if subject in msit_included:
            try:
                msit_raw = mne_read_msit(subject)
                msit_baseline = compute_subject_baseline(
                    msit_raw, cfg["roi_channels"], iaf_hz, float(qc_row["alpha_peak_height_db"]),
                    prefix="msit_")
                baseline.update(msit_baseline)
            except FileNotFoundError:
                pass

        baseline_rows[subject] = baseline

        cycle_stats_rows.append({
            "subject": subject,
            "usable_duration_s": usable_s,
            "excluded_harmonic_index": meta["excluded_harmonic_index"],
            "dropped_channels": ";".join(meta["dropped_channels"]),
            "n_roi_channels_used": len(cfg["roi_channels"]) - len(meta["dropped_channels"]),
        })

    write_outputs(pswt_rows, baseline_rows, cycle_stats_rows, FEATURES_DIR, rid, git_sha(),
                  gate_verdict=gate_result["verdict"])

    return {"n_subjects": len(pswt_rows), "n_features_pswt": len(next(iter(pswt_rows.values()), {})),
            "n_features_baseline": len(next(iter(baseline_rows.values()), {})),
            "gate_verdict": gate_result["verdict"]}


def mne_read_msit(subject: str):
    """Loads the MSIT continuous derivative directly (no eyes-closed window —
    that concept is rest-only). Label-blind: same PREPROC_DIR convention as
    epoching.load_eyes_closed_continuous."""
    import mne

    from pearl_preproc.paths import PREPROC_DIR

    fif_path = PREPROC_DIR / subject / "eeg" / f"{subject}_task-msit_desc-preproc_eeg.fif"
    if not fif_path.exists():
        raise FileNotFoundError(fif_path)
    return mne.io.read_raw_fif(fif_path, preload=True, verbose=False)
