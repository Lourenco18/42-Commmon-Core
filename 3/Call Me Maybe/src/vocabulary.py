import json
import sys
from typing import Dict, List, Optional, Tuple


class Vocabulary:
    def __init__(self) -> None:
        self.id_to_token: Dict[int, str] = {}
        self.token_to_ids: Dict[str, List[int]] = {}
        self.vocab_size: int = 0

    @classmethod
    def from_json_path(cls, path: str) -> Optional["Vocabulary"]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw: Dict = json.load(f)
        except FileNotFoundError:
            print(f"[ERROR] Vocabulary file not found: '{path}'",
                  file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in vocabulary file '{path}': {e}",
                  file=sys.stderr)
            return None
        except OSError as e:
            print(f"[ERROR] Could not read vocabulary file '{path}': {e}",
                  file=sys.stderr)
            return None

        def _to_int(value) -> Optional[int]:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        keys_are_ids = all(_to_int(key) is not None for key in raw.keys())
        values_are_ids = all(_to_int(value) is not None for value in
                             raw.values())

        vocab = cls()
        skipped = 0

        if keys_are_ids and all(isinstance(value, str) for value in
                                raw.values()):
            for key, token_str in raw.items():
                token_id = _to_int(key)
                if token_id is None:
                    skipped += 1
                    continue
                token_str = str(token_str)
                vocab.id_to_token[token_id] = token_str
                vocab.token_to_ids.setdefault(token_str, []).append(token_id)
        elif values_are_ids:
            for token_str, token_id_raw in raw.items():
                token_id = _to_int(token_id_raw)
                if token_id is None:
                    skipped += 1
                    continue
                token_str = str(token_str)
                vocab.id_to_token[token_id] = token_str
                vocab.token_to_ids.setdefault(token_str, []).append(token_id)
        else:
            for key, token_str in raw.items():
                token_id = _to_int(key)
                if token_id is None or not isinstance(token_str, str):
                    skipped += 1
                    continue
                vocab.id_to_token[token_id] = token_str
                vocab.token_to_ids.setdefault(token_str, []).append(token_id)

        # if skipped:
        #     print(
        #         f"[WARNING] Skipped {skipped} invalid vocabulary"
        #         f"entr{'y' if skipped == 1 else 'ies'}.",
        #         file=sys.stderr,
        #     )

        vocab.vocab_size = len(vocab.id_to_token)
        print(f"[INFO] Loaded vocabulary with {vocab.vocab_size} tokens.")
        return vocab

    def token_id_to_string(self, token_id: int) -> Optional[str]:
        return self.id_to_token.get(token_id)

    def find_tokens_with_prefix(self, prefix: str) -> List[Tuple[int, str]]:

        results: List[Tuple[int, str]] = []
        for token_id, token_str in self.id_to_token.items():
            if token_str.startswith(prefix):
                results.append((token_id, token_str))
        return results

    def find_tokens_exact(self, target: str) -> List[int]:
        return self.token_to_ids.get(target, [])

    def find_tokens_containing(self, substring: str) -> List[Tuple[int, str]]:
        results: List[Tuple[int, str]] = []
        for token_id, token_str in self.id_to_token.items():
            if substring in token_str:
                results.append((token_id, token_str))
        return results

    def get_all_ids(self) -> List[int]:
        """Return all token IDs in the vocabulary.

        Returns:
            Sorted list of all integer token IDs.
        """
        return sorted(self.id_to_token.keys())
