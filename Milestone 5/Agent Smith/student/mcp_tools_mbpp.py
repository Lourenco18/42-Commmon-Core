"""MCP server exposing the mandatory MBPP tool(s) (Section V.3 point 2).

Run standalone for manual testing:
    python mcp_tools_mbpp.py                 # stdio transport (default)
    python mcp_tools_mbpp.py --http 8765      # streamable-HTTP transport

Used by the sandbox via:
    uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import traceback

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-smith-mbpp-tools")


def _run_candidate(code: str, test_list: list[str], conn) -> None:
    namespace: dict = {}
    output_lines: list[str] = []
    try:
        exec(compile(code, "<candidate>", "exec"), namespace)
        for test in test_list:
            try:
                exec(compile(test, "<test>", "exec"), namespace)
                output_lines.append(f"PASS: {test}")
            except AssertionError as exc:
                conn.send({"success": False, "output": "\n".join(output_lines + [f"FAIL: {test} ({exc})"])})
                return
            except Exception as exc:  # noqa: BLE001
                conn.send({"success": False,
                           "output": "\n".join(output_lines + [f"ERROR running {test}: {exc}"])})
                return
        conn.send({"success": True, "output": "\n".join(output_lines)})
    except Exception:
        conn.send({"success": False, "output": traceback.format_exc()})


@mcp.tool()
def run_tests(code: str, test_list: list[str]) -> str:
    """Run a candidate MBPP solution against the given test assertions.

    Args:
        code: The full source of the candidate Python function(s).
        test_list: A list of Python `assert ...` statements to run against `code`.

    Returns:
        A JSON string: {"success": bool, "output": str}
    """
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe()
    proc = ctx.Process(target=_run_candidate, args=(code, test_list, child_conn))
    proc.start()
    proc.join(timeout=10)
    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
        return json.dumps({"success": False, "output": "Execution timed out after 10 seconds."})
    if parent_conn.poll():
        return json.dumps(parent_conn.recv())
    return json.dumps({"success": False, "output": "Candidate process crashed with no output."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", type=int, default=None, help="Serve over streamable HTTP on this port")
    args = parser.parse_args()
    if args.http:
        mcp.settings.port = args.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
