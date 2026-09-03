# Journal des transformations — education_prioritaire

Nombre d'étapes appliquées : 19

## Étape 1 — suppression_doublons

- Stratégie retenue : **aucune_action**
- Justification : Aucun doublon strict détecté ; aucune suppression nécessaire.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0

## Étape 2 — correction_type (variable : niveau)

- Stratégie retenue : **conversion_type**
- Justification : Le type observé ('str') ne correspondait pas au type attendu ('category') pour cette variable ; conversion appliquée pour garantir la cohérence des traitements statistiques ultérieurs.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - type_avant : str
    - type_apres : category

## Étape 3 — correction_type (variable : statut)

- Stratégie retenue : **conversion_type**
- Justification : Le type observé ('str') ne correspondait pas au type attendu ('category') pour cette variable ; conversion appliquée pour garantir la cohérence des traitements statistiques ultérieurs.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - type_avant : str
    - type_apres : category

## Étape 4 — correction_type (variable : academie)

- Stratégie retenue : **conversion_type**
- Justification : Le type observé ('str') ne correspondait pas au type attendu ('category') pour cette variable ; conversion appliquée pour garantir la cohérence des traitements statistiques ultérieurs.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - type_avant : str
    - type_apres : category

## Étape 5 — correction_type (variable : departement)

- Stratégie retenue : **conversion_type**
- Justification : Le type observé ('str') ne correspondait pas au type attendu ('category') pour cette variable ; conversion appliquée pour garantir la cohérence des traitements statistiques ultérieurs.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - type_avant : str
    - type_apres : category

## Étape 6 — harmonisation_categories (variable : statut)

- Stratégie retenue : **mapping_explicite**
- Justification : Les modalités observées ont été harmonisées vers une nomenclature unique afin d'éviter que des variantes d'écriture (casse, orthographe, abréviations) ne soient traitées comme des catégories distinctes.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - mapping_applique : {'REP': 'REP', 'REP+': 'REP+', 'Hors EP': 'Hors EP'}

## Étape 7 — harmonisation_categories (variable : niveau)

- Stratégie retenue : **mapping_explicite**
- Justification : Les modalités observées ont été harmonisées vers une nomenclature unique afin d'éviter que des variantes d'écriture (casse, orthographe, abréviations) ne soient traitées comme des catégories distinctes.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 5250
    - mapping_applique : {'CP': 'CP', 'CE1': 'CE1', 'CM1': 'CM1', 'CM2': 'CM2', '6e': '6e'}

## Étape 8 — traitement_valeurs_impossibles (variable : ips)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 160] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 160

## Étape 9 — traitement_valeurs_impossibles (variable : effectif_eleves)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [1, 60] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 1
    - borne_max : 60

## Étape 10 — traitement_valeurs_impossibles (variable : taille_moyenne_classe)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [1, 40] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 1
    - borne_max : 40

## Étape 11 — traitement_valeurs_impossibles (variable : score_francais)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 12 — traitement_valeurs_impossibles (variable : score_mathematiques)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 13 — traitement_valeurs_impossibles (variable : score_global)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 14 — traitement_valeurs_impossibles (variable : taux_maitrise_francais)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 15 — traitement_valeurs_impossibles (variable : taux_maitrise_mathematiques)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 16 — traitement_valeurs_impossibles (variable : variable_cible)

- Stratégie retenue : **aucune_action**
- Justification : Aucune valeur hors des bornes plausibles [0, 100] détectée pour cette variable.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
    - borne_min : 0
    - borne_max : 100

## Étape 17 — exclusion_variable (variable : nombre_classes)

- Stratégie retenue : **exclusion_de_la_variable**
- Justification : Variance nulle confirmée par le contrôle qualité (phase 7) : la variable ne prend qu'une seule valeur sur l'ensemble des observations. Conservée dans data/interim/ pour traçabilité, retirée de data/processed/ (jeu prêt pour analyse).
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0

## Étape 18 — revue_outliers_iqr (variable : score_francais, score_mathematiques, score_global, taux_maitrise_francais, taux_maitrise_mathematiques, variable_cible, effectif_eleves, taille_moyenne_classe)

- Stratégie retenue : **conservation_sans_modification**
- Justification : Valeurs aberrantes IQR (classées MINEUR en phase 7) toutes situées dans les plages plausibles métier. Représentent une variation naturelle et non des erreurs de saisie.
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0

## Étape 19 — controle_coherence_croisee (variable : statut, rep, rep_plus, education_prioritaire, score_global)

- Stratégie retenue : **aucune_action**
- Justification : Aucune incohérence détectée par le contrôle qualité (phase 7).
- Lignes avant : 5250 — Lignes après : 5250
- Valeurs modifiées / concernées : 0
