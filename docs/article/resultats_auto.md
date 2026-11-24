# Tableaux de résultats (générés automatiquement)

Fichier produit par `scripts/tableaux_resultats.py` : **ne pas modifier à la main**.
Les chiffres viennent de `outputs/qcm/` et de `data/processed/`. Les tableaux 2 à 8
et 11 contiennent une ligne par méthode ; la ligne `llm` n'apparaît qu'une fois
l'étape 5 exécutée sur GPU.

## Tableau 1 — Corpus et passages

| index | Titre | Auteur | Format | Pages | Mots brut | Mots nettoyés | % retiré | Passages | Mots/passage | Tokens max |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Programmation en langage C | Anne Canteaut (INRIA) | polycopié LaTeX | 133 | 36361 | 23243 | 36,1 | 130 | 164 | 452 |
| C2 | Le langage C | Patrick Trau | polycopié | 71 | 20292 | 12452 | 38,6 | 81 | 151 | 458 |
| C3 | Programmation C | M. E. Elhdhili, H. Boucetta | polycopié Word | 76 | 21115 | 13247 | 37,3 | 88 | 134 | 383 |
| C4 | Programmation en langage C | M. Qbadou (ENSET Mohammedia), 2022/2023 | polycopié Word | 68 | 11764 | 5663 | 51,9 | 34 | 127 | 392 |
| C5 | Initiation au langage C | non indiqué | polycopié LaTeX | 52 | 14726 | 8145 | 44,7 | 55 | 137 | 448 |
| C6 | Cours de langage C | Jacquelin Charbonnel (CNRS) | diapositives | 60 | 10126 | 3730 | 63,2 | 27 | 114 | 445 |
| Total | Total | 6 cours |  | 460 | 114384 | 66480 | 41,9 | 415 | 145 | 458 |

## Tableau 2 — Couverture et rendement par méthode
> QCM du LLM absents (étape 5 non exécutée sur GPU) : la comparaison base / LLM reste à compléter.

| Méthode | Passages testés | QCM produits | Couverture (%) | Acceptés | Taux d'acceptation (%) | QCM acceptés / passages (%) |
|---|---|---|---|---|---|---|
| base | 120 | 97 | 80,8 | 61 | 62,9 | 50,8 |

## Tableau 3 — Défauts de forme détectés (% des QCM de la méthode)

| Méthode | F1 | F2 | F3 | F4 | F5 | F6 | F7 | Conformes (%) |
|---|---|---|---|---|---|---|---|---|
| base | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 99 |

## Tableau 4 — Taux de passage de chaque test (% des QCM)

| Méthode | V1 répondabilité | V2 bonne réponse unique | V3 aucun distracteur correct | V1 et V2 et V3 |
|---|---|---|---|---|
| base | 96,9 | 89,7 | 69,1 | 62,9 |

## Tableau 5 — Cascade des rejets (nombre de QCM)

| Méthode | forme (F1–F7) | V1 | V2 | V3 | accepté |
|---|---|---|---|---|---|
| base | 1 | 3 | 9 | 23 | 61 |

## Tableau 6 — Typologie des rejets (nombre de QCM)

| Catégorie | base | Total |
|---|---|---|
| texte source dégradé | 1 | 1 |
| défaut de forme | 1 | 1 |
| réponse introuvable | 3 | 3 |
| bonne réponse non confirmée | 8 | 8 |
| distracteur proche de la réponse | 21 | 21 |
| distracteur confirmé sans être proche | 2 | 2 |
| Total | 36 | 36 |

## Tableau 7 — Ablation des contrôles du filtre (taux d'acceptation)

| Variante | % acceptés (base) | % acceptés (total) |
|---|---|---|
| filtre complet | 62,9 | 62,9 |
| sans forme | 62,9 | 62,9 |
| sans V1 | 64,9 | 64,9 |
| sans V2 | 66 | 66 |
| sans V3 | 86,6 | 86,6 |
| forme seule | 99 | 99 |
| aucun filtre | 100 | 100 |

## Tableau 8 — Ablations de modèles

| Méthode | Modèle QA | AUC (vrai passage / autre cours) | % vraies questions acceptées à 5 % de fausses acceptations |
|---|---|---|---|
| base | XLM-R SQuAD 2.0 (retenu) | 0,993 | 96,9 |
| base | CamemBERT FQuAD/PIAF (écarté) | 0,786 | 30,9 |

| Variante NLI | Discernement base (%) | % V2+V3 (base) | Clé fausse détectée par V3 (tirage 10.2, %) |
|---|---|---|---|
| B, 2 phrases (retenu) | 90,7 | 64,9 | 83 |
| A, 2 phrases | 64,9 | 16,5 | 95,2 |
| B, 1 phrase | 91,8 | 85,6 | 24,7 |
| B, 4 phrases | 86,6 | 54,6 | 69 |

## Tableau 9 — Sensibilité aux seuils

| Seuil | Valeurs testées | Valeur retenue | % acceptés à la valeur retenue | % acceptés : min – max sur la plage |
|---|---|---|---|---|
| V1 : centile du contrôle négatif | 0,8 – 0,99 | 0,95 | 62,9 | 54,6 – 64,9 |
| V2 : implication min. de la bonne réponse | 0,3 – 0,8 | 0,5 | 62,9 | 61,9 – 63,9 |
| V3 : implication max. d'un distracteur | 0,6 – 0,99 | 0,9 | 62,9 | 28,9 – 86,6 |

## Tableau 10 — Biais de longueur (test binomial contre 25 %)

| Méthode | QCM | Bonne réponse = plus longue | % | p (H0 : 25 %) |
|---|---|---|---|---|
| base | 97 | 24 | 24,7 | 1 |

## Tableau 11 — Évaluation humaine : en attente des annotations (voir data/annotations/GUIDE_ANNOTATION.md)

## Ce qu'il reste à calculer

- générer `qcm_llm.jsonl` (étape 5, GPU) puis réexécuter les étapes 6 à 8 ;
- relancer l'ablation mDeBERTa sur GPU (étape 10.4) ;
- remplir les deux grilles d'annotation puis réexécuter l'étape 9.

Après chaque mise à jour : `python3 scripts/verifier_sorties.py`.
