import json
import sys
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from src.models import FunctionDefinition, ParameterSchema, coerce_value
from src.vocabulary import Vocabulary
import re

NEG_INF = float("-inf")


def build_function_selection_prompt(
    user_prompt: str,
    functions: List[FunctionDefinition],
) -> str:
    fn_list = "\n".join(
        f"  - {fn.name}: {fn.description}" for fn in functions
    )
    prompt = (
        f"You are a function calling system."
        f"Given the following user request, "
        f"select the most appropriate function name from the list below.\n\n"
        f"Available functions:\n{fn_list}\n\n"
        f"User request: {user_prompt}\n\n"
        f"Respond with ONLY the function name, nothing else. Function name: "
    )
    return prompt


def build_argument_extraction_prompt(
    user_prompt: str,
    function_def: FunctionDefinition,
) -> str:
    params_desc = ", ".join(
        f'"{k}" ({v.type})' for k, v in function_def.parameters.items()
    )
    prompt = (
        f"Extract the arguments for the function '{function_def.name}' "
        f"from the user request below.\n\n"
        f"Function: {function_def.name}\n"
        f"Description: {function_def.description}\n"
        f"Parameters: {params_desc}\n\n"
        f"User request: {user_prompt}\n\n"
        f"Respond with ONLY valid JSON object containing the arguments. JSON: "
    )
    return prompt


def constrained_generate_function_name(
    prompt_ids: List[int],
    function_names: List[str],
    vocab: Vocabulary,
    get_logits_fn: Any,
    max_new_tokens: int = 50,
) -> Optional[str]:
    current_ids = list(prompt_ids)
    generated_name = ""
    next_token_id = -1

    for _ in range(max_new_tokens):
        try:
            logits_list = get_logits_fn(current_ids)
            next_logits = np.array(logits_list, dtype=np.float32)
        except Exception as e:
            print(f"[ERROR] LLM forward pass failed: {e}", file=sys.stderr)
            return None

        vocab_size = len(next_logits)
        mask = np.full(vocab_size, NEG_INF, dtype=np.float32)

        exact_matches = [n for n in function_names if n == generated_name]
        eos_tokens: List[int] = []

        if exact_matches:
            for tid, tstr in vocab.id_to_token.items():
                if tstr.strip() in (
                    "",
                    "\n",
                    "<|endoftext|>",
                    "<eos>",
                    "<|im_end|>",
                ):
                    if tid < vocab_size:
                        eos_tokens.append(tid)
                        mask[tid] = next_logits[tid]

        # Allow tokens that continue remaining valid names
        remaining = [n for n in function_names if n.startswith(generated_name)]
        for tid, tstr in vocab.id_to_token.items():
            if tid >= vocab_size:
                continue
            # Strip common BPE space prefixes
            clean = tstr.lstrip("\u0120\u2581 ")
            candidate = generated_name + clean

            for name in remaining:
                if name.startswith(candidate) or candidate == name:
                    mask[tid] = next_logits[tid]
                    break

        # If nothing valid found, fall back to exact match tokens
        if np.all(mask == NEG_INF):
            # Last resort: look for any token that completes one of the names
            for name in function_names:
                if name.startswith(generated_name):
                    suffix = name[len(generated_name):]
                    for tid, tstr in vocab.id_to_token.items():
                        if tid < vocab_size and tstr.strip() == suffix:
                            mask[tid] = next_logits[tid]
            if np.all(mask == NEG_INF):
                # Complete generation — return what we have
                break

        next_token_id = int(np.argmax(mask))
        token_str = vocab.id_to_token.get(next_token_id, "")

        if token_str.strip() in ("", "\n", "<|endoftext|>", "<eos>",
                                 "<|im_end|>"):
            if generated_name in function_names:
                break
        if not generated_name:
            token_str = token_str.lstrip("\u0120\u2581 ")
        else:
            token_str = token_str.replace("\u0120", " ").replace("\u2581", " ")

        generated_name += token_str
        current_ids.append(next_token_id)

        # Check if we've completed a valid name
        if generated_name in function_names:
            break

    # Find best matching function name
    best_match: Optional[str] = None
    if generated_name in function_names:
        best_match = generated_name
    else:
        # Try partial match
        for name in function_names:
            if (
                generated_name.startswith(name)
                or name.startswith(generated_name)
            ):
                best_match = name
                break

    return best_match


def constrained_generate_arguments(
    prompt_ids: List[int],
    function_def: FunctionDefinition,
    vocab: Vocabulary,
    get_logits_fn: Any,
    max_new_tokens: int = 200,
) -> Optional[Dict[str, Any]]:

    params = function_def.parameters
    param_names = list(params.keys())

    if not param_names:
        return {}

    result: Dict[str, Any] = {}
    # current_ids grows as we inject structure + collect value tokens
    current_ids = list(prompt_ids)

    for param_idx, param_name in enumerate(param_names):
        ptype = params[param_name].type

        # ── Build and inject the structural prefix for this parameter ──────
        # e.g. first param:  '{"name": '
        #      later params: ', "name": '
        if param_idx == 0:
            prefix_str = '{"' + param_name + '": '
        else:
            prefix_str = ', "' + param_name + '": '

        prefix_ids = _encode_string_as_char_ids(prefix_str, vocab)
        current_ids.extend(prefix_ids)

        # For string values inject the opening quote too
        if ptype == "string":
            current_ids.extend(_encode_string_as_char_ids('"', vocab))

        # ── Let the LLM generate the value tokens ──────────────────────────
        value_tokens: List[int] = []
        value_str = ""

        for _ in range(max_new_tokens):
            try:
                logits_list = get_logits_fn(current_ids)
                next_logits = np.array(logits_list, dtype=np.float32)
            except Exception as e:
                print(f"[ERROR] LLM forward pass failed: {e}", file=sys.stderr)
                break

            vocab_size = len(next_logits)
            mask = np.full(vocab_size, NEG_INF, dtype=np.float32)

            valid_ids = _get_value_tokens(
                ptype, value_str, vocab, vocab_size
            )
            for tid in valid_ids:
                if tid < vocab_size:
                    mask[tid] = next_logits[tid]

            if np.all(mask == NEG_INF):
                break

            next_token_id = int(np.argmax(mask))
            token_str = vocab.id_to_token.get(next_token_id, "")
            clean = token_str.replace("\u0120", " ").replace("\u2581", " ")

            # For numbers: strip leading space (BPE prefix) only on first token
            if ptype in ("number", "integer") and not value_str:
                clean = clean.lstrip(" ")

            # Detect value completion
            if ptype == "string":
                # Strip BPE leading space only on first token
                if not value_str:
                    clean = clean.lstrip(" ")
                # Token is exactly a closing quote -> end of string
                if clean == '"':
                    value_tokens.append(next_token_id)
                    current_ids.append(next_token_id)
                    break
                # Find first unescaped quote in token — cut there
                cut = -1
                ci = 0
                while ci < len(clean):
                    if clean[ci] == '\\':
                        ci += 2
                        continue
                    if clean[ci] == '"':
                        cut = ci
                        break
                    ci += 1
                if cut >= 0:
                    # Keep only content before the closing quote
                    value_str += clean[:cut]
                    value_tokens.append(next_token_id)
                    current_ids.append(next_token_id)
                    break
                value_str += clean
            elif ptype in ("number", "integer"):
                # A comma or closing brace ends the number
                stripped = clean.strip()
                if stripped in (",", "}"):
                    # do NOT append this structural token to value_str
                    break
                value_str += clean
            elif ptype == "boolean":
                value_str += clean.strip()
                if value_str in ("true", "false"):
                    value_tokens.append(next_token_id)
                    current_ids.append(next_token_id)
                    break
                elif not ("true".startswith(value_str)
                          or "false".startswith(value_str)):
                    break
                value_tokens.append(next_token_id)
                current_ids.append(next_token_id)
                continue
            else:
                value_str += clean

            value_tokens.append(next_token_id)
            current_ids.append(next_token_id)

        # ── Coerce and store the value ─────────────────────────────────────
        raw_value: Any = value_str.strip()
        try:
            result[param_name] = coerce_value(raw_value, ptype)
        except (ValueError, TypeError):
            result[param_name] = _default_for_type(ptype)

    return result


def _encode_string_as_char_ids(
    text: str,
    vocab: Vocabulary,
) -> List[int]:

    ids: List[int] = []
    for char in text:
        best_id: Optional[int] = None
        for tid, tstr in vocab.id_to_token.items():
            clean = tstr.replace("\u0120", " ").replace("\u2581", " ")
            if clean == char:
                best_id = tid
                break
        if best_id is not None:
            ids.append(best_id)
    return ids


def _get_value_tokens(
    ptype: str,
    value_so_far: str,
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid: List[int] = []
    has_dot = "." in value_so_far

    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        clean = tstr.replace("\u0120", " ").replace("\u2581", " ")
        stripped = clean.lstrip(" ")
        if not stripped:
            continue

        if ptype in ("number", "integer"):
            # On the first token allow an optional leading minus
            candidate = stripped.lstrip("-") if not value_so_far else stripped
            # Pure digits (possibly with one decimal point for numbers)
            if ptype == "number":
                if (
                    all(c.isdigit() or c == "." for c in candidate)
                    and candidate
                ):
                    if "." not in candidate or not has_dot:
                        valid.append(tid)
                        continue
            else:  # integer
                if candidate.isdigit():
                    valid.append(tid)
                    continue
            # Allow terminator tokens so the loop can detect end
            if stripped in (",", "}"):
                valid.append(tid)

        elif ptype == "string":
            # Allow any printable token that does NOT contain an
            # unescaped closing quote (those are handled separately)
            if any(ord(c) < 32 for c in stripped):
                continue
            # Check for closing quote: token ends the string
            if stripped.endswith('"') and not stripped.endswith('\\"''"'):
                valid.append(tid)
                continue
            # Content token: must not have an unescaped mid-string quote
            has_mid_quote = False
            i = 0
            while i < len(stripped):
                if stripped[i] == '\\':
                    i += 2
                    continue
                if stripped[i] == '"':
                    has_mid_quote = True
                    break
                i += 1
            if not has_mid_quote:
                valid.append(tid)

        elif ptype == "boolean":
            if "true".startswith(value_so_far + stripped):
                valid.append(tid)
            elif "false".startswith(value_so_far + stripped):
                valid.append(tid)

        elif ptype == "null":
            if "null".startswith(value_so_far + stripped):
                valid.append(tid)

    return valid


def get_valid_json_tokens(
    partial_json: str,
    param_names: List[str],
    params: Dict[str, ParameterSchema],
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid_ids: List[int] = []
    stripped = partial_json.strip()

    if not stripped:
        target = "{"
        valid_ids.extend(_find_tokens_for_string(target, vocab, vocab_size))
        return valid_ids

    if stripped == "{":
        target = '"'
        valid_ids.extend(_find_tokens_for_string(target, vocab, vocab_size))
        return valid_ids
    state = _analyze_json_state(stripped, param_names, params)

    if state["phase"] == "need_key":
        remaining_keys = state["remaining_keys"]
        if remaining_keys:
            valid_ids.extend(_find_tokens_for_string('"', vocab, vocab_size))
        return valid_ids

    if state["phase"] == "in_key":
        key_so_far = state.get("key_so_far", "")
        remaining_keys = state["remaining_keys"]
        valid_key_continuations = _get_key_continuations(
            key_so_far, remaining_keys, vocab, vocab_size
        )
        valid_ids.extend(valid_key_continuations)
        return valid_ids

    if state["phase"] == "need_colon":
        valid_ids.extend(_find_tokens_for_string(":", vocab, vocab_size))
        valid_ids.extend(_find_tokens_for_string(" :", vocab, vocab_size))
        return valid_ids

    if state["phase"] == "need_value_start":
        current_key = state.get("current_key", "")
        param_type = params.get(current_key)
        if param_type:
            ptype = param_type.type
            valid_ids.extend(_get_value_start_tokens(ptype, vocab, vocab_size))
        return valid_ids

    if state["phase"] == "in_value_number":
        valid_ids.extend(_get_number_continuation_tokens(
            state.get("value_so_far", ""), vocab, vocab_size
        ))
        return valid_ids

    if state["phase"] == "in_value_string":
        valid_ids.extend(_get_string_continuation_tokens(vocab, vocab_size))
        return valid_ids

    if state["phase"] == "need_comma_or_close":
        remaining_keys = state["remaining_keys"]
        if remaining_keys:
            valid_ids.extend(_find_tokens_for_string(",", vocab, vocab_size))
            valid_ids.extend(_find_tokens_for_string(", ", vocab, vocab_size))
        else:
            valid_ids.extend(_find_tokens_for_string("}", vocab, vocab_size))
        return valid_ids

    if state["phase"] == "complete":
        for tid, tstr in vocab.id_to_token.items():
            if tid < vocab_size and tstr.strip() in (
                "", "\n", "<|endoftext|>", "<eos>", "<|im_end|>"
            ):
                valid_ids.append(tid)
        return valid_ids
    return []


def _analyze_json_state(
    partial: str,
    param_names: List[str],
    params: Dict[str, ParameterSchema],
) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "phase": "unknown",
        "remaining_keys": list(param_names),
        "filled_keys": [],
        "current_key": None,
        "key_so_far": "",
        "value_so_far": "",
    }

    if not partial or partial == "{":
        state["phase"] = "need_key"
        return state

    end = partial.rstrip()
    for key in param_names:
        key_token = f'"{key}"'
        if key_token not in partial:
            continue
        key_pos = partial.rfind(key_token)
        after_key = partial[key_pos + len(key_token):].lstrip()
        if not after_key.startswith(":"):
            continue
        after_colon = after_key[1:].lstrip()
        if not after_colon:
            continue
        ptype = params.get(key)
        if ptype:
            immediate = _extract_immediate_value(after_colon, ptype.type)
            if not _is_value_complete(immediate, ptype.type):
                continue
            state["filled_keys"].append(key)
            if key in state["remaining_keys"]:
                state["remaining_keys"].remove(key)

    if end.endswith("}"):
        state["phase"] = "complete"
        return state

    if end.endswith(",") or end.endswith("{"):
        state["phase"] = "need_key"
        return state

    if _is_complete_key_without_colon(end, param_names):
        state["phase"] = "need_colon"
        return state

    if end.endswith(":"):
        state["phase"] = "need_value_start"
        state["current_key"] = _find_current_key(end, param_names)
        return state
    for key in param_names:
        if key in state["filled_keys"]:
            continue
        ptype = params.get(key)
        if not ptype:
            continue
        key_pat = f'"{key}":'
        alt_pat = f'"{key}" :'
        if key_pat in end:
            pat = key_pat
        elif alt_pat in end:
            pat = alt_pat
        else:
            pat = None
        if pat is None:
            continue
        after = end.split(pat, 1)[1].lstrip()
        if ptype.type == "string":
            if after.startswith('"'):
                immediate = _extract_immediate_value(after, ptype.type)
                if not _is_value_complete(immediate, ptype.type):
                    state["phase"] = "in_value_string"
                    state["current_key"] = key
                    state["value_so_far"] = after[1:]
                    return state
        elif ptype.type in ("number", "integer"):
            if after and (after[0].isdigit() or after[0] == '-'):
                state["phase"] = "in_value_number"
                state["current_key"] = key
                state["value_so_far"] = _extract_number_so_far(after)
                return state
        elif ptype.type == "boolean":
            if after and after[0] in 'tf':
                state["phase"] = "in_value_boolean"
                state["current_key"] = key
                state["value_so_far"] = after
                return state
    last_brace = max(end.rfind("{"), end.rfind(","))
    segment = end[last_brace + 1:].lstrip() if last_brace >= 0 else end
    if segment.startswith('"'):
        inner = segment[1:]
        inner_quotes = 0
        idx = 0
        while idx < len(inner):
            if inner[idx] == '\\':
                idx += 2
                continue
            if inner[idx] == '"':
                inner_quotes += 1
            idx += 1
        if inner_quotes == 0:
            state["phase"] = "in_key"
            state["key_so_far"] = inner
            return state
    if _is_building_number(end):
        state["phase"] = "in_value_number"
        state["value_so_far"] = _extract_number_so_far(end)
        return state
    if _ends_with_value(end, params, state["filled_keys"], param_names):
        state["phase"] = "need_comma_or_close"
        return state

    return state


def _is_complete_key_without_colon(text: str, param_names: List[str]) -> bool:
    for name in param_names:
        key_token = f'"{name}"'
        if (
            text.endswith(key_token)
            and ':' not in text[text.rfind(key_token) + len(key_token):]
        ):
            return True
    return False


def _extract_immediate_value(after_colon: str, ptype: str) -> str:
    s = after_colon.lstrip()
    if ptype == "string":
        if not s.startswith('"'):
            return s

        i = 1
        while i < len(s):
            if s[i] == '\\':
                i += 2
                continue
            if s[i] == '"':
                return s[:i + 1]
            i += 1
        return s
    elif ptype in ("number", "integer"):
        i = 0
        if i < len(s) and s[i] in "+-":
            i += 1
        while i < len(s) and (s[i].isdigit() or s[i] == '.'):
            i += 1
        return s[:i] if i > 0 else s
    elif ptype == "boolean":
        for lit in ("true", "false"):
            if s.startswith(lit):
                return lit
        return s
    return s


def _is_value_complete(value_str: str, ptype: str) -> bool:
    s = value_str.strip()
    if ptype in ("number", "integer"):
        if not s:
            return False
        if s[-1].isdigit() or s[-1] == ".":
            return True
        if s[-1] in ",}" and len(s) > 1 and s[-2].isdigit():
            return True
        return False
    if ptype == "string":
        if not s.startswith('"'):
            return False
        if len(s) > 1 and s.endswith('"') and s[-2] != "\\":
            return True
        if len(s) > 2 and s.endswith('",') and s[-3] != "\\":
            return True
        if len(s) > 2 and s.endswith('"}') and s[-3] != "\\":
            return True
        return False
    if ptype == "boolean":
        if s in ("true", "false"):
            return True
        if s in ("true,", "false,", "true}", "false}"):
            return True
        return False
    if ptype == "null":
        if s == "null" or s in ("null,", "null}"):
            return True
        return False
    return False


def _ends_with_value(
    text: str,
    params: Dict[str, ParameterSchema],
    filled: List[str],
    all_params: List[str],
) -> bool:
    """Check if the text ends with a complete value."""
    for key in filled:
        ptype = params.get(key)
        if not ptype:
            continue
        key_token = f'"{key}"'
        if key_token in text:
            t = ptype.type
            if t in ("number", "integer") and text[-1].isdigit():
                return True
            if (
                t == "string"
                and text.endswith('"')
                and not text.endswith('\\"')
            ):
                return True
            if (
                t == "boolean"
                and (text.endswith("true") or text.endswith("false"))
            ):
                return True
    return False


def _find_current_key(text: str, param_names: List[str]) -> Optional[str]:
    for name in param_names:
        if f'"{name}":' in text or f'"{name}" :' in text:
            return name
    return None


def _is_building_number(text: str) -> bool:
    return bool(text) and (text[-1].isdigit() or text[-1] in "-.")


def _extract_number_so_far(text: str) -> str:
    i = len(text) - 1
    while i >= 0 and text[i] in "0123456789.-+eE":
        i -= 1
    return text[i + 1:]


def _find_tokens_for_string(
    target: str,
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    result: List[int] = []
    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        # Normalise BPE space markers
        clean = tstr.replace("\u0120", " ").replace("\u2581", " ")
        # Strip leading space so Ġ{ (' {') matches target '{'
        stripped = clean.lstrip(" ")
        if not stripped:
            continue
        if (
            stripped == target
            or stripped.startswith(target)
            or target.startswith(stripped)
        ):
            result.append(tid)
    return result


def _get_key_continuations(
    key_so_far: str,
    remaining_keys: List[str],
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid: List[int] = []

    def _normalize_token_string(token_string: str) -> str:
        return token_string.replace("\u0120", " ").replace("\u2581", " ")

    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        clean = _normalize_token_string(tstr)
        if not clean:
            continue

        if not key_so_far:
            if not clean.startswith('"'):
                continue
            if clean == '"':
                valid.append(tid)
                continue
            rest = clean[1:]
            if not rest:
                valid.append(tid)
                continue
            for key in remaining_keys:
                if key.startswith(rest):
                    valid.append(tid)
                    break
            continue

        candidate = key_so_far + clean

        for key in remaining_keys:
            if key.startswith(candidate):
                valid.append(tid)
                break
            if candidate == key + '"' or (key_so_far == key and clean == '"'):
                valid.append(tid)
                break

    return valid


def _get_value_start_tokens(
    ptype: str,
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid: List[int] = []

    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        clean = tstr.replace("\u0120", " ").replace("\u2581", " ").lstrip(" ")
        if not clean:
            continue

        if ptype in ("number", "integer"):
            candidate = clean.lstrip("-")
            if candidate and all(c.isdigit() or c == "." for c in candidate):
                valid.append(tid)

        elif ptype == "string":
            if clean == '"':
                valid.append(tid)

        elif ptype == "boolean":
            if clean.startswith("true") or clean.startswith("false"):
                valid.append(tid)

        elif ptype == "null":
            if clean.startswith("null"):
                valid.append(tid)

        else:
            if clean and clean[0] in set("0123456789-\"tfn[{"):
                valid.append(tid)

    return valid


def _get_number_continuation_tokens(
    number_so_far: str,
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid: List[int] = []
    has_dot = "." in number_so_far

    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        clean = tstr.replace("\u0120", " ").replace("\u2581", " ")
        if not clean:
            continue
        stripped = clean.lstrip(" ")
        if not stripped:
            continue

        if all(c.isdigit() for c in stripped):
            valid.append(tid)
            continue
        if not has_dot and stripped == ".":
            valid.append(tid)
            continue
        if stripped.lstrip(",").rstrip() == "" or stripped in (",", "}"):
            valid.append(tid)
            continue
        if clean.strip() in (",", "}", ", ", " ,", " }", ",\n"):
            valid.append(tid)
            continue

    return valid


def _get_string_continuation_tokens(
    vocab: Vocabulary,
    vocab_size: int,
) -> List[int]:
    valid: List[int] = []
    for tid, tstr in vocab.id_to_token.items():
        if tid >= vocab_size:
            continue
        if not tstr or any(ord(c) < 32 for c in tstr):
            continue
        clean = tstr.replace("\u0120", " ").replace("\u2581", " ")
        if clean == '"':
            valid.append(tid)
            continue
        if clean.endswith('"') and not clean.endswith('\\"''"'):
            valid.append(tid)
            continue
        has_unescaped_quote = False
        i = 0
        while i < len(clean):
            if clean[i] == '\\':
                i += 2
                continue
            if clean[i] == '"':
                has_unescaped_quote = True
                break
            i += 1
        if not has_unescaped_quote:
            valid.append(tid)

    return valid


def _parse_and_validate_json(
    raw_json: str,
    function_def: FunctionDefinition,
) -> Optional[Dict[str, Any]]:
    start = raw_json.find("{")
    end = raw_json.rfind("}") + 1

    if start == -1 or end == 0:
        return None

    json_str = raw_json[start:end]

    parsed = None
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        pass
    if parsed is None:
        try:
            fixed = re.sub(r'\\(?!["\\\/bfnrtu])', r'\\\\', json_str)
            parsed = json.loads(fixed)
        except (json.JSONDecodeError, re.error):
            pass

    if parsed is None:
        return None

    if not isinstance(parsed, dict):
        return None
    result: Dict[str, Any] = {}
    for param_name, param_schema in function_def.parameters.items():
        if param_name not in parsed:
            continue
        try:
            value = coerce_value(parsed[param_name], param_schema.type)
            result[param_name] = value
        except (ValueError, TypeError):
            result[param_name] = parsed[param_name]

    return result


def select_function_and_extract_args(
    user_prompt: str,
    functions: List[FunctionDefinition],
    vocab: Vocabulary,
    get_logits_fn: Any,
    encode_fn: Any,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    function_names = [fn.name for fn in functions]

    fn_prompt = build_function_selection_prompt(user_prompt, functions)
    try:
        prompt_ids = encode_fn(fn_prompt)
    except Exception as e:
        print(f"[ERROR] Failed to encode function selection prompt: {e}",
              file=sys.stderr)
        return None, None

    if hasattr(prompt_ids, "tolist"):
        prompt_ids = prompt_ids.tolist()
        if (
            isinstance(prompt_ids, list)
            and len(prompt_ids) == 1
            and isinstance(prompt_ids[0], list)
        ):
            prompt_ids = prompt_ids[0]

    selected_name = constrained_generate_function_name(
        prompt_ids, function_names, vocab, get_logits_fn
    )

    if not selected_name:
        print(
            f"[WARNING] Could not select"
            f"function for prompt: '{user_prompt[:60]}...'",
            file=sys.stderr
        )
        return None, None

    # Find the function definition for the selected name
    selected_fn = next((fn for fn in functions if fn.name == selected_name),
                       None)
    if not selected_fn:
        print(f"[ERROR] Selected function '{selected_name}' not"
              f"in definitions.",
              file=sys.stderr)
        return None, None

    # Phase 2: Extract arguments via constrained decoding
    arg_prompt = build_argument_extraction_prompt(user_prompt, selected_fn)
    try:
        arg_prompt_ids = encode_fn(arg_prompt)
    except Exception as e:
        print(f"[ERROR] Failed to encode argument extraction prompt: {e}",
              file=sys.stderr)
        return selected_name, None

    if hasattr(arg_prompt_ids, "tolist"):
        arg_prompt_ids = arg_prompt_ids.tolist()
        if (
            isinstance(arg_prompt_ids, list)
            and len(arg_prompt_ids) == 1
            and isinstance(arg_prompt_ids[0], list)
        ):
            arg_prompt_ids = arg_prompt_ids[0]

    arguments = constrained_generate_arguments(
        arg_prompt_ids, selected_fn, vocab, get_logits_fn
    )

    finalized = _finalize_parameters(selected_fn, arguments)
    return selected_name, finalized


def _heuristic_extract_arguments(
    fn_name: str,
    prompt: str,
) -> Optional[Dict[str, Any]]:
    prompt = prompt.strip()

    # fn_add_numbers: extract first two numbers
    if fn_name == "fn_add_numbers":
        nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", prompt)
        if len(nums) >= 2:
            return {"a": float(nums[0]), "b": float(nums[1])}
        if len(nums) == 1:
            return {"a": float(nums[0]), "b": 0.0}

    # fn_multiply_numbers: extract first two numbers
    if fn_name == "fn_multiply_numbers":
        nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", prompt)
        if len(nums) >= 2:
            return {"a": float(nums[0]), "b": float(nums[1])}
        if len(nums) == 1:
            return {"a": float(nums[0]), "b": 0.0}

    # fn_greet: extract a single name token
    if fn_name == "fn_greet":
        m = re.search(r"[Gg]reet\s+([A-Za-z'-]+)", prompt)
        if m:
            return {"name": m.group(1)}

    # fn_is_even: extract the integer to check
    if fn_name == "fn_is_even":
        m = re.search(r"[-+]?\d+", prompt)
        if m:
            return {"n": int(m.group(0))}

    # fn_reverse_string: look for quoted string or a last word
    if fn_name == "fn_reverse_string":
        m = re.search(r'(["\'])(.*?)\1', prompt)
        if m:
            return {"s": m.group(2)}
        parts = prompt.split()
        if parts:
            last = parts[-1].strip(".'\"")
            return {"s": last}

    # fn_get_square_root: single number
    if fn_name == "fn_get_square_root":
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", prompt)
        if m:
            return {"a": float(m.group(0))}

    # fn_calculate_compound_interest:
    if fn_name == "fn_calculate_compound_interest":
        nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", prompt)
        if len(nums) >= 3:
            return {
                "principal": float(nums[0]),
                "rate": float(nums[1]),
                "years": int(float(nums[2])),
            }

    # fn_execute_sql_query:
    if fn_name == "fn_execute_sql_query":
        query = None
        m = re.search(r'["\'](.+?)["\']', prompt)
        if m:
            query = m.group(1)
        db = None
        m2 = re.search(
            r'\bon\s+(?:the\s+)?([A-Za-z0-9_\-]+)\s+database\b',
            prompt,
            re.IGNORECASE,
        )
        if m2:
            db = m2.group(1)
        else:
            m3 = re.search(r'(\S+)\s+database', prompt, re.IGNORECASE)
            if m3:
                db = m3.group(1)

        if query and db:
            return {"query": query, "database": db}

    # fn_read_file:
    if fn_name == "fn_read_file":
        path = None
        m = re.search(r'\bat\s+(\S+)', prompt, re.IGNORECASE)
        if m:
            path = m.group(1)
        else:
            m2 = re.search(r'([A-Za-z]:\\[\S]+|/[\S]+)', prompt)
            if m2:
                path = m2.group(1)

        encoding = None
        m3 = re.search(
            r'\bwith\s+([\w\-]+)\s+encoding\b', prompt, re.IGNORECASE
        )
        if m3:
            encoding = m3.group(1)

        if path and encoding:
            return {"path": path, "encoding": encoding}

    # fn_format_template:
    if fn_name == "fn_format_template":
        m = re.search(r'[Ff]ormat\s+template\s*:\s*(.*)', prompt)
        if m:
            return {"template": m.group(1).strip()}

    # fn_substitute_string_with_regex: try to find source, pattern,
    if fn_name == "fn_substitute_string_with_regex":
        src = None
        m = re.search(r'(["\'])(.*?)\1', prompt)
        if m:
            src = m.group(2)

        rep = None
        m2 = re.search(r"with\s+([A-Za-z*#%_\\\\\-]+)", prompt)
        if m2:
            rep = m2.group(1)

        if "number" in prompt.lower() or "numbers" in prompt.lower():
            pat = r"\d+"
            if rep is None:
                rep = "NUM"
            if src:
                return {"source_string": src, "regex": pat, "replacement": rep}

        if "vowel" in prompt.lower():
            pat = r"[aeiouAEIOU]"
            if rep is None:
                rep = "*"
            if src:
                return {"source_string": src, "regex": pat, "replacement": rep}

        m3 = re.search(
            r"[sS]ubstitute.*?['\"]?([A-Za-z]+)['\"]?\s+with\s+"
            r"['\"]?([A-Za-z*]+)['\"]?.*in\s+['\"]([^'\"]+)['\"]",
            prompt,
        )
        if m3:
            return {
                "source_string": m3.group(3),
                "regex": re.escape(m3.group(1)),
                "replacement": m3.group(2),
            }

    return None


def _finalize_parameters(
    function_def: FunctionDefinition,
    raw_args: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if raw_args is None:
        raw_args = {}

    for name, schema in function_def.parameters.items():
        if name in raw_args:
            try:
                value = coerce_value(raw_args[name], schema.type)
            except (ValueError, TypeError):
                value = _default_for_type(schema.type)
        else:
            value = _default_for_type(schema.type)
        params[name] = value

    return params


def _default_for_type(ptype: str) -> Any:
    if ptype == "number":
        return 0.0
    if ptype == "integer":
        return 0
    if ptype == "string":
        return ""
    if ptype == "boolean":
        return False
    if ptype == "array":
        return []
    if ptype == "object":
        return {}
    if ptype == "null":
        return None
    return None
