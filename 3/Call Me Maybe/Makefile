.PHONY: install run debug lint lint-strict clean

install:
	uv sync

run:
	uv run python -m src

debug:
	uv run python -m pdb -m src

flake:
	python -m flake8 src
	python -m mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

flake-strict:
	python -m flake8 src
	python -m mypy src --strict

clean:
	rm -rf .venv 2>/dev/null || true
	rm -f uv.lock 2>/dev/null || true
	rm -rf data/output 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
