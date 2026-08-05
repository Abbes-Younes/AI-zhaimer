# Phase 1 Download Plan (ds004796)

Usable budget: **95 GB** (115 GB total − 20 GB reserve).

Manifest: `D:\younes\AI-zhaimer\pearl\data\derivatives\phase0\.tmp-20260805T175341Z-d891d70\phase1_manifest.csv` (final location: `data/derivatives/phase0/phase1_manifest.csv`).

| Scope | Raw GB | Est. derivatives GB | Total GB | Fits in 95 GB? |
|---|---|---|---|---|
| A_full_eeg | 75.87 | 66.98 | 142.85 | NO |
| B_rest_msit | 46.47 | 40.93 | 87.4 | YES |
| C_rest_msit_only | 46.47 | 40.93 | 87.4 | YES |

**Recommendation: C_rest_msit_only**

## Derivative footprint assumptions
- Target processing rate: **250 Hz**, float32 (4 bytes/sample).
- Epoched output = preprocessed × 1.5 (2-s epochs, 50% overlap).
- ICA = one full-length solution per subject ≈ preprocessed size.
- Channel count: README-documented 128 (sidecars carry no EEGChannelCount).
- Duration backed out of measured .eeg sizes at int32 (4 B/sample).
- Sidecar parameters used: {"msit": {"sampling_frequency": 1000}, "rest": {"sampling_frequency": 1000}, "sternberg": {"sampling_frequency": 1000}}

## Note on Scope B vs C
The listing contains a single `task-rest` file per subject (rest covers both
eyes-open and eyes-closed conditions within one recording, per the dataset README).
There is no `acq-`/`run-` split in the file names, so **Scope C is file-level
identical to Scope B** — the eyes-closed subset is an epoch-level carve-out made
during Phase 1 processing, not a separate download.

## Why Scope A is rejected
Full EEG raw is 75.87 GB, leaving ~19 GB for derivatives. The derivative model
estimates ~67 GB under the full-EEG scope, so Scope A does not fit the 95 GB
budget. This is the phase's expected outcome (Scope B/C prior), not an escalation:
Scope C fits with headroom and is recommended.

## Note on education trend test
The education monotone-trend test (Spearman) is reported for the 3-group
multiclass framing only — a trend across a 2-group collapse is degenerate.
The categorical (chi-square/Fisher) test runs for all three framings.

## Manifest
`data/derivatives/phase0/phase1_manifest.csv` lists every S3 key for the
recommended scope with per-file bytes and a running total. **Nothing has been
downloaded.** The manifest requires human approval before Phase 1 executes it.

