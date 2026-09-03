"""Génère automatiquement toutes les figures du projet à partir des données processed.

Ce script ne recopie pas la logique métier : il réutilise exclusivement les
fonctions déjà définies dans ``src/`` (chargement des données, statistiques,
modélisation, analyses avancées) et reproduit uniquement le code de tracé
matplotlib présent dans les notebooks 05, 06, 07 et 08.

Chaque figure générée est vérifiée : le fichier doit exister et ne pas être
vide, sinon une erreur explicite (RuntimeError) est levée.

Usage :
    python scripts/generate_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")  # backend non interactif : nécessaire pour un script

import matplotlib.pyplot as plt
import statsmodels.api as sm

from src.analysis import (
    distribution_table,
    figures_output_dir,
    group_comparison_table,
)
from src.analysis.advanced import (
    build_school_level_panel,
    cluster_school_profiles,
    gap_over_time,
)
from src.data import load_processed_dataset
from src.modeling import fit_ols, prepare_model_frame

DATASET_NAME = "education_prioritaire"
TARGET = "variable_cible"
EXPLANATORY = ["statut", "niveau", "ips", "dedoublement"]
CATEGORICAL = ["statut", "niveau"]

plt.rcParams["figure.dpi"] = 100


def _check_output(path: Path, label: str) -> Path:
    """Vérifie qu'une figure a bien été écrite (existence + non vide)."""
    if not path.exists():
        raise RuntimeError(f"Échec de génération de la figure '{label}' : fichier absent ({path})")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Échec de génération de la figure '{label}' : fichier vide ({path})")
    return path


def generate_descriptive_figures(df, fig_dir: Path) -> None:
    """Notebook 05 — figures descriptives."""
    # 05_distribution_variable_cible.png
    dist = distribution_table(df, TARGET, bins=10)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(
        dist["borne_basse"],
        dist["effectif"],
        width=(dist["borne_haute"] - dist["borne_basse"]) * 0.9,
        align="edge",
        color="#4C72B0",
        edgecolor="black",
    )
    ax.set_title("Distribution du score global (variable cible)")
    ax.set_xlabel("Score global (0-100)")
    ax.set_ylabel("Nombre d'observations (effectif)")
    fig.tight_layout()
    path = fig_dir / "05_distribution_variable_cible.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "05_distribution_variable_cible")

    # 05_moyenne_par_statut.png
    tab_statut = group_comparison_table(df, TARGET, "statut")
    fig, ax = plt.subplots(figsize=(7, 5))
    order = tab_statut.sort_values("moyenne", ascending=False)
    ax.bar(
        order["statut"],
        order["moyenne"],
        yerr=order["moyenne"] - order["ic_95_basse"],
        capsize=6,
        color=["#55A868", "#DD8452", "#C44E52"],
    )
    ax.set_title("Score global moyen par statut d'éducation prioritaire (IC 95%)")
    ax.set_xlabel("Statut")
    ax.set_ylabel("Score global moyen (0-100)")
    fig.tight_layout()
    path = fig_dir / "05_moyenne_par_statut.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "05_moyenne_par_statut")

    # 05_score_par_niveau_statut.png
    ordre_niveaux = ["CP", "CE1", "CM1", "CM2", "6e"]
    ct_moyenne = df.pivot_table(index="statut", columns="niveau", values=TARGET, aggfunc="mean")
    ct_plot = ct_moyenne[ordre_niveaux]
    fig, ax = plt.subplots(figsize=(8, 5))
    for statut in ct_plot.index:
        ax.plot(ordre_niveaux, ct_plot.loc[statut], marker="o", label=statut)
    ax.set_title("Score global moyen par niveau scolaire et statut")
    ax.set_xlabel("Niveau scolaire (ordre chronologique)")
    ax.set_ylabel("Score global moyen (0-100)")
    ax.legend(title="Statut")
    fig.tight_layout()
    path = fig_dir / "05_score_par_niveau_statut.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "05_score_par_niveau_statut")

    # 05_score_vs_ips.png
    fig, ax = plt.subplots(figsize=(7, 5))
    couleurs = {"Hors EP": "#55A868", "REP": "#DD8452", "REP+": "#C44E52"}
    for statut, sous_df in df.groupby("statut"):
        ax.scatter(
            sous_df["ips"], sous_df[TARGET], s=8, alpha=0.4, label=statut, color=couleurs.get(statut)
        )
    ax.set_title("Score global en fonction de l'IPS, par statut")
    ax.set_xlabel("IPS (indice de position sociale)")
    ax.set_ylabel("Score global (0-100)")
    ax.legend(title="Statut")
    fig.tight_layout()
    path = fig_dir / "05_score_vs_ips.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "05_score_vs_ips")

    print("Figures descriptives (05) régénérées.")


def generate_modeling_figures(df, fig_dir: Path) -> None:
    """Notebook 06 — diagnostics du modèle OLS."""
    frame = prepare_model_frame(df, TARGET, EXPLANATORY, categorical=CATEGORICAL, group_column="ecole_id")
    result_ols, _formule_ols = fit_ols(frame, TARGET, EXPLANATORY, categorical=CATEGORICAL, cluster_column="ecole_id")

    residus = result_ols.resid
    valeurs_ajustees = result_ols.fittedvalues

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(valeurs_ajustees, residus, s=6, alpha=0.4, color="#4C72B0")
    axes[0].axhline(0, color="red", linestyle="--")
    axes[0].set_title("Résidus vs valeurs ajustées")
    axes[0].set_xlabel("Score global prédit (0-100)")
    axes[0].set_ylabel("Résidu (observé - prédit)")

    sm.qqplot(residus, line="45", ax=axes[1])
    axes[1].set_title("Diagramme quantile-quantile des résidus")

    fig.tight_layout()
    path = fig_dir / "06_diagnostics_ols.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "06_diagnostics_ols")

    print("Figures de modélisation (06) régénérées.")


def generate_specialized_figures(df, fig_dir: Path) -> None:
    """Notebook 07 — segmentation des écoles."""
    school_profiles = build_school_level_panel(df)
    feature_cols = ["score_moyen", "ips_moyen", "taille_moyenne_classe", "part_dedoublement"]
    clustered, _centers = cluster_school_profiles(
        school_profiles, feature_cols=feature_cols, n_clusters=3, random_state=42
    )

    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(
        clustered["ips_moyen"],
        clustered["score_moyen"],
        c=clustered["cluster"],
        cmap="viridis",
        s=45,
        alpha=0.8,
    )
    ax.set_title("Segmentation des écoles : score moyen vs IPS moyen")
    ax.set_xlabel("IPS moyen (indice de position sociale)")
    ax.set_ylabel("Score moyen (0-100)")
    legend = ax.legend(*scatter.legend_elements(), title="Cluster")
    ax.add_artist(legend)
    fig.tight_layout()
    path = fig_dir / "07_segmentation_ecoles.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "07_segmentation_ecoles")

    print("Figures spécialisées (07) régénérées.")


def generate_longitudinal_figures(df, fig_dir: Path) -> None:
    """Notebook 08 — figures longitudinales."""
    # 08_tendance_temporelle_statut.png
    yearly_status = df.groupby(["annee", "statut"], observed=True)[TARGET].mean().reset_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    for statut, sdf in yearly_status.groupby("statut", observed=True):
        ax.plot(sdf["annee"], sdf[TARGET], marker="o", label=statut)
    ax.set_title("Évolution temporelle du score moyen par statut")
    ax.set_xlabel("Année")
    ax.set_ylabel("Score moyen (0-100)")
    ax.legend(title="Statut")
    fig.tight_layout()
    path = fig_dir / "08_tendance_temporelle_statut.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "08_tendance_temporelle_statut")

    # 08_ecart_repplus_horsep_temps.png
    gap_repplus_horsep = gap_over_time(
        df, value_col=TARGET, time_col="annee", group_col="statut", group_ref="Hors EP", group_compare="REP+"
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(
        gap_repplus_horsep["annee"],
        gap_repplus_horsep["ecart_compare_moins_ref"],
        marker="o",
        color="#C44E52",
    )
    ax.axhline(0, color="black", linestyle="--")
    ax.set_title("Écart temporel REP+ - Hors EP")
    ax.set_xlabel("Année")
    ax.set_ylabel("Écart de score (points)")
    fig.tight_layout()
    path = fig_dir / "08_ecart_repplus_horsep_temps.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "08_ecart_repplus_horsep_temps")

    # 08_distribution_delta_ecoles.png
    school_panel = build_school_level_panel(df, value_col=TARGET)
    school_delta = school_panel.pivot(index="ecole_id", columns="annee", values="score_moyen")
    school_delta["delta_2017_2023"] = school_delta[2023] - school_delta[2017]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(school_delta["delta_2017_2023"], bins=20, edgecolor="black", color="#4C72B0")
    ax.set_title("Distribution des variations école (score moyen 2023 - 2017)")
    ax.set_xlabel("Variation de score (points)")
    ax.set_ylabel("Nombre d'écoles")
    fig.tight_layout()
    path = fig_dir / "08_distribution_delta_ecoles.png"
    fig.savefig(path)
    plt.close(fig)
    _check_output(path, "08_distribution_delta_ecoles")

    print("Figures longitudinales (08) régénérées.")


def main() -> None:
    try:
        df = load_processed_dataset(DATASET_NAME)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Impossible de charger le jeu de données processed '{DATASET_NAME}' : {exc}"
        ) from exc

    fig_dir = figures_output_dir()

    try:
        generate_descriptive_figures(df, fig_dir)
        generate_modeling_figures(df, fig_dir)
        generate_specialized_figures(df, fig_dir)
        generate_longitudinal_figures(df, fig_dir)
    except Exception as exc:  # noqa: BLE001 - on veut un message explicite en cas d'échec
        raise RuntimeError(f"Échec de la génération des figures : {exc}") from exc

    print("Toutes les figures ont été générées et vérifiées avec succès.")


if __name__ == "__main__":
    main()
