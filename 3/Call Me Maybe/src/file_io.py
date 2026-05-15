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
    if not os.path.exists(path):
        print(
            f"[ERROR] Functions definition file not found: '{path}'",
            file=sys.stderr,
        )
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
            f"[ERROR] '{path}' must contain a JSON array of"
            f" function definitions.",
            file=sys.stderr,
        )
        return None

    definitions: List[FunctionDefinition] = []
    for i, item in enumerate(raw):
        try:
            definitions.append(FunctionDefinition.model_validate(item))
        except Exception as e:
            print(
                f"[WARNING] Skipping invalid function definition at index {i}:"
                f" {e}",
                file=sys.stderr,
            )

    if not definitions:
        print("[ERROR] No valid function definitions found.", file=sys.stderr)
        return None

    print(
        f"[INFO] Loaded {len(definitions)} function definition(s)"
        f" from '{path}'."
    )
    return definitions


def load_prompts(path: str) -> Optional[List[PromptEntry]]:
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
    output_dir = os.path.dirname(path)
    if output_dir:
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            print(
                "[ERROR] Could not create output directory '",
                f"{output_dir}': {e}",
                file=sys.stderr,
            )

    serializable = [r.model_dump() for r in results]

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(
            "[ERROR] Could not create output directory '",
            f"{output_dir}': {e}",
            file=sys.stderr,
        )
        return False

    print(f"[INFO] Saved {len(results)} result(s) to '{path}'.")
    return True
