#!/usr/bin/env python3
"""Implements the logic behind exam_mbpp.sh / exam_swebench.sh / exam_sandbox.sh.

Kept in one Python module (invoked by the three tiny shell wrappers) because
looping over JSON task files, tracking a pass threshold, and cleaning up temp
testbeds is painful in pure bash and error-prone to get right three times over.

    python3 exam_runner.py mbpp      --student-path ./student --moulinette-path ./moulinette --env-file .env
    python3 exam_runner.py swebench  --student-path ./student --moulinette-path ./moulinette --env-file .env
    python3 exam_runner.py sandbox   --student-path ./student --moulinette-path ./moulinette --env-file .env

Env-loaded settings (all optional -- if no API key is found, the run falls
back to the bundled DummyProvider + canned fixture scripts under
fixtures/dummy_llm_scripts/, so this file, and therefore `make test`, always
works offline):
    OPENROUTER_API_KEY (or whatever --api-key-env points to)
    MODEL_NAME          (default: "dummy/offline-mock")
    PROVIDER_URL         (default: "https://openrouter.ai/api/v1")
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "dummy_llm_scripts"

MBPP_TASK_IDS = [1, 2, 3, 4, 5]
SWEBENCH_INSTANCE_IDS = ["demo__stringutils-1", "demo__mathutils-1", "demo__listutils-1"]


def load_env_file(path: str | None) -> None:
    if not path:
        return
    p = Path(path)
    if not p.exists():
        print(f"[exam_runner] WARNING: env file '{path}' not found, continuing without it.")
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    print(f"    $ {' '.join(cmd)}  (cwd={cwd})")
    return subprocess.run(cmd, cwd=cwd, env=env or os.environ.copy(),
                           capture_output=True, text=True)


def _print_result(proc: subprocess.CompletedProcess):
    if proc.stdout.strip():
        print("      " + proc.stdout.strip().replace("\n", "\n      "))
    if proc.returncode != 0 and proc.stderr.strip():
        print("      STDERR: " + proc.stderr.strip().replace("\n", "\n      "))


# ---------------------------------------------------------------------------
# MBPP exam
# ---------------------------------------------------------------------------


def exam_mbpp(args) -> int:
    student = Path(args.student_path).resolve()
    moulinette = Path(args.moulinette_path).resolve()
    api_key_env = args.api_key_env
    use_dummy = args.dummy or not os.environ.get(api_key_env)
    if use_dummy:
        print(f"[exam_mbpp] No '{api_key_env}' found (or --dummy passed): using the bundled "
              f"DummyProvider + canned fixture scripts. Pass a real key via --env-file for a live run.")

    with tempfile.TemporaryDirectory(prefix="agent_smith_exam_mbpp_") as tmp:
        tmp_path = Path(tmp)
        passed = 0
        for task_id in MBPP_TASK_IDS:
            print(f"\n=== MBPP task {task_id} ===")
            task_file = tmp_path / f"task_{task_id}.json"
            sol_file = tmp_path / f"solution_{task_id}.json"

            dump = run([sys.executable, "-m", "moulinette_eval.cli", "dump", "mbpp",
                        "--output", str(task_file), "--task-id", str(task_id)], cwd=moulinette)
            _print_result(dump)

            agent_cmd = [sys.executable, "-m", "agent_mbpp",
                         "--task-file", str(task_file), "--output", str(sol_file)]
            if use_dummy:
                agent_cmd += ["--dummy-script", str(FIXTURES_DIR / f"mbpp_{task_id}.json")]
            else:
                agent_cmd += ["--model-name", os.environ.get("MODEL_NAME", ""),
                               "--provider-url", os.environ.get("PROVIDER_URL", "https://openrouter.ai/api/v1"),
                               "--api-key-env", api_key_env]
            agent = run(agent_cmd, cwd=student)
            _print_result(agent)

            validate = run([sys.executable, "-m", "moulinette_eval.cli", "validate", "mbpp",
                             str(task_file), str(sol_file)], cwd=moulinette)
            _print_result(validate)
            if validate.returncode == 0:
                passed += 1

        total = len(MBPP_TASK_IDS)
        print(f"\n[exam_mbpp] {passed}/{total} tasks passed (threshold: 4/5)")
        return 0 if passed >= 4 else 1


# ---------------------------------------------------------------------------
# SWE-bench exam
# ---------------------------------------------------------------------------


def exam_swebench(args) -> int:
    student = Path(args.student_path).resolve()
    moulinette = Path(args.moulinette_path).resolve()
    api_key_env = args.api_key_env
    use_dummy = args.dummy or not os.environ.get(api_key_env)
    if use_dummy:
        print(f"[exam_swebench] No '{api_key_env}' found (or --dummy passed): using the bundled "
              f"DummyProvider + canned fixture scripts. Pass a real key via --env-file for a live run.")

    with tempfile.TemporaryDirectory(prefix="agent_smith_exam_swebench_") as tmp:
        tmp_path = Path(tmp)
        passed = 0
        for instance_id in SWEBENCH_INSTANCE_IDS:
            print(f"\n=== SWE-bench task {instance_id} ===")
            task_file = tmp_path / f"task_{instance_id}.json"
            sol_file = tmp_path / f"solution_{instance_id}.json"
            run_testbed = tmp_path / f"testbed_run_{instance_id}"
            verify_testbed = tmp_path / f"testbed_verify_{instance_id}"

            dump = run([sys.executable, "-m", "moulinette_eval.cli", "dump", "swebench",
                        "--output", str(task_file), "--task-id", instance_id], cwd=moulinette)
            _print_result(dump)

            task_data = json.loads(task_file.read_text())
            is_local_fixture = task_data["docker_image"].startswith("local-fixture:")

            if is_local_fixture:
                prep = run([sys.executable, "-m", "moulinette_eval.cli", "prepare-testbed", "swebench",
                            instance_id, "--dest", str(run_testbed)], cwd=moulinette)
                _print_result(prep)
                agent_cmd = [sys.executable, "-m", "agent_swebench",
                             "--task-file", str(task_file), "--output", str(sol_file),
                             "--testbed-path", str(run_testbed)]
            else:
                # Real SWE-bench Verified instance: let agent_swebench provision Docker itself.
                agent_cmd = [sys.executable, "-m", "agent_swebench",
                             "--task-file", str(task_file), "--output", str(sol_file)]

            if use_dummy:
                agent_cmd += ["--dummy-script", str(FIXTURES_DIR / f"swebench_{instance_id}.json")]
            else:
                agent_cmd += ["--model-name", os.environ.get("MODEL_NAME", ""),
                               "--provider-url", os.environ.get("PROVIDER_URL", "https://openrouter.ai/api/v1"),
                               "--api-key-env", api_key_env]
            agent = run(agent_cmd, cwd=student)
            _print_result(agent)

            validate_cmd = [sys.executable, "-m", "moulinette_eval.cli", "validate", "swebench",
                             str(task_file), str(sol_file)]
            if is_local_fixture:
                prep2 = run([sys.executable, "-m", "moulinette_eval.cli", "prepare-testbed", "swebench",
                             instance_id, "--dest", str(verify_testbed)], cwd=moulinette)
                _print_result(prep2)
                validate_cmd += ["--testbed-path", str(verify_testbed)]
            validate = run(validate_cmd, cwd=moulinette)
            _print_result(validate)
            if validate.returncode == 0:
                passed += 1

            # "you are responsible to clean it after your program execution" (Section V.4)
            for d in (run_testbed, verify_testbed):
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)

        total = len(SWEBENCH_INSTANCE_IDS)
        print(f"\n[exam_swebench] {passed}/{total} tasks passed (threshold: 2/3)")
        return 0 if passed >= 2 else 1


# ---------------------------------------------------------------------------
# Sandbox security exam
# ---------------------------------------------------------------------------


def exam_sandbox(args) -> int:
    student = Path(args.student_path).resolve()
    print("\n=== Sandbox security & MCP protocol tests ===")
    proc = run([sys.executable, "-m", "pytest",
                "tests/test_sandbox_security.py", "tests/test_mcp_tools.py", "-v"], cwd=student)
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr)
    print(f"\n[exam_sandbox] {'ALL PASS' if proc.returncode == 0 else 'FAILURES DETECTED'}")
    return proc.returncode


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="exam_runner")
    parser.add_argument("kind", choices=["mbpp", "swebench", "sandbox"])
    parser.add_argument("--student-path", required=True)
    parser.add_argument("--moulinette-path", required=True)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--dummy", action="store_true",
                         help="Force offline DummyProvider mode even if an API key is present")
    args = parser.parse_args(argv)

    load_env_file(args.env_file)

    if args.kind == "mbpp":
        return exam_mbpp(args)
    if args.kind == "swebench":
        return exam_swebench(args)
    return exam_sandbox(args)


if __name__ == "__main__":
    sys.exit(main())
