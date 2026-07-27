"""One-off script: generates participants_labels.tsv from the subject ID
lists in reference/classification.pdf (transcribed by hand below)."""
import csv
from pathlib import Path

GROUP_N = [f"sub-{i:02d}" for i in range(1, 32)]  # sub-01..sub-31

GROUP_APM = [  # A+P-, "risque simple"
    "sub-38", "sub-47", "sub-53", "sub-57", "sub-58", "sub-59", "sub-60",
    "sub-61", "sub-62", "sub-63", "sub-64", "sub-65", "sub-66", "sub-67",
    "sub-68", "sub-70", "sub-71", "sub-72", "sub-73", "sub-74", "sub-75",
    "sub-76", "sub-77", "sub-78", "sub-79", "sub-80",
]

GROUP_APP = [  # A+P+, "double risque"
    "sub-32", "sub-33", "sub-34", "sub-35", "sub-36", "sub-37", "sub-39",
    "sub-40", "sub-41", "sub-42", "sub-43", "sub-44", "sub-45", "sub-46",
    "sub-48", "sub-49", "sub-50", "sub-51", "sub-52", "sub-54", "sub-55",
    "sub-56",
]

assert len(GROUP_N) == 31
assert len(GROUP_APM) == 26
assert len(GROUP_APP) == 22

ROWS = []
for sid in GROUP_N:
    ROWS.append((sid, "N", 0, 0, 0))
for sid in GROUP_APM:
    ROWS.append((sid, "A+P-", 1, 0, 1))
for sid in GROUP_APP:
    ROWS.append((sid, "A+P+", 1, 1, 2))

ROWS.sort(key=lambda r: int(r[0].split("-")[1]))

out_path = Path(__file__).parent / "participants_labels.tsv"
with out_path.open("w", newline="") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow([
        "subject_id", "group", "task1_risk_vs_norisk",
        "task2_high_vs_lownormal", "task3_multiclass",
    ])
    writer.writerows(ROWS)

print(f"Wrote {len(ROWS)} rows to {out_path}")
