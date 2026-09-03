"""Tests des fonctions de nettoyage et transformation (src/data/cleaning.py)."""

import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import (
    IMPUTATION_STRATEGIES,
    TransformationJournal,
    TransformationStep,
    analyze_missing_values,
    compare_before_after,
    fix_column_types,
    handle_impossible_values,
    harmonize_categories,
    impute_missing_values,
    load_interim_dataset,
    load_processed_dataset,
    remove_duplicate_rows,
    save_interim_dataset,
    save_processed_dataset,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "annee": ["2020", "2020", "2021"],
            "statut": ["Hors EP", "Hors EP", "Rep"],
            "score": [55.0, 55.0, 999.0],
            "ips": [70.0, 70.0, np.nan],
        }
    )


def test_remove_duplicate_rows_drops_exact_duplicates(sample_df):
    result = remove_duplicate_rows(sample_df)
    assert len(result) == 2
    assert result.index.tolist() == [0, 1]


def test_remove_duplicate_rows_logs_to_journal(sample_df):
    journal = TransformationJournal(dataset_name="test")
    remove_duplicate_rows(sample_df, journal=journal)
    assert len(journal.steps) == 1
    assert journal.steps[0].action == "suppression_doublons"
    assert journal.steps[0].n_valeurs_modifiees == 1


def test_remove_duplicate_rows_no_duplicates_logs_no_action():
    df = pd.DataFrame({"a": [1, 2, 3]})
    journal = TransformationJournal(dataset_name="test")
    remove_duplicate_rows(df, journal=journal)
    assert journal.steps[0].strategie == "aucune_action"


def test_fix_column_types_converts_to_int64():
    df = pd.DataFrame({"annee": ["2020", "2021", "2022"]})
    result = fix_column_types(df, {"annee": "int64"})
    assert str(result["annee"].dtype) == "int64"


def test_fix_column_types_converts_to_category():
    df = pd.DataFrame({"statut": ["REP", "REP+", "Hors EP"]})
    result = fix_column_types(df, {"statut": "category"})
    assert str(result["statut"].dtype) == "category"


def test_fix_column_types_skips_missing_column():
    df = pd.DataFrame({"a": [1, 2]})
    result = fix_column_types(df, {"colonne_absente": "int64"})
    assert list(result.columns) == ["a"]


def test_fix_column_types_logs_transformation():
    df = pd.DataFrame({"annee": ["2020", "2021"]})
    journal = TransformationJournal(dataset_name="test")
    fix_column_types(df, {"annee": "int64"}, journal=journal)
    assert len(journal.steps) == 1
    assert journal.steps[0].action == "correction_type"


def test_harmonize_categories_applies_mapping():
    df = pd.DataFrame({"statut": ["Rep", "Rep+", "Hors EP"]})
    result = harmonize_categories(df, "statut", {"Rep": "REP", "Rep+": "REP+"})
    assert set(result["statut"]) == {"REP", "REP+", "Hors EP"}


def test_harmonize_categories_missing_column_returns_unchanged():
    df = pd.DataFrame({"a": [1]})
    result = harmonize_categories(df, "colonne_absente", {"x": "y"})
    assert list(result.columns) == ["a"]


def test_handle_impossible_values_marks_out_of_range_as_missing():
    df = pd.DataFrame({"score": [10.0, 999.0, 55.0]})
    result = handle_impossible_values(df, "score", (0, 100))
    assert result["score"].isna().sum() == 1
    assert result.loc[1, "score"] != result.loc[1, "score"]  # NaN


def test_handle_impossible_values_supprimer_lignes_strategy():
    df = pd.DataFrame({"score": [10.0, 999.0, 55.0]})
    result = handle_impossible_values(df, "score", (0, 100), strategy="supprimer_lignes")
    assert len(result) == 2
    assert 999.0 not in result["score"].values


def test_handle_impossible_values_no_impossible_values_no_change():
    df = pd.DataFrame({"score": [10.0, 50.0, 55.0]})
    result = handle_impossible_values(df, "score", (0, 100))
    assert result["score"].isna().sum() == 0


def test_analyze_missing_values_reports_counts_and_percentages():
    df = pd.DataFrame({"a": [1, None, 3, None], "b": [1, 2, 3, 4]})
    table = analyze_missing_values(df)
    assert table.loc["a", "n_manquants"] == 2
    assert table.loc["a", "pourcentage_manquant"] == 50.0
    assert table.loc["b", "n_manquants"] == 0


@pytest.mark.parametrize("strategy", ["moyenne", "mediane", "mode"])
def test_impute_missing_values_numeric_strategies_remove_all_na(strategy):
    df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
    result = impute_missing_values(df, "x", strategy, justification="test")
    assert result["x"].isna().sum() == 0


def test_impute_missing_values_suppression_strategy_drops_rows():
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    result = impute_missing_values(df, "x", "suppression", justification="test")
    assert len(result) == 2
    assert result["x"].isna().sum() == 0


def test_impute_missing_values_categorie_inconnu_for_categorical():
    df = pd.DataFrame({"cat": pd.Categorical(["a", None, "b"])})
    result = impute_missing_values(df, "cat", "categorie_inconnu", justification="test")
    assert result["cat"].isna().sum() == 0
    assert "Inconnu" in result["cat"].values


def test_impute_missing_values_imputation_par_groupe_requires_group_columns():
    df = pd.DataFrame({"groupe": ["a", "a", "b"], "x": [1.0, np.nan, 5.0]})
    with pytest.raises(ValueError):
        impute_missing_values(df, "x", "imputation_par_groupe", justification="test")


def test_impute_missing_values_imputation_par_groupe_fills_by_group():
    df = pd.DataFrame({"groupe": ["a", "a", "b", "b"], "x": [1.0, np.nan, 10.0, 12.0]})
    result = impute_missing_values(
        df, "x", "imputation_par_groupe", justification="test", group_columns=["groupe"]
    )
    assert result["x"].isna().sum() == 0
    assert result.loc[1, "x"] == 1.0  # médiane du groupe "a" (seule valeur non-nulle)


def test_impute_missing_values_no_missing_logs_no_action():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    journal = TransformationJournal(dataset_name="test")
    impute_missing_values(df, "x", "moyenne", justification="test", journal=journal)
    assert journal.steps[0].strategie == "aucune_action"


def test_impute_missing_values_rejects_unknown_strategy():
    df = pd.DataFrame({"x": [1.0, np.nan]})
    with pytest.raises(ValueError):
        impute_missing_values(df, "x", "strategie_inexistante", justification="test")


def test_all_documented_strategies_are_valid_members():
    strategies = (
        "suppression",
        "moyenne",
        "mediane",
        "mode",
        "categorie_inconnu",
        "imputation_par_groupe",
        "knn",
        "mice",
    )
    for strategy in strategies:
        assert strategy in IMPUTATION_STRATEGIES


def test_compare_before_after_reports_expected_columns():
    before = pd.DataFrame({"x": [1.0, 2.0, np.nan]})
    after = pd.DataFrame({"x": [1.0, 2.0, 1.5]})
    comparison = compare_before_after(before, after, columns=["x"])
    assert comparison.loc[0, "n_manquants_avant"] == 1
    assert comparison.loc[0, "n_manquants_apres"] == 0
    assert comparison.loc[0, "n_avant"] == 2
    assert comparison.loc[0, "n_apres"] == 3


def test_transformation_journal_log_and_to_markdown():
    journal = TransformationJournal(dataset_name="test")
    journal.log(
        TransformationStep(
            variable="x",
            action="test_action",
            strategie="test_strategie",
            justification="test",
            n_lignes_avant=10,
            n_lignes_apres=10,
            n_valeurs_modifiees=2,
        )
    )
    assert len(journal.steps) == 1
    markdown = journal.to_markdown()
    assert "test_action" in markdown
    assert "x" in markdown


def test_transformation_journal_save_writes_md_and_json(tmp_path):
    journal = TransformationJournal(dataset_name="test")
    journal.log(
        TransformationStep(
            variable="x",
            action="test_action",
            strategie="test_strategie",
            justification="test",
            n_lignes_avant=10,
            n_lignes_apres=10,
            n_valeurs_modifiees=2,
        )
    )
    paths = journal.save(tmp_path, "journal_test")
    assert paths["markdown"].exists()
    assert paths["json"].exists()


def test_save_and_load_interim_dataset_roundtrip(tmp_path, monkeypatch):
    import src.data.cleaning as cleaning_module

    monkeypatch.setattr(cleaning_module, "INTERIM_DIR", tmp_path)
    df = pd.DataFrame({"a": [1, 2, 3]})
    path = save_interim_dataset(df, "test_dataset")
    assert path.exists()
    assert path.name == "test_dataset_clean.csv"

    loaded = load_interim_dataset("test_dataset")
    pd.testing.assert_frame_equal(loaded, df)


def test_save_and_load_processed_dataset_roundtrip(tmp_path, monkeypatch):
    import src.data.cleaning as cleaning_module

    monkeypatch.setattr(cleaning_module, "PROCESSED_DIR", tmp_path)
    df = pd.DataFrame({"a": [1, 2, 3]})
    path = save_processed_dataset(df, "test_dataset")
    assert path.exists()
    assert path.name == "test_dataset_analysis_ready.csv"

    loaded = load_processed_dataset("test_dataset")
    pd.testing.assert_frame_equal(loaded, df)


def test_load_processed_dataset_raises_clear_error_if_missing(tmp_path, monkeypatch):
    import src.data.cleaning as cleaning_module

    monkeypatch.setattr(cleaning_module, "PROCESSED_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_processed_dataset("dataset_absent")
