# Génération de QCM avec validation automatique

Projet de TALN, sujet 11. Filière IA & Science des Données, 5e année, EMSI Rabat, 2026/2027.

Le système lit un support de cours et produit des **questions à choix multiples** : une question, une bonne réponse et trois distracteurs plausibles. Un **validateur automatique** contrôle ensuite chaque QCM et rejette ceux qui ne passent pas l'un de ces trois tests :

1. la question est répondable à partir du texte du cours ;
2. une seule option est correcte ;
3. aucun distracteur n'est correct.

On mesure ensuite ce que ce filtre apporte par rapport à une évaluation humaine.

## Structure du dépôt

```
.
├── README.md                  ← ce fichier
├── requirements.txt           ← dépendances Python
├── .gitignore
├── notebooks/
│   └── QCM_generation_validation.ipynb   ← LIVRABLE 1 : notebook exécuté de bout en bout
├── data/
│   ├── raw/                   ← 6 supports de cours PDF (non versionnés) + sources.csv
│   ├── processed/             ← textes nettoyés et passages découpés (passages.jsonl)
│   └── annotations/           ← grilles d'évaluation humaine (60 QCM, ≥ 2 évaluateurs)
├── outputs/
│   ├── qcm/                   ← QCM générés (base, LLM), acceptés et rejetés par le validateur
│   └── figures/               ← graphiques utilisés dans l'article
└── docs/
    ├── Analyse_des_besoins_Sujet11_QCM.pdf
    └── article/               ← LIVRABLE 2 : article de 7 pages maximum
```

**Pourquoi tout le code est dans le notebook et pas dans un dossier `src/`.** Le notebook est le livrable noté. À l'oral, l'enseignant demande « que fait cette cellule ? ». Tout garder dans le notebook permet de lire le projet de haut en bas sans aller-retour entre fichiers, et de l'exécuter tel quel sur Colab.

## Pipeline

| Étape | Contenu | État |
|---|---|---|
| 0 | Configuration, graines, chemins | ✅ |
| 1 | Collecte des 6 supports de cours (langage C) | ✅ |
| 2 | Extraction et nettoyage du texte (accents LaTeX, code, sommaires, en-têtes) | ✅ |
| 3 | Découpage en passages | ✅ |
| 4 | Base de référence : questions à trous + distracteurs par embeddings | ✅ |
| 5 | Modèle avancé : LLM ouvert Qwen2.5-7B-Instruct (prompt few-shot, sortie JSON) | 🟡 code prêt, génération à lancer sur Colab |
| 6 | Contrôles de forme | ⏳ |
| 7 | Validateur V1 / V2 / V3 (questions-réponses + NLI) | ⏳ |
| 8 | Filtrage et mesure de l'apport du filtre | ⏳ |
| 9 | Évaluation humaine (60 QCM) et accord entre évaluateurs | ⏳ |
| 10 | Ablations et sensibilité aux seuils | ⏳ |
| 11 | Analyse des erreurs, limites, éthique | ⏳ |

## Exécution

**Sur Google Colab (nécessaire pour l'étape 5, qui demande un GPU) :**
1. Créer un jeton GitHub : *GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens*. Le limiter à ce dépôt, avec le droit *Contents : Read and write*.
2. Dans Colab : *Fichier → Ouvrir un notebook → GitHub*, cocher « Inclure les dépôts privés », puis ouvrir `notebooks/QCM_generation_validation.ipynb`.
3. Ajouter le jeton dans les secrets Colab (icône 🔑 à gauche) sous le nom `GITHUB_TOKEN`, et activer l'accès au notebook. Il ne faut jamais écrire le jeton dans une cellule.
4. Activer le GPU : *Exécution → Modifier le type d'exécution → GPU T4*.
5. *Exécution → Tout exécuter*. La première cellule clone le dépôt. L'étape 1 demande de téléverser les 6 PDF.
6. Après l'exécution, récupérer `outputs/qcm/qcm_llm.jsonl` et `outputs/qcm/llm_brut.jsonl` (panneau Fichiers → Télécharger), puis les placer dans `outputs/qcm/` du dépôt local. Les exécutions suivantes, même sans GPU, relisent ce cache.

**En local (sans GPU, étapes 0 à 4, puis la suite si le cache du LLM est présent) :**
```bash
pip install -r requirements.txt
jupyter notebook notebooks/QCM_generation_validation.ipynb
```

## Données

Le corpus est composé de 6 supports de cours publics sur la **programmation en langage C** :

| id | Fichier | Auteur / établissement |
|---|---|---|
| C1 | `cours.pdf` | Anne Canteaut (INRIA) |
| C2 | `LelangageC_rgww.pdf` | Patrick Trau |
| C3 | `cours_programmation_c.pdf` | M. E. Elhdhili, H. Boucetta |
| C4 | `annexe_08_2_cours_programmation en langage C.pdf` | M. Qbadou (ENSET Mohammedia) |
| C5 | `coursC.pdf` | auteur non indiqué |
| C6 | `support-C-JacquelinCharbonnel.pdf` | Jacquelin Charbonnel (CNRS) |

Les auteurs conservent leurs droits : les PDF **ne sont pas versionnés** (voir `.gitignore`). Pour exécuter le notebook, il faut les déposer dans `data/raw/`. Sur Colab, le notebook propose de les téléverser. Les détails (pages, nombre de mots, part supprimée par le nettoyage) sont dans `data/raw/sources.csv`, que le notebook génère.
