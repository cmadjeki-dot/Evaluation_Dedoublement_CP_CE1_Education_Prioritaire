from __future__ import annotations

"""Outils d'analyses avancées (spécialisée, longitudinale, causalité faisable/non faisable)."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class ApplicabilityDecision:
    """Décision d'applicabilité pour une famille d'analyse."""

    domaine: str
    applicable: bool
    justification: str

    def label(self) -> str:
        return "APPLICABLE" if self.applicable else "NON APPLICABLE"


def evaluate_specialized_methods(df: pd.DataFrame) -> pd.DataFrame:
    """Évalue la pertinence des méthodes spécialisées demandées par le cahier des charges."""
    methods = [
        "psychometrie",
        "series_temporelles",
        "segmentation",
        "clustering",
        "analyse_spatiale",
        "nlp",
        "causalite",
        "longitudinal",
        "scoring",
        "prevision",
        "survie",
        "multiniveaux",
    ]
    rows: list[dict[str, str | bool]] = []

    n_years = int(df["annee"].nunique())
    has_text = any(str(df[col].dtype) == "object" and col not in {"source", "source_url"} for col in df.columns)
    has_geo = {"academie", "departement"}.issubset(df.columns)
    has_hierarchy = "ecole_id" in df.columns and df.groupby("ecole_id").size().min() > 1
    has_binary_target = set(pd.Series(df["variable_cible"]).dropna().unique()).issubset({0, 1})

    for method in methods:
        applicable = False
        justification = "Non retenu."

        if method == "psychometrie":
            applicable = False
            justification = (
                "NON APPLICABLE : pas d'items de test individuels ni de matrice item-réponse "
                "(scores agrégés uniquement)."
            )
        elif method == "series_temporelles":
            applicable = n_years >= 5
            justification = (
                "APPLICABLE : 7 années observées permettent une analyse de tendance temporelle agrégée."
                if applicable
                else "NON APPLICABLE : historique temporel insuffisant."
            )
        elif method in {"segmentation", "clustering"}:
            applicable = True
            justification = (
                "APPLICABLE : les écoles peuvent être segmentées selon IPS, taille de classe et scores ; "
                "utile pour profiler des contextes d'intervention."
            )
        elif method == "analyse_spatiale":
            applicable = has_geo
            justification = (
                "APPLICABLE : présence d'agrégats territoriaux (département/académie), "
                "mais pas de coordonnées fines pour l'autocorrélation spatiale."
            )
        elif method == "nlp":
            applicable = has_text
            justification = (
                "NON APPLICABLE : pas de corpus textuel métier exploitable pour NLP."
                if not applicable
                else "APPLICABLE : présence de texte libre."
            )
        elif method == "causalite":
            applicable = False
            justification = (
                "NON APPLICABLE en inférence forte : statut et exposition varient aléatoirement "
                "dans les données simulées, sans protocole d'identification crédible."
            )
        elif method == "longitudinal":
            applicable = has_hierarchy and n_years >= 3
            justification = (
                "APPLICABLE : panel écoles répété sur 7 ans, permettant des trajectoires au niveau école."
            )
        elif method == "scoring":
            applicable = True
            justification = "APPLICABLE : variable cible continue adaptée à un score prédictif."
        elif method == "prevision":
            applicable = n_years >= 5
            justification = (
                "APPLICABLE avec prudence : courte série (7 ans) utile pour projection simple, "
                "pas pour prévision structurelle robuste."
            )
        elif method == "survie":
            applicable = False
            justification = "NON APPLICABLE : absence de temps-jusqu'à-événement et de censure."
        elif method == "multiniveaux":
            applicable = has_hierarchy
            justification = (
                "APPLICABLE : structure hiérarchique (observations répétées au sein des écoles)."
            )

        rows.append(
            {
                "methode": method,
                "applicable": bool(applicable),
                "statut": "APPLICABLE" if applicable else "NON APPLICABLE",
                "justification": justification,
            }
        )
    return pd.DataFrame(rows)


def yearly_trend_by_group(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    time_col: str = "annee",
) -> pd.DataFrame:
    """Calcule la pente temporelle (régression linéaire simple) par groupe."""
    rows: list[dict[str, float | int | str]] = []
    for group_value, group_df in df.groupby(group_col, observed=True):
        yearly = group_df.groupby(time_col, observed=True)[value_col].mean().sort_index()
        x = yearly.index.to_numpy(dtype=float)
        y = yearly.to_numpy(dtype=float)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        rows.append(
            {
                group_col: str(group_value),
                "n_points_temporels": int(len(yearly)),
                "pente_par_an": float(slope),
                "interception": float(intercept),
                "r": float(r_value),
                "r2": float(r_value**2),
                "p_value_pente": float(p_value),
                "erreur_standard_pente": float(std_err),
                "moyenne_debut": float(y[0]),
                "moyenne_fin": float(y[-1]),
                "delta_debut_fin": float(y[-1] - y[0]),
            }
        )
    return pd.DataFrame(rows).sort_values("pente_par_an", ascending=False).reset_index(drop=True)


def gap_over_time(
    df: pd.DataFrame,
    value_col: str,
    time_col: str,
    group_col: str,
    group_ref: str,
    group_compare: str,
) -> pd.DataFrame:
    """Calcule l'écart moyen dans le temps entre deux groupes."""
    yearly = (
        df[df[group_col].isin([group_ref, group_compare])]
        .groupby([time_col, group_col], observed=True)[value_col]
        .mean()
        .unstack(group_col)
        .sort_index()
    )
    if group_ref not in yearly.columns or group_compare not in yearly.columns:
        raise ValueError("Groupes introuvables pour le calcul d'écart temporel.")

    out = yearly.copy()
    out["ecart_compare_moins_ref"] = out[group_compare] - out[group_ref]
    return out.reset_index()


def build_school_level_panel(df: pd.DataFrame, value_col: str = "variable_cible") -> pd.DataFrame:
    """Construit un panel école-année agrégé (moyenne sur niveaux)."""
    panel = (
        df.groupby(["ecole_id", "annee"], observed=True)
        .agg(
            score_moyen=(value_col, "mean"),
            ips_moyen=("ips", "mean"),
            taille_moyenne_classe=("taille_moyenne_classe", "mean"),
            part_dedoublement=("dedoublement", "mean"),
            rep=("rep", "mean"),
            rep_plus=("rep_plus", "mean"),
            statut_mode=("statut", lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan),
        )
        .reset_index()
    )
    return panel


def did_feasibility_report(df: pd.DataFrame) -> dict[str, object]:
    """Évalue la faisabilité d'une stratégie causale type DiD.

    L'évaluation suit des prérequis minimaux :
    - unités cohérentes dans le temps (statut relativement stable ou transition interprétable),
    - traitement aligné avec le protocole policy (ici CP/CE1 prioritairement),
    - présence d'un groupe de comparaison crédible,
    - fenêtre pré-traitement identifiable.
    """
    ecole_year = df.drop_duplicates(["ecole_id", "annee"])[["ecole_id", "annee", "statut"]]
    statut_changes = (
        ecole_year.sort_values(["ecole_id", "annee"])
        .groupby("ecole_id")["statut"]
        .apply(lambda s: int((s != s.shift()).sum()))
    )
    share_schools_with_changes = float((statut_changes > 0).mean())

    cp_ce1 = df[df["niveau"].isin(["CP", "CE1"])]
    others = df[~df["niveau"].isin(["CP", "CE1"])]
    treat_cpce1 = float(cp_ce1["dedoublement"].mean())
    treat_others = float(others["dedoublement"].mean())
    protocol_alignment_gap = abs(treat_cpce1 - treat_others)

    # L'alignement est jugé crédible seulement si le traitement est nettement plus élevé en CP/CE1.
    aligned_with_policy = protocol_alignment_gap >= 0.15

    # Groupe de comparaison minimal : présence durable de Hors EP et REP/REP+ chaque année.
    year_status_counts = (
        df.drop_duplicates(["ecole_id", "annee"])
        .groupby(["annee", "statut"], observed=True)["ecole_id"]
        .nunique()
        .unstack("statut")
        .fillna(0)
    )
    has_controls_each_year = bool((year_status_counts.min(axis=1) > 0).all())

    reasons: list[str] = []
    if share_schools_with_changes > 0.3:
        reasons.append(
            "Les statuts des écoles varient fortement dans le temps (changement annuel fréquent), "
            "ce qui invalide l'interprétation d'un groupe traité stable."
        )
    if not aligned_with_policy:
        reasons.append(
            "L'exposition au dédoublement n'est pas spécifique à CP/CE1 dans ces données "
            "(écart CP/CE1 vs autres niveaux trop faible)."
        )
    if not has_controls_each_year:
        reasons.append(
            "Les groupes de comparaison ne sont pas présents de façon robuste sur toutes les années."
        )

    applicable = len(reasons) == 0
    return {
        "applicable": applicable,
        "share_schools_with_status_changes": share_schools_with_changes,
        "mean_treatment_cp_ce1": treat_cpce1,
        "mean_treatment_other_levels": treat_others,
        "policy_alignment_gap": protocol_alignment_gap,
        "has_controls_each_year": has_controls_each_year,
        "reasons_if_not_applicable": reasons,
    }


def build_decision_indicators(
    df: pd.DataFrame,
    trend_table: pd.DataFrame,
    gap_table: pd.DataFrame,
    model_metrics: dict[str, float],
    icc: float,
) -> pd.DataFrame:
    """Construit 5 à 10 indicateurs décisionnels calculés depuis les données réelles du projet."""
    rows: list[dict[str, object]] = []

    global_mean = float(df["variable_cible"].mean())
    rows.append(
        {
            "nom": "Score global moyen",
            "definition": "Moyenne de la variable cible sur l'ensemble des observations.",
            "formule": "mean(variable_cible)",
            "valeur": global_mean,
            "unite": "points sur 100",
            "population": "Toutes observations (2017-2023, CP à 6e)",
            "interpretation": "Niveau moyen de performance globale du système observé.",
            "limites": "Agrégation globale masquant les écarts territoriaux et de statut.",
            "utilisation_possible": "Repère macro pour suivre l'évolution générale annuelle.",
        }
    )

    means = df.groupby("statut", observed=True)["variable_cible"].mean()
    gap_rep_plus = float(means["REP+"] - means["Hors EP"])
    rows.append(
        {
            "nom": "Écart REP+ vs Hors EP",
            "definition": "Différence de score moyen entre REP+ et Hors EP.",
            "formule": "mean(variable_cible|REP+) - mean(variable_cible|Hors EP)",
            "valeur": gap_rep_plus,
            "unite": "points sur 100",
            "population": "Statuts REP+ et Hors EP",
            "interpretation": "Mesure brute de l'inégalité de performance entre extrêmes de statut.",
            "limites": "Indicateur associatif non causal, sensible à la composition des groupes.",
            "utilisation_possible": "Priorisation des dispositifs d'appui vers les zones REP+.",
        }
    )

    trend_map = trend_table.set_index("statut")["pente_par_an"]
    rows.append(
        {
            "nom": "Tendance annuelle Hors EP",
            "definition": "Pente de la tendance temporelle du score moyen Hors EP.",
            "formule": "slope(annee -> mean(variable_cible|Hors EP))",
            "valeur": float(trend_map["Hors EP"]),
            "unite": "points/an",
            "population": "Observations Hors EP",
            "interpretation": "Variation moyenne annuelle du score Hors EP.",
            "limites": "Tendance linéaire simplifiée sur 7 années.",
            "utilisation_possible": "Étalonnage d'une dynamique de référence hors EP.",
        }
    )
    rows.append(
        {
            "nom": "Tendance annuelle REP+",
            "definition": "Pente de la tendance temporelle du score moyen REP+.",
            "formule": "slope(annee -> mean(variable_cible|REP+))",
            "valeur": float(trend_map["REP+"]),
            "unite": "points/an",
            "population": "Observations REP+",
            "interpretation": "Variation moyenne annuelle du score REP+.",
            "limites": "Tendance linéaire simplifiée sur 7 années.",
            "utilisation_possible": "Suivi de l'intensité de progression en éducation prioritaire renforcée.",
        }
    )

    gap_col = "ecart_compare_moins_ref"
    gap_delta = float(gap_table[gap_col].iloc[-1] - gap_table[gap_col].iloc[0])
    rows.append(
        {
            "nom": "Évolution de l'écart REP+ vs Hors EP (2017→2023)",
            "definition": "Variation de l'écart de score REP+ moins Hors EP entre début et fin de période.",
            "formule": "(gap_2023) - (gap_2017)",
            "valeur": gap_delta,
            "unite": "points sur 100",
            "population": "REP+ et Hors EP par année",
            "interpretation": "Négatif = creusement de l'écart en défaveur de REP+.",
            "limites": "Ne prouve pas un effet causal d'une politique.",
            "utilisation_possible": "Alerte stratégique sur réduction ou aggravation des inégalités.",
        }
    )

    dedoublement_share = float(df["dedoublement"].mean())
    rows.append(
        {
            "nom": "Part d'observations dédoublées",
            "definition": "Proportion d'observations avec dedoublement=1.",
            "formule": "mean(dedoublement)",
            "valeur": dedoublement_share,
            "unite": "proportion (0-1)",
            "population": "Toutes observations",
            "interpretation": "Mesure l'intensité d'exposition au dédoublement dans le panel.",
            "limites": "Ne renseigne pas à elle seule sur l'efficacité pédagogique.",
            "utilisation_possible": "Suivi de couverture du dispositif.",
        }
    )

    rows.append(
        {
            "nom": "RMSE modèle explicatif OLS",
            "definition": "Erreur quadratique moyenne racine du modèle OLS sur le jeu observé.",
            "formule": "sqrt(mean((y - y_pred)^2))",
            "valeur": float(model_metrics["rmse"]),
            "unite": "points sur 100",
            "population": "Toutes observations (in-sample)",
            "interpretation": "Ordre de grandeur de l'erreur moyenne de prédiction du modèle.",
            "limites": "Mesure in-sample, non validée ici sur jeu externe.",
            "utilisation_possible": "Suivi de la robustesse d'un outil de pilotage prédictif.",
        }
    )

    rows.append(
        {
            "nom": "R² modèle explicatif OLS",
            "definition": "Part de variance expliquée par le modèle OLS.",
            "formule": "1 - SSE/SST",
            "valeur": float(model_metrics["r2"]),
            "unite": "proportion (0-1)",
            "population": "Toutes observations (in-sample)",
            "interpretation": "Capacité explicative globale des variables retenues.",
            "limites": "Ne démontre pas la causalité des effets.",
            "utilisation_possible": "Comparer versions successives du modèle explicatif.",
        }
    )

    rows.append(
        {
            "nom": "ICC effet école (modèle mixte)",
            "definition": "Part de variance résiduelle attribuable aux différences inter-écoles.",
            "formule": "var_inter_ecole / (var_inter_ecole + var_residuelle)",
            "valeur": float(icc),
            "unite": "proportion (0-1)",
            "population": "Toutes observations",
            "interpretation": "Faible valeur = faible surcroît d'information école après contrôles.",
            "limites": "Dépend de la spécification du modèle mixte.",
            "utilisation_possible": "Décider du niveau de granularité du pilotage (école vs macro).",
        }
    )

    indicators = pd.DataFrame(rows)
    indicators["valeur"] = indicators["valeur"].astype(float).round(6)
    return indicators


def cluster_school_profiles(
    school_panel: pd.DataFrame,
    feature_cols: list[str],
    n_clusters: int = 3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Segmente les écoles via K-Means sur un profil de variables numériques."""
    if n_clusters < 2:
        raise ValueError("n_clusters doit être >= 2.")

    features = school_panel[feature_cols].copy()
    if features.isna().sum().sum() > 0:
        raise ValueError("Le clustering ne supporte pas les valeurs manquantes.")

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(features)
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    labels = kmeans.fit_predict(x_scaled)

    segmented = school_panel.copy()
    segmented["cluster"] = labels

    centers_scaled = pd.DataFrame(kmeans.cluster_centers_, columns=feature_cols)
    centers_original = pd.DataFrame(
        scaler.inverse_transform(centers_scaled),
        columns=feature_cols,
    )
    centers_original["cluster"] = centers_original.index
    return segmented, centers_original


__all__ = [
    "ApplicabilityDecision",
    "evaluate_specialized_methods",
    "yearly_trend_by_group",
    "gap_over_time",
    "build_school_level_panel",
    "did_feasibility_report",
    "build_decision_indicators",
    "cluster_school_profiles",
]
