"""A small, self-contained set of SWE-bench-style tasks.

Real SWE-bench Verified tasks ship as Docker images pulled from ghcr.io, which
this authoring/testing sandbox cannot reach (no network egress to that
registry, no Docker daemon). To keep the framework's SWE-bench code path
(MCP tools, orchestrator, patch generation, moulinette validation) fully
testable offline, three tiny synthetic "instances" are embedded here: a real
git repository with one seeded bug and a real pytest suite each.

For a genuine grading run against real SWE-bench Verified, replace
`prepare_local_testbed` with a step that pulls `docker_image` and swap
`agent_swebench`'s `--testbed-path` flag for the Docker path (see
agent_swebench/__main__.py `DockerTestbed`) -- no other code changes needed,
which is exactly the "sufficiently abstract" requirement in Section V.4/V.6.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

TASKS = {
    "demo__stringutils-1": {
        "instance_id": "demo__stringutils-1",
        "problem_statement": (
            "reverse_words(sentence) in src/stringutils.py is supposed to return the sentence "
            "with word order reversed, e.g. reverse_words('hello world') == 'world hello'. "
            "Currently calling it raises/returns the wrong type. Fix the bug so tests/test_stringutils.py passes."
        ),
        "docker_image": "local-fixture:demo__stringutils-1",
        "hints_text": "list.reverse() mutates in place and returns None.",
        "repo": "demo/stringutils",
    },
    "demo__mathutils-1": {
        "instance_id": "demo__mathutils-1",
        "problem_statement": (
            "is_prime(n) in src/mathutils.py incorrectly classifies some composite numbers as prime "
            "for larger inputs (e.g. is_prime(100) should be False). Fix the bug so "
            "tests/test_mathutils.py passes."
        ),
        "docker_image": "local-fixture:demo__mathutils-1",
        "hints_text": "Check the loop bound used to test divisibility.",
        "repo": "demo/mathutils",
    },
    "demo__listutils-1": {
        "instance_id": "demo__listutils-1",
        "problem_statement": (
            "dedupe_preserve_order(items) in src/listutils.py should remove duplicates while "
            "preserving the first-occurrence order, e.g. dedupe_preserve_order([3,1,3,2,1]) == [3,1,2]. "
            "Fix the bug so tests/test_listutils.py passes."
        ),
        "docker_image": "local-fixture:demo__listutils-1",
        "hints_text": "A plain set() does not preserve insertion order.",
        "repo": "demo/listutils",
    },
}


def eval_script_for(instance_id: str) -> str:
    return f"{sys.executable} -m pytest tests/ -q"


def prepare_local_testbed(instance_id: str, dest: Path) -> Path:
    """Copy the fixture repo to `dest` and git-init it (fresh working tree)."""
    src = FIXTURES_DIR / instance_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(["git", "-c", "user.email=agent@smith.local", "-c", "user.name=Agent Smith",
                     "commit", "-q", "-m", "initial state"], cwd=dest, check=True)
    return dest
