"""MCP server exposing the mandatory SWE-bench tools (Section V.5).

Reads the repository root from the TESTBED_PATH environment variable, exactly
as mandated: "the moulinette sets the environment variable TESTBED_PATH to the
repository root before starting your MCP server. Your tools must read this
exact variable name to locate the repository."

Run standalone for manual testing:
    TESTBED_PATH=/path/to/repo python mcp_tools_swebench.py
    TESTBED_PATH=/path/to/repo python mcp_tools_swebench.py --http 8766

Used by the sandbox via:
    uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-smith-swebench-tools")


def _testbed() -> Path:
    path = os.environ.get("TESTBED_PATH")
    if not path:
        raise RuntimeError("TESTBED_PATH environment variable is not set.")
    return Path(path)


def _resolve_in_testbed(filepath: str) -> Path:
    p = Path(filepath)
    if not p.is_absolute():
        p = _testbed() / p
    resolved = p.resolve()
    testbed_resolved = _testbed().resolve()
    if testbed_resolved not in resolved.parents and resolved != testbed_resolved:
        raise PermissionError(f"'{filepath}' is outside the testbed ({testbed_resolved}).")
    return resolved


# -- File System Tools -------------------------------------------------------


@mcp.tool()
def read_file(filepath: str, start_line: int = 1, end_line: int = -1) -> str:
    """Read a file's content with line numbers (like `cat -n`).

    Args:
        filepath: Absolute or testbed-relative path to the file.
        start_line: First line to include (1-indexed, inclusive).
        end_line: Last line to include (inclusive). -1 means "to end of file".
    """
    try:
        path = _resolve_in_testbed(filepath)
        lines = path.read_text(errors="replace").splitlines()
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] Could not read '{filepath}': {exc}"

    end = len(lines) if end_line == -1 else min(end_line, len(lines))
    start = max(1, start_line)
    out = [f"{i}: {lines[i - 1]}" for i in range(start, end + 1) if 1 <= i <= len(lines)]
    if not out:
        return f"[ERROR] Requested range {start_line}-{end_line} is out of bounds (file has {len(lines)} lines)."
    return "\n".join(out)


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace an exact string in a file with a new string.

    Fails explicitly (rather than silently) if `old_str` is not found, or is
    found more than once (ambiguous edit). If the file is Python, the result
    is syntax-checked so the LLM is told immediately if the edit broke it.
    """
    try:
        path = _resolve_in_testbed(filepath)
        content = path.read_text()
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] Could not read '{filepath}': {exc}"

    count = content.count(old_str)
    if count == 0:
        return f"[ERROR] old_str was not found in '{filepath}'. No changes made."
    if count > 1:
        return (f"[ERROR] old_str occurs {count} times in '{filepath}' -- the edit is ambiguous. "
                f"Provide a longer, unique old_str. No changes made.")

    new_content = content.replace(old_str, new_str, 1)
    path.write_text(new_content)

    if path.suffix == ".py":
        try:
            ast.parse(new_content)
        except SyntaxError as exc:
            return (f"[EDIT APPLIED but INTRODUCED A SYNTAX ERROR] {filepath}:{exc.lineno}: {exc.msg}\n"
                    f"The file was still written -- fix it with another edit_file call.")
    return f"[OK] Edit applied to '{filepath}'."


@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files in `directory` (recursively) matching a glob `pattern`."""
    try:
        base = _resolve_in_testbed(directory)
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"
    if not base.exists():
        return f"[ERROR] Directory '{directory}' does not exist."
    matches = sorted(str(p) for p in base.rglob(pattern) if p.is_file() and ".git" not in p.parts)
    if not matches:
        return f"[NO MATCHES] No files matching '{pattern}' under '{directory}'."
    return "\n".join(matches)


# -- Code Search Tools --------------------------------------------------------


def _grep(pattern_words_in_line, file_pattern: str = "*.py", max_results: int = 200) -> str:
    results = []
    for path in sorted(_testbed().rglob(file_pattern)):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
                if pattern_words_in_line(line):
                    results.append(f"{path}:{lineno} {line.strip()}")
                    if len(results) >= max_results:
                        results.append(f"... [truncated at {max_results} results]")
                        return "\n".join(results)
        except Exception:
            continue
    return "\n".join(results) if results else "[NO MATCHES]"


@mcp.tool()
def search_code(pattern: str, file_pattern: str = "*.py") -> str:
    """Grep-like search across the codebase for a literal or regex `pattern`.

    Args:
        pattern: Text or regular expression to search for.
        file_pattern: Glob restricting which files are searched (default: "*.py").
    """
    import re
    try:
        rx = re.compile(pattern)
        return _grep(lambda line: rx.search(line) is not None, file_pattern)
    except re.error:
        return _grep(lambda line: pattern in line, file_pattern)


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    """Find the `def name(...)` or `class name(...)` definition in the codebase."""
    import re
    rx = re.compile(rf"^\s*(def|class)\s+{re.escape(name)}\b")
    return _grep(lambda line: rx.match(line) is not None, "*.py")


@mcp.tool()
def find_references(name: str, filepath: str = "", line: int = 0) -> str:
    """Find all usages of a symbol (function or class name) across the codebase."""
    import re
    rx = re.compile(rf"\b{re.escape(name)}\b")
    return _grep(lambda l: rx.search(l) is not None, "*.py")


# -- Execution Tools -----------------------------------------------------------


def _load_eval_script() -> str:
    script_path = os.environ.get("EVAL_SCRIPT_PATH")
    if script_path and Path(script_path).exists():
        return Path(script_path).read_text()
    inline = os.environ.get("EVAL_SCRIPT")
    if inline:
        return inline
    raise RuntimeError("No evaluation script found (set EVAL_SCRIPT_PATH or EVAL_SCRIPT).")


@mcp.tool()
def run_tests() -> str:
    """Execute the task's evaluation script and return its combined output."""
    try:
        script = _load_eval_script()
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"
    proc = subprocess.run(
        ["bash", "-c", script], cwd=str(_testbed()),
        capture_output=True, text=True, timeout=600,
    )
    return (f"[exit_code={proc.returncode}]\n"
            f"--- stdout ---\n{proc.stdout[-8000:]}\n"
            f"--- stderr ---\n{proc.stderr[-4000:]}")


@mcp.tool()
def get_patch() -> str:
    """Return the unified git diff of every change made so far in the testbed."""
    proc = subprocess.run(
        ["git", "-c", "core.fileMode=false", "diff"],
        cwd=str(_testbed()), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return f"[ERROR] git diff failed: {proc.stderr}"
    return proc.stdout


@mcp.tool()
def run_command(command: str, workdir: str = "") -> str:
    """Execute a shell command in the given working directory.

    Returns stdout, stderr, and the exit code as a JSON string.
    """
    cwd = str(_resolve_in_testbed(workdir)) if workdir else str(_testbed())
    try:
        proc = subprocess.run(
            ["bash", "-c", command], cwd=cwd, capture_output=True, text=True, timeout=120,
        )
        return json.dumps({
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-4000:],
            "exit_code": proc.returncode,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"stdout": "", "stderr": "command timed out after 120s", "exit_code": -1})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", type=int, default=None, help="Serve over streamable HTTP on this port")
    args = parser.parse_args()
    if args.http:
        mcp.settings.port = args.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
