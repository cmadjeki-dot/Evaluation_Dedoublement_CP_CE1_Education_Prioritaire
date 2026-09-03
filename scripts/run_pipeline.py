"""Pipeline complet et reproductible du projet.

Enchaîne automatiquement toutes les étapes de la chaîne analytique :

    DONNÉES RAW -> CONTRÔLE QUALITÉ -> NETTOYAGE -> PROCESSED
    -> ANALYSES -> MODÈLES -> INDICATEURS -> FIGURES -> TABLEAUX
    -> RAPPORT -> SITE -> VALIDATION DES ARTEFACTS

Chaque étape réutilise exclusivement les fonctions déjà définies dans
``src/`` et les scripts d'artefacts existants (``generate_figures.py``,
``generate_tables.py``, ``generate_report.py``, ``build_static_site.py``) :
aucune logique n'est recopiée.

Comportement :
    - le pipeline s'arrête à la première étape en échec (« fail fast ») ;
    - l'étape responsable de l'échec est explicitement indiquée ;
    - chaque étape est journalisée (horodatage, statut, durée) dans
      ``outputs/logs/pipeline_<horodatage>.log`` et sur la sortie standard ;
    - à la fin de chaque étape, les fichiers de sortie attendus sont vérifiés
      (existence + non-vacuité) avant de passer à l'étape suivante ;
    - le message final « PIPELINE : OK » n'est affiché que si toutes les
      étapes se sont terminées avec succès et que tous les artefacts
      attendus ont été validés.

Usage :
    python scripts/run_pipeline.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.data import (  # noqa: E402
    acquire_project_data,
    load_raw_dataset,
)
from src.data.cleaning import (  # noqa: E402
    TransformationJournal,
    TransformationStep,
    analyze_missing_values,
    compare_before_after,
    fix_column_types,
    handle_impossible_values,
    harmonize_categories,
    remove_duplicate_rows,
    save_interim_dataset,
    save_processed_dataset,
)
from src.quality import (  # noqa: E402
    render_report_markdown,
    run_full_quality_check,
    save_quality_report,
)
from src.utils.paths import LOGS_DIR  # noqa: E402

DATASET_NAME = "education_prioritaire"


class PipelineError(RuntimeError):
    """Erreur levée par une étape du pipeline, avec le nom de l'étape responsable."""

    def __init__(self, step_name: str, original_error: Exception):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Étape « {step_name} » en échec : {original_error}")


class PipelineLogger:
    """Journalise les étapes du pipeline sur la sortie standard et dans un fichier log."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lines: list[str] = []

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def write(self, message: str) -> None:
        line = f"[{self._timestamp()}] {message}"
        print(line)
        self._lines.append(line)
        self.log_path.write_text("\n".join(self._lines) + "\n", encoding="utf-8")


def _check_expected_files(paths: list[Path], step_name: str) -> None:
    """Vérifie que chaque fichier attendu existe et n'est pas vide."""
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"Fichier attendu absent après l'étape « {step_name} » : {path}")
        if path.is_file() and path.stat().st_size == 0:
            raise RuntimeError(f"Fichier attendu vide après l'étape « {step_name} » : {path}")


def run_step(logger: PipelineLogger, step_name: str, func, *args, **kwargs):
    """Exécute une étape du pipeline, journalise son statut et arrête le pipeline en cas d'échec."""
    logger.write(f"DÉBUT — {step_name}")
    start = time.monotonic()
    try:
        result = func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - on veut capturer toute erreur d'étape
        duration = time.monotonic() - start
        logger.write(f"ÉCHEC — {step_name} (après {duration:.2f}s) : {exc}")
        raise PipelineError(step_name, exc) from exc
    duration = time.monotonic() - start
    logger.write(f"SUCCÈS — {step_name} (durée : {duration:.2f}s)")
    return result


# ---------------------------------------------------------------------------
# Étape 1 — Données brutes
# ---------------------------------------------------------------------------
def step_raw_data() -> Path:
    result = acquire_project_data()
    _check_expected_files([result.path], "données brutes")
    return result.path


# ---------------------------------------------------------------------------
# Étape 2 — Contrôle qualité
# ---------------------------------------------------------------------------
def step_quality_control() -> None:
    from src.utils.paths import REPORTS_DIR

    raw_result = load_raw_dataset()
    df = raw_result.dataframe
    report = run_full_quality_check(df)
    render_report_markdown(report, dataset_path=raw_result.path)
    saved_paths = save_quality_report(report, REPORTS_DIR, dataset_path=raw_result.path)
    _check_expected_files(list(saved_paths.values()), "contrôle qualité")


# ---------------------------------------------------------------------------
# Étape 3 — Nettoyage -> data/interim puis data/processed
# ---------------------------------------------------------------------------
def step_cleaning() -> Path:
    from src.utils.paths import REPORTS_DIR

    raw_result = load_raw_dataset()
    df_raw = raw_result.dataframe

    journal = TransformationJournal(dataset_name=DATASET_NAME)
    df = df_raw.copy()

    df = remove_duplicate_rows(df, journal)

    type_cible = {
        "annee": "int64",
        "niveau": "category",
        "statut": "category",
        "academie": "category",
        "departement": "category",
    }
    df = fix_column_types(df, type_cible, journal)

    mapping_statut = {v: v for v in ["REP", "REP+", "Hors EP"]}
    mapping_niveau = {v: v for v in ["CP", "CE1", "CM1", "CM2", "6e"]}
    df = harmonize_categories(df, "statut", mapping_statut, journal)
    df = harmonize_categories(df, "niveau", mapping_niveau, journal)

    df = handle_impossible_values(df, "ips", (0, 160), "marquer_manquant", journal)
    df = handle_impossible_values(df, "effectif_eleves", (1, 60), "marquer_manquant", journal)
    df = handle_impossible_values(df, "taille_moyenne_classe", (1, 40), "marquer_manquant", journal)
    score_columns = [
        "score_francais",
        "score_mathematiques",
        "score_global",
        "taux_maitrise_francais",
        "taux_maitrise_mathematiques",
        "variable_cible",
    ]
    for col in score_columns:
        df = handle_impossible_values(df, col, (0, 100), "marquer_manquant", journal)

    journal.log(
        TransformationStep(
            action="exclusion_variable",
            variable="nombre_classes",
            strategie="exclusion_de_la_variable",
            justification=(
                "Variance nulle confirmée par le contrôle qualité (phase 7) : la variable ne prend "
                "qu'une seule valeur sur l'ensemble des observations. Conservée dans data/interim/ "
                "pour traçabilité, retirée de data/processed/ (jeu prêt pour analyse)."
            ),
            n_lignes_avant=len(df),
            n_lignes_apres=len(df),
            n_valeurs_modifiees=0,
        )
    )

    analyze_missing_values(df)

    journal.log(
        TransformationStep(
            action="revue_outliers_iqr",
            variable=", ".join(score_columns + ["effectif_eleves", "taille_moyenne_classe"]),
            strategie="conservation_sans_modification",
            justification=(
                "Valeurs aberrantes IQR (classées MINEUR en phase 7) toutes situées dans les plages "
                "plausibles métier. Représentent une variation naturelle et non des erreurs de saisie."
            ),
            n_lignes_avant=len(df),
            n_lignes_apres=len(df),
            n_valeurs_modifiees=0,
        )
    )

    journal.log(
        TransformationStep(
            action="controle_coherence_croisee",
            variable="statut, rep, rep_plus, education_prioritaire, score_global",
            strategie="aucune_action",
            justification="Aucune incohérence détectée par le contrôle qualité (phase 7).",
            n_lignes_avant=len(df),
            n_lignes_apres=len(df),
            n_valeurs_modifiees=0,
        )
    )

    numeric_columns = [
        "effectif_eleves",
        "taille_moyenne_classe",
        "ips",
        "score_francais",
        "score_mathematiques",
        "score_global",
        "variable_cible",
    ]
    compare_before_after(df_raw, df, columns=numeric_columns)

    interim_path = save_interim_dataset(df, DATASET_NAME)

    df_processed = df.drop(columns=["nombre_classes"])
    processed_path = save_processed_dataset(df_processed, DATASET_NAME)

    journal_paths = journal.save(REPORTS_DIR, "journal_transformations_donnees_education_prioritaire")

    _check_expected_files([interim_path, processed_path, *journal_paths.values()], "nettoyage")
    return processed_path


# ---------------------------------------------------------------------------
# Étapes 4 à 9 — Analyses, modèles, indicateurs, figures, tableaux, rapport, site
# via les scripts existants (aucune logique recopiée)
# ---------------------------------------------------------------------------
def _run_script(script_name: str) -> None:
    """Exécute un script du projet dans un sous-processus Python et lève une erreur explicite en cas d'échec."""
    script_path = PROJECT_ROOT / "scripts" / script_name
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.stdout:
        try:
            print(completed.stdout, end="")
        except UnicodeEncodeError:
            print(completed.stdout.encode("ascii", errors="replace").decode("ascii"), end="")
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "code de retour non nul"
        raise RuntimeError(f"{script_name} a échoué : {detail}")


def step_generate_tables() -> None:
    _run_script("generate_tables.py")
    from src.utils.paths import TABLES_DIR

    expected = [
        TABLES_DIR / "05_comparaison_statut.csv",
        TABLES_DIR / "06_coefficients_ols.csv",
        TABLES_DIR / "07_clusters_profils_ecoles.csv",
        TABLES_DIR / "08_tendance_lineaire_par_statut.csv",
        TABLES_DIR / "09_faisabilite_causale_did.csv",
        TABLES_DIR / "indicateurs_decisionnels.csv",
    ]
    _check_expected_files(expected, "analyses, modèles, indicateurs et tableaux")


def step_generate_figures() -> None:
    _run_script("generate_figures.py")
    from src.utils.paths import FIGURES_DIR

    expected = [
        FIGURES_DIR / "05_distribution_variable_cible.png",
        FIGURES_DIR / "06_diagnostics_ols.png",
        FIGURES_DIR / "07_segmentation_ecoles.png",
        FIGURES_DIR / "08_tendance_temporelle_statut.png",
    ]
    _check_expected_files(expected, "figures")


def step_generate_report() -> None:
    _run_script("generate_report.py")
    from src.utils.paths import PROJECT_ROOT as ROOT

    _check_expected_files([ROOT / "docs" / "rapport_final.md"], "rapport final")


def step_build_site() -> None:
    _run_script("build_static_site.py")
    from src.utils.paths import SITE_DIR

    _check_expected_files([SITE_DIR / "index.html"], "site statique")


# ---------------------------------------------------------------------------
# Étape finale — validation globale des artefacts
# ---------------------------------------------------------------------------
def step_validate_artifacts() -> dict[str, int]:
    from src.utils.paths import FIGURES_DIR, REPORTS_DIR, SITE_DIR, TABLES_DIR

    n_figures = len(list(FIGURES_DIR.glob("*.png")))
    n_tables = len(list(TABLES_DIR.glob("*.csv")))
    n_reports = len(list(REPORTS_DIR.glob("*.md")))
    n_site_figures = len(list((SITE_DIR / "figures").glob("*.png")))
    n_site_tables = len(list((SITE_DIR / "tables").glob("*.csv")))

    counts = {
        "figures_outputs": n_figures,
        "tables_outputs": n_tables,
        "rapports_outputs": n_reports,
        "figures_site": n_site_figures,
        "tables_site": n_site_tables,
    }

    if n_figures == 0:
        raise RuntimeError("Validation finale échouée : aucune figure trouvée dans outputs/figures/.")
    if n_tables == 0:
        raise RuntimeError("Validation finale échouée : aucune table trouvée dans outputs/tables/.")
    if n_reports == 0:
        raise RuntimeError("Validation finale échouée : aucun rapport trouvé dans outputs/reports/.")
    if n_site_figures == 0 or n_site_tables == 0:
        raise RuntimeError("Validation finale échouée : le site statique ne contient pas les artefacts attendus.")

    return counts


def main() -> int:
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"pipeline_{horodatage}.log"
    logger = PipelineLogger(log_path)

    logger.write("=== DÉBUT DU PIPELINE ===")
    logger.write(f"Journal détaillé : {log_path}")

    steps = [
        ("Acquisition des données brutes", step_raw_data, []),
        ("Contrôle qualité", step_quality_control, []),
        ("Nettoyage et préparation (interim + processed)", step_cleaning, []),
        ("Analyses, modélisation et indicateurs (tables)", step_generate_tables, []),
        ("Génération des figures", step_generate_figures, []),
        ("Génération du rapport final", step_generate_report, []),
        ("Construction du site statique", step_build_site, []),
    ]

    try:
        for step_name, func, args in steps:
            run_step(logger, step_name, func, *args)

        counts = run_step(logger, "Validation finale des artefacts", step_validate_artifacts)
        logger.write(f"Synthèse des artefacts validés : {counts}")
    except PipelineError as exc:
        logger.write("=== PIPELINE : ÉCHEC ===")
        logger.write(f"Étape responsable : {exc.step_name}")
        logger.write(f"Erreur : {exc.original_error}")
        print()
        print(f"PIPELINE : ÉCHEC — étape responsable : « {exc.step_name} »")
        print(f"Détail : {exc.original_error}")
        print(f"Voir le journal complet : {log_path}")
        return 1
    except Exception as exc:  # noqa: BLE001 - filet de sécurité pour toute erreur imprévue
        logger.write("=== PIPELINE : ÉCHEC (erreur imprévue) ===")
        logger.write(f"Erreur : {exc}")
        print()
        print(f"PIPELINE : ÉCHEC — erreur imprévue : {exc}")
        print(f"Voir le journal complet : {log_path}")
        return 1

    logger.write("=== PIPELINE : OK ===")
    print()
    print("PIPELINE : OK")
    print(f"Toutes les étapes se sont terminées avec succès. Journal complet : {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
