"""phase_5.md §0c: Sternberg must be included in the full-EEG download scope
now that Stage 1 ingests all three tasks.
"""
from __future__ import annotations

import pandas as pd

from pearl_audit.download_plan import build_scopes


def test_full_eeg_scope_includes_sternberg():
    size_df = pd.DataFrame({
        "task": ["rest", "msit", "sternberg", "rest"],
        "subject": ["sub-01", "sub-01", "sub-01", "sub-02"],
        "bytes": [100, 100, 100, 100],
        "modality": ["eeg", "eeg", "eeg", "eeg"],
    })
    scopes = build_scopes(size_df)
    assert "sternberg" in scopes["A_full_eeg"]["tasks"]
