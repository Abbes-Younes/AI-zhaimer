# Phase 5 Stage 3 Validation — Step 0: Stability/Sensitivity Characterization

**Verdict: the 0.651 headline number is not a stable estimate. Bootstrap
resampling shows its center is close to the nuisance-only line and its
tails cross well below chance.**

## Method

Two resampling schemes on the already-computed 64-subject PSWT feature/label
matrix (no new preprocessing, no new feature/model choice — reused
`pearl_models.cv.pooled_repeated_cv` unchanged, lighter `n_repeats=1` per
resample to keep this cheap):

- **Leave-k-out** (k=2..8, 25 repeats each, 175 total): randomly drop k
  subjects, recompute pooled CV AUC on the rest.
- **Subject-level bootstrap** (150 resamples, full n=64, sampled with
  replacement): standard resampling-based stability check.

**A real bug was caught and fixed before trusting either number**: the
first bootstrap implementation passed row-position indices as the CV
`groups` array rather than original subject identity, so a subject
duplicated by resampling could land in both the train and test fold of the
same split — leakage, not signal. This inflated the first-pass bootstrap
median to 0.787 (100% "above nuisance-only," 0% "below chance") — an
implausibly strong number given leave-k-out's own median was 0.625 with no
duplication risk. Fixed by passing the original sampled index as the group
identity (`groups=idx`, so `StratifiedGroupKFold` keeps every duplicate of
one subject together); results below are post-fix.

## Results

| Method | n | 5th pct | median | 95th pct | % above nuisance-only (0.557) | % below chance (0.5) |
|---|---|---|---|---|---|---|
| Leave-k-out | 175 | 0.531 | 0.625 | 0.715 | 87.4% | 1.1% |
| Bootstrap | 150 | **0.407** | **0.565** | 0.726 | **54.0%** | **24.0%** |

Bootstrap range: [0.270, 0.859]. Leave-k-out medians by k are stable
(0.61–0.66) across k=2 through k=8 — dropping a handful of subjects doesn't
collapse the effect, but the observed 0.651 sits above every leave-k-out
median, consistent with 0.651 itself being a somewhat favorable draw.

## Interpretation

**Bootstrap resampling is the more representative simulation of "what
would this analysis show on a different same-size draw from the same
population"** — closer to what independent replication would actually test
than leave-k-out (which only ever removes a few subjects from the same
fixed majority). Its result is the more important one here:

- **The bootstrap median (0.565) sits almost exactly on the nuisance-only
  line (0.557)** — the center of the resampling distribution shows no
  meaningful separation from "covariates alone," even though the single
  point estimate Stage 3 reported (0.651) does.
- **Only 54% of bootstrap resamples even exceed the nuisance-only line** —
  barely better than a coin flip on "does EEG add anything," despite Stage
  3's single run reporting a seemingly clear win.
- **24% of bootstrap resamples land below chance entirely**, with a
  worst-case draw of 0.270. A result whose resampling distribution puts a
  quarter of its mass below chance is not a located, reliable effect.

This corroborates, with a different and arguably more informative method,
what the marginal p-value and chance-crossing CI already suggested in
`reports/phase5_stage3_checkpoint.md`: **the 0.651 point estimate is near
the high end of what this sample can produce by chance alone, not a
reliably-located effect.**

## Recommendation on Step 1 (attribution re-run)

Per the validation plan's own checkpoint: Step 1 (isolating which of Stage
1's two preprocessing fixes drives the change, ~3-4h) was scoped to inform
delivery *if* the result looked corroborated. It doesn't. Attribution
matters less when the underlying result itself doesn't reliably clear even
its own nuisance-only comparison under resampling — knowing *which fix*
produced an unstable number doesn't make the number stable. **Recommend
treating Step 0 alone as sufficient grounds against the positive framing**,
and reserving Step 1's compute budget for confirming this reading rather
than searching for attribution of a result that may not need explaining.

This is a recommendation, not a unilateral decision to skip Step 1 — see
the response accompanying this report for the checkpoint question.
