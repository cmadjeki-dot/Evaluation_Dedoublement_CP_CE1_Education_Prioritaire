"""Dashboard interactif Streamlit — restitution des résultats du projet.

Ce dashboard NE recalcule rien : il lit uniquement les artefacts déjà produits
par le pipeline (``outputs/tables``, ``outputs/figures``, ``outputs/reports``,
``outputs/models``, ``data/processed``). Si un artefact est absent, l'appli
l'indique clairement plutôt que de tenter de le régénérer.

Lancement :
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.paths import (  # noqa: E402
    FIGURES_DIR,
    MODELS_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    TABLES_DIR,
)

PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "education_prioritaire_analysis_ready.csv"

st.set_page_config(
    page_title="Dashboard - Évaluation du dédoublement CP/CE1",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Chargement des artefacts (lecture seule, mis en cache)
# --------------------------------------------------------------------------
@st.cache_data
def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return pd.read_csv(path)


@st.cache_data
def load_json(path: Path) -> dict | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_text(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    return path.read_text(encoding="utf-8")


def missing_artifact(label: str, path: Path) -> None:
    st.warning(
        f"Artefact manquant : **{label}**\n\n"
        f"Chemin attendu : `{path}`\n\n"
        "Exécutez `python scripts/run_pipeline.py` pour le générer."
    )


# Données analysis-ready (pour filtres/tableaux/téléchargements)
data = load_csv(PROCESSED_DATA_PATH)

# Tables
indicateurs = load_csv(TABLES_DIR / "indicateurs_decisionnels.csv")
comparaison_statut = load_csv(TABLES_DIR / "05_comparaison_statut.csv")
comparaison_dedoublement = load_csv(TABLES_DIR / "05_comparaison_dedoublement.csv")
crosstab = load_csv(TABLES_DIR / "05_crosstab_statut_niveau_moyenne.csv")
tests_diff = load_csv(TABLES_DIR / "05_tests_difference_statut.csv")
coeff_ols = load_csv(TABLES_DIR / "06_coefficients_ols.csv")
coeff_mixte = load_csv(TABLES_DIR / "06_coefficients_mixte.csv")
serie_temporelle = load_csv(TABLES_DIR / "08_serie_temporelle_score_par_statut.csv")
tendance_lineaire = load_csv(TABLES_DIR / "08_tendance_lineaire_par_statut.csv")
faisabilite_did = load_csv(TABLES_DIR / "09_faisabilite_causale_did.csv")
prediction_metrics = load_csv(TABLES_DIR / "09_prediction_metrics.csv")

# Rapports qualité
rapport_qualite = load_json(REPORTS_DIR / "rapport_qualite_donnees_brutes.json")
rapport_resume_txt = load_text(REPORTS_DIR / "rapport_resume.txt")

# Modèle
modele_resume = load_text(MODELS_DIR / "06_modele_ols_variable_cible_resume.txt")


# --------------------------------------------------------------------------
# Barre latérale : filtres
# --------------------------------------------------------------------------
st.sidebar.title("Filtres")
st.sidebar.caption("Les filtres s'appliquent aux vues basées sur les données `data/processed/`.")

if data is not None:
    statuts_disponibles = sorted(data["statut"].dropna().unique().tolist())
    niveaux_disponibles = sorted(data["niveau"].dropna().unique().tolist())
    annees_disponibles = sorted(data["annee"].dropna().unique().tolist())

    statuts_selectionnes = st.sidebar.multiselect("Statut", statuts_disponibles, default=statuts_disponibles)
    niveaux_selectionnes = st.sidebar.multiselect("Niveau scolaire", niveaux_disponibles, default=niveaux_disponibles)
    annee_min, annee_max = st.sidebar.select_slider(
        "Période",
        options=annees_disponibles,
        value=(min(annees_disponibles), max(annees_disponibles)),
    )

    data_filtree = data[
        data["statut"].isin(statuts_selectionnes)
        & data["niveau"].isin(niveaux_selectionnes)
        & data["annee"].between(annee_min, annee_max)
    ]
else:
    data_filtree = None
    st.sidebar.info("Données processed introuvables : filtres indisponibles.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Ce dashboard lit uniquement les résultats déjà calculés par le pipeline. "
    "Il ne relance aucun traitement scientifique."
)

# --------------------------------------------------------------------------
# En-tête
# --------------------------------------------------------------------------
st.title("Dashboard de synthèse")
st.caption("Effet du dédoublement des classes de CP/CE1 en éducation prioritaire sur les performances scolaires.")
st.caption("Données simulées de manière reproductible (seed fixe) — voir `src/data/acquisition.py`.")

tab_overview, tab_quality, tab_descriptive, tab_models, tab_indicators, tab_recommendations = st.tabs(
    [
        "Vue d'ensemble",
        "Qualité des données",
        "Analyse descriptive",
        "Modèles",
        "Indicateurs décisionnels",
        "Recommandations",
    ]
)

# --------------------------------------------------------------------------
# Onglet Vue d'ensemble (KPI)
# --------------------------------------------------------------------------
with tab_overview:
    st.header("Vue d'ensemble")

    if indicateurs is not None:
        kpi_row = indicateurs.set_index("nom")
        col1, col2, col3, col4 = st.columns(4)
        try:
            col1.metric("Score global moyen", f"{kpi_row.loc['Score global moyen', 'valeur']:.2f} / 100")
            col2.metric("Écart REP+ vs Hors EP", f"{kpi_row.loc['Écart REP+ vs Hors EP', 'valeur']:.2f} pts")
            col3.metric("R² modèle OLS", f"{kpi_row.loc['R² modèle explicatif OLS', 'valeur']:.3f}")
            part_dedoublees = kpi_row.loc["Part d'observations dédoublées", "valeur"]
            col4.metric("Part d'observations dédoublées", f"{part_dedoublees:.1%}")
        except KeyError:
            st.dataframe(indicateurs, use_container_width=True)
    else:
        missing_artifact("indicateurs_decisionnels.csv", TABLES_DIR / "indicateurs_decisionnels.csv")

    if rapport_resume_txt:
        st.subheader("Résumé synthétique")
        st.text(rapport_resume_txt)

    if data_filtree is not None:
        st.subheader("Aperçu des données filtrées")
        st.write(f"{len(data_filtree)} observation(s) sur {len(data)} au total.")
        st.dataframe(data_filtree.head(200), use_container_width=True)
        st.download_button(
            "Télécharger les données filtrées (CSV)",
            data_filtree.to_csv(index=False).encode("utf-8"),
            file_name="donnees_filtrees.csv",
            mime="text/csv",
        )

# --------------------------------------------------------------------------
# Onglet Qualité des données
# --------------------------------------------------------------------------
with tab_quality:
    st.header("Qualité des données")

    if rapport_qualite is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lignes", rapport_qualite.get("n_rows"))
        col2.metric("Colonnes", rapport_qualite.get("n_columns"))
        counts = rapport_qualite.get("summary_counts", {})
        col3.metric("Anomalies critiques", counts.get("CRITIQUE", 0))
        col4.metric("Anomalies importantes", counts.get("IMPORTANT", 0))

        issues = pd.DataFrame(rapport_qualite.get("issues", []))
        if not issues.empty:
            severite = st.multiselect(
                "Filtrer par sévérité",
                sorted(issues["severity"].unique()),
                default=list(issues["severity"].unique()),
            )
            st.dataframe(issues[issues["severity"].isin(severite)], use_container_width=True)
    else:
        missing_artifact("rapport_qualite_donnees_brutes.json", REPORTS_DIR / "rapport_qualite_donnees_brutes.json")

    rapport_qualite_md = load_text(REPORTS_DIR / "rapport_qualite_donnees_brutes.md")
    if rapport_qualite_md:
        with st.expander("Voir le rapport qualité complet (Markdown)"):
            st.markdown(rapport_qualite_md)

# --------------------------------------------------------------------------
# Onglet Analyse descriptive
# --------------------------------------------------------------------------
with tab_descriptive:
    st.header("Analyse descriptive")

    col_left, col_right = st.columns(2)
    with col_left:
        if comparaison_statut is not None:
            st.subheader("Score moyen par statut")
            st.bar_chart(comparaison_statut.set_index("statut")["moyenne"])
            st.dataframe(comparaison_statut, use_container_width=True)
        else:
            missing_artifact("05_comparaison_statut.csv", TABLES_DIR / "05_comparaison_statut.csv")

    with col_right:
        if comparaison_dedoublement is not None:
            st.subheader("Score moyen selon exposition au dédoublement")
            st.dataframe(comparaison_dedoublement, use_container_width=True)
        else:
            missing_artifact("05_comparaison_dedoublement.csv", TABLES_DIR / "05_comparaison_dedoublement.csv")

    if crosstab is not None:
        st.subheader("Tableau croisé statut × niveau (score moyen)")
        st.dataframe(crosstab, use_container_width=True)

    if tests_diff is not None:
        st.subheader("Tests de différence entre statuts")
        st.dataframe(tests_diff, use_container_width=True)

    st.subheader("Figures")
    figure_files = sorted(FIGURES_DIR.glob("05_*.png"))
    if figure_files:
        cols = st.columns(2)
        for index, figure_path in enumerate(figure_files):
            with cols[index % 2]:
                st.image(str(figure_path), caption=figure_path.name, use_container_width=True)
    else:
        missing_artifact("figures d'analyse descriptive (05_*.png)", FIGURES_DIR)

# --------------------------------------------------------------------------
# Onglet Modèles
# --------------------------------------------------------------------------
with tab_models:
    st.header("Modèles")

    if coeff_ols is not None:
        st.subheader("Coefficients — modèle OLS")
        st.dataframe(coeff_ols, use_container_width=True)
    else:
        missing_artifact("06_coefficients_ols.csv", TABLES_DIR / "06_coefficients_ols.csv")

    if coeff_mixte is not None:
        st.subheader("Coefficients — modèle à effets mixtes")
        st.dataframe(coeff_mixte, use_container_width=True)

    if prediction_metrics is not None:
        st.subheader("Métriques de prédiction")
        st.dataframe(prediction_metrics, use_container_width=True)

    diagnostics_path = FIGURES_DIR / "06_diagnostics_ols.png"
    if diagnostics_path.exists():
        st.subheader("Diagnostics du modèle OLS")
        st.image(str(diagnostics_path), use_container_width=True)

    if modele_resume:
        with st.expander("Voir le résumé statsmodels complet"):
            st.text(modele_resume)

    if serie_temporelle is not None:
        st.subheader("Évolution temporelle du score par statut")
        pivot = serie_temporelle.pivot(index="annee", columns="statut", values="variable_cible")
        st.line_chart(pivot)

    if tendance_lineaire is not None:
        st.subheader("Tendance annuelle par statut")
        st.dataframe(tendance_lineaire, use_container_width=True)

    if faisabilite_did is not None:
        st.subheader("Faisabilité d'une analyse causale (différence-de-différences)")
        st.dataframe(faisabilite_did, use_container_width=True)

# --------------------------------------------------------------------------
# Onglet Indicateurs décisionnels
# --------------------------------------------------------------------------
with tab_indicators:
    st.header("Indicateurs décisionnels")

    if indicateurs is not None:
        for _, row in indicateurs.iterrows():
            with st.expander(f"{row['nom']} — {row['valeur']:.4g} {row['unite']}"):
                st.write(f"**Définition** : {row['definition']}")
                st.write(f"**Formule** : `{row['formule']}`")
                st.write(f"**Population** : {row['population']}")
                st.write(f"**Interprétation** : {row['interpretation']}")
                st.write(f"**Limites** : {row['limites']}")
                st.write(f"**Utilisation possible** : {row['utilisation_possible']}")

        st.download_button(
            "Télécharger la table des indicateurs (CSV)",
            indicateurs.to_csv(index=False).encode("utf-8"),
            file_name="indicateurs_decisionnels.csv",
            mime="text/csv",
        )
    else:
        missing_artifact("indicateurs_decisionnels.csv", TABLES_DIR / "indicateurs_decisionnels.csv")

# --------------------------------------------------------------------------
# Onglet Recommandations / rapport
# --------------------------------------------------------------------------
with tab_recommendations:
    st.header("Recommandations et rapport final")

    rapport_final_path = PROJECT_ROOT / "docs" / "rapport_final.md"
    rapport_final = load_text(rapport_final_path)
    if rapport_final:
        st.markdown(rapport_final)
        st.download_button(
            "Télécharger le rapport final (Markdown)",
            rapport_final.encode("utf-8"),
            file_name="rapport_final.md",
            mime="text/markdown",
        )
    else:
        missing_artifact("rapport_final.md", rapport_final_path)
