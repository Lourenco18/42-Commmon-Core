*This project has been created as part of the 42 curriculum by \<your_login\>.*

# RAG against the machine

## Description

A **Retrieval-Augmented Generation (RAG)** system that answers questions about the vLLM codebase. The system ingests the vLLM repository, builds a searchable knowledge base using BM25, retrieves relevant code snippets and documentation for any query, and generates natural language answers using the **Qwen/Qwen3-0.6B** LLM.

**Goal**: Given a question about vLLM, find the relevant source files and generate an accurate, context-grounded answer.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAG Pipeline                                │
│                                                                 │
│  Repository ──► Chunker ──► BM25 Index ──► Retriever           │
│                                                |                │
│  Query ──────────────────────────────────────►│                │
│                                                ▼                │
│                                          Top-k Chunks           │
│                                                |                │
│                                                ▼                │
│                                       Qwen3-0.6B LLM           │
│                                                |                │
│                                                ▼                │
│                                          Answer (JSON)          │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**
- `src/student/chunker.py` — File chunking strategies (Python + text)
- `src/student/indexer.py` — BM25 index building and persistence
- `src/student/generator.py` — LLM answer generation (Qwen3-0.6B)
- `src/student/models.py` — Pydantic data models
- `src/student/__main__.py` — CLI (Python Fire)

---

## Chunking Strategy

Different strategies are applied based on file type:

**Python files (`.py`)**: AST-based chunking splits on top-level `def` and `class` boundaries, keeping logical code units together. Falls back to line-based splitting for files with syntax errors.

**Text/Markdown files (`.md`, `.rst`, `.txt`, etc.)**: Paragraph-based chunking splits on double newlines and merges adjacent paragraphs up to `max_chunk_size` characters (default: 2000).

Both strategies include a size-based fallback that splits along line boundaries when a block exceeds `max_chunk_size`.

---

## Retrieval Method

**BM25 (Best Match 25)** — a probabilistic ranking function based on term frequency and inverse document frequency.

**Tokenization**: Text is split on non-alphanumeric characters, lowercased, and expanded for camelCase and snake_case identifiers. This improves recall on code-heavy queries.

**Ranking**: For a query, each chunk is scored with BM25Okapi. The top-k scoring chunks are returned with their `file_path`, `first_character_index`, and `last_character_index`.

---

## Instructions

### Requirements

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) package manager

### Installation

```bash
make install
# or manually:
uv venv && uv sync
```

### Data Setup

Place the vLLM repository in `data/raw/`:

```bash
mkdir -p data/raw
cp -r /path/to/vllm-0.10.1 data/raw/
```

### Indexing

```bash
uv run python -m student index --max_chunk_size 2000
# Output: data/processed/bm25_index/
```

### Search a single query

```bash
uv run python -m student search "How to configure OpenAI server?" --k 10
```

### Answer a single query

```bash
uv run python -m student answer "How to configure OpenAI server?" --k 10
```

### Search a dataset

```bash
uv run python -m student search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 \
    --save_directory data/output/search_results
```

### Evaluate search results

```bash
uv run python -m student evaluate \
    --student_results_path data/output/search_results/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json \
    --k 10
```

### Answer a dataset

```bash
uv run python -m student answer_dataset \
    --student_search_results_path data/output/search_results/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer
```

### Lint

```bash
make lint
```

---

## Performance Analysis

| Dataset | Metric | Target | Notes |
|---------|--------|--------|-------|
| Docs    | Recall@5 | ≥ 80% | Markdown/RST chunking |
| Code    | Recall@5 | ≥ 50% | Python AST chunking |

- **Indexing time**: Under 5 minutes for the vLLM repository.
- **Cold start latency**: Under 60 seconds (BM25 loads from pickle in seconds; LLM load is the bottleneck).
- **Warm retrieval throughput**: BM25 scoring is fast; 1000 queries in under 90 seconds is achievable without GPU.

---

## Design Decisions

1. **BM25 over TF-IDF**: BM25Okapi has better term saturation behavior for code, where keywords repeat heavily.
2. **AST chunking for Python**: Preserves semantic units (functions, classes) as retrieval atoms. This is critical for code recall — a question about a specific method should retrieve that method's chunk.
3. **Paragraph chunking for text**: Markdown sections naturally correspond to documentation topics.
4. **No GPU required**: Uses `torch.float32` on CPU. The Qwen3-0.6B model is small enough to run without a GPU.
5. **Pydantic v2**: Full type safety and automatic JSON serialization/deserialization.

---

## Challenges Faced

- **Code vs. text duality**: The vLLM repo mixes Python source and Markdown docs. Different chunking strategies are essential — generic sentence splitting would break code logic.
- **Tokenization for code**: Standard NLP tokenizers split on underscores, breaking Python identifiers. The custom tokenizer retains the full token plus its parts for better recall.
- **Index persistence**: Serializing BM25Okapi (pickle) plus chunk metadata (JSON) + chunk texts (pickle) avoids re-indexing at every startup.
- **LLM context window**: Qwen3-0.6B has limited context. The prompt builder truncates each snippet to `max_context_length` characters and limits the number of sources.

---

## Resources

- [BM25 — Wikipedia](https://en.wikipedia.org/wiki/Okapi_BM25)
- [rank_bm25 library](https://github.com/dorianbrown/rank_bm25)
- [Qwen3 model card](https://huggingface.co/Qwen/Qwen3-0.6B)
- [RAG paper — Lewis et al. 2020](https://arxiv.org/abs/2005.11401)
- [Python Fire documentation](https://github.com/google/python-fire)
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)
- [vLLM project](https://github.com/vllm-project/vllm)

### AI Usage

AI (Claude) was used to:
- Draft initial boilerplate for Pydantic models and type annotations.
- Suggest the AST-based Python chunking approach.
- Help structure docstrings to PEP 257 / Google style.

All generated code was reviewed, tested, and understood before inclusion.
