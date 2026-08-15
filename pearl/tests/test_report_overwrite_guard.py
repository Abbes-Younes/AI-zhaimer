"""phase_7.md §3 — report writers must not silently overwrite existing
deliverables, and must not hardcode result-describing prose.

Both failure modes are real and already happened in this project:
- Phase 5 required manual archive-before-run at every stage because report
  writers overwrite fixed paths in place.
- A null-assuming narrative shipped unmodified alongside a positive result and
  had to be corrected after the fact (reports/phase5_stage3_checkpoint.md).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from pearl_preproc.paths import ReportOverwriteError, guarded_write

SRC = Path(__file__).resolve().parent.parent / "src"


def test_guarded_write_creates_new_file(tmp_path):
    target = tmp_path / "report.md"
    guarded_write(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_guarded_write_refuses_to_overwrite_by_default(tmp_path):
    target = tmp_path / "report.md"
    target.write_text("original deliverable", encoding="utf-8")

    with pytest.raises(ReportOverwriteError):
        guarded_write(target, "new content")

    # the original must be untouched by the refused write
    assert target.read_text(encoding="utf-8") == "original deliverable"


def test_guarded_write_archives_then_writes_when_allowed(tmp_path):
    target = tmp_path / "report.md"
    target.write_text("original deliverable", encoding="utf-8")

    guarded_write(target, "new content", allow_overwrite=True)

    assert target.read_text(encoding="utf-8") == "new content"
    archived = list(tmp_path.glob("report.md.bak-*"))
    assert len(archived) == 1, "the prior version must be archived, never discarded"
    assert archived[0].read_text(encoding="utf-8") == "original deliverable"


def test_guarded_write_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "run-123" / "report.md"
    guarded_write(target, "body")
    assert target.read_text(encoding="utf-8") == "body"


def test_repeated_allowed_overwrites_do_not_collide(tmp_path):
    """Two archived versions must both survive -- an archive scheme that
    collides would silently destroy the very thing it exists to protect."""
    target = tmp_path / "report.md"
    target.write_text("v1", encoding="utf-8")
    guarded_write(target, "v2", allow_overwrite=True)
    guarded_write(target, "v3", allow_overwrite=True)

    archived = sorted(p.read_text(encoding="utf-8") for p in tmp_path.glob("report.md.bak-*"))
    assert archived == ["v1", "v2"]
    assert target.read_text(encoding="utf-8") == "v3"


# --- no hardcoded result-describing prose in report modules -----------------

_REPORT_MODULES = [
    SRC / "pearl_models" / "reports.py",
    SRC / "pearl_preproc" / "report_qc.py",
    SRC / "pearl_preproc" / "analysis_plan.py",
    SRC / "pearl_features" / "confound_gate_report.py",
]

# A bare AUC-like decimal sitting in a prose string is the signature of a
# hardcoded result. Config-driven reference lines are read from cfg, not typed
# into a sentence.
_HARDCODED_RESULT = re.compile(
    r"(AUC\s*0\.\d+)"          # "AUC 0.474"
    r"|(verdict\s*\(frozen)"     # "verdict (frozen: NULL, ...)"
    , re.IGNORECASE)


@pytest.mark.parametrize("module", _REPORT_MODULES, ids=lambda p: p.name)
def test_report_module_has_no_hardcoded_result_prose(module):
    """phase_7.md §3: 'Delete every hardcoded result-describing sentence.
    Narrative text is generated from the computed numbers or it is not
    generated at all.'"""
    if not module.exists():
        pytest.skip(f"{module.name} not present")
    offenders = [
        f"{module.name}:{i}: {line.strip()[:100]}"
        for i, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1)
        if _HARDCODED_RESULT.search(line)
    ]
    assert not offenders, (
        "report modules must not hardcode a result in prose -- a re-run would "
        "emit a stale or factually wrong claim:\n" + "\n".join(offenders))
