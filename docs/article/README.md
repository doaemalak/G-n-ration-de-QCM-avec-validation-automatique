# LIVRABLE 2 — article

- **`article.md`** : l'article (≤ 7 pages), rédigé à partir du notebook et des
  sorties de `outputs/qcm/`.
- **`resultats_auto.md`** : tableaux de résultats **générés** par
  `scripts/tableaux_resultats.py`. Ne pas modifier à la main : relancer le script.

## Ce qui est mesuré et ce qui reste à compléter

Le LLM, les ablations (mDeBERTa, température) et l'article sont à jour. Seules les
sections d'évaluation humaine restent marquées **À COMPLÉTER** :

| Section | Dépend de | Commande ensuite |
|---|---|---|
| 4.2 et 6.2 (LLM) | ✅ `outputs/qcm/qcm_llm.jsonl` (115 QCM) | rien à faire |
| 6.3 et 8 (évaluation humaine) | `data/annotations/grille_evaluateur_{A,B}.csv` | réexécuter l'étape 9, ou lancer `python3 scripts/tableaux_resultats.py` (kappa, apport, matrice de confusion, F1) |
| 7 (température, mDeBERTa) | ✅ exécuté | rien à faire |

Après chaque mise à jour :

```bash
python3 scripts/tableaux_resultats.py   # met à jour resultats_auto.md
python3 scripts/verifier_sorties.py     # signale les incohérences
```

Puis reporter dans `article.md` les chiffres des tableaux 2 à 14, et supprimer les
marqueurs `À COMPLÉTER` (le vérificateur les compte).

## Mise en page (7 pages maximum)

L'article doit tenir en 7 pages, tableaux et références compris. Deux options :

```bash
make article        # équivaut à la commande ci-dessous
pandoc article.md -o article.pdf --pdf-engine=xelatex --resource-path=. \
  -V geometry:margin=1.8cm -V fontsize=10pt -V lang=fr
```

Les réglages ci-dessus donnent exactement 7 pages avec le texte actuel (3 800 mots,
5 tableaux, 3 figures). Pour contrôler après une mise à jour :

```bash
python3 -c "from pypdf import PdfReader; print(len(PdfReader('article.pdf').pages))"
```

Si le rendu dépasse 7 pages, réduire le texte plutôt que les marges : le barème porte
sur 7 pages, et les résultats à venir (LLM, annotations) ajouteront des lignes de
tableaux. Les caractères `≥` et `≤` ne sont pas disponibles dans la police LaTeX par
défaut : écrire « au moins » / « au plus ».

## Vérifications avant de rendre

- [ ] aucun marqueur `À COMPLÉTER` ne subsiste ;
- [ ] les chiffres cités correspondent à `resultats_auto.md` ;
- [ ] les figures citées existent dans `outputs/figures/` ;
- [ ] les six cours sont cités avec leur auteur (pas de PDF redistribué) ;
- [ ] `python3 scripts/verifier_sorties.py` ne renvoie aucune erreur.
