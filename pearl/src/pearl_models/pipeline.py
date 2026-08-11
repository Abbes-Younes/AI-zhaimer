"""§7 — orchestration and outputs for Phase 3."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from pearl_models.paths import MODELS_DIR, git_sha


def assemble_cv_predictions(analysis_name: str, subjects: list[str], y_true: np.ndarray,
                             oof_proba: np.ndarray, repeat: int) -> pd.DataFrame:
    return pd.DataFrame({
        "analysis": analysis_name, "subject": subjects, "y_true": y_true,
        "oof_proba": oof_proba, "repeat": repeat,
    })


def assemble_cv_metrics(results: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for name, r in results.items():
        row = {
            "analysis": name, "auc": r["auc"], "ci_low": r["ci"][0], "ci_high": r["ci"][1],
            "p_value": r.get("p_value"), "p_value_holm": r.get("p_value_holm"),
            "n_subjects_used": r["n_subjects_used"],
        }
        ref = r.get("reference_lines", {})
        for k, v in ref.items():
            if isinstance(v, (int, float)):
                row[f"ref_{k}"] = v
        rows.append(row)
    return pd.DataFrame(rows)


def write_outputs(predictions: pd.DataFrame, metrics: pd.DataFrame, stability: pd.DataFrame,
                   out_dir: Path, run_id: str, git_sha_value: str, gate_verdict: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out_dir / "cv_predictions.csv", index=False)
    metrics.to_csv(out_dir / "cv_metrics.csv", index=False)
    stability.to_csv(out_dir / "feature_stability.csv", index=False)
    (out_dir / "_meta.json").write_text(json.dumps({
        "run_id": run_id, "git_sha": git_sha_value, "primary_verdict": gate_verdict,
    }, indent=2) + "\n", encoding="utf-8")


def run(run_id: str | None = None) -> dict:
    """Orchestrates Tasks 4-11 end to end: positive controls first (stopping
    if 1a fails), benchmark reproduction, nuisance-only, primary + secondary,
    leakage checklist, results report, final model + model card."""
    import yaml

    from pearl_models.positive_controls import run_sex_control, run_eyes_open_closed_control
    from pearl_models.benchmark import run_msit_benchmark
    from pearl_models.nuisance import run_nuisance_only
    from pearl_models.primary import run_primary_analysis, run_secondary_set, feature_stability
    from pearl_models.leakage import run_full_checklist
    from pearl_models.reports import write_positive_controls, write_benchmark_reproduction, write_results
    from pearl_models.delivery import train_final_model, write_model_card, write_provenance_json
    from pearl_models.paths import CONFIG_DIR, REPORTS_DIR
    from pearl_models.data import load_pswt_features
    from pearl_features.features import load_features_config
    from pearl_preproc.paths import make_run_id
    import joblib

    rid = run_id or make_run_id()
    cfg = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    features_cfg = load_features_config()

    from pearl_models.data import load_pswt_features as _lp, load_nuisance as _ln
    sex_result = run_sex_control(cfg, _lp(), _ln())
    eo_result = run_eyes_open_closed_control(cfg, features_cfg)
    write_positive_controls(eo_result, sex_result, REPORTS_DIR / "phase3_positive_controls.md",
                             cfg["positive_controls"]["eyes_open_closed_auc_floor"],
                             cfg["positive_controls"]["sex_auc_reference_floor"])

    if eo_result["auc"] < cfg["positive_controls"]["eyes_open_closed_auc_floor"]:
        return {"stopped_at": "positive_control_1a", "eo_result": eo_result}

    benchmark_result = run_msit_benchmark(cfg)
    write_benchmark_reproduction(benchmark_result, REPORTS_DIR / "phase3_benchmark_reproduction.md")

    primary = run_primary_analysis(cfg)
    secondary = run_secondary_set(cfg)

    feature_cols = list(load_pswt_features().columns)
    fs = feature_stability(primary["features_only"]["fold_diagnostics"], feature_cols)

    groups = np.arange(primary["features_only"]["n_subjects_used"])
    leak_cfg = {"cv": {"n_splits": cfg["cv"]["n_splits"], "inner_n_splits": cfg["cv"]["inner_n_splits"],
                       "seed": cfg["cv"]["seed"]}}
    leakage_result = run_full_checklist(primary["features_only"],
                                         primary["features_only"]["perm_aucs"], groups, leak_cfg)

    verdict = "POSITIVE" if (primary["features_only"]["auc"] > primary["nuisance_only"]["auc"]
                              and primary["features_only"]["p_value"] < 0.05) else "NULL"

    write_results(primary, secondary, eo_result, sex_result, benchmark_result, fs, leakage_result,
                  cfg, REPORTS_DIR / "phase3_results.md")

    pipeline_model, provenance = train_final_model(cfg, primary["features_only"])
    joblib.dump(pipeline_model, MODELS_DIR / "model_final.joblib")
    write_model_card(provenance, MODELS_DIR / "model_card.md")
    write_provenance_json(provenance, MODELS_DIR / "provenance.json")

    all_results = {"features_only": primary["features_only"],
                   "features_plus_nuisance": primary["features_plus_nuisance"],
                   "nuisance_only": primary["nuisance_only"], **secondary}
    metrics = assemble_cv_metrics(all_results)

    pred_frames = []
    for name, r in {"features_only": primary["features_only"],
                     "features_plus_nuisance": primary["features_plus_nuisance"]}.items():
        pred_frames.append(assemble_cv_predictions(
            name, r["subject_ids"], r["y"], r["oof_proba_last_repeat"], repeat=0))
    predictions = pd.concat(pred_frames, ignore_index=True) if pred_frames else pd.DataFrame()

    write_outputs(predictions, metrics, fs, MODELS_DIR, rid, git_sha(), verdict)

    return {"primary": primary, "secondary": secondary, "verdict": verdict,
            "eo_result": eo_result, "sex_result": sex_result, "benchmark_result": benchmark_result}
