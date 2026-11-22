VENV := .venv
PYTHON := $(VENV)/bin/python


$(PYTHON):
	python3 -m venv $(VENV)

install: $(PYTHON)
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install Pac-Man/mazegenerator-00001-py3-none-any.whl

run:
	$(PYTHON) pac-man.py config.json

debug:
	$(PYTHON) -m pdb pac-man.py config.json

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

deep-clean: clean
	rm -rf .venv venv build dist *.egg-info .pytest_cache
	rm -rf data
	rm -f uv.lock
	rm -f .mypy_cache
	rm -f pacman-*.zips
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true

lint: install
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	       --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict --ignore-missing-imports

package: install
	$(PYTHON) -m pip install pyinstaller
	$(PYTHON) -m PyInstaller --noconfirm pacman.spec
	cp config.json dist/
	@OS_NAME=$$(uname -s); \
	case "$$OS_NAME" in \
		Darwin) PLATFORM=macos ;; \
		Linux) PLATFORM=linux ;; \
		*) PLATFORM=$$OS_NAME ;; \
	esac; \
	rm -f pacman-$$PLATFORM.zip; \
	cd dist && zip -r ../pacman-$$PLATFORM.zip .; \
	cd ..; \
	echo "Created pacman-$$PLATFORM.zip"

.PHONY: install run debug clean deep-clean lint lint-strict package