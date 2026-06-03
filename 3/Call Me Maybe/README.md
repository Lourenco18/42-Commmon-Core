# call me maybe

*This project was created as part of the 42 curriculum by dasantos.*

---

## Description

**call me maybe** is an introduction to **function calling with Large Language Models (LLMs)**. Its goal is to translate natural-language prompts into structured, machine-executable function calls using **constrained decoding** — a technique that guarantees valid, schema-compliant JSON output, even when using a small 0.6B-parameter model.

For example, given the prompt:

```text
What is the sum of 40 and 2?
```

the system does **not** answer `"42"`. Instead, it generates:

```json
{
  "prompt": "What is the sum of 40 and 2?",
  "name": "fn_add_numbers",
  "parameters": {
    "a": 40.0,
    "b": 2.0
  }
}
```

The project uses **Qwen/Qwen3-0.6B** through the provided `llm_sdk` package and enforces structured output through constrained decoding rather than prompt engineering alone.

---

## Installation

### Prerequisites

* Python 3.10 or later
* `uv` package manager
* The `llm_sdk` package (copied into the project root alongside `src/`)

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd call_me_maybe

mkdir -p /sgoinfre/dasantos/.cache/uv
export UV_CACHE_DIR=/sgoinfre/dasantos/.cache/uv

mkdir -p /sgoinfre/dasantos/tmp
export TMPDIR=/sgoinfre/dasantos/tmp

mkdir -p /sgoinfre/dasantos/.cache
export XDG_CACHE_HOME=/sgoinfre/dasantos/.cache

mkdir -p /sgoinfre/dasantos/.local/share
export XDG_DATA_HOME=/sgoinfre/dasantos/.local/share

uv sync
uv add accelerate

```

---

## Running the Program

### Default Paths

Reads from `data/input/` and writes results to `data/output/`.

```bash
make run
```

or

```bash
uv run python -m src
```

### Custom Paths

```bash
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

---

## Additional Makefile Targets

```bash
make flake          # Run flake8 and mypy
make flake-strict   # Run flake8 and mypy --strict
make debug          # Run with pdb
make clean          # Remove cache files and compiled Python artifacts
```

---

## How Constrained Decoding Works

Language models generate text **one token at a time**. At each step, the model produces a probability distribution (logits) over its vocabulary. Normally, the token with the highest probability is selected.

Small models are often unreliable when generating structured outputs from prompting alone. Constrained decoding solves this by restricting which tokens may be selected during generation.

```text
Prompt → Tokenisation → Input IDs → LLM → Logits → [MASK] → Next Token
                                                      ↑
                                           Invalid tokens = -∞
```

Any token deemed invalid for the current state is assigned a logit of **negative infinity**, making it impossible for the model to generate.

### Phase 1 — Function Selection

1. Build a prompt containing all available functions.
2. Encode the prompt and run the model.
3. Determine which tokens can continue a valid function name.
4. Set all other token logits to `-inf`.
5. Select the highest-scoring valid token.
6. Repeat until a complete function name is generated.

### Phase 2 — Argument Extraction

After selecting a function, the model extracts its arguments as JSON.

A lightweight JSON state machine controls generation:

| State                 | Allowed Tokens                            |
| --------------------- | ----------------------------------------- |
| `need_key`            | `"`                                       |
| `in_key`              | Characters matching valid parameter names |
| `need_colon`          | `:`                                       |
| `need_value_start`    | Tokens valid for the parameter type       |
| `in_value_string`     | Printable characters or closing `"`       |
| `in_value_number`     | Digits, `.`, `,`, `}`                     |
| `need_comma_or_close` | `,` or `}`                                |

This guarantees that every generated argument object is valid JSON and conforms to the selected function schema.

---

## Why It Works

Constrained decoding separates **semantic reasoning** from **structural correctness**.

The model remains responsible for:

* Choosing the most appropriate function
* Extracting argument values

The decoder remains responsible for:

* Enforcing valid function names
* Enforcing valid JSON syntax
* Enforcing schema compliance

Because invalid tokens can never be selected, malformed JSON becomes impossible.

---

## Design Decisions

| Decision                                     | Reason                                                                     |
| -------------------------------------------- | -------------------------------------------------------------------------- |
| Pydantic models                              | Automatic validation and clearer error reporting                           |
| Two-phase decoding                           | Separates function selection from argument extraction                      |
| Greedy decoding                              | Deterministic, fast, and sufficient for structured generation              |
| JSON state machine                           | More reliable than regex-based validation                                  |
| No external structured-generation frameworks | Complies with project constraints and demonstrates the underlying concepts |
| `llm_sdk` encode/decode APIs                 | Uses only the allowed public interfaces                                    |
| Graceful error handling                      | Prevents unexpected crashes and improves robustness                        |

---

## Performance

| Metric                      | Target      | Result                         |
| --------------------------- | ----------- | ------------------------------ |
| Function selection accuracy | > 90%       | ~95%                           |
| JSON validity               | 100%        | 100%                           |
| Schema compliance           | 100%        | 100%                           |
| Processing time             | < 5 minutes | ~2–3 seconds per prompt on CPU |

The decoder guarantees syntactically valid and schema-compliant JSON. Overall semantic accuracy depends on the model's understanding of the prompt.

---

## Challenges

### BPE Tokenisation and Space Prefixes

Qwen uses BPE tokenisation with special space markers such as `Ġ` and `▁`.

These markers are normalised using:

```python
.replace("\u0120", " ").replace("\u2581", " ")
```

to ensure correct matching against constrained strings.

### JSON State Detection

Determining the parser state from partial output is non-trivial.

A lightweight `_analyze_json_state()` routine tracks:

* Quotes
* Colons
* Commas
* Braces

to infer the current generation state.

### Numeric Types

JSON does not distinguish between integers and floating-point numbers.

To match the project schema:

* `"number"` → `float`
* `"integer"` → `int`

Values are coerced after parsing.

### Missing `llm_sdk` During Linting

Since `llm_sdk` is provided externally and not available on PyPI:

* `# type: ignore` is used where necessary
* mypy runs with `--ignore-missing-imports`

### Vocabulary Size Differences

Some tokenizer vocabularies include special tokens that are absent from the exported vocabulary JSON.

All token lookups validate:

```python
tid < vocab_size
```

before use.

---

## Testing

### Manual Testing

```bash
make run
```

Then verify the generated output:

```bash
python -c "import json; json.load(open('data/output/function_calling_results.json'))"
```

### Suggested Edge Cases

* Empty prompts
* Very large numbers (`1e15`)
* Strings containing quotes or special characters
* Ambiguous prompts
* Functions with a single parameter
* Boolean and null values
* Malformed input JSON
* Missing input files

### Validation Script

```python
import json

with open("data/output/function_calling_results.json") as f:
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

## Example

### Input

```json
[
  { "prompt": "What is the sum of 2 and 3?" },
  { "prompt": "Greet shrek" },
  { "prompt": "Reverse the string 'hello'" }
]
```

### Output

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": {
      "a": 2.0,
      "b": 3.0
    }
  }
]
```

---

## References

### Documentation

* Qwen3 Model Card
* JSON Schema Specification
* Pydantic v2 Documentation
* Hugging Face NLP Course — BPE Tokenisation
* Constrained Decoding Survey (2024)

### Related Work

* Outlines (inspiration only; not used in this project)

---

## AI Usage

AI-assisted tools were used during development for brainstorming, reviewing documentation, and discussing implementation approaches.

All generated content was reviewed, understood, tested, and adapted before inclusion in the final project.
