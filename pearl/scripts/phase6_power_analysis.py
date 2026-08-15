"""Phase 6 Stage A2 — power / MDE / CI-width analysis for the sex control at n=64.

Two questions the plan needs answered:
  1. What AUC can this cohort reliably detect at 80% power? (sensitivity
     analysis at the achieved n -- the defensible alternative to post-hoc power)
  2. How wide is a 95% CI on an AUC at this n? -- i.e. is phase_6.md's
     "bootstrap lower bound > 0.50" gate achievable at all?
"""
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(r"d:\younes\AI-zhaimer\.claude\skills\statistical-power\scripts")))
from power import mde, power as power_fn  # noqa: E402

N1, N2 = 34, 30          # sex balance in the frozen 64-subject cohort
ALPHA = 0.05
RATIO = N2 / N1


def auc_to_d(auc: float) -> float:
    """Binormal, equal-variance: d = sqrt(2) * Phi^-1(AUC)."""
    return np.sqrt(2.0) * norm.ppf(auc)


def d_to_auc(d: float) -> float:
    return float(norm.cdf(d / np.sqrt(2.0)))


def hanley_mcneil_se(auc: float, n1: int, n2: int) -> float:
    """Hanley & McNeil (1982) SE of a *single* AUC estimate.

    NOTE: this is a LOWER BOUND on the SE of a cross-validated AUC, which
    carries additional variance from the resampling/model-fitting itself.
    The real bootstrap CI in this project is therefore WIDER than what this
    predicts -- which only strengthens the conclusion below.
    """
    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc**2 / (1.0 + auc)
    var = (auc * (1 - auc) + (n1 - 1) * (q1 - auc**2) + (n2 - 1) * (q2 - auc**2)) / (n1 * n2)
    return float(np.sqrt(var))


print("=" * 72)
print(f"Phase 6 Stage A2 -- power analysis, n={N1} vs {N2} (total {N1+N2}), alpha={ALPHA}")
print("=" * 72)

print("\n[1] MINIMUM DETECTABLE EFFECT at 80% / 90% power (sensitivity analysis)")
for pw in (0.80, 0.90):
    d = mde(test="t_ind", nobs1=N1, power=pw, alpha=ALPHA, ratio=RATIO)
    print(f"    power={pw:.2f}:  Cohen's d = {d:.3f}  ->  AUC = {d_to_auc(d):.3f}")

print("\n[2] POWER ACROSS PLAUSIBLE AUCs (the deliverable -- a curve, not one number)")
print(f"    {'AUC':>6} {'d':>7} {'power':>8}")
for auc in (0.58, 0.60, 0.65, 0.685, 0.693, 0.70, 0.75, 0.80):
    d = auc_to_d(auc)
    pw = power_fn(test="t_ind", effect_size=d, nobs1=N1, alpha=ALPHA, ratio=RATIO)
    print(f"    {auc:>6.3f} {d:>7.3f} {pw:>8.3f}")

print("\n[3] EXPECTED 95% CI WIDTH ON AN AUC (Hanley-McNeil; LOWER bound for CV-AUC)")
print(f"    {'AUC':>6} {'SE':>7} {'95% CI':>18} {'width':>7} {'lower>0.50?':>12}")
for auc in (0.58, 0.65, 0.693, 0.75, 0.80, 0.85):
    se = hanley_mcneil_se(auc, N1, N2)
    lo, hi = auc - 1.96 * se, auc + 1.96 * se
    print(f"    {auc:>6.3f} {se:>7.4f}  [{lo:>6.3f}, {hi:>6.3f}] {hi-lo:>7.3f} "
          f"{'YES' if lo > 0.50 else 'no':>12}")

print("\n[4] WHAT AUC IS NEEDED FOR THE phase_6.md GATE (CI lower bound > 0.50)?")
for auc in np.arange(0.60, 0.95, 0.005):
    se = hanley_mcneil_se(float(auc), N1, N2)
    if auc - 1.96 * se > 0.50:
        print(f"    Smallest AUC whose 95% CI clears 0.50: {auc:.3f}")
        d = auc_to_d(float(auc))
        pw = power_fn(test="t_ind", effect_size=d, nobs1=N1, alpha=ALPHA, ratio=RATIO)
        print(f"    -> Cohen's d = {d:.3f}, power to detect it here = {pw:.3f}")
        break

print("\n[5] OBSERVED-DATA REFERENCE POINTS (reported, not used as post-hoc power)")
for label, auc in (("Phase 4 rung1 (sex, old preproc)", 0.693),
                    ("Phase 4 rung3 (sex, old preproc)", 0.685),
                    ("PSWT sex control", 0.465),
                    ("published genotype benchmark", 0.58)):
    se = hanley_mcneil_se(max(auc, 1 - auc), N1, N2)
    print(f"    {label:<36} AUC={auc:.3f}  approx 95% CI half-width +/-{1.96*se:.3f}")
print()
