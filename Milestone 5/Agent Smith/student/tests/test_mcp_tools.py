import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sandbox.mcp_client import MCPClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_mbpp_run_tests_pass():
    client = MCPClient(stdio_command=f"{sys.executable} {REPO_ROOT / 'mcp_tools_mbpp.py'}")
    try:
        assert "run_tests" in client.tool_names
        result = json.loads(client.call_tool_sync(
            "run_tests", code="def add(a, b):\n    return a + b\n",
            test_list=["assert add(1, 2) == 3", "assert add(-1, 1) == 0"],
        ))
        assert result["success"] is True
    finally:
        client.close()


def test_mbpp_run_tests_fail_is_explicit():
    client = MCPClient(stdio_command=f"{sys.executable} {REPO_ROOT / 'mcp_tools_mbpp.py'}")
    try:
        result = json.loads(client.call_tool_sync(
            "run_tests", code="def add(a, b):\n    return a - b\n",
            test_list=["assert add(1, 2) == 3"],
        ))
        assert result["success"] is False
        assert "FAIL" in result["output"]
    finally:
        client.close()


@pytest.fixture
def testbed(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "mod.py").write_text(
        "def add(a, b):\n    return a - b  # bug: should be +\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=t",
                     "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def _swebench_client(testbed_path: Path, eval_script: str) -> MCPClient:
    env = dict(os.environ)
    env["TESTBED_PATH"] = str(testbed_path)
    env["EVAL_SCRIPT"] = eval_script
    return MCPClient(stdio_command=f"{sys.executable} {REPO_ROOT / 'mcp_tools_swebench.py'}", env=env)


def test_swebench_read_search_edit_patch_run(testbed):
    eval_script = f"{sys.executable} -c \"import sys; sys.path.insert(0,'src'); from mod import add; assert add(1,2)==3\""
    client = _swebench_client(testbed, eval_script)
    try:
        expected_tools = {
            "read_file", "edit_file", "list_files", "search_code",
            "search_function_or_class_definition_in_code", "find_references",
            "run_tests", "get_patch", "run_command",
        }
        assert expected_tools.issubset(set(client.tool_names))

        content = client.call_tool_sync("read_file", filepath="src/mod.py", start_line=1, end_line=2)
        assert "1: def add" in content

        found = client.call_tool_sync("search_function_or_class_definition_in_code", name="add")
        assert "mod.py" in found

        edit_result = client.call_tool_sync(
            "edit_file", filepath="src/mod.py",
            old_str="return a - b  # bug: should be +",
            new_str="return a + b",
        )
        assert "[OK]" in edit_result

        run_result = client.call_tool_sync("run_command", command="echo hi", workdir="")
        assert json.loads(run_result)["exit_code"] == 0

        test_result = client.call_tool_sync("run_tests")
        assert "exit_code=0" in test_result

        patch = client.call_tool_sync("get_patch")
        assert "diff --git" in patch
        assert "+    return a + b" in patch
    finally:
        client.close()


def test_swebench_edit_file_rejects_ambiguous_match(testbed):
    (testbed / "src" / "dup.py").write_text("x = 1\nx = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=testbed, check=True)
    subprocess.run(["git", "-c", "user.email=t@t.com", "-c", "user.name=t",
                     "commit", "-q", "-m", "dup"], cwd=testbed, check=True)
    client = _swebench_client(testbed, "true")
    try:
        result = client.call_tool_sync("edit_file", filepath="src/dup.py", old_str="x = 1", new_str="x = 2")
        assert "ambiguous" in result
    finally:
        client.close()


def test_swebench_edit_file_reports_syntax_error(testbed):
    client = _swebench_client(testbed, "true")
    try:
        result = client.call_tool_sync(
            "edit_file", filepath="src/mod.py",
            old_str="def add(a, b):", new_str="def add(a, b:",
        )
        assert "SYNTAX ERROR" in result
    finally:
        client.close()


def test_swebench_path_traversal_is_blocked(testbed):
    client = _swebench_client(testbed, "true")
    try:
        result = client.call_tool_sync("read_file", filepath="/etc/passwd", start_line=1, end_line=1)
        assert "[ERROR]" in result
    finally:
        client.close()
