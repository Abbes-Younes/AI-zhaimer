# Phase 3 Benchmark Reproduction (MSIT) — VERDICT: AT_CHANCE

AT CHANCE — STOP AND ESCALATE (phase_3.md §10). This pipeline's MSIT baseline-feature reproduction does not approach the published 0.58. The pipeline differs from the published one (different feature family — band power/1-f vs. multitaper/TFAAT — and/or different preprocessing/sample) in a way that must be understood before the 0.58 figure is quoted as a meaningful comparison target. This does NOT by itself invalidate the primary PSWT-on-rest analysis, which uses neither this feature family nor this task — but the benchmark comparison in every downstream report must be presented with this caveat, not as a validated external check.

## Result

- AUC: **0.459** (published benchmark: 0.58, chance: 0.50)
- 95% bootstrap CI: [0.252, 0.721]
- Permutation p-value: 0.5473
- Subjects used (MSIT-QC-surviving, complete baseline features): 55

## Framing caveat

The published 0.58 came from task-state MSIT with multitaper/TFAAT spectral features and an SVM classifier (Li et al. 2025) — not this project's simple relative-band-power + 1/f baseline with L2 logistic regression. The source paper also found task EEG outperforms resting-state EEG for this classification problem, so 0.58 is, if anything, an optimistic bar for this project's rest-based primary analysis, independent of this reproduction attempt's outcome.
