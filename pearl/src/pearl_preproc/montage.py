"""Montage construction for the actiCAP 128-channel recordings.

The recorded layout is the extended 10-5 system: 125/127 channel names match
``standard_1005`` exactly (verified against sub-01's .vhdr). The two remaining
actiCAP-specific sites, O9 and O10 (far lateral occipital), are placed as the
normalized mean of their natural neighbours' unit vectors, scaled to the head
radius. The .vhdr's own [Coordinates] section was tested against several
spherical conventions and matches none well (residual ~0.67), so it is not
used; standard_1005 geometry is authoritative for the 125 shared sites.
"""
from __future__ import annotations

import re
from pathlib import Path

import mne
import numpy as np


def _vhdr_channel_names(vhdr_path: Path) -> list[str]:
    text = vhdr_path.read_text(encoding="latin-1")
    return re.findall(r"^Ch\d+=(.+?),,", text, re.M)


def build_montage(vhdr_path: Path, head_radius_m: float = 0.085) -> mne.channels.DigMontage:
    """Build a montage covering all channels of *vhdr_path*.

    Uses ``standard_1005`` for the 125 shared sites and places O9/O10 as
    neighbour-averaged positions. Raises if any vhdr channel is uncovered.
    """
    names = _vhdr_channel_names(vhdr_path)
    montage = mne.channels.make_standard_montage("standard_1005")
    pos = montage.get_positions()["ch_pos"]

    missing = [n for n in names if n not in pos]
    if not missing:
        return montage

    # Place missing sites (expected: O9/O10) from neighbour averages.
    neighbors = {
        "O9": ["PO9", "OI1h", "POO9h"],
        "O10": ["PO10", "OI2h", "POO10h"],
    }
    extra: dict[str, np.ndarray] = {}
    for name in missing:
        nb = neighbors.get(name)
        if not nb or any(n not in pos for n in nb):
            raise ValueError(
                f"channel {name} not in standard_1005 and no usable neighbours "
                f"({nb}) — refusing to invent a montage position")
        unit = np.mean([pos[n] / np.linalg.norm(pos[n]) for n in nb], axis=0)
        extra[name] = unit / np.linalg.norm(unit) * head_radius_m

    all_pos = {**pos, **extra}
    # MNE 1.12 signature: make_dig_montage(ch_pos, nasion, lpa, rpa, ...)
    fid = montage.get_positions()
    combined = mne.channels.make_dig_montage(
        ch_pos=all_pos, nasion=fid.get("nasion"), lpa=fid.get("lpa"),
        rpa=fid.get("rpa"), coord_frame="head")
    return combined
