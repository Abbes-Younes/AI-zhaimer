# Benchmark citation verification (phase_2.md §0d)

**Status:** VERIFIED

**Claimed benchmark:** AUC ≈ 0.58, cross-subject early-AD susceptibility
prediction, task EEG, SVM, multitaper spectral features.

**Full reference:** Li, Z.; Wang, H.; Song, J.; Gong, J. (2025). Exploring
Task-Related EEG for Cross-Subject Early Alzheimer's Disease Susceptibility
Prediction in Middle-Aged Adults Using Multitaper Spectral Analysis. *Sensors*,
25(1), 52. DOI: [10.3390/s25010052](https://doi.org/10.3390/s25010052)
(received 2024-12-09, accepted 2024-12-24, published online January 2025).
Open-access full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC11723164/

**Task and classifier that produced the 0.58:** Multi-Source Interference Task
(MSIT), **low-demand condition (ML)** — not resting-state, and not the
high-demand MSIT condition. Feature set: Time–Frequency Area Average Test
(TFAAT), derived from multitaper spectral analysis. Classifier: Support Vector
Machine (SVM). Quoting the paper: "The ROC AUC value of the SVM method under
the ML condition reached the maximum value of 0.58, with all four
classification methods exhibiting significant differences." The paper also
reports that task-state EEG (MSIT, Sternberg) outperformed resting-state EEG
for this cross-subject classification problem.

**Verification method:** WebSearch + WebFetch on 2026-08-09, matched against
the MDPI publisher record (`mdpi.com/1424-8220/25/1/52`, blocked by a 403 on
direct fetch) and cross-confirmed against the PubMed Central full text
(PMC11723164) and PubMed record (PMID 39796844).

**Framing match to this project:** **Partial mismatch, worth stating
explicitly rather than eliding.** The 0.58 benchmark comes from **task-state
EEG under the MSIT low-demand condition**, using multitaper spectral features
and SVM — the same MSIT paradigm this project also collects, but a different
feature family (multitaper/TFAAT spectral, not PSR/PSWT waveform-shape) and a
different task condition than this project's primary target, which is
**rest-based** (`binary_risk_vs_none`, per Amendment 1). The paper's own
finding that task EEG outperformed resting-state EEG for this classification
problem is itself a relevant caveat: this project's rest-based primary target
is being compared against a benchmark derived from the *better-performing*
modality in the source paper, which if anything makes 0.58 an optimistic
(not conservative) reference point for a rest-based analysis. This should be
carried into Phase 3's benchmark discussion, not silently treated as an
apples-to-apples number.
