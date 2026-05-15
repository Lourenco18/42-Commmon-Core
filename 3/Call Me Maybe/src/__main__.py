import argparse
import importlib
import os
import sys
from typing import Any, List, Optional

from src.models import CLIArgs, FunctionCallResult
from src.file_io import load_function_definitions, load_prompts, save_results
from src.vocabulary import Vocabulary
from src.function_selector import select_function_and_extract_args


def _patch_sdk_path() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidates = [
        project_root,
        os.path.join(project_root, "llm_sdk"),
    ]

    for path in candidates:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


_patch_sdk_path()


def parse_args() -> CLIArgs:
    parser = argparse.ArgumentParser(
        description="call me maybe - LLM function calling with"
        "constrained decoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python -m src\n"
            "  uv run python -m src --functions_definition"
            "data/input/functions_definition.json"
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


def load_llm_sdk() -> Optional[Any]:
    try:
        llm_module = importlib.import_module("llm_sdk")
        Small_LLM_Model = getattr(llm_module, "Small_LLM_Model")
        print("[INFO] Loading LLM model (Qwen/Qwen3-0.6B) -"
              "this may take a moment...")
        model = Small_LLM_Model()
        print("[INFO] LLM model loaded successfully.")
        return model
    except ImportError as exc:
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(current_file))
        searched = "\n".join(f"    {p}" for p in sys.path[:8])
        print(
            f"[ERROR] Could not import 'llm_sdk': {exc}\n"
            f"  Paths searched:\n{searched}\n"
            f"  Place the llm_sdk folder directly inside: {project_root}",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(f"[ERROR] Failed to initialise LLM model: {exc}",
              file=sys.stderr)
        return None


def run(args: CLIArgs) -> int:
    # 1. Load function definitions
    functions = load_function_definitions(args.functions_definition)
    if functions is None:
        return 1

    # 2. Load input prompts
    prompts = load_prompts(args.input)
    if prompts is None:
        return 1

    # 3. Load the LLM SDK
    model: Any = load_llm_sdk()
    if model is None:
        return 1

    # 4. Load vocabulary from the tokenizer file (full vocab)
    #    or vocab file (BPE)
    vocab: Optional[Vocabulary] = None
    for method_name in (
        "get_path_to_tokenizer_file",
        "get_path_to_vocab_file",
    ):
        try:
            method = getattr(model, method_name)
            vocab_path = method()
            vocab = Vocabulary.from_json_path(vocab_path)
            if vocab and vocab.vocab_size > 0:
                break
            vocab = None
        except Exception as exc:
            print(f"[WARNING] {method_name}() failed: {exc}", file=sys.stderr)

    if vocab is None:
        print(
            "[ERROR] Could not load vocabulary from LLM SDK.",
            file=sys.stderr,
        )
        return 1

    # 5. Process each prompt with constrained decoding
    results: List[FunctionCallResult] = []
    total = len(prompts)

    for idx, entry in enumerate(prompts, start=1):
        prompt_text = entry.prompt
        prompt_preview = prompt_text[:60]
        print(f"[INFO] Processing prompt {idx}/{total}: '{prompt_preview}'...")

        try:
            fn_name, arguments = select_function_and_extract_args(
                user_prompt=prompt_text,
                functions=functions,
                vocab=vocab,
                get_logits_fn=model.get_logits_from_input_ids,
                encode_fn=model.encode,
            )
        except Exception as exc:
            prompt_preview = prompt_text[:40]
            print(
                f"[ERROR] Unexpected error processing prompt '"
                f"{prompt_preview}': {exc}", file=sys.stderr,)
            fn_name = None
            arguments = None

        if fn_name is None:
            prompt_preview = prompt_text[:60]
            print(
                f"[WARNING] Could not determine function for: "
                f"'{prompt_preview}'",
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
        print(
            "[ERROR] No results were generated. "
            "Check input files and model.",
            file=sys.stderr,
        )
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
