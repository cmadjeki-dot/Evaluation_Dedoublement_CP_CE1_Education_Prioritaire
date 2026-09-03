

from src.pipeline import build_group_summary, generate_synthetic_dataset


def test_generate_synthetic_dataset(tmp_path):
    path = tmp_path / "sample.csv"
    df = generate_synthetic_dataset(path)

    assert not df.empty
    assert set(["annee", "ecole_id", "rep_status", "niveau", "discipline", "score"]).issubset(df.columns)
    assert df["score"].between(0, 100).all()


def test_build_group_summary(tmp_path):
    path = tmp_path / "sample.csv"
    df = generate_synthetic_dataset(path)
    summary = build_group_summary(df)

    assert set(["rep_status", "niveau", "score_moyen"]).issubset(summary.columns)
    assert summary["score_moyen"].notna().all()
    assert summary["rep_status"].nunique() == 3
