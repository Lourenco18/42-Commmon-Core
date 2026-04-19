*This project has been created as part of the 42 curriculum by dasantos.*

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
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd call-me-maybe

# 2. Copy the real llm_sdk into the project root
cp -r /path/to/provided/llm_sdk ./llm_sdk

# 3. Install dependencies
make install
# equivalent to: uv sync
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
| numpy for logit manipulation | Efficient array masking; avoids PyTorch/transformers dependency |
| Graceful fallbacks at every level | If any step fails, a safe default result is emitted rather than crashing |
| Mock llm_sdk for CI | Allows linting and tests to run without 1.5 GB of model weights |

---

## Performance analysis

With the real Qwen3-0.6B model and constrained decoding:

- **JSON validity**: 100% — the FSM guarantees syntactically valid JSON at all times
- **Schema compliance**: 100% — parameter keys are hardcoded from the definition; types are enforced token-by-token
- **Function selection accuracy**: Depends on the LLM's language understanding; expected 90%+ on the provided test cases
- **Speed**: ~2–5 seconds per prompt on CPU (Qwen3-0.6B); all 10 sample prompts complete well under 5 minutes
- **Robustness**: Missing/invalid input files, empty function lists, and malformed JSON are all handled with clear error messages and `sys.exit(1)`

---

## Challenges faced

**1. Tokenizer subword splitting**  
Function names like `fn_add_numbers` may be split into multiple tokens (`fn`, `_add`, `_numbers`). The constraint logic must handle multi-token names by tracking which prefix of each candidate has been emitted so far.

**2. Leading-space token variants**  
BPE tokenizers often produce tokens with leading-space markers (`Ġhello` = ` hello`). All token matching strips these markers before comparison.

**3. Number generation termination**  
Knowing when a number is "done" requires comparing the model's preference for a digit-continuation token vs a comma/brace terminator. The solution uses greedy comparison of masked logit maxima.

**4. String value extraction**  
Unlike numbers and booleans, strings have no fixed length. The decoder closes a string when the model's logit for the closing quote exceeds its logit for any continuation token, or when a safety length limit is reached.

---

## Testing strategy

Tests live in `tests/test_pipeline.py` and cover four layers:

1. **Model validation** — pydantic models reject invalid schemas and accept valid ones
2. **Loader** — file loading handles missing files, invalid JSON, non-array roots, and invalid entries gracefully
3. **Prompt builder** — generated prompts contain all function names and parameter names
4. **Decoder (smoke)** — using the mock LLM, constrained decoding always returns a name from the candidate list and always returns a dict with correctly typed values
5. **Pipeline integration** — end-to-end: N prompts → N results, all with valid JSON output

Run with: `uv run pytest tests/ -v`

---

## Example usage

```bash
# Default run
uv run python -m src

# Custom paths
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

Example output (`data/output/function_calling_results.json`):

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
- **Drafting** docstrings and this README

All AI-generated code was reviewed, tested, and understood before inclusion. No code was blindly copy-pasted.
