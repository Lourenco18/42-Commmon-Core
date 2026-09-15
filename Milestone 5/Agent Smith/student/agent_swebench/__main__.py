"""SWE-bench agent CLI (Section V.4).

    uv run python -m agent_swebench --task-file ../cache/swebench_task.json \\
        --output ../cache/swebench_solution.json \\
        --model-name "model/name" --provider-url "https://provider.api/v1"

Two ways to provision the "testbed" the MCP tools operate on:

  1. Real evaluation: `docker_image` from the task is pulled and started, and
     `mcp_tools_swebench.py` is executed *inside* the container via
     `docker exec -i <container> python3 mcp_tools_swebench.py` (stdio transport),
     so file/test/git access all happen inside the Dockerized repo, per
     "(a) deploy the sandbox inside the Docker container" (Section V.4).
     This requires a working `docker` daemon and network access to pull the
     image -- both intentionally unavailable in the authoring/test sandbox
     used to build this project (see README "Known Limitations").

  2. `--testbed-path <dir>`: skip Docker entirely and point the MCP server at
     an existing local git checkout via TESTBED_PATH. This is what `make test`
     uses (see student/tests) to exercise the real orchestrator/sandbox/MCP
     code paths end-to-end without Docker or a live LLM key.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core.llm_provider import DummyProvider, provider_from_env
from agent_core.models import SWEBenchTaskInput
from agent_core.orchestrator import Orchestrator, OrchestratorLimits
from agent_core.prompts import build_system_prompt
from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor
from sandbox.manual import build_manual
from sandbox.mcp_client import MCPClient

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_TOOLS_SCRIPT = REPO_ROOT / "mcp_tools_swebench.py"

# Hard limits from Section VI.1.2
MAX_ITERATIONS = 30
MAX_INPUT_TOKENS = 300_000
MAX_OUTPUT_TOKENS = 10_000
TIMEOUT_SECONDS = 900


def build_task_description(task: SWEBenchTaskInput) -> str:
    hints = f"\nHints:\n{task.hints_text}\n" if task.hints_text else ""
    return (
        f"SWE-bench instance: {task.instance_id}\n"
        f"Repository: {task.repo}\n\n"
        f"Problem statement:\n{task.problem_statement}\n{hints}\n"
        "Explore the repository with search_code / search_function_or_class_definition_in_code / "
        "read_file, make your fix with edit_file, verify with run_tests(), and once satisfied "
        "call final_answer(get_patch())."
    )


class DockerTestbed:
    """Provisions (and cleans up) a Docker container as the SWE-bench testbed."""

    def __init__(self, task: SWEBenchTaskInput):
        self.task = task
        self.container_name = f"agent-smith-{task.instance_id}".replace("/", "_")

    def __enter__(self) -> str:
        if shutil.which("docker") is None:
            raise RuntimeError(
                "docker is not available in this environment. Use --testbed-path for local/dev runs."
            )
        subprocess.run(["docker", "rm", "-f", self.container_name],
                        capture_output=True)  # best-effort cleanup of stale containers
        subprocess.run(
            ["docker", "run", "-d", "--name", self.container_name, "--network", "none",
             self.task.docker_image, "sleep", str(TIMEOUT_SECONDS + 60)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(["docker", "cp", str(MCP_TOOLS_SCRIPT), f"{self.container_name}:/mcp_tools_swebench.py"],
                        check=True, capture_output=True, text=True)
        return (f"docker exec -i "
                f"-e TESTBED_PATH=/testbed -e EVAL_SCRIPT={json_quote(self.task.eval_script)} "
                f"{self.container_name} python3 /mcp_tools_swebench.py")

    def __exit__(self, exc_type, exc, tb):
        # "you are responsible to clean it after your program execution" (Section V.4)
        subprocess.run(["docker", "rm", "-f", self.container_name], capture_output=True)


def json_quote(s: str) -> str:
    return json.dumps(s)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agent_swebench")
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-name", default="")
    parser.add_argument("--provider-url", default="")
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    parser.add_argument("--testbed-path", default=None,
                         help="Skip Docker; use this local git checkout as TESTBED_PATH (dev/testing mode)")
    parser.add_argument("--dummy-script", default=None,
                         help="Path to a JSON list of canned LLM responses (offline testing, no API key needed)")
    args = parser.parse_args(argv)

    task = SWEBenchTaskInput(**json.loads(Path(args.task_file).read_text()))

    docker_ctx = None
    if args.testbed_path:
        mcp_env = dict(os.environ)
        mcp_env["TESTBED_PATH"] = str(Path(args.testbed_path).resolve())
        mcp_env["EVAL_SCRIPT"] = task.eval_script
        mcp_client = MCPClient(
            stdio_command=f"{sys.executable} {MCP_TOOLS_SCRIPT}", env=mcp_env,
        )
    else:
        docker_ctx = DockerTestbed(task)
        stdio_cmd = docker_ctx.__enter__()
        mcp_client = MCPClient(stdio_command=stdio_cmd)

    sandbox_config = SandboxConfig(allowed_directories=["/testbed", "/tmp/agent"])
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
        task_id=task.instance_id, benchmark="swebench", limits=limits,
    )

    try:
        solution = orchestrator.run()
    finally:
        executor.shutdown()
        mcp_client.close()
        provider.close()
        if docker_ctx is not None:
            docker_ctx.__exit__(None, None, None)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(solution.model_dump_json(indent=2))
    print(f"Wrote {args.output} (success={solution.success}, iterations={solution.iterations})")
    return 0 if solution.success else 1


if __name__ == "__main__":
    sys.exit(main())
