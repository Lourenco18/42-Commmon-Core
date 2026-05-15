"""Vocabulary utilities for mapping token IDs to string representations.

Handles tokenizer.json (HuggingFace format) and plain vocab.json files.
The tokenizer.json format used by Qwen3 stores vocab under model.vocab as
a {token_string: token_id} mapping.
"""

import json
import sys
from typing import Any, Dict, List, Optional, Tuple


class Vocabulary:
    """Manages token-to-string and string-to-token mappings for a
    language model.

    Attributes:
        id_to_token: Maps integer token ID to token string.
        token_to_ids: Maps token string to list of token IDs.
        vocab_size: Total number of tokens loaded.
    """

    def __init__(self) -> None:
        """Initialise an empty Vocabulary."""
        self.id_to_token: Dict[int, str] = {}
        self.token_to_ids: Dict[str, List[int]] = {}
        self.vocab_size: int = 0

    @classmethod
    def from_json_path(cls, path: str) -> Optional["Vocabulary"]:
        """Load vocabulary from a JSON file (tokenizer.json or vocab.json).

        Tries multiple known formats in order:
        1. HuggingFace tokenizer.json  {"model": {"vocab": {token: id}}}
        2. added_tokens list           [{"id": n, "content": s}]
        3. Flat token->id mapping      {"token_str": id, ...}
        4. Flat id->token mapping      {"id_str": "token_str", ...}

        Args:
            path: Path to tokenizer.json or vocab.json.

        Returns:
            A populated Vocabulary, or None if loading fails.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw: Dict[str, Any] = json.load(f)
        except FileNotFoundError:
            print(
                f"[ERROR] Vocabulary file not found: '{path}'",
                file=sys.stderr,
            )
            return None
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Invalid JSON in '{path}': {exc}", file=sys.stderr)
            return None
        except OSError as exc:
            print(f"[ERROR] Could not read '{path}': {exc}", file=sys.stderr)
            return None

        vocab = cls()

        # Format 1: tokenizer.json {"model": {"vocab": {token: id}}}
        model_section = raw.get("model", {})
        if isinstance(model_section, dict):
            inner_vocab = model_section.get("vocab")
            if isinstance(inner_vocab, dict) and inner_vocab:
                vocab._load_token_to_id(inner_vocab)

        # Format 2: added_tokens [{"id": n, "content": s}] (special tokens)
        added = raw.get("added_tokens", [])
        if isinstance(added, list):
            for entry in added:
                if isinstance(entry, dict):
                    tid = entry.get("id")
                    content = entry.get("content")
                    if isinstance(tid, int) and isinstance(content, str):
                        if tid not in vocab.id_to_token:
                            vocab.id_to_token[tid] = content
                            vocab.token_to_ids.setdefault(
                                content, []
                            ).append(tid)

        # Format 3/4: flat dict at top level (plain vocab.json)
        if vocab.vocab_size == 0:
            vocab._load_flat(raw)

        vocab.vocab_size = len(vocab.id_to_token)

        if vocab.vocab_size == 0:
            print(f"[ERROR] No tokens loaded from '{path}'.", file=sys.stderr)
            return None

        print(f"[INFO] Loaded vocabulary with {vocab.vocab_size} tokens.")
        return vocab

    def _load_token_to_id(self, mapping: Dict[str, Any]) -> None:
        """Load from a token_string->token_id dictionary.

        Args:
            mapping: Dict mapping token strings to integer IDs.
        """
        for token_str, token_id_raw in mapping.items():
            try:
                token_id = int(token_id_raw)
                tstr = str(token_str)
                self.id_to_token[token_id] = tstr
                self.token_to_ids.setdefault(tstr, []).append(token_id)
            except (ValueError, TypeError):
                pass

    def _load_flat(self, mapping: Dict[str, Any]) -> None:
        """Auto-detect and load a flat id<->token dictionary.

        Args:
            mapping: Flat dict to parse.
        """
        sample = list(mapping.items())[:20]
        values_are_ints = all(isinstance(v, int) for _, v in sample)

        for key, value in mapping.items():
            try:
                if values_are_ints:
                    tstr = str(key)
                    token_id = int(value)
                else:
                    token_id = int(key)
                    tstr = str(value)
                self.id_to_token[token_id] = tstr
                self.token_to_ids.setdefault(tstr, []).append(token_id)
            except (ValueError, TypeError):
                pass

    def token_id_to_string(self, token_id: int) -> Optional[str]:
        """Return the string for a token ID, or None if not found.

        Args:
            token_id: The integer token ID.

        Returns:
            Token string or None.
        """
        return self.id_to_token.get(token_id)

    def find_tokens_with_prefix(self, prefix: str) -> List[Tuple[int, str]]:
        """Find all tokens whose string starts with prefix.

        Args:
            prefix: The prefix to search for.

        Returns:
            List of (token_id, token_string) pairs.
        """
        return [
            (tid, tstr)
            for tid, tstr in self.id_to_token.items()
            if tstr.startswith(prefix)
        ]

    def find_tokens_exact(self, target: str) -> List[int]:
        """Find all token IDs matching target exactly.

        Args:
            target: The exact string to match.

        Returns:
            List of matching token IDs.
        """
        return self.token_to_ids.get(target, [])

    def find_tokens_containing(self, substring: str) -> List[Tuple[int, str]]:
        """Find all tokens containing substring.

        Args:
            substring: The substring to search for.

        Returns:
            List of (token_id, token_string) pairs.
        """
        return [
            (tid, tstr)
            for tid, tstr in self.id_to_token.items()
            if substring in tstr
        ]

    def get_all_ids(self) -> List[int]:
        """Return all token IDs sorted.

        Returns:
            Sorted list of all integer token IDs.
        """
        return sorted(self.id_to_token.keys())
