"""LLM provider abstraction (Section V.6 / IV.2).

Design goals dictated by the subject:
  * support multiple providers/models (any OpenAI-compatible /chat/completions API)
  * support multiple API keys per provider, with rotation on rate-limit/error
  * track usage (tokens, retries, latency, requests)
  * stay abstract enough to switch providers without refactoring the agent loop

`DummyProvider` is not part of the graded deliverable's "LLM provider" per se --
it is a deterministic, offline stand-in used by the test-suite (`make test`) so
that CI / grading can validate the *framework* (extraction, sandbox, orchestrator,
tools) without needing a real, paid or rate-limited API key.
"""
from __future__ import annotations

import itertools
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

import httpx


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    retries: int
    api_url: str
    model_name: str


class LLMProvider:
    """OpenAI-compatible chat-completions client with multi-key rotation."""

    def __init__(self, base_url: str, model_name: str, api_keys: List[str],
                 stop_sequences: Optional[List[str]] = None,
                 max_retries: int = 4, timeout_s: float = 60.0):
        if not api_keys:
            raise ValueError("At least one API key is required")
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._keys = itertools.cycle(api_keys)
        self.stop_sequences = stop_sequences or ["<end_code>", "</tool_call>", "Observation:"]
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self._client = httpx.Client(timeout=timeout_s)

    def _next_key(self) -> str:
        return next(self._keys)

    def generate(self, system_prompt: str, messages: List[dict]) -> LLMResponse:
        """Send one chat-completion request, rotating keys and retrying on failure."""
        payload_messages = [{"role": "system", "content": system_prompt}] + messages
        last_error: Optional[Exception] = None
        retries = 0

        for attempt in range(self.max_retries + 1):
            key = self._next_key()
            start = time.time()
            try:
                resp = self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model_name,
                        "messages": payload_messages,
                        "stop": self.stop_sequences,
                        "temperature": 0.2,
                    },
                )
                elapsed_ms = (time.time() - start) * 1000
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise RuntimeError(f"provider returned {resp.status_code}: {resp.text[:200]}")
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    text=text,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    request_time_ms=elapsed_ms,
                    retries=retries,
                    api_url=self.base_url,
                    model_name=self.model_name,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                retries += 1
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
                continue

        raise RuntimeError(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

    def close(self):
        self._client.close()


class DummyProvider:
    """Deterministic offline provider used by the test-suite.

    It plays back a fixed script of "LLM turns" so the orchestrator, code
    extraction and sandbox can be exercised end-to-end without network access
    or a paid API key. See student/tests for how it's used.
    """

    def __init__(self, script: List[str], model_name: str = "dummy/offline-mock"):
        self._script = list(script)
        self._idx = 0
        self.model_name = model_name
        self.base_url = "local://dummy"

    def generate(self, system_prompt: str, messages: List[dict]) -> LLMResponse:
        start = time.time()
        if self._idx < len(self._script):
            text = self._script[self._idx]
            self._idx += 1
        else:
            text = "final_answer('')\n<end_code>"
        elapsed_ms = (time.time() - start) * 1000
        return LLMResponse(
            text=text,
            input_tokens=len(system_prompt.split()) + sum(len(m["content"].split()) for m in messages),
            output_tokens=len(text.split()),
            request_time_ms=elapsed_ms,
            retries=0,
            api_url=self.base_url,
            model_name=self.model_name,
        )

    def close(self):
        pass


def provider_from_env(base_url: str, model_name: str, key_env_prefix: str = "OPENROUTER_API_KEY") -> LLMProvider:
    """Build an LLMProvider using keys from environment variables.

    Supports multiple keys per provider via `KEY`, `KEY_2`, `KEY_3`, ... so
    students can add capacity without code changes (Section V.6.1).
    """
    keys = []
    if os.environ.get(key_env_prefix):
        keys.append(os.environ[key_env_prefix])
    i = 2
    while os.environ.get(f"{key_env_prefix}_{i}"):
        keys.append(os.environ[f"{key_env_prefix}_{i}"])
        i += 1
    if not keys:
        raise RuntimeError(f"No API key found in environment variable(s) starting with {key_env_prefix}")
    return LLMProvider(base_url=base_url, model_name=model_name, api_keys=keys)
