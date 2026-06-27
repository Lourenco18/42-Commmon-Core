"""Pac-Man — entry point.

Usage:
    python3 pac-man.py config.json

The program takes exactly one argument: a path to a JSON configuration file.
"""

import logging
import sys

MIN_PYTHON: tuple[int, int] = (3, 10)

if sys.version_info < MIN_PYTHON:
    sys.exit(
        "Error: this project requires Python "
        f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} or later "
        f"(running on Python {sys.version_info.major}."
        f"{sys.version_info.minor}).\n"
        "Use a newer interpreter, e.g.: python3.10 pac-man.py config.json"
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Parse arguments, load config, and run the game."""
    if len(sys.argv) != 2:
        print("Usage: python3 pac-man.py <config.json>")
        sys.exit(1)

    config_path: str = sys.argv[1]

    from src.config import load_config
    config = load_config(config_path)

    from src.game import Game
    game = Game(config)
    game.run()


if __name__ == "__main__":
    main()
