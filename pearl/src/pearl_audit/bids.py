"""BIDS entity parsing (phase_0,5.md Task 1).

Replaces the fragile ``re.match(r"task-(\\w+)", fname)`` approach with a
real parser that understands BIDS entities generically (``sub-``, ``task-``,
``acq-``, ``run-``, ``ses-``, ...), so the same code keeps working when new
entities appear in the listing.
"""
from __future__ import annotations

from pathlib import Path


def parse_bids_entities(path: str) -> dict:
    """Parse BIDS entities from a file path or filename.

    Parameters
    ----------
    path : str
        A BIDS-style path or bare filename, e.g. ``sub-80/eeg/sub-80_task-msit_eeg.eeg``.

    Returns
    -------
    dict
        A dict with keys ``sub``, ``task``, ``run``, ``suffix``, ``ext``
        (``None`` when absent) plus any other entities present (``acq``,
        ``ses``, ...). Returns ``{}`` for names that carry no entities at all
        (e.g. ``dataset_description.json``, ``participants.tsv``).

    Notes
    -----
    Pure, side-effect free, and never raises on a malformed name — malformed
    chunks are skipped and the caller decides what to do with the result.
    """
    name = Path(str(path)).name

    # Extensions — handle compound extensions like .nii.gz
    suffixes = Path(name).suffixes
    ext = "".join(suffixes) if suffixes else None
    stem = name[: -len(ext)] if ext else name

    chunks = stem.split("_")

    entities: dict[str, str] = {}
    suffix: str | None = None

    for idx, chunk in enumerate(chunks):
        if "-" in chunk:
            # key-value entity chunk, e.g. "task-msit", "sub-80", "acq-AP-PA"
            key, _, value = chunk.partition("-")
            key = key.strip().lower()
            value = value.strip()
            if key and value:
                entities[key] = value
        elif idx == len(chunks) - 1:
            # final chunk without a '-' is the suffix (eeg, bold, T1w, ...)
            suffix = chunk

    if not entities:
        return {}

    result: dict = {
        "sub": entities.get("sub"),
        "task": entities.get("task"),
        "run": entities.get("run"),
        "suffix": suffix,
        "ext": ext,
    }
    # Surface any additional entities (acq, ses, desc, ...) as-is
    for k, v in entities.items():
        if k not in result:
            result[k] = v
    return result
