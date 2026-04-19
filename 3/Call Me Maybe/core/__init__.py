"""Mock llm_sdk for testing and linting purposes.

Replace this directory with the real llm_sdk provided with the project.
This mock lets tests and linting run without the actual model weights.
"""

import json
import os
import tempfile
from typing import List

import numpy as np

_VOCAB_SIZE = 1000

# Build a small deterministic vocabulary
_VOCAB: dict = {}

for _ch in ["{", "}", ":", ",", '"', " ", "\n", "true", "false"]:
    _VOCAB[_ch] = len(_VOCAB)

for _d in "0123456789.-":
    _VOCAB[_d] = len(_VOCAB)

for _tok in [
    "fn", "_add", "_numbers", "fn_add", "fn_add_numbers",
    "fn_greet", "fn_reverse", "_string", "fn_reverse_string",
    "fn_multiply", "fn_is", "_even", "fn_is_even",
    "add", "greet", "reverse", "multiply", "is", "even",
    "numbers", "string", "a", "b", "n", "s", "x", "y", "name",
    "hello", "world", "shrek", "john", "alice",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "10", "42", "100", "200", "265", "345",
]:
    if _tok not in _VOCAB:
        _VOCAB[_tok] = len(_VOCAB)

for _c in sorted(set("fn_adumbersgritvslyoe")):
    if _c not in _VOCAB:
        _VOCAB[_c] = len(_VOCAB)

while len(_VOCAB) < _VOCAB_SIZE:
    _dummy = f"<d{len(_VOCAB)}>"
    _VOCAB[_dummy] = len(_VOCAB)


def _make_vocab_file() -> str:
    """Write the vocabulary to a temporary JSON file.

    Returns:
        Absolute path to the vocabulary JSON file.
    """
    fd, path = tempfile.mkstemp(suffix=".json", prefix="mock_vocab_")
    with os.fdopen(fd, "w") as f:
        json.dump(_VOCAB, f)
    return path


_VOCAB_PATH = _make_vocab_file()
_ID_TO_TOKEN = {v: k for k, v in _VOCAB.items()}


class Small_LLM_Model:
    """Mock Small_LLM_Model for testing without model weights.

    In production, replace with the real llm_sdk.Small_LLM_Model
    which wraps Qwen3-0.6B.
    """

    def __init__(self) -> None:
        """Initialise the mock model."""
        self._vocab_size = _VOCAB_SIZE

    def get_logits_from_input_ids(
        self,
        input_ids: np.ndarray,
    ) -> np.ndarray:
        """Return mock logits for testing.

        Args:
            input_ids: Integer array of shape (1, seq_len).

        Returns:
            Logits array of shape (1, seq_len, vocab_size).
        """
        seq_len = input_ids.shape[1] if input_ids.ndim == 2 else 1
        rng = np.random.default_rng(seed=int(input_ids.sum()) % 9999)
        logits = rng.standard_normal(
            (1, seq_len, self._vocab_size)
        ).astype(np.float32)
        for tok, tid in _VOCAB.items():
            if tok in ("{", "}", ":", ",", '"'):
                logits[0, -1, tid] += 0.5
        return logits

    def get_path_to_vocabulary_json(self) -> str:
        """Return the path to the vocabulary JSON file.

        Returns:
            Absolute path string.
        """
        return _VOCAB_PATH

    def encode(self, text: str) -> List[int]:
        """Encode text into token IDs using greedy longest-match.

        Args:
            text: Input string.

        Returns:
            List of integer token IDs.
        """
        ids: List[int] = []
        i = 0
        while i < len(text):
            matched = False
            for length in range(min(20, len(text) - i), 0, -1):
                substr = text[i:i + length]
                if substr in _VOCAB:
                    ids.append(_VOCAB[substr])
                    i += length
                    matched = True
                    break
            if not matched:
                ids.append(0)
                i += 1
        return ids

    def decode(self, token_ids: List[int]) -> str:
        """Decode token IDs back into a string.

        Args:
            token_ids: List of integer token IDs.

        Returns:
            Decoded string.
        """
        return "".join(_ID_TO_TOKEN.get(tid, "") for tid in token_ids)
