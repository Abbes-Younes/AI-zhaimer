"""§3 — the single inference path both the CLI and the thin API call:
BIDS EEG in -> Phase 1 preprocessing -> Phase 2 features -> calibrated
score with uncertainty and the OOD refusal -> JSON out.

Assumes `bids_dir` follows this project's raw layout convention
(sub-XX/eeg/sub-XX_task-rest_eeg.{vhdr,eeg,vmrk}), the same layout
pearl_preproc.preprocess.raw_paths_for expects -- documented in
RUNBOOK.md. A fully generic arbitrary-BIDS-directory reader is out of
scope; this project's reusable pipeline code is tied to ds004796's layout.
"""
from __future__ import annotations

from pathlib import Path

# Single source of truth, imported rather than duplicated: this module is the
# path the container and API actually serve, and it previously carried its own
# copy of the disclaimer -- so strengthening the one in delivery.py silently
# left the shipped surface on the old, weaker wording (phase_7.md §1).
from pearl_models.delivery import _DISCLAIMER  # noqa: E402


def _preprocess_subject(bids_dir: str | Path, subject: str, task: str = "rest") -> dict:
    """Runs Phase 1 preprocessing for one subject/task, returns its QC row
    (n_bad_channels, n_ica_removed, artifact_frac, iaf_hz, ...)."""
    from pearl_preproc.config import load_preproc_config
    from pearl_preproc.preprocess import process_subject_task

    cfg = load_preproc_config()
    return process_subject_task(subject, task, cfg)


def _extract_features(subject: str, qc_row: dict, feature_columns: list[str]) -> list[list[float]]:
    """Runs Phase 2 PSWT feature extraction, returns a single-row matrix in
    the exact column order the shipped model was trained on."""
    from pearl_features.features import compute_subject_features, load_features_config

    features_cfg = load_features_config()
    feats, _meta = compute_subject_features(subject, features_cfg, qc_row["iaf_hz"])
    return [[feats.get(c, float("nan")) for c in feature_columns]]


def _load_model(model_dir: str | Path) -> tuple[dict, object]:
    """Loads the shipped model + its provenance (model_card's structured
    twin -- provenance.json, written alongside model_card.md at delivery
    time) from model_dir."""
    import json
    import joblib

    model_dir = Path(model_dir)
    pipeline = joblib.load(model_dir / "model_final.joblib")
    provenance = json.loads((model_dir / "provenance.json").read_text(encoding="utf-8"))
    return provenance, pipeline


def score_bids_subject(bids_dir: str | Path, subject: str, model_dir: str | Path) -> dict:
    from pearl_models.delivery import is_out_of_distribution

    qc_row = _preprocess_subject(bids_dir, subject)
    provenance, pipeline = _load_model(model_dir)

    ood, reason = is_out_of_distribution(qc_row, provenance["training_qc_ranges"])
    if ood:
        return {"status": "cannot_score", "reason": reason, "actionable": False,
                "not_validated": True, "disclaimer": _DISCLAIMER,
                "run_id": provenance.get("run_id"), "git_sha": provenance.get("git_sha")}

    feature_row = _extract_features(subject, qc_row, provenance["feature_columns"])
    proba = pipeline.predict_proba(feature_row)[:, 1][0]
    return {"status": "scored", "probability": float(proba), "actionable": False,
            "not_validated": True, "disclaimer": _DISCLAIMER,
            "run_id": provenance.get("run_id"), "git_sha": provenance.get("git_sha")}
