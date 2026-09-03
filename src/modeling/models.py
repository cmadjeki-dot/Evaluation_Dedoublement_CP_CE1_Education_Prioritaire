"""Fonctions de modélisation statistique réutilisables.

Choix méthodologique documenté (voir notebooks/06_modelisation.ipynb pour la justification complète) :

- La variable cible (`variable_cible`) est continue (échelle ~0-100), sans borne stricte imposée par
  un processus de comptage : une régression linéaire est donc adaptée sur le plan du type de variable.
- La structure des données est hiérarchique et répétée : 150 écoles, chacune observée exactement 35 fois
  (7 années × 5 niveaux), nichées dans 10 départements et 6 académies. Les observations d'une même école
  ne sont pas indépendantes (corrélation intra-école).
- Deux approches sont donc comparées, sans en imposer une seule a priori :
    1. OLS avec écarts-types groupés ("cluster-robust") au niveau école, qui corrige l'inférence sans
       modéliser explicitement la hiérarchie ;
    2. Un modèle linéaire à effets mixtes (écoles en effet aléatoire), qui modélise explicitement la
       corrélation intra-école et permet de décomposer la variance inter/intra-école.
- Le modèle retenu est justifié dans le notebook à partir des diagnostics (résidus, CIV intra-classe),
  pas choisi par défaut.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from src.utils.paths import MODELS_DIR, ensure_directory


@dataclass
class ModelResult:
    """Conteneur normalisé pour présenter un résultat de modélisation."""

    nom_modele: str
    formule: str
    n_observations: int
    coefficients: pd.DataFrame
    metriques: dict
    diagnostics: dict = field(default_factory=dict)
    horodatage: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "nom_modele": self.nom_modele,
            "formule": self.formule,
            "n_observations": self.n_observations,
            "coefficients": self.coefficients.reset_index().to_dict(orient="records"),
            "metriques": self.metriques,
            "diagnostics": self.diagnostics,
            "horodatage": self.horodatage,
        }


def prepare_model_frame(
    df: pd.DataFrame,
    target: str,
    explanatory: list[str],
    categorical: list[str] | None = None,
    group_column: str | None = None,
) -> pd.DataFrame:
    """Sélectionne et encode les variables nécessaires à la modélisation.

    Les variables catégorielles listées dans `categorical` sont converties en type `category`
    (l'encodage one-hot / effets de référence est ensuite géré par la formule R-like de statsmodels).
    Aucune valeur manquante n'est autorisée dans les colonnes utilisées (le jeu de données traité
    ne devrait plus en contenir ; une erreur explicite est levée sinon plutôt qu'une suppression silencieuse).
    """
    categorical = categorical or []
    columns = [target] + list(explanatory)
    if group_column and group_column not in columns:
        columns.append(group_column)
    frame = df[columns].copy()

    n_manquants = int(frame.isna().sum().sum())
    if n_manquants > 0:
        raise ValueError(
            f"{n_manquants} valeurs manquantes détectées dans les colonnes du modèle. "
            "Le jeu de données traité ne devrait pas en contenir : vérifier la provenance."
        )

    for column in categorical:
        frame[column] = frame[column].astype("category")

    return frame


def fit_ols(
    df: pd.DataFrame,
    target: str,
    explanatory: list[str],
    categorical: list[str] | None = None,
    cluster_column: str | None = None,
) -> tuple["sm.regression.linear_model.RegressionResultsWrapper", str]:
    """Ajuste une régression linéaire (OLS), avec écarts-types groupés (cluster-robust) si demandé.

    Retourne le résultat statsmodels ainsi que la formule utilisée (pour traçabilité).
    """
    categorical = categorical or []
    terms = [f"C({c})" if c in categorical else c for c in explanatory]
    formule = f"{target} ~ " + " + ".join(terms)

    modele = smf.ols(formule, data=df)
    if cluster_column:
        resultat = modele.fit(
            cov_type="cluster", cov_kwds={"groups": df[cluster_column]}
        )
    else:
        resultat = modele.fit()
    return resultat, formule


def fit_mixed_effects(
    df: pd.DataFrame,
    target: str,
    explanatory: list[str],
    group_column: str,
    categorical: list[str] | None = None,
) -> tuple["sm.regression.mixed_linear_model.MixedLMResultsWrapper", str]:
    """Ajuste un modèle linéaire à effets mixtes (intercept aléatoire par `group_column`).

    Adapté à une structure hiérarchique (observations répétées au sein d'une même unité, ici l'école).
    """
    categorical = categorical or []
    terms = [f"C({c})" if c in categorical else c for c in explanatory]
    formule = f"{target} ~ " + " + ".join(terms)

    modele = smf.mixedlm(formule, data=df, groups=df[group_column])
    resultat = modele.fit(reml=True)
    return resultat, formule


def intraclass_correlation(mixed_result) -> float:
    """Calcule le coefficient de corrélation intra-classe (ICC) d'un modèle à effets mixtes.

    ICC = variance inter-groupe / (variance inter-groupe + variance résiduelle).
    Un ICC élevé confirme la pertinence de modéliser la structure hiérarchique.
    """
    variance_groupe = float(mixed_result.cov_re.iloc[0, 0])
    variance_residuelle = float(mixed_result.scale)
    return variance_groupe / (variance_groupe + variance_residuelle)


def ols_coefficients_table(result) -> pd.DataFrame:
    """Construit un tableau de coefficients avec IC 95% à partir d'un résultat OLS."""
    conf_int = result.conf_int()
    conf_int.columns = ["ic_95_basse", "ic_95_haute"]
    table = pd.DataFrame(
        {
            "coefficient": result.params,
            "erreur_standard": result.bse,
            "statistique_t": result.tvalues,
            "p_value": result.pvalues,
        }
    ).join(conf_int)
    return table


def mixed_effects_coefficients_table(result) -> pd.DataFrame:
    """Construit un tableau de coefficients (effets fixes) pour un modèle à effets mixtes."""
    conf_int = result.conf_int()
    conf_int.columns = ["ic_95_basse", "ic_95_haute"]
    table = pd.DataFrame(
        {
            "coefficient": result.params,
            "erreur_standard": result.bse,
            "statistique_z": result.tvalues,
            "p_value": result.pvalues,
        }
    ).join(conf_int)
    return table


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """Métriques de qualité d'ajustement pour un modèle de régression."""
    residus = y_true.to_numpy() - y_pred
    sse = float(np.sum(residus**2))
    sst = float(np.sum((y_true.to_numpy() - y_true.mean()) ** 2))
    r2 = 1 - sse / sst if sst > 0 else float("nan")
    rmse = float(np.sqrt(np.mean(residus**2)))
    mae = float(np.mean(np.abs(residus)))
    return {"r2": r2, "rmse": rmse, "mae": mae, "n": int(len(y_true))}


def save_model(result, name: str) -> Path:
    """Sauvegarde un modèle statsmodels ajusté dans outputs/models/[name].pickle."""
    ensure_directory(MODELS_DIR)
    path = MODELS_DIR / f"{name}.pickle"
    result.save(str(path))
    return path


def save_model_summary(model_result: ModelResult, name: str) -> dict[str, Path]:
    """Sauvegarde un résumé structuré (JSON) et lisible (texte) d'un ModelResult."""
    ensure_directory(MODELS_DIR)
    json_path = MODELS_DIR / f"{name}_resume.json"
    txt_path = MODELS_DIR / f"{name}_resume.txt"

    with open(json_path, "w", encoding="utf-8") as fichier:
        json.dump(model_result.to_dict(), fichier, ensure_ascii=False, indent=2)

    with open(txt_path, "w", encoding="utf-8") as fichier:
        fichier.write(f"Modèle : {model_result.nom_modele}\n")
        fichier.write(f"Formule : {model_result.formule}\n")
        fichier.write(f"N observations : {model_result.n_observations}\n\n")
        fichier.write("Coefficients :\n")
        fichier.write(model_result.coefficients.to_string())
        fichier.write("\n\nMétriques :\n")
        for cle, valeur in model_result.metriques.items():
            fichier.write(f"  {cle} : {valeur}\n")

    return {"json": json_path, "txt": txt_path}


__all__ = [
    "ModelResult",
    "prepare_model_frame",
    "fit_ols",
    "fit_mixed_effects",
    "intraclass_correlation",
    "ols_coefficients_table",
    "mixed_effects_coefficients_table",
    "regression_metrics",
    "save_model",
    "save_model_summary",
]
