# Paths — override on the command line if needed
DATA_RAW       = data/raw
VLLM_DIR       = $(DATA_RAW)/vllm-0.10.1
VLLM_ZIP       = vllm-0.10.1.zip
DATASETS_SRC   = datasets_public/public
DS_ANSWERED    = data/datasets/AnsweredQuestions
DS_UNANSWERED  = data/datasets/UnansweredQuestions
INDEX_DIR      = data/processed/bm25_index
OUTPUT_SEARCH  = data/output/search_results
OUTPUT_ANSWERS = data/output/search_results_and_answer
MAX_CHUNK       = 2000
K              = 10

.PHONY: install run debug clean deep-clean lint lint-strict \
        prepare index test evaluate answer_dataset test_all

# ── Dependencies ───────────────────────────────────────────────────────────────
install:
	uv venv && uv sync

# ── Run / Debug ────────────────────────────────────────────────────────────────
run:
	uv run python -m student

debug:
	uv run python -m pdb -m student

# ── Prepare: unzip vLLM + copy datasets ───────────────────────────────────────
# Usage:
#   make prepare                          (uses defaults above)
#   make prepare VLLM_ZIP=path/to/file.zip DATASETS_SRC=path/to/datasets_public/public
prepare:
	@echo "==> Creating data directories..."
	@mkdir -p $(DATA_RAW) $(DS_ANSWERED) $(DS_UNANSWERED) \
	          $(OUTPUT_SEARCH) $(OUTPUT_ANSWERS)
	@echo "==> Extracting vLLM repository..."
	@if [ -d "$(VLLM_DIR)" ]; then \
		echo "    $(VLLM_DIR) already exists, skipping unzip."; \
	elif [ -f "$(VLLM_ZIP)" ]; then \
		unzip -q "$(VLLM_ZIP)" -d "$(DATA_RAW)"; \
		echo "    Extracted to $(VLLM_DIR)"; \
	else \
		echo "    ERROR: $(VLLM_ZIP) not found."; \
		echo "    Copy vllm-0.10.1.zip to $(DATA_RAW)/ or set VLLM_ZIP=<path>"; \
		exit 1; \
	fi
	@echo "==> Copying datasets..."
	@if [ -d "$(DATASETS_SRC)/AnsweredQuestions" ]; then \
		cp $(DATASETS_SRC)/AnsweredQuestions/*.json $(DS_ANSWERED)/; \
		cp $(DATASETS_SRC)/UnansweredQuestions/*.json $(DS_UNANSWERED)/; \
		echo "    Datasets copied."; \
	else \
		echo "    WARNING: $(DATASETS_SRC) not found."; \
		echo "    Set DATASETS_SRC=<path to datasets_public/public> or copy JSONs manually."; \
	fi
	@echo "==> Done. Run 'make index' next."

# ── Index ──────────────────────────────────────────────────────────────────────
index:
	@echo "==> Indexing vLLM repository (max_chunk_size=$(MAX_CHUNK))..."
	uv run python -m student index \
		--max_chunk_size $(MAX_CHUNK)
	@echo "==> Index complete."

# ── Test: search + evaluate both datasets ─────────────────────────────────────
test:
	@echo "==> Searching docs dataset..."
	uv run python -m student search_dataset \
		--dataset_path $(DS_UNANSWERED)/dataset_docs_public.json \
		--k $(K) \
		--save_directory $(OUTPUT_SEARCH)
	@echo "==> Evaluating docs dataset (target Recall@5 >= 0.80)..."
	uv run python -m student evaluate \
		--student_results_path $(OUTPUT_SEARCH)/dataset_docs_public.json \
		--dataset_path $(DS_ANSWERED)/dataset_docs_public.json \
		--k $(K)
	@echo ""
	@echo "==> Searching code dataset..."
	uv run python -m student search_dataset \
		--dataset_path $(DS_UNANSWERED)/dataset_code_public.json \
		--k $(K) \
		--save_directory $(OUTPUT_SEARCH)
	@echo "==> Evaluating code dataset (target Recall@5 >= 0.50)..."
	uv run python -m student evaluate \
		--student_results_path $(OUTPUT_SEARCH)/dataset_code_public.json \
		--dataset_path $(DS_ANSWERED)/dataset_code_public.json \
		--k $(K)

# ── Generate LLM answers for both datasets ────────────────────────────────────
answer_dataset:
	@echo "==> Generating answers for docs dataset..."
	uv run python -m student answer_dataset \
		--student_search_results_path $(OUTPUT_SEARCH)/dataset_docs_public.json \
		--save_directory $(OUTPUT_ANSWERS)
	@echo "==> Generating answers for code dataset..."
	uv run python -m student answer_dataset \
		--student_search_results_path $(OUTPUT_SEARCH)/dataset_code_public.json \
		--save_directory $(OUTPUT_ANSWERS)

# ── Full pipeline: prepare → index → test → answer ────────────────────────────
test_all: prepare index test answer_dataset
	@echo ""
	@echo "==> Full pipeline complete."
	@echo "    Search results : $(OUTPUT_SEARCH)/"
	@echo "    Answers        : $(OUTPUT_ANSWERS)/"

# ── Lint ───────────────────────────────────────────────────────────────────────
lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	        --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# ── Deep Clean: remove everything not meant for submission ────────────────────
# Keeps: src/, pyproject.toml, uv.lock, README.md, Makefile, .gitignore
# Removes: data/, .venv/, generated outputs, caches, model weights
deep-clean: clean
	@echo "==> Removing generated data and outputs..."
	@rm -rf data/processed data/output
	@echo "==> Removing virtual environment..."
	@rm -rf .venv
	@echo "==> Removing model cache (HuggingFace weights)..."
	@rm -rf ~/.cache/huggingface/hub/models--Qwen* 2>/dev/null || true
	@echo ""
	@echo "==> Project is clean and ready for submission."
	@echo "    The following are intentionally kept:"
	@echo "      src/           — source code"
	@echo "      pyproject.toml — dependency manifest"
	@echo "      uv.lock        — locked dependencies (required by subject)"
	@echo "      README.md      — documentation"
	@echo "      Makefile       — automation"
	@echo "      .gitignore     — git configuration"
	@echo ""
	@echo "    The following are intentionally removed:"
	@echo "      data/processed/ — generated index (re-run 'make index')"
	@echo "      data/output/    — generated results (re-run 'make test')"
	@echo "      .venv/          — virtual env (re-run 'make install')"
	@echo "      HuggingFace cache — model weights (re-downloaded on first use)"