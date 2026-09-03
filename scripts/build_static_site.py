"""Construit une version statique et partageable des artefacts du projet.

Ce script ne recalcule rien : il republie dans ``site/`` les artefacts déjà
produits par ``generate_figures.py``, ``generate_tables.py`` et
``generate_report.py`` (figures, tableaux, rapport final), puis génère une
page ``site/index.html`` qui les liste.

Chaque étape est vérifiée : les répertoires source doivent contenir au moins
un fichier utile, et chaque fichier copié doit exister et ne pas être vide
après copie, sinon une erreur explicite (RuntimeError) est levée.

Usage :
    python scripts/build_static_site.py
"""

from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.paths import (
    FIGURES_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    SITE_DIR,
    TABLES_DIR,
    ensure_directory,
    ensure_project_directories,
)

DOCS_REPORT_PATH = PROJECT_ROOT / "docs" / "rapport_final.md"
INDICATEURS_PATH = TABLES_DIR / "indicateurs_decisionnels.csv"

# Liens externes de restitution publique. À remplacer par les URLs réelles
# une fois le dépôt GitHub et le dashboard hébergé publiquement disponibles.
GITHUB_REPO_URL = (
    "https://github.com/cmadjeki-dot/Evaluation_Dedoublement_CP_CE1_Education_Prioritaire"
)
DASHBOARD_PUBLIC_URL = (
    "https://evaluationdedoublementcpce1educationprioritaire-dsqnzzhphhk9qw.streamlit.app/"
)

CONTEXTE_PROJET = (
    "Effet du dédoublement des classes de CP/CE1 en éducation prioritaire sur les performances "
    "scolaires, suivi à court terme (CP/CE1), moyen terme (CM1/CM2) et long terme (entrée en 6e). "
    "Les données utilisées sont simulées de manière reproductible (seed fixe) : les résultats "
    "illustrent la démarche méthodologique et ne constituent pas des statistiques officielles."
)


def _check_output(path: Path, label: str) -> Path:
    """Vérifie qu'un fichier de sortie existe et n'est pas vide."""
    if not path.exists():
        raise RuntimeError(f"Échec de publication du site : '{label}' absent ({path})")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Échec de publication du site : '{label}' vide ({path})")
    return path


def _clear_published_files(directory: Path, pattern: str) -> None:
    """Supprime les fichiers précédemment publiés (hors .gitkeep) avant de republier."""
    for existing in directory.glob(pattern):
        if existing.name == ".gitkeep":
            continue
        existing.unlink()


def publish_figures() -> list[Path]:
    """Copie toutes les figures PNG de outputs/figures/ vers site/figures/."""
    source_files = sorted(FIGURES_DIR.glob("*.png"))
    if not source_files:
        raise RuntimeError(
            f"Aucune figure trouvée dans {FIGURES_DIR}. Exécutez d'abord scripts/generate_figures.py."
        )

    target_dir = ensure_directory(SITE_DIR / "figures")
    _clear_published_files(target_dir, "*.png")

    published: list[Path] = []
    for source in source_files:
        target = target_dir / source.name
        shutil.copy2(source, target)
        published.append(_check_output(target, f"figure {source.name}"))

    print(f"Figures publiées : {len(published)} fichier(s) dans {target_dir}")
    return published


def publish_tables() -> list[Path]:
    """Copie tous les tableaux CSV de outputs/tables/ vers site/tables/."""
    source_files = sorted(TABLES_DIR.glob("*.csv"))
    if not source_files:
        raise RuntimeError(
            f"Aucun tableau trouvé dans {TABLES_DIR}. Exécutez d'abord scripts/generate_tables.py."
        )

    target_dir = ensure_directory(SITE_DIR / "tables")
    _clear_published_files(target_dir, "*.csv")

    published: list[Path] = []
    for source in source_files:
        target = target_dir / source.name
        shutil.copy2(source, target)
        published.append(_check_output(target, f"tableau {source.name}"))

    print(f"Tableaux publiés : {len(published)} fichier(s) dans {target_dir}")
    return published


def publish_report() -> Path:
    """Copie le rapport final (docs/rapport_final.md) vers site/reports/."""
    if not DOCS_REPORT_PATH.exists():
        raise RuntimeError(
            f"Rapport final introuvable ({DOCS_REPORT_PATH}). Exécutez d'abord scripts/generate_report.py."
        )

    target_dir = ensure_directory(SITE_DIR / "reports")
    _clear_published_files(target_dir, "*.md")

    target = target_dir / "rapport_final.md"
    shutil.copy2(DOCS_REPORT_PATH, target)
    _check_output(target, "rapport_final.md")

    # Conserve également la dernière archive horodatée disponible, si elle existe.
    archives = sorted(REPORTS_DIR.glob("rapport_final_*.md"))
    if archives:
        latest_archive = archives[-1]
        archive_target = target_dir / latest_archive.name
        shutil.copy2(latest_archive, archive_target)
        _check_output(archive_target, latest_archive.name)

    print(f"Rapport publié dans {target_dir}")
    return target


def load_kpi_rows() -> list[dict[str, str]]:
    """Charge les indicateurs décisionnels déjà calculés pour la section KPI du site."""
    if not INDICATEURS_PATH.exists() or INDICATEURS_PATH.stat().st_size == 0:
        return []
    table = pd.read_csv(INDICATEURS_PATH)
    return table.to_dict(orient="records")


def build_index_html(figures: list[Path], tables: list[Path], report_path: Path) -> Path:
    """Génère site/index.html listant les artefacts publiés."""
    tables_items = "\n".join(
        f'      <li><a href="tables/{t.name}">{t.name}</a></li>' for t in tables
    )

    kpi_rows = load_kpi_rows()
    if kpi_rows:
        kpi_card_parts = []
        for row in kpi_rows:
            valeur_fmt = html.escape(f"{row['valeur']:.3g}")
            unite_fmt = html.escape(str(row["unite"]))
            nom_fmt = html.escape(str(row["nom"]))
            interpretation_fmt = html.escape(str(row["interpretation"]))
            kpi_card_parts.append(
                f"""      <div class="kpi-card">
        <div class="kpi-valeur">{valeur_fmt} <span class="kpi-unite">{unite_fmt}</span></div>
        <div class="kpi-nom">{nom_fmt}</div>
        <div class="kpi-interpretation">{interpretation_fmt}</div>
      </div>"""
            )
        kpi_cards = "\n".join(kpi_card_parts)
    else:
        kpi_cards = "      <p>Indicateurs décisionnels non disponibles (exécutez le pipeline).</p>"

    figures_grid_html = "\n".join(
        f'        <div><img src="figures/{f.name}" alt="{f.name}" loading="lazy"><p>{f.name}</p></div>'
        for f in figures
    )

    page_html = f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Projet Statistique — Restitution</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
      .container {{ max-width: 1000px; margin: auto; }}
      h2 {{ margin-top: 2.5rem; border-bottom: 1px solid #d1d5db; padding-bottom: 0.3rem; }}
      ul {{ line-height: 1.6; }}
      a {{ color: #1d4ed8; }}
      .badge {{
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 0.4rem;
        background: #eef2ff; color: #3730a3; font-size: 0.85rem; margin-right: 0.5rem;
      }}
      .kpi-grid {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem; margin-top: 1rem;
      }}
      .kpi-card {{
        border: 1px solid #d1d5db; border-radius: 0.5rem; padding: 1rem; background: #f9fafb;
      }}
      .kpi-valeur {{ font-size: 1.6rem; font-weight: bold; color: #1d4ed8; }}
      .kpi-unite {{ font-size: 0.85rem; color: #6b7280; font-weight: normal; }}
      .kpi-nom {{ font-weight: 600; margin-top: 0.3rem; }}
      .kpi-interpretation {{ font-size: 0.85rem; color: #4b5563; margin-top: 0.3rem; }}
      .links-row a {{ margin-right: 1.2rem; }}
      .figures-grid {{
        display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;
      }}
      .figures-grid img {{ width: 100%; border: 1px solid #e5e7eb; border-radius: 0.4rem; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
      th, td {{ border: 1px solid #e5e7eb; padding: 0.3rem 0.5rem; text-align: left; }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Projet de statistique publique — Restitution</h1>
      <p>{html.escape(CONTEXTE_PROJET)}</p>
      <p class="links-row">
        <a href="{html.escape(GITHUB_REPO_URL)}">Dépôt GitHub</a>
        <a href="{html.escape(DASHBOARD_PUBLIC_URL)}">Dashboard interactif (Streamlit)</a>
      </p>

      <h2>Indicateurs clés (KPI)</h2>
      <div class="kpi-grid">
{kpi_cards}
      </div>

      <h2>Méthodologie</h2>
      <ol>
        <li>Cadrage métier et statistique (contexte, problématique, population, variable cible).</li>
        <li>Acquisition des données et description initiale.</li>
        <li>Contrôle qualité (doublons, valeurs manquantes, anomalies, outliers).</li>
        <li>Nettoyage et préparation (imputation justifiée, journal de transformation).</li>
        <li>Analyse descriptive (comparaisons par statut, tableaux croisés, intervalles de confiance).</li>
        <li>Modélisation (OLS, modèle à effets mixtes) et analyses spécialisées.</li>
        <li>Analyses longitudinale et causale (différence-de-différences, avec évaluation de faisabilité).</li>
        <li>Indicateurs décisionnels et restitution non technique.</li>
      </ol>

      <h2>Rapport final</h2>
      <ul>
        <li><a href="reports/{report_path.name}">{report_path.name}</a></li>
      </ul>

      <h2>Figures ({len(figures)})</h2>
      <div class="figures-grid">
{figures_grid_html}
      </div>

      <h2>Tableaux ({len(tables)})</h2>
      <ul>
{tables_items}
      </ul>
    </div>
  </body>
</html>
"""
    index_path = SITE_DIR / "index.html"
    index_path.write_text(page_html, encoding="utf-8")
    _check_output(index_path, "index.html")
    print(f"Page d'accueil générée : {index_path}")
    return index_path


def main() -> None:
    ensure_project_directories()
    ensure_directory(SITE_DIR / "figures")
    ensure_directory(SITE_DIR / "tables")
    ensure_directory(SITE_DIR / "reports")
    print("Construction du site statique...")

    try:
        figures = publish_figures()
        tables = publish_tables()
        report_path = publish_report()
        build_index_html(figures, tables, report_path)
    except Exception as exc:
        raise RuntimeError(f"Échec de la construction du site statique : {exc}") from exc

    print("Site statique construit et vérifié avec succès.")


if __name__ == "__main__":
    main()
