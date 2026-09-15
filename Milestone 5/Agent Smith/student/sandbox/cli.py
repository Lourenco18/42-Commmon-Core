"""Sandbox CLI entry point.

Usage (matches Section V.2 point 1 of the subject exactly):

    uv run sandbox
    uv run sandbox sandbox_template.json
    uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
    uv run sandbox --mcp-server <URL>
    uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json
"""
from __future__ import annotations

import argparse
import sys

from sandbox.config import SandboxConfig
from sandbox.executor import SandboxExecutor
from sandbox.manual import build_manual
from sandbox.mcp_client import MCPClient


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sandbox", description="Agent Smith interactive sandbox")
    parser.add_argument("config", nargs="?", default=None, help="Path to a sandbox_template.json config file")
    parser.add_argument("--mcp-stdio", default=None, help="Command to launch an MCP server over stdio")
    parser.add_argument("--mcp-server", default=None, help="URL of a streamable-HTTP MCP server")
    parser.add_argument("--manual", action="store_true", help="Print the generated manual and exit")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = SandboxConfig.load(args.config)

    mcp_client = None
    if args.mcp_stdio:
        mcp_client = MCPClient(stdio_command=args.mcp_stdio)
    elif args.mcp_server:
        mcp_client = MCPClient(http_url=args.mcp_server)

    if args.manual:
        print(build_manual(config, mcp_client))
        return 0

    print("Agent Smith interactive sandbox. Type 'exit' or Ctrl+D to quit.")
    if mcp_client:
        print(f"Connected MCP tools: {', '.join(mcp_client.tool_names) or '(none)'}")
    print(f"Authorized imports: {', '.join(config.authorized_imports)}")
    print(f"Allowed directories: {', '.join(config.allowed_directories)}")
    print()

    executor = SandboxExecutor(config=config, mcp_client=mcp_client)
    try:
        while True:
            try:
                line = input(">>> ")
            except EOFError:
                print()
                break
            if line.strip() in ("exit", "exit()", "quit", "quit()"):
                break
            if not line.strip():
                continue
            result = executor.execute(line)
            print(result.feedback(), end="" if result.feedback().endswith("\n") else "\n")
            if result.final_answer is not None:
                print(f"[final_answer received]: {result.final_answer!r}")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        executor.shutdown()
        if mcp_client:
            mcp_client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
