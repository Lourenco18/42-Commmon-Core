"""Constrained decoding engine for guaranteed valid JSON function calls."""

import json
import sys
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from src.models import FunctionDefinition


class ArgState(Enum):
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


def _load_vocabulary(vocab_path: str) -> Tuple[Dict[int, str], Dict[str, int]]:
    try:
        with open(vocab_path, "r", encoding="utf-8") as f:
            raw: Dict[str, int] = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERROR] Cannot load vocabulary: {e}", file=sys.stderr)
        sys.exit(1)

    id_to_token: Dict[int, str] = {v: k for k, v in raw.items()}
    return id_to_token, raw


def _clean(tok_str: str) -> str:
    return tok_str.lstrip("Ġ Ċ▁")


def _mask_to_allowed(logits: np.ndarray, allowed_ids: Set[int]) -> np.ndarray:
    masked = np.full_like(logits, -np.inf)
    for tid in allowed_ids:
        if 0 <= tid < len(logits):
            masked[tid] = logits[tid]
    return masked


def _get_logits_1d(model: Any, input_ids: Any) -> np.ndarray:
    if hasattr(input_ids, "tolist"):
        input_ids = input_ids.flatten().tolist()
    raw = model.get_logits_from_input_ids(input_ids)
    if hasattr(raw, "cpu"):
        raw = raw.cpu()
    if hasattr(raw, "numpy"):
        arr: np.ndarray = raw.numpy()
    else:
        arr = np.array(raw)
    if arr.ndim == 3:
        return arr[0, -1, :]  # type: ignore[no-any-return]
    if arr.ndim == 2:
        return arr[0, :]  # type: ignore[no-any-return]
    return arr  # type: ignore[no-any-return]

def _build_structural_sets(token_to_id: Dict[str, int]) -> Dict[str, Set[int]]:
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


def _build_number_sets(token_to_id: Dict[str, int]) -> Tuple[Set[int], Set[int]]:
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
    fn_names = [fn.name for fn in functions]
    input_ids: List[int] = model.encode(prompt)
    if hasattr(input_ids, "tolist"):
        input_ids = input_ids.flatten().tolist()
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

        exact = next((n for n in fn_names if candidate == n), None)
        if exact:
            return exact

        if not any(n.startswith(candidate) for n in fn_names):
            for name in fn_names:
                if name.startswith(generated_text):
                    suffix = name[len(generated_text):]
                    if chosen_str.startswith(suffix):
                        return name
            break

        generated_text = candidate
        input_ids = input_ids + [chosen_id]

    if fn_names:
        return max(
            fn_names,
            key=lambda n: len([1 for a, b in zip(n, generated_text) if a == b]),
        )
    return functions[0].name


def _coerce_value(raw: str, param_type: str) -> Any:
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
    params = function.parameters
    param_names = list(params.keys())
    input_ids: List[int] = model.encode(prompt)
    if hasattr(input_ids, "tolist"):
        input_ids = input_ids.flatten().tolist()
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
        logits = _get_logits_1d(model, input_ids)
        masked = _mask_to_allowed(logits, allowed)
        tid = int(np.argmax(masked))
        return tid, _clean(id_to_token.get(tid, ""))

    def push(tok_id: int) -> None:
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
            candidates = [k for k in remaining_keys if k.startswith(current_key)]
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
                    best = min(remaining_keys, key=lambda k: abs(len(k) - len(current_key)))
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
            ptype = params[current_key].type if current_key in params else "string"
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
                    result[current_key] = _coerce_value(current_value_buf, params[current_key].type)
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
                    result[current_key] = _coerce_value(current_value_buf, "boolean")
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
    def __init__(self, model: Any) -> None:
        self.model = model
        vocab_path = model.get_path_to_vocab_file()  # <- corrigido
        self.id_to_token, self.token_to_id = _load_vocabulary(vocab_path)
        print(f"[INFO] Vocabulary loaded: {len(self.id_to_token)} tokens", file=sys.stderr)
    def decode_function_name(self, prompt: str, functions: List[FunctionDefinition]) -> str:
        return select_function_name(
            self.model, prompt, functions, self.id_to_token, self.token_to_id
        )

    def decode_arguments(self, prompt: str, function: FunctionDefinition) -> Dict[str, Any]:
        return extract_arguments(
            self.model, prompt, function, self.id_to_token, self.token_to_id
        )
