.PHONY: install run debug clean deep-clean lint lint-strict package

install:
	python3 -m pip install -r requirements.txt
	python3 -m pip install Pac-Man/mazegenerator-00001-py3-none-any.whl

run:
	python3 pac-man.py config.json

debug:
	python3 -m pdb pac-man.py config.json

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

deep-clean: clean
	rm -rf .venv venv build dist *.egg-info .pytest_cache
	rm -rf data
	rm -f uv.lock
	rm -f .mypy_cache
	rm -f pacman-*.zip
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true

lint:
	flake8 src
	mypy src --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	       --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 src
	mypy src --strict --ignore-missing-imports

package:
	python3 -m pip install pyinstaller
	python3 -m PyInstaller --noconfirm pacman.spec
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