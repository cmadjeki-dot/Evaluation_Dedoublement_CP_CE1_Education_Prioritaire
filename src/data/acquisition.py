from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.paths import DATA_DIR, ensure_directory

RAW_DATASET_NAME = "donnees_brutes_education_prioritaire.csv"
RAW_DATA_DIR = DATA_DIR

DATA_SOURCE_DESCRIPTION = {
    "provenance": (
        "Données de référence issues de la logique Open Data DEPP autour de la taille des classes, "
        "des évaluations CP/CE1/CM1/CM2/6e et des indicateurs territoriaux."
    ),
    "mode": "simulation reproductible si aucune source locale n'est fournie",
    "objectif": "Conserver une copie brute immuable dans data/raw avant tout nettoyage ou analyse",
    "url_reference": (
        "https://www.education.gouv.fr/depp/taille-des-classes-du-premier-degre-dans-le-secteur-public-"
        "la-baisse-s-observe-au-dela-des-classes-12263"
    ),
}


@dataclass(frozen=True)
class DataAcquisitionResult:
    dataframe: pd.DataFrame
    path: Path
    metadata: dict[str, Any]


def build_synthetic_open_data() -> pd.DataFrame:
    """Build a reproducible synthetic dataset that mirrors the structure of the DEPP project."""
    rng = np.random.default_rng(42)
    years = [2017, 2018, 2019, 2020, 2021, 2022, 2023]
    academies = ["Paris", "Lyon", "Grenoble", "Bordeaux", "Nantes", "Lille"]
    departments = [
        "Paris",
        "Rhône",
        "Nord",
        "Gironde",
        "Loire-Atlantique",
        "Bas-Rhin",
        "Bouches-du-Rhône",
        "Hérault",
        "Puy-de-Dôme",
        "Moselle",
    ]
    levels = ["CP", "CE1", "CM1", "CM2", "6e"]
    rep_statuses = ["Hors EP", "REP", "REP+"]

    rows: list[dict[str, Any]] = []

    for year in years:
        for school_id in range(1, 151):
            rep_status = rng.choice(rep_statuses, p=[0.56, 0.28, 0.16])
            academy = academies[(school_id + year) % len(academies)]
            department = departments[(school_id + year) % len(departments)]
            effectif_ecole = int(round(18 + rng.normal(0, 6) + (0 if rep_status == "Hors EP" else 4)))
            effectif_ecole = max(10, min(80, effectif_ecole))
            nombre_classes = max(2, int(round(effectif_ecole / (18 + rng.random() * 7))))
            taille_classe = max(12.0, min(30.0, 18 + rng.normal(0, 4.5) + (0 if rep_status == "Hors EP" else -3.5)))
            taille_moyenne_classe = round(float(taille_classe), 2)
            dedoublement = int(rep_status in {"REP", "REP+"} and taille_moyenne_classe <= 18)
            ips = round(float(np.clip(rng.normal(72, 14), 40, 100)), 2)
            education_prioritaire = int(rep_status != "Hors EP")

            for niveau in levels:
                base_score = {"CP": 60, "CE1": 64, "CM1": 68, "CM2": 71, "6e": 74}[niveau]
                rep_bonus = {"Hors EP": 8, "REP": -2, "REP+": -6}[rep_status]
                level_bonus = {"CP": 1, "CE1": 4, "CM1": 7, "CM2": 9, "6e": 12}[niveau]
                exposure_gain = 8 if dedoublement and niveau in {"CP", "CE1"} else 0
                year_trend = (year - 2017) * 0.8
                size_penalty = max(0.0, (taille_moyenne_classe - 18) * 0.9)
                score_francais = (
                    base_score + rep_bonus + level_bonus + exposure_gain
                    + year_trend - size_penalty + rng.normal(0, 4.5)
                )
                score_mathematiques = score_francais - 2 + rng.normal(0, 4.0)
                score_francais = float(np.clip(score_francais, 0, 100))
                score_mathematiques = float(np.clip(score_mathematiques, 0, 100))
                score_global = round(float(np.clip((score_francais + score_mathematiques) / 2, 0, 100)), 2)
                taux_maitrise_francais = float(np.clip(0.7 * score_francais + 18 + rng.normal(0, 4), 0, 100))
                taux_maitrise_mathematiques = float(np.clip(0.68 * score_mathematiques + 18 + rng.normal(0, 4), 0, 100))

                rows.append(
                    {
                        "annee": int(year),
                        "ecole_id": int(school_id),
                        "academie": academy,
                        "departement": department,
                        "niveau": niveau,
                        "statut": rep_status,
                        "rep": int(rep_status == "REP"),
                        "rep_plus": int(rep_status == "REP+"),
                        "education_prioritaire": education_prioritaire,
                        "effectif_eleves": int(effectif_ecole),
                        "nombre_classes": int(nombre_classes),
                        "taille_moyenne_classe": round(float(taille_moyenne_classe), 2),
                        "dedoublement": int(dedoublement),
                        "ips": ips,
                        "score_francais": round(score_francais, 2),
                        "score_mathematiques": round(score_mathematiques, 2),
                        "score_global": score_global,
                        "taux_maitrise_francais": round(float(taux_maitrise_francais), 2),
                        "taux_maitrise_mathematiques": round(float(taux_maitrise_mathematiques), 2),
                        "variable_cible": score_global,
                        "source": "simulation_reproductible",
                        "source_url": DATA_SOURCE_DESCRIPTION["url_reference"],
                    }
                )

    df = pd.DataFrame(rows)
    df["niveau"] = pd.Categorical(df["niveau"], categories=["CP", "CE1", "CM1", "CM2", "6e"], ordered=True)
    df["statut"] = pd.Categorical(df["statut"], categories=["Hors EP", "REP", "REP+"], ordered=True)
    return df


def raw_data_path() -> Path:
    ensure_directory(RAW_DATA_DIR)
    return RAW_DATA_DIR / RAW_DATASET_NAME


def dataset_exists(path: Path | None = None) -> bool:
    target = path or raw_data_path()
    return target.exists()


def acquire_project_data(force_rebuild: bool = False, path: Path | None = None) -> DataAcquisitionResult:
    """Load existing raw data or create a reproducible synthetic dataset, then save it in data/raw."""
    target_path = path or raw_data_path()

    if force_rebuild or not target_path.exists():
        dataframe = build_synthetic_open_data()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(target_path, index=False)
        provenance = {
            "mode": "synthetic_reproducible",
            "path": str(target_path),
            "rows": int(len(dataframe)),
            "columns": list(dataframe.columns),
            "source": DATA_SOURCE_DESCRIPTION,
        }
    else:
        dataframe = pd.read_csv(target_path)
        provenance = {
            "mode": "existing_raw_data",
            "path": str(target_path),
            "rows": int(len(dataframe)),
            "columns": list(dataframe.columns),
            "source": DATA_SOURCE_DESCRIPTION,
        }

    return DataAcquisitionResult(dataframe=dataframe, path=target_path, metadata=provenance)


def load_raw_dataset(path: Path | None = None) -> DataAcquisitionResult:
    target_path = path or raw_data_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Aucune donnée brute n'a été trouvée à l'emplacement : {target_path}")
    dataframe = pd.read_csv(target_path)
    metadata = {
        "mode": "loaded_raw_data",
        "path": str(target_path),
        "rows": int(len(dataframe)),
        "columns": list(dataframe.columns),
        "source": DATA_SOURCE_DESCRIPTION,
    }
    return DataAcquisitionResult(dataframe=dataframe, path=target_path, metadata=metadata)


__all__ = [
    "DataAcquisitionResult",
    "RAW_DATASET_NAME",
    "DATA_SOURCE_DESCRIPTION",
    "build_synthetic_open_data",
    "raw_data_path",
    "dataset_exists",
    "acquire_project_data",
    "load_raw_dataset",
]
