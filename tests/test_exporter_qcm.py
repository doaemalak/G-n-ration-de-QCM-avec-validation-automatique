"""Tests de ``scripts/exporter_qcm.py`` (formats GIFT, HTML, CSV)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import exporter_qcm as exp  # noqa: E402


def qcm_exemple(qid="BASE_C1_000", methode="base"):
    return {
        "qcm_id": qid,
        "methode": methode,
        "passage_id": "C1_000",
        "cours_id": "C1",
        "question": "Complétez la phrase : « Le C a été conçu par Dennis _____. »",
        "options": ["Richie", "donnant", "livre", "annule"],
        "index_correct": 0,
        "reponse": "Richie",
    }


@pytest.fixture
def jsonl(tmp_path):
    chemin = tmp_path / "qcm.jsonl"
    chemin.write_text("\n".join(json.dumps(q) for q in [qcm_exemple(), qcm_exemple("BASE_C1_001")]),
                      encoding="utf-8")
    return chemin


def test_caracteres_reserves_gift():
    assert exp.echapper_gift("a ~ b = c") == "a \\~ b \\= c"
    assert exp.echapper_gift("ligne 1\nligne 2") == "ligne 1 ligne 2"
    assert exp.echapper_gift("http://x:y") == "http\\://x\\:y"


def test_categorie_moodle():
    assert exp.categorie_moodle("QCM TALN — langage C") == "QCM_TALN_langage_C"
    assert exp.categorie_moodle("A/B") == "A/B"


def test_gift_une_bonne_reponse_et_trois_distracteurs():
    texte = exp.en_gift([qcm_exemple()], "Test")
    assert "$CATEGORY: Test/base" in texte
    bloc = texte.split("::BASE_C1_000::")[1]
    assert bloc.count("\n    =") == 1
    assert bloc.count("\n    ~") == 3
    assert "\n    =Richie\n" in bloc


def test_html_echappe_le_contenu():
    q = qcm_exemple()
    q["question"] = "<script>alert(1)</script>"
    page = exp.en_html([q])
    assert "&lt;script&gt;" in page
    assert "<script>alert(1)</script>" not in page
    assert 'data-correct="0"' in page
    assert page.count("<label") == 4


def test_csv_colonnes_et_valeurs():
    lignes = exp.en_csv([exp.preparer([qcm_exemple()], {})[0]])
    assert len(lignes[0]) == len(exp.COLONNES)
    assert lignes[0][exp.COLONNES.index("A")] == "Richie"
    assert lignes[0][exp.COLONNES.index("bonne_reponse")] == "Richie"


def test_controler_refuse_une_structure_invalide():
    q = qcm_exemple()
    q["options"] = ["a", "b", "c"]
    with pytest.raises(ValueError, match="4 options"):
        exp.controler(q)

    q = qcm_exemple()
    q["index_correct"] = 7
    with pytest.raises(ValueError, match="index_correct"):
        exp.controler(q)

    q = qcm_exemple()
    q["options"] = ["a", "a", "b", "c"]
    with pytest.raises(ValueError, match="double"):
        exp.controler(q)


def test_exporter_ecrit_les_trois_fichiers(tmp_path, jsonl):
    ecrits = exp.exporter(exp.preparer(exp.charger_jsonl(jsonl), {}), tmp_path / "sortie", "Test")
    assert set(ecrits) == {"gift", "html", "csv"}
    assert all(p.exists() and p.stat().st_size > 0 for p in ecrits.values())
    with (tmp_path / "sortie" / "qcm.csv").open(encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.reader(f, delimiter=";"))
    assert lignes[0] == exp.COLONNES
    assert len(lignes) == 3


def test_principal_jsonl_absent(tmp_path, capsys):
    code = exp.principal(["--entree", str(tmp_path / "absent.jsonl"), "--sortie", str(tmp_path / "o")])
    assert code == 1
    assert "absent" in capsys.readouterr().err


def test_principal_bout_en_bout(tmp_path, jsonl):
    sortie = tmp_path / "export"
    code = exp.principal(["--entree", str(jsonl), "--passages", str(tmp_path / "aucun.jsonl"),
                          "--sortie", str(sortie), "--limite", "1"])
    assert code == 0
    assert (sortie / "qcm_moodle_gift.txt").read_text(encoding="utf-8").count("::BASE_") == 1
