"""Builds text prompts for the LLM to facilitate function calling."""

from typing import List

from src.models import FunctionDefinition


def build_function_selection_prompt(
    user_prompt: str,
    functions: List[FunctionDefinition],
) -> str:
    lines = [
        "You are a function calling assistant.",
        "Given the user request, output only the exact function name.",
        "",
        "Available functions:",
    ]
    for fn in functions:
        param_desc = ", ".join(
            f"{name}: {pdef.type}"
            for name, pdef in fn.parameters.items()
        )
        lines.append(f"  - {fn.name}({param_desc}): {fn.description}")

    lines += [
        "",
        f'User request: "{user_prompt}"',
        "",
        "Function name to call: ",
    ]
    return "\n".join(lines)


def build_argument_extraction_prompt(
    user_prompt: str,
    function: FunctionDefinition,
) -> str:
    param_schema = ", ".join(
        f'"{name}": <{pdef.type}>'
        for name, pdef in function.parameters.items()
    )

    lines = [
        "You are a function argument extractor.",
        (
            f'Extract the arguments for function "{function.name}"'
            f" from the user request."
        ),
        f"Function description: {function.description}",
        "",
        "Parameters:",
    ]
    for name, pdef in function.parameters.items():
        lines.append(f"  - {name} ({pdef.type})")

    lines += [
        "",
        f'User request: "{user_prompt}"',
        "",
        f"Output only the JSON arguments: {{{param_schema}}}",
        "",
        "Arguments: ",
    ]
    return "\n".join(lines)
