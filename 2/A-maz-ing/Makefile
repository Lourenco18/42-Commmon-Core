##############################################################################
# A-Maze-ing — Makefile
# Targets: install | run | debug | clean | lint | lint-strict | test | build
##############################################################################

PYTHON     := $(shell \
	if [ -x .venv/bin/python ]; then echo .venv/bin/python; \
	else echo python3; fi)
CONFIG     := config.txt
MAIN       := a_maze_ing.py

.PHONY: all install run debug clean lint lint-strict test build help

all: lint test

# ── Dependencies ──────────────────────────────────────────────────────────────
install:
	@echo "[install] Installing project dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "[install] Installing MLX wheel for your OS..."
	@if [ -f /etc/fedora-release ] || grep -qi "fedora\|rhel\|centos" /etc/os-release 2>/dev/null; then \
		$(PYTHON) -m pip install mlx-2.2-py3-fedora-any.whl; \
	else \
		$(PYTHON) -m pip install mlx-2.2-py3-ubuntu-any.whl; \
	fi
	@echo "[install] Done."

# ── Run ───────────────────────────────────────────────────────────────────────
run:
	$(PYTHON) $(MAIN) $(CONFIG)

# ── Debug ─────────────────────────────────────────────────────────────────────
debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

# ── Lint (mandatory flags) ────────────────────────────────────────────────────
lint:
	@echo "[lint] Running flake8..."
	flake8 .
	@echo "[lint] Running mypy..."
	mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs
	@echo "[lint] All checks passed."

# ── Lint strict (optional) ────────────────────────────────────────────────────
lint-strict:
	@echo "[lint-strict] Running flake8..."
	flake8 .
	@echo "[lint-strict] Running mypy --strict..."
	mypy . --strict --ignore-missing-imports
	@echo "[lint-strict] All checks passed."

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	@echo "[test] Running pytest..."
	$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "[test] Validating output_validator.py (requires a generated maze)..."
	@if [ -f maze.txt ]; then \
		$(PYTHON) output_validator.py maze.txt && echo "[test] output_validator: OK"; \
	else \
		echo "[test] maze.txt not found; run 'make run' first to validate output."; \
	fi

# ── Build mazegen wheel ───────────────────────────────────────────────────────
build:
	@echo "[build] Building mazegen wheel..."
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build
	@echo "[build] Wheel and tarball are in dist/."

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	@echo "[clean] Removing caches and artefacts..."
	find . -type d -name "__pycache__"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist"         -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build"        -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "[clean] Done."

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo "  install      Install all dependencies (pip + correct MLX wheel)"
	@echo "  run          Run the maze generator with $(CONFIG)"
	@echo "  debug        Run under Python debugger (pdb)"
	@echo "  lint         flake8 + mypy (mandatory flags)"
	@echo "  lint-strict  flake8 + mypy --strict"
	@echo "  test         Run pytest + output_validator.py"
	@echo "  build        Build the mazegen pip package"
	@echo "  clean        Remove all caches and build artefacts"
