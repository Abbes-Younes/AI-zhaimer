"""Label blindness for pearl_features (phase_2.md §2, extending phase_1.md §2a).

Only confound_gate.py is sanctioned to touch group labels, and only to measure
contamination (phase_2.md §1) — it never feeds labels into feature extraction.
"""
from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "pearl_features"
SANCTIONED = {"confound_gate.py"}
FORBIDDEN = [
    "client_groups", "cohort_definition", "genotype", "final_include",
    "A_P_plus", "A_P_minus", "risk_vs_none", "pearl_audit",
    "participants_labels",
]


def _processing_files():
    if not SRC.exists():
        return []
    return [f for f in sorted(SRC.rglob("*.py")) if f.name not in SANCTIONED]


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
                if any(t in line for t in ["pearl_audit", "reconcile_groups", "client_groups"]):
                    offenders.append(f"{f.name}: {line.strip()}")
    assert not offenders, f"forbidden imports: {offenders}"


def test_features_yaml_is_label_free():
    cfg_path = SRC.parent.parent / "config" / "features.yaml"
    if not cfg_path.exists():
        return  # created in Task 12; nothing to violate yet
    text = cfg_path.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in text, f"features.yaml mentions {token!r}"
