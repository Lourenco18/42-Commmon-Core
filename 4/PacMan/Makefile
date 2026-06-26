.PHONY: install run debug clean lint lint-strict

install:
	pip install -r requirements.txt
	pip install Pac-Man/mazegenerator-00001-py3-none-any.whl

run:
	python3 pac-man.py config.json

debug:
	python3 -m pdb pac-man.py config.json

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	       --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
