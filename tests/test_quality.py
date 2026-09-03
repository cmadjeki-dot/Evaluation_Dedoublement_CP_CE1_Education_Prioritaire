"""Tests des fonctions de contrôle qualité (src/quality/checks.py)."""

import numpy as np
import pandas as pd
import pytest

from src.quality.checks import (
    SEVERITY_CRITIQUE,
    SEVERITY_IMPORTANT,
    SEVERITY_MINEUR,
    QualityIssue,
    QualityReport,
    check_duplicate_identifiers,
    check_duplicate_rows,
    check_impossible_values,
    check_missing_values,
    check_outliers_iqr,
    check_type_consistency,
    check_unexpected_categories,
    render_report_markdown,
    run_full_quality_check,
    save_quality_report,
)


def test_check_duplicate_rows_detects_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    issue = check_duplicate_rows(df)
    assert issue.n_affected == 1
    assert issue.severity == SEVERITY_IMPORTANT


def test_check_duplicate_rows_no_duplicates_is_minor():
    df = pd.DataFrame({"a": [1, 2, 3]})
    issue = check_duplicate_rows(df)
    assert issue.n_affected == 0
    assert issue.severity == SEVERITY_MINEUR


def test_check_duplicate_identifiers_detects_duplicate_keys():
    df = pd.DataFrame({"annee": [2020, 2020, 2021], "ecole_id": [1, 1, 2], "niveau": ["CP", "CP", "CE1"]})
    issue = check_duplicate_identifiers(df)
    assert issue.n_affected == 2
    assert issue.severity == SEVERITY_CRITIQUE


def test_check_duplicate_identifiers_missing_key_columns_returns_minor():
    df = pd.DataFrame({"x": [1, 2, 3]})
    issue = check_duplicate_identifiers(df)
    assert issue.severity == SEVERITY_MINEUR
    assert issue.n_affected == 0


def test_check_missing_values_severity_scales_with_percentage():
    df = pd.DataFrame({"peu_manquant": [1, 2, 3, 4, None] * 20, "beaucoup_manquant": [None] * 25 + list(range(75))})
    issues = check_missing_values(df)
    by_var = {issue.variable: issue for issue in issues}
    assert by_var["peu_manquant"].n_affected == 20
    assert by_var["beaucoup_manquant"].severity == SEVERITY_CRITIQUE


def test_check_missing_values_no_missing_returns_no_issues():
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert check_missing_values(df) == []


def test_check_type_consistency_detects_wrong_type():
    df = pd.DataFrame({"annee": ["2020", "2021"]})
    issues = check_type_consistency(df, expected_types={"annee": "integer"})
    assert len(issues) == 1
    assert issues[0].variable == "annee"


def test_check_type_consistency_correct_type_no_issue():
    df = pd.DataFrame({"annee": [2020, 2021]})
    issues = check_type_consistency(df, expected_types={"annee": "integer"})
    assert issues == []


def test_check_unexpected_categories_detects_unknown_modality():
    df = pd.DataFrame({"statut": ["Hors EP", "REP", "INCONNU_STATUT"]})
    issues = check_unexpected_categories(df, expected_categories={"statut": {"Hors EP", "REP", "REP+"}})
    assert len(issues) == 1
    assert "INCONNU_STATUT" in issues[0].details["modalites_inattendues"]


def test_check_unexpected_categories_all_known_no_issue():
    df = pd.DataFrame({"statut": ["Hors EP", "REP"]})
    issues = check_unexpected_categories(df, expected_categories={"statut": {"Hors EP", "REP", "REP+"}})
    assert issues == []


def test_check_impossible_values_detects_out_of_range():
    df = pd.DataFrame({"score": [50.0, 999.0, -5.0]})
    issues = check_impossible_values(df, plausible_ranges={"score": (0, 100)})
    assert len(issues) == 1
    assert issues[0].n_affected == 2


def test_check_outliers_iqr_detects_extreme_values():
    values = [48.0, 49.0, 50.0, 51.0, 52.0] * 4 + [5000.0]
    df = pd.DataFrame({"x": values})
    issues = check_outliers_iqr(df, columns=["x"])
    assert len(issues) == 1
    assert issues[0].n_affected == 1


def test_check_outliers_iqr_constant_column_no_issue():
    df = pd.DataFrame({"x": [10.0] * 10})
    issues = check_outliers_iqr(df, columns=["x"])
    assert issues == []


def test_quality_issue_to_dict_roundtrip():
    issue = QualityIssue(
        code="TEST",
        severity=SEVERITY_MINEUR,
        variable="x",
        description="desc",
        n_affected=1,
    )
    data = issue.to_dict()
    assert data["code"] == "TEST"
    assert data["severity"] == SEVERITY_MINEUR
    assert data["n_affected"] == 1


def test_quality_report_summary_counts():
    report = QualityReport(generated_at="now", n_rows=10, n_columns=2, columns=["a", "b"])
    report.add(QualityIssue(code="A", severity=SEVERITY_CRITIQUE, variable="a", description="", n_affected=1))
    report.add(QualityIssue(code="B", severity=SEVERITY_MINEUR, variable="b", description="", n_affected=1))
    counts = report.summary_counts()
    assert counts[SEVERITY_CRITIQUE] == 1
    assert counts[SEVERITY_MINEUR] == 1
    assert counts[SEVERITY_IMPORTANT] == 0


@pytest.fixture
def messy_dataframe():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "annee": [2020] * 30,
            "ecole_id": list(range(1, 31)),
            "niveau": ["CP"] * 30,
            "statut": ["Hors EP"] * 29 + ["STATUT_INVALIDE"],
            "score": list(rng.normal(60, 5, 29)) + [999.0],
        }
    )
    # Introduire un doublon d'identifiant logique et une valeur manquante.
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    df.loc[1, "score"] = np.nan
    return df


def test_run_full_quality_check_returns_populated_report(messy_dataframe):
    report = run_full_quality_check(messy_dataframe)
    assert isinstance(report, QualityReport)
    assert report.n_rows == len(messy_dataframe)
    assert len(report.issues) > 0
    # Le rapport doit détecter au moins une anomalie critique (identifiant dupliqué, valeur impossible).
    assert report.summary_counts()[SEVERITY_CRITIQUE] >= 1


def test_render_report_markdown_contains_summary(messy_dataframe):
    report = run_full_quality_check(messy_dataframe)
    markdown = render_report_markdown(report)
    assert "CRITIQUE" in markdown or SEVERITY_CRITIQUE in markdown
    assert str(report.n_rows) in markdown


def test_save_quality_report_writes_files(tmp_path, messy_dataframe):
    report = run_full_quality_check(messy_dataframe)
    paths = save_quality_report(report, tmp_path, dataset_path="dummy.csv")
    assert paths["markdown"].exists()
    assert paths["json"].exists()
    assert paths["markdown"].read_text(encoding="utf-8")
    assert paths["json"].read_text(encoding="utf-8")


def test_run_full_quality_check_never_mutates_input_dataframe(messy_dataframe):
    original = messy_dataframe.copy(deep=True)
    run_full_quality_check(messy_dataframe)
    pd.testing.assert_frame_equal(messy_dataframe, original)
