# Phase 1 Budget — Measured (ds004796)

Gate: continuous-derivative total **≤ 30.0 GB** (phase_1.md §0c). Measured total: **17.73 GB** → PASS.

## Measured per-task figures

| Task | Subjects | Mean duration (s) | Min–max (s) | Raw GB (measured) | Continuous @ target (GB) |
|---|---|---|---|---|---|
| msit | 79 | 588.6 | 525.2–886.6 | 22.0 | 5.5 |
| rest | 78 | 663.0 | 617.7–835.2 | 24.47 | 12.23 |

Raw total (manifest): **46.47 GB**.
Derivative total: **17.73 GB** (one float32 continuous file per subject per task at the target rate; ICA solutions are kilobytes — not counted as data, phase_1.md §0b).

## §0a Streaming consequence

Raw and derivatives never coexist: each subject is downloaded, preprocessed, verified, and its raw deleted. Peak raw on disk with a one-subject lookahead: **1.41 GB** — not the 46.47 GB full-download figure. Raw is therefore never the binding constraint.

## §0d Scope A is now reachable

Phase 0.5 rejected Scope A (full EEG, incl. Sternberg) because raw (75.87 GB) plus derivatives (~67 GB under the old double-counting model) did not fit 95 GB. Under streaming, peak raw is ~1.2 GB regardless of scope, so the full dataset is affordable. Sternberg is deliberately NOT added this phase (prove the pipeline on rest + MSIT first); this note records that Scope A can be revisited cheaply in Phase 2.

## vs Phase 0.5 estimate

Phase 0.5 estimated 46.47 GB raw + 40.93 GB derivatives = 87.4 GB co-resident. The Phase 0.5 derivative model double-counted (epoched copies ×1.5 and full-size ICA copies). The measured model stores only the continuous derivative (17.73 GB), so the total footprint is ~19.14 GB.

## Method

duration_s = .eeg bytes / (127 ch × 4 B float32 × 1000 Hz native) — per subject per task from the measured size survey. Continuous bytes = 127 × duration × target rate × 4 B, target rates from config/preproc.yaml (rest 500 Hz, msit 250 Hz).

