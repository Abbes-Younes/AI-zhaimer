"""BrainVision triplet validation (phase_1.md §1).

Every recording is .eeg + .vhdr + .vmrk. A .vhdr whose DataFile/MarkerFile
point at files we do not actually have is a silent corruption and must be
caught before preprocessing. Pure functions — no MNE dependency.
"""
from __future__ import annotations

import re
from pathlib import Path


class TripletError(Exception):
    """A BrainVision triplet is incomplete or internally inconsistent."""


def parse_vhdr_links(vhdr_path: Path) -> dict:
    """Extract DataFile/MarkerFile fields from a .vhdr header."""
    text = vhdr_path.read_text(encoding="latin-1")
    out: dict[str, str] = {}
    for field in ("DataFile", "MarkerFile"):
        m = re.search(rf"^{field}=(.+)$", text, re.M)
        out[field] = m.group(1).strip() if m else ""
    return out


def validate_triplet(vhdr_path: Path) -> dict:
    """Validate that *vhdr_path*'s referenced .eeg and .vmrk exist.

    Returns a dict of resolved paths. Raises TripletError with a specific
    reason (missing .eeg → "orphaned .vhdr"; marker mismatch; zero-size .eeg).

    Tolerates one specific, verifiable discrepancy (remediation 2026-08-09,
    sub-52): some ds004796 headers still carry the pre-BIDS recording
    basename in DataFile/MarkerFile (e.g. ``Q5ER_rest.eeg``) while the actual
    files on disk use the canonical BIDS name. This is accepted ONLY when the
    canonical siblings (``<vhdr.stem>.eeg`` / ``.vmrk``) exist AND the
    sibling ``.vmrk`` itself declares the SAME stale DataFile — i.e. the
    rename is internally consistent, not a random mismatch. Any other
    mismatch still raises. The returned dict flags ``header_discrepancy``
    so it can be recorded in the derivative's provenance.
    """
    if not vhdr_path.exists():
        raise TripletError(f"vhdr missing: {vhdr_path}")
    if vhdr_path.suffix.lower() != ".vhdr":
        raise TripletError(f"not a .vhdr file: {vhdr_path}")

    links = parse_vhdr_links(vhdr_path)
    datafile = links.get("DataFile") or ""
    markerfile = links.get("MarkerFile") or ""

    if not datafile:
        raise TripletError(f"{vhdr_path.name}: .vhdr has no DataFile field")
    if not markerfile:
        raise TripletError(f"{vhdr_path.name}: .vhdr has no MarkerFile field")

    eeg_path = vhdr_path.parent / datafile
    vmrk_path = vhdr_path.parent / markerfile
    header_discrepancy = False

    if not eeg_path.exists() or not vmrk_path.exists():
        sib_eeg = vhdr_path.with_suffix(".eeg")
        sib_vmrk = vhdr_path.with_suffix(".vmrk")
        if sib_eeg.exists() and sib_vmrk.exists():
            sib_text = sib_vmrk.read_text(encoding="latin-1", errors="replace")
            m = re.search(r"^DataFile=(.+)$", sib_text, re.M)
            sib_declared = m.group(1).strip() if m else None
            if sib_declared == datafile:
                eeg_path, vmrk_path = sib_eeg, sib_vmrk
                header_discrepancy = True

    if not eeg_path.exists():
        raise TripletError(
            f"ORPHANED .vhdr: {vhdr_path.name} points at DataFile={datafile} "
            f"which does not exist on disk")
    if not vmrk_path.exists():
        raise TripletError(
            f"{vhdr_path.name}: MarkerFile={markerfile} does not exist on disk")
    if eeg_path.stat().st_size == 0:
        raise TripletError(f"{eeg_path.name}: zero-byte .eeg file")

    # The marker file must name the .eeg it describes (sanity cross-check).
    marker_text = vmrk_path.read_text(encoding="latin-1", errors="replace")
    m = re.search(r"^DataFile=(.+)$", marker_text, re.M)
    if m and m.group(1).strip() not in (datafile, eeg_path.name):
        raise TripletError(
            f"{vmrk_path.name} references DataFile={m.group(1)!r} but the "
            f".vhdr declares {datafile!r} — inconsistent triplet")

    return {
        "vhdr": str(vhdr_path),
        "eeg": str(eeg_path),
        "vmrk": str(vmrk_path),
        "datafile": datafile,
        "markerfile": markerfile,
        "header_discrepancy": header_discrepancy,
        "declared_datafile": datafile if header_discrepancy else None,
    }


def find_valid_triplets(eeg_dir: Path) -> dict[str, dict]:
    """Validate every .vhdr in *eeg_dir*; return {stem: resolved triplet}.

    Raises TripletError on the first invalid triplet (the caller decides
    whether to quarantine the subject).
    """
    if not eeg_dir.exists():
        return {}
    triplets: dict[str, dict] = {}
    for vhdr in sorted(eeg_dir.glob("*.vhdr")):
        triplets[vhdr.stem] = validate_triplet(vhdr)
    return triplets
