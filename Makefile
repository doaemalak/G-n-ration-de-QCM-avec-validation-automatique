# Makefile du projet : raccourcis pour les outils d'après-notebook.
# Le pipeline lui-même vit dans notebooks/QCM_generation_validation.ipynb.

PYTHON ?= python3

.PHONY: aide verifier exporter tableaux article archive-colab test tout propre

aide:
	@echo "make verifier   — contrôle la cohérence des sorties versionnées"
	@echo "make exporter   — Moodle GIFT + HTML + CSV des QCM acceptés"
	@echo "make tableaux   — régénère docs/article/resultats_auto.md"
	@echo "make article    — rend docs/article/article.pdf (≤ 7 pages)"
	@echo "make archive-colab — zip du dépôt à téléverser dans Colab (sans GitHub)"
	@echo "make test       — lance pytest"
	@echo "make tout       — verifier + exporter + tableaux + test"
	@echo "make propre     — supprime les exports et les caches de test"

verifier:
	$(PYTHON) scripts/verifier_sorties.py

exporter:
	$(PYTHON) scripts/exporter_qcm.py

tableaux:
	$(PYTHON) scripts/tableaux_resultats.py

# Archive pour Colab : dépôt + PDF de data/raw s'ils sont présents, sans .git.
# À téléverser dans le panneau Fichiers de Colab, puis :
#   !unzip -q /content/taln-colab.zip -d /content/TALN
# La cellule 2 du notebook détecte le dépôt et ne clone rien.
archive-colab:
	@rm -f taln-colab.zip
	@zip -qr taln-colab.zip . -x ".git/*" ".venv/*" "*/__pycache__/*" ".pytest_cache/*" \
	  "outputs/export/*" "docs/article/*.pdf" "taln-colab.zip" "*.DS_Store" "*.pyc"
	@echo "taln-colab.zip : $$(du -h taln-colab.zip | cut -f1)"
	@ls data/raw/*.pdf >/dev/null 2>&1 || echo "⚠ data/raw/ ne contient aucun PDF : les ajouter avant l'archive, sinon les téléverser dans Colab."

# Rendu vérifié : 7 pages A4 à 10 pt avec 1,8 cm de marge.
article:
	pandoc docs/article/article.md -o docs/article/article.pdf --pdf-engine=xelatex \
	  --resource-path=docs/article \
	  -V geometry:margin=1.8cm -V fontsize=10pt -V lang=fr

test:
	$(PYTHON) -m pytest -q

tout: verifier exporter tableaux test

propre:
	rm -rf outputs/export .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
