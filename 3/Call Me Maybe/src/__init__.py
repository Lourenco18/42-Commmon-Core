"""call-me-maybe: function calling via constrained decoding."""

from src.decoder import ConstrainedDecoder
from src.loader import load_function_definitions, load_prompts, save_results
from src.models import FunctionCallResult, FunctionDefinition, PromptEntry
from src.pipeline import run_pipeline
from src.prompt_builder import (
    build_argument_extraction_prompt,
    build_function_selection_prompt,
)

__all__ = [
    "FunctionDefinition",
    "PromptEntry",
    "FunctionCallResult",
    "load_function_definitions",
    "load_prompts",
    "save_results",
    "build_function_selection_prompt",
    "build_argument_extraction_prompt",
    "ConstrainedDecoder",
    "run_pipeline",
]
