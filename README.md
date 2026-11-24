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
├── CONTRIBUTING.md            ← état du projet, ce qui reste à faire, conventions
├── Makefile                   ← raccourcis : verifier, exporter, tableaux, test
├── requirements.txt           ← dépendances Python (sans GPU)
├── requirements-gpu.txt       ← bitsandbytes, accelerate (Colab T4)
├── requirements-dev.txt       ← pytest et dépendances des scripts (CI)
├── .gitignore
├── notebooks/
│   └── QCM_generation_validation.ipynb   ← LIVRABLE 1 : notebook exécuté de bout en bout
├── scripts/                   ← OUTILS D'APRÈS-NOTEBOOK (aucun modèle, aucun GPU)
│   ├── verifier_sorties.py    ← cohérence des artefacts versionnés
│   ├── exporter_qcm.py        ← Moodle GIFT + HTML + CSV des QCM acceptés
│   └── tableaux_resultats.py  ← régénère les tableaux de l'article
├── tests/                     ← pytest sur les scripts ci-dessus
├── data/
│   ├── raw/                   ← 6 supports de cours PDF (non versionnés) + sources.csv
│   ├── processed/             ← textes nettoyés et passages découpés (passages.jsonl)
│   └── annotations/           ← grilles d'évaluation humaine (60 QCM, ≥ 2 évaluateurs)
├── outputs/
│   ├── qcm/                   ← QCM générés (base, LLM), acceptés et rejetés par le validateur
│   ├── export/                ← GIFT/HTML/CSV, régénérés (non versionnés)
│   └── figures/               ← graphiques utilisés dans l'article
└── docs/
    ├── Analyse_des_besoins_Sujet11_QCM.pdf
    └── article/               ← LIVRABLE 2 : article (≤ 7 pages) + tableaux générés
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
| 6 | Contrôles de forme (7 règles testées, biais de longueur) | ✅ |
| 7 | Validateur V1 / V2 / V3 (questions-réponses SQuAD 2.0 + NLI, seuil V1 par contrôle négatif) | ✅ |
| 8 | Filtrage final (forme ET V1 ET V2 ET V3), motifs de rejet, rendement, candidats naïfs | ✅ |
| 9 | Évaluation humaine (60 QCM) et accord entre évaluateurs | 🟡 grille, guide et analyses prêts ; annotations à faire après l'étape 5 |
| 10 | Ablations (contrôles, modèles QA/NLI, formulation, température) et sensibilité aux seuils | ✅ (mDeBERTa et température : sur GPU) |
| 11 | Analyse des erreurs (typologie des rejets, hallucinations, erreurs du validateur), limites, éthique | ✅ |
| — | Export des QCM acceptés (Moodle GIFT, HTML, CSV) — besoin BF13 de l'analyse des besoins | ✅ `scripts/exporter_qcm.py` |
| — | Livrable 2 : article ≤ 7 pages et tableaux de résultats | 🟡 `docs/article/article.md`, marqueurs « À COMPLÉTER » |

## Exécution

**Sur Google Colab (nécessaire pour l'étape 5, qui demande un GPU) :**
1. Créer un jeton GitHub : *GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens*. Le limiter à ce dépôt, avec le droit *Contents : Read and write*.
2. Dans Colab : *Fichier → Ouvrir un notebook → GitHub*, cocher « Inclure les dépôts privés », puis ouvrir `notebooks/QCM_generation_validation.ipynb`.
3. Ajouter le jeton dans les secrets Colab (icône 🔑 à gauche) sous le nom `GITHUB_TOKEN`, et activer l'accès au notebook. Il ne faut jamais écrire le jeton dans une cellule.
4. Activer le GPU : *Exécution → Modifier le type d'exécution → GPU T4*.
5. *Exécution → Tout exécuter*. La première cellule clone le dépôt. L'étape 1 demande de téléverser les 6 PDF.
6. Après l'exécution, récupérer `outputs/qcm/qcm_llm.jsonl`, `outputs/qcm/llm_brut.jsonl`, `outputs/qcm/scores_validateur.jsonl`, `outputs/qcm/scores_ablation.jsonl` et `outputs/qcm/qcm_llm_temperature.jsonl` (panneau Fichiers → Télécharger), puis les placer dans `outputs/qcm/` du dépôt local. Les exécutions suivantes, même sans GPU, relisent ce cache.

**Évaluation humaine (étape 9), une fois les QCM du LLM présents :**
1. Réexécuter le notebook. Il crée dans `data/annotations/` les fichiers `grille_evaluateur_A.csv`, `grille_evaluateur_B.csv` et `cle_echantillon.csv`.
2. Chaque membre du binôme lit `GUIDE_ANNOTATION.md`, puis remplit **sa** grille seul, dans Excel ou LibreOffice, en gardant le format CSV avec le séparateur `;`. Il ne faut pas ouvrir `cle_echantillon.csv` avant d'avoir terminé.
3. Réexécuter le notebook : l'accord entre évaluateurs et l'apport du filtre se calculent automatiquement.

**En local (sans GPU, étapes 0 à 4, puis la suite si le cache du LLM est présent) :**
```bash
pip install -r requirements.txt
jupyter notebook notebooks/QCM_generation_validation.ipynb
```
Sur GPU, ajouter `pip install -r requirements-gpu.txt` (le notebook le fait lui-même s'il
le faut). `bitsandbytes` n'est volontairement pas dans `requirements.txt` : il ne
s'installe pas sur toutes les machines sans CUDA.

## Outils d'après-notebook

Trois scripts lisent les sorties déjà produites ; ils ne relancent aucun modèle et
tournent sans GPU ni PDF. `make` enchaîne les quatre commandes.

```bash
make verifier     # invariants de tous les artefacts (schéma des QCM, décisions, caches)
make exporter     # outputs/export/qcm_moodle_gift.txt, qcm.html, qcm.csv
make tableaux     # docs/article/resultats_auto.md depuis outputs/qcm/
make test         # pytest (formats, contrôles, chemins multi-méthodes)
```

- **`verifier_sorties.py`** vérifie 4 000 invariants : 4 options distinctes, `reponse ==
  options[index_correct]`, partition acceptés/rejetés, `forme_ok` cohérent avec les sept
  règles, seuil V1 reproduit depuis le contrôle négatif, caches complets et comparables.
  Il avertit (sans échouer) quand les QCM du LLM ou les annotations manquent encore.
- **`exporter_qcm.py`** produit une banque de questions Moodle (format GIFT), une page
  HTML autonome pour relire les QCM en cours, et un CSV pour Excel. C'est le besoin
  BF13 de `docs/Analyse_des_besoins_Sujet11_QCM.pdf`, absent du notebook.
- **`tableaux_resultats.py`** recalcule les tableaux de l'article depuis les fichiers :
  un chiffre cité ne peut plus être périmé ni copié à la main. Il ajoute
  automatiquement la ligne `llm` et les kappas dès que ces données existent.

La CI (`.github/workflows/verifications.yml`) exécute le vérificateur, les tests et les
deux générateurs à chaque *push*.

## État et suite

Ce qui reste à faire est détaillé dans `CONTRIBUTING.md` : générer les QCM du LLM sur
Colab (étape 5), faire remplir les deux grilles d'annotation (étape 9), puis finaliser
l'article (`docs/article/README.md`). Les sections concernées de l'article portent un
marqueur **À COMPLÉTER** ; les tableaux se mettent à jour tout seuls.

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
