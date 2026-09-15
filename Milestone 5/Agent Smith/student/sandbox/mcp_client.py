"""MCP client used by the sandbox to reach an external MCP server.

The MCP protocol itself is async. Since the rest of this codebase (the sandbox
parent-process loop, the orchestrator) is written synchronously for simplicity,
this module runs a private asyncio event loop in a background thread and
exposes a blocking `call_tool_sync` method. This is the ONLY place in the
project that is allowed to touch the network / spawn the MCP server process --
it always runs in the parent process, never inside the restricted sandbox
child (see sandbox/executor.py).
"""
from __future__ import annotations

import asyncio
import json
import shlex
import threading
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:  # pragma: no cover - older mcp versions
    streamablehttp_client = None


class MCPToolSchema:
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MCPClient:
    """Connects to one MCP server (stdio command OR HTTP URL) and exposes its tools."""

    def __init__(self, stdio_command: Optional[str] = None, http_url: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None):
        if bool(stdio_command) == bool(http_url):
            raise ValueError("Provide exactly one of stdio_command or http_url")
        self.stdio_command = stdio_command
        self.http_url = http_url
        self.env = env
        self.tools: List[MCPToolSchema] = []
        self.tool_names: List[str] = []
        self.resources: List[Any] = []
        self.prompts: List[Any] = []

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._session: Optional[ClientSession] = None
        self._stack: Optional[AsyncExitStack] = None

        self._run(self._connect())

    # -- internal plumbing ------------------------------------------------

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def _connect(self):
        self._stack = AsyncExitStack()
        if self.stdio_command:
            parts = shlex.split(self.stdio_command)
            params = StdioServerParameters(command=parts[0], args=parts[1:], env=self.env)
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            if streamablehttp_client is None:
                raise RuntimeError("streamable HTTP transport not available in this mcp version")
            read, write, _ = await self._stack.enter_async_context(streamablehttp_client(self.http_url))

        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._session = session

        tools_result = await session.list_tools()
        self.tools = [
            MCPToolSchema(t.name, t.description or "", t.inputSchema or {})
            for t in tools_result.tools
        ]
        self.tool_names = [t.name for t in self.tools]

        try:
            res = await session.list_resources()
            self.resources = res.resources
        except Exception:
            self.resources = []
        try:
            pr = await session.list_prompts()
            self.prompts = pr.prompts
        except Exception:
            self.prompts = []

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            text = "\n".join(getattr(c, "text", str(c)) for c in result.content)
            raise RuntimeError(text)
        parts = []
        for c in result.content:
            parts.append(getattr(c, "text", str(c)))
        return "\n".join(parts)

    # -- public sync API ----------------------------------------------------

    def call_tool_sync(self, _tool_name: str, *args, **kwargs) -> str:
        """Call an MCP tool by name. Positional args are matched to the tool's
        declared input schema order; keyword args are passed through directly.

        The tool-name parameter is intentionally named `_tool_name` (leading
        underscore) rather than `name`, since several mandatory tools (e.g.
        `search_function_or_class_definition_in_code(name=...)`) legitimately
        have their own argument called `name`.
        """
        arguments = dict(kwargs)
        if args:
            schema = next((t.input_schema for t in self.tools if t.name == _tool_name), {})
            props = list((schema or {}).get("properties", {}).keys())
            for i, val in enumerate(args):
                if i < len(props):
                    arguments[props[i]] = val
        return self._run(self._call_tool(_tool_name, arguments))

    def manual(self) -> str:
        """Render a human/LLM-readable manual of every tool this server exposes.

        This is generated dynamically from the connected server's schemas, per
        Section V.2 point 5: "When a different MCP server is connected, the
        manual should automatically reflect that server's tools."
        """
        lines = ["## Available tools (from connected MCP server)\n"]
        for t in self.tools:
            lines.append(f"### {t.name}(...)")
            if t.description:
                lines.append(t.description.strip())
            props = (t.input_schema or {}).get("properties", {})
            required = set((t.input_schema or {}).get("required", []))
            if props:
                lines.append("Parameters:")
                for pname, pschema in props.items():
                    ptype = pschema.get("type", "any")
                    req = "required" if pname in required else "optional"
                    lines.append(f"  - {pname} ({ptype}, {req})")
            lines.append("")
        if not self.tools:
            lines.append("(no tools exposed by this server)")
        return "\n".join(lines)

    def close(self):
        try:
            self._run(self._stack.aclose())
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
