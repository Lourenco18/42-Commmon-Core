import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mazegen_src"))

from maze_config import load_config, MazeConfig
from maze_output import write_output
from maze_display import display_maze
from mazegen.generator import MazeGenerator


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py <config_file>", file=sys.stderr)
        sys.exit(1)

    config_path: str = sys.argv[1]

    try:
        cfg: MazeConfig = load_config(config_path)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"Error reading configuration: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        gen = MazeGenerator(
            width=cfg.width,
            height=cfg.height,
            seed=cfg.seed,
            entry=cfg.entry,
            exit_=cfg.exit_,
        )
        gen.generate(perfect=cfg.perfect)
    except (ValueError, RuntimeError) as exc:
        print(f"Maze generation error: {exc}", file=sys.stderr)
        sys.exit(1)

    result = gen._get_42_pattern()
    if result is None:
        print(
            "Warning: maze is too small to embed the '42' pattern.",
            file=sys.stderr,
        )

    try:
        write_output(gen, cfg.output_file)
    except OSError as exc:
        print(f"Error writing output file: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Maze written to {cfg.output_file}")
    display_maze(gen, cfg)


if __name__ == "__main__":
    main()
