"""Tests des fonctions de modélisation statistique (src/modeling/models.py)."""

import numpy as np
import pandas as pd
import pytest

from src.modeling.models import (
    ModelResult,
    fit_mixed_effects,
    fit_ols,
    intraclass_correlation,
    ols_coefficients_table,
    prepare_model_frame,
    regression_metrics,
    save_model,
    save_model_summary,
)


@pytest.fixture
def modeling_frame():
    rng = np.random.default_rng(42)
    n_ecoles = 20
    n_par_ecole = 15
    rows = []
    for ecole in range(n_ecoles):
        effet_ecole = rng.normal(0, 3)
        for _ in range(n_par_ecole):
            statut = rng.choice(["Hors EP", "REP", "REP+"])
            bonus = {"Hors EP": 5, "REP": 0, "REP+": -3}[statut]
            score = 60 + bonus + effet_ecole + rng.normal(0, 4)
            rows.append({"ecole_id": ecole, "statut": statut, "score": score})
    return pd.DataFrame(rows)


def test_prepare_model_frame_selects_and_encodes_columns(modeling_frame):
    frame = prepare_model_frame(
        modeling_frame, target="score", explanatory=["statut"], categorical=["statut"]
    )
    assert set(frame.columns) == {"score", "statut"}
    assert str(frame["statut"].dtype) == "category"


def test_prepare_model_frame_raises_if_missing_values_present(modeling_frame):
    df = modeling_frame.copy()
    df.loc[0, "score"] = np.nan
    with pytest.raises(ValueError):
        prepare_model_frame(df, target="score", explanatory=["statut"])


def test_fit_ols_returns_result_and_formula(modeling_frame):
    result, formule = fit_ols(modeling_frame, target="score", explanatory=["statut"], categorical=["statut"])
    assert "score ~" in formule
    assert hasattr(result, "params")
    assert result.nobs == len(modeling_frame)


def test_fit_ols_with_cluster_robust_errors(modeling_frame):
    result, _ = fit_ols(
        modeling_frame,
        target="score",
        explanatory=["statut"],
        categorical=["statut"],
        cluster_column="ecole_id",
    )
    assert hasattr(result, "params")


def test_fit_mixed_effects_returns_result_with_group_variance(modeling_frame):
    result, formule = fit_mixed_effects(
        modeling_frame, target="score", explanatory=["statut"], group_column="ecole_id", categorical=["statut"]
    )
    assert "score ~" in formule
    assert hasattr(result, "cov_re")


def test_intraclass_correlation_between_zero_and_one(modeling_frame):
    result, _ = fit_mixed_effects(
        modeling_frame, target="score", explanatory=["statut"], group_column="ecole_id", categorical=["statut"]
    )
    icc = intraclass_correlation(result)
    assert 0.0 <= icc <= 1.0


def test_ols_coefficients_table_has_expected_columns(modeling_frame):
    result, _ = fit_ols(modeling_frame, target="score", explanatory=["statut"], categorical=["statut"])
    table = ols_coefficients_table(result)
    for column in ("coefficient", "erreur_standard", "statistique_t", "p_value", "ic_95_basse", "ic_95_haute"):
        assert column in table.columns


def test_regression_metrics_perfect_fit_gives_r2_one():
    y_true = pd.Series([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.0, 2.0, 3.0, 4.0])
    metrics = regression_metrics(y_true, y_pred)
    assert metrics["r2"] == pytest.approx(1.0)
    assert metrics["rmse"] == pytest.approx(0.0)
    assert metrics["mae"] == pytest.approx(0.0)
    assert metrics["n"] == 4


def test_regression_metrics_with_residuals():
    y_true = pd.Series([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.5, 2.5, 2.5, 3.5])
    metrics = regression_metrics(y_true, y_pred)
    assert metrics["rmse"] == pytest.approx(0.5, abs=1e-9)
    assert metrics["mae"] == pytest.approx(0.5, abs=1e-9)


def test_save_model_writes_pickle(tmp_path, monkeypatch, modeling_frame):
    import src.modeling.models as models_module

    monkeypatch.setattr(models_module, "MODELS_DIR", tmp_path)
    result, _ = fit_ols(modeling_frame, target="score", explanatory=["statut"], categorical=["statut"])
    path = save_model(result, "modele_test")
    assert path.exists()
    assert path.suffix == ".pickle"


def test_save_model_summary_writes_json_and_txt(tmp_path, monkeypatch, modeling_frame):
    import src.modeling.models as models_module

    monkeypatch.setattr(models_module, "MODELS_DIR", tmp_path)
    result, formule = fit_ols(modeling_frame, target="score", explanatory=["statut"], categorical=["statut"])
    coefficients = ols_coefficients_table(result)
    model_result = ModelResult(
        nom_modele="modele_test",
        formule=formule,
        n_observations=int(result.nobs),
        coefficients=coefficients,
        metriques={"r2": float(result.rsquared)},
    )
    paths = save_model_summary(model_result, "modele_test")
    assert paths["json"].exists()
    assert paths["txt"].exists()
    assert "modele_test" in paths["txt"].read_text(encoding="utf-8")


def test_model_result_to_dict_contains_expected_keys(modeling_frame):
    result, formule = fit_ols(modeling_frame, target="score", explanatory=["statut"], categorical=["statut"])
    coefficients = ols_coefficients_table(result)
    model_result = ModelResult(
        nom_modele="modele_test",
        formule=formule,
        n_observations=int(result.nobs),
        coefficients=coefficients,
        metriques={"r2": float(result.rsquared)},
    )
    data = model_result.to_dict()
    for key in ("nom_modele", "formule", "n_observations", "coefficients", "metriques", "horodatage"):
        assert key in data
