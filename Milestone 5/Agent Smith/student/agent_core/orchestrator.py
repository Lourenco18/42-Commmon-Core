"""The central agent loop: Thought -> Code -> Observation -> repeat.

This is the "Agent/Orchestrator" box from the architecture diagram in
Chapter III: it calls the LLM, extracts code, feeds it to the sandbox, reads
observations, and repeats until final_answer() is called or a hard limit
(iterations / tokens / time) is hit.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from agent_core.code_extraction import extract_code
from agent_core.models import SolutionOutput, StepMetrics
from sandbox.executor import SandboxExecutor


@dataclass
class OrchestratorLimits:
    max_iterations: int
    max_input_tokens: int
    max_output_tokens: int
    max_time_seconds: float


class Orchestrator:
    def __init__(self, provider, executor: SandboxExecutor, system_prompt: str,
                 task_id: str, benchmark: str, limits: OrchestratorLimits):
        self.provider = provider
        self.executor = executor
        self.system_prompt = system_prompt
        self.task_id = task_id
        self.benchmark = benchmark
        self.limits = limits

    def run(self) -> SolutionOutput:
        messages: list[dict] = []
        steps: list[StepMetrics] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_requests = 0
        start = time.time()
        error: Optional[str] = None
        success = False
        solution = ""

        for step_idx in range(1, self.limits.max_iterations + 1):
            elapsed = time.time() - start
            if elapsed > self.limits.max_time_seconds:
                error = f"Wall-clock time limit ({self.limits.max_time_seconds}s) exceeded."
                break
            if total_input_tokens > self.limits.max_input_tokens:
                error = f"Cumulative input token limit ({self.limits.max_input_tokens}) exceeded."
                break
            if total_output_tokens > self.limits.max_output_tokens:
                error = f"Cumulative output token limit ({self.limits.max_output_tokens}) exceeded."
                break

            try:
                response = self.provider.generate(self.system_prompt, messages)
            except Exception as exc:  # noqa: BLE001
                error = f"LLM request failed permanently: {exc}"
                break

            total_requests += 1
            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens
            messages.append({"role": "assistant", "content": response.text})

            extraction = extract_code(response.text)

            if extraction.code is None:
                observation = f"[SANDBOX] {extraction.warning}"
                sandbox_input = ""
                sandbox_output = observation
                messages.append({"role": "user", "content": f"Observation:\n{observation}"})
                steps.append(StepMetrics(
                    step=step_idx,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    request_time_ms=response.request_time_ms,
                    api_url=response.api_url,
                    model_name=response.model_name,
                    llm_output=response.text,
                    sandbox_input=sandbox_input,
                    sandbox_output=sandbox_output,
                    retries=response.retries,
                ))
                continue

            result = self.executor.execute(extraction.code)
            feedback = result.feedback()
            if extraction.warning:
                feedback = f"[SANDBOX] Note: {extraction.warning}\n{feedback}"

            steps.append(StepMetrics(
                step=step_idx,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                request_time_ms=response.request_time_ms,
                api_url=response.api_url,
                model_name=response.model_name,
                llm_output=response.text,
                sandbox_input=extraction.code,
                sandbox_output=feedback,
                retries=response.retries,
            ))

            if result.final_answer is not None:
                success = True
                solution = result.final_answer
                break

            messages.append({"role": "user", "content": f"Observation:\n{feedback}"})
        else:
            error = f"Maximum iterations ({self.limits.max_iterations}) reached without final_answer()."

        if not success and error is None:
            error = f"Maximum iterations ({self.limits.max_iterations}) reached without final_answer()."

        return SolutionOutput(
            task_id=self.task_id,
            benchmark=self.benchmark,
            success=success,
            solution=solution,
            iterations=len(steps),
            total_requests=total_requests,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_time_seconds=time.time() - start,
            steps=steps,
            system_prompt=self.system_prompt,
            error=None if success else error,
        )
