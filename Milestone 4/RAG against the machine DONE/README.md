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

### Installation

```bash
mkdir -p /sgoinfre/dasantos/.cache/uv
export UV_CACHE_DIR=/sgoinfre/dasantos/.cache/uv
make install
```

### Local rehearsal with the real exam scripts

```bash
make install
make prepare
make index
make exam-retrieval 
make exam-edge-cases
make exam-answer
```

`make prepare` extracts `datasets_private.zip`, `exams.zip`, and
`moulinette_pkg.zip` in place (whatever their internal folder layout
turns out to be), and stages the private datasets exactly where
`exam_retrieval.sh` looks for them — that path is computed by the
script itself as two directories above wherever `exam_retrieval.sh`
ends up, so this is done by locating the file, not by assuming a fixed
structure. The `exam-*` targets locate `exam_retrieval.sh` and the
moulinette binary the same way, so this works regardless of whether
the zips were already extracted, extracted flat at the root, or
checked out as siblings of this repo instead. Re-running `make
prepare` is safe — already-extracted material is left alone.

None of `exams.zip`/`exams_pkg/`/`exams/`, `moulinette_pkg.zip`/
`moulinette_pkg/`, or `datasets_private.zip`/`private/` are part of
this repository (see `.gitignore`) — they're school-provided grading
material, and `private/` in particular contains the ground-truth
answers, which should never end up committed.

### Step-by-step testing guide

```bash
make install
make lint          # install dependencies
make prepare          # set up data/raw/ and data/datasets/
make index            # build BM25 index
# Search a single query
uv run python -m student search "How to configure OpenAI server?" --k 10

# Answer a single query
uv run python -m student answer "How to configure OpenAI server?" --k 10
make exam-edge-cases  
make exam-retrieval 
make exam-answer   
   
make deep-clean  
  
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