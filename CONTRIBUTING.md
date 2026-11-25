# Contribuer

Projet de TALN (sujet 11) : génération de QCM à partir de supports de cours et
validation automatique. Ce guide décrit l'état du dépôt, ce qui reste à faire et les
conventions à respecter pour que les livrables restent cohérents.

## Règle d'or : où va le code

- **Le pipeline reste dans le notebook** (`notebooks/QCM_generation_validation.ipynb`).
  C'est le livrable noté et il doit s'exécuter de haut en bas sur Colab. On n'ajoute
  pas d'étape du pipeline dans un module séparé.
- **`scripts/` contient l'après-notebook** : exporter les QCM, vérifier les sorties,
  régénérer les tableaux de l'article. Ces scripts lisent les fichiers produits et ne
  relancent aucun modèle : ils tournent sans GPU et sans les PDF.
- **`tests/`** vérifie ces scripts et la cohérence du dépôt. Il ne teste pas le
  notebook (il faudrait les PDF et les modèles).

Toute modification du notebook doit être **réexécutée** (`Exécution → Tout exécuter`)
avant d'être poussée : les sorties visibles font partie du livrable.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # étapes 0 à 4 et 6 à 11, sans GPU
pip install -r requirements-dev.txt    # pytest et dépendances des scripts
```

Sur Colab (GPU), `bitsandbytes` et `accelerate` sont installés automatiquement par la
cellule de chargement du LLM ; sinon `pip install -r requirements-gpu.txt`.

## État du projet

| Élément | État |
|---|---|
| Étapes 0 à 8, 10.1 à 10.5, 11 | ✅ exécutées, sorties versionnées |
| Étape 5 — génération LLM | ✅ 115/120 QCM valides (95,8 %), cache versionné |
| Étape 9 — évaluation humaine (60 QCM, 2 évaluateurs) | 🟡 grilles de 60 QCM créées ; annotations à faire |
| Étape 10.5 — température du LLM | ✅ exécutée |
| Ablation du générateur (SmolLM3-3B, Gemma 3 4B) | 🟡 protocole dans `docs/llm/CHOIX_MODELE.md` |
| LIVRABLE 2 — article | 🟡 article à jour (7 pages) ; 6.3 et 8 en attente des annotations |

### 1. QCM du LLM (déjà générés)

**État : 115 QCM générés avec `Qwen/Qwen3-4B-Instruct-2507` (95,8 % des 120 passages),
cache versionné dans `outputs/qcm/qcm_llm.jsonl`.** Les étapes ci-dessous servent à
régénérer ou à changer de modèle.

Modèle par défaut : `Qwen/Qwen3-4B-Instruct-2507` (voir `docs/llm/CHOIX_MODELE.md`).
Sans accès GitHub dans le navigateur, utiliser `make archive-colab` et téléverser le zip
dans Colab (voir README) : le notebook détecte le dépôt et ne clone rien.
Pour une ablation, changer `QCM_LLM_MODEL` **et** `QCM_LLM_CACHE` : le notebook refuse
un cache produit par un autre modèle.

1. Colab, GPU T4, jeton GitHub dans les secrets sous le nom `GITHUB_TOKEN`.
2. Téléverser les six PDF dans `data/raw/` (ils ne sont pas versionnés).
3. *Exécution → Tout exécuter*.
4. Récupérer `outputs/qcm/qcm_llm.jsonl`, `llm_brut.jsonl`, `qcm_llm_temperature.jsonl`,
   `scores_validateur.jsonl`, `scores_ablation.jsonl` et les replacer dans le dépôt.

### 2. Annoter les 60 QCM

Les grilles sont déjà créées : `data/annotations/grille_evaluateur_A.csv`,
`..._B.csv` et `cle_echantillon.csv` (15 QCM par case méthode × décision). Chaque
évaluateur remplit **sa** grille seul, après avoir lu `GUIDE_ANNOTATION.md`, sans ouvrir
la clé. Pour préserver l'aveugle, n'envoyer au peer que sa grille et le guide. Réexécuter
ensuite l'étape 9 du notebook, ou lancer `python3 scripts/tableaux_resultats.py` (qui
calcule kappa, apport du filtre et matrice de confusion).

### 3. Finaliser l'article

L'article est déjà à jour pour le LLM et les ablations (7 pages). Après les annotations,
voir `docs/article/README.md` : régénérer les tableaux, compléter les sections 6.3 et 8,
supprimer les marqueurs `À COMPLÉTER`, puis `make article` (rendu vérifié : 7 pages).

## Commandes utiles

```bash
make verifier     # cohérence de tous les artefacts versionnés
make exporter     # Moodle GIFT + HTML + CSV depuis les QCM acceptés
make tableaux     # régénère docs/article/resultats_auto.md
make test         # pytest
make tout         # les quatre
```

Sans `make`, les mêmes commandes sont dans le `Makefile`.

## Conventions

- **Langue** : français, y compris dans le code (noms de variables, commentaires).
- **Reproductibilité** : graines fixées (`CONFIG["seed"]`), décodage glouton par défaut
  pour le LLM, caches JSON versionnés. Un cache n'est recalculé que si les modèles
  changent (champ `signature` de `scores_validateur.jsonl`).
- **Fichiers pour Excel** : séparateur `;` et encodage `utf-8-sig`.
- **Schéma d'un QCM** (identique pour toutes les méthodes) :
  `qcm_id`, `methode`, `passage_id`, `cours_id`, `question`, `options` (4), `index_correct`,
  `reponse`. Le LLM ajoute `justification`, `essai`, `duree_s`.
- **Ne jamais écraser** une grille d'annotation ni un cache de génération sans le dire
  dans la *pull request* : ce sont des heures de travail ou de GPU.
- **Provenance du LLM** : chaque QCM enregistre son champ `modele` ; ne pas réutiliser
  un cache produit par un autre modèle (le notebook s'arrête et l'explique).
- **Un chiffre = une source** : les nombres de l'article viennent de
  `scripts/tableaux_resultats.py`, pas d'un copier-coller. Si un seuil change dans le
  notebook, mettre à jour `CENTILE_V1`, `IMP_MIN_V2`, `IMP_MAX_V3` dans le script ;
  l'assertion intégrée échoue si les décisions ne concordent plus.

## Avant de pousser

```bash
python3 scripts/verifier_sorties.py   # doit afficher « Toutes les sorties sont cohérentes »
python3 -m pytest -q                  # doit passer
```

Noter les changements qui ne se lisent pas dans le notebook (bug corrigé, mesure
ajoutée, chiffre de l'article modifié) dans `CHANGELOG.md`, avec la commande qui permet
de les vérifier.

La CI (`.github/workflows/verifications.yml`) exécute ces deux commandes à chaque
*push* et *pull request*. Les avertissements (QCM du LLM absents, grilles vides) sont
attendus tant que les étapes GPU et humaines ne sont pas faites ; `--strict` les
transforme en échec.

## Pull request

- Décrire **ce qui est mesuré** et joindre les chiffres avant/après si un résultat change.
- Séparer les commits : notebook / script / article.
- Ne pas versionner les PDF de cours (droits des auteurs), ni les jetons GitHub, ni les
  fichiers `outputs/export/` (régénérables).
