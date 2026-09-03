# Rapport final

*Document généré automatiquement le 2026-09-03 12:25 par `scripts/generate_report.py`, à partir des tables réellement calculées dans `outputs/tables/`.*

## Objectif
Ce document centralise la synthèse méthodologique et les résultats clés du projet portant sur l'effet du dédoublement des classes de CP/CE1 en éducation prioritaire sur les performances scolaires.

## Périmètre
- Analyse du dédoublement des classes de CP et CE1 en éducation prioritaire.
- Comparaison REP, REP+ et hors éducation prioritaire.
- Suivi des performances à court, moyen et long terme (CP → CE1 → CM1 → CM2 → 6e).
- **Données simulées** (seed fixe, voir `src/data/acquisition.py`) : les résultats illustrent la démarche méthodologique et ne constituent pas des statistiques officielles.

## Méthodologie
1. Collecte et validation des données (`notebooks/01`, `notebooks/02`).
2. Contrôle qualité et nettoyage (`notebooks/03`, `notebooks/04`).
3. Analyse descriptive (`notebooks/05`).
4. Modélisation (OLS, modèle mixte) et analyses spécialisées (`notebooks/06`, `notebooks/07`).
5. Analyses longitudinale et causale (`notebooks/08`, `notebooks/09`).
6. Indicateurs décisionnels et restitution (`notebooks/10`, `notebooks/11`).

## Chiffres clés

- Score global moyen (variable cible) : **78.23 / 100** (moyenne des moyennes par statut).
  - Hors EP : moyenne = 81.71, effectif = 2940, écart-type = 10.29.
  - REP : moyenne = 75.17, effectif = 1460, écart-type = 8.94.
  - REP+ : moyenne = 71.46, effectif = 850, écart-type = 8.42.

### Tests de différence entre statuts (vs Hors EP)

| Statut comparé | Référence | Différence de moyennes | Statistique t | p-valeur | Significatif (5%) |
|---|---|---|---|---|---|
| REP+ | Hors EP | -10.25 | -29.669 | 2.04e-155 | Oui |
| REP | Hors EP | -6.53 | -21.689 | 1.25e-97 | Oui |

### Modèle explicatif (OLS)

Le modèle OLS comporte 9 coefficients estimés (constante + effets des variables explicatives encodées). Le détail complet (coefficient, erreur standard, statistique t, p-valeur, IC 95%) est disponible dans `outputs/tables/06_coefficients_ols.csv`. Les métriques de performance globales (R², RMSE) figurent dans la table des indicateurs décisionnels ci-dessous.

### Tendance temporelle par statut

| Statut | Pente (points/an) |
|---|---|
| REP | 1.068 |
| REP+ | 0.836 |
| Hors EP | 0.811 |

### Faisabilité d'une analyse causale (différence-de-différences)

- **Applicable** : Non
- Part des écoles avec changement de statut dans le temps : 100.0 %
- Exposition moyenne au dédoublement (CP/CE1) : 33.5 %
- Exposition moyenne au dédoublement (autres niveaux) : 33.5 %
- Raisons de non-applicabilité :
  - Les statuts des écoles varient fortement dans le temps (changement annuel fréquent), ce qui invalide l'interprétation d'un groupe traité stable.
  - L'exposition au dédoublement n'est pas spécifique à CP/CE1 dans ces données (écart CP/CE1 vs autres niveaux trop faible).

## Indicateurs décisionnels

La table complète (nom, définition, formule, valeur, unité, population, interprétation, limites, utilisation possible) est disponible dans `outputs/tables/indicateurs_decisionnels.csv`. Extrait :

| Indicateur | Valeur | Unité | Interprétation |
|---|---|---|---|
| Score global moyen | 78.2311 | points sur 100 | Niveau moyen de performance globale du système observé. |
| Écart REP+ vs Hors EP | -10.2491 | points sur 100 | Mesure brute de l'inégalité de performance entre extrêmes de statut. |
| Tendance annuelle Hors EP | 0.8113 | points/an | Variation moyenne annuelle du score Hors EP. |
| Tendance annuelle REP+ | 0.8365 | points/an | Variation moyenne annuelle du score REP+. |
| Évolution de l'écart REP+ vs Hors EP (2017→2023) | -1.1808 | points sur 100 | Négatif = creusement de l'écart en défaveur de REP+. |
| Part d'observations dédoublées | 0.3352 | proportion (0-1) | Mesure l'intensité d'exposition au dédoublement dans le panel. |
| RMSE modèle explicatif OLS | 5.7072 | points sur 100 | Ordre de grandeur de l'erreur moyenne de prédiction du modèle. |
| R² modèle explicatif OLS | 0.7030 | proportion (0-1) | Capacité explicative globale des variables retenues. |
| ICC effet école (modèle mixte) | 0.0068 | proportion (0-1) | Faible valeur = faible surcroît d'information école après contrôles. |

## Limites générales
- Les données sont simulées : les valeurs numériques ne doivent pas être citées comme des statistiques officielles de la DEPP.
- Les analyses associatives (corrélation, régression observationnelle) ne démontrent pas de lien causal.
- La faisabilité d'une différence-de-différences dépend de la structure de déploiement effectivement disponible dans les données (voir notebook 09).

## Artefacts associés
- Figures : `outputs/figures/`
- Tables : `outputs/tables/`
- Modèles : `outputs/models/`
- Notebooks source : `notebooks/00` à `notebooks/11`
