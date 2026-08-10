"""Feature + label + nuisance assembly (phase_3.md).

Phase 3 is explicitly the only phase that touches the primary target — this
module is the sanctioned place labels are joined. It reads only the named
demographic columns from participants.tsv (age, sex, education, BDI, SES),
never the genotype columns (APOE_*, PICALM_*) also present in that file.
"""
from __future__ import annotations

import pandas as pd

from pearl_preproc.paths import PROJECT_ROOT, RAW_META_DIR, QC_DIR
from pearl_features.paths import FEATURES_DIR

LABELS_TSV = PROJECT_ROOT.parent / "data" / "labels" / "participants_labels.tsv"
PARTICIPANTS_TSV = RAW_META_DIR / "participants.tsv"

DEMOGRAPHIC_COLUMNS = ["age", "sex", "education", "BDI", "SES"]
QC_NUISANCE_COLUMNS = ["n_bad_channels", "n_ica_removed", "artifact_frac"]


def load_labels() -> pd.DataFrame:
    df = pd.read_csv(LABELS_TSV, sep="\t")
    return df.rename(columns={"task1_risk_vs_norisk": "risk_vs_none"})[
        ["subject_id", "group", "risk_vs_none"]]


def load_nuisance() -> pd.DataFrame:
    demo = pd.read_csv(PARTICIPANTS_TSV, sep="\t")[["participant_id", *DEMOGRAPHIC_COLUMNS]]
    demo = demo.rename(columns={"participant_id": "subject"}).set_index("subject")

    qc = pd.read_csv(QC_DIR / "qc_metrics.csv")
    qc_rest = qc[qc["task"].isin(["rest", "task-rest"])].set_index("subject")[QC_NUISANCE_COLUMNS]

    return demo.join(qc_rest, how="outer")


def load_pswt_features() -> pd.DataFrame:
    return pd.read_csv(FEATURES_DIR / "features_pswt.csv", index_col="subject")


def load_baseline_features() -> pd.DataFrame:
    return pd.read_csv(FEATURES_DIR / "features_baseline.csv", index_col="subject")


def assemble(feature_sets: dict[str, pd.DataFrame], labels: pd.DataFrame,
             nuisance: pd.DataFrame) -> pd.DataFrame:
    out = None
    for name, df in feature_sets.items():
        out = df if out is None else out.join(df, how="inner", rsuffix=f"_{name}")
    out = out.join(nuisance, how="left")
    labels_indexed = labels.set_index("subject_id")
    out = out.join(labels_indexed, how="left")
    out.index.name = "subject"
    return out
