"""§6 — delivery. The client asked for a deployable tool; ship it, positioned
correctly. The reported performance is always the cross-validated number
from Task 8, never a number computed on the training data.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_DISCLAIMER = ("research pipeline output — a research score, not a risk assessment, "
               "screening result, or diagnosis")


def train_final_model(cfg: dict, primary_result: dict) -> tuple[Pipeline, dict]:
    """Trains on all 64 subjects (evaluation already frozen and reported in
    Task 8/10 -- this fit is for deployment only, never re-evaluated as a
    performance number)."""
    from pearl_models.data import load_pswt_features, load_labels, load_nuisance
    from pearl_models.paths import CONFIG_DIR, sha256_file, git_sha
    from pearl_preproc.paths import participants_tsv_sha256, get_run_id, make_run_id

    pswt = load_pswt_features()
    labels = load_labels().set_index("subject_id")
    joined = pswt.join(labels[["risk_vs_none"]], how="inner")
    feature_cols = list(pswt.columns)
    X = joined[feature_cols].to_numpy(dtype=float)
    y = joined["risk_vs_none"].to_numpy(dtype=int)
    groups = np.arange(len(y))

    inner_cv = StratifiedGroupKFold(n_splits=cfg["cv"]["inner_n_splits"], shuffle=True,
                                     random_state=cfg["cv"]["seed"])
    search = GridSearchCV(LogisticRegression(solver="lbfgs", max_iter=2000),
                           param_grid={"C": cfg["cv"]["c_grid"]}, cv=inner_cv, scoring="roc_auc")

    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    X_imp = imputer.fit_transform(X)
    X_scaled = scaler.fit_transform(X_imp)
    search.fit(X_scaled, y, groups=groups)

    # groups is trivially unique-per-row for the final full-cohort fit (every
    # subject contributes exactly one row), so a plain StratifiedKFold is
    # mathematically equivalent to StratifiedGroupKFold here -- used directly
    # because CalibratedClassifierCV.fit does not route a groups= kwarg to
    # its cv splitter without explicit sklearn metadata-routing config.
    from sklearn.model_selection import StratifiedKFold
    outer_cv = StratifiedKFold(n_splits=cfg["cv"]["n_splits"], shuffle=True,
                                random_state=cfg["cv"]["seed"])
    calibrated = CalibratedClassifierCV(
        LogisticRegression(solver="lbfgs", max_iter=2000, C=search.best_params_["C"]),
        method="sigmoid", cv=outer_cv)
    calibrated.fit(X_scaled, y)

    pipeline = Pipeline([("imputer", imputer), ("scaler", scaler), ("model", calibrated)])

    nuisance = load_nuisance().loc[joined.index]
    from pearl_models.nuisance import NUISANCE_COLUMNS as _demo_and_qc  # noqa
    qc_columns = ["n_bad_channels", "n_ica_removed", "artifact_frac"]
    training_qc_ranges = {col: (float(nuisance[col].min()), float(nuisance[col].max()))
                           for col in qc_columns}

    rid = get_run_id() or make_run_id()
    provenance = {
        "run_id": rid,
        "git_sha": git_sha(),
        "feature_config_hash": sha256_file(CONFIG_DIR / "features.yaml"),
        "participants_tsv_sha256": participants_tsv_sha256(),
        "cv_estimated_auc": primary_result["auc"],
        "cv_estimated_ci": list(primary_result["ci"]),
        "cv_estimated_p_value": primary_result["p_value"],
        "training_qc_ranges": training_qc_ranges,
        "n_training_subjects": len(y),
        "feature_columns": feature_cols,
        "best_c": search.best_params_["C"],
    }
    return pipeline, provenance


def is_out_of_distribution(qc_row: dict, training_qc_ranges: dict) -> tuple[bool, str]:
    for metric, (lo, hi) in training_qc_ranges.items():
        if metric not in qc_row:
            continue
        value = qc_row[metric]
        if value < lo or value > hi:
            return True, f"{metric}={value} outside training range [{lo}, {hi}]"
    return False, ""


def score_subject(pipeline, qc_row: dict, feature_row, training_qc_ranges: dict) -> dict:
    ood, reason = is_out_of_distribution(qc_row, training_qc_ranges)
    if ood:
        return {"status": "cannot_score", "reason": reason}

    proba = pipeline.predict_proba(feature_row)[:, 1][0]
    return {"status": "scored", "probability": float(proba), "disclaimer": _DISCLAIMER}


_REQUIRED_MODEL_CARD_FIELDS = ["run_id", "git_sha", "cv_estimated_auc", "cv_estimated_ci",
                                "training_qc_ranges", "participants_tsv_sha256"]


def write_model_card(provenance: dict, out_path: Path) -> None:
    missing = [f for f in _REQUIRED_MODEL_CARD_FIELDS
               if not provenance.get(f) and provenance.get(f) != 0]
    if missing:
        raise ValueError(f"model card cannot be written: missing required fields {missing}")

    auc = provenance["cv_estimated_auc"]
    ci = provenance["cv_estimated_ci"]
    lines = [
        "# Model Card — PEARL-Neuro PSWT risk_vs_none classifier",
        "",
        f"**{_DISCLAIMER.upper()}.**",
        "",
        "## Intended use",
        "",
        "Research artifact only. This model does NOT demonstrate a usable predictive "
        "relationship between PSWT waveform-shape EEG features and genetic Alzheimer's-risk "
        f"group: its cross-validated performance (AUC {auc:.3f}) does not exceed chance or "
        "this project's nuisance-only reference line. It is shipped per project delivery "
        "requirements (phase_3.md §6), not because it is fit for prediction.",
        "",
        "## Out of scope",
        "",
        "- Any clinical, diagnostic, or screening use.",
        "- Any use presenting its output as a risk assessment for an individual.",
        "- Scoring recordings whose QC metrics fall outside the training cohort's range "
        "(the tool refuses these automatically, see 'Out-of-distribution refusal' below).",
        "",
        "## Training cohort and exclusions",
        "",
        f"- N = {provenance['n_training_subjects']} subjects.",
        "- Cohort: per-(subject, task) QC exclusion rule (Amendment 1, "
        "`reports/analysis_plan_frozen.md`), rest-task, `binary_risk_vs_none` primary target.",
        "- 15 of the original 79 subjects excluded by Phase 1/2 QC before this cohort was frozen.",
        "",
        "## CV-estimated performance (never a training-data number)",
        "",
        f"- AUC: **{auc:.3f}**",
        f"- 95% bootstrap CI: [{ci[0]:.3f}, {ci[1]:.3f}]",
        f"- Permutation p-value: {provenance.get('cv_estimated_p_value', float('nan')):.4f}",
        "- Full detail: `reports/phase3_results.md`",
        "",
        "## Known limitations",
        "",
        "- Underpowered at N=64 (see Amendment 2 §0f).",
        "- Positive control 1b (sex classification) also landed at chance — the feature "
        "pipeline's cross-subject generalisation is itself uncertain, independent of genotype.",
        "- Two of 20 declared PSWT features (`harmonic_amplitude_profile_h1_median`/`h1_iqr`) "
        "are tautologically constant and carry no information.",
        "",
        "## Out-of-distribution refusal",
        "",
        "The tool refuses to score any input whose QC metrics fall outside the training "
        "cohort's observed range:",
        "",
    ]
    for metric, (lo, hi) in provenance["training_qc_ranges"].items():
        lines.append(f"- `{metric}`: [{lo}, {hi}]")
    lines += [
        "",
        "## Provenance",
        "",
        f"- run_id: `{provenance['run_id']}`",
        f"- git_sha: `{provenance['git_sha']}`",
        f"- feature_config_hash: `{provenance.get('feature_config_hash', '')}`",
        f"- participants_tsv_sha256: `{provenance['participants_tsv_sha256']}`",
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_provenance_json(provenance: dict, out_path: Path) -> None:
    """Machine-readable twin of model_card.md, for pearl_models.inference to
    load without parsing Markdown (phase_4.md Task D)."""
    import json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
