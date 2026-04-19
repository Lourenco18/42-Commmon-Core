"""Data models for call-me-maybe using pydantic for validation."""

from typing import Any, Dict

from pydantic import BaseModel, field_validator


class ParameterDef(BaseModel):
    """Definition of a single function parameter."""

    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure type is a supported JSON schema type.

        Args:
            v: The type string to validate.

        Returns:
            The validated type string.
        """
        allowed = {
            "number", "string", "boolean",
            "integer", "array", "object",
        }
        if v not in allowed:
            raise ValueError(f"Unsupported parameter type: {v!r}")
        return v


class ReturnDef(BaseModel):
    """Definition of a function return type."""

    type: str


class FunctionDefinition(BaseModel):
    """Schema for a callable function exposed to the LLM."""

    name: str
    description: str
    parameters: Dict[str, ParameterDef]
    returns: ReturnDef


class PromptEntry(BaseModel):
    """A single natural-language prompt from the test input file."""

    prompt: str


class FunctionCallResult(BaseModel):
    """Output record: which function to call and with what arguments."""

    prompt: str
    name: str
    parameters: Dict[str, Any]
