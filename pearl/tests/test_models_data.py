import pandas as pd

from pearl_models.data import assemble


def test_assemble_inner_joins_feature_sets_and_left_joins_labels():
    feats_a = pd.DataFrame({"a1": [1.0, 2.0]}, index=pd.Index(["sub-01", "sub-02"], name="subject"))
    feats_b = pd.DataFrame({"b1": [10.0]}, index=pd.Index(["sub-01"], name="subject"))
    labels = pd.DataFrame({"subject_id": ["sub-01", "sub-02"], "risk_vs_none": [1, 0]})
    nuisance = pd.DataFrame({"age": [50]}, index=pd.Index(["sub-01"], name="subject"))

    out = assemble({"a": feats_a, "b": feats_b}, labels=labels, nuisance=nuisance)

    assert list(out.index) == ["sub-01"]  # inner join across feature sets
    assert "a1" in out.columns and "b1" in out.columns
    assert out.loc["sub-01", "risk_vs_none"] == 1
    assert out.loc["sub-01", "age"] == 50


def test_assemble_leaves_missing_nuisance_as_nan_not_dropped():
    feats_a = pd.DataFrame({"a1": [1.0]}, index=pd.Index(["sub-03"], name="subject"))
    labels = pd.DataFrame({"subject_id": ["sub-03"], "risk_vs_none": [0]})
    nuisance = pd.DataFrame({"age": []}, index=pd.Index([], name="subject"))

    out = assemble({"a": feats_a}, labels=labels, nuisance=nuisance)

    assert "sub-03" in out.index
    assert pd.isna(out.loc["sub-03", "age"])
