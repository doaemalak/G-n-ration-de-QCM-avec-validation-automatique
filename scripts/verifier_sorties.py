#!/usr/bin/env python3
"""Vérifie la cohérence des artefacts versionnés du projet.

Le notebook produit une dizaine de fichiers (JSONL, CSV, figures). Quand les QCM
du LLM arrivent, ou quand une cellule est réexécutée, ces fichiers peuvent se
désynchroniser sans que rien ne le signale : un QCM accepté qui n'a pas passé V2,
un cache plus vieux que ``validation.csv``, un identifiant de passage disparu…

Ce script relit les sorties **telles qu'elles sont versionnées** et contrôle
leurs invariants. Il ne recalcule aucun modèle et ne demande ni GPU, ni PDF :
il tourne en une seconde, y compris en intégration continue.

    python3 scripts/verifier_sorties.py          # rapport lisible
    python3 scripts/verifier_sorties.py --strict # les avertissements échouent aussi

Code de sortie : 0 si aucune erreur, 1 sinon.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QCM_DIR = ROOT / "outputs" / "qcm"
FIG_DIR = ROOT / "outputs" / "figures"
DATA_DIR = ROOT / "data"

CATEGORIES_REJET = {
    "texte source dégradé", "défaut de forme", "réponse introuvable",
    "bonne réponse non confirmée", "distracteur proche de la réponse",
    "distracteur confirmé sans être proche",
}

FICHIERS_ATTENDUS = [
    "README.md",
    "requirements.txt",
    "notebooks/QCM_generation_validation.ipynb",
    "data/raw/sources.csv",
    "data/processed/corpus_nettoye.jsonl",
    "data/processed/passages.jsonl",
    "data/processed/echantillon.csv",
    "data/annotations/GUIDE_ANNOTATION.md",
    "outputs/qcm/qcm_base.jsonl",
    "outputs/qcm/qcm_acceptes.jsonl",
    "outputs/qcm/qcm_rejetes.jsonl",
    "outputs/qcm/validation.csv",
    "outputs/qcm/controles_forme.csv",
    "outputs/qcm/scores_validateur.jsonl",
    "outputs/qcm/scores_ablation.jsonl",
    "outputs/qcm/typologie_rejets.csv",
    "outputs/qcm/sensibilite_seuils.csv",
    "outputs/figures/nettoyage_lignes.png",
    "outputs/figures/longueur_passages.png",
    "outputs/figures/v1_controle_negatif.png",
    "outputs/figures/filtre_motifs.png",
    "outputs/figures/sensibilite_seuils.png",
]


class Rapport:
    """Collecte les erreurs (bloquantes) et les avertissements (à relire)."""

    def __init__(self) -> None:
        self.erreurs: list[str] = []
        self.avertissements: list[str] = []
        self.controles = 0

    def erreur(self, message: str) -> None:
        self.erreurs.append(message)

    def avertir(self, message: str) -> None:
        self.avertissements.append(message)

    def verifier(self, condition: bool, message: str) -> bool:
        """Enregistre une erreur si la condition est fausse."""
        self.controles += 1
        if not condition:
            self.erreur(message)
        return condition

    def afficher(self, strict: bool = False) -> int:
        print(f"{self.controles} contrôles effectués.")
        for message in self.avertissements:
            print(f"  ⚠ {message}")
        for message in self.erreurs:
            print(f"  ✘ {message}")
        if self.erreurs:
            print(f"\n{len(self.erreurs)} erreur(s) : les sorties ne sont pas cohérentes.")
            return 1
        if strict and self.avertissements:
            print(f"\n{len(self.avertissements)} avertissement(s) et mode --strict : échec.")
            return 1
        print("\n✔ Toutes les sorties sont cohérentes.")
        return 0


# --------------------------------------------------------------------------- #
# Lecture tolérante : un fichier absent est signalé une fois, pas à chaque test
# --------------------------------------------------------------------------- #
def lire_jsonl(chemin: Path, rapport: Rapport) -> list[dict]:
    if not chemin.exists():
        rapport.erreur(f"{chemin.relative_to(ROOT)} est absent")
        return []
    try:
        with chemin.open(encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except json.JSONDecodeError as e:
        rapport.erreur(f"{chemin.relative_to(ROOT)} : JSON invalide ({e})")
        return []


def lire_csv(chemin: Path, rapport: Rapport, **kw) -> list[dict]:
    if not chemin.exists():
        rapport.erreur(f"{chemin.relative_to(ROOT)} est absent")
        return []
    with chemin.open(encoding=kw.pop("encoding", "utf-8"), newline="") as f:
        return list(csv.DictReader(f, **kw))


def en_bool(valeur: str) -> bool:
    return str(valeur).strip().lower() in {"true", "1", "vrai", "oui", "yes"}


def nombre(valeur: str) -> float:
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return math.nan


def quantile(valeurs: list[float], q: float) -> float:
    """Quantile par interpolation linéaire, comme ``numpy.quantile`` (méthode par défaut)."""
    ordonnees = sorted(valeurs)
    if not ordonnees:
        return math.nan
    position = (len(ordonnees) - 1) * q
    bas = math.floor(position)
    haut = math.ceil(position)
    if bas == haut:
        return ordonnees[bas]
    return ordonnees[bas] + (ordonnees[haut] - ordonnees[bas]) * (position - bas)


# --------------------------------------------------------------------------- #
def verifier_fichiers(rapport: Rapport) -> None:
    for relatif in FICHIERS_ATTENDUS:
        chemin = ROOT / relatif
        rapport.verifier(chemin.exists(), f"{relatif} est absent")
        if chemin.exists():
            rapport.verifier(chemin.stat().st_size > 0, f"{relatif} est vide")


def verifier_passages(rapport: Rapport) -> tuple[dict[str, dict], list[dict]]:
    passages = lire_jsonl(DATA_DIR / "processed" / "passages.jsonl", rapport)
    if not passages:
        return {}, []
    index = {}
    for p in passages:
        rapport.verifier(p.get("passage_id") not in index,
                         f"passage_id en double : {p.get('passage_id')}")
        index[p.get("passage_id")] = p
        for champ in ("passage_id", "cours_id", "section", "texte", "n_mots"):
            if champ not in p:
                rapport.erreur(f"passage {p.get('passage_id', '?')} : champ {champ} manquant")
        rapport.verifier(isinstance(p.get("n_mots"), int) and p.get("n_mots", 0) > 0,
                         f"passage {p.get('passage_id')} : n_mots invalide")

    echantillon = lire_csv(DATA_DIR / "processed" / "echantillon.csv", rapport)
    if echantillon:
        ids = [ligne["passage_id"] for ligne in echantillon]
        rapport.verifier(len(ids) == len(set(ids)), "echantillon.csv contient des passages en double")
        rapport.verifier(all(i in index for i in ids),
                         "echantillon.csv référence un passage absent de passages.jsonl")
        par_cours = Counter(ligne["cours_id"] for ligne in echantillon)
        rapport.verifier(len(par_cours) == 6, f"echantillon.csv couvre {len(par_cours)} cours au lieu de 6")
        tailles = {c: n for c, n in par_cours.items()}
        rapport.verifier(len(set(tailles.values())) == 1,
                         f"echantillon.csv n'est pas équilibré par cours : {tailles}")
    return index, echantillon


def verifier_qcm(rapport: Rapport, passages: dict[str, dict]) -> dict[str, list[dict]]:
    """Contrôle les QCM de chaque fichier et renvoie {nom: liste}."""
    noms = ["qcm_base", "qcm_acceptes", "qcm_rejetes"]
    if (QCM_DIR / "qcm_llm.jsonl").exists():
        noms.append("qcm_llm")
    fichiers = {nom: lire_jsonl(QCM_DIR / f"{nom}.jsonl", rapport) for nom in noms}

    for nom, qcm in fichiers.items():
        if not qcm:
            continue
        ids = [q.get("qcm_id") for q in qcm]
        rapport.verifier(len(ids) == len(set(ids)), f"{nom}.jsonl : qcm_id en double")
        for q in qcm:
            qid = q.get("qcm_id", "?")
            manquants = [k for k in ("qcm_id", "methode", "passage_id", "cours_id",
                                     "question", "options", "index_correct", "reponse") if k not in q]
            if manquants:
                rapport.erreur(f"{nom}.jsonl, {qid} : champ(s) manquant(s) {manquants}")
                continue
            options = q["options"]
            rapport.verifier(isinstance(options, list) and len(options) == 4,
                             f"{nom}.jsonl, {qid} : 4 options attendues")
            if not isinstance(options, list) or len(options) != 4:
                continue
            rapport.verifier(all(isinstance(o, str) and o.strip() for o in options),
                             f"{nom}.jsonl, {qid} : option vide")
            rapport.verifier(len({o.strip().lower() for o in options}) == 4,
                             f"{nom}.jsonl, {qid} : options en double")
            rapport.verifier(q["index_correct"] in range(4),
                             f"{nom}.jsonl, {qid} : index_correct hors de 0-3")
            if q["index_correct"] in range(4):
                rapport.verifier(options[q["index_correct"]] == q["reponse"],
                                 f"{nom}.jsonl, {qid} : reponse différente de options[index_correct]")
            rapport.verifier(bool(str(q["question"]).strip()), f"{nom}.jsonl, {qid} : question vide")
            if passages:
                p = passages.get(q["passage_id"])
                rapport.verifier(p is not None,
                                 f"{nom}.jsonl, {qid} : passage_id {q['passage_id']} inconnu")
                if p:
                    rapport.verifier(p["cours_id"] == q["cours_id"],
                                     f"{nom}.jsonl, {qid} : cours_id {q['cours_id']} ≠ "
                                     f"{p['cours_id']} du passage")

    # Un QCM rejeté doit expliquer pourquoi ; un accepté ne doit rien avoir à justifier.
    for q in fichiers.get("qcm_rejetes", []):
        rapport.verifier(bool(q.get("motifs")), f"QCM rejeté {q.get('qcm_id')} sans motif")
    for q in fichiers.get("qcm_acceptes", []):
        rapport.verifier(not q.get("motifs"), f"QCM accepté {q.get('qcm_id')} avec des motifs d'échec")
    for q in fichiers.get("qcm_base", []):
        rapport.verifier(q.get("methode") == "base", f"qcm_base.jsonl : {q.get('qcm_id')} n'est pas de méthode base")
    for q in fichiers.get("qcm_llm", []):
        rapport.verifier(q.get("methode") == "llm", f"qcm_llm.jsonl : {q.get('qcm_id')} n'est pas de méthode llm")

    # Les deux générateurs partagent le même échantillon : base et LLM ne se recouvrent pas.
    base = {q.get("passage_id") for q in fichiers.get("qcm_base", [])}
    llm = {q.get("passage_id") for q in fichiers.get("qcm_llm", [])}
    if llm:
        rapport.verifier(not (base & llm),
                         f"{len(base & llm)} passage(s) produisent à la fois un QCM base et un QCM LLM "
                         "(identifiants différents attendus : BASE_x / LLM_x)")
    return fichiers


def verifier_validation(rapport: Rapport, fichiers: dict[str, list[dict]]) -> None:
    lignes = lire_csv(QCM_DIR / "validation.csv", rapport)
    if not lignes:
        return
    colonnes = {"qcm_id", "methode", "cours_id", "index_correct", "qa_score", "qa_score_neg",
                "implication", "V1", "V2", "V3", "forme_ok"}
    manquantes = colonnes - set(lignes[0])
    if manquantes:
        rapport.erreur(f"validation.csv : colonne(s) manquante(s) {sorted(manquantes)}")
        return

    ids = [l["qcm_id"] for l in lignes]
    rapport.verifier(len(ids) == len(set(ids)), "validation.csv : qcm_id en double")

    tous = fichiers.get("qcm_base", []) + fichiers.get("qcm_llm", [])
    if tous:
        attendus = {q["qcm_id"] for q in tous}
        rapport.verifier(set(ids) == attendus,
                         "validation.csv ne couvre pas exactement les QCM générés "
                         f"({len(attendus - set(ids))} manquant(s), {len(set(ids) - attendus)} en trop)")

    acceptes = {q["qcm_id"] for q in fichiers.get("qcm_acceptes", [])}
    rejetes = {q["qcm_id"] for q in fichiers.get("qcm_rejetes", [])}
    if acceptes or rejetes:
        rapport.verifier(not (acceptes & rejetes), "un QCM est à la fois accepté et rejeté")
        rapport.verifier(set(ids) == acceptes | rejetes,
                         "qcm_acceptes + qcm_rejetes ne couvrent pas les lignes de validation.csv")

    # Seuil V1 de l'étape 7.3 : 95e centile des scores du contrôle négatif, lu dans le fichier.
    negatifs = [nombre(l["qa_score_neg"]) for l in lignes if not math.isnan(nombre(l["qa_score_neg"]))]
    seuil_v1 = quantile(negatifs, 0.95) if negatifs else math.nan

    for ligne in lignes:
        qid = ligne["qcm_id"]
        forme, v1, v2, v3 = (en_bool(ligne[k]) for k in ("forme_ok", "V1", "V2", "V3"))
        attendu = forme and v1 and v2 and v3
        if acceptes or rejetes:
            rapport.verifier((qid in acceptes) == attendu,
                             f"{qid} : accepté={qid in acceptes} mais forme ET V1 ET V2 ET V3 = {attendu}")
        try:
            implication = json.loads(ligne["implication"])
        except json.JSONDecodeError:
            rapport.erreur(f"{qid} : colonne implication illisible")
            continue
        if not (isinstance(implication, list) and len(implication) == 4):
            rapport.erreur(f"{qid} : 4 probabilités d'implication attendues")
            continue

        # Colonnes dérivées : elles doivent se recalculer exactement depuis implication.
        c = int(ligne["index_correct"])
        rapport.verifier(0 <= c < 4, f"{qid} : index_correct hors de 0-3")
        if 0 <= c < 4:
            rapport.verifier(math.isclose(nombre(ligne["imp_bonne"]), implication[c], abs_tol=1e-6),
                             f"{qid} : imp_bonne ≠ implication[index_correct]")
            dist = max(v for k, v in enumerate(implication) if k != c)
            rapport.verifier(math.isclose(nombre(ligne["imp_max_distracteur"]), dist, abs_tol=1e-6),
                             f"{qid} : imp_max_distracteur ≠ maximum des distracteurs")
        prefere = int(nombre(ligne["option_preferee"]))
        rapport.verifier(prefere in range(4) and implication[prefere] == max(implication),
                         f"{qid} : option_preferee n'est pas l'option de plus forte implication")
        if v2:
            rapport.verifier(prefere == c,
                             f"{qid} : V2 vrai alors que l'option préférée ({prefere}) n'est pas la bonne ({c})")
        if not math.isnan(seuil_v1) and not math.isnan(nombre(ligne["qa_score"])):
            rapport.verifier(v1 == (nombre(ligne["qa_score"]) >= seuil_v1 - 1e-9),
                             f"{qid} : V1 incohérent avec le seuil du contrôle négatif ({seuil_v1:.3f})")
        rapport.verifier(ligne["cours_id"] and ligne["methode"], f"{qid} : cours_id ou methode vide")


def verifier_forme(rapport: Rapport, fichiers: dict[str, list[dict]]) -> None:
    lignes = lire_csv(QCM_DIR / "controles_forme.csv", rapport)
    if not lignes:
        return
    regles = [c for c in lignes[0] if c.startswith("F")]
    rapport.verifier(len(regles) == 7, f"controles_forme.csv : {len(regles)} règles au lieu de 7")
    rapport.verifier("forme_ok" in lignes[0], "controles_forme.csv : colonne forme_ok absente")
    ids = [l["qcm_id"] for l in lignes]
    rapport.verifier(len(ids) == len(set(ids)), "controles_forme.csv : qcm_id en double")

    tous = fichiers.get("qcm_base", []) + fichiers.get("qcm_llm", [])
    if tous:
        rapport.verifier(set(ids) == {q["qcm_id"] for q in tous},
                         "controles_forme.csv ne couvre pas exactement les QCM générés")

    for ligne in lignes:
        defauts = [r for r in regles if en_bool(ligne[r])]
        rapport.verifier(en_bool(ligne["forme_ok"]) == (not defauts),
                         f"{ligne['qcm_id']} : forme_ok incohérent avec les règles {defauts}")

    # La forme est calculée sur les mêmes QCM dans validation.csv : les deux doivent concorder.
    validation = {l["qcm_id"]: l for l in lire_csv(QCM_DIR / "validation.csv", rapport)}
    for ligne in lignes:
        v = validation.get(ligne["qcm_id"])
        if v:
            rapport.verifier(en_bool(ligne["forme_ok"]) == en_bool(v["forme_ok"]),
                             f"{ligne['qcm_id']} : forme_ok diffère entre les deux fichiers")


def verifier_caches(rapport: Rapport, fichiers: dict[str, list[dict]]) -> None:
    tous = fichiers.get("qcm_base", []) + fichiers.get("qcm_llm", [])
    ids = {q["qcm_id"] for q in tous}

    scores = lire_jsonl(QCM_DIR / "scores_validateur.jsonl", rapport)
    if scores:
        rapport.verifier(len(scores) == len({s.get("qcm_id") for s in scores}),
                         "scores_validateur.jsonl : qcm_id en double")
        if ids:
            rapport.verifier(ids <= {s.get("qcm_id") for s in scores},
                             "scores_validateur.jsonl ne couvre pas tous les QCM générés")
        signatures = {json.dumps(s.get("signature"), sort_keys=True) for s in scores}
        rapport.verifier(len(signatures) == 1,
                         f"scores_validateur.jsonl mélange {len(signatures)} signatures de modèles : "
                         "les scores ne sont pas comparables")
        for s in scores:
            rapport.verifier(isinstance(s.get("implication"), list) and len(s["implication"]) == 4,
                             f"scores_validateur.jsonl, {s.get('qcm_id')} : implication invalide")
            for champ in ("qa_score", "qa_score_neg"):
                rapport.verifier(not math.isnan(nombre(s.get(champ))),
                                 f"scores_validateur.jsonl, {s.get('qcm_id')} : {champ} non numérique")

    ablations = lire_jsonl(QCM_DIR / "scores_ablation.jsonl", rapport)
    if ablations:
        rapport.verifier(len(ablations) == len({a.get("qcm_id") for a in ablations}),
                         "scores_ablation.jsonl : qcm_id en double")
        if ids:
            rapport.verifier(ids <= {a.get("qcm_id") for a in ablations},
                             "scores_ablation.jsonl ne couvre pas tous les QCM générés")
        for a in ablations:
            for champ, valeur in a.items():
                if champ == "qcm_id":
                    continue
                if isinstance(valeur, list):
                    rapport.verifier(len(valeur) == 4,
                                     f"scores_ablation.jsonl, {a['qcm_id']} : {champ} n'a pas 4 valeurs")


def verifier_tableaux(rapport: Rapport) -> None:
    typo = lire_csv(QCM_DIR / "typologie_rejets.csv", rapport)
    if typo:
        inconnues = {l["categorie"] for l in typo} - CATEGORIES_REJET
        rapport.verifier(not inconnues, f"typologie_rejets.csv : catégorie(s) inconnue(s) {sorted(inconnues)}")
        rapport.verifier(len({l["qcm_id"] for l in typo}) == len(typo),
                         "typologie_rejets.csv : QCM classé deux fois")

    sens = lire_csv(QCM_DIR / "sensibilite_seuils.csv", rapport)
    if sens:
        rapport.verifier(len({l["seuil"] for l in sens}) == 3,
                         "sensibilite_seuils.csv : 3 seuils attendus (V1, V2, V3)")
        for ligne in sens:
            v = nombre(ligne["% acceptés"])
            rapport.verifier(not math.isnan(v) and 0 <= v <= 100,
                             f"sensibilite_seuils.csv : taux d'acceptation invalide ({ligne['% acceptés']})")


def verifier_livrables(rapport: Rapport) -> None:
    article = ROOT / "docs" / "article" / "article.md"
    if not article.exists():
        rapport.avertir("docs/article/article.md (LIVRABLE 2) n'existe pas encore")
    else:
        texte = article.read_text(encoding="utf-8")
        restes = texte.count("À COMPLÉTER")
        if restes:
            rapport.avertir(f"article.md contient encore {restes} marqueur(s) « À COMPLÉTER »")

    llm = QCM_DIR / "qcm_llm.jsonl"
    if not llm.exists():
        rapport.avertir("QCM du LLM absents (étape 5) : la comparaison base / LLM et l'évaluation "
                        "humaine ne peuvent pas être finalisées")
    grilles = sorted((DATA_DIR / "annotations").glob("grille_evaluateur_*.csv"))
    if len(grilles) < 2:
        rapport.avertir("grilles d'annotation absentes : les étapes 9.4, 9.5 et 11.4 restent vides")


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--strict", action="store_true", help="échouer aussi sur les avertissements")
    args = p.parse_args(argv)

    rapport = Rapport()
    verifier_fichiers(rapport)
    passages, _ = verifier_passages(rapport)
    fichiers = verifier_qcm(rapport, passages)
    verifier_validation(rapport, fichiers)
    verifier_forme(rapport, fichiers)
    verifier_caches(rapport, fichiers)
    verifier_tableaux(rapport)
    verifier_livrables(rapport)
    return rapport.afficher(strict=args.strict)


if __name__ == "__main__":
    sys.exit(principal())
