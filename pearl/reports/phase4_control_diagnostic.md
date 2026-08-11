# Phase 4 Control Diagnostic — VERDICT: ANY RUNG SIGNIFICANT

This diagnostic runs against a **positive control target (sex)**, never against the primary target (`binary_risk_vs_none`). It cannot change the primary verdict (frozen: NULL, AUC 0.474). Its only output is which of the two sentences below the final report is entitled to write.

**Resolved sentence:** The pitch-synchronous feature family did not detect genotype group, on a cohort where other EEG features do carry subject-level information. This is a negative result for the method as applied here.

## Ladder (run in declared order; all three rungs computed regardless of outcome)

| Rung | Features | AUC | 95% CI | Permutation p | Significant (p<0.05)? |
|---|---|---|---|---|---|
| 1 — baseline spectral (16 features) | | 0.693 | [0.402, 0.829] | 0.0130 | **YES** |  *(first rung to pass — drives the interpretation below)*
| 2 — PSWT + baseline combined | | 0.556 | [0.336, 0.764] | 0.2647 | no |
| 3 — per-channel/zone, fresh computation | | 0.685 | [0.418, 0.840] | 0.0240 | **YES** |

## §0d decision table

| Outcome | Final report says |
|---|---|
| Any rung clearly above chance | The pitch-synchronous feature family did not detect genotype group, on a cohort where other EEG features do carry subject-level information. This is a negative result for the method as applied here. |
| All three at chance | No subject-level EEG signal of any kind was detectable in this cohort at n=64, including a target known to be detectable in larger samples. The genotype result is therefore inconclusive, not negative. |

**Outcome marked:** Any rung clearly above chance (stopped at rung1_baseline).

## Additional observation

Rung 2 (PSWT + baseline combined) was **not** significant (p=0.2647) even though both rungs that compose it individually were. Adding PSWT features diluted rather than added to the detectable signal — further evidence that the PSWT feature family specifically carries no useful subject-level information here, rather than the combined analysis simply lacking power.

## Methodology note (rung 3)

Rung 3 uses 5 coarse anatomical zones (frontal, central, parietal, occipital, temporal) rather than all 127 individual channels, to keep the feature count tractable at n=64. 71 of 127 channels (standard extended-10-5 sites with recognized zone prefixes) were mapped; the remaining 56 (far-lateral/interstitial extended sites) were not assigned a zone and are excluded from this diagnostic. This is exploratory, not a declared feature family — it exists only to test whether ROI-averaging destroyed between-subject variance.
