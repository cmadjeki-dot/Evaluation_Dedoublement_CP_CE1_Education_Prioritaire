from __future__ import annotations

"""Fonctions réutilisables de contrôle qualité pour le projet.

Ce module détecte des problèmes de qualité de données sans jamais corriger
silencieusement quoi que ce soit. Chaque fonction retourne une structure de
données décrivant précisément ce qui a été détecté, afin qu'une décision de
correction explicite et tracée puisse être prise plus tard (notebook de
nettoyage).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEVERITY_CRITIQUE = "CRITIQUE"
SEVERITY_IMPORTANT = "IMPORTANT"
SEVERITY_MINEUR = "MINEUR"

EXPECTED_CATEGORIES = {
    "statut": {"Hors EP", "REP", "REP+"},
    "niveau": {"CP", "CE1", "CM1", "CM2", "6e"},
}

EXPECTED_TYPES = {
    "annee": "integer",
    "ecole_id": "integer",
    "academie": "string",
    "departement": "string",
    "niveau": "string",
    "statut": "string",
    "rep": "integer",
    "rep_plus": "integer",
    "education_prioritaire": "integer",
    "effectif_eleves": "integer",
    "nombre_classes": "integer",
    "taille_moyenne_classe": "float",
    "dedoublement": "integer",
    "ips": "float",
    "score_francais": "float",
    "score_mathematiques": "float",
    "score_global": "float",
    "taux_maitrise_francais": "float",
    "taux_maitrise_mathematiques": "float",
    "variable_cible": "float",
}

# Bornes de plausibilité métier (valeurs impossibles en dehors de ces bornes).
PLAUSIBLE_RANGES = {
    "annee": (2000, 2035),
    "effectif_eleves": (1, 500),
    "nombre_classes": (1, 30),
    "taille_moyenne_classe": (5, 45),
    "ips": (0, 160),
    "score_francais": (0, 100),
    "score_mathematiques": (0, 100),
    "score_global": (0, 100),
    "taux_maitrise_francais": (0, 100),
    "taux_maitrise_mathematiques": (0, 100),
    "variable_cible": (0, 100),
}

# Identifiant logique d'une observation : une combinaison qui devrait être unique.
NATURAL_KEY_COLUMNS = ["annee", "ecole_id", "niveau"]


@dataclass
class QualityIssue:
    """Représente un problème de qualité détecté, sans correction appliquée."""

    code: str
    severity: str
    variable: str | None
    description: str
    n_affected: int
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "variable": self.variable,
            "description": self.description,
            "n_affected": self.n_affected,
            "details": self.details,
        }


@dataclass
class QualityReport:
    """Rapport de qualité complet, agrégeant toutes les vérifications."""

    generated_at: str
    n_rows: int
    n_columns: int
    columns: list[str]
    issues: list[QualityIssue] = field(default_factory=list)

    def add(self, issue: QualityIssue) -> None:
        self.issues.append(issue)

    def issues_by_severity(self, severity: str) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == severity]

    def summary_counts(self) -> dict[str, int]:
        return {
            SEVERITY_CRITIQUE: len(self.issues_by_severity(SEVERITY_CRITIQUE)),
            SEVERITY_IMPORTANT: len(self.issues_by_severity(SEVERITY_IMPORTANT)),
            SEVERITY_MINEUR: len(self.issues_by_severity(SEVERITY_MINEUR)),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "columns": self.columns,
            "summary_counts": self.summary_counts(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def check_duplicate_rows(df: pd.DataFrame) -> QualityIssue:
    """Détecte les lignes entièrement dupliquées."""
    n_duplicates = int(df.duplicated(keep="first").sum())
    severity = SEVERITY_IMPORTANT if n_duplicates > 0 else SEVERITY_MINEUR
    return QualityIssue(
        code="DUPLICATE_ROWS",
        severity=severity,
        variable=None,
        description="Lignes strictement identiques sur l'ensemble des colonnes.",
        n_affected=n_duplicates,
        details={"pourcentage": round(100 * n_duplicates / max(len(df), 1), 3)},
    )


def check_duplicate_identifiers(df: pd.DataFrame, key_columns: list[str] | None = None) -> QualityIssue:
    """Détecte les identifiants logiques dupliqués (ex : année + école + niveau)."""
    key_columns = key_columns or NATURAL_KEY_COLUMNS
    present_columns = [c for c in key_columns if c in df.columns]
    if not present_columns:
        return QualityIssue(
            code="DUPLICATE_IDENTIFIERS",
            severity=SEVERITY_MINEUR,
            variable=None,
            description="Colonnes d'identifiant logique absentes, vérification impossible.",
            n_affected=0,
            details={"colonnes_attendues": key_columns},
        )
    n_duplicates = int(df.duplicated(subset=present_columns, keep=False).sum())
    severity = SEVERITY_CRITIQUE if n_duplicates > 0 else SEVERITY_MINEUR
    return QualityIssue(
        code="DUPLICATE_IDENTIFIERS",
        severity=severity,
        variable=", ".join(present_columns),
        description="Combinaisons d'identifiant logique (année, école, niveau) apparaissant plusieurs fois.",
        n_affected=n_duplicates,
        details={"colonnes_utilisees": present_columns},
    )


def check_missing_values(df: pd.DataFrame) -> list[QualityIssue]:
    """Détecte les valeurs manquantes par variable, avec pourcentage."""
    issues: list[QualityIssue] = []
    n_rows = max(len(df), 1)
    for column in df.columns:
        n_missing = int(df[column].isna().sum())
        if n_missing == 0:
            continue
        pct_missing = round(100 * n_missing / n_rows, 3)
        if pct_missing >= 20:
            severity = SEVERITY_CRITIQUE
        elif pct_missing >= 5:
            severity = SEVERITY_IMPORTANT
        else:
            severity = SEVERITY_MINEUR
        issues.append(
            QualityIssue(
                code="MISSING_VALUES",
                severity=severity,
                variable=column,
                description=f"Valeurs manquantes détectées sur la variable '{column}'.",
                n_affected=n_missing,
                details={"pourcentage": pct_missing},
            )
        )
    return issues


def check_type_consistency(df: pd.DataFrame, expected_types: dict[str, str] | None = None) -> list[QualityIssue]:
    """Détecte les types de colonnes incohérents avec les types attendus."""
    expected_types = expected_types or EXPECTED_TYPES
    issues: list[QualityIssue] = []

    for column, expected in expected_types.items():
        if column not in df.columns:
            continue
        series = df[column]
        actual_kind = series.dtype.kind  # i/u=int, f=float, O=object, b=bool

        is_consistent = True
        if expected == "integer" and actual_kind not in ("i", "u", "b"):
            is_consistent = False
        elif expected == "float" and actual_kind not in ("f", "i", "u"):
            is_consistent = False
        elif expected == "string" and actual_kind not in ("O", "U", "S"):
            is_consistent = False

        if not is_consistent:
            issues.append(
                QualityIssue(
                    code="TYPE_INCONSISTENCY",
                    severity=SEVERITY_IMPORTANT,
                    variable=column,
                    description=f"Type observé ({series.dtype}) incohérent avec le type attendu ({expected}).",
                    n_affected=int(len(series)),
                    details={"type_attendu": expected, "type_observe": str(series.dtype)},
                )
            )
    return issues


def check_unexpected_categories(df: pd.DataFrame, expected_categories: dict[str, set[str]] | None = None) -> list[QualityIssue]:
    """Détecte les modalités inattendues pour les variables catégorielles connues."""
    expected_categories = expected_categories or EXPECTED_CATEGORIES
    issues: list[QualityIssue] = []

    for column, allowed_values in expected_categories.items():
        if column not in df.columns:
            continue
        observed_values = set(df[column].dropna().astype(str).unique())
        unexpected = observed_values.difference(allowed_values)
        if unexpected:
            n_affected = int(df[column].astype(str).isin(unexpected).sum())
            issues.append(
                QualityIssue(
                    code="UNEXPECTED_CATEGORY",
                    severity=SEVERITY_CRITIQUE,
                    variable=column,
                    description=f"Modalités non attendues détectées sur '{column}'.",
                    n_affected=n_affected,
                    details={"modalites_inattendues": sorted(unexpected), "modalites_attendues": sorted(allowed_values)},
                )
            )
    return issues


def check_impossible_values(df: pd.DataFrame, plausible_ranges: dict[str, tuple[float, float]] | None = None) -> list[QualityIssue]:
    """Détecte les valeurs numériquement impossibles au regard de bornes métier."""
    plausible_ranges = plausible_ranges or PLAUSIBLE_RANGES
    issues: list[QualityIssue] = []

    for column, (low, high) in plausible_ranges.items():
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce")
        mask = (series < low) | (series > high)
        n_affected = int(mask.sum())
        if n_affected > 0:
            issues.append(
                QualityIssue(
                    code="IMPOSSIBLE_VALUE",
                    severity=SEVERITY_CRITIQUE,
                    variable=column,
                    description=f"Valeurs hors des bornes plausibles [{low}, {high}] pour '{column}'.",
                    n_affected=n_affected,
                    details={"borne_min": low, "borne_max": high},
                )
            )
    return issues


def check_outliers_iqr(df: pd.DataFrame, columns: list[str] | None = None, factor: float = 1.5) -> list[QualityIssue]:
    """Détecte les valeurs aberrantes par la méthode de l'écart interquartile (IQR)."""
    numeric_columns = columns or [c for c in df.select_dtypes(include=[np.number]).columns]
    issues: list[QualityIssue] = []

    for column in numeric_columns:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        mask = (series < lower_bound) | (series > upper_bound)
        n_affected = int(mask.sum())
        if n_affected > 0:
            pct = round(100 * n_affected / max(len(series), 1), 3)
            severity = SEVERITY_IMPORTANT if pct >= 1 else SEVERITY_MINEUR
            issues.append(
                QualityIssue(
                    code="OUTLIER_IQR",
                    severity=severity,
                    variable=column,
                    description=f"Valeurs aberrantes détectées par la méthode IQR sur '{column}'.",
                    n_affected=n_affected,
                    details={
                        "borne_basse": round(float(lower_bound), 3),
                        "borne_haute": round(float(upper_bound), 3),
                        "pourcentage": pct,
                    },
                )
            )
    return issues


def check_suspicious_distributions(df: pd.DataFrame, columns: list[str] | None = None) -> list[QualityIssue]:
    """Détecte des distributions suspectes : variance nulle, forte asymétrie, concentration excessive."""
    numeric_columns = columns or [c for c in df.select_dtypes(include=[np.number]).columns]
    issues: list[QualityIssue] = []

    for column in numeric_columns:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue

        if series.nunique() == 1:
            issues.append(
                QualityIssue(
                    code="ZERO_VARIANCE",
                    severity=SEVERITY_IMPORTANT,
                    variable=column,
                    description=f"La variable '{column}' ne prend qu'une seule valeur (variance nulle).",
                    n_affected=int(len(series)),
                    details={"valeur_unique": float(series.iloc[0])},
                )
            )
            continue

        skewness = float(series.skew())
        if abs(skewness) >= 2:
            issues.append(
                QualityIssue(
                    code="SUSPICIOUS_SKEWNESS",
                    severity=SEVERITY_MINEUR,
                    variable=column,
                    description=f"Asymétrie marquée détectée sur '{column}' (skewness={skewness:.2f}).",
                    n_affected=int(len(series)),
                    details={"skewness": round(skewness, 3)},
                )
            )

        mode_share = series.value_counts(normalize=True).iloc[0]
        if mode_share >= 0.9:
            issues.append(
                QualityIssue(
                    code="EXCESSIVE_CONCENTRATION",
                    severity=SEVERITY_IMPORTANT,
                    variable=column,
                    description=f"Plus de 90% des valeurs de '{column}' sont concentrées sur une seule valeur.",
                    n_affected=int(len(series)),
                    details={"part_valeur_dominante": round(float(mode_share), 3)},
                )
            )
    return issues


def check_cross_variable_consistency(df: pd.DataFrame) -> list[QualityIssue]:
    """Détecte les incohérences entre plusieurs variables liées."""
    issues: list[QualityIssue] = []

    if {"rep", "rep_plus", "statut"}.issubset(df.columns):
        mismatch_rep = df[(df["statut"] == "REP") & (df["rep"] != 1)]
        mismatch_rep_plus = df[(df["statut"] == "REP+") & (df["rep_plus"] != 1)]
        n_affected = int(len(mismatch_rep) + len(mismatch_rep_plus))
        if n_affected > 0:
            issues.append(
                QualityIssue(
                    code="INCONSISTENT_STATUS_FLAGS",
                    severity=SEVERITY_CRITIQUE,
                    variable="statut, rep, rep_plus",
                    description="Incohérence entre le statut textuel (REP/REP+) et les indicateurs binaires associés.",
                    n_affected=n_affected,
                    details={},
                )
            )

    if {"education_prioritaire", "statut"}.issubset(df.columns):
        expected_ep = (df["statut"] != "Hors EP").astype(int)
        mismatch = df["education_prioritaire"].astype("Int64") != expected_ep.astype("Int64")
        n_affected = int(mismatch.sum())
        if n_affected > 0:
            issues.append(
                QualityIssue(
                    code="INCONSISTENT_EDUCATION_PRIORITAIRE_FLAG",
                    severity=SEVERITY_CRITIQUE,
                    variable="education_prioritaire, statut",
                    description="L'indicateur 'education_prioritaire' n'est pas cohérent avec le statut REP/REP+/Hors EP.",
                    n_affected=n_affected,
                    details={},
                )
            )

    if {"nombre_classes", "effectif_eleves"}.issubset(df.columns):
        implied_class_size = df["effectif_eleves"] / df["nombre_classes"].replace(0, np.nan)
        mask = implied_class_size > 45
        n_affected = int(mask.sum())
        if n_affected > 0:
            issues.append(
                QualityIssue(
                    code="INCONSISTENT_CLASS_SIZE",
                    severity=SEVERITY_IMPORTANT,
                    variable="effectif_eleves, nombre_classes",
                    description="Taille de classe implicite (effectif / nombre de classes) anormalement élevée (> 45 élèves).",
                    n_affected=n_affected,
                    details={},
                )
            )

    if {"score_global", "score_francais", "score_mathematiques"}.issubset(df.columns):
        recomputed = (df["score_francais"] + df["score_mathematiques"]) / 2
        mismatch = (df["score_global"] - recomputed).abs() > 0.5
        n_affected = int(mismatch.sum())
        if n_affected > 0:
            issues.append(
                QualityIssue(
                    code="INCONSISTENT_SCORE_GLOBAL",
                    severity=SEVERITY_IMPORTANT,
                    variable="score_global, score_francais, score_mathematiques",
                    description="Le score global ne correspond pas à la moyenne des scores par discipline (écart > 0.5 point).",
                    n_affected=n_affected,
                    details={},
                )
            )

    return issues


def run_full_quality_check(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
) -> QualityReport:
    """Exécute l'ensemble des contrôles de qualité et retourne un rapport consolidé.

    Aucune correction n'est appliquée : ce rapport documente uniquement les
    problèmes détectés, classés par sévérité (CRITIQUE / IMPORTANT / MINEUR).
    """
    report = QualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        n_rows=int(len(df)),
        n_columns=int(df.shape[1]),
        columns=list(df.columns),
    )

    report.add(check_duplicate_rows(df))
    report.add(check_duplicate_identifiers(df, key_columns))

    for issue in check_missing_values(df):
        report.add(issue)
    for issue in check_type_consistency(df):
        report.add(issue)
    for issue in check_unexpected_categories(df):
        report.add(issue)
    for issue in check_impossible_values(df):
        report.add(issue)
    for issue in check_outliers_iqr(df):
        report.add(issue)
    for issue in check_suspicious_distributions(df):
        report.add(issue)
    for issue in check_cross_variable_consistency(df):
        report.add(issue)

    return report


def render_report_markdown(report: QualityReport, dataset_path: Path | str | None = None) -> str:
    """Formate le rapport de qualité en Markdown lisible."""
    counts = report.summary_counts()
    lines: list[str] = [
        "# Rapport de contrôle qualité",
        "",
        f"Généré le : {report.generated_at}",
    ]
    if dataset_path is not None:
        lines.append(f"Fichier analysé : {dataset_path}")
    lines += [
        "",
        "## Vue d'ensemble",
        "",
        f"- Nombre de lignes : {report.n_rows}",
        f"- Nombre de colonnes : {report.n_columns}",
        f"- Problèmes CRITIQUES : {counts[SEVERITY_CRITIQUE]}",
        f"- Problèmes IMPORTANTS : {counts[SEVERITY_IMPORTANT]}",
        f"- Problèmes MINEURS : {counts[SEVERITY_MINEUR]}",
        "",
        "## Détail des problèmes détectés",
        "",
    ]

    if not report.issues:
        lines.append("Aucun problème détecté par les contrôles automatisés.")
    else:
        for severity in (SEVERITY_CRITIQUE, SEVERITY_IMPORTANT, SEVERITY_MINEUR):
            issues = report.issues_by_severity(severity)
            if not issues:
                continue
            lines.append(f"### {severity}")
            lines.append("")
            for issue in issues:
                variable_txt = f" (variable : {issue.variable})" if issue.variable else ""
                lines.append(f"- **{issue.code}**{variable_txt} — {issue.description} — observations concernées : {issue.n_affected}")
                if issue.details:
                    for key, value in issue.details.items():
                        lines.append(f"    - {key} : {value}")
            lines.append("")

    lines += [
        "## Décisions de correction",
        "",
        "Aucune correction automatique n'a été appliquée à ce stade. Toute correction "
        "future devra être décidée explicitement dans le notebook de nettoyage "
        "(`04_nettoyage.ipynb`), et devra être justifiée et tracée (règle appliquée, "
        "nombre de lignes concernées, raison métier ou statistique).",
    ]

    return "\n".join(lines)


def save_quality_report(
    report: QualityReport,
    output_dir: Path,
    dataset_path: Path | str | None = None,
    base_name: str = "rapport_qualite_donnees_brutes",
) -> dict[str, Path]:
    """Enregistre le rapport de qualité en Markdown et en JSON dans outputs/reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / f"{base_name}.md"
    json_path = output_dir / f"{base_name}.json"

    markdown_path.write_text(render_report_markdown(report, dataset_path), encoding="utf-8")

    import json

    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    return {"markdown": markdown_path, "json": json_path}


__all__ = [
    "SEVERITY_CRITIQUE",
    "SEVERITY_IMPORTANT",
    "SEVERITY_MINEUR",
    "QualityIssue",
    "QualityReport",
    "check_duplicate_rows",
    "check_duplicate_identifiers",
    "check_missing_values",
    "check_type_consistency",
    "check_unexpected_categories",
    "check_impossible_values",
    "check_outliers_iqr",
    "check_suspicious_distributions",
    "check_cross_variable_consistency",
    "run_full_quality_check",
    "render_report_markdown",
    "save_quality_report",
]
