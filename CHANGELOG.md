# Journal des modifications

Ce fichier garde la trace des changements qui ne se lisent pas dans le notebook.
Il est mis à jour à chaque contribution ; le détail des commits reste dans `git log`.

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
