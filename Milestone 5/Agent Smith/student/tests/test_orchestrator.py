import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core.llm_provider import DummyProvider
from agent_core.orchestrator import Orchestrator, OrchestratorLimits
from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor


def make_orchestrator(script, max_iterations=10):
    provider = DummyProvider(script)
    executor = SandboxExecutor(config=SandboxConfig())
    limits = OrchestratorLimits(
        max_iterations=max_iterations, max_input_tokens=100_000,
        max_output_tokens=100_000, max_time_seconds=60,
    )
    orch = Orchestrator(provider=provider, executor=executor, system_prompt="you are an agent",
                         task_id="t1", benchmark="mbpp", limits=limits)
    return orch, executor


def test_successful_run_reaches_final_answer():
    script = [
        "Code:\n```python\nx = 1 + 1\nprint(x)\n```\n<end_code>",
        "Code:\n```python\nfinal_answer('done')\n```\n<end_code>",
    ]
    orch, executor = make_orchestrator(script)
    try:
        solution = orch.run()
        assert solution.success is True
        assert solution.solution == "done"
        assert solution.iterations == 2
        assert solution.total_requests == 2
        assert solution.steps[0].sandbox_output  # observation recorded
        assert solution.error is None
    finally:
        executor.shutdown()


def test_missing_code_block_does_not_crash_and_gives_feedback():
    script = [
        "I have no code block here.",
        "Code:\n```python\nfinal_answer('ok')\n```\n<end_code>",
    ]
    orch, executor = make_orchestrator(script)
    try:
        solution = orch.run()
        assert solution.success is True
        assert "No valid code block" in solution.steps[0].sandbox_output
    finally:
        executor.shutdown()


def test_iteration_limit_is_enforced():
    script = ["Code:\n```python\nprint('looping')\n```\n<end_code>"] * 20
    orch, executor = make_orchestrator(script, max_iterations=3)
    try:
        solution = orch.run()
        assert solution.success is False
        assert solution.iterations == 3
        assert "Maximum iterations" in solution.error
    finally:
        executor.shutdown()


def test_output_json_schema_round_trips():
    script = ["Code:\n```python\nfinal_answer('x')\n```\n<end_code>"]
    orch, executor = make_orchestrator(script)
    try:
        solution = orch.run()
        payload = solution.model_dump_json()
        assert '"benchmark":"mbpp"' in payload.replace(" ", "")
    finally:
        executor.shutdown()
