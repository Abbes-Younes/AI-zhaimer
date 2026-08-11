"""Driver for phase_5.md §0b's ICA n_components comparison (Task 2 of the
Stage 1 plan). Ad-hoc, run-once script -- not part of the CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pearl_preproc.config import load_preproc_config
from pearl_preproc.ica_component_eval import compare_n_components
from pearl_preproc.paths import DATA_DIR

SUBJECTS_TASKS = [
    ("sub-50", "rest"), ("sub-05", "msit"), ("sub-03", "msit"),
    ("sub-54", "rest"), ("sub-36", "rest"), ("sub-57", "msit"),
    ("sub-30", "rest"), ("sub-70", "rest"), ("sub-45", "rest"),
    ("sub-56", "msit"),
]

if __name__ == "__main__":
    cfg = load_preproc_config()
    scratch_dir = DATA_DIR / "phase5_scratch" / "ica_n_components_eval"
    df = compare_n_components(SUBJECTS_TASKS, cfg, scratch_dir)
    out_csv = DATA_DIR / "phase5_scratch" / "ica_n_components_eval_results.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(df.to_string(index=False))
    print(f"\nwrote {out_csv}")
