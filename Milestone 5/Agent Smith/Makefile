.PHONY: install install-student install-moulinette test test-unit test-sandbox test-mbpp test-swebench benchmark clean help

VENV ?= .venv
PYTHON ?= python3
ENV_FILE ?= .env

help:
	@echo "Agent Smith -- available targets:"
	@echo "  make install        Create a venv and install student + moulinette (editable, with dev deps)"
	@echo "  make test           Run EVERYTHING: unit tests + all 3 exam scripts (offline, no API key needed)"
	@echo "  make test-unit      Run only the pytest unit tests (student + moulinette)"
	@echo "  make test-sandbox   Run only exam_sandbox.sh (security + MCP protocol tests)"
	@echo "  make test-mbpp      Run only exam_mbpp.sh (5 tasks, offline dummy provider by default)"
	@echo "  make test-swebench  Run only exam_swebench.sh (3 tasks, offline dummy provider by default)"
	@echo "  make clean          Remove venv, caches and generated evaluation logs"
	@echo ""
	@echo "To run against a REAL LLM provider instead of the offline dummy, put your keys in"
	@echo "  '$(ENV_FILE)' (see .env.example) and run e.g.:"
	@echo "    ./exam_mbpp.sh --student-path ./student --moulinette-path ./moulinette --env-file $(ENV_FILE)"

$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)

install: $(VENV)/bin/python
	$(VENV)/bin/pip install --quiet --upgrade pip
	$(VENV)/bin/pip install --quiet -e ./student[dev]
	$(VENV)/bin/pip install --quiet -e ./moulinette

# --- The single command graders/CI should run -----------------------------
test: install test-unit test-sandbox test-mbpp test-swebench
	@echo ""
	@echo "======================================================"
	@echo " ALL CHECKS PASSED (unit tests + sandbox + mbpp + swebench)"
	@echo "======================================================"

test-unit: install
	$(VENV)/bin/python -m pytest student/tests -v
	$(VENV)/bin/python -m pytest moulinette/tests -v

test-sandbox: install
	$(VENV)/bin/python exam_runner.py sandbox --student-path ./student --moulinette-path ./moulinette

test-mbpp: install
	$(VENV)/bin/python exam_runner.py mbpp --student-path ./student --moulinette-path ./moulinette \
		$(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

test-swebench: install
	$(VENV)/bin/python exam_runner.py swebench --student-path ./student --moulinette-path ./moulinette \
		$(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

# Convenience target to (re)generate BENCHMARK_REPORT.md's backing solution.json
# files against a REAL provider. Requires a populated .env -- see Section V.7.
benchmark: install
	@echo "See BENCHMARK_REPORT.md for the full multi-model/multi-provider benchmarking protocol."
	@echo "This target is a starting point only; edit it to loop over your chosen models."

clean:
	rm -rf $(VENV) student/.pytest_cache moulinette/.pytest_cache cache evaluations
	find . -name "__pycache__" -type d -prune -exec rm -rf {} \;
