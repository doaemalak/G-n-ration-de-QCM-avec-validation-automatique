"""Tests de ``scripts/verifier_sorties.py``.

Deux familles : les invariants du dépôt tel qu'il est versionné (test
d'intégration), et des corruptions volontaires dans une copie temporaire, pour
vérifier que le script *détecte* bien les incohérences.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import verifier_sorties as verif  # noqa: E402


# --------------------------------------------------------------------------- #
# Fonctions utilitaires
# --------------------------------------------------------------------------- #
def test_quantile_comme_numpy():
    valeurs = [3.0, 1.0, 4.0, 1.5, 9.0, 2.0]
    for q in (0.0, 0.25, 0.5, 0.95, 1.0):
        assert verif.quantile(valeurs, q) == pytest.approx(np.quantile(valeurs, q))


def test_en_bool_tolere_les_ecritures_excel():
    assert all(verif.en_bool(v) for v in ("True", "true", "1", "VRAI", "oui"))
    assert not any(verif.en_bool(v) for v in ("False", "0", "", "non", "nan"))


# --------------------------------------------------------------------------- #
# Le dépôt versionné doit passer
# --------------------------------------------------------------------------- #
def test_depot_versionne_coherent(capsys):
    code = verif.principal([])
    sortie = capsys.readouterr().out
    assert "contrôles effectués" in sortie
    assert code == 0, sortie


# --------------------------------------------------------------------------- #
# Les corruptions doivent être détectées
# --------------------------------------------------------------------------- #
@pytest.fixture
def copie(tmp_path, monkeypatch):
    """Copie minimale du dépôt, branchée sur les constantes globales du script."""
    for relatif in ("data/processed", "data/raw", "outputs/qcm", "outputs/figures",
                    "data/annotations", "notebooks", "docs/article"):
        cible = tmp_path / relatif
        if (ROOT / relatif).exists():
            shutil.copytree(ROOT / relatif, cible)
    shutil.copy(ROOT / "README.md", tmp_path / "README.md")
    shutil.copy(ROOT / "requirements.txt", tmp_path / "requirements.txt")
    (tmp_path / "docs" / "article" / "article.md").write_text("article", encoding="utf-8")

    monkeypatch.setattr(verif, "ROOT", tmp_path)
    monkeypatch.setattr(verif, "QCM_DIR", tmp_path / "outputs" / "qcm")
    monkeypatch.setattr(verif, "DATA_DIR", tmp_path / "data")
    return tmp_path


def _reecrire_jsonl(chemin: Path, lignes: list[dict]) -> None:
    chemin.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in lignes) + "\n",
                      encoding="utf-8")


def _lire_jsonl(chemin: Path) -> list[dict]:
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


def _lire_csv(chemin: Path) -> tuple[list[str], list[dict]]:
    with chemin.open(encoding="utf-8", newline="") as f:
        lecteur = csv.DictReader(f)
        return lecteur.fieldnames, list(lecteur)


def _ecrire_csv(chemin: Path, colonnes: list[str], lignes: list[dict]) -> None:
    with chemin.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        w.writerows(lignes)


def test_copie_saine_passe(copie, capsys):
    assert verif.principal([]) == 0, capsys.readouterr().out


def test_detecte_un_accepte_qui_echoue_a_v2(copie):
    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    fichiers = verif.verifier_qcm(rapport, passages)

    colonnes, lignes = _lire_csv(copie / "outputs" / "qcm" / "validation.csv")
    # Un QCM accepté dont V2 est faux, et déplacé dans qcm_acceptes.
    cible = next(l for l in lignes if l["V2"] == "True" and l["V1"] == "True"
                 and l["V3"] == "True" and l["forme_ok"] == "True")
    cible["V2"] = "False"
    _ecrire_csv(copie / "outputs" / "qcm" / "validation.csv", colonnes, lignes)

    acceptes = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_acceptes.jsonl")
    ancien_id = cible["qcm_id"]
    acceptes.append({**next(q for q in fichiers["qcm_base"] if q["qcm_id"] == ancien_id), "motifs": []})
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_acceptes.jsonl", acceptes)

    rapport = verif.Rapport()
    verif.verifier_validation(rapport, fichiers)
    assert any("forme ET V1 ET V2 ET V3" in e for e in rapport.erreurs)


def test_detecte_une_cle_de_correction_incoherente(copie):
    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    fichiers = verif.verifier_qcm(rapport, passages)

    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    base[0]["options"] = list(reversed(base[0]["options"]))   # l'index ne suit plus
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl", base)

    rapport = verif.Rapport()
    verif.verifier_qcm(rapport, passages)
    assert any("reponse différente de options[index_correct]" in e for e in rapport.erreurs)


def test_detecte_un_forme_ok_incoherent(copie):
    colonnes, lignes = _lire_csv(copie / "outputs" / "qcm" / "controles_forme.csv")
    regle = next(c for c in colonnes if c.startswith("F1"))
    lignes[0][regle] = "True"
    lignes[0]["forme_ok"] = "True"          # un défaut et pourtant « conforme »
    _ecrire_csv(copie / "outputs" / "qcm" / "controles_forme.csv", colonnes, lignes)

    rapport = verif.Rapport()
    verif.verifier_forme(rapport, {})
    assert any("forme_ok incohérent" in e for e in rapport.erreurs)


def test_detecte_un_qcm_sur_un_passage_inconnu(copie):
    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    base[0]["passage_id"] = "C9_999"
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl", base)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    verif.verifier_qcm(rapport, passages)
    assert any("passage_id C9_999 inconnu" in e for e in rapport.erreurs)


def test_detecte_un_id_en_double(copie):
    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    base.append(dict(base[0]))
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl", base)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    verif.verifier_qcm(rapport, passages)
    assert any("qcm_id en double" in e for e in rapport.erreurs)


def test_base_et_llm_partagent_les_memes_passages(copie):
    """Le recouvrement des passages est normal ; seuls les qcm_id doivent différer."""
    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    llm = [{**q, "qcm_id": q["qcm_id"].replace("BASE_", "LLM_"), "methode": "llm"} for q in base[:20]]
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_llm.jsonl", llm)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    verif.verifier_qcm(rapport, passages)
    assert not any("aucun passage commun" in e for e in rapport.erreurs)
    assert not any("qcm_id présent(s) à la fois" in e for e in rapport.erreurs)


def test_detecte_un_cache_llm_multi_modeles(copie):
    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    llm = [{**q, "qcm_id": q["qcm_id"].replace("BASE_", "LLM_"), "methode": "llm",
            "modele": choix} for q, choix in
           zip(base[:4], ["Qwen/Qwen3-4B-Instruct-2507"] * 2 + ["HuggingFaceTB/SmolLM3-3B"] * 2)]
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_llm.jsonl", llm)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    verif.verifier_qcm(rapport, passages)
    assert any("mélange" in e and "modèles" in e for e in rapport.erreurs)


def test_avertit_sur_un_cache_sans_modele(copie):
    base = _lire_jsonl(copie / "outputs" / "qcm" / "qcm_base.jsonl")
    llm = [{**q, "qcm_id": q["qcm_id"].replace("BASE_", "LLM_"), "methode": "llm"} for q in base[:2]]
    _reecrire_jsonl(copie / "outputs" / "qcm" / "qcm_llm.jsonl", llm)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    verif.verifier_qcm(rapport, passages)
    assert not any("mélange" in e for e in rapport.erreurs)
    assert any("ne renseigne pas le modèle" in a for a in rapport.avertissements)


def test_mode_strict_echoue_sur_avertissement(copie, capsys):
    (copie / "docs" / "article" / "article.md").unlink()
    code = verif.principal(["--strict"])
    assert code == 1
    assert "--strict" in capsys.readouterr().out


def test_temperature_cache_sans_controle_negatif_est_tolere(copie):
    """Les QCM de l'ablation de température n'ont pas de qa_score_neg (NaN) :
    ils ne doivent pas être jugés comme des QCM principaux incohérents."""
    scores = _lire_jsonl(copie / "outputs" / "qcm" / "scores_validateur.jsonl")
    modele = next(s for s in scores if s.get("signature"))
    scores.append({**modele, "qcm_id": "LLM_C1_000_T0.7", "qa_score_neg": float("nan")})
    _reecrire_jsonl(copie / "outputs" / "qcm" / "scores_validateur.jsonl", scores)

    rapport = verif.Rapport()
    passages, _ = verif.verifier_passages(rapport)
    fichiers = verif.verifier_qcm(rapport, passages)
    verif.verifier_caches(rapport, fichiers)
    assert not any("qa_score_neg non numérique" in e for e in rapport.erreurs)
