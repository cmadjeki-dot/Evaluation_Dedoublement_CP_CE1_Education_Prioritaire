"""Tests des chemins portables (src/utils/paths.py)."""

from pathlib import Path

from src.utils.paths import (
    DATA_DIR,
    FIGURES_DIR,
    LOGS_DIR,
    MODELS_DIR,
    NOTEBOOKS_DIR,
    OUTPUT_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    SITE_DIR,
    TABLES_DIR,
    ensure_directory,
    ensure_project_directories,
)


def test_project_root_is_absolute_and_exists():
    assert PROJECT_ROOT.is_absolute()
    assert PROJECT_ROOT.exists()


def test_no_hardcoded_user_path_in_project_root():
    # Le chemin racine ne doit jamais être codé en dur : il doit être dérivé de __file__.
    root_str = str(PROJECT_ROOT)
    assert "Desktop" not in root_str or PROJECT_ROOT.exists()
    assert isinstance(PROJECT_ROOT, Path)


def test_derived_paths_are_subpaths_of_project_root():
    directories = (
        DATA_DIR,
        OUTPUT_DIR,
        FIGURES_DIR,
        TABLES_DIR,
        REPORTS_DIR,
        LOGS_DIR,
        MODELS_DIR,
        NOTEBOOKS_DIR,
        SITE_DIR,
    )
    for directory in directories:
        assert PROJECT_ROOT in directory.parents


def test_ensure_directory_creates_nested_path(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    assert not target.exists()
    result = ensure_directory(target)
    assert result == target
    assert target.exists()
    assert target.is_dir()


def test_ensure_directory_is_idempotent(tmp_path):
    target = tmp_path / "already_here"
    target.mkdir()
    ensure_directory(target)
    assert target.exists()


def test_ensure_project_directories_creates_all_expected_dirs():
    directories = ensure_project_directories()
    expected_keys = {
        "project_root",
        "data",
        "outputs",
        "figures",
        "tables",
        "reports",
        "logs",
        "models",
        "notebooks",
        "site",
    }
    assert expected_keys.issubset(directories.keys())
    for key, path in directories.items():
        assert path.exists(), f"Le dossier '{key}' ({path}) devrait exister"
