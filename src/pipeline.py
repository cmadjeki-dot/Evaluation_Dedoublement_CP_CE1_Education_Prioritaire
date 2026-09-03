from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns

from src.utils.paths import DATA_DIR, FIGURES_DIR, OUTPUT_DIR, REPORTS_DIR, TABLES_DIR, ensure_directory, ensure_project_directories

matplotlib.use("Agg")
import matplotlib.pyplot as plt

GRADE_ORDER = ["CP", "CE1", "CM1", "CM2", "6e"]
REP_STATUS_ORDER = ["Hors EP", "REP", "REP+"]
DISCIPLINE_ORDER = ["Français", "Mathématiques"]


def generate_synthetic_dataset(path: Path) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    years = range(2018, 2025)
    school_ids = range(1, 181)
    academies = ["Paris", "Lyon", "Lille", "Bordeaux", "Nantes"]
    departments = ["Ain", "Bas-Rhin", "Bouches-du-Rhône", "Gironde", "Hérault", "Loire", "Maine-et-Loire", "Moselle", "Nord", "Paris", "Puy-de-Dôme", "Saône-et-Loire"]

    rows = []
    for year in years:
        for school_id in school_ids:
            rep_status = rng.choice(REP_STATUS_ORDER, p=[0.55, 0.30, 0.15])
            academy = academies[(school_id + year) % len(academies)]
            department = departments[(school_id + year) % len(departments)]
            school_size = int(round({"Hors EP": 24, "REP": 20, "REP+": 17}[rep_status] + rng.normal(0, 3)))
            school_size = max(12, min(32, school_size))
            students_count = int(round(school_size * rng.uniform(0.9, 1.2)))
            ips = float(rng.normal(0, 12))

            for grade in GRADE_ORDER:
                for discipline in DISCIPLINE_ORDER:
                    class_size = int(round(school_size + rng.normal(0, 2.5)))
                    class_size = max(12, min(34, class_size))
                    exposition_dedoublement = int(rep_status in ["REP", "REP+"] and class_size <= 18)
                    baseline = {"CP": 58, "CE1": 60, "CM1": 63, "CM2": 66, "6e": 69}[grade]
                    discipline_bonus = {"Français": 4, "Mathématiques": 1}[discipline]
                    rep_bonus = {"Hors EP": 10, "REP": -4, "REP+": -12}[rep_status]
                    year_trend = (year - 2018) * 1.1
                    grade_trend = {"CP": 0, "CE1": 2, "CM1": 5, "CM2": 7, "6e": 9}[grade]
                    exposure_gain = 9 if exposition_dedoublement else 0
                    size_penalty = max(0, class_size - 18) * 0.9
                    score = baseline + discipline_bonus + rep_bonus + year_trend + grade_trend + exposure_gain - size_penalty + ips * 0.12 + rng.normal(0, 4.5)
                    score = max(0, min(100, score))
                    mastery_rate = min(100, max(0, 0.68 * score + 15 + rng.normal(0, 5)))

                    rows.append(
                        {
                            "annee": year,
                            "ecole_id": school_id,
                            "academie": academy,
                            "departement": department,
                            "rep_status": rep_status,
                            "niveau": grade,
                            "discipline": discipline,
                            "taille_classe": class_size,
                            "effectif_ecole": students_count,
                            "ips_ecole": round(ips, 2),
                            "exposition_dedoublement": exposition_dedoublement,
                            "score": round(float(score), 2),
                            "taux_maitrise": round(float(mastery_rate), 2),
                        }
                    )

    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def load_or_generate_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return generate_synthetic_dataset(path)
    return pd.read_csv(path)


def build_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["rep_status", "niveau"], as_index=False)
        .agg(score_moyen=("score", "mean"), taille_classe_moyenne=("taille_classe", "mean"), taux_maitrise_moyen=("taux_maitrise", "mean"))
        .sort_values(["rep_status", "niveau"], ascending=[True, True])
        .reset_index(drop=True)
    )


def build_year_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["annee", "rep_status"], as_index=False)
        .agg(score_moyen=("score", "mean"), taille_classe_moyenne=("taille_classe", "mean"))
        .sort_values(["rep_status", "annee"])\
        .reset_index(drop=True)
    )


def build_exposure_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("exposition_dedoublement", as_index=False)
        .agg(score_moyen=("score", "mean"), effectif=("score", "size"))
        .rename(columns={"exposition_dedoublement": "classe_dedoublee"})
    )


def plot_group_comparison(summary: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(11, 6))
    sns.barplot(data=summary, x="niveau", y="score_moyen", hue="rep_status", order=GRADE_ORDER)
    plt.title("Score moyen par niveau et statut REP")
    plt.ylabel("Score moyen")
    plt.xlabel("Niveau")
    plt.legend(title="Statut")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_year_trend(trend: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(11, 6))
    for rep_status, group in trend.groupby("rep_status"):
        plt.plot(group["annee"], group["score_moyen"], marker="o", label=rep_status)
    plt.title("Évolution du score moyen par année")
    plt.ylabel("Score moyen")
    plt.xlabel("Année")
    plt.legend(title="Statut")
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def plot_class_size_effect(df: pd.DataFrame, output_path: Path) -> None:
    ordered = df[["taille_classe", "score"]].sort_values("taille_classe").reset_index(drop=True)
    coeffs = np.polyfit(ordered["taille_classe"], ordered["score"], 1)
    trend_line = np.poly1d(coeffs)

    plt.figure(figsize=(10, 6))
    plt.scatter(df["taille_classe"], df["score"], alpha=0.25, s=18)
    xs = np.linspace(df["taille_classe"].min(), df["taille_classe"].max(), 200)
    plt.plot(xs, trend_line(xs), color="darkred", linewidth=2, label=f"Tendance: {coeffs[0]:.2f}x + {coeffs[1]:.2f}")
    plt.title("Relation entre taille de classe et score")
    plt.xlabel("Taille de classe")
    plt.ylabel("Score")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def write_report(summary: pd.DataFrame, trend: pd.DataFrame, exposure_summary: pd.DataFrame, output_path: Path) -> None:
    best_group = summary.loc[summary["score_moyen"].idxmax()]
    rep_plus_mean = summary.loc[summary["rep_status"] == "REP+", "score_moyen"].mean()
    hors_ep_mean = summary.loc[summary["rep_status"] == "Hors EP", "score_moyen"].mean()
    difference = hors_ep_mean - rep_plus_mean
    exposure_gain = (
        float(exposure_summary.loc[exposure_summary["classe_dedoublee"] == 1, "score_moyen"].iloc[0])
        - float(exposure_summary.loc[exposure_summary["classe_dedoublee"] == 0, "score_moyen"].iloc[0])
    )

    lines = [
        "Rapport synthétique - Evaluation du dédoublement des classes",
        "========================================================",
        f"Meilleur groupe observé : {best_group['rep_status']} - {best_group['niveau']} (score moyen : {best_group['score_moyen']:.2f})",
        f"Écart moyen entre Hors EP et REP+ : {difference:.2f} points",
        f"Gain moyen associé à l'exposition au dédoublement : {exposure_gain:.2f} points",
        "",
        "Résumé des résultats :",
        "- Le dédoublement est associé à des performances supérieures lorsque les classes restent compactes.",
        "- Les écarts de performance restent visibles entre les zones REP/REP+ et hors éducation prioritaire.",
        "- La progression temporelle est positive sur la période étudiée mais n'est pas interprétée comme un effet causal pur.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    directories = ensure_project_directories()
    ensure_directory(DATA_DIR)
    ensure_directory(OUTPUT_DIR)
    ensure_directory(FIGURES_DIR)
    ensure_directory(TABLES_DIR)
    ensure_directory(REPORTS_DIR)

    raw_data_path = DATA_DIR / "etablissements_performance_synthese.csv"
    df = load_or_generate_data(raw_data_path)

    summary = build_group_summary(df)
    trend = build_year_trend(df)
    exposure_summary = build_exposure_summary(df)

    summary_path = TABLES_DIR / "score_par_groupe.csv"
    trend_path = TABLES_DIR / "score_par_annee.csv"
    summary.to_csv(summary_path, index=False)
    trend.to_csv(trend_path, index=False)

    plot_group_comparison(summary, FIGURES_DIR / "score_par_groupe.png")
    plot_year_trend(trend, FIGURES_DIR / "score_par_annee.png")
    plot_class_size_effect(df, FIGURES_DIR / "score_par_taille_classe.png")
    write_report(summary, trend, exposure_summary, REPORTS_DIR / "rapport_resume.txt")

    print(f"Données générées : {len(df)} lignes")
    print(f"Fichier source : {raw_data_path}")
    print(f"Résumé : {summary_path}")
    print(f"Graphiques produits dans : {FIGURES_DIR}")
    print(f"Rapport produit dans : {REPORTS_DIR}")
    print(f"Répertoire projet : {directories['project_root']}")


if __name__ == "__main__":
    main()
