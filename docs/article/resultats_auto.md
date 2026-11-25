# Tableaux de résultats (générés automatiquement)

Fichier produit par `scripts/tableaux_resultats.py` : **ne pas modifier à la main**.
Les chiffres viennent de `outputs/qcm/` et de `data/processed/`. Les tableaux 2 à 8
et 11 contiennent une ligne par méthode ; la ligne `llm` n'apparaît qu'une fois
l'étape 5 exécutée sur GPU.

## Tableau 1 — Corpus et passages

| Cours | Titre | Auteur | Format | Pages | Mots brut | Mots nettoyés | % retiré | Passages | Mots/passage | Tokens max |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Programmation en langage C | Anne Canteaut (INRIA) | polycopié LaTeX | 133 | 36361 | 23243 | 36,1 | 130 | 164 | 452 |
| C2 | Le langage C | Patrick Trau | polycopié | 71 | 20292 | 12452 | 38,6 | 81 | 151 | 458 |
| C3 | Programmation C | M. E. Elhdhili, H. Boucetta | polycopié Word | 76 | 21115 | 13247 | 37,3 | 88 | 134 | 383 |
| C4 | Programmation en langage C | M. Qbadou (ENSET Mohammedia), 2022/2023 | polycopié Word | 68 | 11764 | 5663 | 51,9 | 34 | 127 | 392 |
| C5 | Initiation au langage C | non indiqué | polycopié LaTeX | 52 | 14726 | 8145 | 44,7 | 55 | 137 | 448 |
| C6 | Cours de langage C | Jacquelin Charbonnel (CNRS) | diapositives | 60 | 10126 | 3730 | 63,2 | 27 | 114 | 445 |
| Total |  | 6 cours |  | 460 | 114384 | 66480 | 41,9 | 415 | 145 | 458 |

## Tableau 2 — Couverture et rendement par méthode
> Générateur LLM : `Qwen/Qwen3-4B-Instruct-2507`.

| Méthode | Passages testés | QCM produits | Couverture (%) | Acceptés | Taux d'acceptation (%) | QCM acceptés / passages (%) |
|---|---|---|---|---|---|---|
| base | 120 | 97 | 80,8 | 25 | 25,8 | 20,8 |
| llm | 120 | 115 | 95,8 | 30 | 26,1 | 25 |

## Tableau 3 — Défauts de forme détectés (% des QCM de la méthode)

| Méthode | F1 | F2 | F3 | F4 | F5 | F6 | F7 | Conformes (%) |
|---|---|---|---|---|---|---|---|---|
| base | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 99 |
| llm | 10,4 | 0 | 1,7 | 0,9 | 3,5 | 5,2 | 0 | 79,1 |

## Tableau 4 — Taux de passage de chaque test (% des QCM)

| Méthode | V1 répondabilité | V2 bonne réponse unique | V3 aucun distracteur correct | V1 et V2 et V3 |
|---|---|---|---|---|
| base | 44,3 | 89,7 | 69,1 | 25,8 |
| llm | 80,9 | 51,3 | 74,8 | 33 |

## Tableau 5 — Cascade des rejets (nombre de QCM)

| Méthode | forme (F1–F7) | V1 | V2 | V3 | accepté |
|---|---|---|---|---|---|
| base | 1 | 54 | 7 | 10 | 25 |
| llm | 24 | 16 | 37 | 8 | 30 |

## Tableau 6 — Typologie des rejets (nombre de QCM)

| Catégorie | base | llm | Total |
|---|---|---|---|
| texte source dégradé | 2 | 5 | 7 |
| défaut de forme | 1 | 24 | 25 |
| réponse introuvable | 52 | 15 | 67 |
| bonne réponse non confirmée | 7 | 34 | 41 |
| distracteur proche de la réponse | 9 | 3 | 12 |
| distracteur confirmé sans être proche | 1 | 4 | 5 |
| Total | 72 | 85 | 157 |

## Tableau 7 — Couverture par cours (QCM produits pour 20 passages)

| Cours | Passages | base | llm |
|---|---|---|---|
| C1 | 20 | 19 | 20 |
| C2 | 20 | 19 | 19 |
| C3 | 20 | 20 | 17 |
| C4 | 20 | 18 | 20 |
| C5 | 20 | 18 | 19 |
| C6 | 20 | 3 | 20 |

## Tableau 8 — Contrôles négatifs et défauts injectés

| Méthode | Contrôle négatif V1 | AUC | % de questions sans réponse acceptées | dont rejetés par V2 (%) | dont rejetés par V3 (%) |
|---|---|---|---|---|---|
| base | autre cours | 0,993 | 0 | — | — |
| base | même cours | 0,992 | 0 | — | — |
| llm | autre cours | 0,942 | 9,6 | — | — |
| llm | même cours | 0,944 | 11,3 | — | — |
| base | clé de correction fausse | — | — | 100 | 77,8 |
| llm | clé de correction fausse | — | — | 100 | 31,2 |

## Tableau 9 — Ablation des contrôles du filtre (taux d'acceptation)

| Variante | % acceptés (base) | % acceptés (llm) | % acceptés (total) |
|---|---|---|---|
| filtre complet | 25,8 | 26,1 | 25,9 |
| sans forme | 25,8 | 33 | 29,7 |
| sans V1 | 64,9 | 33 | 47,6 |
| sans V2 | 28,9 | 47 | 38,7 |
| sans V3 | 36,1 | 33 | 34,4 |
| forme seule | 99 | 79,1 | 88,2 |
| aucun filtre | 100 | 100 | 100 |

## Tableau 10 — Ablations de modèles

| Méthode | Modèle QA | AUC (vrai passage / autre cours) | % vraies questions acceptées à 5 % de fausses acceptations |
|---|---|---|---|
| base | XLM-R SQuAD 2.0 (retenu) | 0,993 | 96,9 |
| base | CamemBERT FQuAD/PIAF (écarté) | 0,786 | 30,9 |
| llm | XLM-R SQuAD 2.0 (retenu) | 0,942 | 73,9 |
| llm | CamemBERT FQuAD/PIAF (écarté) | 0,78 | 27,8 |

| Variante NLI | Discernement base (%) | % V2+V3 (base) | % V2+V3 (llm) | Clé fausse détectée par V3 (tirage 10.2, %) |
|---|---|---|---|---|
| B, 2 phrases (retenu) | 90,7 | 64,9 | 41,7 | 64,3 |
| A, 2 phrases | 64,9 | 16,5 | — | 95,2 |
| B, 1 phrase | 91,8 | 85,6 | 39,1 | 24,8 |
| B, 4 phrases | 86,6 | 54,6 | 37,4 | 60,5 |
| B, 2 phrases, mDeBERTa | 69,1 | 21,6 | 48,7 | 37,1 |

## Tableau 11 — Sensibilité aux seuils

| Seuil | Méthode | Valeurs testées | Valeur retenue | % acceptés à la valeur retenue | % acceptés : min – max sur la plage |
|---|---|---|---|---|---|
| V1 : centile du contrôle négatif | base | 0,8 – 0,99 | 0,95 | 25,8 | 18,6 – 49,5 |
| V1 : centile du contrôle négatif | llm | 0,8 – 0,99 | 0,95 | 26,1 | 24,3 – 33,0 |
| V2 : implication min. de la bonne réponse | base | 0,3 – 0,8 | 0,5 | 25,8 | 25,8 – 26,8 |
| V2 : implication min. de la bonne réponse | llm | 0,3 – 0,8 | 0,5 | 26,1 | 16,5 – 29,6 |
| V3 : implication max. d'un distracteur | base | 0,6 – 0,99 | 0,9 | 25,8 | 11,3 – 36,1 |
| V3 : implication max. d'un distracteur | llm | 0,6 – 0,99 | 0,9 | 26,1 | 11,3 – 33,0 |

## Tableau 12 — Biais de longueur (test binomial contre 25 %)

| Méthode | QCM | Bonne réponse = plus longue | % | p (H0 : 25 %) |
|---|---|---|---|---|
| base | 97 | 23 | 23,7 | 0,816 |
| llm | 115 | 49 | 42,6 | 0 |

## Tableau 13 — Évaluation humaine

| Critère | Kappa | IC 95 % (bootstrap) | Pondération | AC1 de Gwet | Accord brut (%) |
|---|---|---|---|---|---|
| clarte | 0,4 | [0,06 ; 0,61] | quadratic | 0,725 | 76,7 |
| difficulte | 0,192 | [0,03 ; 0,41] | quadratic | 0,606 | 68,3 |
| unicite | -0,017 | [-0,04 ; 0,00] | aucune | 0,966 | 96,7 |

| Règle | Méthode | Part réelle d'acceptés | Qualité avant filtre (%) | Qualité après filtre (%) | Apport (points) | Précision des rejets (%) | Rappel des défauts (%) |
|---|---|---|---|---|---|---|---|
| stricte (A et B) | base | 0,26 | 93,3 | 93,3 | 0 | 6,7 | 74,2 |
| stricte (A et B) | llm | 0,26 | 93,3 | 93,3 | 0 | 6,7 | 73,9 |
| indulgente (A ou B) | base | 0,26 | 100 | 100 | 0 | 0 | — |
| indulgente (A ou B) | llm | 0,26 | 100 | 100 | 0 | 0 | — |

| Règle | Méthode | Vrais positifs | Faux positifs | Faux négatifs | Vrais négatifs | Précision (%) | IC 95 % précision (Wilson) | Rappel (%) | F1 (%) |
|---|---|---|---|---|---|---|---|---|---|
| stricte (A et B) | toutes | 28 | 2 | 28 | 2 | 93,3 | [78,7 ; 98,2] | 50 | 65,1 |
| stricte (A et B) | base | 14 | 1 | 14 | 1 | 93,3 | [70,2 ; 98,8] | 50 | 65,1 |
| stricte (A et B) | llm | 14 | 1 | 14 | 1 | 93,3 | [70,2 ; 98,8] | 50 | 65,1 |
| indulgente (A ou B) | toutes | 30 | 0 | 30 | 0 | 100 | [88,6 ; 100,0] | 50 | 66,7 |
| indulgente (A ou B) | base | 15 | 0 | 15 | 0 | 100 | [79,6 ; 100,0] | 50 | 66,7 |
| indulgente (A ou B) | llm | 15 | 0 | 15 | 0 | 100 | [79,6 ; 100,0] | 50 | 66,7 |

## Tableau 14 — Calibration de V1 : seuil global contre seuil par méthode

| Calibration | Méthode | Seuil V1 | Fausse acceptation (%) | V1 (%) | Acceptés | Taux d'acceptation (%) |
|---|---|---|---|---|---|---|
| global (déployé) | base | -1,87 | 0 | 44,3 | 25 | 25,8 |
| global (déployé) | llm | -1,87 | 9,6 | 80,9 | 30 | 26,1 |
| par méthode | base | -8,8 | 5,2 | 96,9 | 61 | 62,9 |
| par méthode | llm | -1,1 | 5,2 | 73,9 | 29 | 25,2 |

## Ce qu'il reste à calculer

- remplir les deux grilles d'annotation puis réexécuter l'étape 9.

Après chaque mise à jour : `python3 scripts/verifier_sorties.py`.
