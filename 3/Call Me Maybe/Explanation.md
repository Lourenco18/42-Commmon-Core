# Call Me Maybe — Project Explanation

## What this project is about

You are building a **function calling system** for a small LLM. Given a natural language
sentence like *"What is the sum of 40 and 2?"*, your program must output structured JSON
like this:

```json
{
  "prompt": "What is the sum of 40 and 2?",
  "name": "fn_add_numbers",
  "parameters": {"a": 40.0, "b": 2.0}
}
```

The LLM does not directly compute the answer — it picks the right function and extracts
the arguments. A downstream system would then actually call `fn_add_numbers(a=40, b=2)`.

---

## The core challenge: why not just prompt the model?

Small models (like Qwen3-0.6B, ~500M parameters) are very unreliable at generating valid
JSON when simply prompted. They might succeed 30% of the time. The solution is
**constrained decoding**: you intercept the model's token-by-token generation process and
force it to only ever produce tokens that maintain a valid JSON structure.

---

## Key concepts explained

### 1. Tokens and token IDs

LLMs do not read words — they read **tokens**, which are subword fragments. For example:
- `"hello"` → `[15339]`
- `"fn_add_numbers"` → might be split into `["fn", "_add", "_numbers"]` → `[3261, 914, 5219]`

The `llm_sdk` gives you:
- `encode(text)` → converts a string to a list of integer token IDs
- `decode(token_ids)` → converts token IDs back to a string
- `get_path_to_vocabulary_json()` → path to a JSON file listing every token string mapped to its ID

### 2. Logits

At each generation step, the model produces a **logit** (raw score) for every token in its
vocabulary (typically 32,000+ tokens). Higher logit = more likely to be chosen next.

You get logits by calling:
```python
logits = model.get_logits_from_input_ids(input_ids_tensor)
```

Normally, you pick the token with the highest logit (greedy decoding) or sample from the
distribution. With constrained decoding, you **set invalid tokens to `-inf`** before
selecting, so only valid tokens can ever be chosen.

### 3. Constrained decoding — step by step

Imagine you are generating the arguments JSON for `fn_add_numbers`, which takes
`{"a": number, "b": number}`. Here is how you constrain each position:

```
Position 0: must be "{"         → allow only token(s) that produce "{"
Position 1: must be "\"a\""      → allow only token(s) that produce the key "a"
Position 2: must be ":"         → allow only ":"
Position 3: must be a number    → allow digits, minus sign, decimal point tokens
Position 4: must be "," or "}"  → allow only those
Position 5: must be "\"b\""      → allow only key "b"
...and so on
```

At each step you:
1. Get logits from the model
2. Set every token that is NOT valid at this position to `-float('inf')`
3. Apply softmax and pick the highest remaining logit (or sample)
4. Append the chosen token to the sequence and repeat

### 4. The vocabulary JSON file

This file maps every token ID to its string form. You use it to answer questions like:
- "Which token IDs correspond to the string `fn_add_numbers`?"
- "Which token IDs start with a digit (so I can allow numeric values)?"

```python
import json

with open(model.get_path_to_vocabulary_json()) as f:
    vocab = json.load(f)  # { "token_string": token_id, ... }

# Reverse it for lookups by ID
id_to_token = {v: k for k, v in vocab.items()}
```

---

## Project structure

```
project/
├── src/
│   ├── __init__.py
│   ├── __main__.py          ← entry point, argparse
│   ├── models.py            ← pydantic models
│   ├── loader.py            ← JSON file loading with error handling
│   ├── prompt_builder.py    ← builds the text prompt for the LLM
│   ├── decoder.py           ← constrained decoding logic (the hard part)
│   └── pipeline.py          ← ties everything together
├── llm_sdk/                 ← provided, copy as-is
├── data/
│   ├── input/
│   │   ├── function_definitions.json
│   │   └── function_calling_tests.json
│   └── output/              ← generated, not committed to git
├── pyproject.toml
├── uv.lock
├── Makefile
├── .gitignore
└── README.md
```

---

## Tools and libraries used

| Tool | Why |
|------|-----|
| `uv` | Fast Python package manager; runs the project with `uv run python -m src` |
| `pydantic` | Data validation — all your data classes (function definitions, results) must use it |
| `numpy` | Useful for manipulating logit arrays (setting values to `-inf`, argmax, etc.) |
| `json` | Standard library for reading/writing JSON files |
| `argparse` | Standard library for CLI arguments (`--input`, `--output`, `--functions_definition`) |
| `flake8` | Linting — enforces code style |
| `mypy` | Static type checking — all functions need type hints |
| `llm_sdk` | Provided wrapper around the Qwen3-0.6B model |
| `pytest` | For writing your own tests (not graded, but essential for development) |

**Forbidden**: `dspy`, `pytorch` (direct), `huggingface transformers`, `outlines` — these
would automate the very constrained decoding logic you are meant to implement yourself.

---

## The two-stage generation strategy

### Stage 1 — Select the function name

Build a prompt like:

```
Available functions:
- fn_add_numbers: Add two numbers together
- fn_greet: Generate a greeting
- fn_reverse_string: Reverse a string

User request: "What is the sum of 40 and 2?"

Call function:
```

Then run constrained decoding where the only valid tokens are those that spell out one
of the available function names (e.g., `fn_add_numbers`). You do this character-by-character
or subword-by-subword, building a prefix tree (trie) of valid function name continuations.

### Stage 2 — Generate the arguments

Once you know the function name, you know exactly which parameters are required and what
types they should have. Build the arguments JSON token-by-token with full schema enforcement:

- Only allow the exact parameter key names (from the function definition)
- Only allow value tokens matching the declared type (`number`, `string`, `boolean`)
- Only allow structural tokens (`{`, `}`, `"`, `:`, `,`) in the correct positions

---

## Pydantic models (models.py)

```python
from pydantic import BaseModel
from typing import Dict, Any

class ParameterDef(BaseModel):
    type: str  # "number", "string", "boolean"

class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, ParameterDef]
    returns: ParameterDef

class FunctionCallResult(BaseModel):
    prompt: str
    name: str
    parameters: Dict[str, Any]
```

---

## Makefile rules

```makefile
install:
    uv sync

run:
    uv run python -m src

debug:
    uv run python -m pdb -m src

clean:
    find . -type d -name __pycache__ -exec rm -rf {} +
    rm -rf .mypy_cache

lint:
    flake8 .
    mypy . --warn-return-any --warn-unused-ignores \
           --ignore-missing-imports --disallow-untyped-defs \
           --check-untyped-defs
```

---

## Common mistakes to avoid

1. **Prompting only and hoping** — the model will not reliably produce valid JSON from a
   prompt alone. You must implement real constrained decoding.

2. **Using private `_methods`** from `llm_sdk` — forbidden. Only use the four public methods
   documented in the spec.

3. **Hardcoding function names or argument values** — the grader will use different input
   files. Your decoder must work with any function definition.

4. **Crashing on bad input** — wrap file loading and JSON parsing in `try/except`. Print
   a clear error message and exit gracefully.

5. **Forgetting type coercion** — when the function definition says `"type": "number"`, the
   output JSON must have a float, not a string. E.g. `{"a": 40.0}` not `{"a": "40"}`.

6. **Not running mypy/flake8 before submitting** — the linter will catch type hint errors
   that will cost you points.

---

## Suggested development order

1. Get the project running end-to-end with a dummy decoder (always picks the first function,
   always returns `{}` for arguments). This verifies your CLI, file I/O, and output format work.
2. Implement the vocabulary loading and build your token → string mapping.
3. Implement constrained decoding for function name selection only.
4. Implement constrained decoding for arguments (start with `number` type only, then add
   `string`, then `boolean`).
5. Test edge cases: empty strings, large numbers, functions with 3+ parameters.
6. Add type hints, docstrings, pass mypy and flake8.
7. Write the README.

---

## Resources to read

- Qwen3 model card: https://huggingface.co/Qwen/Qwen3-0.6B
- Pydantic docs: https://docs.pydantic.dev
- Outlines paper (understanding constrained decoding): https://arxiv.org/abs/2307.09702
  (you cannot use the library, but the paper explains the concept well)
- BPE tokenization explained: https://huggingface.co/learn/nlp-course/chapter6/5