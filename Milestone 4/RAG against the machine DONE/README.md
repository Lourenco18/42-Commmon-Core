*This project has been created as part of the 42 curriculum by dasantos.*

# RAG against the machine

## Description

A **Retrieval-Augmented Generation (RAG)** system that answers questions about the vLLM codebase. The system ingests the vLLM repository, builds a searchable knowledge base using BM25, retrieves the most relevant code snippets and documentation for any query, and generates natural language answers grounded in that context using **Qwen/Qwen3-0.6B**.

**Goal**: given a question about vLLM, find the exact source locations that answer it and produce an accurate, source-grounded response.

---

## System Architecture

```
vLLM Repository
      │
      ▼
┌─────────┐   chunks   ┌────────────┐   BM25 scores   ┌───────────┐
│ Chunker │ ─────────► │ BM25 Index │ ──────────────► │ Retriever │
└─────────┘            └────────────┘                 └─────┬─────┘
(chunker.py)           (indexer.py)                         │
                                                       Top-k chunks
Query ─────────────────────────────────────────────────────┘
                                                            │
                                                            ▼
                                                   ┌─────────────┐
                                                   │ Qwen3-0.6B  │
                                                   └──────┬──────┘
                                                  (generator.py)
                                                          │
                                                          ▼
                                                   JSON Answer
```

| File | Role |
|------|------|
| `src/student/chunker.py` | Python AST + text/Markdown chunking |
| `src/student/indexer.py` | BM25 index build, persistence, search |
| `src/student/generator.py` | Qwen3-0.6B answer generation |
| `src/student/models.py` | Pydantic data models |
| `src/student/__main__.py` | CLI entry point (Python Fire) |

---

## Chunking Strategy

Two strategies are applied based on file type:

**Python files (`.py`) — AST-based chunking**: parsed with Python's `ast` module. Top-level `def` and `class` definitions are used as chunk boundaries, keeping each function or class intact. Falls back to line-based splitting on syntax errors or when a block exceeds `max_chunk_size`.

**Text and Markdown files — Paragraph-based chunking**: split on double newlines (`\n\n`). Adjacent paragraphs are merged greedily up to `max_chunk_size` characters. Oversized paragraphs are further split along line boundaries.

Maximum chunk size is **2000 characters** by default, configurable via `--max_chunk_size`.

---

## Retrieval Method

**BM25** (`BM25Okapi` from `rank_bm25`) — a probabilistic ranking function with term saturation and document-length normalisation, which outperforms plain TF-IDF on repetitive codebases.

**Tokenisation**: text is lowercased and split on non-alphanumeric characters. camelCase and snake_case identifiers are additionally split into sub-words — both the full token and its parts are indexed. This improves recall on code queries where the same concept appears as `OpenAICompatibleServer`, `openai_compatible_server`, or `openai compatible server`.

**Index persistence**: the BM25 model is serialised with `pickle`, chunk metadata in JSON, and chunk texts in a separate pickle. This allows sub-second cold-start reloads without re-indexing.

---

## Instructions

### Requirements

- Python 3.10 or later
- [`uv`](https://github.com/astral-sh/uv) package manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
make install
```

### For evaluators / correctors

This project's Python package is named **`student`** (not `src`). Both of
these work identically — no flag needed:

```bash
uv run python -m student search "How to configure OpenAI server?" --k 10
uv run python -m src     search "How to configure OpenAI server?" --k 10
```

`python -m src` is provided as a thin compatibility shim
(`src/__main__.py`) that forwards to `student.__main__`, so it matches
the commands used in the official evaluation sheet exactly, with
nothing to configure.

If you are running the official exam scripts (`exams/scripts/*.sh`,
provided separately by the school) against this repo, the module name
is `student`:

```bash
./exams/scripts/exam_retrieval.sh \
    --student-path ./student \
    --moulinette-path ./moulinette-ubuntu \
    --module-name student

./exams/scripts/exam_edge_cases.sh \
    --student-path ./student \
    --module-name student
```

(`--module-name` defaults to `src`; since `python -m src` also works
here via the shim above, the scripts will actually succeed either way
— the explicit flag is just belt-and-braces.)

The exam scripts expect this checkout at `<eval-root>/student/`, with
the private datasets unzipped at `<eval-root>/data/datasets/private/`
(sibling to `student/`, per the evaluation sheet's guidelines — not
inside this repo). Indexing still reads from `data/raw/vllm-0.10.1`
**inside** this repo, so run `make prepare` here first.

If you have the `exams/` folder and moulinette binary checked out as
siblings of this repo (for your own rehearsal, not part of grading),
you can also just run:

```bash
make exam-retrieval    # wraps exam_retrieval.sh
make exam-edge-cases   # wraps exam_edge_cases.sh
make exam-answer       # wraps exam_answer.sh (interactive)
```

### Step-by-step testing guide

**Step 1 — Verify the project structure**

```bash
ls -1
```

Expected at the project root:

```
Makefile
README.md
pyproject.toml
uv.lock
src/
```

**Step 2 — Install dependencies**

```bash
make install

uv pip list | grep student
# student   0.1.0   /path/to/project

uv run python -m student --help
# COMMANDS: index | search | search_dataset | answer | answer_dataset | evaluate
```

**Step 3 — Prepare the data**

```bash
make prepare
```

Verify:

```bash
ls data/raw/
# vllm-0.10.1/

ls data/datasets/AnsweredQuestions/
# dataset_code_public.json   dataset_docs_public.json

ls data/datasets/UnansweredQuestions/
# dataset_code_public.json   dataset_docs_public.json
```

**Step 4 — Build the index**

```bash
make index
```

Verify:

```bash
ls data/processed/
# bm25_index/   chunks/
```

**Step 5 — Test a single search query**

```bash
uv run python -m student search "How does vLLM handle tokenization?" --k 5
```

Expected: 5 results with `file_path`, character range, and score.

**Step 6 — Run the full evaluation (public datasets, own `evaluate` command)**

```bash
make test
```

Expected results:

```
Docs dataset — Recall@5: 0.830   (target ≥ 0.80) ✓
Code dataset — Recall@5: 0.590   (target ≥ 0.50) ✓
```

**Step 6b — Cross-check with the official moulinette (optional, local-only)**

`moulinette_pkg/` (the compiled binaries) is provided by the school for
self-testing only — it is **not** part of this repository (see
`.gitignore`). If you have it locally, place it next to this project
and run:

```bash
chmod +x ../moulinette_pkg/moulinette-ubuntu   # once

../moulinette_pkg/moulinette-ubuntu evaluate_student_search_results \
    data/output/search_results/dataset_docs_public.json \
    data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10 --max_context_length 2000 --threshold 0.80

../moulinette_pkg/moulinette-ubuntu evaluate_student_search_results \
    data/output/search_results/dataset_code_public.json \
    data/datasets/AnsweredQuestions/dataset_code_public.json \
    --k 10 --max_context_length 2000 --threshold 0.50
```

On macOS the binary is Linux-only (ELF); run it via Docker instead:

```bash
docker run --rm --platform linux/amd64 -v "$(pwd)/..":/work -w /work/student ubuntu:24.04 \
  ../moulinette_pkg/moulinette-ubuntu evaluate_student_search_results \
  data/output/search_results/dataset_docs_public.json \
  data/datasets/AnsweredQuestions/dataset_docs_public.json \
  --k 10 --max_context_length 2000 --threshold 0.80
```

**Step 7 — Generate LLM answers**

```bash
make answer_dataset
```

Verify:

```bash
ls data/output/search_results_and_answer/
# dataset_code_public.json   dataset_docs_public.json
```

Inspect one answer:

```bash
i=42
jq -s --argjson i "$i" '
. as [$docs, $results]
| {
    index: $i,
    question: $docs.rag_questions[$i].question,
    expected: $docs.rag_questions[$i].answer,
    predicted: $results.search_results[$i].answer
  }
' \
data/datasets/AnsweredQuestions/dataset_docs_public.json \
data/output/search_results_and_answer/dataset_docs_public.json
```

**Step 8 — lint**

```bash
make lint
# flake8 . → 0 errors
# mypy .   → Success: no issues found

make lint-strict
# flake8 . → 0 errors
# mypy . --strict → Success: no issues found
```

**Step 9 — Clean for submission**

```bash
make deep-clean

ls -1
# Makefile  README.md  pyproject.toml  uv.lock  src/  .gitignore
```

### Quick reference

```bash
make install          # install dependencies
make prepare          # set up data/raw/ and data/datasets/
make index            # build BM25 index
make test             # search + evaluate both datasets (public)
make answer_dataset   # generate LLM answers for both datasets (public)
make test_all         # prepare + index + test + answer_dataset, in one shot
make lint             # flake8 + mypy (subject-required flags)
make lint-strict      # flake8 + mypy --strict
make deep-clean       # clean for submission

# Local rehearsal only — needs exams/ + moulinette checked out as
# siblings of this repo (see "For evaluators / correctors" above):
make exam-retrieval   # wraps exam_retrieval.sh
make exam-edge-cases  # wraps exam_edge_cases.sh
make exam-answer      # wraps exam_answer.sh (interactive)
```

---

## Example Usage

```bash
# Index
uv run python -m student index --max_chunk_size 2000

# Search a single query
uv run python -m student search "How to configure OpenAI server?" --k 10

# Answer a single query
uv run python -m student answer "How to configure OpenAI server?" --k 10

# Search a dataset
uv run python -m student search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 \
    --save_directory data/output/search_results

# Evaluate
uv run python -m student evaluate \
    --student_results_path data/output/search_results/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10

# Answer a dataset
uv run python -m student answer_dataset \
    --student_search_results_path data/output/search_results/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer
```

---

## Performance Analysis

Official grading uses the **private** datasets via `exam_retrieval.sh`
(200 questions total: 100 docs + 100 code):

| Metric | Target | Result (private) | Result (public) |
|--------|--------|-------------------|------------------|
| Indexing time | ≤ 300 s | **9 s** | ~9 s |
| Warm retrieval — 200 questions | ≤ 90 s | **19 s** | ~19 s |
| Recall@5 — Docs | ≥ 0.80 | **0.840** | 0.830 |
| Recall@5 — Code | ≥ 0.50 | **0.590** | 0.590 |
| Cold start latency | ≤ 60 s | < 1 s (BM25 only) | — |

All four values above were confirmed by running the official
`exam_retrieval.sh` script against the compiled `moulinette-ubuntu`
binary and the private ground-truth datasets — not just this
project's own `evaluate` command.

---

## Design Decisions

1. **BM25 over TF-IDF**: better term saturation on a repetitive codebase where keywords like `tokenizer` appear hundreds of times.
2. **AST-based Python chunking**: splitting at `def`/`class` boundaries keeps functions and classes intact as retrieval units.
3. **Paragraph merging for Markdown**: vLLM docs are naturally sectioned by blank lines — merging keeps related content together.
4. **Custom tokeniser**: indexing both full identifiers and their snake/camel sub-parts improves recall on method-name queries.
5. **CPU-only inference**: `torch.float32` on CPU — Qwen3-0.6B is small enough to run without a GPU.
6. **Pydantic v2**: all pipeline I/O is validated by the exact models from the subject; `model_dump_json()` produces the required JSON directly.

---

## Challenges Faced

- **Code vs. text duality**: generic splitters break code logic. The dual strategy (AST for Python, paragraphs for text) was essential.
- **Identifier tokenisation**: standard tokenisers drop underscores, breaking Python identifiers. The custom tokeniser indexes sub-parts alongside the full token.
- **Index serialisation**: BM25Okapi is not directly serialisable — split into model (pickle) + metadata (JSON) + texts (pickle) for fast reloads.
- **LLM context limits**: Qwen3-0.6B has a 2048-token window — each snippet is truncated to `max_context_length` characters to avoid cutting off the answer.

---

## Resources

- [Qwen3-0.6B — HuggingFace](https://huggingface.co/Qwen/Qwen3-0.6B)
- [RAG paper — Lewis et al. 2020](https://arxiv.org/abs/2005.11401)
- [vLLM project](https://github.com/vllm-project/vllm)
- [Python `ast` module](https://docs.python.org/3/library/ast.html)

### AI Usage

AI was used to:
- Draft the initial Pydantic model structure and type annotations.
- Suggest the AST-based Python chunking approach and its fallback logic.
- Format docstrings to PEP 257 / Google style consistently.
- Review the IoU overlap formula against the moulinette specification.

All generated content was reviewed, tested, and understood before inclusion.