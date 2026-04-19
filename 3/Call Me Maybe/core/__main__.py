import argparse
import sys
from pathlib import Path

from src.loader import load_function_definitions, load_prompts, save_results
from src.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Translate natural language prompts into "
            "structured function calls."
        )
    )
    parser.add_argument(
        "--functions_definition",
        type=Path,
        default=Path("data/input/functions_definition.json"),
        help="Path to the JSON file defining available functions.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/input/function_calling_tests.json"),
        help="Path to the JSON file containing prompts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/output/function_calling_results.json"),
        help="Path for the output JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point: load inputs, run pipeline, save results."""
    args = parse_args()

    print("[INFO] Loading function definitions...", file=sys.stderr)
    functions = load_function_definitions(args.functions_definition)
    print(
        f"[INFO] Loaded {len(functions)} function(s).",
        file=sys.stderr,
    )

    print("[INFO] Loading prompts...", file=sys.stderr)
    prompts = load_prompts(args.input)
    print(f"[INFO] Loaded {len(prompts)} prompt(s).", file=sys.stderr)

    print("[INFO] Loading LLM model...", file=sys.stderr)
    try:
        from llm_sdk import Small_LLM_Model  # type: ignore[import]
        model = Small_LLM_Model()
    except ImportError:
        print(
            "[ERROR] llm_sdk not found. "
            "Copy llm_sdk/ into the project root.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to load LLM model: {e}", file=sys.stderr)
        sys.exit(1)

    print("[INFO] Running pipeline...", file=sys.stderr)
    results = run_pipeline(model, prompts, functions)

    save_results(results, args.output)
    print(
        f"[INFO] Done. {len(results)} result(s) written to {args.output}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
