"""Régénère automatiquement toutes les tables du projet.

Ce script réutilise exclusivement les fonctions définies dans ``src/`` (aucune
logique n'est recopiée depuis les notebooks). Il charge le jeu de données
"analysis ready", recalcule les tables descriptives, de modélisation, de
segmentation, longitudinales, causales et décisionnelles, puis vérifie que
chaque fichier de sortie existe réellement et n'est pas vide.

Utilisation :
    python scripts/generate_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.analysis.advanced import (
    build_decision_indicators,
    build_school_level_panel,
    cluster_school_profiles,
    did_feasibility_report,
    evaluate_specialized_methods,
    gap_over_time,
    yearly_trend_by_group,
)
from src.analysis.descriptive import (
    confidence_interval_mean,
    crosstab_summary,
    distribution_table,
    group_comparison_table,
    group_difference_test,
    save_table,
    summary_statistics,
)
from src.data.cleaning import load_processed_dataset
from src.modeling.models import (
    fit_mixed_effects,
    fit_ols,
    intraclass_correlation,
    mixed_effects_coefficients_table,
    ols_coefficients_table,
    prepare_model_frame,
    regression_metrics,
)
from src.utils.paths import TABLES_DIR, ensure_project_directories

DATASET_NAME = "education_prioritaire"
TARGET = "variable_cible"
EXPLANATORY = ["statut", "niveau", "ips", "dedoublement"]
CATEGORICAL = ["statut", "niveau"]


def _check_output(path: Path, label: str) -> Path:
    """Vérifie qu'un fichier de sortie existe et n'est pas vide."""
    if not path.exists():
        raise RuntimeError(f"Échec de génération de la table '{label}' : fichier absent ({path})")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Échec de génération de la table '{label}' : fichier vide ({path})")
    return path


def generate_descriptive_tables(df: pd.DataFrame) -> None:
    """Notebook 05 — tables descriptives."""
    stats_globales = summary_statistics(df, TARGET).to_frame(name="valeur")
    _check_output(save_table(stats_globales, "05_stats_globales_variable_cible"), "05_stats_globales_variable_cible")

    ic = confidence_interval_mean(df, TARGET)
    ic_table = pd.DataFrame([ic.__dict__])
    name = "05_intervalle_confiance_variable_cible"
    _check_output(save_table(ic_table, name), name)

    distribution = distribution_table(df, TARGET, bins=10)
    _check_output(save_table(distribution, "05_distribution_variable_cible"), "05_distribution_variable_cible")

    comparaison_statut = group_comparison_table(df, TARGET, "statut")
    _check_output(save_table(comparaison_statut, "05_comparaison_statut"), "05_comparaison_statut")

    test_repplus = group_difference_test(df, TARGET, "statut", "REP+", "Hors EP")
    test_rep = group_difference_test(df, TARGET, "statut", "REP", "Hors EP")
    tests_df = pd.DataFrame([test_repplus, test_rep])
    _check_output(save_table(tests_df, "05_tests_difference_statut"), "05_tests_difference_statut")

    comparaison_dedoublement = group_comparison_table(df, TARGET, "dedoublement")
    _check_output(save_table(comparaison_dedoublement, "05_comparaison_dedoublement"), "05_comparaison_dedoublement")

    crosstab = crosstab_summary(df, TARGET, "statut", "niveau", aggregation="mean")
    _check_output(save_table(crosstab, "05_crosstab_statut_niveau_moyenne"), "05_crosstab_statut_niveau_moyenne")

    effectifs = df.groupby(["niveau", "statut"], observed=True).size().unstack("statut")
    _check_output(save_table(effectifs, "05_effectifs_niveau_statut"), "05_effectifs_niveau_statut")

    print("Tables descriptives (05) régénérées.")


def generate_modeling_tables(df: pd.DataFrame):
    """Notebook 06 — tables de modélisation. Retourne (metriques_ols, icc) pour réutilisation."""
    frame = prepare_model_frame(df, TARGET, EXPLANATORY, categorical=CATEGORICAL, group_column="ecole_id")

    result_ols, _formule_ols = fit_ols(frame, TARGET, EXPLANATORY, categorical=CATEGORICAL, cluster_column="ecole_id")
    tab_ols = ols_coefficients_table(result_ols)
    _check_output(save_table(tab_ols, "06_coefficients_ols"), "06_coefficients_ols")

    metriques_ols = regression_metrics(frame[TARGET], result_ols.fittedvalues)

    result_mixed, _formule_mixed = fit_mixed_effects(
        frame, TARGET, EXPLANATORY, group_column="ecole_id", categorical=CATEGORICAL
    )
    tab_mixed = mixed_effects_coefficients_table(result_mixed)
    _check_output(save_table(tab_mixed, "06_coefficients_mixte"), "06_coefficients_mixte")

    icc = intraclass_correlation(result_mixed)

    print("Tables de modélisation (06) régénérées.")
    return metriques_ols, icc


def generate_specialized_tables(df: pd.DataFrame):
    """Notebook 07 — tables de segmentation. Retourne school_profiles pour réutilisation éventuelle."""
    applicability = evaluate_specialized_methods(df)
    name = "07_applicabilite_methodes_specialisees"
    _check_output(save_table(applicability, name), name)

    school_profiles = build_school_level_panel(df)
    feature_cols = ["score_moyen", "ips_moyen", "taille_moyenne_classe", "part_dedoublement"]
    clustered, centers = cluster_school_profiles(
        school_profiles, feature_cols=feature_cols, n_clusters=3, random_state=42
    )

    cluster_summary = (
        clustered.groupby("cluster", observed=True)[feature_cols]
        .mean()
        .assign(effectif=clustered.groupby("cluster", observed=True).size())
        .sort_values("score_moyen", ascending=False)
    )
    _check_output(save_table(cluster_summary, "07_clusters_profils_ecoles"), "07_clusters_profils_ecoles")

    centers_sorted = centers.sort_values("cluster")
    _check_output(save_table(centers_sorted, "07_centres_clusters"), "07_centres_clusters")

    print("Tables spécialisées (07) régénérées.")


def generate_longitudinal_tables(df: pd.DataFrame):
    """Notebook 08 — tables longitudinales. Retourne gap_repplus_horsep pour réutilisation."""
    yearly_status = df.groupby(["annee", "statut"], observed=True)[TARGET].mean().reset_index()
    name = "08_serie_temporelle_score_par_statut"
    _check_output(save_table(yearly_status, name), name)

    trend_status = yearly_trend_by_group(df, value_col=TARGET, group_col="statut", time_col="annee")
    _check_output(save_table(trend_status, "08_tendance_lineaire_par_statut"), "08_tendance_lineaire_par_statut")

    gap_repplus_horsep = gap_over_time(
        df, value_col=TARGET, time_col="annee", group_col="statut", group_ref="Hors EP", group_compare="REP+"
    )
    name = "08_ecart_repplus_vs_horsep_temps"
    _check_output(save_table(gap_repplus_horsep, name), name)

    school_panel = build_school_level_panel(df, value_col=TARGET)
    _check_output(save_table(school_panel, "08_panel_ecole_annee"), "08_panel_ecole_annee")

    school_delta = school_panel.pivot(index="ecole_id", columns="annee", values="score_moyen")
    school_delta["delta_2017_2023"] = school_delta[2023] - school_delta[2017]
    delta_summary = school_delta["delta_2017_2023"].describe().to_frame(name="valeur")
    name = "08_distribution_delta_ecoles_2017_2023"
    _check_output(save_table(delta_summary, name), name)

    print("Tables longitudinales (08) régénérées.")
    return trend_status, gap_repplus_horsep


def generate_causal_tables(df: pd.DataFrame) -> None:
    """Notebook 09 — tables causales."""
    corr_vars = ["variable_cible", "ips", "taille_moyenne_classe", "dedoublement", "rep", "rep_plus"]
    correlation_matrix = df[corr_vars].corr(numeric_only=True)
    _check_output(save_table(correlation_matrix, "09_correlation_matrix"), "09_correlation_matrix")

    frame = prepare_model_frame(df, TARGET, EXPLANATORY, categorical=CATEGORICAL, group_column="ecole_id")
    result_ols, _formule = fit_ols(frame, TARGET, EXPLANATORY, categorical=CATEGORICAL, cluster_column="ecole_id")
    tab_ols = ols_coefficients_table(result_ols)
    association_table = tab_ols[[c for c in ["variable", "coefficient", "p_value"] if c in tab_ols.columns]]
    _check_output(save_table(association_table, "09_association_ols_coefficients"), "09_association_ols_coefficients")

    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    X = df[["statut", "niveau", "ips", "dedoublement", "taille_moyenne_classe", "effectif_eleves"]]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    categorical_features = ["statut", "niveau"]
    numeric_features = ["ips", "dedoublement", "taille_moyenne_classe", "effectif_eleves"]
    preprocess = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )
    pred_model = Pipeline(steps=[("preprocess", preprocess), ("model", LinearRegression())])
    pred_model.fit(X_train, y_train)
    y_pred = pred_model.predict(X_test)

    prediction_metrics = pd.DataFrame(
        [
            {"metrique": "R2_test", "valeur": r2_score(y_test, y_pred)},
            {"metrique": "RMSE_test", "valeur": np.sqrt(mean_squared_error(y_test, y_pred))},
            {"metrique": "MAE_test", "valeur": mean_absolute_error(y_test, y_pred)},
        ]
    )
    _check_output(save_table(prediction_metrics, "09_prediction_metrics"), "09_prediction_metrics")

    feasibility_df = pd.DataFrame([did_feasibility_report(df)])
    _check_output(save_table(feasibility_df, "09_faisabilite_causale_did"), "09_faisabilite_causale_did")

    print("Tables causales (09) régénérées.")


def generate_decision_indicators(
    df: pd.DataFrame,
    trend_status: pd.DataFrame,
    gap_repplus_horsep: pd.DataFrame,
    metriques_ols,
    icc,
) -> None:
    """Notebook 10 — indicateurs décisionnels."""
    indicateurs = build_decision_indicators(
        df=df,
        trend_table=trend_status,
        gap_table=gap_repplus_horsep,
        model_metrics=metriques_ols,
        icc=icc,
    )
    output_path = TABLES_DIR / "indicateurs_decisionnels.csv"
    indicateurs.to_csv(output_path, index=False)
    _check_output(output_path, "indicateurs_decisionnels")

    print("Indicateurs décisionnels (10) régénérés.")


def main() -> None:
    ensure_project_directories()
    print("Génération des tables...")

    try:
        df = load_processed_dataset(DATASET_NAME)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Impossible de charger le jeu de données '{DATASET_NAME}' : {exc}"
        ) from exc

    try:
        generate_descriptive_tables(df)
        metriques_ols, icc = generate_modeling_tables(df)
        generate_specialized_tables(df)
        trend_status, gap_repplus_horsep = generate_longitudinal_tables(df)
        generate_causal_tables(df)
        generate_decision_indicators(df, trend_status, gap_repplus_horsep, metriques_ols, icc)
    except Exception as exc:
        raise RuntimeError(f"Échec de la génération des tables : {exc}") from exc

    print("Toutes les tables ont été générées et vérifiées avec succès.")


if __name__ == "__main__":
    main()

