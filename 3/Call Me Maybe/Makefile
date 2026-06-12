.PHONY: install run debug lint lint-strict clean

install:
	mkdir -p /sgoinfre/dasantos/.cache/uv
	export UV_CACHE_DIR=/sgoinfre/dasantos/.cache/uv

	mkdir -p /sgoinfre/dasantos/tmp
	export TMPDIR=/sgoinfre/dasantos/tmp

	mkdir -p /sgoinfre/dasantos/.cache
	export XDG_CACHE_HOME=/sgoinfre/dasantos/.cache

	mkdir -p /sgoinfre/dasantos/.local/share
	export XDG_DATA_HOME=/sgoinfre/dasantos/.local/share
	uv sync
	uv add accelerate

run:
	uv run python -m src

debug:
	uv run python -m pdb -m src

flake:
	python3 -m flake8 src
	python3 -m mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

flake-strict:
	python3 -m flake8 src
	python3 -m mypy src --strict

clean:
	uv cache clean
	rm -rf .venv 2>/dev/null || true
	rm -f uv.lock 2>/dev/null || true
	rm -rf data/output 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
