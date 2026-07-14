VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
MAP ?= maps/easy/01_linear_path.txt

$(PYTHON):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install flake8 mypy

install: $(PYTHON)

run: $(PYTHON)
	$(PYTHON) main.py $(MAP)
test:
	python main.py $(MAP)
debug: $(PYTHON)
	$(PYTHON) -m pdb main.py $(MAP)

lint: $(PYTHON)
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores \
	    --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: $(PYTHON)
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

.PHONY: install run debug clean lint lint-strict