#!/usr/bin/env python3
"""Régénère les tableaux de résultats de l'article depuis les sorties du notebook.

L'article (``docs/article/article.md``) cite des chiffres produits par le
notebook. Quand les QCM du LLM arrivent, quand les grilles d'annotation sont
remplies ou quand un seuil change, ces chiffres doivent être mis à jour. Ce
script les recalcule **directement depuis les fichiers** et écrit
``docs/article/resultats_auto.md`` : plus de copier-coller manuel, donc plus de
tableau périmé.

Ce qui est produit
------------------
- données : corpus et passages ;
- génération : couverture et rendement par méthode (base, LLM si présent) ;
- contrôles de forme et validateur : taux par règle et par test ;
- cascade des motifs de rejet et typologie des rejets ;
- ablations (contrôles, modèles QA/NLI) et sensibilité aux seuils ;
- biais de longueur ;
- évaluation humaine (kappa, apport du filtre) **si** les grilles existent.

Le script ne relance aucun modèle : il lit uniquement les caches et les CSV
versionnés, comme ``scripts/verifier_sorties.py``. Il utilise pandas, numpy,
scipy et scikit-learn, déjà présents dans ``requirements.txt``.

    python3 scripts/tableaux_resultats.py
    python3 scripts/tableaux_resultats.py --sortie /tmp/resultats.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score, roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
QCM_DIR = ROOT / "outputs" / "qcm"
DATA_DIR = ROOT / "data"

# Seuils du validateur, choisis à l'étape 7 (sections 7.3 et 7.4 du notebook).
# Ils sont répétés ici parce que le notebook ne les écrit pas dans un fichier ;
# l'assertion de `decisions()` vérifie qu'ils reproduisent bien les décisions
# enregistrées dans validation.csv.
CENTILE_V1 = 0.95
IMP_MIN_V2 = 0.5
IMP_MAX_V3 = 0.9

REGLES_FORME = ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]
ORDRE_CONTROLES = ["forme", "V1", "V2", "V3"]


# --------------------------------------------------------------------------- #
# Utilitaires
# --------------------------------------------------------------------------- #
def lire_jsonl(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def charger() -> dict:
    """Charge tout ce dont les tableaux ont besoin, en tolérant l'absence du LLM."""
    passages = pd.DataFrame(lire_jsonl(DATA_DIR / "processed" / "passages.jsonl"))
    sources = pd.read_csv(DATA_DIR / "raw" / "sources.csv")
    validation = pd.read_csv(QCM_DIR / "validation.csv")
    validation["implication"] = validation["implication"].apply(json.loads)

    base = pd.DataFrame(lire_jsonl(QCM_DIR / "qcm_base.jsonl"))
    llm = pd.DataFrame(lire_jsonl(QCM_DIR / "qcm_llm.jsonl"))
    qcm = pd.concat([d for d in (base, llm) if not d.empty], ignore_index=True)

    forme = pd.read_csv(QCM_DIR / "controles_forme.csv")
    ablation = pd.DataFrame(lire_jsonl(QCM_DIR / "scores_ablation.jsonl"))
    typologie = pd.read_csv(QCM_DIR / "typologie_rejets.csv")
    sensibilite = pd.read_csv(QCM_DIR / "sensibilite_seuils.csv")

    if qcm.empty:
        raise SystemExit("Aucun QCM trouvé : lancer le notebook jusqu'à l'étape 8.")
    if len(validation) != len(qcm):
        raise SystemExit(
            f"validation.csv ({len(validation)} QCM) et les QCM générés ({len(qcm)}) "
            "ne concordent pas : réexécuter l'étape 7 du notebook."
        )
    return {"passages": passages, "sources": sources, "validation": validation,
            "base": base, "llm": llm, "qcm": qcm, "forme": forme,
            "ablation": ablation, "typologie": typologie, "sensibilite": sensibilite}


def markdown(df: pd.DataFrame, index: bool = False) -> str:
    """Tableau Markdown sans dépendre de ``tabulate``.

    Un index nommé (méthode, catégorie…) porte une information : il est remis
    en colonne. Un simple index de ligne (RangeIndex) est laissé de côté.
    """
    donnees = df.reset_index() if (index or not isinstance(df.index, pd.RangeIndex)) else df.copy()
    colonnes = [str(c) for c in donnees.columns]
    lignes = ["| " + " | ".join(colonnes) + " |",
              "|" + "|".join("---" for _ in colonnes) + "|"]
    for _, ligne in donnees.iterrows():
        cellules = []
        for valeur in ligne:
            if isinstance(valeur, float):
                cellules.append("—" if np.isnan(valeur) else f"{valeur:g}".replace(".", ","))
            else:
                cellules.append(str(valeur))
        lignes.append("| " + " | ".join(cellules) + " |")
    return "\n".join(lignes)


def fr(valeur: float, decimales: int = 1) -> str:
    """Nombre au format français (virgule décimale), pour les cellules texte."""
    return f"{valeur:.{decimales}f}".replace(".", ",")


def methodes(donnees: dict) -> list[str]:
    return sorted(donnees["validation"]["methode"].unique())


# --------------------------------------------------------------------------- #
# Tableaux
# --------------------------------------------------------------------------- #
def tableau_donnees(donnees: dict) -> tuple[str, pd.DataFrame]:
    src, pas = donnees["sources"], donnees["passages"]
    par_cours = pas.groupby("cours_id").agg(
        passages=("passage_id", "count"), mots_moyens=("n_mots", "mean"),
        tokens_max=("n_tokens", "max"))
    df = (src.set_index("id")[["titre", "auteur", "format", "n_pages", "n_mots_brut",
                               "n_mots_nettoye", "%_retire"]]
          .join(par_cours))
    df["mots_moyens"] = df["mots_moyens"].round(0).astype("Int64")
    df = df.rename(columns={"titre": "Titre", "auteur": "Auteur", "format": "Format",
                            "n_pages": "Pages", "n_mots_brut": "Mots brut",
                            "n_mots_nettoye": "Mots nettoyés", "%_retire": "% retiré",
                            "passages": "Passages", "mots_moyens": "Mots/passage",
                            "tokens_max": "Tokens max"})
    total = pd.DataFrame([{
        "Titre": "Total", "Auteur": f"{len(src)} cours", "Format": "",
        "Pages": int(src["n_pages"].sum()), "Mots brut": int(src["n_mots_brut"].sum()),
        "Mots nettoyés": int(src["n_mots_nettoye"].sum()),
        "% retiré": round(100 * (1 - src["n_mots_nettoye"].sum() / src["n_mots_brut"].sum()), 1),
        "Passages": len(pas), "Mots/passage": int(pas["n_mots"].mean()),
        "Tokens max": int(pas["n_tokens"].max()),
    }], index=["Total"])
    df = pd.concat([df, total[df.columns]]).fillna("")
    return "Tableau 1 — Corpus et passages", df
    return "Tableau 1 — Corpus et passages", df


def tableau_generation(donnees: dict) -> tuple[str, pd.DataFrame]:
    """Couverture et rendement : ce que l'enseignant récupère vraiment."""
    val = donnees["validation"].copy()
    val["accepte"] = val[["forme_ok", "V1", "V2", "V3"]].all(axis=1)
    n_passages = len(pd.read_csv(DATA_DIR / "processed" / "echantillon.csv"))
    lignes = []
    for m in methodes(donnees):
        g = val[val["methode"] == m]
        lignes.append({
            "Méthode": m,
            "Passages testés": n_passages,
            "QCM produits": len(g),
            "Couverture (%)": round(100 * len(g) / n_passages, 1),
            "Acceptés": int(g["accepte"].sum()),
            "Taux d'acceptation (%)": round(100 * g["accepte"].mean(), 1),
            "QCM acceptés / passages (%)": round(100 * g["accepte"].sum() / n_passages, 1),
        })
    df = pd.DataFrame(lignes).set_index("Méthode")
    note = ("" if not donnees["llm"].empty else
            "\n> QCM du LLM absents (étape 5 non exécutée sur GPU) : la comparaison "
            "base / LLM reste à compléter.")
    return "Tableau 2 — Couverture et rendement par méthode" + note, df


def tableau_forme(donnees: dict) -> tuple[str, pd.DataFrame]:
    forme = donnees["forme"]
    lignes = []
    colonnes = {r: next((c for c in forme.columns if c.startswith(r + " ")), None)
                for r in REGLES_FORME}
    for m, g in forme.groupby("methode"):
        ligne = {"Méthode": m}
        for r, colonne in colonnes.items():
            ligne[r] = round(100 * g[colonne].mean(), 1) if colonne else np.nan
        ligne["Conformes (%)"] = round(100 * g["forme_ok"].mean(), 1)
        lignes.append(ligne)
    return "Tableau 3 — Défauts de forme détectés (% des QCM de la méthode)", \
        pd.DataFrame(lignes).set_index("Méthode")


def tableau_validateur(donnees: dict) -> tuple[str, pd.DataFrame]:
    val = donnees["validation"]
    lignes = []
    for m in methodes(donnees):
        g = val[val["methode"] == m]
        lignes.append({
            "Méthode": m,
            "V1 répondabilité": round(100 * g["V1"].mean(), 1),
            "V2 bonne réponse unique": round(100 * g["V2"].mean(), 1),
            "V3 aucun distracteur correct": round(100 * g["V3"].mean(), 1),
            "V1 et V2 et V3": round(100 * g["semantique_ok"].mean(), 1),
        })
    return "Tableau 4 — Taux de passage de chaque test (% des QCM)", \
        pd.DataFrame(lignes).set_index("Méthode")


def tableau_cascade(donnees: dict) -> tuple[str, pd.DataFrame]:
    """Motif du rejet : premier contrôle échoué, dans l'ordre forme → V1 → V2 → V3."""
    val = donnees["validation"].copy()
    forme = donnees["forme"].set_index("qcm_id")
    val["forme_ok"] = val["qcm_id"].map(forme["forme_ok"])
    val["accepte"] = val[["forme_ok", "V1", "V2", "V3"]].all(axis=1)

    def premier(r):
        for controle in ORDRE_CONTROLES:
            if not r["forme_ok" if controle == "forme" else controle]:
                return controle
        return "accepté"

    val["motif"] = val.apply(premier, axis=1)
    df = (pd.crosstab(val["methode"], val["motif"])
          .reindex(columns=ORDRE_CONTROLES + ["accepté"], fill_value=0))
    df.index.name = "Méthode"
    df = df.rename(columns={"forme": "forme (F1–F7)", "accepté": "accepté"})
    return "Tableau 5 — Cascade des rejets (nombre de QCM)", df


def tableau_typologie(donnees: dict) -> tuple[str, pd.DataFrame]:
    typo = donnees["typologie"]
    ordre = ["texte source dégradé", "défaut de forme", "réponse introuvable",
             "bonne réponse non confirmée", "distracteur proche de la réponse",
             "distracteur confirmé sans être proche"]
    df = (pd.crosstab(typo["categorie"], typo["methode"])
          .reindex(ordre, fill_value=0))
    df["Total"] = df.sum(axis=1)
    df.loc["Total"] = df.sum()
    df.index.name = "Catégorie"
    return "Tableau 6 — Typologie des rejets (nombre de QCM)", df


def decisions(donnees: dict, controles=("forme", "V1", "V2", "V3"),
              centile: float = CENTILE_V1, v2: float = IMP_MIN_V2,
              v3: float = IMP_MAX_V3, implication: np.ndarray | None = None) -> pd.Series:
    """Recalcule la décision du filtre, comme la cellule 10.1 du notebook."""
    val = donnees["validation"]
    imp = np.array(val["implication"].tolist()) if implication is None else implication
    c = val["index_correct"].to_numpy()
    r = np.arange(len(c))
    tests = {
        "forme": donnees["forme"].set_index("qcm_id").loc[val["qcm_id"], "forme_ok"].to_numpy(bool),
        "V1": val["qa_score"].to_numpy() >= np.quantile(val["qa_score_neg"], centile),
        "V2": (imp.argmax(axis=1) == c) & (imp[r, c] >= v2),
        "V3": np.where(np.eye(4, dtype=bool)[c], -1, imp).max(axis=1) < v3,
    }
    accepte = np.ones(len(val), dtype=bool)
    for controle in controles:
        accepte &= tests[controle]
    return pd.Series(accepte, index=val["qcm_id"])


def tableau_ablation_controles(donnees: dict) -> tuple[str, pd.DataFrame]:
    val = donnees["validation"]
    tous = ("forme", "V1", "V2", "V3")
    variantes = {"filtre complet": tous}
    variantes.update({f"sans {t}": tuple(x for x in tous if x != t) for t in tous})
    variantes["forme seule"] = ("forme",)
    variantes["aucun filtre"] = ()

    # Les seuils codés ici doivent reproduire exactement les décisions de l'étape 8.
    reference = pd.read_csv(QCM_DIR / "validation.csv")
    reference["accepte"] = reference[["forme_ok", "V1", "V2", "V3"]].all(axis=1)
    calcule = decisions(donnees).to_numpy()
    if not np.array_equal(calcule, reference.set_index("qcm_id").loc[val["qcm_id"], "accepte"].to_numpy()):
        raise SystemExit(
            "Les seuils de scripts/tableaux_resultats.py ne reproduisent pas les décisions de "
            "validation.csv. Mettre à jour CENTILE_V1 / IMP_MIN_V2 / IMP_MAX_V3 d'après l'étape 7."
        )

    lignes = []
    for nom, ctrl in variantes.items():
        acc = decisions(donnees, controles=ctrl)
        ligne = {"Variante": nom}
        for m in methodes(donnees):
            masque = val["methode"] == m
            ligne[f"% acceptés ({m})"] = round(100 * acc[masque.to_numpy()].mean(), 1)
        ligne["% acceptés (total)"] = round(100 * acc.mean(), 1)
        lignes.append(ligne)
    return "Tableau 7 — Ablation des contrôles du filtre (taux d'acceptation)", \
        pd.DataFrame(lignes).set_index("Variante")


def tableau_ablation_modeles(donnees: dict) -> tuple[str, pd.DataFrame]:
    val, abl = donnees["validation"], donnees["ablation"]
    if abl.empty:
        return "Tableau 8 — Ablations de modèles (indisponible)", pd.DataFrame()
    # Les QCM du LLM peuvent être plus récents que le cache d'ablation : on aligne,
    # les lignes manquantes deviennent NaN et sont signalées par « — ».
    abl = abl.set_index("qcm_id").reindex(val["qcm_id"]).reset_index()
    imp = np.array(val["implication"].tolist())
    c = val["index_correct"].to_numpy()
    r = np.arange(len(c))

    lignes = []
    for m in methodes(donnees):
        g = (val["methode"] == m).to_numpy()
        for nom, pos, neg in [
            ("XLM-R SQuAD 2.0 (retenu)", val.loc[g, "qa_score"], val.loc[g, "qa_score_neg"]),
            ("CamemBERT FQuAD/PIAF (écarté)", abl.loc[g, "cam_score"], abl.loc[g, "cam_score_neg"]),
        ]:
            pos, neg = np.asarray(pos, float), np.asarray(neg, float)
            if np.isnan(pos).any() or np.isnan(neg).any():
                lignes.append({"Méthode": m, "Modèle QA": nom,
                               "AUC (vrai passage / autre cours)": np.nan,
                               "% vraies questions acceptées à 5 % de fausses acceptations": np.nan})
                continue
            seuil = np.quantile(neg, CENTILE_V1)
            lignes.append({
                "Méthode": m, "Modèle QA": nom,
                "AUC (vrai passage / autre cours)": round(
                    roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg]), 3),
                "% vraies questions acceptées à 5 % de fausses acceptations": round(100 * (pos >= seuil).mean(), 1),
            })
    df_qa = pd.DataFrame(lignes)

    def discernement(imp_v: np.ndarray, dispo: np.ndarray) -> float:
        ok = dispo & donnees["validation"]["methode"].eq("base").to_numpy()
        return round(100 * (imp_v[ok].argmax(axis=1) == c[ok]).mean(), 1) if ok.any() else np.nan

    variantes = {"B, 2 phrases (retenu)": (imp, np.ones(len(imp), bool), None),
                 "A, 2 phrases": (None, None, "nli_A_k2"),
                 "B, 1 phrase": (None, None, "nli_B_k1"),
                 "B, 4 phrases": (None, None, "nli_B_k4")}
    if "nli_mdeberta" in abl:
        variantes["B, 2 phrases, mDeBERTa"] = (None, None, "nli_mdeberta")

    lignes_nli = []
    rng = np.random.default_rng(42)
    fausse_cle = (c + rng.integers(1, 4, len(c))) % 4
    for nom, (imp_v, dispo, colonne) in variantes.items():
        if colonne is not None:
            brut = [v if isinstance(v, list) else [np.nan] * 4 for v in abl[colonne]]
            imp_v = np.array(brut, dtype=float)
            dispo = ~np.isnan(imp_v).any(axis=1)
        v23 = np.zeros(len(val), bool)
        if dispo.any():
            pref = imp_v.argmax(axis=1) == c
            v23 = pref & (imp_v[r, c] >= IMP_MIN_V2) & (np.where(np.eye(4, dtype=bool)[c], -1, imp_v).max(1) < IMP_MAX_V3)
        ligne = {"Variante NLI": nom,
                 "Discernement base (%)": discernement(np.nan_to_num(imp_v, nan=-1), dispo)}
        for m in methodes(donnees):
            masque = dispo & (val["methode"] == m).to_numpy()
            ligne[f"% V2+V3 ({m})"] = round(100 * v23[masque].mean(), 1) if masque.any() else np.nan
        pref_dispo = (np.nan_to_num(imp_v, nan=-1).argmax(axis=1) == c) & dispo
        detecte = np.where(np.eye(4, dtype=bool)[fausse_cle], -1,
                           np.nan_to_num(imp_v, nan=-1)).max(axis=1)[pref_dispo] >= IMP_MAX_V3
        ligne["Clé fausse détectée par V3 (tirage 10.2, %)"] = round(100 * detecte.mean(), 1) if pref_dispo.any() else np.nan
        lignes_nli.append(ligne)

    return "Tableau 8 — Ablations de modèles", (df_qa, pd.DataFrame(lignes_nli).set_index("Variante NLI"))


def tableau_sensibilite(donnees: dict) -> tuple[str, pd.DataFrame]:
    sens = donnees["sensibilite"]
    defauts = {"V1 : centile du contrôle négatif": CENTILE_V1,
               "V2 : implication min. de la bonne réponse": IMP_MIN_V2,
               "V3 : implication max. d'un distracteur": IMP_MAX_V3}
    lignes = []
    for seuil, g in sens.groupby("seuil"):
        defaut = defauts.get(seuil, np.nan)
        proche = g.iloc[(g["valeur"] - defaut).abs().argsort()[:1]]
        lignes.append({
            "Seuil": seuil,
            "Valeurs testées": f"{fr(g['valeur'].min(), 3).rstrip('0').rstrip(',')} – "
                               f"{fr(g['valeur'].max(), 3).rstrip('0').rstrip(',')}",
            "Valeur retenue": defaut,
            "% acceptés à la valeur retenue": round(float(proche["% acceptés"].iloc[0]), 1),
            "% acceptés : min – max sur la plage": f"{fr(g['% acceptés'].min())} – {fr(g['% acceptés'].max())}",
        })
    return "Tableau 9 — Sensibilité aux seuils", pd.DataFrame(lignes).set_index("Seuil")


def tableau_longueur(donnees: dict) -> tuple[str, pd.DataFrame]:
    lignes = []
    for nom, df in (("base", donnees["base"]), ("llm", donnees["llm"])):
        if df.empty:
            continue
        k = sum(int(np.argmax([len(o) for o in q["options"]])) == q["index_correct"] for q in df.to_dict("records"))
        lignes.append({"Méthode": nom, "QCM": len(df), "Bonne réponse = plus longue": k,
                       "%": round(100 * k / len(df), 1),
                       "p (H0 : 25 %)": round(binomtest(k, len(df), 0.25).pvalue, 3)})
    return "Tableau 10 — Biais de longueur (test binomial contre 25 %)", \
        pd.DataFrame(lignes).set_index("Méthode")


def tableau_annotations(donnees: dict) -> tuple[str, list[pd.DataFrame]]:
    """Kappa et apport du filtre, si les deux grilles existent."""
    cle = DATA_DIR / "annotations" / "cle_echantillon.csv"
    grilles = {e: DATA_DIR / "annotations" / f"grille_evaluateur_{e}.csv" for e in ("A", "B")}
    if not cle.exists() or not all(p.exists() for p in grilles.values()):
        return ("Tableau 11 — Évaluation humaine : en attente des annotations "
                "(voir data/annotations/GUIDE_ANNOTATION.md)"), []

    annotations = {}
    for e, chemin in grilles.items():
        g = pd.read_csv(chemin, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
        if (g[["clarte", "difficulte", "unicite"]].apply(lambda s: s.str.strip()) == "").all(axis=None):
            return f"Tableau 11 — Évaluation humaine : la grille {e} est encore vierge", []
        for col in ("clarte", "difficulte", "unicite"):
            g[col] = pd.to_numeric(g[col], errors="coerce")
        annotations[e] = g.set_index("eval_id")

    A, B = annotations["A"], annotations["B"]
    m = A.join(B, lsuffix="_A", rsuffix="_B")
    kappas = pd.DataFrame([
        {"Critère": critere,
         "Kappa": round(cohen_kappa_score(m[f"{critere}_A"], m[f"{critere}_B"], weights=poids), 3),
         "Pondération": poids or "aucune",
         "Accord brut (%)": round(100 * (m[f"{critere}_A"] == m[f"{critere}_B"]).mean(), 1)}
        for critere, poids in [("clarte", "quadratic"), ("difficulte", "quadratic"), ("unicite", None)]
    ]).set_index("Critère")

    accept_A = (A["clarte"] >= 2) & (A["unicite"] == 1)
    accept_B = (B["clarte"] >= 2) & (B["unicite"] == 1)
    d = pd.read_csv(cle)
    d["strict"] = d["eval_id"].map(accept_A & accept_B).astype(float)
    d["indulgent"] = d["eval_id"].map(accept_A | accept_B).astype(float)

    val = donnees["validation"].copy()
    val["accepte"] = val[["forme_ok", "V1", "V2", "V3"]].all(axis=1)
    lignes = []
    for regle in ("strict", "indulgent"):
        for methode in methodes(donnees):
            g = d[d["methode"] == methode]
            if g.empty:
                continue
            g_val = val[val["methode"] == methode]
            w_acc = g_val["accepte"].mean()
            p_acc = g.loc[g["accepte"], regle].mean()
            p_rej = g.loc[~g["accepte"], regle].mean()
            avant = w_acc * p_acc + (1 - w_acc) * p_rej
            defauts_rejetes = (1 - w_acc) * (1 - p_rej)
            defauts = defauts_rejetes + w_acc * (1 - p_acc)
            lignes.append({
                "Règle": "stricte (A et B)" if regle == "strict" else "indulgente (A ou B)",
                "Méthode": methode,
                "Part réelle d'acceptés": round(w_acc, 2),
                "Qualité avant filtre (%)": round(100 * avant, 1),
                "Qualité après filtre (%)": round(100 * p_acc, 1),
                "Apport (points)": round(100 * (p_acc - avant), 1),
                "Précision des rejets (%)": round(100 * (1 - p_rej), 1),
                "Rappel des défauts (%)": round(100 * defauts_rejetes / defauts, 1) if defauts else np.nan,
            })
    qualite = pd.DataFrame(lignes)

    # Le filtre comme classifieur du verdict humain strict.
    d = d.merge(val[["qcm_id", "accepte"]], on="qcm_id")
    vrais_positifs = int((d["accepte"] & (d["strict"] == 1)).sum())
    faux_positifs = int((d["accepte"] & (d["strict"] == 0)).sum())
    faux_negatifs = int((~d["accepte"] & (d["strict"] == 1)).sum())
    precision = vrais_positifs / (vrais_positifs + faux_positifs) if vrais_positifs + faux_positifs else np.nan
    rappel = vrais_positifs / (vrais_positifs + faux_negatifs) if vrais_positifs + faux_negatifs else np.nan
    confusion = pd.DataFrame([{
        "QCM acceptés par le filtre": int(d["accepte"].sum()),
        "dont jugés acceptables": vrais_positifs,
        "QCM rejetés par le filtre": int((~d["accepte"]).sum()),
        "dont jugés inacceptables": int((~d["accepte"] & (d["strict"] == 0)).sum()),
        "Précision du filtre (%)": round(100 * precision, 1),
        "Rappel des défauts (%)": round(100 * rappel, 1) if not np.isnan(rappel) else np.nan,
    }])
    return "Tableau 11 — Évaluation humaine (sans intervalle de confiance ; le notebook fait foi)", \
        [kappas.reset_index(), qualite, confusion]


# --------------------------------------------------------------------------- #
def construire(donnees: dict) -> str:
    sections = ["# Tableaux de résultats (générés automatiquement)",
                "",
                "Fichier produit par `scripts/tableaux_resultats.py` : **ne pas modifier à la main**.",
                "Les chiffres viennent de `outputs/qcm/` et de `data/processed/`. Les tableaux 2 à 8",
                "et 11 contiennent une ligne par méthode ; la ligne `llm` n'apparaît qu'une fois",
                "l'étape 5 exécutée sur GPU.", ""]
    for titre, table in [
        tableau_donnees(donnees), tableau_generation(donnees), tableau_forme(donnees),
        tableau_validateur(donnees), tableau_cascade(donnees), tableau_typologie(donnees),
        tableau_ablation_controles(donnees),
    ]:
        sections += [f"## {titre}", "", markdown(table), ""]

    titre, contenu = tableau_ablation_modeles(donnees)
    sections += [f"## {titre}", ""]
    if isinstance(contenu, tuple):
        qa, nli = contenu
        sections += [markdown(qa), "", markdown(nli), ""]
    else:
        sections += [markdown(contenu), ""]

    titre, table = tableau_sensibilite(donnees)
    sections += [f"## {titre}", "", markdown(table), ""]
    titre, table = tableau_longueur(donnees)
    sections += [f"## {titre}", "", markdown(table), ""]

    titre, tables = tableau_annotations(donnees)
    sections += [f"## {titre}", ""]
    for table in tables:
        sections += [markdown(table), ""]

    pending = []
    if donnees["llm"].empty:
        pending.append("générer `qcm_llm.jsonl` (étape 5, GPU) puis réexécuter les étapes 6 à 8 ;")
    if not donnees["ablation"].empty and "nli_mdeberta" not in donnees["ablation"]:
        pending.append("relancer l'ablation mDeBERTa sur GPU (étape 10.4) ;")
    if donnees["ablation"].empty or "qa_score_neg_meme_cours" not in donnees["ablation"]:
        pending.append("calculer le contrôle négatif « même cours » (étape 11.5) ;")
    pending.append("remplir les deux grilles d'annotation puis réexécuter l'étape 9.")

    sections += ["## Ce qu'il reste à calculer", ""]
    sections += [f"- {p}" for p in pending]
    sections += ["", "Après chaque mise à jour : `python3 scripts/verifier_sorties.py`."]
    return "\n".join(sections) + "\n"


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sortie", type=Path, default=ROOT / "docs" / "article" / "resultats_auto.md")
    args = p.parse_args(argv)

    donnees = charger()
    texte = construire(donnees)
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(texte, encoding="utf-8")

    n = len(donnees["validation"])
    print(f"Tableaux régénérés depuis {n} QCM ({', '.join(methodes(donnees))})")
    print(f"  → {args.sortie.relative_to(ROOT) if args.sortie.is_relative_to(ROOT) else args.sortie}")
    if donnees["llm"].empty:
        print("  (QCM du LLM absents : la ligne llm et l'évaluation humaine restent à compléter)")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
