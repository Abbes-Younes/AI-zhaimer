"""Tests for reconcile_groups.py — genotype normalisation and group derivation."""
from __future__ import annotations

import pytest

from pearl_audit.reconcile_groups import (
    normalise_apoe,
    normalise_picalm,
    derive_group,
    is_apoe_e4_carrier,
    is_apoe_e4_homozygote,
    load_client_groups,
    client_subject_set,
)


# ---------------------------------------------------------------------------
# APOE normalisation
# ---------------------------------------------------------------------------

class TestNormaliseApoe:
    """Test every APOE format observed in the wild, plus edge cases."""

    @pytest.mark.parametrize("raw,expected", [
        ("e3/e3", (3, 3)),
        ("3/3", (3, 3)),
        ("33", (3, 3)),
        ("E3E3", (3, 3)),
        ("e3/e4", (3, 4)),
        ("3/4", (3, 4)),
        ("34", (3, 4)),
        ("E3E4", (3, 4)),
        ("e4/e3", (4, 3)),
        ("e4/e4", (4, 4)),
        ("4/4", (4, 4)),
        ("44", (4, 4)),
        ("e2/e3", (2, 3)),
        ("e2/e4", (2, 4)),
        ("e2/e2", (2, 2)),
    ])
    def test_valid_formats(self, raw, expected):
        assert normalise_apoe(raw) == expected

    @pytest.mark.parametrize("raw", [
        "", "NA", "nan", "  ", None,
    ])
    def test_missing_values_raise(self, raw):
        with pytest.raises(ValueError, match="Missing"):
            normalise_apoe(raw)

    @pytest.mark.parametrize("raw", [
        "e5/e3", "foo", "e3/e3/e4", "abc",
    ])
    def test_malformed_raises(self, raw):
        with pytest.raises(ValueError):
            normalise_apoe(raw)


# ---------------------------------------------------------------------------
# PICALM normalisation
# ---------------------------------------------------------------------------

class TestNormalisePicalm:
    @pytest.mark.parametrize("raw,expected", [
        ("AA", "AA"), ("AG", "AG"), ("GG", "GG"),
        ("aa", "AA"), ("ag", "AG"), ("gg", "GG"),
        ("A/A", "AA"), ("A/G", "AG"), ("G/G", "GG"),
    ])
    def test_valid_formats(self, raw, expected):
        assert normalise_picalm(raw) == expected

    @pytest.mark.parametrize("raw", [
        "", "NA", "nan", None,
    ])
    def test_missing_values_raise(self, raw):
        with pytest.raises(ValueError, match="Missing"):
            normalise_picalm(raw)

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError):
            normalise_picalm("TT")


# ---------------------------------------------------------------------------
# Group derivation
# ---------------------------------------------------------------------------

class TestDeriveGroup:
    """Test group derivation rules from client_groups.yaml."""

    def test_n_group(self):
        assert derive_group("e3/e3", "AA") == "N"
        assert derive_group("e3/e3", "AG") == "N"

    def test_a_p_minus_group(self):
        assert derive_group("e3/e4", "AA") == "A_P_minus"
        assert derive_group("e4/e3", "AG") == "A_P_minus"
        assert derive_group("e4/e4", "AA") == "A_P_minus"

    def test_a_p_plus_group(self):
        assert derive_group("e3/e4", "GG") == "A_P_plus"
        assert derive_group("e4/e4", "GG") == "A_P_plus"
        assert derive_group("e4/e3", "GG") == "A_P_plus"

    def test_e3e3_with_risk_raises(self):
        """e3/e3 + GG doesn't fit any group — should raise."""
        with pytest.raises(ValueError):
            derive_group("e3/e3", "GG")


# ---------------------------------------------------------------------------
# Client groups loading
# ---------------------------------------------------------------------------

class TestClientGroups:
    def test_load_groups(self):
        groups = load_client_groups()
        assert "N" in groups
        assert "A_P_minus" in groups
        assert "A_P_plus" in groups

    def test_subject_totals(self):
        groups = load_client_groups()
        assert len(groups["N"]["subjects"]) == 31
        assert len(groups["A_P_minus"]["subjects"]) == 26
        assert len(groups["A_P_plus"]["subjects"]) == 22

    def test_disjoint(self):
        groups = load_client_groups()
        all_subjects = []
        for g in groups.values():
            all_subjects.extend(g["subjects"])
        assert len(all_subjects) == len(set(all_subjects)), "Duplicate subjects found"

    def test_sum_to_79(self):
        groups = load_client_groups()
        total = sum(len(g["subjects"]) for g in groups.values())
        assert total == 79

    def test_sub69_absent(self):
        groups = load_client_groups()
        all_subjects = []
        for g in groups.values():
            all_subjects.extend(g["subjects"])
        assert "sub-69" not in all_subjects

    def test_client_subject_set(self):
        groups = load_client_groups()
        mapping = client_subject_set(groups)
        assert mapping["sub-01"] == "N"
        assert mapping["sub-38"] == "A_P_minus"
        assert mapping["sub-32"] == "A_P_plus"


# ---------------------------------------------------------------------------
# Carrier/homozygote helpers
# ---------------------------------------------------------------------------

class TestCarrierHelpers:
    def test_e4_carrier(self):
        assert is_apoe_e4_carrier((3, 4)) is True
        assert is_apoe_e4_carrier((4, 4)) is True
        assert is_apoe_e4_carrier((3, 3)) is False

    def test_e4_homozygote(self):
        assert is_apoe_e4_homozygote((4, 4)) is True
        assert is_apoe_e4_homozygote((3, 4)) is False
        assert is_apoe_e4_homozygote((3, 3)) is False
