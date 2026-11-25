# Journal des modifications

Ce fichier garde la trace des changements qui ne se lisent pas dans le notebook.
Il est mis à jour à chaque contribution ; le détail des commits reste dans `git log`.

## 2026-11-25 — Exécution Colab du LLM et mise à jour de l'article

**Contexte.** L'étape 5 a été exécutée sur Colab T4 avec Qwen3-4B-Instruct-2507, puis
les sorties ont été copiées dans le dépôt. Le notebook versionné est désormais la
version exécutée (sans la cellule Colab `!unzip`), avec les sorties visibles.

**Résultats du run.** 115 QCM valides sur 120 passages (95,8 %) : 109 au premier essai,
6 après relance, 5 échecs de format ; 7,79 s par QCM. Le LLM couvre 20/20 passages de C6
contre 3/20 pour la base, et 85 % de ses questions sont de compréhension. Il est moins
fiable : 79,1 % de forme, 51,3 % de V2, 42,6 % de biais de longueur (p < 0,001), 31,2 %
de clés fausses détectées, 9,6 % de fausses acceptations sur le contrôle négatif.

**Point de méthode — calibration de V1.** Le seuil global (−1,87) est le 95e centile des
scores négatifs des deux générateurs réunis. Il donne 0 % de fausse acceptation à la base
et 9,6 % au LLM : la base chute de 96,9 % à 44,3 % de V1 et de 61 à 25 QCM acceptés. Un
seuil par méthode (base −8,8 ; LLM −1,10) rétablit 5 % pour chacun : base 61/97 (62,9 %),
LLM 29/115 (25,2 %). Le tableau 14 de `resultats_auto.md` donne les deux lectures ; il
faut le citer dans l'article et ne pas présenter 25/97 comme une propriété du générateur.

**Corrections et ajouts.**

- `scripts/verifier_sorties.py` : les QCM d'ablation de température, ajoutés au cache
  avec `qa_score_neg = NaN` par construction, ne sont plus signalés comme incohérents.
- `scripts/tableaux_resultats.py` : la sensibilité aux seuils est calculée par
  (seuil, méthode) et non plus en mélangeant base et LLM ; ajout du tableau 14
  (calibration globale contre calibration par méthode).
- `tests/` : 36 tests (contre 33). Le test des décisions n'est plus figé sur 61/97 ;
  ajout d'un test du cache de température, de la sensibilité par méthode et du tableau 14.
- `docs/article/article.md` : sections 4.2, 6.1, 6.2, 7, 8, 9 et 10 mises à jour avec
  le LLM, les ablations mDeBERTa/température et la calibration. L'article tient en
  **7 pages** ; seuls la section 6.3 et le bilan humain de la section 8 restent
  **À COMPLÉTER** (annotations).
- `README.md`, `CONTRIBUTING.md`, `docs/article/README.md`, `docs/llm/CHOIX_MODELE.md` :
  états mis à jour (étape 5 et ablations faites ; annotation en cours).

**Reste à faire.** Les deux membres du binôme remplissent chacun leur grille
(`grille_evaluateur_A.csv`, `..._B.csv`), sans ouvrir `cle_echantillon.csv`. Ensuite,
`python3 scripts/tableaux_resultats.py` calcule le kappa, la qualité avant/après filtre,
la précision/rappel/F1 et la matrice de confusion ; compléter les sections 6.3 et 8,
puis régénérer `article.pdf`. L'ablation SmolLM3-3B reste optionnelle.

**Vérifier.**

```bash
python3 scripts/verifier_sorties.py   # 8288 contrôles, 0 erreur
python3 -m pytest -q                  # 36 passed
python3 scripts/tableaux_resultats.py # resultats_auto.md
make article                          # 7 pages
```

## 2026-11-24 — Évaluation du filtre comme classifieur (BF12)

**Contexte.** L'analyse des besoins demande, au §9.1, de traiter le filtre comme un
classifieur du verdict humain et de rapporter « précision, rappel, F1, matrice de
confusion ». Le notebook calculait déjà la précision des rejets et le rappel des
défauts, mais le script qui alimente l'article ne produisait ni F1 ni matrice de
confusion complète.

**Correction d'un bug latent.** `scripts/tableaux_resultats.py` fusionnait la clé
d'échantillonnage avec `validation.csv` sur une colonne `accepte` présente des deux
côtés. pandas renommait alors les colonnes en `accepte_x` / `accepte_y`, et la ligne
`d["accepte"]` levait un `KeyError`. Le chemin n'était jamais exécuté, faute
d'annotations : le script aurait échoué **le jour où les deux grilles sont remplies**.
La fusion remplace maintenant la décision de la clé par celle recalculée depuis
`validation.csv`, sans collision.

**Ajouts.**

- `scripts/tableaux_resultats.py` : le tableau 13 contient désormais, pour chaque règle
  de verdict (stricte « A et B », indulgente « A ou B ») et pour chaque méthode
  (`toutes`, `base`, `llm` si présent) :
  - les quatre cases de la matrice de confusion — vrais positifs (bons QCM gardés),
    faux positifs (mauvais gardés), faux négatifs (bons rejetés), vrais négatifs
    (mauvais rejetés) ;
  - la précision, le rappel et le F1 du filtre.
- `notebooks/QCM_generation_validation.ipynb`, cellule 9.6 (section 9.5) : le même
  calcul est affiché dans le notebook, dans la branche « annotations prêtes ». La
  branche non exécutée (grilles absentes) est inchangée : la sortie visible reste
  « En attente des deux grilles remplies. ». **À réexécuter une fois les grilles
  remplies**, comme le demande `CONTRIBUTING.md`.
- `tests/test_tableaux_resultats.py` : nouveau test qui fabrique une clé et deux
  grilles synthétiques, exécute `tableau_annotations` et vérifie que les quatre cases
  somment au nombre de QCM, que la précision, le rappel et le F1 se recalculent
  exactement. Ce test aurait échoué avec l'ancien `KeyError`.
- `docs/article/article.md` (§6.3) et `docs/article/README.md` : la liste des mesures
  à reporter mentionne la matrice de confusion, la précision, le rappel et le F1.

**Correction cosmétique.** Le tableau 1 de `resultats_auto.md` avait une colonne
d'index nommée `index` et une ligne « Total » dont la colonne `Titre` répétait
« Total ». L'index s'appelle maintenant `Cours` et la ligne totale ne duplique plus
le libellé.

**Vérifier.**

```bash
python3 -m pytest -q
python3 scripts/verifier_sorties.py
python3 scripts/tableaux_resultats.py   # inchangé tant que les grilles sont vides
```

## Comment documenter une prochaine contribution

Ajouter une section datée ci-dessus avec quatre rubriques : **contexte**, **bug ou
manque**, **fichiers touchés**, **vérification**. Si un chiffre de l'article change,
indiquer l'ancienne et la nouvelle valeur, et la commande qui les produit.
