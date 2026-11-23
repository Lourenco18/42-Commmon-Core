import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)
MAX_ENTRIES: int = 10
NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9 ]{1,10}$")


def _validate_name(name: str) -> str:
    """Perform the  validate name operation.

    Args:
        name: Player name.

    Returns:
        Result of the operation."""
    name = name.strip()[:10]
    if not name or not NAME_PATTERN.match(name):
        return "Player"
    return name


class HighscoreEntry:
    """Store a validated player name and score."""
    def __init__(self, name: str, score: int) -> None:
        """Initialize a HighscoreEntry instance.

        Args:
            name: Player name.
            score: Non-negative score value."""
        self.name: str = _validate_name(name)
        self.score: int = max(0, int(score))

    def to_dict(self) -> dict[str, object]:
        """Convert the highscore entry to a JSON-compatible mapping.

        Returns:
            Result of the operation."""
        return {"name": self.name, "score": self.score}


class HighscoreSystem:
    """Load, rank, display, and persist highscore entries."""
    def __init__(self, filename: str) -> None:
        """Initialize a HighscoreSystem instance.

        Args:
            filename: Path to the highscore file."""
        self.filename: str = filename
        self.entries: list[HighscoreEntry] = []
        self.load()

    def load(self) -> None:
        """Load and validate saved highscores, resetting on file errors."""
        if not os.path.exists(self.filename):
            self.entries = []
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                raw: object = json.load(f)
            if not isinstance(raw, list):
                raise ValueError("Root must be a list")
            loaded: list[HighscoreEntry] = []
            for item in raw:
                if isinstance(item, dict):
                    try:
                        name = str(item.get("name", "Player"))
                        score = int(item.get("score", 0))
                        loaded.append(HighscoreEntry(name, score))
                    except (TypeError, ValueError):
                        pass
            self.entries = sorted(
                loaded,
                key=lambda e: e.score,
                reverse=True)[
                :MAX_ENTRIES]
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("Could not load highscores: %s", exc)
            self.entries = []

    def save(self) -> None:
        """Write the current highscore entries to disk."""
        try:
            os.makedirs(os.path.dirname(self.filename) or ".", exist_ok=True)
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
        except OSError as exc:
            logger.warning("Could not save highscores: %s", exc)

    def add(self, name: str, score: int) -> Optional[int]:
        """Insert a score, keep the top ten, and return its rank.

        Args:
            name: Player name.
            score: Non-negative score value.

        Returns:
            Result of the operation."""
        entry = HighscoreEntry(name, score)
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.score, reverse=True)
        self.entries = self.entries[:MAX_ENTRIES]
        if entry in self.entries:
            return self.entries.index(entry) + 1
        return None

    def is_highscore(self, score: int) -> bool:
        """Check whether a score would enter the top ten.

        Args:
            score: Non-negative score value.

        Returns:
            Result of the operation."""
        return len(
            self.entries) < MAX_ENTRIES or score > self.entries[-1].score

    def get_top(self, n: int = MAX_ENTRIES) -> list[HighscoreEntry]:
        """Return the highest-ranking entries up to the requested count.

        Args:
            n: Maximum number of entries to return.

        Returns:
            Result of the operation."""
        return self.entries[:n]
