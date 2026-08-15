"""Phase 5 Stage 3 validation, Step 2 prep: confirms the restored production
preprocessing tree (both fixes applied, config/preproc.yaml back at its
permanent defaults) reproduces Stage 3's headline numbers at FULL precision
(frozen config/models.yaml, unmodified -- 1000 permutations / 2000
bootstrap), after two isolation diagnostic runs at reduced precision
overwrote the live features/preproc trees in between.

Run from `pearl/`: PYTHONPATH=src python scripts/phase5_stage3_confirm_restore.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pearl_models.paths import CONFIG_DIR, REPORTS_DIR, make_run_id, git_sha
from pearl_models.primary import run_primary_analysis


def fmt_ci(ci) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def main() -> None:
    cfg = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    result = run_primary_analysis(cfg)
    fo = result["features_only"]
    fn = result["features_plus_nuisance"]
    no = result["nuisance_only"]

    print(f"n_subjects_used={fo['n_subjects_used']}")
    print(f"features_only: auc={fo['auc']:.4f} ci={fmt_ci(fo['ci'])} p={fo['p_value']:.4f}")
    print(f"features_plus_nuisance: auc={fn['auc']:.4f} ci={fmt_ci(fn['ci'])} p={fn['p_value']:.4f}")
    print(f"nuisance_only: auc={no['auc']:.4f} ci={fmt_ci(no['ci'])} p={no['p_value']:.4f}")

    meta_dir = REPORTS_DIR.parent / "data" / "derivatives" / "models_stage3"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "confirm_restore_meta.json").write_text(json.dumps({
        "run_id": make_run_id(), "git_sha": git_sha(),
        "features_only_auc": fo["auc"], "features_only_ci": list(fo["ci"]),
        "features_only_p": fo["p_value"], "n_subjects_used": fo["n_subjects_used"],
        "nuisance_only_auc": no["auc"], "nuisance_only_ci": list(no["ci"]),
    }, indent=2) + "\n", encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
