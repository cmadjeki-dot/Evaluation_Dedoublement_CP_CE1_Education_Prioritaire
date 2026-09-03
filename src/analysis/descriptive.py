from __future__ import annotations

"""Fonctions réutilisables d'analyse descriptive.

Ce module fournit des fonctions génériques (effectifs, tendance centrale,
dispersion, quantiles, comparaisons de groupes, tableaux croisés, intervalles
de confiance) réutilisées par `notebooks/05_analyse_descriptive.ipynb`.

Aucune fonction ne produit d'interprétation causale : ce module se limite à la
description statistique. Les décisions d'interprétation restent documentées
dans le notebook.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.paths import FIGURES_DIR, TABLES_DIR, ensure_directory


@dataclass
class ConfidenceInterval:
    """Intervalle de confiance pour une moyenne (calculé via la loi de Student)."""

    moyenne: float
    borne_basse: float
    borne_haute: float
    niveau_confiance: float
    effectif: int
    ecart_type: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "moyenne": self.moyenne,
            "borne_basse": self.borne_basse,
            "borne_haute": self.borne_haute,
            "niveau_confiance": self.niveau_confiance,
            "effectif": self.effectif,
            "ecart_type": self.ecart_type,
        }


def summary_statistics(df: pd.DataFrame, column: str) -> pd.Series:
    """Retourne les statistiques descriptives usuelles d'une variable numérique.

    Inclut : effectif, moyenne, médiane, écart-type, min, max, quantiles 25/75,
    coefficient de variation et asymétrie (skewness).
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"La variable '{column}' ne contient aucune valeur numérique exploitable.")

    stats_dict = {
        "effectif": int(series.count()),
        "moyenne": float(series.mean()),
        "mediane": float(series.median()),
        "ecart_type": float(series.std(ddof=1)),
        "minimum": float(series.min()),
        "quantile_25": float(series.quantile(0.25)),
        "quantile_75": float(series.quantile(0.75)),
        "maximum": float(series.max()),
        "coefficient_variation": float(series.std(ddof=1) / series.mean()) if series.mean() != 0 else float("nan"),
        "asymetrie_skewness": float(series.skew()),
    }
    return pd.Series(stats_dict, name=column)


def confidence_interval_mean(
    df: pd.DataFrame,
    column: str,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """Calcule l'intervalle de confiance de la moyenne d'une variable (loi de Student).

    Approprié lorsque l'effectif est suffisant (>= 30) ou lorsque la variable
    est raisonnablement proche d'une distribution normale ; à interpréter avec
    prudence sinon.
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    n = int(series.count())
    if n < 2:
        raise ValueError(f"Effectif insuffisant ({n}) pour calculer un intervalle de confiance sur '{column}'.")

    mean = float(series.mean())
    sem = float(series.std(ddof=1) / np.sqrt(n))
    alpha = 1 - confidence
    t_critique = stats.t.ppf(1 - alpha / 2, df=n - 1)
    marge = t_critique * sem

    return ConfidenceInterval(
        moyenne=mean,
        borne_basse=mean - marge,
        borne_haute=mean + marge,
        niveau_confiance=confidence,
        effectif=n,
        ecart_type=float(series.std(ddof=1)),
    )


def group_comparison_table(
    df: pd.DataFrame,
    target: str,
    group_column: str,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Compare la variable cible entre modalités d'une variable de groupe.

    Retourne, par modalité : effectif, moyenne, médiane, écart-type,
    quantiles 25/75, et intervalle de confiance de la moyenne.
    """
    rows = []
    for modalite, sous_groupe in df.groupby(group_column, observed=True):
        series = pd.to_numeric(sous_groupe[target], errors="coerce").dropna()
        n = int(series.count())
        if n < 2:
            ic_basse, ic_haute = float("nan"), float("nan")
        else:
            ic = confidence_interval_mean(sous_groupe, target, confidence=confidence)
            ic_basse, ic_haute = ic.borne_basse, ic.borne_haute
        rows.append(
            {
                group_column: modalite,
                "effectif": n,
                "moyenne": float(series.mean()) if n > 0 else float("nan"),
                "mediane": float(series.median()) if n > 0 else float("nan"),
                "ecart_type": float(series.std(ddof=1)) if n > 1 else float("nan"),
                "quantile_25": float(series.quantile(0.25)) if n > 0 else float("nan"),
                "quantile_75": float(series.quantile(0.75)) if n > 0 else float("nan"),
                f"ic_{int(confidence * 100)}_basse": ic_basse,
                f"ic_{int(confidence * 100)}_haute": ic_haute,
            }
        )
    table = pd.DataFrame(rows).sort_values("moyenne", ascending=False).reset_index(drop=True)
    return table


def crosstab_summary(
    df: pd.DataFrame,
    target: str,
    row_variable: str,
    column_variable: str,
    aggregation: str = "mean",
) -> pd.DataFrame:
    """Tableau croisé de la variable cible selon deux variables catégorielles.

    aggregation : 'mean', 'median', ou 'count'.
    """
    if aggregation not in {"mean", "median", "count"}:
        raise ValueError("aggregation doit être 'mean', 'median' ou 'count'.")

    pivot = pd.pivot_table(
        df,
        values=target,
        index=row_variable,
        columns=column_variable,
        aggfunc=aggregation,
        observed=True,
    )
    return pivot.round(3)


def group_difference_test(
    df: pd.DataFrame,
    target: str,
    group_column: str,
    group_a,
    group_b,
) -> dict[str, float]:
    """Test t de Welch comparant la moyenne de la variable cible entre deux modalités.

    Ne permet aucune interprétation causale : mesure uniquement si la différence
    de moyenne observée entre deux groupes est statistiquement significative,
    toutes choses égales par ailleurs non contrôlées ici.
    """
    serie_a = pd.to_numeric(df.loc[df[group_column] == group_a, target], errors="coerce").dropna()
    serie_b = pd.to_numeric(df.loc[df[group_column] == group_b, target], errors="coerce").dropna()

    if len(serie_a) < 2 or len(serie_b) < 2:
        raise ValueError("Effectif insuffisant dans au moins un des deux groupes pour réaliser le test.")

    stat_t, p_value = stats.ttest_ind(serie_a, serie_b, equal_var=False)
    return {
        "groupe_a": str(group_a),
        "groupe_b": str(group_b),
        "moyenne_a": float(serie_a.mean()),
        "moyenne_b": float(serie_b.mean()),
        "difference_moyennes": float(serie_a.mean() - serie_b.mean()),
        "statistique_t": float(stat_t),
        "p_value": float(p_value),
        "n_a": int(len(serie_a)),
        "n_b": int(len(serie_b)),
    }


def distribution_table(df: pd.DataFrame, column: str, bins: int = 10) -> pd.DataFrame:
    """Table de distribution (histogramme discrétisé) d'une variable numérique."""
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    counts, edges = np.histogram(series, bins=bins)
    table = pd.DataFrame(
        {
            "borne_basse": edges[:-1].round(2),
            "borne_haute": edges[1:].round(2),
            "effectif": counts,
            "pourcentage": (100 * counts / counts.sum()).round(2),
        }
    )
    return table


def save_table(table: pd.DataFrame, name: str) -> Path:
    """Sauvegarde un tableau au format CSV dans outputs/tables/."""
    ensure_directory(TABLES_DIR)
    path = TABLES_DIR / f"{name}.csv"
    table.to_csv(path, index=table.index.name is not None)
    return path


def figures_output_dir() -> Path:
    ensure_directory(FIGURES_DIR)
    return FIGURES_DIR


__all__ = [
    "ConfidenceInterval",
    "summary_statistics",
    "confidence_interval_mean",
    "group_comparison_table",
    "crosstab_summary",
    "group_difference_test",
    "distribution_table",
    "save_table",
    "figures_output_dir",
]
