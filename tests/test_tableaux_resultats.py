"""Tests de ``scripts/tableaux_resultats.py``.

Le script ne doit produire que des chiffres vérifiables : on compare les
décisions recalculées à celles du notebook, on contrôle les formats, et on
simule un dépôt où les QCM du LLM existent, pour tester le chemin multi-méthodes
(même s'ils sont encore absents du dépôt).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import tableaux_resultats as tab  # noqa: E402


# --------------------------------------------------------------------------- #
# Outils de rendu
# --------------------------------------------------------------------------- #
def test_markdown_virgule_decimale_et_index_nomme():
    df = pd.DataFrame({"valeur": [1.5, 2.0]}, index=pd.Index(["a", "b"], name="Méthode"))
    texte = tab.markdown(df)
    assert texte.splitlines()[0] == "| Méthode | valeur |"
    assert "| a | 1,5 |" in texte
    assert "| b | 2 |" in texte


def test_markdown_ignore_le_rangeindex():
    df = pd.DataFrame({"x": [1]})
    assert "index" not in tab.markdown(df)


# --------------------------------------------------------------------------- #
# Cohérence des calculs avec les sorties versionnées
# --------------------------------------------------------------------------- #
def test_les_seuils_reproduisent_les_decisions_du_notebook():
    donnees = tab.charger()
    val = donnees["validation"]
    reference = pd.read_csv(ROOT / "outputs" / "qcm" / "validation.csv")
    reference["accepte"] = reference[["forme_ok", "V1", "V2", "V3"]].all(axis=1)
    calcule = tab.decisions(donnees)
    attendu = reference.set_index("qcm_id").loc[val["qcm_id"], "accepte"].to_numpy()
    assert np.array_equal(calcule.to_numpy(), attendu)
    assert calcule.mean() == pytest.approx(61 / 97, abs=1e-3)


def test_controle_des_seuils_refuse_une_decision_incoherente(monkeypatch):
    """Si les décisions recalculées ne collent plus à validation.csv, le script s'arrête."""
    donnees = tab.charger()
    monkeypatch.setattr(tab, "decisions",
                        lambda d, controles=("forme", "V1", "V2", "V3"), **kw:
                        pd.Series(False, index=d["validation"]["qcm_id"]))
    with pytest.raises(SystemExit, match="ne reproduisent pas"):
        tab.tableau_ablation_controles(donnees)


def test_un_autre_centile_change_bien_les_decisions():
    donnees = tab.charger()
    # Centile plus bas = seuil V1 moins exigeant = un QCM de plus accepté (cf. tableau 9).
    assert tab.decisions(donnees, centile=0.80).sum() > tab.decisions(donnees).sum()


def test_longueur_et_binomial():
    donnees = tab.charger()
    _, df = tab.tableau_longueur(donnees)
    assert df.loc["base", "QCM"] == len(donnees["base"])
    assert 0 <= df.loc["base", "p (H0 : 25 %)"] <= 1


def test_controles_negatifs_reproduisent_la_section_7_5():
    donnees = tab.charger()
    _, df = tab.tableau_controles_negatifs(donnees)
    assert df.loc[("base", "autre cours"), "AUC"] == pytest.approx(0.993)
    assert df.loc[("base", "même cours"), "AUC"] == pytest.approx(0.992)
    assert df.loc[("base", "clé de correction fausse"), "dont rejetés par V2 (%)"] == 100
    assert df.loc[("base", "clé de correction fausse"), "dont rejetés par V3 (%)"] == pytest.approx(77.8)


def test_couverture_par_cours():
    _, df = tab.tableau_couverture(tab.charger())
    assert df.loc["C6", "base"] == 3
    assert df.loc["C3", "base"] == 20


def test_donnees_et_passages():
    donnees = tab.charger()
    _, df = tab.tableau_donnees(donnees)
    assert df.loc["Total", "Pages"] == 460
    assert df.loc["Total", "Passages"] == len(donnees["passages"])
    assert "C6" in df.index


def test_tableaux_multi_methodes_quand_le_llm_arrive(tmp_path, monkeypatch):
    """Simule un dépôt avec QCM du LLM : deux méthodes doivent apparaître partout."""
    qcm_dir = tmp_path / "outputs" / "qcm"
    qcm_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "data", tmp_path / "data")
    for nom in ("qcm_base.jsonl", "validation.csv", "controles_forme.csv",
                "scores_ablation.jsonl", "typologie_rejets.csv", "sensibilite_seuils.csv"):
        shutil.copy(ROOT / "outputs" / "qcm" / nom, qcm_dir / nom)

    base = [json.loads(l) for l in (qcm_dir / "qcm_base.jsonl").read_text(encoding="utf-8").splitlines()]
    llm = [{**q, "qcm_id": q["qcm_id"].replace("BASE_", "LLM_"), "methode": "llm"}
           for q in base[:20]]
    (qcm_dir / "qcm_llm.jsonl").write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in llm),
                                           encoding="utf-8")

    # Les 20 passages ont maintenant deux QCM (base + llm) : on duplique les lignes d'analyse.
    correspondance = {q["qcm_id"]: q["qcm_id"].replace("BASE_", "LLM_") for q in base[:20]}
    for nom in ("validation.csv", "controles_forme.csv"):
        table = pd.read_csv(qcm_dir / nom)
        copies = table[table["qcm_id"].isin(correspondance)].copy()
        copies["qcm_id"] = copies["qcm_id"].map(correspondance)
        copies["methode"] = "llm"
        pd.concat([table, copies]).to_csv(qcm_dir / nom, index=False)
    typo = pd.read_csv(qcm_dir / "typologie_rejets.csv")
    copies = typo[typo["qcm_id"].isin(correspondance)].copy()
    copies["qcm_id"] = copies["qcm_id"].map(correspondance)
    copies["methode"] = "llm"
    pd.concat([typo, copies]).to_csv(qcm_dir / "typologie_rejets.csv", index=False)

    monkeypatch.setattr(tab, "ROOT", tmp_path)
    monkeypatch.setattr(tab, "QCM_DIR", qcm_dir)
    monkeypatch.setattr(tab, "DATA_DIR", tmp_path / "data")

    donnees = tab.charger()
    assert set(tab.methodes(donnees)) == {"base", "llm"}
    texte = tab.construire(donnees)
    assert "| llm |" in texte

    titre, df = tab.tableau_generation(donnees)
    assert set(df.index) == {"base", "llm"}
    titre, df = tab.tableau_cascade(donnees)
    assert "llm" in df.index


# --------------------------------------------------------------------------- #
# Évaluation humaine : le filtre comme classifieur (BF12)
# --------------------------------------------------------------------------- #
def _depot_avec_annotations(tmp_path: Path) -> tuple[Path, Path, pd.DataFrame]:
    """Copie minimale du dépôt + une clé et deux grilles synthétiques complètes."""
    qcm_dir = tmp_path / "outputs" / "qcm"
    qcm_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "data", tmp_path / "data")
    for nom in ("qcm_base.jsonl", "validation.csv", "controles_forme.csv",
                "scores_ablation.jsonl", "typologie_rejets.csv", "sensibilite_seuils.csv"):
        shutil.copy(ROOT / "outputs" / "qcm" / nom, qcm_dir / nom)

    val = pd.read_csv(qcm_dir / "validation.csv")
    val["accepte"] = val[["forme_ok", "V1", "V2", "V3"]].all(axis=1)
    cle = val[["qcm_id", "methode", "accepte"]].copy()
    cle.insert(0, "eval_id", [f"EVAL_{i + 1:02d}" for i in range(len(cle))])
    cle.to_csv(tmp_path / "data" / "annotations" / "cle_echantillon.csv", index=False)

    for evaluateur in ("A", "B"):
        grille = pd.DataFrame({
            "eval_id": cle["eval_id"], "cours": cle["methode"], "passage": "",
            "question": "question", "A": "a", "B": "b", "C": "c", "D": "d",
            "bonne_reponse_indiquee": "A", "clarte": 3, "difficulte": 2,
            "unicite": 1, "commentaire": "",
        })
        # Quelques défauts, pour que les métriques ne soient pas triviales.
        grille.loc[::5, "clarte"] = 1
        grille.loc[::3, "difficulte"] = 1
        grille.loc[::4, "difficulte"] = 3
        grille.loc[::7, "unicite"] = 0
        grille.to_csv(tmp_path / "data" / "annotations" / f"grille_evaluateur_{evaluateur}.csv",
                      sep=";", index=False, encoding="utf-8-sig")
    return tmp_path, qcm_dir, cle


def test_tableau_annotations_calcule_matrice_de_confusion(tmp_path, monkeypatch):
    """Sans ce test, le chemin des annotations n'était jamais exécuté : il levait
    ``KeyError: 'accepte'`` à cause d'une fusion avec une colonne homonyme."""
    depot, qcm_dir, cle = _depot_avec_annotations(tmp_path)
    monkeypatch.setattr(tab, "ROOT", depot)
    monkeypatch.setattr(tab, "QCM_DIR", qcm_dir)
    monkeypatch.setattr(tab, "DATA_DIR", depot / "data")

    donnees = tab.charger()
    titre, tables = tab.tableau_annotations(donnees)
    assert "Évaluation humaine" in titre
    assert len(tables) == 3
    kappas, qualite, classifieur = tables
    assert set(kappas["Critère"]) == {"clarte", "difficulte", "unicite"}
    assert {"Qualité avant filtre (%)", "Apport (points)"} <= set(qualite.columns)
    assert {"F1 (%)", "Précision (%)", "Rappel (%)"} <= set(classifieur.columns)

    ligne = classifieur.loc[("stricte (A et B)", "toutes")]
    vp, fp, fn, vn = (int(ligne[c]) for c in
                      ("Vrais positifs", "Faux positifs", "Faux négatifs", "Vrais négatifs"))
    assert vp + fp + fn + vn == len(cle)

    # Vérification indépendante : on relit la grille et la clé, et on recompte.
    grille = pd.read_csv(depot / "data" / "annotations" / "grille_evaluateur_A.csv",
                         sep=";", encoding="utf-8-sig")
    humain = ((grille["clarte"] >= 2) & (grille["unicite"] == 1)).to_numpy(bool)
    filtre = cle["accepte"].to_numpy(bool)
    assert (vp, fp, fn, vn) == (int((filtre & humain).sum()), int((filtre & ~humain).sum()),
                                int((~filtre & humain).sum()), int((~filtre & ~humain).sum()))
    precision, rappel = vp / (vp + fp), vp / (vp + fn)
    assert ligne["Précision (%)"] == pytest.approx(100 * precision, abs=0.05)
    assert ligne["Rappel (%)"] == pytest.approx(100 * rappel, abs=0.05)
    assert ligne["F1 (%)"] == pytest.approx(200 * precision * rappel / (precision + rappel), abs=0.05)

    # Une ligne par méthode, en plus de la ligne « toutes ».
    assert ("stricte (A et B)", "base") in classifieur.index
