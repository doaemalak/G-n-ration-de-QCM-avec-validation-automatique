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
