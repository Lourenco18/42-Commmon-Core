"""Utilities for loading and validating input JSON files."""

import json
import sys
from pathlib import Path
from typing import List

from pydantic import ValidationError

from src.models import FunctionDefinition, PromptEntry


def load_function_definitions(path: Path) -> List[FunctionDefinition]:
    """Load and validate a list of function definitions from a JSON file.

    Args:
        path: Path to the function definitions JSON file.

    Returns:
        A list of validated FunctionDefinition objects.
    """
    if not path.exists():
        print(
            f"[ERROR] Function definitions file not found: {path}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        print(
            f"[ERROR] Invalid JSON in function definitions file: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as e:
        print(
            f"[ERROR] Cannot read function definitions file: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(raw, list):
        print(
            "[ERROR] Function definitions file must contain a JSON array.",
            file=sys.stderr,
        )
        sys.exit(1)

    definitions: List[FunctionDefinition] = []
    for i, item in enumerate(raw):
        try:
            definitions.append(FunctionDefinition.model_validate(item))
        except ValidationError as e:
            print(
                f"[ERROR] Function definition #{i} is invalid: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

    if not definitions:
        print(
            "[ERROR] Function definitions file is empty.",
            file=sys.stderr,
        )
        sys.exit(1)

    return definitions


def load_prompts(path: Path) -> List[PromptEntry]:
    """Load and validate a list of prompt entries from a JSON file.

    Args:
        path: Path to the prompts JSON file.

    Returns:
        A list of validated PromptEntry objects.
    """
    if not path.exists():
        print(
            f"[ERROR] Input prompts file not found: {path}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        print(
            f"[ERROR] Invalid JSON in input prompts file: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as e:
        print(
            f"[ERROR] Cannot read input prompts file: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(raw, list):
        print(
            "[ERROR] Input prompts file must contain a JSON array.",
            file=sys.stderr,
        )
        sys.exit(1)

    entries: List[PromptEntry] = []
    for i, item in enumerate(raw):
        try:
            entries.append(PromptEntry.model_validate(item))
        except ValidationError as e:
            print(
                f"[WARNING] Prompt entry #{i} is invalid, skipping: {e}",
                file=sys.stderr,
            )

    if not entries:
        print(
            "[ERROR] No valid prompt entries found in input file.",
            file=sys.stderr,
        )
        sys.exit(1)

    return entries


def save_results(  # type: ignore[type-arg]
    results: list,
    path: Path,
) -> None:
    """Serialize and write function call results to a JSON output file.

    Args:
        results: List of FunctionCallResult objects.
        path: Destination path for the output JSON file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    output = [r.model_dump() for r in results]
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Results written to {path}")
    except OSError as e:
        print(f"[ERROR] Cannot write output file: {e}", file=sys.stderr)
        sys.exit(1)
