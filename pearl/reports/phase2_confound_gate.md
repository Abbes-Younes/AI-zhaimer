# Phase 2 Confound Gate — VERDICT: PROCEED

PROCEED — preprocessing carries no detectable group information.

## §1b — QC-only classifier (the decisive test)

- Mean AUC (subject-level stratified group k-fold, nested, permutation-tested): **0.509**
- 95% bootstrap CI: [0.416, 0.769]
- Permutation p-value: 0.4845

## §1a — Association tests, full cohort (N=79)

| metric                  | test           |   statistic |     p_value |      p_fdr |   effect_size |    ci_low |   ci_high |
|:------------------------|:---------------|------------:|------------:|-----------:|--------------:|----------:|----------:|
| n_bad_channels          | kruskal-wallis |    5.47618  | 0.0646938   | 0.10351    |     0.0149835 | 0         | 0.0729934 |
| occipital_bads          | kruskal-wallis |    5.99877  | 0.0498178   | 0.0996355  |     0.0172361 | 0         | 0.0805585 |
| n_ica_removed           | kruskal-wallis |    0.510843 | 0.77459     | 0.885245   |     0         | 0         | 0.0267379 |
| line_noise_index_before | kruskal-wallis |    8.43605  | 0.0147277   | 0.0589109  |     0.0277416 | 0         | 0.0921209 |
| line_noise_index_after  | kruskal-wallis |    0.760934 | 0.683542    | 0.885245   |     0         | 0         | 0.0330064 |
| artifact_frac           | kruskal-wallis |   19.1058   | 7.09938e-05 | 0.00056795 |     0.0737321 | 0.0217727 | 0.152285  |
| iaf_hz                  | kruskal-wallis |    0.236261 | 0.88858     | 0.88858    |     0         | 0         | 0.0256101 |
| alpha_peak_height_db    | kruskal-wallis |    6.12967  | 0.0466616   | 0.0996355  |     0.0178003 | 0         | 0.0822248 |

## §1a — Association tests, surviving cohort (per-task rule)

| metric                  | test           |   statistic |     p_value |      p_fdr |   effect_size |     ci_low |   ci_high |
|:------------------------|:---------------|------------:|------------:|-----------:|--------------:|-----------:|----------:|
| n_bad_channels          | kruskal-wallis |    6.05498  | 0.0484372   | 0.0968743  |    0.0198773  | 0          | 0.0917012 |
| occipital_bads          | kruskal-wallis |    6.20872  | 0.0448533   | 0.0968743  |    0.020631   | 0          | 0.0860075 |
| n_ica_removed           | kruskal-wallis |    0.762702 | 0.682938    | 0.910584   |    0          | 0          | 0.0355096 |
| line_noise_index_before | kruskal-wallis |   14.342    | 0.000768561 | 0.00614848 |    0.0604999  | 0.0124778  | 0.142319  |
| line_noise_index_after  | kruskal-wallis |    0.161209 | 0.922558    | 0.922558   |    0          | 0          | 0.0262373 |
| artifact_frac           | kruskal-wallis |   12.7227   | 0.00172702  | 0.00690809 |    0.0525623  | 0.00804911 | 0.137789  |
| iaf_hz                  | kruskal-wallis |    0.26055  | 0.877854    | 0.922558   |    0          | 0          | 0.0294003 |
| alpha_peak_height_db    | kruskal-wallis |    3.90218  | 0.142119    | 0.22739    |    0.00932443 | 0          | 0.0765415 |

## §1a — Exclusion status × group (Fisher's exact)

- Odds ratio: 0.830
- p-value: 0.6871

## §1c — Carry-forward covariates

Bad-channel count and ICA-components-removed join SES and BDI as declared Phase 3 covariates, regardless of this verdict (see Amendment 1, `reports/analysis_plan_frozen.md`).
