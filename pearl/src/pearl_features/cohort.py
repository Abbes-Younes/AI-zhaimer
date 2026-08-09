"""Per-(subject, task) exclusion (phase_2.md §0a).

Reuses the existing per-row `verdict` column in qc_metrics.csv unchanged — no
new threshold logic. A (subject, task) pair is excluded iff its own row's
verdict == "fail". This is the rule-change-not-threshold-change phase_2.md
§0a requires: the collapse to subject level lived only in
pearl_preproc.qc.freeze_exclusions, and Phase 2 simply does not apply that
collapse.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pearl_preproc.paths import QC_DIR


def load_qc_metrics() -> pd.DataFrame:
    return pd.read_csv(QC_DIR / "qc_metrics.csv")


def per_task_cohort(qc: pd.DataFrame) -> pd.DataFrame:
    out = qc[["subject", "task", "verdict"]].copy()
    out["included"] = out["verdict"] != "fail"
    return out.reset_index(drop=True)


def rest_cohort_n(per_task: pd.DataFrame) -> int:
    is_rest = per_task["task"].isin(["rest", "task-rest"])
    return int((is_rest & per_task["included"]).sum())


def write_cohort_csv(per_task: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    per_task.to_csv(out_path, index=False)
