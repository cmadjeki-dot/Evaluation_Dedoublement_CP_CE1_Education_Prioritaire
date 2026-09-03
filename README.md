# Evaluation_Dedoublement_CP_CE1_Education_Prioritaire

## Contexte

Le projet s’inscrit dans le cadre de l’évaluation des politiques éducatives et du pilotage des ressources dans l’enseignement élémentaire. Il vise à analyser, de manière rigoureuse et reproductible, la question du dédoublement de classes de CP et de CE1 en éducation prioritaire, en comparant les situations REP, REP+ et hors éducation prioritaire.

## Problématique

L’enjeu métier consiste à déterminer si une organisation pédagogique fondée sur un effet de dédoublement, ou sur une réduction sensible de la taille des classes, est associée à des performances scolaires supérieures, en particulier dans les établissements en difficulté. La question est de savoir si cette stratégie est corrélée à une meilleure progression des élèves, sans conclure hâtivement à un effet causal.

## Population étudiée

La population cible est constituée des classes de CP et de CE1 dans les établissements scolaires de l’éducation prioritaire et hors éducation prioritaire, sur une période temporelle de plusieurs années. L’étude prend en compte des établissements de taille variable et des situations de contexte socio-économique distinctes.

## Variable cible

La variable cible est la performance scolaire mesurée par un score de réussite ou d’acquisition, ainsi que, de manière complémentaire, le taux de maîtrise associé à la discipline concernée. Le projet se centre sur des indicateurs de niveau et de maîtrise, évalués par rapport au contexte de classe.

## Variables explicatives

Les principales variables explicatives sont :

- le statut REP / REP+ / Hors EP ;
- le niveau scolaire (CP, CE1, CM1, CM2, 6e) ;
- la taille de classe ;
- l’exposition au dédoublement ;
- l’année d’observation ;
- l’académie et le département ;
- l’effectif de l’école ;
- le niveau socio-économique ou indice de contexte (si disponible dans les données de référence).

## Objectifs

- comprendre la structure du problème métier et la logique de décision associée ;
- formaliser une question statistique exploitable ;
- identifier les variables pertinentes pour l’analyse ;
- construire un pipeline reproductible de préparation, analyse et restitution ;
- produire des indicateurs synthétiques et des visualisations lisibles ;
- préparer un cadre méthodologique fiable pour une étude plus poussée avec des données réelles.

## Méthodologie

Le projet suit une démarche structurée en plusieurs étapes :

1. cadrage métier et définition du problème statistique ;
2. acquisition ou génération d’un jeu de données cohérent ;
3. préparation et nettoyage des données ;
4. description statistique et contrôle qualité ;
5. modélisation et analyse spécialisée ;
6. calcul d’indicateurs de décision ;
7. restitution sous forme de tableaux, graphiques et rapport.

## Architecture du projet

```text
Evaluation_Dedoublement_CP_CE1_Education_Prioritaire
├── .github/
├── dashboard/
├── data/
│   ├── external/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── docs/
├── notebooks/
├── outputs/
│   ├── figures/
│   ├── logs/
│   ├── models/
│   ├── reports/
│   └── tables/
├── scripts/
├── site/
├── src/
│   ├── analysis/
│   ├── data/
│   ├── modeling/
│   ├── quality/
│   ├── reporting/
│   ├── utils/
│   └── visualization/
├── tests/
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
├── main.py
└── ...
```

## Installation

Prérequis :

- Python 3.12 ou supérieur
- Gestionnaire de packages pip
- Environnement virtuel recommandé

```bash
python -m venv .venv
. .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate # Windows
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement

```bash
python main.py
python -m pytest -q
```

Le lancement du projet permet de générer les données de travail, les tableaux synthétiques, les graphiques et le résumé analytique dans les dossiers d’output.

## Séquence des notebooks

La séquence prévue est la suivante :

1. `00_cadrage.ipynb` — cadrage métier et statistique
2. `01_generation_ou_acquisition_des_donnees.ipynb` — acquisition des données
3. `02_importation_et_description.ipynb` — import et description
4. `03_controle_qualite.ipynb` — contrôle qualité
5. `04_nettoyage.ipynb` — nettoyage des données
6. `05_analyse_descriptive.ipynb` — analyse descriptive
7. `06_modelisation.ipynb` — modélisation
8. `07_analyse_specialisee.ipynb` — analyse spécialisée
9. `08_analyse_longitudinale.ipynb` — analyse longitudinale
10. `09_analyse_causale.ipynb` — analyse causale
11. `10_indicateurs_decisionnels.ipynb` — indicateurs décisionnels
12. `11_restitution.ipynb` — restitution
13. `12_pipeline_complet.ipynb` — pipeline complet
14. `13_presentation_orale.ipynb` — préparation de la présentation

## Tests

Le projet inclut des tests de validation du pipeline principal dans le dossier `tests/`.

```bash
python -m pytest -q
```

## Dashboard

Le dossier `dashboard/` contient une application de type tableau de bord destinée à présenter les résultats de synthèse de manière lisible et exploitable.

## Résultats

Le projet est conçu pour produire :

- des tableaux de synthèse,
- des représentations visuelles des performances,
- des rapports de synthèse,
- des indicateurs utiles pour la décision et la communication.

À ce stade, les résultats doivent être interprétés comme des résultats de pipeline et de cadrage méthodologique, et non comme des conclusions définitives sans validation sur données réelles.

## Reproductibilité

La reproductibilité du projet repose sur :

- un environnement virtuel isolé,
- un fichier `requirements.txt` explicite,
- une configuration `pyproject.toml`,
- des scripts de génération et d’analyse cohérents,
- une organisation standardisée des données et des sorties.

## GitHub

Le projet est structuré pour être versionné de manière claire et lisible dans un dépôt GitHub, avec une séparation nette entre code, données, sorties, tests et documentation.

---

## Résumé de la question statistique

Le projet cherche à répondre à la question suivante :

- le dédoublement ou la réduction des effectifs de classe est-il associé à des performances scolaires plus élevées dans les contextes défavorisés, en particulier en REP ou REP+ ?

Cette question est formulée comme un objectif de recherche exploitable, sans supposer à l’avance un effet causal démontré.
