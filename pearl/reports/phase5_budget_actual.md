# Phase 5 Stage 1 Budget — Measured, rest+msit+sternberg (ds004796)

Sternberg ingestion (phase_5.md §0c) adds a third task to the manifest used by Phase 1. Gate: continuous-derivative total **≤ 30.0 GB** (same gate as phase_1.md §0c). Measured total: **25.08 GB** → PASS.

## Measured per-task figures

| Task | Subjects | Mean duration (s) | Min–max (s) | Raw GB (measured) | Continuous @ target (GB) |
|---|---|---|---|---|---|
| msit | 79 | 588.6 | 525.2–886.6 | 22.0 | 5.5 |
| rest | 78 | 663.0 | 617.7–835.2 | 24.47 | 12.23 |
| sternberg | 78 | 796.5 | 770.7–940.4 | 29.39 | 7.35 |

Raw total (manifest, all 3 tasks): **75.87 GB**.
Derivative total: **25.08 GB** (one float32 continuous file per subject per task at the target rate; ICA solutions are kilobytes, not counted as data).

## Why Scope A is now selected (reverses Phase 0.5's rejection)

Phase 0.5 rejected Scope A because its co-resident-storage model put raw (75.87 GB) + derivatives (~67 GB, since corrected — that model double-counted epoched/ICA copies) over the 95 GB budget. Phase 1's streaming download→process→verify→delete design (proven in production, phase_1.md §0d) means raw and derivatives never co-reside: peak raw on disk is bounded by a one-subject lookahead, **not** the full-scope raw total. That note was written but not acted on during Phase 1 (rest+msit only, to prove the pipeline first); Stage 1 of Phase 5 acts on it now.

## Streaming consequence (unchanged from Phase 1)

Raw and derivatives never coexist: each subject is downloaded, preprocessed, verified, and its raw deleted. Peak raw on disk with a one-subject lookahead: **2.22 GB** — not the 75.87 GB full-download figure. Raw is therefore never the binding constraint, for any of the 3 tasks.

## Method

duration_s = .eeg bytes / (127 ch × 4 B float32 × 1000 Hz native) — per subject per task from the measured size survey (data/derivatives/phase0/size_survey.csv, which already contains sternberg rows from Phase 0's original full-dataset listing). Continuous bytes = 127 × duration × target rate × 4 B, target rates from config/preproc.yaml (rest 500 Hz, msit/sternberg 250 Hz).

