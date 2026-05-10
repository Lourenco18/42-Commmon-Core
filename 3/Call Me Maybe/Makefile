.PHONY: install run debug clean lint lint-strict

UV_BIN := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)

ensure-uv:
	@if ! command -v uv > /dev/null 2>&1 && [ ! -f $(HOME)/.local/bin/uv ]; then \
		echo "[INFO] uv not found. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi

install: ensure-uv
	$(UV_BIN) sync

run: ensure-uv
	PYTHONPATH=llm_sdk $(UV_BIN) run python -m src

debug: ensure-uv
	PYTHONPATH=llm_sdk $(UV_BIN) run python -m pdb -m src

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

lint: ensure-uv
	PYTHONPATH=llm_sdk $(UV_BIN) run flake8 .
	PYTHONPATH=llm_sdk $(UV_BIN) run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict: ensure-uv
	PYTHONPATH=llm_sdk $(UV_BIN) run flake8 .
	PYTHONPATH=llm_sdk $(UV_BIN) run mypy . --strict