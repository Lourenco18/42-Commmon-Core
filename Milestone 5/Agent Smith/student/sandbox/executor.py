"""The sandbox execution engine.

Architecture (matches the diagram in the subject, Chapter III):

    Orchestrator -> SandboxExecutor.execute(code) -> child process
                                                        |
                                                        | restricted exec()
                                                        | (imports / paths / builtins checked)
                                                        |
                        MCP tool call  <----------------+  (blocks, sent back to parent
                        (parent process, has                over a pipe, because the
                         network access)                     child has none)

Security properties enforced entirely with the standard library (no RestrictedPython):
  * Import allowlist        -> custom __import__ consulting SandboxConfig.import_is_allowed
  * Filesystem allowlist    -> custom open() consulting SandboxConfig.path_is_allowed
  * No network access       -> `socket`, `urllib`, `http`, `requests`, `ssl` are never importable
                                (they are simply absent from authorized_imports by default, and
                                even if listed, real network egress is blocked at the OS/container
                                boundary by the deployment -- see README "Sandbox Design")
  * Execution timeout       -> SIGALRM inside the child (interrupts pure-Python loops at
                                bytecode boundaries) + a parent-side hard join(timeout) that
                                SIGTERMs then SIGKILLs the child if it does not respond in time
  * Memory limit             -> resource.setrlimit(RLIMIT_AS, ...) set in the child before running
                                any user code
  * Restricted builtins      -> a curated __builtins__ dict; dangerous builtins
                                (eval, exec, compile, __import__, input, breakpoint, ...) removed
                                or replaced by safe wrappers
  * KeyboardInterrupt/SystemExit are re-raised, never silently swallowed
"""
from __future__ import annotations

import multiprocessing as mp
import queue
import resource
import signal
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from sandbox.config import SandboxConfig

# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


class SandboxTimeout(Exception):
    """Raised inside the child when SIGALRM fires."""


@dataclass
class ExecutionResult:
    stdout: str = ""
    error: Optional[str] = None
    final_answer: Optional[str] = None
    timed_out: bool = False
    truncated: bool = False

    def feedback(self, max_chars: int = 8000) -> str:
        """Render an explicit, LLM-readable observation string.

        Per Section V.1: the LLM must NEVER be left guessing about what happened.
        """
        parts = []
        if self.timed_out:
            parts.append("[SANDBOX] Execution exceeded the configured timeout. "
                          "Output below is PARTIAL.")
        if self.stdout:
            parts.append(self.stdout)
        if self.error:
            parts.append(f"[SANDBOX ERROR]\n{self.error}")
        if self.final_answer is not None:
            parts.append("[SANDBOX] final_answer() was called. Task loop will stop.")
        text = "\n".join(parts) if parts else "[SANDBOX] Code executed with no output."
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n[SANDBOX] Output truncated to {max_chars} characters."
            self.truncated = True
        return text


# ---------------------------------------------------------------------------
# Child process worker
# ---------------------------------------------------------------------------

# Builtins that are always dangerous inside the sandbox, regardless of config.
_FORBIDDEN_BUILTINS = {
    "eval", "exec", "compile", "__import__", "input", "breakpoint",
    "open",  # replaced below with a restricted version
    "exit", "quit", "help", "copyright", "credits", "license",
}


def _alarm_handler(signum, frame):  # pragma: no cover - exercised via subprocess
    raise SandboxTimeout("execution timed out")


def _make_restricted_open(config: SandboxConfig):
    real_open = open

    def restricted_open(file, mode="r", *args, **kwargs):
        if any(c in mode for c in ("w", "a", "x", "+")) or "r" in mode:
            if not config.path_is_allowed(file):
                raise PermissionError(
                    f"[SANDBOX] Access to '{file}' is denied. "
                    f"Allowed directories: {config.allowed_directories}"
                )
        return real_open(file, mode, *args, **kwargs)

    return restricted_open


def _make_restricted_import(config: SandboxConfig):
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        top_level = name.split(".")[0]
        # Allow submodule imports if either the exact dotted name or the
        # top-level '<name>.*' wildcard is authorized.
        if not (config.import_is_allowed(name) or config.import_is_allowed(top_level)):
            raise ImportError(
                f"[SANDBOX] Import of '{name}' is blocked by the sandbox allowlist. "
                f"Authorized imports: {config.authorized_imports}"
            )
        return real_import(name, globals, locals, fromlist, level)

    return restricted_import


def _build_namespace(config: SandboxConfig, tool_names: list[str], conn) -> Dict[str, Any]:
    """Build the exec() global namespace: safe builtins + MCP tool wrappers + final_answer."""
    safe_builtins = {
        k: v for k, v in vars(__import__("builtins")).items() if k not in _FORBIDDEN_BUILTINS
    }
    safe_builtins["open"] = _make_restricted_open(config)
    safe_builtins["__import__"] = _make_restricted_import(config)

    namespace: Dict[str, Any] = {"__builtins__": safe_builtins}

    def make_tool_wrapper(tool_name: str) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            conn.send(("TOOL_CALL", tool_name, args, kwargs))
            kind, payload = conn.recv()
            if kind == "TOOL_ERROR":
                raise RuntimeError(f"[MCP TOOL ERROR] {tool_name}: {payload}")
            return payload

        wrapper.__name__ = tool_name
        return wrapper

    for name in tool_names:
        namespace[name] = make_tool_wrapper(name)

    def final_answer(answer: str):
        conn.send(("FINAL_ANSWER", answer))
        raise _FinalAnswerSignal(answer)

    namespace["final_answer"] = final_answer
    return namespace


class _FinalAnswerSignal(Exception):
    def __init__(self, answer: str):
        super().__init__("final_answer() called")
        self.answer = answer


def _child_main(conn, config: SandboxConfig, tool_names: list[str]):
    """Entry point of the persistent sandbox child process."""
    try:
        resource.setrlimit(
            resource.RLIMIT_AS,
            (config.max_memory_mb * 1024 * 1024, resource.RLIM_INFINITY),
        )
    except (ValueError, resource.error):
        pass  # some platforms disallow RLIMIT_AS; best effort

    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _alarm_handler)

    namespace = _build_namespace(config, tool_names, conn)
    conn.send(("READY", None))

    while True:
        try:
            msg = conn.recv()
        except (EOFError, KeyboardInterrupt):
            break
        if msg[0] == "SHUTDOWN":
            break
        if msg[0] != "EXEC":
            continue
        code = msg[1]
        timeout_s = msg[2]

        import io
        import contextlib

        stdout_buf = io.StringIO()
        final_answer_value = None
        error_text = None
        timed_out = False

        if hasattr(signal, "SIGALRM"):
            signal.alarm(max(1, int(timeout_s)))
        try:
            with contextlib.redirect_stdout(stdout_buf):
                exec(compile(code, "<agent_code>", "exec"), namespace)
        except _FinalAnswerSignal as fa:
            final_answer_value = fa.answer
        except SandboxTimeout:
            timed_out = True
            error_text = f"Execution exceeded {timeout_s}s and was interrupted."
        except (KeyboardInterrupt, SystemExit):
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)
            raise
        except Exception:
            error_text = "".join(traceback.format_exception(*sys.exc_info()))
        finally:
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)

        conn.send((
            "DONE",
            {
                "stdout": stdout_buf.getvalue(),
                "error": error_text,
                "final_answer": final_answer_value,
                "timed_out": timed_out,
            },
        ))


# ---------------------------------------------------------------------------
# Parent-side controller
# ---------------------------------------------------------------------------


class SandboxExecutor:
    """Parent-side handle to a persistent, isolated sandbox child process.

    One instance == one agent "session": variables persist across .execute() calls,
    matching the code-based tool calling requirement (persistent state between steps).
    """

    def __init__(self, config: Optional[SandboxConfig] = None, mcp_client=None):
        self.config = config or SandboxConfig()
        self.mcp_client = mcp_client  # object exposing .call_tool_sync(name, args, kwargs) -> str
        self._tool_names = list(mcp_client.tool_names) if mcp_client else []
        self._proc: Optional[mp.Process] = None
        self._conn = None
        self._start()

    def _start(self):
        # 'fork' is used (Linux/macOS) instead of 'spawn': spawn re-imports the
        # launching __main__ module in the child, which is fragile when the
        # orchestrator itself is invoked via `python -m ...` or from a REPL.
        # fork is also markedly faster to start, which matters since a fresh
        # sandbox session is created per solved task.
        start_method = "fork" if "fork" in mp.get_all_start_methods() else "spawn"
        ctx = mp.get_context(start_method)
        parent_conn, child_conn = ctx.Pipe()
        self._proc = ctx.Process(
            target=_child_main, args=(child_conn, self.config, self._tool_names), daemon=True
        )
        self._proc.start()
        self._conn = parent_conn
        ready = self._conn.recv()
        assert ready[0] == "READY"

    def restart(self):
        self.shutdown()
        self._start()

    def shutdown(self):
        if self._proc and self._proc.is_alive():
            try:
                self._conn.send(("SHUTDOWN", None))
            except (BrokenPipeError, OSError):
                pass
            self._proc.join(timeout=2)
            if self._proc.is_alive():
                self._proc.terminate()
                self._proc.join(timeout=2)
            if self._proc.is_alive():
                self._proc.kill()

    def execute(self, code: str) -> ExecutionResult:
        """Run `code` in the sandbox, servicing MCP tool calls until completion or timeout."""
        if not self._proc or not self._proc.is_alive():
            self._start()

        timeout = self.config.max_execution_time_seconds
        self._conn.send(("EXEC", code, timeout))
        deadline = time.time() + timeout + 5  # grace period for IPC/tool latency

        while True:
            remaining = deadline - time.time()
            if remaining <= 0 or not self._conn.poll(remaining):
                # Hard timeout: force-kill the child (SIGTERM then SIGKILL).
                self._proc.terminate()
                self._proc.join(timeout=2)
                if self._proc.is_alive():
                    self._proc.kill()
                self._start()
                return ExecutionResult(
                    error=f"Execution exceeded {timeout}s and the sandbox process was killed.",
                    timed_out=True,
                )

            kind, *payload = self._conn.recv()

            if kind == "TOOL_CALL":
                tool_name, args, kwargs = payload
                try:
                    result = self.mcp_client.call_tool_sync(tool_name, *args, **kwargs)
                    self._conn.send(("TOOL_RESULT", result))
                except Exception as exc:  # noqa: BLE001 - surfaced to the sandboxed code
                    self._conn.send(("TOOL_ERROR", str(exc)))
                continue

            if kind == "FINAL_ANSWER":
                # informational echo; DONE message follows right after
                continue

            if kind == "DONE":
                data = payload[0]
                return ExecutionResult(
                    stdout=data["stdout"],
                    error=data["error"],
                    final_answer=data["final_answer"],
                    timed_out=data["timed_out"],
                )
