"""Phase 2 paths. Mirrors pearl_preproc.paths conventions; not label-bearing
(exempt from the label-blindness scan the same way pearl_preproc.paths is)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pearl_preproc.paths import (  # noqa: F401  (re-exported on purpose)
    PROJECT_ROOT, DATA_DIR, CONFIG_DIR, REPORTS_DIR,
    make_run_id, get_run_id, set_run_id, sha256_file, git_sha,
)

PHASE2_DIR = DATA_DIR / "derivatives" / "phase2"
FEATURES_DIR = DATA_DIR / "derivatives" / "features"
FEATURES_YAML = CONFIG_DIR / "features.yaml"


def staging_dir(base: Path) -> Path:
    run_id = get_run_id()
    if run_id:
        return base / f".tmp-{run_id}"
    return base


def finalize_staged(base: Path) -> None:
    """Swap base/.tmp-<run_id>/* into base/, matching pearl_preproc.paths.finalize_run."""
    run_id = get_run_id()
    if not run_id:
        return
    tmp = base / f".tmp-{run_id}"
    base.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        for item in tmp.iterdir():
            dest = base / item.name
            if dest.exists():
                shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(tmp, ignore_errors=True)
    (base / "_meta.json").write_text(
        json.dumps({"run_id": run_id, "finalized_at": datetime.now(timezone.utc).isoformat()},
                   indent=2) + "\n", encoding="utf-8")
