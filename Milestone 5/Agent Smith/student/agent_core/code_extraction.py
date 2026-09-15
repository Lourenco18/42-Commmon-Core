"""Extracts executable Python code from an LLM response, whatever format it used.

Per Section V.1: LLMs are trained on different tool-calling conventions. This
module normalizes all of them into a single Python snippet before it reaches
the sandbox, so the sandbox itself stays format-agnostic.

Supported input formats (non-exhaustive, per the subject):
  (a) Python code blocks (primary)  -- ```python ... ``` optionally followed by <end_code>
  (b) XML tool calls (Anthropic-style) -- <invoke name="..."><parameter name="k">v</parameter></invoke>
  (c) JSON/Hermes tool calls        -- <tool_call>{"name": "...", "arguments": {...}}</tool_call>
  (d) ReAct format                  -- Action: tool_name\nAction Input: {...}

If nothing is found, `extract_code` returns (None, reason) so the sandbox can
give explicit feedback rather than silently doing nothing (Section V.1 warning box).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractionResult:
    code: Optional[str]
    format_used: Optional[str]
    warning: Optional[str] = None  # set when a malformed block was interpreted anyway


_PY_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)(?:```|<end_code>)", re.DOTALL)
_XML_INVOKE_RE = re.compile(
    r'<invoke\s+name="([^"]+)"\s*>(.*?)</invoke>', re.DOTALL
)
_XML_PARAM_RE = re.compile(
    r'<parameter\s+name="([^"]+)"\s*>(.*?)</parameter>', re.DOTALL
)
_JSON_TOOLCALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_REACT_RE = re.compile(
    r"Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\n\s*Action Input:\s*(\{.*?\}|\S.*)", re.DOTALL
)


def _py_repr_value(value) -> str:
    """Render a JSON-decoded value as a Python literal for a function call."""
    return repr(value)


def _call_from_name_args(name: str, arguments: dict) -> str:
    args_src = ", ".join(f"{k}={_py_repr_value(v)}" for k, v in arguments.items())
    return f"result = {name}({args_src})\nprint(result)"


def extract_code(llm_output: str) -> ExtractionResult:
    """Best-effort extraction, trying formats in order of likelihood."""

    # (a) Python code block -- primary format
    m = _PY_BLOCK_RE.search(llm_output)
    if m:
        code = m.group(1).strip()
        if code:
            return ExtractionResult(code=code, format_used="python_block")
        return ExtractionResult(code=None, format_used=None,
                                  warning="A python code block was found but was empty.")

    # (b) XML tool calls (Anthropic-style <invoke>)
    m = _XML_INVOKE_RE.search(llm_output)
    if m:
        name, body = m.group(1), m.group(2)
        args = {}
        for pname, pval in _XML_PARAM_RE.findall(body):
            args[pname] = pval.strip()
        code = _call_from_name_args(name, args)
        return ExtractionResult(
            code=code, format_used="xml_invoke",
            warning="Non-Python <invoke> tool call format was auto-converted to a Python call.",
        )

    # (c) JSON / Hermes-style <tool_call>{...}</tool_call>
    m = _JSON_TOOLCALL_RE.search(llm_output)
    if m:
        try:
            data = json.loads(m.group(1))
            name = data["name"]
            args = data.get("arguments", {})
            code = _call_from_name_args(name, args)
            return ExtractionResult(
                code=code, format_used="json_tool_call",
                warning="Non-Python <tool_call> JSON format was auto-converted to a Python call.",
            )
        except (json.JSONDecodeError, KeyError) as exc:
            return ExtractionResult(
                code=None, format_used=None,
                warning=f"A <tool_call> block was found but could not be parsed as valid JSON: {exc}",
            )

    # (d) ReAct format: "Action: tool\nAction Input: {...}"
    m = _REACT_RE.search(llm_output)
    if m:
        name, raw_args = m.group(1), m.group(2).strip()
        try:
            args = json.loads(raw_args)
            if not isinstance(args, dict):
                args = {"value": args}
        except json.JSONDecodeError:
            args = {"value": raw_args}
        code = _call_from_name_args(name, args)
        return ExtractionResult(
            code=code, format_used="react",
            warning="ReAct Action/Action Input format was auto-converted to a Python call.",
        )

    return ExtractionResult(
        code=None, format_used=None,
        warning="No valid code block, <invoke>, <tool_call>, or ReAct Action was found in the response.",
    )
