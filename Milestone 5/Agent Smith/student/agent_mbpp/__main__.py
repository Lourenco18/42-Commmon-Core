"""MBPP agent CLI (Section V.3 point 1).

    uv run python -m agent_mbpp --task-file ../cache/mbpp_task.json \\
        --output ../cache/mbpp_solution.json \\
        --model-name "model/name" --provider-url "https://provider.api/v1"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `import agent_core`, `import sandbox`

from agent_core.llm_provider import DummyProvider, provider_from_env
from agent_core.models import MBPPTaskInput
from agent_core.orchestrator import Orchestrator, OrchestratorLimits
from agent_core.prompts import build_system_prompt
from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor
from sandbox.manual import build_manual
from sandbox.mcp_client import MCPClient

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_TOOLS_SCRIPT = REPO_ROOT / "mcp_tools_mbpp.py"

# Hard limits from Section VI.1.1
MAX_ITERATIONS = 10
MAX_INPUT_TOKENS = 6000
MAX_OUTPUT_TOKENS = 1500
TIMEOUT_SECONDS = 120


def build_task_description(task: MBPPTaskInput) -> str:
    return (
        f"MBPP task #{task.task_id}\n\n"
        f"{task.task_definition}\n\n"
        f"Function signature to implement:\n{task.function_definition}\n\n"
        f"Test imports: {task.test_imports}\n"
        f"Your candidate solution will be checked with `run_tests(code, test_list)` "
        f"using these tests:\n" + "\n".join(task.test_list) + "\n\n"
        "When your candidate solution passes run_tests, call "
        "final_answer(your_full_function_source_code)."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agent_mbpp")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", default="")
    parser.add_argument("--provider-url", default="")
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    parser.add_argument("--dummy-script", default=None,
                         help="Path to a JSON list of canned LLM responses (offline testing, no API key needed)")
    args = parser.parse_args(argv)

    task = MBPPTaskInput(**json.loads(Path(args.task_file).read_text()))

    mcp_client = MCPClient(stdio_command=f"{sys.executable} {MCP_TOOLS_SCRIPT}")
    sandbox_config = SandboxConfig()
    executor = SandboxExecutor(config=sandbox_config, mcp_client=mcp_client)

    manual = build_manual(sandbox_config, mcp_client)
    system_prompt = build_system_prompt(build_task_description(task), manual)

    if args.dummy_script:
        script = json.loads(Path(args.dummy_script).read_text())
        provider = DummyProvider(script)
    else:
        provider = provider_from_env(args.provider_url, args.model_name, args.api_key_env)

    limits = OrchestratorLimits(
        max_iterations=args.max_iterations,
        max_input_tokens=MAX_INPUT_TOKENS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        max_time_seconds=TIMEOUT_SECONDS,
    )
    orchestrator = Orchestrator(
        provider=provider, executor=executor, system_prompt=system_prompt,
        task_id=str(task.task_id), benchmark="mbpp", limits=limits,
    )

    try:
        solution = orchestrator.run()
    finally:
        executor.shutdown()
        mcp_client.close()
        provider.close()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(solution.model_dump_json(indent=2))
    print(f"Wrote {args.output} (success={solution.success}, iterations={solution.iterations})")
    return 0 if solution.success else 1


if __name__ == "__main__":
    sys.exit(main())
