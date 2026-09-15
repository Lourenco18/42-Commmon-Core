import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core.code_extraction import extract_code


def test_python_block():
    text = "Thought: ok\nCode:\n```python\nprint(1+1)\n```\n<end_code>"
    r = extract_code(text)
    assert r.format_used == "python_block"
    assert r.code.strip() == "print(1+1)"
    assert r.warning is None


def test_no_code_block_gives_explicit_feedback():
    r = extract_code("I think the answer is 42, no code needed.")
    assert r.code is None
    assert "No valid code block" in r.warning


def test_xml_invoke_is_converted_to_python():
    text = (
        'Thought: reading a file\n'
        '<invoke name="read_file"><parameter name="filepath">/testbed/a.py</parameter>'
        '<parameter name="start_line">1</parameter></invoke>'
    )
    r = extract_code(text)
    assert r.format_used == "xml_invoke"
    assert "read_file(" in r.code
    assert "filepath=" in r.code
    assert r.warning is not None


def test_json_tool_call_is_converted_to_python():
    text = '<tool_call>{"name": "search_code", "arguments": {"pattern": "foo"}}</tool_call>'
    r = extract_code(text)
    assert r.format_used == "json_tool_call"
    assert "search_code(" in r.code
    assert "pattern=" in r.code


def test_malformed_json_tool_call_gives_explicit_feedback():
    text = "<tool_call>{not valid json}</tool_call>"
    r = extract_code(text)
    assert r.code is None
    assert "could not be parsed" in r.warning


def test_react_format_is_converted_to_python():
    text = 'Action: list_files\nAction Input: {"directory": "/testbed"}'
    r = extract_code(text)
    assert r.format_used == "react"
    assert "list_files(" in r.code
