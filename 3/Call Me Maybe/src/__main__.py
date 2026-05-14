"""Main entry point for the call me maybe function calling system.

Run with: uv run python -m src [--functions_definition <path>] [--input <path>] [--output <path>]

This module orchestrates:
1. Parsing CLI arguments
2. Loading the LLM SDK and model
3. Loading input files
4. Running constrained decoding for each prompt
5. Writing results to the output file
"""

import argparse
import os
import sys
from typing import List, Optional

from src.models import CLIArgs, FunctionCallResult
from src.file_io import load_function_definitions, load_prompts, save_results
from src.vocabulary import Vocabulary
from src.function_selector import select_function_and_extract_args


def _patch_sdk_path() -> None:
    """Add all candidate llm_sdk locations to sys.path.

    The SDK may be placed in two ways relative to the project root:
      1. <root>/llm_sdk/          — the inner package is directly importable
      2. <root>/llm_sdk/llm_sdk/  — school-provided nested layout (seen in screenshot)

    We add both the project root AND the llm_sdk/ subdirectory to sys.path
    so that 'import llm_sdk' resolves in either case.
    """
    # Project root = parent of the 'src' directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidates = [
        project_root,                              # handles case 1
        os.path.join(project_root, "llm_sdk"),     # handles case 2 (nested)
    ]

    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


# Patch the path before any llm_sdk import attempt
_patch_sdk_path()


def parse_args() -> CLIArgs:
    """Parse and validate command-line arguments.

    Returns:
        A CLIArgs pydantic model with the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="call me maybe - LLM function calling with constrained decoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python -m src\n"
            "  uv run python -m src --functions_definition data/input/functions_definition.json"
            " --input data/input/function_calling_tests.json"
            " --output data/output/function_calling_results.json\n"
        ),
    )
    parser.add_argument(
        "--functions_definition",
        type=str,
        default="data/input/functions_definition.json",
        help="Path to the JSON file containing function definitions.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/input/function_calling_tests.json",
        help="Path to the JSON file containing input prompts.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/output/function_calling_results.json",
        help="Path to write the output JSON results.",
    )

    parsed = parser.parse_args()
    try:
        return CLIArgs(
            functions_definition=parsed.functions_definition,
            input=parsed.input,
            output=parsed.output,
        )
    except Exception as e:
        print(f"[ERROR] Invalid arguments: {e}", file=sys.stderr)
        sys.exit(1)


def load_llm_sdk() -> Optional[object]:
    """Attempt to import and initialise the LLM SDK.

    _patch_sdk_path() has already inserted both the project root and the
    llm_sdk/ subdirectory into sys.path, so 'import llm_sdk' resolves
    whether the package lives at:
      - <root>/llm_sdk/          (direct layout)
      - <root>/llm_sdk/llm_sdk/  (nested layout shipped by the school)

    Returns:
        An initialised Small_LLM_Model instance, or None on failure.
    """
    try:
        from llm_sdk import Small_LLM_Model  # type: ignore
        print("[INFO] Loading LLM model (Qwen/Qwen3-0.6B) - this may take a moment...")
        model = Small_LLM_Model()
        print("[INFO] LLM model loaded successfully.")
        return model
    except ImportError as exc:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        searched = "\n".join(f"    {p}" for p in sys.path[:8])
        print(
            f"[ERROR] Could not import 'llm_sdk': {exc}\n"
            f"  Paths searched:\n{searched}\n"
            f"  Place the llm_sdk folder directly inside: {project_root}",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(f"[ERROR] Failed to initialise LLM model: {exc}", file=sys.stderr)
        return None


def run(args: CLIArgs) -> int:
    """Execute the full function calling pipeline.

    Args:
        args: Validated CLI arguments.

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    # 1. Load function definitions
    functions = load_function_definitions(args.functions_definition)
    if functions is None:
        return 1

    # 2. Load input prompts
    prompts = load_prompts(args.input)
    if prompts is None:
        return 1

    # 3. Load the LLM SDK
    model = load_llm_sdk()
    if model is None:
        return 1

    # 4. Load vocabulary
    try:
        vocab_path = model.get_path_to_vocabulary_json()  # type: ignore[union-attr]
    except Exception as exc:
        print(f"[ERROR] Could not get vocabulary path from LLM SDK: {exc}", file=sys.stderr)
        return 1

    vocab = Vocabulary.from_json_path(vocab_path)
    if vocab is None:
        return 1

    # 5. Process each prompt with constrained decoding
    results: List[FunctionCallResult] = []
    total = len(prompts)

    for idx, entry in enumerate(prompts, start=1):
        prompt_text = entry.prompt
        print(f"[INFO] Processing prompt {idx}/{total}: '{prompt_text[:60]}'...")

        try:
            fn_name, arguments = select_function_and_extract_args(
                user_prompt=prompt_text,
                functions=functions,
                vocab=vocab,
                get_logits_fn=model.get_logits_from_input_ids,  # type: ignore[union-attr]
                encode_fn=model.encode,  # type: ignore[union-attr]
            )
        except Exception as exc:
            print(
                f"[ERROR] Unexpected error processing prompt '{prompt_text[:40]}': {exc}",
                file=sys.stderr,
            )
            fn_name = None
            arguments = None

        if fn_name is None:
            print(
                f"[WARNING] Could not determine function for: '{prompt_text[:60]}'",
                file=sys.stderr,
            )
            continue

        if arguments is None:
            print(
                f"[WARNING] Could not extract arguments for '{fn_name}' "
                f"from: '{prompt_text[:60]}'",
                file=sys.stderr,
            )
            arguments = {}

        result = FunctionCallResult(
            prompt=prompt_text,
            name=fn_name,
            parameters=arguments,
        )
        results.append(result)
        print(f"[INFO] -> {fn_name}({arguments})")

    if not results:
        print("[ERROR] No results were generated. Check input files and model.",
              file=sys.stderr)
        return 1

    # 6. Save results
    success = save_results(results, args.output)
    if not success:
        return 1

    print(f"\n[DONE] Processed {len(results)}/{total} prompt(s) successfully.")
    return 0


def main() -> None:
    """CLI entry point - parse args and run the pipeline."""
    args = parse_args()
    exit_code = run(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
