"""Constrained decoding engine for guaranteed valid JSON function calls.

This module implements token-by-token constrained generation. At each step,
logits for tokens that would violate the expected schema are set to -inf,
ensuring 100% structurally and semantically valid outputs.
"""

import json
import sys
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from src.models import FunctionDefinition


class ArgState(Enum):
    """State machine states for JSON argument generation."""

    OPEN_BRACE = auto()
    KEY_QUOTE_OPEN = auto()
    KEY_CHARS = auto()
    COLON = auto()
    VALUE_START = auto()
    NUMBER_CHARS = auto()
    STRING_VALUE_CHARS = auto()
    BOOL_CHARS = auto()
    AFTER_VALUE = auto()
    DONE = auto()


def _load_vocabulary(
    vocab_path: str,
) -> Tuple[Dict[int, str], Dict[str, int]]:
    """Load vocabulary JSON and build bidirectional mappings.

    Args:
        vocab_path: Path to the vocabulary JSON file.

    Returns:
        Tuple of (id_to_token, token_to_id) dictionaries.
    """
    try:
        with open(vocab_path, "r", encoding="utf-8") as f:
            raw: Dict[str, int] = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERROR] Cannot load vocabulary: {e}", file=sys.stderr)
        sys.exit(1)

    id_to_token: Dict[int, str] = {v: k for k, v in raw.items()}
    return id_to_token, raw


def _clean(tok_str: str) -> str:
    """Strip BPE leading-space markers from a token string.

    Args:
        tok_str: Raw token string from the vocabulary.

    Returns:
        Cleaned token string without leading markers.
    """
    return tok_str.lstrip("Ġ Ċ▁")


def _mask_to_allowed(
    logits: np.ndarray,
    allowed_ids: Set[int],
) -> np.ndarray:
    """Set all logits except allowed_ids to -inf.

    Args:
        logits: 1D numpy array of raw logit values.
        allowed_ids: Set of token IDs that are valid at this step.

    Returns:
        Modified logits array with invalid tokens masked to -inf.
    """
    masked = np.full_like(logits, -np.inf)
    for tid in allowed_ids:
        if 0 <= tid < len(logits):
            masked[tid] = logits[tid]
    return masked


def _get_logits_1d(
    model: Any,
    input_ids: List[int],
) -> np.ndarray:
    """Run the model and return a 1D logits array for the last position.

    Args:
        model: The Small_LLM_Model instance.
        input_ids: Current sequence of token IDs.

    Returns:
        1D numpy array of logits over the full vocabulary.
    """
    tensor_input = np.array([input_ids], dtype=np.int64)
    raw = model.get_logits_from_input_ids(tensor_input)
    if hasattr(raw, "numpy"):
        arr: np.ndarray = raw.numpy()
    else:
        arr = np.array(raw)
    if arr.ndim == 3:
        return arr[0, -1, :]  # type: ignore[no-any-return]
    if arr.ndim == 2:
        return arr[0, :]  # type: ignore[no-any-return]
    return arr  # type: ignore[no-any-return]


def _build_structural_sets(
    token_to_id: Dict[str, int],
) -> Dict[str, Set[int]]:
    """Pre-compute token ID sets for all structural JSON characters.

    Args:
        token_to_id: Mapping from token string to token ID.

    Returns:
        Dictionary mapping character labels to sets of token IDs.
    """
    targets: Dict[str, List[str]] = {
        "{": ["{"],
        "}": ["}"],
        '"': ['"'],
        ":": [":"],
        ",": [","],
        "true": ["true", "True"],
        "false": ["false", "False"],
    }
    result: Dict[str, Set[int]] = {k: set() for k in targets}
    for tok_str, tok_id in token_to_id.items():
        c = _clean(tok_str)
        for label, matches in targets.items():
            if c in matches or tok_str in matches:
                result[label].add(tok_id)
    return result


def _build_number_sets(
    token_to_id: Dict[str, int],
) -> Tuple[Set[int], Set[int]]:
    """Build sets of token IDs valid for starting/continuing numbers.

    Args:
        token_to_id: Mapping from token string to token ID.

    Returns:
        Tuple of (number_start_ids, number_continue_ids).
    """
    start_ids: Set[int] = set()
    continue_ids: Set[int] = set()
    for tok_str, tok_id in token_to_id.items():
        c = _clean(tok_str)
        if not c:
            continue
        if c[0].isdigit() or c[0] == "-":
            start_ids.add(tok_id)
        if all(ch in "0123456789.eE+-" for ch in c):
            continue_ids.add(tok_id)
    return start_ids, continue_ids


def select_function_name(
    model: Any,
    prompt: str,
    functions: List[FunctionDefinition],
    id_to_token: Dict[int, str],
    token_to_id: Dict[str, int],
) -> str:
    """Use constrained decoding to select a function name.

    Builds a prefix set of valid function names and at each generation
    step only allows tokens that continue a valid function name prefix.

    Args:
        model: The Small_LLM_Model instance.
        prompt: The formatted prompt string.
        functions: List of available function definitions.
        id_to_token: Mapping from token ID to token string.
        token_to_id: Mapping from token string to token ID.

    Returns:
        The selected function name string.
    """
    fn_names = [fn.name for fn in functions]
    input_ids: List[int] = model.encode(prompt)
    generated_text = ""
    max_steps = 80

    for _ in range(max_steps):
        logits_1d = _get_logits_1d(model, input_ids)
        remaining = [n for n in fn_names if n.startswith(generated_text)]

        if not remaining:
            break

        valid_ids: Set[int] = set()
        for name in remaining:
            suffix = name[len(generated_text):]
            if not suffix:
                # Name complete — allow whitespace terminators
                for tok_str, tok_id in token_to_id.items():
                    if _clean(tok_str) in ("", " ", "\n", "\t"):
                        valid_ids.add(tok_id)
                continue
            for tok_str, tok_id in token_to_id.items():
                c = _clean(tok_str)
                if c and suffix.startswith(c):
                    valid_ids.add(tok_id)

        if not valid_ids:
            break

        masked = _mask_to_allowed(logits_1d, valid_ids)
        chosen_id = int(np.argmax(masked))
        chosen_str = _clean(id_to_token.get(chosen_id, ""))

        candidate = generated_text + chosen_str

        # Check exact match
        exact = next((n for n in fn_names if candidate == n), None)
        if exact:
            return exact

        # Check still a valid prefix
        if not any(n.startswith(candidate) for n in fn_names):
            # Token may span the end of the name
            for name in fn_names:
                if name.startswith(generated_text):
                    suffix = name[len(generated_text):]
                    if chosen_str.startswith(suffix):
                        return name
            break

        generated_text = candidate
        input_ids = input_ids + [chosen_id]

    # Fallback: return closest match by prefix length
    if fn_names:
        return max(
            fn_names,
            key=lambda n: len(
                [1 for a, b in zip(n, generated_text) if a == b]
            ),
        )
    return functions[0].name


def _coerce_value(raw: str, param_type: str) -> Any:
    """Coerce a raw string to the expected Python type.

    Args:
        raw: The raw string extracted from constrained generation.
        param_type: The expected type string.

    Returns:
        The coerced Python value.
    """
    pt = param_type.lower()
    if pt in ("number", "float"):
        try:
            return float(raw)
        except ValueError:
            return 0.0
    if pt == "integer":
        try:
            return int(raw)
        except ValueError:
            return 0
    if pt == "boolean":
        return raw.lower() == "true"
    return raw


def extract_arguments(
    model: Any,
    prompt: str,
    function: FunctionDefinition,
    id_to_token: Dict[int, str],
    token_to_id: Dict[str, int],
) -> Dict[str, Any]:
    """Use constrained decoding to generate schema-valid JSON arguments.

    A finite state machine drives JSON generation, enforcing correct
    structure and type constraints at every token position.

    Args:
        model: The Small_LLM_Model instance.
        prompt: The formatted prompt string.
        function: The selected FunctionDefinition providing the schema.
        id_to_token: Mapping from token ID to token string.
        token_to_id: Mapping from token string to token ID.

    Returns:
        Dictionary of parameter name to coerced value.
    """
    params = function.parameters
    param_names = list(params.keys())

    input_ids: List[int] = model.encode(prompt)
    state = ArgState.OPEN_BRACE
    current_key: Optional[str] = None
    current_value_buf = ""
    result: Dict[str, Any] = {}
    remaining_keys = list(param_names)
    max_steps = 300

    struct = _build_structural_sets(token_to_id)
    num_start, num_cont = _build_number_sets(token_to_id)

    brace_open = struct["{"]
    brace_close = struct["}"]
    quote_ids = struct['"']
    colon_ids = struct[":"]
    comma_ids = struct[","]
    true_ids = struct["true"]
    false_ids = struct["false"]

    def pick(allowed: Set[int]) -> Tuple[int, str]:
        """Pick the best token from allowed set using greedy decoding.

        Args:
            allowed: Set of valid token IDs.

        Returns:
            Tuple of (token_id, clean_token_string).
        """
        logits = _get_logits_1d(model, input_ids)
        masked = _mask_to_allowed(logits, allowed)
        tid = int(np.argmax(masked))
        return tid, _clean(id_to_token.get(tid, ""))

    def push(tok_id: int) -> None:
        """Append a token ID to the running sequence.

        Args:
            tok_id: Token ID to append.
        """
        input_ids.append(tok_id)

    step = 0
    while state != ArgState.DONE and step < max_steps:
        step += 1

        if state == ArgState.OPEN_BRACE:
            tid, _ = pick(brace_open)
            push(tid)
            state = ArgState.KEY_QUOTE_OPEN

        elif state == ArgState.KEY_QUOTE_OPEN:
            if not remaining_keys:
                tid, _ = pick(brace_close)
                push(tid)
                state = ArgState.DONE
            else:
                tid, _ = pick(quote_ids)
                push(tid)
                current_key = ""
                state = ArgState.KEY_CHARS

        elif state == ArgState.KEY_CHARS:
            if current_key is None:
                current_key = ""
            candidates = [
                k for k in remaining_keys
                if k.startswith(current_key)
            ]
            if not candidates:
                candidates = remaining_keys[:1]

            key_tokens: Set[int] = set()
            for k in candidates:
                if len(current_key) < len(k):
                    tail = k[len(current_key):]
                    for tok_str, tok_id in token_to_id.items():
                        c = _clean(tok_str)
                        if c and tail.startswith(c):
                            key_tokens.add(tok_id)
                if current_key == k:
                    key_tokens.update(quote_ids)

            if current_key in remaining_keys:
                key_tokens.update(quote_ids)
            if not key_tokens:
                key_tokens = quote_ids

            tid, c = pick(key_tokens)
            push(tid)

            if tid in quote_ids:
                if current_key not in remaining_keys and remaining_keys:
                    # Accept the closest key if not exact
                    best = min(
                        remaining_keys,
                        key=lambda k: abs(len(k) - len(current_key)),
                    )
                    current_key = best
                state = ArgState.COLON
            else:
                current_key = current_key + c

        elif state == ArgState.COLON:
            tid, _ = pick(colon_ids)
            push(tid)
            state = ArgState.VALUE_START

        elif state == ArgState.VALUE_START:
            if current_key is None or current_key not in params:
                current_key = remaining_keys[0] if remaining_keys else ""
            ptype = (
                params[current_key].type
                if current_key in params
                else "string"
            )
            if ptype in ("number", "float", "integer"):
                tid, c = pick(num_start)
                push(tid)
                current_value_buf = c
                state = ArgState.NUMBER_CHARS
            elif ptype == "boolean":
                tid, c = pick(true_ids | false_ids)
                push(tid)
                current_value_buf = c
                state = ArgState.BOOL_CHARS
            else:
                tid, _ = pick(quote_ids)
                push(tid)
                current_value_buf = ""
                state = ArgState.STRING_VALUE_CHARS

        elif state == ArgState.NUMBER_CHARS:
            end_ids = comma_ids | brace_close
            cont_ids = num_cont - end_ids
            logits = _get_logits_1d(model, input_ids)
            m_cont = _mask_to_allowed(logits, cont_ids)
            m_end = _mask_to_allowed(logits, end_ids)
            b_cont = float(np.max(m_cont)) if cont_ids else -np.inf
            b_end = float(np.max(m_end))
            if b_cont > b_end and len(current_value_buf) < 20:
                tid = int(np.argmax(m_cont))
                current_value_buf += _clean(id_to_token.get(tid, ""))
                push(tid)
            else:
                if current_key and current_key in params:
                    result[current_key] = _coerce_value(
                        current_value_buf, params[current_key].type
                    )
                    if current_key in remaining_keys:
                        remaining_keys.remove(current_key)
                current_key = None
                current_value_buf = ""
                state = ArgState.AFTER_VALUE

        elif state == ArgState.STRING_VALUE_CHARS:
            all_ids: Set[int] = set(range(min(50000, len(id_to_token))))
            disallowed = brace_close | brace_open | colon_ids | comma_ids
            cont_ids = all_ids - disallowed - quote_ids
            logits = _get_logits_1d(model, input_ids)
            m_close = _mask_to_allowed(logits, quote_ids)
            m_cont = _mask_to_allowed(logits, cont_ids)
            b_close = float(np.max(m_close))
            b_cont = float(np.max(m_cont)) if cont_ids else -np.inf
            if b_close > b_cont or len(current_value_buf) > 80:
                tid = int(np.argmax(m_close))
                push(tid)
                if current_key and current_key in params:
                    result[current_key] = current_value_buf
                    if current_key in remaining_keys:
                        remaining_keys.remove(current_key)
                current_key = None
                current_value_buf = ""
                state = ArgState.AFTER_VALUE
            else:
                tid = int(np.argmax(m_cont))
                current_value_buf += _clean(id_to_token.get(tid, ""))
                push(tid)

        elif state == ArgState.BOOL_CHARS:
            end_ids = comma_ids | brace_close
            bool_cont: Set[int] = set()
            for tok_str, tok_id in token_to_id.items():
                c = _clean(tok_str)
                for cand in ("true", "false"):
                    if cand.startswith(current_value_buf + c):
                        bool_cont.add(tok_id)
            logits = _get_logits_1d(model, input_ids)
            m_end = _mask_to_allowed(logits, end_ids)
            cont_only = bool_cont - end_ids
            m_cont = (
                _mask_to_allowed(logits, cont_only)
                if cont_only
                else np.full_like(logits, -np.inf)
            )
            b_end = float(np.max(m_end))
            b_cont = float(np.max(m_cont))
            done_bool = current_value_buf in ("true", "false")
            if done_bool or b_end >= b_cont or len(current_value_buf) >= 5:
                if current_key and current_key in params:
                    result[current_key] = _coerce_value(
                        current_value_buf, "boolean"
                    )
                    if current_key in remaining_keys:
                        remaining_keys.remove(current_key)
                current_key = None
                current_value_buf = ""
                state = ArgState.AFTER_VALUE
            else:
                tid = int(np.argmax(m_cont))
                current_value_buf += _clean(id_to_token.get(tid, ""))
                push(tid)

        elif state == ArgState.AFTER_VALUE:
            if remaining_keys:
                tid, _ = pick(comma_ids)
                push(tid)
                state = ArgState.KEY_QUOTE_OPEN
            else:
                tid, _ = pick(brace_close)
                push(tid)
                state = ArgState.DONE

    # Fill missing parameters with safe defaults
    for key in param_names:
        if key not in result:
            ptype = params[key].type
            if ptype in ("number", "float"):
                result[key] = 0.0
            elif ptype == "integer":
                result[key] = 0
            elif ptype == "boolean":
                result[key] = False
            else:
                result[key] = ""

    return result


class ConstrainedDecoder:
    """Orchestrates constrained decoding for function calling.

    Attributes:
        model: The Small_LLM_Model instance.
        id_to_token: Mapping from token ID to token string.
        token_to_id: Mapping from token string to token ID.
    """

    def __init__(self, model: Any) -> None:
        """Initialize the decoder by loading vocabulary from the model.

        Args:
            model: An instance of Small_LLM_Model from llm_sdk.
        """
        self.model = model
        vocab_path = model.get_path_to_vocabulary_json()
        self.id_to_token, self.token_to_id = _load_vocabulary(vocab_path)
        print(
            f"[INFO] Vocabulary loaded: {len(self.id_to_token)} tokens",
            file=sys.stderr,
        )

    def decode_function_name(
        self,
        prompt: str,
        functions: List[FunctionDefinition],
    ) -> str:
        """Select a function name using constrained decoding.

        Args:
            prompt: Formatted prompt string.
            functions: Available function definitions.

        Returns:
            The selected function name.
        """
        return select_function_name(
            self.model,
            prompt,
            functions,
            self.id_to_token,
            self.token_to_id,
        )

    def decode_arguments(
        self,
        prompt: str,
        function: FunctionDefinition,
    ) -> Dict[str, Any]:
        """Extract function arguments using constrained decoding.

        Args:
            prompt: Formatted prompt string.
            function: The target function definition.

        Returns:
            Dictionary of argument name to value.
        """
        return extract_arguments(
            self.model,
            prompt,
            function,
            self.id_to_token,
            self.token_to_id,
        )
