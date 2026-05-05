"""Tests for call-me-maybe components."""

import json
import tempfile
from pathlib import Path

import pytest

from src.loader import load_function_definitions, load_prompts
from src.models import FunctionCallResult, FunctionDefinition, PromptEntry
from src.prompt_builder import (
    build_argument_extraction_prompt,
    build_function_selection_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FUNCTIONS = [
    {
        "name": "fn_add_numbers",
        "description": "Add two numbers.",
        "parameters": {"a": {"type": "number"}, "b": {"type": "number"}},
        "returns": {"type": "number"},
    },
    {
        "name": "fn_greet",
        "description": "Greet a person.",
        "parameters": {"name": {"type": "string"}},
        "returns": {"type": "string"},
    },
]

SAMPLE_PROMPTS = [
    {"prompt": "What is the sum of 2 and 3?"},
    {"prompt": "Greet alice"},
]


@pytest.fixture
def functions_file(tmp_path: Path) -> Path:
    """Write sample function definitions to a temp file."""
    p = tmp_path / "functions.json"
    p.write_text(json.dumps(SAMPLE_FUNCTIONS))
    return p


@pytest.fixture
def prompts_file(tmp_path: Path) -> Path:
    """Write sample prompts to a temp file."""
    p = tmp_path / "prompts.json"
    p.write_text(json.dumps(SAMPLE_PROMPTS))
    return p


@pytest.fixture
def fn_defs() -> list:
    """Return parsed FunctionDefinition objects."""
    return [FunctionDefinition.model_validate(f) for f in SAMPLE_FUNCTIONS]


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------

class TestModels:
    """Tests for pydantic model validation."""

    def test_function_definition_valid(self) -> None:
        """A well-formed function definition validates correctly."""
        fn = FunctionDefinition.model_validate(SAMPLE_FUNCTIONS[0])
        assert fn.name == "fn_add_numbers"
        assert "a" in fn.parameters
        assert fn.parameters["a"].type == "number"

    def test_function_definition_invalid_type(self) -> None:
        """An unknown parameter type should raise ValidationError."""
        from pydantic import ValidationError
        bad = dict(SAMPLE_FUNCTIONS[0])
        bad["parameters"] = {"a": {"type": "unicorn"}}
        with pytest.raises(ValidationError):
            FunctionDefinition.model_validate(bad)

    def test_prompt_entry_valid(self) -> None:
        """A prompt entry with a string prompt validates."""
        entry = PromptEntry.model_validate({"prompt": "hello"})
        assert entry.prompt == "hello"

    def test_function_call_result(self) -> None:
        """FunctionCallResult serialises to the expected dict shape."""
        r = FunctionCallResult(
            prompt="test", name="fn_greet", parameters={"name": "alice"}
        )
        d = r.model_dump()
        assert d["prompt"] == "test"
        assert d["name"] == "fn_greet"
        assert d["parameters"]["name"] == "alice"


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------

class TestLoader:
    """Tests for JSON file loading utilities."""

    def test_load_function_definitions(self, functions_file: Path) -> None:
        """Valid JSON file loads correctly."""
        fns = load_function_definitions(functions_file)
        assert len(fns) == 2
        assert fns[0].name == "fn_add_numbers"

    def test_load_prompts(self, prompts_file: Path) -> None:
        """Valid prompts file loads correctly."""
        entries = load_prompts(prompts_file)
        assert len(entries) == 2
        assert entries[0].prompt == "What is the sum of 2 and 3?"

    def test_load_missing_file_exits(self, tmp_path: Path) -> None:
        """Missing file causes SystemExit."""
        with pytest.raises(SystemExit):
            load_function_definitions(tmp_path / "nonexistent.json")

    def test_load_invalid_json_exits(self, tmp_path: Path) -> None:
        """Invalid JSON causes SystemExit."""
        bad = tmp_path / "bad.json"
        bad.write_text("{ this is not json }")
        with pytest.raises(SystemExit):
            load_function_definitions(bad)

    def test_load_non_array_exits(self, tmp_path: Path) -> None:
        """Non-array JSON root causes SystemExit."""
        bad = tmp_path / "bad.json"
        bad.write_text('{"key": "value"}')
        with pytest.raises(SystemExit):
            load_function_definitions(bad)


# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    """Tests for prompt construction functions."""

    def test_function_selection_prompt_contains_all_names(
        self, fn_defs: list
    ) -> None:
        """All function names appear in the selection prompt."""
        prompt = build_function_selection_prompt("Add 2 and 3", fn_defs)
        assert "fn_add_numbers" in prompt
        assert "fn_greet" in prompt
        assert "Add 2 and 3" in prompt

    def test_argument_extraction_prompt_contains_params(
        self, fn_defs: list
    ) -> None:
        """Parameter names appear in the argument extraction prompt."""
        fn = fn_defs[0]  # fn_add_numbers
        prompt = build_argument_extraction_prompt("Add 2 and 3", fn)
        assert "fn_add_numbers" in prompt
        assert '"a"' in prompt or "a" in prompt
        assert '"b"' in prompt or "b" in prompt


# ---------------------------------------------------------------------------
# Decoder smoke tests (using mock model)
# ---------------------------------------------------------------------------

class TestDecoder:
    """Smoke tests for the constrained decoder using the mock LLM."""

    def test_decode_function_name_returns_valid_name(
        self, fn_defs: list
    ) -> None:
        """Constrained decoding returns a name from the candidate list."""
        from llm_sdk import Small_LLM_Model
        from src.decoder import ConstrainedDecoder

        model = Small_LLM_Model()
        decoder = ConstrainedDecoder(model)
        prompt = build_function_selection_prompt("Add 2 and 3", fn_defs)
        name = decoder.decode_function_name(prompt, fn_defs)
        fn_names = [f.name for f in fn_defs]
        assert name in fn_names, f"Got unexpected name: {name!r}"

    def test_decode_arguments_returns_dict(self, fn_defs: list) -> None:
        """Argument decoding always returns a dictionary."""
        from llm_sdk import Small_LLM_Model
        from src.decoder import ConstrainedDecoder

        model = Small_LLM_Model()
        decoder = ConstrainedDecoder(model)
        fn = fn_defs[0]  # fn_add_numbers with params a, b
        prompt = build_argument_extraction_prompt("Add 2 and 3", fn)
        args = decoder.decode_arguments(prompt, fn)
        assert isinstance(args, dict)
        # Both required parameters must be present
        assert "a" in args
        assert "b" in args

    def test_decode_arguments_types(self, fn_defs: list) -> None:
        """Number parameters are returned as float/int, not strings."""
        from llm_sdk import Small_LLM_Model
        from src.decoder import ConstrainedDecoder

        model = Small_LLM_Model()
        decoder = ConstrainedDecoder(model)
        fn = fn_defs[0]  # fn_add_numbers
        prompt = build_argument_extraction_prompt("Add 2 and 3", fn)
        args = decoder.decode_arguments(prompt, fn)
        assert isinstance(args["a"], (int, float))
        assert isinstance(args["b"], (int, float))

    def test_decode_string_argument(self, fn_defs: list) -> None:
        """String parameters are returned as str."""
        from llm_sdk import Small_LLM_Model
        from src.decoder import ConstrainedDecoder

        model = Small_LLM_Model()
        decoder = ConstrainedDecoder(model)
        fn = fn_defs[1]  # fn_greet with param name: string
        prompt = build_argument_extraction_prompt("Greet alice", fn)
        args = decoder.decode_arguments(prompt, fn)
        assert isinstance(args["name"], str)


# ---------------------------------------------------------------------------
# Pipeline integration test
# ---------------------------------------------------------------------------

class TestPipeline:
    """Integration tests for the full pipeline."""

    def test_pipeline_produces_results(self, fn_defs: list) -> None:
        """Pipeline returns one result per prompt."""
        from llm_sdk import Small_LLM_Model
        from src.pipeline import run_pipeline

        model = Small_LLM_Model()
        entries = [PromptEntry(prompt=p["prompt"]) for p in SAMPLE_PROMPTS]
        results = run_pipeline(model, entries, fn_defs)
        assert len(results) == len(entries)

    def test_pipeline_results_are_valid(self, fn_defs: list) -> None:
        """All pipeline results have valid name and parameters."""
        from llm_sdk import Small_LLM_Model
        from src.pipeline import run_pipeline

        model = Small_LLM_Model()
        entries = [PromptEntry(prompt=p["prompt"]) for p in SAMPLE_PROMPTS]
        fn_names = [f.name for f in fn_defs]
        results = run_pipeline(model, entries, fn_defs)
        for r in results:
            assert r.name in fn_names
            assert isinstance(r.parameters, dict)

    def test_pipeline_output_is_valid_json(
        self, fn_defs: list, tmp_path: Path
    ) -> None:
        """Pipeline output serialises to valid, parseable JSON."""
        from llm_sdk import Small_LLM_Model
        from src.loader import save_results
        from src.pipeline import run_pipeline

        model = Small_LLM_Model()
        entries = [PromptEntry(prompt=p["prompt"]) for p in SAMPLE_PROMPTS]
        results = run_pipeline(model, entries, fn_defs)
        out = tmp_path / "output.json"
        save_results(results, out)
        with open(out) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(entries)
        for item in data:
            assert "prompt" in item
            assert "name" in item
            assert "parameters" in item
