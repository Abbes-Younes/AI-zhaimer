"""BrainVision triplet validation (phase_1.md §6)."""
from __future__ import annotations

import pytest

from pearl_preproc.triplets import TripletError, find_valid_triplets, validate_triplet

VHDR_TMPL = """Brain Vision Data Exchange Header File Version 1.0

[Common Infos]
DataFile={datafile}
MarkerFile={markerfile}
NumberOfChannels=2
SamplingInterval=1000

[Binary Infos]
BinaryFormat=IEEE_FLOAT_32
"""

VMRK_TMPL = """Brain Vision Data Exchange Marker File Version 1.0

[Common Infos]
DataFile={datafile}
"""


def _make_triplet(tmp_path, stem="sub-01_task-msit_eeg", orphan=False):
    d = tmp_path / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    datafile = f"{stem}.eeg"
    markerfile = f"{stem}.vmrk"
    (d / f"{stem}.vhdr").write_text(
        VHDR_TMPL.format(datafile=datafile, markerfile=markerfile),
        encoding="latin-1")
    if not orphan:
        (d / datafile).write_bytes(b"\x00" * 64)
    (d / markerfile).write_text(VMRK_TMPL.format(datafile=datafile), encoding="latin-1")
    return d / f"{stem}.vhdr"


def test_valid_triplet_passes(tmp_path):
    vhdr = _make_triplet(tmp_path)
    result = validate_triplet(vhdr)
    assert result["datafile"] == "sub-01_task-msit_eeg.eeg"
    assert result["eeg"].endswith(".eeg")
    assert result["vmrk"].endswith(".vmrk")


def test_valid_sternberg_triplet_passes(tmp_path):
    # phase_5.md §0c: triplet validation is task-name-agnostic; confirm a
    # third task (sternberg) is accepted with no code change needed.
    vhdr = _make_triplet(tmp_path, stem="sub-01_task-sternberg_eeg")
    result = validate_triplet(vhdr)
    assert result["datafile"] == "sub-01_task-sternberg_eeg.eeg"


def test_orphaned_vhdr_detected(tmp_path):
    vhdr = _make_triplet(tmp_path, orphan=True)
    with pytest.raises(TripletError) as exc:
        validate_triplet(vhdr)
    assert "ORPHANED" in str(exc.value)


def test_markerfile_missing(tmp_path):
    vhdr = _make_triplet(tmp_path)
    vhdr.parent.joinpath("sub-01_task-msit_eeg.vmrk").unlink()
    with pytest.raises(TripletError):
        validate_triplet(vhdr)


def test_zero_byte_eeg_rejected(tmp_path):
    vhdr = _make_triplet(tmp_path)
    vhdr.parent.joinpath("sub-01_task-msit_eeg.eeg").write_bytes(b"")
    with pytest.raises(TripletError) as exc:
        validate_triplet(vhdr)
    assert "zero-byte" in str(exc.value)


def test_vhdr_vmrk_inconsistent(tmp_path):
    vhdr = _make_triplet(tmp_path)
    vhdr.parent.joinpath("sub-01_task-msit_eeg.vmrk").write_text(
        VMRK_TMPL.format(datafile="something-else.eeg"), encoding="latin-1")
    with pytest.raises(TripletError) as exc:
        validate_triplet(vhdr)
    assert "inconsistent" in str(exc.value)


def test_find_valid_triplets_keys(tmp_path):
    _make_triplet(tmp_path, stem="sub-01_task-msit_eeg")
    _make_triplet(tmp_path, stem="sub-01_task-rest_eeg")
    found = find_valid_triplets(tmp_path / "eeg")
    assert set(found) == {"sub-01_task-msit_eeg", "sub-01_task-rest_eeg"}


def _make_stale_header_triplet(tmp_path, stem="sub-52_task-rest_eeg", stale="Q5ER_rest"):
    """A .vhdr/.vmrk that still name the pre-BIDS recording (sub-52 case):
    DataFile/MarkerFile point at `stale`, but the actual sibling files on disk
    use the canonical BIDS stem."""
    d = tmp_path / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.vhdr").write_text(
        VHDR_TMPL.format(datafile=f"{stale}.eeg", markerfile=f"{stale}.vmrk"),
        encoding="latin-1")
    (d / f"{stem}.eeg").write_bytes(b"\x00" * 64)
    (d / f"{stem}.vmrk").write_text(
        VMRK_TMPL.format(datafile=f"{stale}.eeg"), encoding="latin-1")
    return d / f"{stem}.vhdr"


def test_stale_bids_rename_resolves_to_siblings(tmp_path):
    vhdr = _make_stale_header_triplet(tmp_path)
    result = validate_triplet(vhdr)
    assert result["eeg"].endswith("sub-52_task-rest_eeg.eeg")
    assert result["vmrk"].endswith("sub-52_task-rest_eeg.vmrk")
    assert result["header_discrepancy"] is True
    assert result["declared_datafile"] == "Q5ER_rest.eeg"


def test_stale_rename_still_rejects_true_orphan(tmp_path):
    # Declared name doesn't exist, AND no canonical sibling exists either.
    d = tmp_path / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sub-52_task-rest_eeg.vhdr").write_text(
        VHDR_TMPL.format(datafile="Q5ER_rest.eeg", markerfile="Q5ER_rest.vmrk"),
        encoding="latin-1")
    with pytest.raises(TripletError) as exc:
        validate_triplet(d / "sub-52_task-rest_eeg.vhdr")
    assert "ORPHANED" in str(exc.value)


def test_stale_rename_rejects_inconsistent_stems(tmp_path):
    # vhdr and vmrk declare DIFFERENT stale names -> not a clean rename, reject.
    d = tmp_path / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    stem = "sub-52_task-rest_eeg"
    (d / f"{stem}.vhdr").write_text(
        VHDR_TMPL.format(datafile="Q5ER_rest.eeg", markerfile="Q5ER_rest.vmrk"),
        encoding="latin-1")
    (d / f"{stem}.eeg").write_bytes(b"\x00" * 64)
    (d / f"{stem}.vmrk").write_text(
        VMRK_TMPL.format(datafile="SOMETHING_ELSE.eeg"), encoding="latin-1")
    with pytest.raises(TripletError):
        validate_triplet(d / f"{stem}.vhdr")
