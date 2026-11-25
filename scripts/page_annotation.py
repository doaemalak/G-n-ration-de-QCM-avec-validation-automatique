"""Génère une page HTML autonome pour remplir une grille d'annotation.

    python scripts/page_annotation.py            # évaluateur B
    python scripts/page_annotation.py --evaluateur A

La page affiche un QCM par écran (passage, question, options), enregistre les réponses
dans le navigateur au fur et à mesure, puis exporte `grille_evaluateur_X.csv` au format
attendu (UTF-8, séparateur « ; »). Les notes déjà présentes dans la grille ne sont
**pas** reprises : l'évaluateur part d'une grille vierge, sans voir de brouillon.
La clé (méthode, décision du filtre) n'est pas incluse non plus.

La page contient des extraits des cours : elle est ignorée par Git (revue_*.html).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ANNOT = RACINE / "data" / "annotations"
COLONNES_QCM = ["eval_id", "cours", "passage", "question", "A", "B", "C", "D",
                "bonne_reponse_indiquee"]


def lire_qcm(evaluateur: str) -> list[dict]:
    chemin = ANNOT / f"grille_evaluateur_{evaluateur}.csv"
    with chemin.open(encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    return [{k: ligne[k] for k in COLONNES_QCM} for ligne in lignes]


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--evaluateur", default="B", choices=["A", "B"])
    args = p.parse_args(argv)

    qcm = lire_qcm(args.evaluateur)
    gabarit = (Path(__file__).parent / "page_annotation_gabarit.html").read_text(encoding="utf-8")
    page = (gabarit
            .replace("__EVALUATEUR__", args.evaluateur)
            .replace("__DONNEES__", json.dumps(qcm, ensure_ascii=False).replace("</", "<\\/")))
    sortie = ANNOT / f"revue_annotation_{args.evaluateur}.html"
    sortie.write_text(page, encoding="utf-8")
    print(f"{len(qcm)} QCM → {sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
