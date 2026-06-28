.PHONY: install run debug clean deep-clean lint lint-strict package

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

deep-clean: clean
	rm -rf .venv venv build dist *.egg-info .pytest_cache
	rm -rf data
	rm -f .python-version uv.lock
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	       --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

package:
	pip install pyinstaller
	pyinstaller --noconfirm pacman.spec