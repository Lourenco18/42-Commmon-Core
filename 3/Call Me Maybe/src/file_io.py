"""File I/O utilities for reading and writing JSON files.

This module handles all file operations including reading function definitions,
input prompts, and writing output results. All errors are handled gracefully.
"""

import json
import os
import sys
from typing import List, Optional

from src.models import (
    FunctionDefinition,
    FunctionCallResult,
    PromptEntry,
)


def load_function_definitions(path: str) -> Optional[List[FunctionDefinition]]:
    """Load and validate function definitions from a JSON file.

    Args:
        path: Path to the functions_definition.json file.

    Returns:
        A list of FunctionDefinition objects, or None if loading fails.
    """
    if not os.path.exists(path):
        print(f"[ERROR] Functions definition file not found: '{path}'", file=sys.stderr)
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in '{path}': {e}", file=sys.stderr)
        return None
    except OSError as e:
        print(f"[ERROR] Could not read '{path}': {e}", file=sys.stderr)
        return None

    if not isinstance(raw, list):
        print(
            f"[ERROR] '{path}' must contain a JSON array of function definitions.",
            file=sys.stderr
        )
        return None

    definitions: List[FunctionDefinition] = []
    for i, item in enumerate(raw):
        try:
            definitions.append(FunctionDefinition.model_validate(item))
        except Exception as e:
            print(
                f"[WARNING] Skipping invalid function definition at index {i}: {e}",
                file=sys.stderr
            )

    if not definitions:
        print("[ERROR] No valid function definitions found.", file=sys.stderr)
        return None

    print(f"[INFO] Loaded {len(definitions)} function definition(s) from '{path}'.")
    return definitions


def load_prompts(path: str) -> Optional[List[PromptEntry]]:
    """Load and validate prompt entries from a JSON file.

    Args:
        path: Path to the function_calling_tests.json file.

    Returns:
        A list of PromptEntry objects, or None if loading fails.
    """
    if not os.path.exists(path):
        print(f"[ERROR] Input file not found: '{path}'", file=sys.stderr)
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in '{path}': {e}", file=sys.stderr)
        return None
    except OSError as e:
        print(f"[ERROR] Could not read '{path}': {e}", file=sys.stderr)
        return None

    if not isinstance(raw, list):
        print(
            f"[ERROR] '{path}' must contain a JSON array of prompt objects.",
            file=sys.stderr
        )
        return None

    prompts: List[PromptEntry] = []
    for i, item in enumerate(raw):
        try:
            prompts.append(PromptEntry.model_validate(item))
        except Exception as e:
            print(
                f"[WARNING] Skipping invalid prompt entry at index {i}: {e}",
                file=sys.stderr
            )

    if not prompts:
        print("[ERROR] No valid prompt entries found.", file=sys.stderr)
        return None

    print(f"[INFO] Loaded {len(prompts)} prompt(s) from '{path}'.")
    return prompts


def save_results(results: List[FunctionCallResult], path: str) -> bool:
    """Save function call results to a JSON output file.

    Args:
        results: List of FunctionCallResult objects to serialize.
        path: Path where the output JSON file will be written.

    Returns:
        True if saving succeeded, False otherwise.
    """
    output_dir = os.path.dirname(path)
    if output_dir:
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(f"[ERROR] Could not create output directory '{output_dir}': {e}", file=sys.stderr)
            return False

    serializable = [r.model_dump() for r in results]

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[ERROR] Could not write output to '{path}': {e}", file=sys.stderr)
        return False

    print(f"[INFO] Saved {len(results)} result(s) to '{path}'.")
    return True
