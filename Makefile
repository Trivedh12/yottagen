.PHONY: setup generate validate audit evaluate test repro all clean help

PYTHON ?= python

help:
	@echo "YottaGen Build and Test Automation Makefile"
	@echo "Targets:"
	@echo "  setup      - Install dependencies (pytest)"
	@echo "  generate   - Generate starter and full synthetic datasets"
	@echo "  validate   - Validate data integrity and schema invariants"
	@echo "  audit      - Execute independent audit engine on inputs"
	@echo "  evaluate   - Evaluate audit findings against ground truth"
	@echo "  test       - Run complete offline pytest test suite"
	@echo "  repro      - Verify byte-identical reproducibility across seeds"
	@echo "  all        - Execute full end-to-end pipeline"

setup:
	$(PYTHON) -m pip install -r requirements.txt

generate:
	$(PYTHON) -m yottagen generate --seed 20261022 --scale starter --out data/starter
	$(PYTHON) -m yottagen generate --seed 20261022 --scale full --out data/full

validate:
	$(PYTHON) -m yottagen validate --data data/full --docs-dir docs

audit:
	$(PYTHON) -m yottagen audit --data data/full --out data/full/audit_findings.csv

evaluate:
	$(PYTHON) -m yottagen evaluate --data data/full --docs-dir docs

test:
	$(PYTHON) -m pytest -v

repro:
	$(PYTHON) -m yottagen repro-check --seed 20261022 --scale starter --out docs/reproducibility_report.md

all: generate validate audit evaluate test repro
	@echo "YottaGen pipeline executed successfully."
