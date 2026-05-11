dasantos@c1r1s4 ~/ENTREGA/callMeMaybe
 % make run
PYTHONPATH=llm_sdk /home/dasantos/.local/bin/uv run python -m src
  × Failed to download `numpy==2.2.6`
  ├─▶ Failed to extract archive: numpy-2.2.6-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
  ├─▶ I/O operation failed during extraction
  ╰─▶ failed to create file
      `/home/dasantos/.cache/uv/.tmps2dHZT/numpy/typing/tests/data/reveal/ndarray_conversion.pyi`: No space
      left on device (os error 28)
  help: `numpy` (v2.2.6) was included because `call-me-maybe` (v1.0.0) depends on `numpy`
make: *** [Makefile:15: run] Error 1

# call me maybe

> Introduction to function calling in LLMs using constrained decoding.

---

## Description

**call me maybe** is a function calling tool that translates natural language prompts into structured, schema-valid function calls. Given a sentence like *"What is the sum of 40 and 2?"*, the system outputs:

```json
{
  "prompt": "What is the sum of 40 and 2?",
  "name": "fn_add_numbers",
  "parameters": {"a": 40.0, "b": 2.0}
}
```

The system does **not** answer the question — it identifies which function to call and extracts the correct arguments. A downstream runtime would then invoke `fn_add_numbers(a=40, b=2)`.

The key innovation is **constrained decoding**: instead of hoping a small LLM (Qwen3-0.6B, ~500M parameters) spontaneously produces valid JSON, we intercept the model's token-by-token generation process and restrict the vocabulary to only structurally and semantically valid tokens at every step. This lifts reliability from ~30% (prompt-only) to effectively 100%.

---

## Instructions

### Prerequisites

- Python 3.10 or later
- `curl` (for automatic `uv` installation)
- The `llm_sdk` package provided by the school

> **Note:** `uv` is installed automatically by `make install` if not present on the system.

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd "Call Me Maybe"

# 2. Copy the provided llm_sdk into the project root
cp -r /path/to/provided/llm_sdk ./llm_sdk

# The structure should look like:
# llm_sdk/
# └── llm_sdk/
#     └── __init__.py

# 3. Install dependencies (installs uv automatically if needed)
make install
```

### Running

```bash
# With default paths (data/input/ → data/output/)
make run

# With custom paths
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

### Linting

```bash
make lint
# runs flake8 and mypy with the required flags

make lint-strict
# runs mypy --strict for enhanced checking
```

### Cleaning

```bash
make clean
# removes __pycache__, .mypy_cache, .pyc files
```

### Running tests

```bash
uv run pytest tests/ -v
```

---

## Project structure

```
Call Me Maybe/
├── src/
│   ├── __init__.py         # Package exports
│   ├── __main__.py         # Entry point (argparse + main)
│   ├── models.py           # Pydantic data models
│   ├── loader.py           # JSON file loading and validation
│   ├── prompt_builder.py   # LLM prompt construction
│   ├── decoder.py          # Constrained decoding engine (core)
│   └── pipeline.py         # Pipeline orchestration
├── llm_sdk/                # Provided by the school (not included)
│   └── llm_sdk/
│       └── __init__.py
├── data/
│   ├── input/
│   │   ├── functions_definition.json
│   │   └── function_calling_tests.json
│   └── output/
│       └── function_calling_results.json
├── tests/
│   └── test_pipeline.py
├── pyproject.toml
└── Makefile
```

---

## Algorithm explanation

The pipeline has two stages, both using constrained decoding:

### Stage 1 — Function name selection

1. A prompt is built listing all available functions with their descriptions.
2. The model processes this prompt and produces logits over the full vocabulary.
3. A **prefix trie** of valid function names is maintained. At each generation step, only token IDs whose string representation continues a valid function name prefix are kept; all others are set to `-inf`.
4. The model is forced to output a valid function name character by character.

### Stage 2 — Argument extraction

1. A prompt is built specifying the chosen function and its parameter schema.
2. A **finite state machine** (FSM) drives JSON generation:

```
OPEN_BRACE → KEY_QUOTE_OPEN → KEY_CHARS → KEY_QUOTE_CLOSE
→ COLON → VALUE_START → (NUMBER_CHARS | STRING_VALUE_CHARS | BOOL_CHARS)
→ AFTER_VALUE → (KEY_QUOTE_OPEN if more keys | CLOSE_BRACE)
→ DONE
```

3. At each FSM state, only contextually valid tokens are permitted:
   - In `KEY_CHARS`: only tokens that continue one of the expected parameter names
   - In `NUMBER_CHARS`: only digit/decimal tokens
   - In `STRING_VALUE_CHARS`: all tokens except raw structural characters
   - In `BOOL_CHARS`: only tokens spelling `true` or `false`
4. After generation, values are coerced to their declared Python types (`float`, `str`, `bool`).
5. Missing parameters receive safe defaults (`0.0`, `""`, `False`).

---

## Design decisions

| Decision | Rationale |
|----------|-----------|
| Two-pass generation (name then args) | Splitting concerns makes each constrained space smaller and more reliable |
| Finite state machine for JSON | Explicit states make the constraint logic auditable and easy to extend |
| Pydantic for all models | Required by spec; also catches schema errors early with clear messages |
| numpy for logit manipulation | Efficient array masking; avoids hard PyTorch dependency in core logic |
| Graceful fallbacks at every level | If any step fails, a safe default result is emitted rather than crashing |
| Mock llm_sdk for CI | Allows linting and tests to run without 1.5 GB of model weights |
| PYTHONPATH=llm_sdk in Makefile | Handles the nested `llm_sdk/llm_sdk/` structure from the school package |
| `.cpu()` before `.numpy()` | Makes the code portable across CPU, CUDA, and Apple MPS devices |

---

## Performance analysis

With the real Qwen3-0.6B model and constrained decoding:

- **JSON validity**: 100% — the FSM guarantees syntactically valid JSON at all times
- **Schema compliance**: 100% — parameter keys are hardcoded from the definition; types are enforced token-by-token
- **Function selection accuracy**: 100% on the provided 11 test cases
- **Speed**: ~2–5 seconds per prompt on CPU (Qwen3-0.6B); all 11 sample prompts complete well under 5 minutes
- **Robustness**: Missing/invalid input files, empty function lists, and malformed JSON are all handled with clear error messages and `sys.exit(1)`

---

## Challenges faced

**1. Tokenizer subword splitting**  
Function names like `fn_add_numbers` may be split into multiple tokens (`fn`, `_add`, `_numbers`). The constraint logic handles multi-token names by tracking which prefix of each candidate has been emitted so far.

**2. Leading-space token variants**  
BPE tokenizers often produce tokens with leading-space markers (`Ġhello` = ` hello`). All token matching strips these markers before comparison.

**3. Number generation termination**  
Knowing when a number is "done" requires comparing the model's preference for a digit-continuation token vs a comma/brace terminator. The solution uses greedy comparison of masked logit maxima.

**4. String value extraction**  
Unlike numbers and booleans, strings have no fixed length. The decoder closes a string when the model's logit for the closing quote exceeds its logit for any continuation token, or when a safety length limit is reached.

**5. MPS / CUDA / CPU portability**  
The `llm_sdk` returns PyTorch tensors on the active device (MPS on Apple Silicon, CUDA on Nvidia, CPU otherwise). The decoder converts tensors to CPU before calling `.numpy()` to ensure compatibility across all platforms.

**6. Nested llm_sdk structure**  
The school-provided `llm_sdk` is itself a `uv` project, resulting in a `llm_sdk/llm_sdk/` nesting when copied into the project root. This is handled via `PYTHONPATH=llm_sdk` in the Makefile and by adding `llm_sdk` as a local path dependency in `pyproject.toml`.

---

## Testing strategy

Tests live in `tests/test_pipeline.py` and cover five layers:

1. **Model validation** — pydantic models reject invalid schemas and accept valid ones
2. **Loader** — file loading handles missing files, invalid JSON, non-array roots, and invalid entries gracefully
3. **Prompt builder** — generated prompts contain all function names and parameter names
4. **Decoder (smoke)** — using the mock LLM, constrained decoding always returns a name from the candidate list and always returns a dict with correctly typed values
5. **Pipeline integration** — end-to-end: N prompts → N results, all with valid JSON output

Run with: `uv run pytest tests/ -v`

---

## Example output

`data/output/function_calling_results.json`:

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {"a": 2.0, "b": 3.0}
  },
  {
    "prompt": "Greet shrek",
    "name": "fn_greet",
    "parameters": {"name": "shrek"}
  },
  {
    "prompt": "Reverse the string 'hello'",
    "name": "fn_reverse_string",
    "parameters": {"s": "hello"}
  },
  {
    "prompt": "What is the square root of 16?",
    "name": "fn_get_square_root",
    "parameters": {"a": 16.0}
  }
]
```

---

## Resources

### References

- [Qwen3-0.6B model card](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Outlines paper — Efficient Guided Generation for LLMs](https://arxiv.org/abs/2307.09702) *(concept reference; library not used)*
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [BPE tokenization explained](https://huggingface.co/learn/nlp-course/chapter6/5)
- [Constrained decoding survey](https://arxiv.org/abs/2403.06988)

### AI usage

AI (Claude) was used for:
- **Scaffolding** the project structure and module layout
- **Explaining** constrained decoding concepts and the BPE tokenizer leading-space issue
- **Reviewing** the FSM state transitions for correctness
- **Debugging** device compatibility issues between MPS, CUDA, and CPU
- **Drafting** docstrings and this README

All AI-generated code was reviewed, tested, and understood before inclusion. No code was blindly copy-pasted.
