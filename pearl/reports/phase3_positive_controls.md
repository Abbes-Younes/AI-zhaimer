# Phase 3 Positive Controls — VERDICT: PROCEED_WITH_CAVEAT

1a high, 1b near chance: the features work (alpha waveform shape is measured correctly and generalises within subject) but do not generalise across subjects for a genuinely detectable cross-subject target (sex). Any primary-analysis null must be reported with this caveat, not as an uncaveated finding about genotype.

## §1a — Eyes-open vs eyes-closed (within-subject, strong control)

- AUC: **0.830** (floor: 0.80)
- 95% bootstrap CI: [0.710, 0.898]
- Permutation p-value: 0.0050
- Subjects used: 61 (dropped: 3)
- Verdict: **PASS**

## §1b — Sex classification (cross-subject, subject-level control)

- AUC: **0.486** (floor: 0.65)
- 95% bootstrap CI: [0.301, 0.745]
- Permutation p-value: 0.6269
- Subjects used: 64
- Verdict: **FAIL**

## §1c — Interpretation table applied

| 1a | 1b | Primary null means |
|---|---|---|
| high | ≥ ~0.65 | pipeline works; a null on genotype is a **real null** — reportable, valuable |
| high | ≈ chance | features work but don't generalise across subjects; report the primary null with that caveat |
| low | any | **pipeline is broken.** Stop. Do not run or report the primary analysis |
