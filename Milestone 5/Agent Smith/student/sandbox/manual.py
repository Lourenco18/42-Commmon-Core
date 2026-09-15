"""Generates the full sandbox manual fed to the LLM (Section V.2 point 5).

Combines: (a) static sandbox usage rules, (b) the configured import/path
limits, and (c) the MCP server's tool schemas, discovered dynamically.
"""
from __future__ import annotations

from sandbox.config import SandboxConfig
from sandbox.mcp_client import MCPClient


def build_manual(config: SandboxConfig, mcp_client: MCPClient | None) -> str:
    lines = [
        "# Sandbox Manual",
        "",
        "You write Python code. It is executed in an isolated child process with:",
        f"- Authorized imports: {', '.join(config.authorized_imports)}",
        f"- Allowed directories: {', '.join(config.allowed_directories)}",
        f"- Execution timeout: {config.max_execution_time_seconds} seconds per code block",
        f"- Memory limit: {config.max_memory_mb} MB",
        "- No network access is available inside the sandbox.",
        "",
        "Variables persist between code blocks you submit (it is a REPL, not a "
        "one-shot script). Use `print(...)` to see values -- anything not printed "
        "is not shown back to you as an Observation.",
        "",
        "## final_answer(answer: str)",
        "Built into the sandbox itself (NOT an MCP tool, always available). "
        "Call it exactly once when you are done:",
        "  - MBPP: final_answer(your_python_function_source_code)",
        "  - SWE-bench: final_answer(get_patch())",
        "Calling it ends the agent loop.",
        "",
    ]
    if mcp_client is not None:
        lines.append(mcp_client.manual())
    else:
        lines.append("(no MCP server connected -- only final_answer is available)")
    return "\n".join(lines)
