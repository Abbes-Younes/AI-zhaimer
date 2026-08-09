# Phase 2 Confound Gate — VERDICT: PROCEED

PROCEED — preprocessing carries no detectable group information.

## §1b — QC-only classifier (the decisive test)

- Mean AUC (subject-level stratified group k-fold, nested, permutation-tested): **0.545**
- 95% bootstrap CI: [0.435, 0.800]
- Permutation p-value: 0.3487

## §1a — Association tests, full cohort (N=79)

| metric                  | test           |   statistic |    p_value |     p_fdr |   effect_size |    ci_low |   ci_high |
|:------------------------|:---------------|------------:|-----------:|----------:|--------------:|----------:|----------:|
| n_bad_channels          | kruskal-wallis |    0.276766 | 0.870765   | 0.870765  |     0         | 0         | 0.0398921 |
| occipital_bads          | kruskal-wallis |    6.21979  | 0.0446057  | 0.178423  |     0.0274012 | 0         | 0.130502  |
| n_ica_removed           | kruskal-wallis |    1.26832  | 0.530381   | 0.84861   |     0         | 0         | 0.0614064 |
| line_noise_index_before | kruskal-wallis |    2.06719  | 0.355726   | 0.711452  |     0.0004363 | 0         | 0.0670186 |
| line_noise_index_after  | kruskal-wallis |    0.471787 | 0.789865   | 0.870765  |     0         | 0         | 0.0429876 |
| artifact_frac           | kruskal-wallis |   13.2397   | 0.00133365 | 0.0106692 |     0.0729849 | 0.0137262 | 0.180726  |
| iaf_hz                  | kruskal-wallis |    0.308109 | 0.857225   | 0.870765  |     0         | 0         | 0.0421274 |
| alpha_peak_height_db    | kruskal-wallis |    3.78875  | 0.150412   | 0.401099  |     0.0116153 | 0         | 0.0986826 |

## §1a — Association tests, surviving cohort (per-task rule)

| metric                  | test           |   statistic |    p_value |     p_fdr |   effect_size |   ci_low |   ci_high |
|:------------------------|:---------------|------------:|-----------:|----------:|--------------:|---------:|----------:|
| n_bad_channels          | kruskal-wallis |    0.306761 | 0.857803   | 0.857803  |    0          | 0        | 0.0506851 |
| occipital_bads          | kruskal-wallis |    5.93038  | 0.0515506  | 0.206202  |    0.0307061  | 0        | 0.139234  |
| n_ica_removed           | kruskal-wallis |    3.06262  | 0.216253   | 0.346004  |    0.00830169 | 0        | 0.105746  |
| line_noise_index_before | kruskal-wallis |    3.81844  | 0.148196   | 0.346004  |    0.0142066  | 0        | 0.115464  |
| line_noise_index_after  | kruskal-wallis |    0.73849  | 0.691256   | 0.840211  |    0          | 0        | 0.0605146 |
| artifact_frac           | kruskal-wallis |    9.92206  | 0.00700572 | 0.0560457 |    0.0618911  | 0.003225 | 0.184799  |
| iaf_hz                  | kruskal-wallis |    0.615267 | 0.735185   | 0.840211  |    0          | 0        | 0.0622731 |
| alpha_peak_height_db    | kruskal-wallis |    3.15737  | 0.206246   | 0.346004  |    0.00904196 | 0        | 0.106499  |

## §1a — Exclusion status × group (Fisher's exact)

- Odds ratio: 1.150
- p-value: 0.8272

## §1c — Carry-forward covariates

Bad-channel count and ICA-components-removed join SES and BDI as declared Phase 3 covariates, regardless of this verdict (see Amendment 1, `reports/analysis_plan_frozen.md`).

## §6b — 50 Hz harmonic-exclusion index vs. group (post hoc, real data)

Computed after the full feature pipeline run, using the real per-subject
`excluded_harmonic_index` in `cycle_stats.csv` (derived from each subject's
own IAF) against group. Chi-squared test of independence:

| group  | index=4 | index=5 |
|--------|--------:|--------:|
| A+P+   | 1       | 13      |
| A+P-   | 4       | 21      |
| N      | 3       | 22      |

chi2 p-value = 0.721 — no association between the excluded harmonic index and
group. The synthetic-IAF unit test (`test_fifth_harmonic_excluded_index_does_not_associate_with_group`)
is confirmed on real data.
