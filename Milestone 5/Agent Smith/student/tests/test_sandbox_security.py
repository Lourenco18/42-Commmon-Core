import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor


@pytest.fixture
def executor():
    config = SandboxConfig(max_execution_time_seconds=2, max_memory_mb=128)
    ex = SandboxExecutor(config=config)
    yield ex
    ex.shutdown()


def test_import_allowlist_blocks_os(executor):
    result = executor.execute("import os")
    assert result.error is not None
    assert "blocked by the sandbox allowlist" in result.error


def test_import_allowlist_allows_math(executor):
    result = executor.execute("import math\nprint(math.sqrt(16))")
    assert result.error is None
    assert "4.0" in result.stdout


def test_wildcard_import_allows_submodules(executor):
    result = executor.execute("import collections.abc\nprint('ok')")
    assert result.error is None


def test_dangerous_builtins_removed(executor):
    # eval/exec/compile/input are removed outright -> referencing them raises NameError.
    for builtin in ["eval", "exec", "compile", "input"]:
        result = executor.execute(f"{builtin}")
        assert result.error is not None, f"{builtin} should not be accessible"
        assert "NameError" in result.error


def test_import_dunder_stays_present_but_restricted(executor):
    # __import__ itself must remain (Python's `import` statement resolves it
    # internally), but *calling* it is still subject to the allowlist.
    result = executor.execute("__import__('os')")
    assert result.error is not None
    assert "blocked by the sandbox allowlist" in result.error


def test_filesystem_allowlist_blocks_outside_paths(executor):
    result = executor.execute("open('/etc/passwd').read()")
    assert result.error is not None
    assert "denied" in result.error


def test_state_persists_between_calls(executor):
    executor.execute("shared_value = 123")
    result = executor.execute("print(shared_value)")
    assert "123" in result.stdout


def test_timeout_is_enforced_and_sandbox_recovers():
    config = SandboxConfig(max_execution_time_seconds=1, max_memory_mb=128)
    ex = SandboxExecutor(config=config)
    try:
        result = ex.execute("while True:\n    pass")
        assert result.timed_out is True
        # sandbox must still be usable afterwards (process was killed & restarted)
        result2 = ex.execute("print('still alive')")
        assert "still alive" in result2.stdout
    finally:
        ex.shutdown()


def test_final_answer_stops_and_is_captured(executor):
    result = executor.execute("final_answer('the answer')")
    assert result.final_answer == "the answer"


def test_no_output_gives_explicit_feedback(executor):
    result = executor.execute("x = 1")
    assert "no output" in result.feedback().lower()


def test_syntax_error_reported_explicitly(executor):
    result = executor.execute("def broken(:\n    pass")
    assert result.error is not None
    assert "SyntaxError" in result.error
