"""Label blindness (phase_1.md §2a) — enforced, not aspirational.

pearl_preproc must have no import path to the label-bearing artifacts
(client_groups.yaml, cohort_definition.csv, genotype columns). This test scans
every source file and fails on the first forbidden reference.

Exactly two modules are sanctioned exceptions:
- ``report_qc.py`` — the ONLY place labels are joined, and only AFTER the
  exclusion list is frozen, to report per-group attrition (phase_1.md §3).
- ``analysis_plan.py`` — a document writer that must name the Phase 2 primary
  target framing in prose (phase_1.md §5); it processes no subject data.

Everything else — download, preprocess, QC thresholds, budget, config — must be
clean. This test fails on the first violation in a processing module.
"""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "pearl_preproc"

# Modules allowed to mention labels (spec-sanctioned, documented above).
SANCTIONED = {"report_qc.py", "analysis_plan.py"}

# Any of these in a processing module is a label-blindness violation.
FORBIDDEN = [
    "client_groups",
    "cohort_definition",
    "genotype",
    "final_include",
    "A_P_plus",
    "A_P_minus",
    "risk_vs_none",       # the Phase 2 primary target framing
    "pearl_audit",        # no import path into the audit package at all
]


def _processing_files():
    return [f for f in sorted(SRC.rglob("*.py"))
            if f.name not in SANCTIONED]


def test_processing_modules_have_no_label_references():
    offenders = []
    for f in _processing_files():
        text = f.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                offenders.append(f"{f.name}: {token}")
    assert not offenders, f"label-blindness violations: {offenders}"


def test_no_import_of_label_modules():
    offenders = []
    for f in _processing_files():
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith(("import ", "from ")):
                if any(t in line for t in ["pearl_audit", "reconcile_groups",
                                           "client_groups", "cohort"]):
                    offenders.append(f"{f.name}: {line.strip()}")
    assert not offenders, f"forbidden imports: {offenders}"


def test_only_sanctioned_modules_may_touch_labels():
    """If a non-sanctioned module ever needs labels, this test forces a review."""
    for f in _processing_files():
        text = f.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            assert token not in text, (
                f"{f.name} references {token!r}; only {sorted(SANCTIONED)} may "
                f"touch labels, and only post-freeze / in prose")


def test_config_is_label_free():
    cfg_path = SRC.parent.parent / "config" / "preproc.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in text, f"preproc.yaml mentions {token!r}"
