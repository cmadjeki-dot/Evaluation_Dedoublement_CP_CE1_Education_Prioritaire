# Évaluation du dédoublement CP/CE1 en éducation prioritaire

[![CI/CD](https://github.com/cmadjeki-dot/Evaluation_Dedoublement_CP_CE1_Education_Prioritaire/actions/workflows/ci.yml/badge.svg)](https://github.com/cmadjeki-dot/Evaluation_Dedoublement_CP_CE1_Education_Prioritaire/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Projet data/statistique reproductible évaluant si le dédoublement des classes de CP et CE1 en éducation prioritaire (REP/REP+) est associé à de meilleures performances scolaires, à partir de données simulées.

## Contexte

Le projet s'inscrit dans le cadre de l'évaluation des politiques éducatives et du pilotage des ressources dans l'enseignement élémentaire. Il analyse, de manière rigoureuse et reproductible, la question du dédoublement de classes de CP et de CE1 en éducation prioritaire, en comparant les situations REP, REP+ et hors éducation prioritaire, sur la période 2017-2023.

## Problématique

Une organisation pédagogique fondée sur le dédoublement des classes (ou une réduction sensible de la taille des classes) est-elle associée à des performances scolaires supérieures, en particulier dans les établissements en difficulté (REP/REP+) ? Le projet répond à cette question par une démarche **associative et non causale** : aucune conclusion d'effet causal n'est présentée sans validation méthodologique adaptée (voir [Limites](#limites)).

> ⚠️ Les données utilisées sont **simulées** (graine fixe, voir [src/data/acquisition.py](/src/data/acquisition.py)). Les chiffres illustrent la démarche méthodologique et ne constituent pas des statistiques officielles.

## Résultats principaux

Chiffres extraits de [outputs/tables/indicateurs_decisionnels.csv](/outputs/tables/indicateurs_decisionnels.csv) et [docs/rapport_final.md](/docs/rapport_final.md) :

| Indicateur | Valeur | Interprétation |
|---|---|---|
| Score global moyen | **78.23 / 100** | Niveau moyen de performance sur l'ensemble des observations (2017-2023). |
| Score moyen par statut | Hors EP 81.71 · REP 75.17 · REP+ 71.46 | Hiérarchie de performance nette entre statuts. |
| Écart REP+ vs Hors EP | **-10.25 pts** (t = -29.7, p < 1e-150) | Écart statistiquement significatif, mais associatif — pas de preuve causale. |
| Évolution de l'écart REP+ vs Hors EP (2017→2023) | **-1.18 pt** | Léger creusement de l'écart sur la période. |
| Part d'observations dédoublées | 33.5 % | Intensité d'exposition au dispositif dans le panel. |
| R² du modèle explicatif (OLS) | **0.703** | Bonne capacité explicative globale des variables retenues. |
| RMSE du modèle OLS | 5.71 pts | Erreur moyenne de prédiction, en échantillon. |
| ICC effet école (modèle mixte) | 0.007 | Très faible variance inter-écoles après contrôle des autres variables. |
| Analyse causale (différence-de-différences) | **Non applicable** | Statuts des écoles trop instables dans le temps pour isoler un groupe traité stable (voir `notebooks/09`). |

Détails complets, tests statistiques et coefficients du modèle : [docs/rapport_final.md](/docs/rapport_final.md).

## Architecture

```text
PROJET STATISTIQUE PUBLIC B
├── .github/workflows/       # CI (tests + lint) et CD (site + artefacts)
├── dashboard/app.py          # Application Streamlit interactive
├── data/                     # raw / interim / processed / external
├── docs/rapport_final.md     # Rapport de synthèse généré automatiquement
├── notebooks/                 # 00 à 13, séquence complète d'analyse
├── outputs/                  # figures, tables, models, reports, logs
├── scripts/                  # génération figures/tables/rapport, pipeline, site
├── site/                     # Site statique (GitHub Pages)
├── src/                       # analysis, data, modeling, quality, reporting,
│                              # utils, visualization
├── tests/                     # tests pytest
├── LICENSE
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Méthodologie

1. Cadrage métier et définition de la question statistique (`notebooks/00`).
2. Génération/acquisition des données simulées (`notebooks/01`).
3. Import, description et contrôle qualité (`notebooks/02`, `notebooks/03`).
4. Nettoyage des données (`notebooks/04`).
5. Analyse descriptive (`notebooks/05`).
6. Modélisation : régression OLS et modèle mixte (`notebooks/06`).
7. Analyses spécialisées, longitudinale et causale (`notebooks/07`, `08`, `09`).
8. Indicateurs décisionnels et restitution (`notebooks/10`, `11`).
9. Pipeline complet et présentation orale (`notebooks/12`, `13`).

## Installation

Prérequis : Python **>= 3.14** (voir `pyproject.toml`).

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# . .venv/bin/activate         # Linux/macOS
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Reproduire le projet

```bash
python -m pytest -q      # tests unitaires
ruff check                # qualité de code
```

Toutes les dépendances sont figées dans [requirements.txt](/requirements.txt) et déclarées dans [pyproject.toml](/pyproject.toml) pour un environnement isolé et reproductible.

## Exécuter le pipeline

```bash
python scripts/run_pipeline.py
```

Le pipeline enchaîne automatiquement : données brutes → contrôle qualité → nettoyage → données `processed` → analyses → modèles → indicateurs → figures → tableaux → rapport → site statique → validation des artefacts. Il s'arrête et signale explicitement l'étape en cause en cas d'échec, et écrit ses logs dans `outputs/logs/`.

## Consulter les résultats

### Dashboard

Tableau de bord interactif Streamlit (testé : titre, filtres, KPI, graphiques, tableaux, téléchargements, sans exception) :
👉 **[Dashboard en ligne](https://evaluationdedoublementcpce1educationprioritaire-dsqnzzhphhk9qw.streamlit.app/)**

En local : `streamlit run dashboard/app.py`

### Site

Site statique de restitution (testé : accueil, KPI, figures, tableaux, rapport, liens) :
👉 **[Site en ligne](https://cmadjeki-dot.github.io/Evaluation_Dedoublement_CP_CE1_Education_Prioritaire/)**

### Rapport

[docs/rapport_final.md](/docs/rapport_final.md) — synthèse méthodologique, chiffres clés, tests statistiques, limites.

### Figures

[outputs/figures/](/outputs/figures) — distributions, comparaisons par statut, évolutions temporelles.

### Tableaux

[outputs/tables/](/outputs/tables) — statistiques descriptives, coefficients du modèle, indicateurs décisionnels.

### Notebooks

Séquence complète disponible dans [notebooks/](/notebooks) :

`00_cadrage` · `01_generation_ou_acquisition_des_donnees` · `02_importation_et_description` · `03_controle_qualite` · `04_nettoyage` · `05_analyse_descriptive` · `06_modelisation` · `07_analyse_specialisee` · `08_analyse_longitudinale` · `09_analyse_causale` · `10_indicateurs_decisionnels` · `11_restitution` · `12_pipeline_complet` · `13_presentation_orale`

## Tests

```bash
python -m pytest -q
```

Les tests couvrent le chargement des données, la structure des jeux de données, les fonctions de transformation, les outputs générés, les modèles, les chemins du projet, le pipeline complet, les imports et les dépendances. Exécutés automatiquement à chaque push/pull request via la CI GitHub Actions.

## Technologies

Python · pandas · numpy · scipy · statsmodels · scikit-learn · openpyxl · matplotlib · plotly · seaborn · jupyterlab / notebook / ipykernel · pytest · ruff · streamlit · GitHub Actions (CI/CD) · GitHub Pages · Streamlit Community Cloud.

## Compétences démontrées

- Cadrage d'une question statistique métier et formalisation d'objectifs mesurables.
- Conception d'une architecture de projet data science industrielle et reproductible (environnement isolé, `pyproject.toml`, `requirements.txt`).
- Pipeline de données bout-en-bout (acquisition → qualité → nettoyage → analyse → modélisation → restitution) automatisé et auditable.
- Modélisation statistique (OLS, modèle mixte) avec évaluation (R², RMSE, ICC) et tests d'hypothèses.
- Distinction rigoureuse entre résultats associatifs et effets causaux, avec diagnostic explicite de faisabilité d'une différence-de-différences.
- Génération automatisée d'artefacts (figures, tableaux, rapport) avec vérifications d'intégrité.
- Tests automatisés (pytest) et qualité de code (ruff) intégrés en CI/CD (GitHub Actions).
- Restitution double : dashboard interactif (Streamlit) et site statique (GitHub Pages), déployés publiquement et vérifiés depuis des URL publiques.

## Limites

- Les données sont **simulées** : les valeurs numériques ne doivent pas être citées comme des statistiques officielles de la DEPP.
- Les analyses associatives (corrélation, régression observationnelle) ne démontrent pas de lien causal.
- La faisabilité d'une différence-de-différences dépend de la structure de déploiement réellement disponible dans les données ; elle a été jugée **non applicable** ici (voir `notebooks/09` et `docs/rapport_final.md`).
- Les métriques du modèle OLS (R², RMSE) sont mesurées en échantillon (in-sample), non validées sur un jeu de données externe.

## Licence

Projet distribué sous licence [MIT](/LICENSE).
