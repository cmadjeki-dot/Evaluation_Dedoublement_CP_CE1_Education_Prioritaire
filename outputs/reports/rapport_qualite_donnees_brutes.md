# Rapport de contrôle qualité

Généré le : 2026-09-03T08:25:08.906631+00:00
Fichier analysé : C:\Users\admin\Desktop\PROJET STATISTIQUE PUBLIC B\data\raw\donnees_brutes_education_prioritaire.csv

## Vue d'ensemble

- Nombre de lignes : 5250
- Nombre de colonnes : 22
- Problèmes CRITIQUES : 0
- Problèmes IMPORTANTS : 1
- Problèmes MINEURS : 10

## Détail des problèmes détectés

### IMPORTANT

- **ZERO_VARIANCE** (variable : nombre_classes) — La variable 'nombre_classes' ne prend qu'une seule valeur (variance nulle). — observations concernées : 5250
    - valeur_unique : 2.0

### MINEUR

- **DUPLICATE_ROWS** — Lignes strictement identiques sur l'ensemble des colonnes. — observations concernées : 0
    - pourcentage : 0.0
- **DUPLICATE_IDENTIFIERS** (variable : annee, ecole_id, niveau) — Combinaisons d'identifiant logique (année, école, niveau) apparaissant plusieurs fois. — observations concernées : 0
    - colonnes_utilisees : ['annee', 'ecole_id', 'niveau']
- **OUTLIER_IQR** (variable : effectif_eleves) — Valeurs aberrantes détectées par la méthode IQR sur 'effectif_eleves'. — observations concernées : 10
    - borne_basse : 4.0
    - borne_haute : 36.0
    - pourcentage : 0.19
- **OUTLIER_IQR** (variable : taille_moyenne_classe) — Valeurs aberrantes détectées par la méthode IQR sur 'taille_moyenne_classe'. — observations concernées : 10
    - borne_basse : 3.055
    - borne_haute : 29.575
    - pourcentage : 0.19
- **OUTLIER_IQR** (variable : score_francais) — Valeurs aberrantes détectées par la méthode IQR sur 'score_francais'. — observations concernées : 7
    - borne_basse : 49.812
    - borne_haute : 108.433
    - pourcentage : 0.133
- **OUTLIER_IQR** (variable : score_mathematiques) — Valeurs aberrantes détectées par la méthode IQR sur 'score_mathematiques'. — observations concernées : 16
    - borne_basse : 46.095
    - borne_haute : 108.295
    - pourcentage : 0.305
- **OUTLIER_IQR** (variable : score_global) — Valeurs aberrantes détectées par la méthode IQR sur 'score_global'. — observations concernées : 8
    - borne_basse : 48.175
    - borne_haute : 108.135
    - pourcentage : 0.152
- **OUTLIER_IQR** (variable : taux_maitrise_francais) — Valeurs aberrantes détectées par la méthode IQR sur 'taux_maitrise_francais'. — observations concernées : 15
    - borne_basse : 50.62
    - borne_haute : 96.3
    - pourcentage : 0.286
- **OUTLIER_IQR** (variable : taux_maitrise_mathematiques) — Valeurs aberrantes détectées par la méthode IQR sur 'taux_maitrise_mathematiques'. — observations concernées : 15
    - borne_basse : 46.916
    - borne_haute : 94.026
    - pourcentage : 0.286
- **OUTLIER_IQR** (variable : variable_cible) — Valeurs aberrantes détectées par la méthode IQR sur 'variable_cible'. — observations concernées : 8
    - borne_basse : 48.175
    - borne_haute : 108.135
    - pourcentage : 0.152

## Décisions de correction

Aucune correction automatique n'a été appliquée à ce stade. Toute correction future devra être décidée explicitement dans le notebook de nettoyage (`04_nettoyage.ipynb`), et devra être justifiée et tracée (règle appliquée, nombre de lignes concernées, raison métier ou statistique).