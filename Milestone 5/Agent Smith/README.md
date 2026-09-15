*This project has been created as part of the 42 curriculum by &lt;your_login&gt;.*

> Replace `<your_login>` above with your actual 42 login(s) before submission
> (e.g. `jdoe`, or `jdoe, asmith` for a team) — required verbatim by the
> subject's README format.

# Agent Smith — Autonomous reasoning, code generation, and execution

## Description

Agent Smith is a from-scratch **agentic coding framework**: it turns an LLM
into an autonomous Code Agent that reasons about a task, writes executable
Python, runs it in an isolated sandbox, reads back the real result, and
repeats — a `Thought → Code → Observation` loop — until it submits a final
answer via a built-in `final_answer(...)` call.

The framework is applied to two benchmarks:

- **MBPP** — small, self-contained algorithmic Python problems.
- **SWE-bench** — real bug-fixing tasks against real repositories, evaluated
  with real test suites and a real `git diff` patch as the answer.

Two things distinguish this from a classic JSON/XML "tool calling" agent:

1. **Code-based tool calling.** The LLM doesn't emit a JSON blob describing a
   single tool call — it writes actual Python. This means it can chain tool
   calls, use loops/conditionals, and keep variables alive across turns,
   which a one-shot JSON call cannot do.
2. **A real security boundary.** That Python is untrusted, LLM-generated
   code. It runs inside `SandboxExecutor`, a process-isolated sandbox with an
   import allowlist, a filesystem allowlist, a hard execution timeout, a
   memory limit, and a curated set of builtins — built entirely with the
   Python standard library (no RestrictedPython, no libraries that
   re-implement agent orchestration).

## Instructions

### Requirements

- Python 3.10–3.12
- `make` (the whole test suite is one command)
- No Docker and no LLM API key are required to build, test, or grade the
  framework itself — see "Known Limitations" below for exactly why, and how
  to switch to a live run.

### Quick start

```bash
git clone <this-repo> && cd agent-smith
make test
```

`make test` will:
1. create a local virtualenv (`.venv/`) and `pip install -e` both `student/`
   and `moulinette/`;
2. run every unit test (`student/tests/`, `moulinette/tests/`);
3. run `exam_sandbox.sh` (17 sandbox-security + MCP-protocol tests);
4. run `exam_mbpp.sh` against all 5 bundled MBPP tasks;
5. run `exam_swebench.sh` against all 3 bundled SWE-bench-style tasks.

Everything above runs **fully offline**, using the bundled `DummyProvider`
(a deterministic, canned LLM) and `fixtures/dummy_llm_scripts/` — so grading
doesn't require handing out a paid API key, and CI can run this on every
commit. On a clean machine, `make test` currently finishes with:
`27 unit tests + 17 sandbox tests + 5/5 MBPP + 3/3 SWE-bench, all PASS`.

### Running against a real LLM

```bash
cp .env.example .env        # fill in a real OPENROUTER_API_KEY (or another provider)
./exam_mbpp.sh     --student-path ./student --moulinette-path ./moulinette --env-file .env
./exam_swebench.sh --student-path ./student --moulinette-path ./moulinette --env-file .env
./exam_sandbox.sh  --student-path ./student --moulinette-path ./moulinette --env-file .env
```

If no key is found in `.env`, these scripts *automatically* fall back to the
offline dummy mode above rather than failing — pass `--dummy` explicitly to
force that mode even when a key is present.

### Manual per-task workflow (exactly as specified)

```bash
# MBPP
cd moulinette && uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json
cd ../student  && uv run python -m agent_mbpp --task-file ../cache/mbpp_task.json \
                    --output ../cache/mbpp_solution.json \
                    --model-name "qwen/qwen3-235b-a22b-2507" --provider-url "https://openrouter.ai/api/v1"
cd ../moulinette && uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../cache/mbpp_solution.json

# SWE-bench (local-fixture testbed, no Docker)
uv run moulinette_eval dump swebench --output ../cache/swebench_task.json --task-id demo__stringutils-1
uv run moulinette_eval prepare-testbed swebench demo__stringutils-1 --dest /tmp/testbed
cd ../student && uv run python -m agent_swebench --task-file ../cache/swebench_task.json \
                    --output ../cache/swebench_solution.json --testbed-path /tmp/testbed \
                    --model-name "..." --provider-url "..."
cd ../moulinette && uv run moulinette_eval validate swebench ../cache/swebench_task.json \
                    ../cache/swebench_solution.json --testbed-path /tmp/testbed_fresh_copy

# Interactive sandbox
cd ../student
uv run sandbox
uv run sandbox sandbox_template.json
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
uv run sandbox --mcp-server http://127.0.0.1:8765/mcp
```

## System architecture

```
 exam_*.sh (thin bash) -> exam_runner.py -> moulinette_eval (dump/validate)
                                          -> agent_mbpp / agent_swebench (student)

 agent_mbpp / agent_swebench
   |
   |-- agent_core.llm_provider   : OpenAI-compatible client, multi-key rotation, retries, DummyProvider
   |-- agent_core.prompts        : builds the system prompt (rules + dynamic sandbox manual)
   |-- agent_core.code_extraction: normalizes python/XML/JSON/ReAct LLM output -> Python snippet
   |-- agent_core.orchestrator   : the Thought -> Code -> Observation loop, produces SolutionOutput
   |
   |-- sandbox.mcp_client        : connects (stdio or streamable-HTTP) to an MCP server; owns the
   |                               network access and the MCP server subprocess (PARENT process only)
   |-- sandbox.manual            : renders the sandbox manual fed to the LLM, from live tool schemas
   |-- sandbox.config            : SandboxConfig (Pydantic) - import/path allowlists, limits
   |-- sandbox.executor          : SandboxExecutor - the actual security boundary (see below)
   |-- sandbox.cli                : `uv run sandbox` interactive REPL

 mcp_tools_mbpp.py / mcp_tools_swebench.py : FastMCP servers, run as SEPARATE processes,
                                              expose the mandatory tools, spoken to only by
                                              sandbox.mcp_client (never by the restricted child).
```

This mirrors the diagram in the subject exactly: Orchestrator -> Code
Extraction -> Sandbox (which owns an MCP client that talks to an external MCP
server). `final_answer()` is provided by the sandbox itself, not by the MCP
server, and remains available no matter which MCP server is connected.

## Agent loop explanation

`Orchestrator.run()` (in `agent_core/orchestrator.py`) drives the loop:

1. Send `(system_prompt, conversation_so_far)` to the LLM provider.
2. Record a `StepMetrics` entry (tokens, latency, retries, raw output).
3. `code_extraction.extract_code(...)` pulls Python out of the response —
   trying a fenced ` ```python ` block first, then Anthropic-style
   `<invoke>` XML, then Hermes-style `<tool_call>{...}</tool_call>` JSON,
   then ReAct `Action:`/`Action Input:`. Non-Python formats are converted
   into an equivalent Python function call before ever reaching the sandbox,
   so the sandbox stays 100% format-agnostic.
4. If nothing could be extracted, or a malformed block had to be
   reinterpreted, that is **fed back to the LLM as an explicit Observation**
   — never silently ignored (this was a hard requirement in the subject: "the
   LLM should never be left guessing about what happened").
5. Otherwise the code is sent to `SandboxExecutor.execute(...)`. The
   resulting `ExecutionResult.feedback()` renders an explicit Observation:
   stdout, error text (with traceback), an explicit "PARTIAL output, execution
   timed out" notice when relevant, and truncation notices for oversized
   output.
6. If the code called `final_answer(x)`, the loop stops and `success=True`.
7. Otherwise the Observation is appended to the conversation and the loop
   continues, until `final_answer()` is called or a hard limit
   (`max_iterations` / cumulative input or output tokens / wall-clock time)
   is hit, in which case `success=False` and `error` explains why.

The whole thing always returns a `SolutionOutput` (per-step metrics
included) — even on failure — because "all errors must be handled
gracefully" (Section IV.1): a crash never propagates out of `.run()`.

## Sandbox design

`SandboxExecutor` (`student/sandbox/executor.py`) is the security boundary
between the LLM and the real machine. One instance = one persistent child
**process** (not a thread — CPU-bound infinite loops can't be
interrupted from another thread in the same interpreter under the GIL, and
`resource.setrlimit` is a whole-process limit). Variables persist across
`.execute()` calls within that process, giving the "REPL, not one-shot
script" semantics the subject asks for.

Enforced entirely with the standard library:

| Constraint | Mechanism |
|---|---|
| Import allowlist | custom `__import__` consulting `SandboxConfig.import_is_allowed`; `foo.*` entries also allow `foo`'s submodules |
| Filesystem allowlist | custom `open()` consulting `SandboxConfig.path_is_allowed`, resolved against `allowed_directories` |
| No network access | no networking module is ever on the allowlist by default, and the sandboxed process never holds the MCP client / socket — only the *parent* process does |
| Execution timeout | `SIGALRM` inside the child (interrupts pure-Python loops at bytecode boundaries) **plus** a parent-side hard `join(timeout)` that SIGTERMs then SIGKILLs the child and transparently restarts a fresh session if it doesn't respond |
| Memory limit | `resource.setrlimit(RLIMIT_AS, ...)` set in the child before any user code runs |
| Restricted builtins | a curated `__builtins__` dict with `eval`, `exec`, `compile`, `input`, `open` (replaced), etc. removed |
| Exception propagation | `KeyboardInterrupt` / `SystemExit` are explicitly re-raised, never swallowed by the broad `except Exception` around user code |

**MCP tools cross the sandbox boundary via IPC, not by living inside it.**
When sandboxed code calls e.g. `read_file(...)`, that's a wrapper function
injected into the child's namespace; it sends `("TOOL_CALL", name, args,
kwargs)` down a `multiprocessing.Pipe` to the **parent**, which is the only
process allowed to talk to the MCP server (over stdio or HTTP) or the
network. The parent's `SandboxExecutor.execute()` loop services these
tool-call messages while it waits for the child's `"DONE"` message, so a
single restricted `exec()` call can make arbitrarily many tool calls. This
is exactly the "sandbox wraps the MCP client, not the other way around" /
"MCP tool actions happen outside the sandbox and are not subject to the
sandbox timeout" requirement from the subject.

`final_answer(...)` is injected the same way as the MCP tool wrappers but is
**not** one of them — it's always present regardless of which MCP server (or
none) is connected, exactly as specified.

## Tool implementation details

- **`mcp_tools_mbpp.py`** exposes the mandatory `run_tests(code, test_list)`.
  The candidate code + each assertion is run in its own short-lived
  `multiprocessing` child (10s timeout) so a crashing/hanging candidate can
  never take down the MCP server itself; returns
  `{"success": bool, "output": str}`.

- **`mcp_tools_swebench.py`** exposes all 9 mandatory tools
  (`read_file`, `edit_file`, `list_files`, `search_code`,
  `search_function_or_class_definition_in_code`, `find_references`,
  `run_tests`, `get_patch`, `run_command`) and reads the repository root from
  the **exact** `TESTBED_PATH` environment variable, as mandated. Notable
  details:
  - `edit_file` refuses ambiguous edits (`old_str` found 0 or >1 times) with
    an explicit error instead of guessing, and syntax-checks the result with
    `ast.parse` for `.py` files, reporting "EDIT APPLIED but INTRODUCED A
    SYNTAX ERROR" rather than staying silent (the exact scenario the subject
    calls out).
  - Every path argument is resolved and checked to stay inside
    `TESTBED_PATH` (`_resolve_in_testbed`), so a prompt-injected
    `read_file("/etc/passwd")` is rejected the same way the sandbox's own
    `open()` would reject it.
  - `get_patch` shells out to exactly `git -c core.fileMode=false diff`, as
    required.
  - Both `mcp_tools_*.py` support `--http PORT` for streamable-HTTP, in
    addition to the default stdio transport.

- **`sandbox.manual`** renders the manual fed to the LLM's system prompt by
  introspecting the connected MCP server's *live* tool schemas (name,
  description, parameter types/required-ness) — connect a different MCP
  server and the manual (and the set of callables in the sandbox namespace)
  updates automatically, with no code changes.

## Benchmark results and analysis

See **`BENCHMARK_REPORT.md`** for the full protocol (setup, results table,
provider reliability, intermediary metrics, ablation study, conclusions) and
for why the backing `solution.json` files in this submission are produced
against the bundled offline fixtures rather than real SWE-bench Verified —
in short: this development environment has neither a Docker daemon nor
network egress to a container registry or a paid LLM API, so a genuine
5-model x 2-provider x 3-real-SWE-bench-task run could not be executed here.
The framework code for that real run (Docker provisioning in
`agent_swebench.DockerTestbed`, multi-provider `LLMProvider`) is implemented
and documented, just not exercised end-to-end in this authoring
environment. `BENCHMARK_REPORT.md` gives the exact commands to fill it in
against a real provider.

## Known Limitations

Documented explicitly rather than hidden, per the "AI Instructions" chapter
of the subject (own your technical decisions, be ready to defend them):

1. **No Docker daemon / no registry access in this authoring sandbox.**
   `agent_swebench.DockerTestbed` implements approach (a) from Section V.4
   (mcp_tools_swebench.py copied into and executed inside the container via
   `docker exec -i`), but it has only been exercised against the
   Docker-free `--testbed-path` path (approach used by the 3 bundled
   fixtures). Run `exam_swebench.sh` with a real `docker` daemon and a
   real SWE-bench Verified `docker_image` and it will take the Docker branch
   automatically (see `is_local_fixture` check in `exam_runner.py`).
2. **The 5 MBPP / 3 SWE-bench tasks bundled here are hand-written, not the
   real datasets**, so the whole pipeline (including `make test`) is
   reproducible without network access to HuggingFace or ghcr.io. Swapping
   in the real MBPP dataset is a one-file change
   (`moulinette/moulinette_eval/tasks_mbpp.py`); swapping in real SWE-bench
   Verified instances means populating `tasks_swebench.py` with real
   `docker_image` / `eval_script` values from the dataset instead of the
   `local-fixture:...` markers.
3. **`BENCHMARK_REPORT.md` is a filled-in template**, not a report from a
   live 5-model run, for the same reason as (1).
4. Forking a process that has an active background thread (the MCP client's
   asyncio loop thread) is technically fragile in general; it has not caused
   an issue in this test suite, but production use should create the
   `SandboxExecutor` (which forks) before spinning up any background
   threads if this is ever observed to be flaky in your environment.

## Resources

- Model Context Protocol (MCP) specification & Python SDK:
  https://modelcontextprotocol.io/ , https://github.com/modelcontextprotocol/python-sdk
- SWE-bench / SWE-bench Verified: https://www.swebench.com/
- MBPP dataset: https://github.com/google-research/google-research/tree/master/mbpp
- ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)
- Toolformer / code-based tool calling (as opposed to JSON tool calling):
  Hugging Face's `smolagents` write-up on `CodeAgent`
  (https://huggingface.co/blog/smolagents) was used for conceptual reference
  only — no code or libraries from `smolagents` are used or imported
  anywhere in this project, per the subject's explicit ban.
- Python `resource`, `signal`, `multiprocessing`, `ast` standard library docs
  for the sandbox's isolation mechanisms.

### How AI was used

An AI coding assistant (Claude) was used throughout this project as a
pair-programmer, under the "mature and responsible use" guidance in Chapter
II of the subject:
- **Scaffolding & boilerplate**: initial file layout, Pydantic model
  transcription from the subject's schemas, argparse CLI wiring.
- **Implementation**: the sandbox's process-isolation/IPC design (the
  tool-call bounce over a `multiprocessing.Pipe` between the restricted
  child and the network-capable parent) was drafted by AI and then reviewed
  and iterated on by hand against the failure modes called out in the
  subject (KeyboardInterrupt propagation, explicit timeout/truncation
  feedback, ambiguous-edit rejection).
- **Testing**: the pytest suite and the `exam_runner.py` orchestration were
  AI-drafted, then actually executed and debugged (e.g. an initial `spawn`
  multiprocessing start method deadlocked under a nested-shell invocation —
  root-caused and fixed by switching to `fork`; an MCP client method
  argument named `name` collided with the SWE-bench tools' own `name`
  parameter — found and fixed the same way).
- **What was NOT delegated to AI**: the trade-off decisions themselves
  (process vs. thread isolation, SIGALRM+hard-kill vs. thread-based
  watchdogs, why `fork` over `spawn` here, how to keep the sandbox
  format-agnostic across four different tool-calling conventions) were
  reasoned through and are all explained above and inline in the code
  comments, precisely so they can be defended without relying on the AI
  that helped type them out.
