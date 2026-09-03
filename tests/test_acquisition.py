"""Tests de la couche d'acquisition des données (src/data/acquisition.py)."""

import pandas as pd
import pytest

from src.data.acquisition import (
    DATA_SOURCE_DESCRIPTION,
    RAW_DATASET_NAME,
    DataAcquisitionResult,
    acquire_project_data,
    build_synthetic_open_data,
    dataset_exists,
    load_raw_dataset,
    raw_data_path,
)

EXPECTED_COLUMNS = {
    "annee",
    "ecole_id",
    "academie",
    "departement",
    "niveau",
    "statut",
    "rep",
    "rep_plus",
    "education_prioritaire",
    "effectif_eleves",
    "nombre_classes",
    "taille_moyenne_classe",
    "dedoublement",
    "ips",
    "score_francais",
    "score_mathematiques",
    "score_global",
    "taux_maitrise_francais",
    "taux_maitrise_mathematiques",
    "variable_cible",
    "source",
    "source_url",
}


def test_build_synthetic_open_data_returns_expected_columns():
    df = build_synthetic_open_data()
    assert not df.empty
    assert EXPECTED_COLUMNS.issubset(set(df.columns))


def test_build_synthetic_open_data_is_reproducible_seed_42():
    df1 = build_synthetic_open_data()
    df2 = build_synthetic_open_data()
    pd.testing.assert_frame_equal(df1, df2)


def test_build_synthetic_open_data_value_ranges_are_plausible():
    df = build_synthetic_open_data()
    assert df["score_francais"].between(0, 100).all()
    assert df["score_mathematiques"].between(0, 100).all()
    assert df["score_global"].between(0, 100).all()
    assert df["ips"].between(40, 100).all()
    assert df["dedoublement"].isin([0, 1]).all()
    assert df["rep"].isin([0, 1]).all()
    assert df["rep_plus"].isin([0, 1]).all()


def test_build_synthetic_open_data_expected_categories():
    df = build_synthetic_open_data()
    assert set(df["statut"].unique()) == {"Hors EP", "REP", "REP+"}
    assert set(df["niveau"].unique()) == {"CP", "CE1", "CM1", "CM2", "6e"}


def test_raw_data_path_returns_expected_filename(tmp_path, monkeypatch):
    import src.data.acquisition as acquisition_module

    monkeypatch.setattr(acquisition_module, "RAW_DATA_DIR", tmp_path)
    path = raw_data_path()
    assert path.name == RAW_DATASET_NAME
    assert path.parent == tmp_path
    assert tmp_path.exists()


def test_dataset_exists_false_then_true(tmp_path):
    candidate = tmp_path / "inexistant.csv"
    assert dataset_exists(candidate) is False
    candidate.write_text("annee\n2020\n", encoding="utf-8")
    assert dataset_exists(candidate) is True


def test_acquire_project_data_creates_file_and_returns_result(tmp_path):
    target = tmp_path / "brut.csv"
    result = acquire_project_data(path=target)

    assert isinstance(result, DataAcquisitionResult)
    assert target.exists()
    assert not result.dataframe.empty
    assert result.path == target
    assert result.metadata["mode"] == "synthetic_reproducible"
    assert result.metadata["rows"] == len(result.dataframe)


def test_acquire_project_data_reuses_existing_file_without_force(tmp_path):
    target = tmp_path / "brut.csv"
    first = acquire_project_data(path=target)
    mtime_before = target.stat().st_mtime_ns

    second = acquire_project_data(path=target)

    assert second.metadata["mode"] == "existing_raw_data"
    assert target.stat().st_mtime_ns == mtime_before
    assert len(second.dataframe) == len(first.dataframe)


def test_acquire_project_data_force_rebuild_overwrites(tmp_path):
    target = tmp_path / "brut.csv"
    acquire_project_data(path=target)
    result = acquire_project_data(path=target, force_rebuild=True)
    assert result.metadata["mode"] == "synthetic_reproducible"


def test_load_raw_dataset_raises_if_missing(tmp_path):
    missing_path = tmp_path / "absent.csv"
    with pytest.raises(FileNotFoundError):
        load_raw_dataset(path=missing_path)


def test_load_raw_dataset_loads_existing_file(tmp_path):
    target = tmp_path / "brut.csv"
    acquire_project_data(path=target)
    result = load_raw_dataset(path=target)
    assert isinstance(result, DataAcquisitionResult)
    assert not result.dataframe.empty
    assert result.metadata["mode"] == "loaded_raw_data"


def test_data_source_description_has_required_keys():
    for key in ("provenance", "mode", "objectif", "url_reference"):
        assert key in DATA_SOURCE_DESCRIPTION
        assert DATA_SOURCE_DESCRIPTION[key]
