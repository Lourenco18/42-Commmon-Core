*This project has been created as part of the 42 curriculum by dasantos.*

# RAG against the machine

## Description

A **Retrieval-Augmented Generation (RAG)** system that answers questions about the vLLM codebase. The system ingests the vLLM repository, builds a searchable knowledge base using BM25, retrieves the most relevant code snippets and documentation for any query, and generates natural language answers grounded in that context using the **Qwen/Qwen3-0.6B** LLM.

**Goal**: given a question about vLLM, find the exact source locations that answer it and produce an accurate, source-grounded response.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          RAG Pipeline                                │
│                                                                      │
│  vLLM Repository                                                     │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────┐   chunks   ┌───────────┐   BM25 scores  ┌──────────┐  │
│  │ Chunker │ ─────────► │ BM25 Index│ ─────────────► │Retriever │  │
│  └─────────┘            └───────────┘                └────┬─────┘  │
│  (chunker.py)           (indexer.py)                      │        │
│                                                       Top-k chunks  │
│  Query ───────────────────────────────────────────────────┘        │
│                                                           │         │
│                                                           ▼         │
│                                                    ┌────────────┐   │
│                                                    │ Qwen3-0.6B │   │
│                                                    │    LLM     │   │
│                                                    └─────┬──────┘   │
│                                                    (generator.py)   │
│                                                          │          │
│                                                          ▼          │
│                                                   JSON Answer       │
│                                               (StudentSearchResults │
│                                             AndAnswer Pydantic model)│
└──────────────────────────────────────────────────────────────────────┘
```

**Source files:**

| File | Role |
|------|------|
| `src/student/chunker.py` | Python AST + text/Markdown chunking strategies |
| `src/student/indexer.py` | BM25 index build, persistence, and search |
| `src/student/generator.py` | Qwen3-0.6B answer generation |
| `src/student/models.py` | All required Pydantic data models |
| `src/student/__main__.py` | CLI entry point (Python Fire) |

---

## Chunking Strategy

Different strategies are applied based on file extension:

**Python files (`.py`) — AST-based chunking**
The file is parsed with Python's `ast` module. Top-level `def` and `class` definitions become natural boundaries. Each top-level block becomes its own chunk, preserving semantic units (a function or class is never split mid-body). If the file has a syntax error, falls back to line-based splitting. If a resulting block exceeds `max_chunk_size`, it is further split along line boundaries.

**Text and Markdown files (`.md`, `.rst`, `.txt`, `.yaml`, etc.) — Paragraph-based chunking**
The file is split on double newlines (`\n\n`). Adjacent paragraphs are merged greedily up to `max_chunk_size` characters. When a paragraph alone exceeds `max_chunk_size`, it is split along line boundaries.

The maximum chunk size is **2000 characters** by default and is configurable via `--max_chunk_size` on the `index` command.

---

## Retrieval Method

**Algorithm**: BM25 (Best Match 25, `BM25Okapi` from `rank_bm25`) — a probabilistic ranking function that improves on TF-IDF with term saturation and document-length normalisation.

**Tokenisation**: Text is lowercased and split on non-alphanumeric characters. Additionally, camelCase tokens are split into their component words and snake_case identifiers are split on underscores. Both the original token and its sub-parts are indexed, which significantly improves recall on code-heavy queries where the same concept may be spelled `BaseProcessingInfo`, `base_processing_info`, or `processing info`.

**Ranking**: For a query, BM25 scores are computed over all indexed chunks. The top-k chunks by score are returned, each with their `file_path`, `first_character_index`, and `last_character_index`.

**Index persistence**: The BM25 model is serialised with `pickle`. Chunk metadata (file path, character offsets) is stored as JSON. Chunk texts are stored separately in a second pickle. This avoids re-indexing on every run.

---

## Instructions

### Requirements

- Python 3.10 or later
- [`uv`](https://github.com/astral-sh/uv) package manager (mandatory — see subject)

### Installation

```bash
make install
# which runs:
uv venv && uv sync
```

> The repository must contain `pyproject.toml` and `uv.lock`. The `uv.lock` file is generated automatically by `uv sync`.

### Data setup

Place the vLLM repository (provided as attachment) inside `data/raw/`:

```bash
mkdir -p data/raw
cp -r /path/to/vllm-0.10.1 data/raw/
# or unzip it:
unzip vllm-0.10.1.zip -d data/raw/
```

Expected layout before indexing:

```
ls -l data/raw
total 11988
drwxrwxr-x 15 student student 4096 Aug 19 00:27 vllm-0.10.1
-rw-r--r--  1 student student 12267696 Nov  2 22:21 vllm-0.10.1.zip
```

### Indexing

```bash
uv run python -m student index --max_chunk_size 2000
```

Expected output:

```
Indexing repository at 'data/raw/vllm-0.10.1'...
Indexing files: 100%|██████████| 89/89 [00:00<00:00]
Indexed 717 chunks.
Ingestion complete! Indices saved under data/processed/bm25_index

ls -l data/processed
drwxrwxr-x  student  bm25_index
drwxrwxr-x  student  chunks
```

---

## Example Usage

### Search a single query

```bash
uv run python -m student search "How to configure OpenAI server?" --k 10
```

### Answer a single query

```bash
uv run python -m student answer "How to configure OpenAI server?" --k 10
```

### Search a full dataset

```bash
uv run python -m student search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 \
    --save_directory data/output/search_results

# Saved student_search_results to data/output/search_results/dataset_docs_public.json
```

### Evaluate search results against ground truth

```bash
uv run python -m student evaluate \
    --student_results_path data/output/search_results/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10

# Student data is valid: True
# Total number of questions: 100
# Evaluation Results
# ========================================
# Recall@1: 0.450
# Recall@3: 0.590
# Recall@5: 0.650
# Recall@10: 0.720
```

### Answer a full dataset

```bash
uv run python -m student answer_dataset \
    --student_search_results_path data/output/search_results/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer

# Saved student_search_results_and_answer to data/output/search_results_and_answer/dataset_docs_public.json
```

### Inspect an answer

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

### Lint

```bash
make lint
```

---

## Performance Analysis

| Metric | Target | Notes |
|--------|--------|-------|
| Indexing time | ≤ 5 minutes | Typically < 5 seconds for the vLLM repo |
| Cold start latency | ≤ 60 seconds | BM25 index loads in < 1s; LLM load dominates |
| Warm retrieval throughput | ≤ 90s for 1000 questions | BM25 scoring is CPU-bound, very fast after cold start |
| Recall@5 — Docs dataset | ≥ 80% | Markdown paragraph chunking optimised for docs |
| Recall@5 — Code dataset | ≥ 50% | Python AST chunking preserves function/class units |

Exceeding the minimum recall thresholds earns additional credit during evaluation.

---

## Design Decisions

1. **BM25 over TF-IDF**: BM25Okapi applies document-length normalisation and term saturation, which matters in a codebase where the same keyword (e.g. `tokenizer`) appears hundreds of times across files.
2. **AST-based Python chunking**: Splitting at `def`/`class` boundaries keeps retrieval atoms semantically coherent. A question about `get_supported_mm_limits` retrieves the actual method, not a fragment of it.
3. **Paragraph merging for Markdown**: vLLM docs are structured as sections separated by blank lines. Merging adjacent paragraphs up to 2000 chars keeps related content together without creating giant chunks.
4. **Custom code tokeniser**: Snake_case and camelCase splitting means a query for "OpenAI compatible server" matches chunks containing `OpenAICompatibleServer`, `openai_compatible_server`, etc.
5. **CPU-only LLM inference**: `torch.float32` on CPU. Qwen3-0.6B is small enough to answer in acceptable time without a GPU, keeping the setup self-contained.
6. **Pydantic v2**: All data in and out of the pipeline is validated by the exact models specified in the subject. `model_dump_json()` produces the required JSON format directly.
7. **Separate `chunks/` directory**: The `data/processed/` layout matches the subject specification exactly (`bm25_index/` + `chunks/`).

---

## Challenges Faced

- **Code vs. text duality**: Generic sentence splitters destroy code structure. The dual chunking strategy (AST for `.py`, paragraphs for text) was essential to avoid retrieving half a function.
- **Tokenisation for identifiers**: Standard NLP tokenisers drop underscores. The custom tokeniser indexes both the full identifier and its underscore-split sub-parts, which measurably improves recall on method-name queries.
- **Index persistence without re-indexing**: BM25Okapi is not trivially serialisable. The solution separates the model (pickle), metadata (JSON), and chunk texts (pickle) into three files, allowing fast cold-start reloads (< 1 second).
- **LLM context window limits**: Qwen3-0.6B has a 2048-token context window. Each retrieved snippet is truncated to `max_context_length` characters (default 2000) and the prompt is kept concise to avoid truncation of the answer.
- **Recall@k overlap semantics**: The subject specifies 5% overlap relative to the ground-truth source. Correctly implementing this — rather than symmetric overlap — matters when retrieved chunks are larger or smaller than GT sources.

---

## Resources

- [Okapi BM25 — Wikipedia](https://en.wikipedia.org/wiki/Okapi_BM25)
- [rank_bm25 library](https://github.com/dorianbrown/rank_bm25)
- [Qwen3-0.6B model card — HuggingFace](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks — Lewis et al. 2020](https://arxiv.org/abs/2005.11401)
- [Python Fire documentation](https://github.com/google/python-fire)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [vLLM project](https://github.com/vllm-project/vllm)
- [Python `ast` module documentation](https://docs.python.org/3/library/ast.html)

### AI Usage

AI (Claude) was used to:
- Draft initial structure for the Pydantic models and type annotations.
- Suggest the AST-based Python chunking approach and its fallback logic.
- Help format docstrings to PEP 257 / Google style consistently.
- Review the overlap fraction formula against the subject specification.

All AI-generated content was reviewed, tested, and understood before inclusion. No code was blindly copy-pasted — each function was read and validated against the subject requirements and the moulinette output format.
