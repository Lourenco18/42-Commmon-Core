# call me maybe

*This project was created as part of the 42 curriculum by dasantos.*

---

## Description

**call me maybe** is an introduction to **function calling with Large Language Models (LLMs)**. Its goal is to translate natural-language prompts into structured, machine-executable function calls using **constrained decoding** — a technique that guarantees the model can only produce valid function names, even when using a small 0.6B-parameter model.

For example, given the prompt:

```text
What is the product of 3 and 5?
```

the system does **not** answer `"15"`. Instead, it generates:

```json
{
  "prompt": "What is the product of 3 and 5?",
  "name": "fn_multiply_numbers",
  "parameters": {
    "a": 3.0,
    "b": 5.0
  }
}
```

The project uses **Qwen/Qwen3-0.6B** through the provided `llm_sdk` package. Function selection is enforced through constrained decoding. Parameter extraction is handled via regex-based parsing applied after the function is chosen.

---

## Project Structure

```
call-me-maybe/
├── src/
│   ├── __main__.py            # Entry point
│   ├── answer_gen.py          # Core logic: constrained decoding + parameter extraction
│   ├── parsing.py             # CLI argument parsing and file I/O
│   └── validation_parsing.py  # Pydantic models for input validation
├── llm_sdk/
│   └── llm_sdk/
│       └── __init__.py        # LLM wrapper (Small_LLM_Model)
├── data/
│   └── input/
│       ├── functions_definition.json   # Available functions + schemas
│       └── function_calling_tests.json # Test prompts
├── Makefile
└── pyproject.toml
```

---

## Installation

### Prerequisites

* Python 3.10 or later
* `uv` package manager
* The `llm_sdk` package (located in `llm_sdk/` at the project root)

### Setup

> **Note for 42 machines:** the commands below redirect cache and temp directories to `/sgoinfre` to avoid quota issues. Adapt the paths to your own login before running.

```bash
# Clone the repository
git clone <your-repo-url>
cd call-me-maybe

# (42 machines) redirect cache dirs — replace <login> with your 42 login
mkdir -p /sgoinfre/dasantos/.cache/uv
export UV_CACHE_DIR=/sgoinfre/<login>/.cache/uv

mkdir -p /sgoinfre/dasantos/tmp
export TMPDIR=/sgoinfre/<login>/tmp

mkdir -p /sgoinfre/dasantos/.cache
export XDG_CACHE_HOME=/sgoinfre/<login>/.cache

mkdir -p /sgoinfre/dasantos/.local/share
export XDG_DATA_HOME=/sgoinfre/<login>/.local/share

uv sync
uv add accelerate
```

Or simply run:

```bash
make install
```

> The Makefile `install` target handles the above. Remember to update the login variable inside the Makefile if needed.

---

## Running the Program

### Default Paths

Reads from `data/input/` and writes results to `data/output/`.

```bash
make run
```

or equivalently:

```bash
uv run python -m src
```

### Custom Paths

Pass all three flags explicitly:

```bash
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

---

## Additional Makefile Targets

| Target         | Description                                   |
|----------------|-----------------------------------------------|
| `make install` | Set up cache dirs and install dependencies    |
| `make run`     | Run the program with default paths            |
| `make debug`   | Run with `pdb` debugger attached              |
| `make flake`   | Run `flake8` + `mypy` (standard mode)         |
| `make flake-strict` | Run `flake8` + `mypy --strict`           |
| `make clean`   | Remove cache, compiled artifacts, output dir  |

---

## How It Works

### Phase 1 — Function Selection via Constrained Decoding

Language models generate text one token at a time. At each step, the model produces a score (logit) for every token in its vocabulary. Normally the highest-scoring token is selected. Small models are often unreliable when asked to produce specific structured strings from prompting alone.

Constrained decoding solves this by **masking invalid tokens at each generation step**:

```text
Prompt → Tokenise → Input IDs → LLM → Logits
                                          ↓
                               Valid token set computed
                               (which function names can
                                still be completed?)
                                          ↓
                               Invalid tokens → -inf
                                          ↓
                               argmax → next token
                                          ↓
                               Repeat until full name matched
```

The valid token set is derived from the list of known function names. At each step, only tokens that can continue at least one valid function name — given the tokens already generated — are kept. All others are set to `-inf`, making them impossible to select.

This guarantees the model always produces an exact, valid function name — no post-processing or retries needed.

### Phase 2 — Parameter Extraction via Regex

After the function name is resolved, its schema is known. Parameters are extracted from the original prompt using regex-based parsing:

- **Numeric types** (`number`, `integer`, `float`): extracted with `[-+]?\d*\.\d+|[-+]?\d+` in order of appearance.
- **String types**: extracted using quoted-string capture first, then semantic patterns keyed on the parameter name (e.g. `path`, `encoding`, `database`, `query`, `template`).
- **Special case** — `fn_substitute_string_with_regex`: uses a dedicated extraction routine that separately identifies the source string, the regex pattern, and the replacement token.

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| Constrained decoding for function names | Guarantees valid output without relying on model reliability |
| Greedy (argmax) token selection | Deterministic, fast, and sufficient for constrained generation |
| Regex-based parameter extraction | Lightweight and practical for the structured prompts in scope |
| Pydantic models for input validation | Automatic schema validation with clear error messages |
| `argparse` for CLI | Standard, flexible, supports both default and custom paths |
| `llm_sdk` encode/decode APIs only | Uses only the allowed public interfaces from the SDK |
| Output written via `json.dump` | Ensures valid, human-readable JSON output |

---

## Input / Output Format

### Input — `functions_definition.json`

An array of function objects, each with a name, description, typed parameters, and a return type:

```json
[
  {
    "name": "fn_multiply_numbers",
    "description": "Multiply two numbers together and return their product.",
    "parameters": {
      "a": { "type": "number" },
      "b": { "type": "number" }
    },
    "returns": { "type": "number" }
  }
]
```

### Input — `function_calling_tests.json`

An array of prompt objects:

```json
[
  { "prompt": "What is the product of 3 and 5?" }
]
```

### Output — `function_calls.json`

An array of results, one per prompt:

```json
[
  {
    "prompt": "What is the product of 3 and 5?",
    "name": "fn_multiply_numbers",
    "parameters": {
      "a": 3.0,
      "b": 5.0
    }
  }
]
```

---

## Validation

After running, verify output is valid JSON:

```bash
python -c "import json; json.load(open('data/output/function_calls.json')); print('OK')"
```

Check schema compliance:

```python
import json

with open("data/output/function_calls.json") as f:
    results = json.load(f)

with open("data/input/functions_definition.json") as f:
    functions = {fn["name"]: fn for fn in json.load(f)}

for result in results:
    assert result["name"] in functions
    schema = functions[result["name"]]
    for parameter in schema["parameters"]:
        assert parameter in result["parameters"]
    print(f"OK: {result['name']}({result['parameters']})")
```

---

## References

* [Qwen3 Model Card — Hugging Face](https://huggingface.co/Qwen/Qwen3-0.6B)
* [Pydantic v2 Documentation](https://docs.pydantic.dev/)
* [Hugging Face NLP Course — BPE Tokenisation](https://huggingface.co/learn/nlp-course)
* [JSON Schema Specification](https://json-schema.org/)
* [Constrained Decoding Survey (2024)](https://arxiv.org/abs/2403.06988)

---

## AI Usage

AI-assisted tools were used during development for brainstorming, reviewing documentation, and discussing implementation approaches. All generated content was reviewed, understood, tested, and adapted before inclusion in the final project.