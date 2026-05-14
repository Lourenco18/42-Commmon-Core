from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, field_validator


class ParameterSchema(BaseModel):
    """Schema definition for a single function parameter.

    Attributes:
        type: The JSON type of the parameter (number, string, boolean, etc.).
    """

    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate that the type is a supported JSON type.

        Args:
            v: The type string to validate.

        Returns:
            The validated type string.

        Raises:
            ValueError: If the type is not supported.
        """
        allowed = {"number", "string", "boolean",
                   "integer", "array", "object", "null"}
        if v not in allowed:
            raise ValueError(f"Unsupported type '{v}'. Allowed: {allowed}")
        return v


class ReturnSchema(BaseModel):
    type: str


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, ParameterSchema]
    returns: ReturnSchema


class PromptEntry(BaseModel):
    prompt: str


class FunctionCallResult(BaseModel):
    prompt: str
    name: str
    parameters: Dict[str, Any]


class GenerationState(BaseModel):
    phase: str = "start"
    generated_tokens: List[int] = []
    partial_json: str = ""
    current_key: Optional[str] = None
    filled_params: Dict[str, Any] = {}
    expected_params: List[str] = []


class VocabularyEntry(BaseModel):
    token_id: int
    token_str: str


class CLIArgs(BaseModel):
    functions_definition: str = "data/input/functions_definition.json"
    input: str = "data/input/function_calling_tests.json"
    output: str = "data/output/function_calling_results.json"


# Type alias for convenience
FunctionDefinitions = List[FunctionDefinition]
PromptList = List[PromptEntry]
ResultList = List[FunctionCallResult]

# JSON type mapping from schema types to Python types
JSON_TYPE_MAP: Dict[str, type] = {
    "number": float,
    "integer": int,
    "string": str,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}

# Reverse mapping for type coercion
PYTHON_TO_JSON_TYPE: Dict[str, str] = {
    "float": "number",
    "int": "integer",
    "str": "string",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "NoneType": "null",
}

# Valid JSON value prefixes by type
VALID_VALUE_PREFIXES: Dict[str, List[str]] = {
    "number": ["-", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "integer": ["-", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "string": ['"'],
    "boolean": ["t", "f"],
    "null": ["n"],
    "array": ["["],
    "object": ["{"],
}


def coerce_value(value: Any, target_type: str) -> Any:
    """Coerce a parsed JSON value to the target type.

    Args:
        value: The raw parsed value.
        target_type: The expected JSON type string.

    Returns:
        The value coerced to the appropriate Python type.
    """
    if target_type in ("number",):
        return float(value)
    if target_type == "integer":
        return int(value)
    if target_type == "string":
        return str(value)
    if target_type == "boolean":
        return bool(value)
    return value


# Union type for parameter values
ParameterValue = Union[float, int, str, bool, list, dict, None]
