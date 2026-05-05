"""Main processing pipeline for function calling."""

import sys
from typing import Any, List

from src.decoder import ConstrainedDecoder
from src.models import FunctionCallResult, FunctionDefinition, PromptEntry
from src.prompt_builder import (
    build_argument_extraction_prompt,
    build_function_selection_prompt,
)


def run_pipeline(
    model: Any,
    prompts: List[PromptEntry],
    functions: List[FunctionDefinition],
) -> List[FunctionCallResult]:
    """Run the full function calling pipeline over all prompts.

    For each prompt:
    1. Build a function-selection prompt and use constrained decoding
       to pick the best matching function name.
    2. Build an argument-extraction prompt and use constrained decoding
       to generate schema-valid JSON arguments.
    3. Package the result as a FunctionCallResult.

    Args:
        model: The Small_LLM_Model instance from llm_sdk.
        prompts: List of natural-language prompt entries.
        functions: List of available function definitions.

    Returns:
        List of FunctionCallResult objects ready for JSON serialisation.
    """
    decoder = ConstrainedDecoder(model)
    results: List[FunctionCallResult] = []
    total = len(prompts)

    for i, entry in enumerate(prompts, 1):
        print(
            f"[INFO] Processing {i}/{total}: {entry.prompt[:60]}",
            file=sys.stderr,
        )
        try:
            fn_prompt = build_function_selection_prompt(
                entry.prompt, functions
            )
            fn_name = decoder.decode_function_name(fn_prompt, functions)
            print(
                f"[INFO]   -> selected: {fn_name}",
                file=sys.stderr,
            )

            fn_def = next(
                (f for f in functions if f.name == fn_name), None
            )
            if fn_def is None:
                fn_def = functions[0]
                print(
                    f"[WARNING] {fn_name!r} not found, "
                    f"falling back to {fn_def.name!r}",
                    file=sys.stderr,
                )

            arg_prompt = build_argument_extraction_prompt(
                entry.prompt, fn_def
            )
            arguments = decoder.decode_arguments(arg_prompt, fn_def)
            print(
                f"[INFO]   -> arguments: {arguments}",
                file=sys.stderr,
            )

            results.append(
                FunctionCallResult(
                    prompt=entry.prompt,
                    name=fn_def.name,
                    parameters=arguments,
                )
            )
        except Exception as e:
            print(
                f"[ERROR] Failed to process prompt {i}: {e}",
                file=sys.stderr,
            )
            results.append(
                FunctionCallResult(
                    prompt=entry.prompt,
                    name=functions[0].name if functions else "unknown",
                    parameters={},
                )
            )

    return results
