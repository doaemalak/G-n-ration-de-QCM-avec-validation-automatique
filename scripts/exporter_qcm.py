#!/usr/bin/env python3
"""Exporte les QCM acceptés par le validateur vers des formats utilisables.

Trois sorties, à partir de ``outputs/qcm/qcm_acceptes.jsonl`` :

1. ``qcm_moodle_gift.txt`` : format GIFT, importable dans Moodle (banque de
   questions). C'est le besoin BF13 de l'analyse des besoins, absent du
   notebook ;
2. ``qcm.html`` : une page autonome (aucun serveur, aucune dépendance) pour
   relire les QCM et les projeter en cours ;
3. ``qcm.csv`` : un tableau unique, séparateur ``;`` et BOM UTF-8, qui s'ouvre
   directement dans Excel ou LibreOffice.

Le script ne modifie jamais les fichiers du notebook : il lit les sorties
déjà produites. Il ne dépend que de la bibliothèque standard, donc il tourne
sans GPU et sans installer torch.

Exemples
--------
    python3 scripts/exporter_qcm.py
    python3 scripts/exporter_qcm.py --entree outputs/qcm/qcm_acceptes.jsonl --sortie /tmp/export
    python3 scripts/exporter_qcm.py --limite 20 --sans-html
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Caractères réservés du format GIFT : ils doivent être échappés par un antislash.
GIFT_RESERVES = "\\~=#{}:"


# --------------------------------------------------------------------------- #
# Lecture et contrôle des données
# --------------------------------------------------------------------------- #
def charger_jsonl(chemin: Path) -> list[dict]:
    """Lit un fichier JSONL et vérifie qu'il n'est pas vide."""
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} est absent. Lancer d'abord le notebook jusqu'à l'étape 8."
        )
    with chemin.open(encoding="utf-8") as f:
        lignes = [json.loads(l) for l in f if l.strip()]
    if not lignes:
        raise ValueError(f"{chemin} ne contient aucun QCM.")
    return lignes


def charger_passages(chemin: Path) -> dict[str, dict]:
    """Index passage_id -> passage (section + texte), pour le contexte dans le HTML."""
    if not chemin.exists():
        return {}
    with chemin.open(encoding="utf-8") as f:
        return {p["passage_id"]: p for p in (json.loads(l) for l in f if l.strip())}


def controler(q: dict) -> None:
    """Vérifie la structure d'un QCM. Une sortie corrompue doit s'arrêter ici."""
    manquants = [k for k in ("qcm_id", "question", "options", "index_correct") if k not in q]
    if manquants:
        raise ValueError(f"{q.get('qcm_id', '?')} : champ(s) manquant(s) {manquants}")
    options = q["options"]
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError(f"{q['qcm_id']} : 4 options attendues, {len(options)} trouvée(s)")
    if len({str(o).strip().lower() for o in options}) != 4:
        raise ValueError(f"{q['qcm_id']} : options en double")
    if q["index_correct"] not in range(4):
        raise ValueError(f"{q['qcm_id']} : index_correct = {q['index_correct']} hors de 0-3")


def preparer(qcm: list[dict], passages: dict[str, dict]) -> list[dict]:
    """Ajoute les champs dérivés utilisés par les trois exports."""
    prep = []
    for q in qcm:
        controler(q)
        passage = passages.get(q.get("passage_id", ""), {})
        prep.append(
            {
                **q,
                "reponse": q["options"][q["index_correct"]],
                "section": passage.get("section", ""),
                "passage": passage.get("texte", ""),
            }
        )
    return prep


# --------------------------------------------------------------------------- #
# 1. Format GIFT (Moodle)
# --------------------------------------------------------------------------- #
def echapper_gift(texte: str) -> str:
    """Échappe un texte pour GIFT.

    GIFT est un format ligne à ligne : un retour à la ligne dans un énoncé
    couperait la question. On remplace donc les sauts de ligne par des espaces
    avant d'échapper les caractères réservés.
    """
    texte = " ".join(str(texte).split())
    return "".join("\\" + c if c in GIFT_RESERVES else c for c in texte)


def categorie_moodle(titre: str) -> str:
    """Nom de catégorie Moodle : le « / » crée une sous-catégorie, le reste est nettoyé."""
    return re.sub(r"[^A-Za-z0-9_/-]+", "_", titre).strip("/_") or "QCM"


def en_gift(qcm: list[dict], titre: str = "QCM TALN") -> str:
    """Produit un fichier GIFT, une catégorie Moodle par méthode."""
    lignes = [
        f"// {titre} — export automatique de outputs/qcm/qcm_acceptes.jsonl",
        "// Importer dans Moodle : Banque de questions > Importer > Format GIFT.",
        "// Ne pas modifier à la main : régénérer avec scripts/exporter_qcm.py.",
        "",
    ]
    methodes = sorted({q.get("methode", "qcm") for q in qcm})
    for methode in methodes:
        lignes.append(f"$CATEGORY: {categorie_moodle(titre)}/{methode}")
        lignes.append("")
        for q in qcm:
            if q.get("methode", "qcm") != methode:
                continue
            lignes.append(f"::{q['qcm_id']}::{echapper_gift(q['question'])}")
            lignes.append("{")
            lignes.append(f"    ={echapper_gift(q['reponse'])}")
            for k, option in enumerate(q["options"]):
                if k != q["index_correct"]:
                    lignes.append(f"    ~{echapper_gift(option)}")
            lignes.append("}")
            lignes.append("")
    return "\n".join(lignes)


# --------------------------------------------------------------------------- #
# 2. Page HTML autonome
# --------------------------------------------------------------------------- #
CSS = """
:root { color-scheme: light dark; --ok:#1a7f37; --ko:#b42318; --cadre:#d0d7de; --fond:#f6f8fa; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       margin: 0 auto; max-width: 52rem; padding: 2rem 1.2rem 4rem; line-height: 1.5; }
h1 { font-size: 1.6rem; margin-bottom: .2rem; }
.intro { color: #57606a; margin-top: 0; }
h2 { font-size: 1.1rem; margin-top: 2.4rem; border-bottom: 1px solid var(--cadre); padding-bottom: .3rem; }
.badge { font-size: .75rem; font-weight: 600; text-transform: uppercase; letter-spacing: .03em;
         background: var(--fond); border: 1px solid var(--cadre); border-radius: 999px;
         padding: .1rem .5rem; color: #57606a; }
.qcm { border: 1px solid var(--cadre); border-radius: .6rem; padding: 1rem 1.1rem; margin: 1.2rem 0; }
.qcm p.enonce { font-weight: 600; margin: 0 0 .8rem; }
label { display: block; padding: .35rem .5rem; border-radius: .35rem; cursor: pointer; }
label:hover { background: var(--fond); }
label.bonne { color: var(--ok); font-weight: 600; }
label.mauvaise { color: var(--ko); text-decoration: line-through; }
.actions { margin-top: .8rem; display: flex; gap: .8rem; align-items: center; flex-wrap: wrap; }
button { font: inherit; padding: .35rem .9rem; border: 1px solid var(--cadre); border-radius: .4rem;
         background: var(--fond); cursor: pointer; }
button:hover { background: var(--cadre); }
.verdict { font-weight: 600; font-size: .9rem; }
.verdict.ok { color: var(--ok); } .verdict.ko { color: var(--ko); }
details { margin-top: .7rem; font-size: .9rem; }
summary { cursor: pointer; color: #57606a; }
.source { font-style: italic; color: #57606a; white-space: pre-wrap; margin-top: .5rem; }
@media print { .actions { display: none; } details { display: block; } .qcm { break-inside: avoid; } }
"""

JS = """
document.querySelectorAll('.qcm').forEach(function (carte) {
  const bonne = Number(carte.dataset.correct);
  const bouton = carte.querySelector('button');
  const verdict = carte.querySelector('.verdict');
  bouton.addEventListener('click', function () {
    const choix = carte.querySelector('input[type=radio]:checked');
    if (!choix) { verdict.textContent = 'Choisir une réponse.'; verdict.className = 'verdict'; return; }
    const k = Number(choix.value);
    carte.querySelectorAll('label').forEach(function (lab) {
      const i = Number(lab.dataset.index);
      lab.classList.toggle('bonne', i === bonne);
      lab.classList.toggle('mauvaise', i === k && i !== bonne);
    });
    verdict.textContent = k === bonne ? 'Correct' : 'Incorrect';
    verdict.className = 'verdict ' + (k === bonne ? 'ok' : 'ko');
    bouton.disabled = true;
    carte.querySelectorAll('input').forEach(function (i) { i.disabled = true; });
    carte.querySelector('details').open = true;
  });
});
"""


def en_html(qcm: list[dict], titre: str = "QCM validés") -> str:
    """Produit une page autonome : questions, correction, passage source."""
    methodes = sorted({q.get("methode", "qcm") for q in qcm})
    blocs = [
        "<!doctype html>",
        '<html lang="fr"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(titre)}</title>",
        f"<style>{CSS}</style></head><body>",
        f"<h1>{html.escape(titre)}</h1>",
        f'<p class="intro">{len(qcm)} questions acceptées par le validateur automatique '
        "(forme, V1, V2 et V3). Chaque question est corrigée et accompagnée du passage du cours "
        "qui la justifie.</p>",
    ]
    for methode in methodes:
        sous = [q for q in qcm if q.get("methode", "qcm") == methode]
        blocs.append(f"<h2>{html.escape(methode)}</h2>")
        blocs.append(f'<p><span class="badge">{len(sous)} questions</span></p>')
        for n, q in enumerate(sous, 1):
            blocs.append(
                f'<section class="qcm" data-correct="{q["index_correct"]}">'
                f'<p class="enonce">{n}. {html.escape(q["question"])}</p>'
            )
            for k, option in enumerate(q["options"]):
                blocs.append(
                    f'<label data-index="{k}"><input type="radio" name="{html.escape(q["qcm_id"])}" '
                    f'value="{k}"> {html.escape(str(option))}</label>'
                )
            blocs.append('<div class="actions"><button type="button">Corriger</button>'
                         '<span class="verdict" aria-live="polite"></span></div>')
            details = []
            if q.get("section"):
                details.append(f"<p><strong>Section :</strong> {html.escape(q['section'])}</p>")
            if q.get("passage"):
                details.append(f'<p class="source">{html.escape(q["passage"])}</p>')
            if q.get("justification"):
                details.append(f"<p><strong>Justification du générateur :</strong> "
                               f"{html.escape(q['justification'])}</p>")
            if details:
                blocs.append("<details><summary>Passage source</summary>" + "".join(details) + "</details>")
            blocs.append("</section>")
    blocs.append(f"<script>{JS}</script></body></html>")
    return "\n".join(blocs)


# --------------------------------------------------------------------------- #
# 3. CSV
# --------------------------------------------------------------------------- #
COLONNES = ["qcm_id", "methode", "cours_id", "section", "question", "A", "B", "C", "D",
            "bonne_reponse", "index_correct", "justification"]


def en_csv(qcm: list[dict]) -> list[list]:
    """Une ligne par QCM, options éclatées en colonnes A à D."""
    lignes = []
    for q in qcm:
        lignes.append([
            q["qcm_id"], q.get("methode", ""), q.get("cours_id", ""), q["section"],
            q["question"], *q["options"], q["reponse"], q["index_correct"],
            q.get("justification", ""),
        ])
    return lignes


# --------------------------------------------------------------------------- #
def exporter(qcm: list[dict], dossier: Path, titre: str,
             avec_gift: bool = True, avec_html: bool = True) -> dict[str, Path]:
    """Écrit les exports demandés et renvoie leurs chemins."""
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits: dict[str, Path] = {}

    if avec_gift:
        chemin = dossier / "qcm_moodle_gift.txt"
        chemin.write_text(en_gift(qcm, titre), encoding="utf-8")
        ecrits["gift"] = chemin

    if avec_html:
        chemin = dossier / "qcm.html"
        chemin.write_text(en_html(qcm, titre), encoding="utf-8")
        ecrits["html"] = chemin

    chemin = dossier / "qcm.csv"
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        # separateur « ; » et BOM UTF-8 : double-clic sous Excel en français
        w = csv.writer(f, delimiter=";")
        w.writerow(COLONNES)
        w.writerows(en_csv(qcm))
    ecrits["csv"] = chemin
    return ecrits


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entree", type=Path, default=ROOT / "outputs" / "qcm" / "qcm_acceptes.jsonl",
                   help="QCM à exporter (JSONL, défaut : les QCM acceptés)")
    p.add_argument("--passages", type=Path, default=ROOT / "data" / "processed" / "passages.jsonl",
                   help="passages du cours, pour afficher la section et le texte source")
    p.add_argument("--sortie", type=Path, default=ROOT / "outputs" / "export",
                   help="dossier de destination")
    p.add_argument("--titre", default="QCM TALN — langage C",
                   help="titre affiché dans le HTML et les catégories GIFT")
    p.add_argument("--limite", type=int, default=0,
                   help="n'exporter que les N premiers QCM (0 = tous)")
    p.add_argument("--sans-gift", action="store_true", help="ne pas écrire le fichier Moodle")
    p.add_argument("--sans-html", action="store_true", help="ne pas écrire la page HTML")
    args = p.parse_args(argv)

    try:
        qcm = preparer(charger_jsonl(args.entree), charger_passages(args.passages))
    except (FileNotFoundError, ValueError) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 1

    if args.limite > 0:
        qcm = qcm[: args.limite]

    ecrits = exporter(qcm, args.sortie, args.titre,
                      avec_gift=not args.sans_gift, avec_html=not args.sans_html)

    par_methode = {}
    for q in qcm:
        par_methode[q.get("methode", "?")] = par_methode.get(q.get("methode", "?"), 0) + 1
    print(f"{len(qcm)} QCM exportés ({', '.join(f'{m} : {n}' for m, n in sorted(par_methode.items()))})")
    for nom, chemin in ecrits.items():
        print(f"  {nom:4s} {chemin.relative_to(ROOT) if chemin.is_relative_to(ROOT) else chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
