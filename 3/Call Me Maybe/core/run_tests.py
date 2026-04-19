"""Standalone test runner - no pytest or pydantic required.

Runs all tests using only stdlib + numpy (which are always available).
Pydantic is mocked minimally so the full logic can be tested.
"""
import json
import os
import sys
import tempfile
import traceback
from typing import Any, Callable, List, Tuple

# ── Minimal pydantic stub so src modules import cleanly ──────────────────────
import types

pydantic_mod = types.ModuleType("pydantic")


class _BaseModel:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return cls(**data)
        return data

    def model_dump(self) -> dict:
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


def _field_validator(*args: Any, **kwargs: Any) -> Callable:  # type: ignore
    def decorator(fn: Callable) -> Callable:
        return fn
    return decorator


pydantic_mod.BaseModel = _BaseModel  # type: ignore
pydantic_mod.field_validator = _field_validator  # type: ignore


class _ValidationError(Exception):
    pass


pydantic_mod.ValidationError = _ValidationError  # type: ignore
sys.modules["pydantic"] = pydantic_mod

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Test framework ────────────────────────────────────────────────────────────
PASSED: List[str] = []
FAILED: List[Tuple[str, str]] = []


def test(name: str) -> Callable:
    """Decorator to register a test function."""
    def decorator(fn: Callable) -> Callable:
        try:
            fn()
            PASSED.append(name)
            print(f"  PASS  {name}")
        except Exception:
            tb = traceback.format_exc()
            FAILED.append((name, tb))
            print(f"  FAIL  {name}")
            print("        " + tb.strip().splitlines()[-1])
        return fn
    return decorator


def assert_eq(a: Any, b: Any, msg: str = "") -> None:
    """Assert two values are equal."""
    if a != b:
        raise AssertionError(
            f"{msg + ': ' if msg else ''}{a!r} != {b!r}"
        )


def assert_in(a: Any, b: Any, msg: str = "") -> None:
    """Assert a is in b."""
    if a not in b:
        raise AssertionError(
            f"{msg + ': ' if msg else ''}{a!r} not in {b!r}"
        )


def assert_isinstance(a: Any, t: Any, msg: str = "") -> None:
    """Assert a is an instance of t."""
    if not isinstance(a, t):
        raise AssertionError(
            f"{msg + ': ' if msg else ''}{a!r} is not {t}"
        )


# ── Import project modules ────────────────────────────────────────────────────
from src.models import (  # noqa: E402
    FunctionCallResult,
    FunctionDefinition,
    ParameterDef,
    PromptEntry,
    ReturnDef,
)
from src.prompt_builder import (  # noqa: E402
    build_argument_extraction_prompt,
    build_function_selection_prompt,
)
from src.decoder import (  # noqa: E402
    ConstrainedDecoder,
    _clean,
    _coerce_value,
    _load_vocabulary,
    _mask_to_allowed,
)
from llm_sdk import Small_LLM_Model  # noqa: E402
import numpy as np  # noqa: E402

# ── Sample data ───────────────────────────────────────────────────────────────
FN_ADD = FunctionDefinition(
    name="fn_add_numbers",
    description="Add two numbers.",
    parameters={
        "a": ParameterDef(type="number"),
        "b": ParameterDef(type="number"),
    },
    returns=ReturnDef(type="number"),
)
FN_GREET = FunctionDefinition(
    name="fn_greet",
    description="Greet a person.",
    parameters={"name": ParameterDef(type="string")},
    returns=ReturnDef(type="string"),
)
FN_IS_EVEN = FunctionDefinition(
    name="fn_is_even",
    description="Check if a number is even.",
    parameters={"n": ParameterDef(type="number")},
    returns=ReturnDef(type="boolean"),
)

ALL_FNS = [FN_ADD, FN_GREET, FN_IS_EVEN]

# ── Tests: models ─────────────────────────────────────────────────────────────
print("\n[Models]")


@test("FunctionDefinition stores name and parameters")
def _() -> None:
    assert_eq(FN_ADD.name, "fn_add_numbers")
    assert_in("a", FN_ADD.parameters)
    assert_eq(FN_ADD.parameters["a"].type, "number")


@test("FunctionCallResult.model_dump has correct keys")
def _() -> None:
    r = FunctionCallResult(
        prompt="test", name="fn_greet", parameters={"name": "alice"}
    )
    d = r.model_dump()
    assert_in("prompt", d)
    assert_in("name", d)
    assert_in("parameters", d)
    assert_eq(d["name"], "fn_greet")


@test("PromptEntry stores prompt string")
def _() -> None:
    e = PromptEntry(prompt="hello world")
    assert_eq(e.prompt, "hello world")


# ── Tests: prompt builder ─────────────────────────────────────────────────────
print("\n[Prompt builder]")


@test("function selection prompt contains all function names")
def _() -> None:
    p = build_function_selection_prompt("Add 2 and 3", ALL_FNS)
    for fn in ALL_FNS:
        assert_in(fn.name, p, f"missing {fn.name}")
    assert_in("Add 2 and 3", p)


@test("argument extraction prompt contains parameter names")
def _() -> None:
    p = build_argument_extraction_prompt("Add 2 and 3", FN_ADD)
    assert_in("fn_add_numbers", p)
    assert_in("a", p)
    assert_in("b", p)


@test("argument extraction prompt mentions param types")
def _() -> None:
    p = build_argument_extraction_prompt("Greet alice", FN_GREET)
    assert_in("string", p)


# ── Tests: decoder helpers ────────────────────────────────────────────────────
print("\n[Decoder helpers]")


@test("_clean strips Ġ marker")
def _() -> None:
    assert_eq(_clean("Ġhello"), "hello")


@test("_clean strips leading space")
def _() -> None:
    assert_eq(_clean(" world"), "world")


@test("_clean leaves clean token unchanged")
def _() -> None:
    assert_eq(_clean("abc"), "abc")


@test("_coerce_value number -> float")
def _() -> None:
    v = _coerce_value("3.14", "number")
    assert_isinstance(v, float)
    assert_eq(v, 3.14)


@test("_coerce_value boolean true -> True")
def _() -> None:
    assert_eq(_coerce_value("true", "boolean"), True)


@test("_coerce_value boolean false -> False")
def _() -> None:
    assert_eq(_coerce_value("false", "boolean"), False)


@test("_coerce_value string -> str unchanged")
def _() -> None:
    assert_eq(_coerce_value("hello", "string"), "hello")


@test("_coerce_value bad number -> 0.0")
def _() -> None:
    assert_eq(_coerce_value("xyz", "number"), 0.0)


@test("_mask_to_allowed sets non-allowed to -inf")
def _() -> None:
    logits = np.array([1.0, 2.0, 3.0, 4.0])
    allowed = {1, 3}
    masked = _mask_to_allowed(logits, allowed)
    assert_eq(masked[0], -np.inf)
    assert_eq(masked[2], -np.inf)
    assert_eq(masked[1], 2.0)
    assert_eq(masked[3], 4.0)


@test("_mask_to_allowed ignores out-of-range IDs")
def _() -> None:
    logits = np.array([1.0, 2.0])
    allowed = {0, 999}
    masked = _mask_to_allowed(logits, allowed)
    assert_eq(masked[0], 1.0)
    assert_eq(masked[1], -np.inf)


# ── Tests: vocabulary loading ─────────────────────────────────────────────────
print("\n[Vocabulary]")


@test("vocabulary loads from model path")
def _() -> None:
    model = Small_LLM_Model()
    path = model.get_path_to_vocabulary_json()
    id_to_tok, tok_to_id = _load_vocabulary(path)
    assert len(id_to_tok) > 0
    assert len(tok_to_id) > 0


@test("vocabulary is bidirectional")
def _() -> None:
    model = Small_LLM_Model()
    path = model.get_path_to_vocabulary_json()
    id_to_tok, tok_to_id = _load_vocabulary(path)
    for tok, tid in list(tok_to_id.items())[:10]:
        assert_eq(id_to_tok[tid], tok)


# ── Tests: mock model ─────────────────────────────────────────────────────────
print("\n[Mock model]")


@test("encode returns a list of ints")
def _() -> None:
    model = Small_LLM_Model()
    ids = model.encode("hello")
    assert_isinstance(ids, list)
    assert len(ids) > 0
    for i in ids:
        assert_isinstance(i, int)


@test("get_logits shape is (1, seq, vocab)")
def _() -> None:
    model = Small_LLM_Model()
    ids = model.encode("test")
    arr = np.array([ids], dtype=np.int64)
    logits = model.get_logits_from_input_ids(arr)
    assert logits.ndim == 3
    assert_eq(logits.shape[0], 1)


@test("decode inverts encode approximately")
def _() -> None:
    model = Small_LLM_Model()
    text = "fn_add"
    ids = model.encode(text)
    out = model.decode(ids)
    assert_isinstance(out, str)
    assert len(out) > 0


# ── Tests: constrained decoder ────────────────────────────────────────────────
print("\n[Constrained decoder]")


@test("decode_function_name returns a valid candidate")
def _() -> None:
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    prompt = build_function_selection_prompt("Add 2 and 3", ALL_FNS)
    name = decoder.decode_function_name(prompt, ALL_FNS)
    fn_names = [f.name for f in ALL_FNS]
    assert_in(name, fn_names, "result must be a known function name")


@test("decode_function_name never returns empty string")
def _() -> None:
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    for prompt_text in ["Add 2 and 3", "Greet alice", "Is 4 even?"]:
        prompt = build_function_selection_prompt(prompt_text, ALL_FNS)
        name = decoder.decode_function_name(prompt, ALL_FNS)
        assert len(name) > 0, f"empty name for: {prompt_text}"


@test("decode_arguments returns dict with all required keys")
def _() -> None:
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    prompt = build_argument_extraction_prompt("Add 2 and 3", FN_ADD)
    args = decoder.decode_arguments(prompt, FN_ADD)
    assert_isinstance(args, dict)
    assert_in("a", args, "param 'a' missing")
    assert_in("b", args, "param 'b' missing")


@test("decode_arguments number params are float/int")
def _() -> None:
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    prompt = build_argument_extraction_prompt("Add 2 and 3", FN_ADD)
    args = decoder.decode_arguments(prompt, FN_ADD)
    assert_isinstance(args["a"], (int, float), "a must be numeric")
    assert_isinstance(args["b"], (int, float), "b must be numeric")


@test("decode_arguments string params are str")
def _() -> None:
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    prompt = build_argument_extraction_prompt("Greet alice", FN_GREET)
    args = decoder.decode_arguments(prompt, FN_GREET)
    assert_in("name", args)
    assert_isinstance(args["name"], str)


@test("decode_arguments fills missing params with defaults")
def _() -> None:
    # Even if the model produces nothing useful, no KeyError
    model = Small_LLM_Model()
    decoder = ConstrainedDecoder(model)
    prompt = build_argument_extraction_prompt("something", FN_ADD)
    args = decoder.decode_arguments(prompt, FN_ADD)
    assert_in("a", args)
    assert_in("b", args)


# ── Tests: loader (using stdlib only, no pydantic) ────────────────────────────
print("\n[Loader]")


@test("save_results writes valid JSON")
def _() -> None:
    from src.loader import save_results
    results = [
        FunctionCallResult(
            prompt="Add 2 and 3",
            name="fn_add_numbers",
            parameters={"a": 2.0, "b": 3.0},
        )
    ]
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.json")
        from pathlib import Path
        save_results(results, Path(out))
        with open(out) as f:
            data = json.load(f)
    assert_isinstance(data, list)
    assert_eq(len(data), 1)
    assert_eq(data[0]["name"], "fn_add_numbers")
    assert_eq(data[0]["parameters"]["a"], 2.0)


@test("save_results creates parent directories")
def _() -> None:
    from src.loader import save_results
    from pathlib import Path
    results = [
        FunctionCallResult(prompt="p", name="fn_greet", parameters={})
    ]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "nested" / "deep" / "out.json"
        save_results(results, out)
        assert out.exists()


# ── Tests: full pipeline ──────────────────────────────────────────────────────
print("\n[Pipeline]")


@test("pipeline produces one result per prompt")
def _() -> None:
    from src.pipeline import run_pipeline
    model = Small_LLM_Model()
    prompts = [
        PromptEntry(prompt="Add 2 and 3"),
        PromptEntry(prompt="Greet alice"),
    ]
    results = run_pipeline(model, prompts, ALL_FNS)
    assert_eq(len(results), 2)


@test("pipeline results all have valid function names")
def _() -> None:
    from src.pipeline import run_pipeline
    model = Small_LLM_Model()
    prompts = [PromptEntry(prompt=p) for p in [
        "Add 2 and 3", "Greet alice", "Is 4 even?"
    ]]
    results = run_pipeline(model, prompts, ALL_FNS)
    fn_names = {f.name for f in ALL_FNS}
    for r in results:
        assert_in(r.name, fn_names)


@test("pipeline results all have dict parameters")
def _() -> None:
    from src.pipeline import run_pipeline
    model = Small_LLM_Model()
    prompts = [PromptEntry(prompt="Add 2 and 3")]
    results = run_pipeline(model, prompts, ALL_FNS)
    assert_isinstance(results[0].parameters, dict)


@test("pipeline output serialises to valid JSON")
def _() -> None:
    from src.pipeline import run_pipeline
    from src.loader import save_results
    from pathlib import Path
    model = Small_LLM_Model()
    prompts = [PromptEntry(prompt="Add 2 and 3")]
    results = run_pipeline(model, prompts, ALL_FNS)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "results.json"
        save_results(results, out)
        with open(out) as f:
            data = json.load(f)
    assert_isinstance(data, list)
    assert_eq(len(data), 1)
    item = data[0]
    assert_in("prompt", item)
    assert_in("name", item)
    assert_in("parameters", item)


@test("pipeline output has no extra keys")
def _() -> None:
    from src.pipeline import run_pipeline
    from src.loader import save_results
    from pathlib import Path
    model = Small_LLM_Model()
    prompts = [PromptEntry(prompt="Add 2 and 3")]
    results = run_pipeline(model, prompts, ALL_FNS)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "results.json"
        save_results(results, out)
        with open(out) as f:
            data = json.load(f)
    allowed_keys = {"prompt", "name", "parameters"}
    for item in data:
        extra = set(item.keys()) - allowed_keys
        assert len(extra) == 0, f"extra keys in output: {extra}"


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"  {len(PASSED)} passed   {len(FAILED)} failed")
print(f"{'='*55}")
if FAILED:
    print("\nFailed tests:")
    for name, tb in FAILED:
        print(f"\n  FAIL: {name}")
        for line in tb.strip().splitlines():
            print(f"    {line}")
    sys.exit(1)
else:
    print("\n  All tests passed!")
