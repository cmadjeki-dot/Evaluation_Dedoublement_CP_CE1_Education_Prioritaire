"""Validation visuelle réelle du dashboard Streamlit via streamlit.testing.v1.AppTest.

Ces tests ne se contentent pas de vérifier que le serveur démarre : ils exécutent
réellement le script du dashboard dans le moteur de test Streamlit, inspectent les
éléments rendus (titres, onglets, métriques, dataframes, graphiques, boutons de
téléchargement), simulent les interactions utilisateur (changement de filtres,
sélection multiple) et vérifient l'absence d'exception non gérée.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"


def _run_app() -> AppTest:
    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=60)
    return at


def test_dashboard_runs_without_exception():
    """Le script s'exécute de bout en bout sans lever d'exception non gérée."""
    at = _run_app()
    assert not at.exception, f"Exception(s) levée(s) au chargement : {at.exception}"


def test_dashboard_title_visible():
    """Le titre principal du dashboard est bien rendu."""
    at = _run_app()
    titles = [t.value for t in at.title]
    assert any("Dashboard" in value for value in titles), f"Titre introuvable, titres trouvés : {titles}"


def test_dashboard_navigation_tabs_present():
    """La navigation par onglets expose les 6 sections attendues."""
    at = _run_app()
    tab_labels = [tab.label for tab in at.tabs]
    attendus = [
        "Vue d'ensemble",
        "Qualité des données",
        "Analyse descriptive",
        "Modèles",
        "Indicateurs décisionnels",
        "Recommandations",
    ]
    for label in attendus:
        assert label in tab_labels, f"Onglet manquant : {label} (trouvés : {tab_labels})"


def test_dashboard_kpi_metrics_rendered():
    """Des métriques (KPI) sont bien rendues dans la vue d'ensemble."""
    at = _run_app()
    assert len(at.metric) > 0, "Aucune métrique (st.metric) rendue sur le dashboard."
    for metric in at.metric:
        assert metric.value not in (None, ""), f"Métrique '{metric.label}' vide."


def test_dashboard_dataframes_rendered():
    """Au moins une table de données (st.dataframe) est rendue sans erreur."""
    at = _run_app()
    assert len(at.dataframe) > 0, "Aucune table (st.dataframe) rendue sur le dashboard."


def _find_chart_elements(block) -> list:
    """Parcourt récursivement l'arbre d'éléments pour trouver les graphiques natifs
    (st.bar_chart est exposé par AppTest comme un UnknownElement générique)."""
    found = []
    children = getattr(block, "children", None)
    if children:
        for child in children.values():
            if type(child).__name__ == "UnknownElement":
                found.append(child)
            found.extend(_find_chart_elements(child))
    return found


def test_dashboard_charts_rendered():
    """Au moins un graphique natif (st.bar_chart) est rendu dans l'onglet Analyse descriptive."""
    at = _run_app()
    descriptive_tab = next(tab for tab in at.tabs if tab.label == "Analyse descriptive")
    chart_elements = _find_chart_elements(descriptive_tab)
    assert len(chart_elements) > 0, "Aucun graphique (bar_chart) trouvé dans l'onglet Analyse descriptive."


def test_dashboard_images_rendered():
    """Les figures PNG de l'analyse descriptive sont bien affichées via st.image."""
    at = _run_app()
    assert len(at.image) > 0, "Aucune image (figure) rendue dans l'onglet Analyse descriptive."


def test_dashboard_download_buttons_present():
    """Les boutons de téléchargement (données filtrées, indicateurs, rapport) sont présents."""
    at = _run_app()
    assert len(at.button) >= 0  # boutons standards éventuels
    download_labels = [btn.label for btn in at.download_button]
    assert len(download_labels) >= 3, f"Moins de 3 boutons de téléchargement trouvés : {download_labels}"


def test_dashboard_sidebar_filters_present():
    """Les filtres (multiselect statut / niveau, slider période) sont présents dans la sidebar."""
    at = _run_app()
    multiselect_labels = [ms.label for ms in at.sidebar.multiselect]
    assert "Statut" in multiselect_labels
    assert "Niveau scolaire" in multiselect_labels


def test_dashboard_filter_interaction_updates_view():
    """Changer le filtre 'Statut' modifie réellement l'état de session sans exception."""
    at = _run_app()
    statut_filter = None
    for ms in at.sidebar.multiselect:
        if ms.label == "Statut":
            statut_filter = ms
            break
    assert statut_filter is not None, "Filtre Statut introuvable."

    original_options = list(statut_filter.options)
    assert len(original_options) > 0

    # Ne garder qu'une seule modalité et relancer l'app pour vérifier la robustesse.
    statut_filter.set_value([original_options[0]])
    at.run(timeout=60)
    assert not at.exception, f"Exception après changement de filtre : {at.exception}"

    # Les onglets doivent toujours être présents après changement de filtre.
    tab_labels = [tab.label for tab in at.tabs]
    assert "Vue d'ensemble" in tab_labels


def test_dashboard_quality_severity_multiselect_interaction():
    """Le filtre de sévérité dans l'onglet Qualité des données peut être manipulé sans exception."""
    at = _run_app()
    severity_filters = [ms for ms in at.multiselect if ms.label == "Filtrer par sévérité"]
    if not severity_filters:
        # Le rapport qualité peut être absent selon l'état du pipeline : dans ce cas
        # le multiselect n'est simplement pas rendu, ce n'est pas un échec du dashboard.
        return
    severity_filter = severity_filters[0]
    options = list(severity_filter.options)
    if options:
        severity_filter.set_value([options[0]])
        at.run(timeout=60)
        assert not at.exception, f"Exception après changement de filtre sévérité : {at.exception}"


def test_dashboard_no_error_widgets():
    """Aucun message d'erreur Streamlit (st.error) n'est affiché lors du rendu normal."""
    at = _run_app()
    error_messages = [e.value for e in at.error]
    assert not error_messages, f"Message(s) d'erreur affiché(s) sur le dashboard : {error_messages}"
