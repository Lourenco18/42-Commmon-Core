import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moulinette_eval.cli import main as moulinette_main


def test_dump_mbpp_writes_task_file(tmp_path):
    out = tmp_path / "task.json"
    rc = moulinette_main(["dump", "mbpp", "--output", str(out), "--task-id", "1"])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["task_id"] == 1
    assert "test_list" in data


def test_validate_mbpp_pass(tmp_path):
    task_file = tmp_path / "task.json"
    moulinette_main(["dump", "mbpp", "--output", str(task_file), "--task-id", "1"])

    sol = {
        "task_id": "1", "benchmark": "mbpp", "success": True,
        "solution": "def sum_list(numbers):\n    return sum(numbers)\n",
        "iterations": 1, "total_requests": 1, "total_input_tokens": 10,
        "total_output_tokens": 10, "total_time_seconds": 1.0, "steps": [],
    }
    sol_file = tmp_path / "solution.json"
    sol_file.write_text(json.dumps(sol))

    try:
        moulinette_main(["validate", "mbpp", str(task_file), str(sol_file)])
        assert False, "should have sys.exit(0) which raises SystemExit"
    except SystemExit as e:
        assert e.code == 0


def test_validate_mbpp_fail_on_wrong_solution(tmp_path):
    task_file = tmp_path / "task.json"
    moulinette_main(["dump", "mbpp", "--output", str(task_file), "--task-id", "1"])

    sol = {
        "task_id": "1", "benchmark": "mbpp", "success": True,
        "solution": "def sum_list(numbers):\n    return 0\n",  # wrong
        "iterations": 1, "total_requests": 1, "total_input_tokens": 10,
        "total_output_tokens": 10, "total_time_seconds": 1.0, "steps": [],
    }
    sol_file = tmp_path / "solution.json"
    sol_file.write_text(json.dumps(sol))

    try:
        moulinette_main(["validate", "mbpp", str(task_file), str(sol_file)])
        assert False
    except SystemExit as e:
        assert e.code == 1


def test_validate_mbpp_fail_on_limit_violation(tmp_path):
    task_file = tmp_path / "task.json"
    moulinette_main(["dump", "mbpp", "--output", str(task_file), "--task-id", "1"])

    sol = {
        "task_id": "1", "benchmark": "mbpp", "success": True,
        "solution": "def sum_list(numbers):\n    return sum(numbers)\n",
        "iterations": 99, "total_requests": 99, "total_input_tokens": 999999,
        "total_output_tokens": 10, "total_time_seconds": 1.0, "steps": [],
    }
    sol_file = tmp_path / "solution.json"
    sol_file.write_text(json.dumps(sol))

    try:
        moulinette_main(["validate", "mbpp", str(task_file), str(sol_file)])
        assert False
    except SystemExit as e:
        assert e.code == 1
