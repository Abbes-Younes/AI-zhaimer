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


def _levenshtein(a: str, b: str) -> int:
    """Edit distance between *a* and *b* (no external dependency needed)."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def _near(a: str, b: str, max_distance: int = 2) -> bool:
    return a == b or _levenshtein(a, b) <= max_distance


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

    Tolerates two specific, verifiable discrepancy patterns seen in ds004796.
    Both require the canonical siblings (``<vhdr.stem>.eeg`` / ``.vmrk``) to
    exist; any other mismatch still raises.

    1. Stale pre-BIDS rename (remediation 2026-08-09, sub-52): DataFile/
       MarkerFile carry the pre-BIDS recording basename (e.g.
       ``Q5ER_rest.eeg``) while the sibling files on disk use the canonical
       BIDS name. Accepted only when the sibling ``.vmrk`` itself declares
       the SAME stale DataFile — i.e. the rename is internally consistent,
       not a random mismatch.
    2. One-off header typo (remediation 2026-08-12, sub-29/sub-57): DataFile
       and/or MarkerFile is a small (edit distance <= 2) corruption of the
       canonical filename itself — a dropped/duplicated character, e.g.
       ``sub-29_task-sternbeg_eeg.eeg`` for ``..._sternberg_...`` or
       ``sub-57_task-sternberg_eeg..vmrk`` with a stray extra dot. Accepted
       only when BOTH the declared DataFile and declared MarkerFile are near
       the canonical sibling filenames — a single field being close is not
       enough corroboration on its own.

    The returned dict flags ``header_discrepancy`` so it can be recorded in
    the derivative's provenance.
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
            consistent_stale_rename = sib_declared == datafile
            near_miss_typo = (_near(datafile, sib_eeg.name)
                               and _near(markerfile, sib_vmrk.name))
            if consistent_stale_rename or near_miss_typo:
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
    # When header_discrepancy already holds, the header text is known to be
    # unreliable (that's why we fell back to canonical siblings) — cross-
    # checking it against itself is only useful as an extra guard against a
    # wildly different name, not against the same near-miss typo pattern.
    marker_text = vmrk_path.read_text(encoding="latin-1", errors="replace")
    m = re.search(r"^DataFile=(.+)$", marker_text, re.M)
    if m and m.group(1).strip() not in (datafile, eeg_path.name):
        declared = m.group(1).strip()
        if not (header_discrepancy and _near(declared, eeg_path.name)):
            raise TripletError(
                f"{vmrk_path.name} references DataFile={declared!r} but the "
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
