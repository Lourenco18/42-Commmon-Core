.PHONY: install run debug lint lint-strict clean

install:
	uv sync
	@echo "[INFO] Installing llm_sdk dependencies..."
	@if [ -f llm_sdk/pyproject.toml ]; then \
		uv pip install --find-links llm_sdk -e llm_sdk/ 2>/dev/null || \
		cd llm_sdk && uv pip install -r requirements.txt 2>/dev/null || \
		echo "[INFO] llm_sdk has no extra install step needed."; \
	fi

run:
	uv run python -m src

debug:
	uv run python -m pdb -m src

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pypackages__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	if [ -d .venv ]; then rm -rf .venv; fi