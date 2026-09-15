"""Configuration model for the sandbox (Section V.2 of the subject)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions.

    Uses an allowlist approach: only imports in `authorized_imports` are allowed.
    Everything else is blocked by default.
    """

    authorized_imports: List[str] = Field(default_factory=lambda: [
        "math", "math.*",
        "collections", "collections.*",
        "itertools", "re", "json",
        "typing", "typing.*",
        "functools", "operator",
        "heapq", "bisect", "copy",
        "string", "random",
        "datetime", "datetime.*",
        "array", "cmath",
    ])
    allowed_directories: List[str] = Field(default_factory=lambda: [
        "/testbed", "/tmp/agent"
    ])
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512

    @classmethod
    def load(cls, path: str | Path | None) -> "SandboxConfig":
        """Load a config from a JSON file, or return defaults if `path` is None."""
        if path is None:
            return cls()
        data = json.loads(Path(path).read_text())
        return cls(**data)

    def import_is_allowed(self, module_name: str) -> bool:
        """Check `module_name` (e.g. 'collections.abc') against the allowlist.

        An exact match in `authorized_imports` is allowed. An entry ending in
        '.*' also allows importing that module's submodules.
        """
        if module_name in self.authorized_imports:
            return True
        for entry in self.authorized_imports:
            if entry.endswith(".*"):
                base = entry[:-2]
                if module_name == base or module_name.startswith(base + "."):
                    return True
        return False

    def path_is_allowed(self, path: str | Path) -> bool:
        """Check that `path` resolves inside one of the allowed directories."""
        try:
            resolved = Path(path).resolve()
        except (OSError, RuntimeError):
            return False
        for allowed in self.allowed_directories:
            allowed_resolved = Path(allowed).resolve()
            if resolved == allowed_resolved or allowed_resolved in resolved.parents:
                return True
        return False
