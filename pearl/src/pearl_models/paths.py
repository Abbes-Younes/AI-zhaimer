"""Phase 3 paths. Mirrors pearl_features.paths conventions."""
from __future__ import annotations

from pearl_preproc.paths import (  # noqa: F401  (re-exported on purpose)
    PROJECT_ROOT, DATA_DIR, CONFIG_DIR, REPORTS_DIR,
    make_run_id, get_run_id, set_run_id, sha256_file, git_sha,
)

MODELS_DIR = DATA_DIR / "derivatives" / "models"
MODELS_YAML = CONFIG_DIR / "models.yaml"
