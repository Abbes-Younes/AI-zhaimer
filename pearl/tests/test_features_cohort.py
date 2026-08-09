import pandas as pd

from pearl_features.cohort import per_task_cohort, rest_cohort_n


def _qc(rows):
    return pd.DataFrame(rows, columns=["subject", "task", "verdict"])


def test_per_task_cohort_excludes_only_failing_rows():
    qc = _qc([
        ("sub-01", "rest", "pass"),
        ("sub-01", "msit", "fail"),
        ("sub-02", "rest", "fail"),
        ("sub-02", "msit", "pass"),
    ])
    out = per_task_cohort(qc)
    included = {(r.subject, r.task): r.included for r in out.itertuples()}
    assert included[("sub-01", "rest")] is True
    assert included[("sub-01", "msit")] is False
    assert included[("sub-02", "rest")] is False
    assert included[("sub-02", "msit")] is True


def test_per_task_cohort_warn_is_included():
    qc = _qc([("sub-03", "rest", "warn")])
    out = per_task_cohort(qc)
    assert bool(out.iloc[0].included) is True


def test_rest_cohort_n_counts_included_rest_rows_only():
    qc = _qc([
        ("sub-01", "rest", "pass"),
        ("sub-02", "rest", "fail"),
        ("sub-03", "rest", "pass"),
        ("sub-03", "msit", "fail"),
    ])
    out = per_task_cohort(qc)
    assert rest_cohort_n(out) == 2
