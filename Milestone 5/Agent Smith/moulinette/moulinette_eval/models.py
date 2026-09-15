"""The moulinette's own copy of the output schema.

Deliberately independent from `student/agent_core/models.py`: the moulinette
must be able to validate ANY student's solution.json without importing their
code.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StepMetrics(BaseModel):
    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = ""
    api_url: str = ""
    model_name: str = ""
    llm_output: str = ""
    sandbox_input: str = ""
    sandbox_output: str = ""
    retries: int = 0


class SolutionOutput(BaseModel):
    task_id: str
    benchmark: str
    success: bool
    solution: str
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List[StepMetrics] = Field(default_factory=list)
    system_prompt: str = ""
    error: Optional[str] = None
    timestamp: str = ""
