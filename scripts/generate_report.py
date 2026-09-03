"""Génère automatiquement le rapport final du projet à partir des artefacts réels.

Ce script ne fabrique aucun résultat : il lit uniquement les tables déjà
produites dans ``outputs/tables/`` (via ``scripts/generate_tables.py``) et le
résumé du modèle dans ``outputs/models/`` pour synthétiser un rapport en
Markdown. Il ne recalcule rien lui-même — il documente ce qui a déjà été
calculé et vérifié ailleurs.

Le rapport est écrit à deux emplacements :
  - ``docs/rapport_final.md`` (version de référence, versionnée) ;
  - ``outputs/reports/rapport_final_<horodatage>.md`` (archive datée).

Usage :
    python scripts/generate_report.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.utils.paths import PROJECT_ROOT, REPORTS_DIR, TABLES_DIR, ensure_project_directories

DOCS_REPORT_PATH = PROJECT_ROOT / "docs" / "rapport_final.md"


def _check_output(path: Path, label: str) -> Path:
    """Vérifie qu'un fichier a bien été écrit (existence + non vide)."""
    if not path.exists():
        raise RuntimeError(f"Échec de génération du rapport '{label}' : fichier absent ({path})")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Échec de génération du rapport '{label}' : fichier vide ({path})")
    return path


def _load_table(name: str) -> pd.DataFrame:
    path = TABLES_DIR / f"{name}.csv"
    if not path.exists():
        raise RuntimeError(
            f"Table requise introuvable : {path}. "
            "Exécutez d'abord scripts/generate_tables.py."
        )
    return pd.read_csv(path)


def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def build_report_content() -> str:
    """Assemble le contenu Markdown du rapport à partir des tables réelles."""
    indicateurs = pd.read_csv(TABLES_DIR / "indicateurs_decisionnels.csv")
    if indicateurs.empty:
        raise RuntimeError("La table indicateurs_decisionnels.csv est vide.")

    comparaison_statut = _load_table("05_comparaison_statut")
    tests_statut = _load_table("05_tests_difference_statut")
    coefficients_ols = _load_table("06_coefficients_ols")
    faisabilite_did = _load_table("09_faisabilite_causale_did")
    tendance_statut = _load_table("08_tendance_lineaire_par_statut")

    # Le score global moyen (toutes observations) est déjà calculé et vérifié
    # dans la table des indicateurs décisionnels (source de vérité unique).
    ligne_score_moyen = indicateurs.loc[indicateurs["nom"] == "Score global moyen"]
    moyenne_generale = (
        float(ligne_score_moyen["valeur"].iloc[0]) if not ligne_score_moyen.empty
        else comparaison_statut["moyenne"].mean()
    )

    horaire = datetime.now().strftime("%Y-%m-%d %H:%M")

    lignes: list[str] = []
    lignes.append("# Rapport final")
    lignes.append("")
    lignes.append(f"*Document généré automatiquement le {horaire} par `scripts/generate_report.py`, "
                   "à partir des tables réellement calculées dans `outputs/tables/`.*")
    lignes.append("")
    lignes.append("## Objectif")
    lignes.append(
        "Ce document centralise la synthèse méthodologique et les résultats clés du projet "
        "portant sur l'effet du dédoublement des classes de CP/CE1 en éducation prioritaire "
        "sur les performances scolaires."
    )
    lignes.append("")
    lignes.append("## Périmètre")
    lignes.append("- Analyse du dédoublement des classes de CP et CE1 en éducation prioritaire.")
    lignes.append("- Comparaison REP, REP+ et hors éducation prioritaire.")
    lignes.append("- Suivi des performances à court, moyen et long terme (CP → CE1 → CM1 → CM2 → 6e).")
    lignes.append(
        "- **Données simulées** (seed fixe, voir `src/data/acquisition.py`) : les résultats "
        "illustrent la démarche méthodologique et ne constituent pas des statistiques officielles."
    )
    lignes.append("")
    lignes.append("## Méthodologie")
    lignes.append("1. Collecte et validation des données (`notebooks/01`, `notebooks/02`).")
    lignes.append("2. Contrôle qualité et nettoyage (`notebooks/03`, `notebooks/04`).")
    lignes.append("3. Analyse descriptive (`notebooks/05`).")
    lignes.append("4. Modélisation (OLS, modèle mixte) et analyses spécialisées (`notebooks/06`, `notebooks/07`).")
    lignes.append("5. Analyses longitudinale et causale (`notebooks/08`, `notebooks/09`).")
    lignes.append("6. Indicateurs décisionnels et restitution (`notebooks/10`, `notebooks/11`).")
    lignes.append("")

    lignes.append("## Chiffres clés")
    lignes.append("")
    lignes.append(f"- Score global moyen (variable cible) : **{_fmt(moyenne_generale)} / 100** "
                   "(moyenne des moyennes par statut).")
    for _, row in comparaison_statut.iterrows():
        lignes.append(
            f"  - {row['statut']} : moyenne = {_fmt(row['moyenne'])}, "
            f"effectif = {int(row['effectif'])}, écart-type = {_fmt(row['ecart_type'])}."
        )
    lignes.append("")
    lignes.append("### Tests de différence entre statuts (vs Hors EP)")
    lignes.append("")
    lignes.append(
        "| Statut comparé | Référence | Différence de moyennes | Statistique t "
        "| p-valeur | Significatif (5%) |"
    )
    lignes.append("|---|---|---|---|---|---|")
    for _, row in tests_statut.iterrows():
        p_val = row["p_value"]
        stat = row["statistique_t"]
        significatif = "Oui" if pd.notna(p_val) and p_val < 0.05 else "Non"
        lignes.append(
            f"| {row['groupe_a']} | {row['groupe_b']} | {_fmt(row['difference_moyennes'])} "
            f"| {_fmt(stat, 3)} | {p_val:.2e} | {significatif} |"
        )
    lignes.append("")

    lignes.append("### Modèle explicatif (OLS)")
    lignes.append("")
    lignes.append(
        f"Le modèle OLS comporte {len(coefficients_ols)} coefficients estimés "
        "(constante + effets des variables explicatives encodées). Le détail complet "
        "(coefficient, erreur standard, statistique t, p-valeur, IC 95%) est disponible dans "
        "`outputs/tables/06_coefficients_ols.csv`. Les métriques de performance globales "
        "(R², RMSE) figurent dans la table des indicateurs décisionnels ci-dessous."
    )
    lignes.append("")

    lignes.append("### Tendance temporelle par statut")
    lignes.append("")
    lignes.append("| Statut | Pente (points/an) |")
    lignes.append("|---|---|")
    for _, row in tendance_statut.iterrows():
        lignes.append(f"| {row['statut']} | {_fmt(row['pente_par_an'], 3)} |")
    lignes.append("")

    lignes.append("### Faisabilité d'une analyse causale (différence-de-différences)")
    lignes.append("")
    row_did = faisabilite_did.iloc[0]
    applicable = bool(row_did["applicable"])
    lignes.append(f"- **Applicable** : {'Oui' if applicable else 'Non'}")
    part_changement = _fmt(row_did["share_schools_with_status_changes"] * 100, 1)
    part_cp_ce1 = _fmt(row_did["mean_treatment_cp_ce1"] * 100, 1)
    part_autres = _fmt(row_did["mean_treatment_other_levels"] * 100, 1)
    lignes.append(f"- Part des écoles avec changement de statut dans le temps : {part_changement} %")
    lignes.append(f"- Exposition moyenne au dédoublement (CP/CE1) : {part_cp_ce1} %")
    lignes.append(f"- Exposition moyenne au dédoublement (autres niveaux) : {part_autres} %")
    if not applicable:
        raisons = json.loads(row_did["reasons_if_not_applicable"])
        lignes.append("- Raisons de non-applicabilité :")
        for raison in raisons:
            lignes.append(f"  - {raison}")
    lignes.append("")

    lignes.append("## Indicateurs décisionnels")
    lignes.append("")
    lignes.append(
        "La table complète (nom, définition, formule, valeur, unité, population, interprétation, "
        "limites, utilisation possible) est disponible dans "
        "`outputs/tables/indicateurs_decisionnels.csv`. Extrait :"
    )
    lignes.append("")
    lignes.append("| Indicateur | Valeur | Unité | Interprétation |")
    lignes.append("|---|---|---|---|")
    for _, row in indicateurs.iterrows():
        valeur = row["valeur"]
        valeur_fmt = _fmt(valeur, 4) if isinstance(valeur, (int, float)) else str(valeur)
        lignes.append(f"| {row['nom']} | {valeur_fmt} | {row['unite']} | {row['interpretation']} |")
    lignes.append("")

    lignes.append("## Limites générales")
    lignes.append("- Les données sont simulées : les valeurs numériques ne doivent pas être citées "
                   "comme des statistiques officielles de la DEPP.")
    lignes.append("- Les analyses associatives (corrélation, régression observationnelle) ne "
                   "démontrent pas de lien causal.")
    lignes.append("- La faisabilité d'une différence-de-différences dépend de la structure de "
                   "déploiement effectivement disponible dans les données (voir notebook 09).")
    lignes.append("")

    lignes.append("## Artefacts associés")
    lignes.append("- Figures : `outputs/figures/`")
    lignes.append("- Tables : `outputs/tables/`")
    lignes.append("- Modèles : `outputs/models/`")
    lignes.append("- Notebooks source : `notebooks/00` à `notebooks/11`")
    lignes.append("")

    return "\n".join(lignes)


def main() -> None:
    ensure_project_directories()

    try:
        content = build_report_content()
    except Exception as exc:  # noqa: BLE001 - message explicite en cas d'échec
        raise RuntimeError(f"Échec de la construction du contenu du rapport : {exc}") from exc

    # Écriture de la version de référence (docs/)
    DOCS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_REPORT_PATH.write_text(content, encoding="utf-8")
    _check_output(DOCS_REPORT_PATH, "docs/rapport_final.md")

    # Archive datée dans outputs/reports/
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = REPORTS_DIR / f"rapport_final_{horodatage}.md"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(content, encoding="utf-8")
    _check_output(archive_path, f"outputs/reports/rapport_final_{horodatage}.md")

    print(f"Rapport écrit dans : {DOCS_REPORT_PATH}")
    print(f"Archive écrite dans : {archive_path}")
    print("Le rapport final a été généré et vérifié avec succès.")


if __name__ == "__main__":
    main()
