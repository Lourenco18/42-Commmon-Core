"""moulinette_eval CLI.

    uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json
    uv run moulinette_eval dump swebench --output ../cache/swebench_task.json
    uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../cache/mbpp_solution.json
    uv run moulinette_eval validate swebench ../cache/swebench_task.json ../cache/swebench_solution.json
    uv run moulinette_eval prepare-testbed swebench demo__stringutils-1 --dest /tmp/testbed
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from moulinette_eval.models import SolutionOutput
from moulinette_eval.tasks_mbpp import TASKS as MBPP_TASKS
from moulinette_eval.tasks_swebench import TASKS as SWEBENCH_TASKS, eval_script_for, prepare_local_testbed

MBPP_LIMITS = dict(max_iterations=10, max_input_tokens=6000, max_output_tokens=1500, timeout=120)
SWEBENCH_LIMITS = dict(max_iterations=30, max_input_tokens=300_000, max_output_tokens=10_000, timeout=900)


# ---------------------------------------------------------------------------
# dump
# ---------------------------------------------------------------------------


def cmd_dump_mbpp(args):
    random.seed(args.seed)
    if args.task_id is not None:
        task = next(t for t in MBPP_TASKS if t["task_id"] == args.task_id)
    else:
        task = random.choice(MBPP_TASKS)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(task, indent=2))
    print(f"Dumped MBPP task #{task['task_id']} -> {args.output}")


def cmd_dump_swebench(args):
    random.seed(args.seed)
    if args.task_id is not None:
        base = dict(SWEBENCH_TASKS[args.task_id])
    else:
        base = dict(random.choice(list(SWEBENCH_TASKS.values())))
    base["eval_script"] = eval_script_for(base["instance_id"])
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(base, indent=2))
    print(f"Dumped SWE-bench task {base['instance_id']} -> {args.output}")
    print("NOTE: docker_image is a local-fixture marker (see README/BENCHMARK_REPORT for why). "
          f"Prepare a local testbed with:\n  uv run moulinette_eval prepare-testbed swebench "
          f"{base['instance_id']} --dest /tmp/testbed_{base['instance_id']}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def _check_limits(sol: SolutionOutput, limits: dict) -> list[str]:
    problems = []
    if sol.iterations > limits["max_iterations"]:
        problems.append(f"iterations {sol.iterations} > limit {limits['max_iterations']}")
    if sol.total_input_tokens > limits["max_input_tokens"]:
        problems.append(f"total_input_tokens {sol.total_input_tokens} > limit {limits['max_input_tokens']}")
    if sol.total_output_tokens > limits["max_output_tokens"]:
        problems.append(f"total_output_tokens {sol.total_output_tokens} > limit {limits['max_output_tokens']}")
    if sol.total_time_seconds > limits["timeout"]:
        problems.append(f"total_time_seconds {sol.total_time_seconds:.1f} > limit {limits['timeout']}")
    return problems


def cmd_validate_mbpp(args):
    task = json.loads(Path(args.task_file).read_text())
    sol = SolutionOutput(**json.loads(Path(args.solution_file).read_text()))

    problems = _check_limits(sol, MBPP_LIMITS)
    if sol.benchmark != "mbpp":
        problems.append(f"benchmark field is '{sol.benchmark}', expected 'mbpp'")
    if sol.task_id != str(task["task_id"]):
        problems.append(f"task_id mismatch: solution={sol.task_id} task={task['task_id']}")

    correctness_ok = False
    correctness_detail = ""
    if sol.success and sol.solution.strip():
        namespace: dict = {}
        try:
            exec(compile(sol.solution, "<solution>", "exec"), namespace)
            failures = []
            for test in task["test_list"]:
                try:
                    exec(compile(test, "<test>", "exec"), namespace)
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{test} -> {exc}")
            correctness_ok = not failures
            correctness_detail = "all tests passed" if correctness_ok else "; ".join(failures)
        except Exception as exc:  # noqa: BLE001
            correctness_detail = f"solution code raised on exec: {exc}"
    else:
        correctness_detail = "agent did not report success or solution is empty"

    passed = correctness_ok and not problems
    print(f"Task {task['task_id']}: {'PASS' if passed else 'FAIL'}")
    print(f"  correctness: {'ok' if correctness_ok else 'FAILED'} ({correctness_detail})")
    for p in problems:
        print(f"  LIMIT VIOLATION: {p}")
    sys.exit(0 if passed else 1)


def cmd_validate_swebench(args):
    task = json.loads(Path(args.task_file).read_text())
    sol = SolutionOutput(**json.loads(Path(args.solution_file).read_text()))

    problems = _check_limits(sol, SWEBENCH_LIMITS)
    if sol.benchmark != "swebench":
        problems.append(f"benchmark field is '{sol.benchmark}', expected 'swebench'")
    if sol.task_id != task["instance_id"]:
        problems.append(f"task_id mismatch: solution={sol.task_id} task={task['instance_id']}")

    patch_present = sol.success and sol.solution.strip().startswith(("diff", "---", "Index:"))
    if sol.success and not patch_present:
        problems.append("success=True but `solution` does not look like a unified git diff")

    test_result = "not checked (pass --testbed-path to run the real eval script against the patch)"
    passed_tests = None
    if args.testbed_path and patch_present:
        testbed = Path(args.testbed_path)
        patch_file = testbed / ".agent_smith_patch.diff"
        patch_file.write_text(sol.solution)
        apply = subprocess.run(["git", "apply", str(patch_file)], cwd=testbed, capture_output=True, text=True)
        if apply.returncode != 0:
            test_result = f"patch failed to apply: {apply.stderr[:300]}"
            passed_tests = False
        else:
            proc = subprocess.run(["bash", "-c", task["eval_script"]], cwd=testbed,
                                   capture_output=True, text=True, timeout=600)
            passed_tests = proc.returncode == 0
            test_result = f"eval_script exit_code={proc.returncode}"

    passed = not problems and patch_present and (passed_tests in (None, True))
    print(f"Task {task['instance_id']}: {'PASS' if passed else 'FAIL'}")
    print(f"  patch present: {patch_present}")
    print(f"  test result: {test_result}")
    for p in problems:
        print(f"  LIMIT VIOLATION: {p}")
    sys.exit(0 if passed else 1)


# ---------------------------------------------------------------------------
# prepare-testbed (helper, not part of the graded surface but useful in dev/CI)
# ---------------------------------------------------------------------------


def cmd_prepare_testbed(args):
    dest = Path(args.dest)
    prepare_local_testbed(args.instance_id, dest)
    print(f"Prepared local testbed for {args.instance_id} at {dest}")


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="moulinette_eval")
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump")
    dump_sub = dump.add_subparsers(dest="benchmark", required=True)
    p = dump_sub.add_parser("mbpp")
    p.add_argument("--output", required=True)
    p.add_argument("--task-id", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_dump_mbpp)
    p = dump_sub.add_parser("swebench")
    p.add_argument("--output", required=True)
    p.add_argument("--task-id", default=None, choices=list(SWEBENCH_TASKS.keys()))
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_dump_swebench)

    validate = sub.add_parser("validate")
    validate_sub = validate.add_subparsers(dest="benchmark", required=True)
    p = validate_sub.add_parser("mbpp")
    p.add_argument("task_file")
    p.add_argument("solution_file")
    p.set_defaults(func=cmd_validate_mbpp)
    p = validate_sub.add_parser("swebench")
    p.add_argument("task_file")
    p.add_argument("solution_file")
    p.add_argument("--testbed-path", default=None)
    p.set_defaults(func=cmd_validate_swebench)

    pt = sub.add_parser("prepare-testbed")
    pt_sub = pt.add_subparsers(dest="benchmark", required=True)
    p = pt_sub.add_parser("swebench")
    p.add_argument("instance_id")
    p.add_argument("--dest", required=True)
    p.set_defaults(func=cmd_prepare_testbed)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
