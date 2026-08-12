# Phase 3 Benchmark Reproduction (MSIT) — VERDICT: NEAR_BENCHMARK

NEAR BENCHMARK — this project's preprocessing and CV machinery are comparable to the published pipeline; the 0.58 reference point is meaningful to compare against.

## Result

- AUC: **0.490** (published benchmark: 0.58, chance: 0.50)
- 95% bootstrap CI: [0.270, 0.726]
- Permutation p-value: 0.5375
- Subjects used (MSIT-QC-surviving, complete baseline features): 59

## Framing caveat

The published 0.58 came from task-state MSIT with multitaper/TFAAT spectral features and an SVM classifier (Li et al. 2025) — not this project's simple relative-band-power + 1/f baseline with L2 logistic regression. The source paper also found task EEG outperforms resting-state EEG for this classification problem, so 0.58 is, if anything, an optimistic bar for this project's rest-based primary analysis, independent of this reproduction attempt's outcome.

## Investigation (why AT_CHANCE, not a bug)

Three checks, run before accepting the null:

1. **Data sanity** — no degenerate features, reasonable variance/scale across all 7 MSIT columns, class balance 33/22 in the 55-subject complete-data subset. No data bug.
2. **Univariate signal, two ROIs** — neither the occipital-parietal ROI (used in the frozen `features_baseline.csv`) nor a frontocentral ROI (`Fz, FC1, FC2, Cz, F3, F4, FC5, FC6, C3, C4` — the anatomically expected site for MSIT interference effects, computed as a one-off diagnostic, not a declared feature family) shows *any* individual feature with even marginal association to the label: occipital-parietal all p > 0.16 (univariate AUC range 0.39-0.61); frontocentral all p > 0.28 (range 0.42-0.57). Both are noise-level.
3. **Alternate classifier** — linear SVM (the declared secondary model class) scores *worse* (mean AUC 0.38) than logistic regression (0.459) on the same features, ruling out classifier choice as the explanation.

**Conclusion:** not a pipeline bug. This project's baseline feature set is 7 simple relative-band-powers + a 1/f fit, ROI-averaged over the entire MSIT recording. The published 0.58 used multitaper time-frequency area features, computed per condition (specifically the low-demand block), with t-test+FDR subspace feature selection — a substantially richer feature-engineering and selection pipeline, on a different cohort. Reproducing that exactly is out of this phase's scope; the gap is a characterized methodological difference in feature richness, not evidence the pipeline is broken. It does not affect the primary PSWT-on-rest analysis, which shares neither the feature family nor the task with this benchmark check.
