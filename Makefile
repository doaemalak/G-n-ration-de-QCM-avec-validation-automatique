# Makefile du projet : raccourcis pour les outils d'après-notebook.
# Le pipeline lui-même vit dans notebooks/QCM_generation_validation.ipynb.

PYTHON ?= python3

.PHONY: aide verifier exporter tableaux article test tout propre

aide:
	@echo "make verifier   — contrôle la cohérence des sorties versionnées"
	@echo "make exporter   — Moodle GIFT + HTML + CSV des QCM acceptés"
	@echo "make tableaux   — régénère docs/article/resultats_auto.md"
	@echo "make article    — rend docs/article/article.pdf (≤ 7 pages)"
	@echo "make test       — lance pytest"
	@echo "make tout       — verifier + exporter + tableaux + test"
	@echo "make propre     — supprime les exports et les caches de test"

verifier:
	$(PYTHON) scripts/verifier_sorties.py

exporter:
	$(PYTHON) scripts/exporter_qcm.py

tableaux:
	$(PYTHON) scripts/tableaux_resultats.py

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
