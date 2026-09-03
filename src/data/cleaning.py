from __future__ import annotations

"""Fonctions réutilisables de nettoyage et de traitement des données.

Contrairement à `src/quality`, qui se contente de détecter des problèmes,
ce module applique des transformations — mais chaque fonction retourne
systématiquement une trace explicite (règle appliquée, nombre de lignes
concernées, justification) afin qu'aucune transformation ne reste silencieuse.

Aucune fonction ne choisit automatiquement une stratégie d'imputation par
défaut : la stratégie doit être choisie explicitement par l'appelant (notebook
de nettoyage), au cas par cas, variable par variable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.utils.paths import PROJECT_ROOT, ensure_directory

INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

IMPUTATION_STRATEGIES = (
    "suppression",
    "moyenne",
    "mediane",
    "mode",
    "categorie_inconnu",
    "imputation_par_groupe",
    "knn",
    "mice",
    "aucune_action",
)


@dataclass
class TransformationStep:
    """Trace d'une transformation unique appliquée à la donnée."""

    variable: str | None
    action: str
    strategie: str
    justification: str
    n_lignes_avant: int
    n_lignes_apres: int
    n_valeurs_modifiees: int
    details: dict[str, Any] = field(default_factory=dict)
    horodatage: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "action": self.action,
            "strategie": self.strategie,
            "justification": self.justification,
            "n_lignes_avant": self.n_lignes_avant,
            "n_lignes_apres": self.n_lignes_apres,
            "n_valeurs_modifiees": self.n_valeurs_modifiees,
            "details": self.details,
            "horodatage": self.horodatage,
        }


@dataclass
class TransformationJournal:
    """Journal cumulatif de toutes les transformations appliquées à un jeu de données."""

    dataset_name: str
    steps: list[TransformationStep] = field(default_factory=list)

    def log(self, step: TransformationStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "n_steps": len(self.steps),
            "steps": [step.to_dict() for step in self.steps],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Journal des transformations — {self.dataset_name}",
            "",
            f"Nombre d'étapes appliquées : {len(self.steps)}",
            "",
        ]
        for i, step in enumerate(self.steps, start=1):
            variable_txt = f" (variable : {step.variable})" if step.variable else ""
            lines.append(f"## Étape {i} — {step.action}{variable_txt}")
            lines.append("")
            lines.append(f"- Stratégie retenue : **{step.strategie}**")
            lines.append(f"- Justification : {step.justification}")
            lines.append(f"- Lignes avant : {step.n_lignes_avant} — Lignes après : {step.n_lignes_apres}")
            lines.append(f"- Valeurs modifiées / concernées : {step.n_valeurs_modifiees}")
            if step.details:
                for key, value in step.details.items():
                    lines.append(f"    - {key} : {value}")
            lines.append("")
        return "\n".join(lines)

    def save(self, output_dir: Path, base_name: str = "journal_transformations") -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"{base_name}.md"
        json_path = output_dir / f"{base_name}.json"

        import json

        md_path.write_text(self.to_markdown(), encoding="utf-8")
        json_path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"markdown": md_path, "json": json_path}


def remove_duplicate_rows(df: pd.DataFrame, journal: TransformationJournal | None = None) -> pd.DataFrame:
    """Supprime les lignes strictement dupliquées (garde la première occurrence)."""
    n_before = len(df)
    n_duplicates = int(df.duplicated(keep="first").sum())
    cleaned = df.drop_duplicates(keep="first").reset_index(drop=True)
    n_after = len(cleaned)

    if journal is not None:
        journal.log(
            TransformationStep(
                variable=None,
                action="suppression_doublons",
                strategie="suppression" if n_duplicates > 0 else "aucune_action",
                justification=(
                    "Suppression des lignes strictement identiques (conservation de la première occurrence), "
                    "car un doublon exact ne peut apporter d'information supplémentaire et fausserait les "
                    "statistiques descriptives et les modèles."
                    if n_duplicates > 0
                    else "Aucun doublon strict détecté ; aucune suppression nécessaire."
                ),
                n_lignes_avant=n_before,
                n_lignes_apres=n_after,
                n_valeurs_modifiees=n_duplicates,
            )
        )
    return cleaned


def fix_column_types(
    df: pd.DataFrame,
    type_map: dict[str, str],
    journal: TransformationJournal | None = None,
) -> pd.DataFrame:
    """Force les types de colonnes vers un type cible (int, float, string, category).

    `type_map` associe un nom de colonne à un type pandas cible ("int64", "float64",
    "string", "category", ...). Les colonnes déjà conformes ne sont pas modifiées.
    """
    result = df.copy()
    n_before = len(result)

    for column, target_type in type_map.items():
        if column not in result.columns:
            continue
        current_dtype = str(result[column].dtype)
        if current_dtype == target_type:
            continue

        n_modifiees = int(len(result))
        try:
            if target_type in ("int64", "Int64"):
                result[column] = pd.to_numeric(result[column], errors="coerce").round().astype(target_type)
            elif target_type == "float64":
                result[column] = pd.to_numeric(result[column], errors="coerce").astype("float64")
            elif target_type == "string":
                result[column] = result[column].astype("string")
            elif target_type == "category":
                result[column] = result[column].astype("category")
            else:
                result[column] = result[column].astype(target_type)
        except (ValueError, TypeError):
            continue

        if journal is not None:
            journal.log(
                TransformationStep(
                    variable=column,
                    action="correction_type",
                    strategie="conversion_type",
                    justification=(
                        f"Le type observé ('{current_dtype}') ne correspondait pas au type attendu "
                        f"('{target_type}') pour cette variable ; conversion appliquée pour garantir la "
                        "cohérence des traitements statistiques ultérieurs."
                    ),
                    n_lignes_avant=n_before,
                    n_lignes_apres=len(result),
                    n_valeurs_modifiees=n_modifiees,
                    details={"type_avant": current_dtype, "type_apres": target_type},
                )
            )
    return result


def harmonize_categories(
    df: pd.DataFrame,
    column: str,
    mapping: dict[str, str],
    journal: TransformationJournal | None = None,
) -> pd.DataFrame:
    """Harmonise les modalités d'une variable catégorielle selon un dictionnaire de correspondance."""
    if column not in df.columns:
        return df

    result = df.copy()
    n_before = len(result)
    original_values = result[column].astype(str)
    mask_changed = original_values.isin(mapping.keys())
    n_changed = int(mask_changed.sum())

    if n_changed > 0:
        result[column] = original_values.replace(mapping)

    if journal is not None:
        journal.log(
            TransformationStep(
                variable=column,
                action="harmonisation_categories",
                strategie="mapping_explicite",
                justification=(
                    "Les modalités observées ont été harmonisées vers une nomenclature unique afin d'éviter "
                    "que des variantes d'écriture (casse, orthographe, abréviations) ne soient traitées comme "
                    "des catégories distinctes."
                    if n_changed > 0
                    else "Aucune modalité à harmoniser n'a été trouvée pour cette variable."
                ),
                n_lignes_avant=n_before,
                n_lignes_apres=len(result),
                n_valeurs_modifiees=n_changed,
                details={"mapping_applique": mapping},
            )
        )
    return result


def handle_impossible_values(
    df: pd.DataFrame,
    column: str,
    valid_range: tuple[float, float],
    strategy: str = "marquer_manquant",
    journal: TransformationJournal | None = None,
) -> pd.DataFrame:
    """Traite les valeurs numériques impossibles (hors bornes plausibles).

    strategy:
        - "marquer_manquant" : remplace la valeur impossible par NaN (pour traitement ultérieur des NA) ;
        - "supprimer_lignes" : supprime les lignes concernées.
    """
    if column not in df.columns:
        return df

    result = df.copy()
    n_before = len(result)
    series = pd.to_numeric(result[column], errors="coerce")
    low, high = valid_range
    mask_impossible = (series < low) | (series > high)
    n_affected = int(mask_impossible.sum())

    if n_affected > 0:
        if strategy == "supprimer_lignes":
            result = result.loc[~mask_impossible].reset_index(drop=True)
        else:
            result.loc[mask_impossible, column] = np.nan

    if journal is not None:
        journal.log(
            TransformationStep(
                variable=column,
                action="traitement_valeurs_impossibles",
                strategie=strategy if n_affected > 0 else "aucune_action",
                justification=(
                    f"Valeurs hors des bornes plausibles [{low}, {high}] détectées ; ces valeurs ne peuvent "
                    "correspondre à une réalité métier et sont donc marquées comme manquantes plutôt que "
                    "conservées telles quelles, afin de ne pas biaiser les statistiques."
                    if n_affected > 0
                    else f"Aucune valeur hors des bornes plausibles [{low}, {high}] détectée pour cette variable."
                ),
                n_lignes_avant=n_before,
                n_lignes_apres=len(result),
                n_valeurs_modifiees=n_affected,
                details={"borne_min": low, "borne_max": high},
            )
        )
    return result


def analyze_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un tableau du nombre et du pourcentage de valeurs manquantes par variable."""
    n_rows = max(len(df), 1)
    n_missing = df.isna().sum()
    pct_missing = (100 * n_missing / n_rows).round(3)
    table = pd.DataFrame({"n_manquants": n_missing, "pourcentage_manquant": pct_missing})
    return table.sort_values("pourcentage_manquant", ascending=False)


def impute_missing_values(
    df: pd.DataFrame,
    column: str,
    strategy: str,
    justification: str,
    group_columns: list[str] | None = None,
    knn_columns: list[str] | None = None,
    n_neighbors: int = 5,
    journal: TransformationJournal | None = None,
) -> pd.DataFrame:
    """Impute ou traite les valeurs manquantes d'une variable selon une stratégie choisie explicitement.

    strategy doit être l'une de : IMPUTATION_STRATEGIES.
    La stratégie n'est jamais choisie automatiquement par cette fonction : elle doit être
    décidée et justifiée par l'appelant, variable par variable.
    """
    if strategy not in IMPUTATION_STRATEGIES:
        raise ValueError(f"Stratégie inconnue : {strategy}. Attendu l'une de {IMPUTATION_STRATEGIES}.")
    if column not in df.columns:
        return df

    result = df.copy()
    n_before = len(result)
    n_missing_before = int(result[column].isna().sum())

    if n_missing_before == 0:
        if journal is not None:
            journal.log(
                TransformationStep(
                    variable=column,
                    action="traitement_valeurs_manquantes",
                    strategie="aucune_action",
                    justification="Aucune valeur manquante détectée pour cette variable ; aucune imputation nécessaire.",
                    n_lignes_avant=n_before,
                    n_lignes_apres=n_before,
                    n_valeurs_modifiees=0,
                )
            )
        return result

    if strategy == "suppression":
        result = result.loc[result[column].notna()].reset_index(drop=True)
    elif strategy == "moyenne":
        value = result[column].mean()
        result[column] = result[column].fillna(value)
    elif strategy == "mediane":
        value = result[column].median()
        result[column] = result[column].fillna(value)
    elif strategy == "mode":
        mode_values = result[column].mode(dropna=True)
        value = mode_values.iloc[0] if not mode_values.empty else None
        result[column] = result[column].fillna(value)
    elif strategy == "categorie_inconnu":
        if isinstance(result[column].dtype, pd.CategoricalDtype) and "Inconnu" not in result[column].cat.categories:
            result[column] = result[column].cat.add_categories(["Inconnu"])
        result[column] = result[column].fillna("Inconnu")
    elif strategy == "imputation_par_groupe":
        if not group_columns:
            raise ValueError("group_columns est requis pour la stratégie 'imputation_par_groupe'.")
        result[column] = result.groupby(group_columns)[column].transform(lambda s: s.fillna(s.median()))
        remaining_na = int(result[column].isna().sum())
        if remaining_na > 0:
            result[column] = result[column].fillna(result[column].median())
    elif strategy == "knn":
        from sklearn.impute import KNNImputer

        feature_columns = knn_columns or [c for c in result.select_dtypes(include=[np.number]).columns]
        if column not in feature_columns:
            feature_columns = [column] + feature_columns
        imputer = KNNImputer(n_neighbors=n_neighbors)
        imputed_array = imputer.fit_transform(result[feature_columns])
        result[feature_columns] = imputed_array
    elif strategy == "mice":
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer

        feature_columns = knn_columns or [c for c in result.select_dtypes(include=[np.number]).columns]
        if column not in feature_columns:
            feature_columns = [column] + feature_columns
        imputer = IterativeImputer(random_state=42, max_iter=15)
        imputed_array = imputer.fit_transform(result[feature_columns])
        result[feature_columns] = imputed_array
    elif strategy == "aucune_action":
        pass

    n_after = len(result)
    n_missing_after = int(result[column].isna().sum()) if column in result.columns else 0
    n_traites = n_missing_before - n_missing_after if strategy != "suppression" else (n_before - n_after)

    if journal is not None:
        journal.log(
            TransformationStep(
                variable=column,
                action="traitement_valeurs_manquantes",
                strategie=strategy,
                justification=justification,
                n_lignes_avant=n_before,
                n_lignes_apres=n_after,
                n_valeurs_modifiees=n_traites,
                details={"n_manquants_avant": n_missing_before, "n_manquants_apres": n_missing_after},
            )
        )
    return result


def compare_before_after(
    before: pd.DataFrame,
    after: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Compare les statistiques descriptives principales avant/après transformation."""
    target_columns = columns or [c for c in after.select_dtypes(include=[np.number]).columns]
    rows = []
    for column in target_columns:
        if column not in before.columns or column not in after.columns:
            continue
        before_series = pd.to_numeric(before[column], errors="coerce")
        after_series = pd.to_numeric(after[column], errors="coerce")
        rows.append(
            {
                "variable": column,
                "n_avant": int(before_series.notna().sum()),
                "n_apres": int(after_series.notna().sum()),
                "moyenne_avant": round(float(before_series.mean()), 3) if before_series.notna().any() else None,
                "moyenne_apres": round(float(after_series.mean()), 3) if after_series.notna().any() else None,
                "mediane_avant": round(float(before_series.median()), 3) if before_series.notna().any() else None,
                "mediane_apres": round(float(after_series.median()), 3) if after_series.notna().any() else None,
                "ecart_type_avant": round(float(before_series.std()), 3) if before_series.notna().any() else None,
                "ecart_type_apres": round(float(after_series.std()), 3) if after_series.notna().any() else None,
                "n_manquants_avant": int(before_series.isna().sum()),
                "n_manquants_apres": int(after_series.isna().sum()),
            }
        )
    return pd.DataFrame(rows)


def save_interim_dataset(df: pd.DataFrame, name: str) -> Path:
    """Sauvegarde un jeu de données intermédiaire dans data/interim/[name]_clean.csv."""
    ensure_directory(INTERIM_DIR)
    path = INTERIM_DIR / f"{name}_clean.csv"
    df.to_csv(path, index=False)
    return path


def save_processed_dataset(df: pd.DataFrame, name: str) -> Path:
    """Sauvegarde un jeu de données prêt pour l'analyse dans data/processed/[name]_analysis_ready.csv."""
    ensure_directory(PROCESSED_DIR)
    path = PROCESSED_DIR / f"{name}_analysis_ready.csv"
    df.to_csv(path, index=False)
    return path


def load_processed_dataset(name: str) -> pd.DataFrame:
    """Charge un jeu de données prêt pour l'analyse depuis data/processed/[name]_analysis_ready.csv."""
    path = PROCESSED_DIR / f"{name}_analysis_ready.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Jeu de données traité introuvable : {path}. "
            "Exécutez d'abord notebooks/04_nettoyage.ipynb."
        )
    return pd.read_csv(path)


def load_interim_dataset(name: str) -> pd.DataFrame:
    """Charge un jeu de données intermédiaire depuis data/interim/[name]_clean.csv."""
    path = INTERIM_DIR / f"{name}_clean.csv"
    if not path.exists():
        raise FileNotFoundError(f"Jeu de données intermédiaire introuvable : {path}.")
    return pd.read_csv(path)


__all__ = [
    "IMPUTATION_STRATEGIES",
    "TransformationStep",
    "TransformationJournal",
    "remove_duplicate_rows",
    "fix_column_types",
    "harmonize_categories",
    "handle_impossible_values",
    "analyze_missing_values",
    "impute_missing_values",
    "compare_before_after",
    "save_interim_dataset",
    "save_processed_dataset",
    "load_processed_dataset",
    "load_interim_dataset",
    "INTERIM_DIR",
    "PROCESSED_DIR",
]
