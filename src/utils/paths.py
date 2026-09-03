from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"
REPORTS_DIR = OUTPUT_DIR / "reports"
LOGS_DIR = OUTPUT_DIR / "logs"
MODELS_DIR = OUTPUT_DIR / "models"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SITE_DIR = PROJECT_ROOT / "site"


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_project_directories() -> dict[str, Path]:
    directories = {
        "project_root": PROJECT_ROOT,
        "data": DATA_DIR,
        "outputs": OUTPUT_DIR,
        "figures": FIGURES_DIR,
        "tables": TABLES_DIR,
        "reports": REPORTS_DIR,
        "logs": LOGS_DIR,
        "models": MODELS_DIR,
        "notebooks": NOTEBOOKS_DIR,
        "site": SITE_DIR,
    }
    for directory in directories.values():
        ensure_directory(directory)
    return directories
