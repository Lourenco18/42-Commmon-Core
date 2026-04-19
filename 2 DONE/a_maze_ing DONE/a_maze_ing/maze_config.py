from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class MazeConfig:

    width: int
    height: int
    entry: Tuple[int, int]
    exit_: Tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = field(default=None)
    algorithm: str = field(default="dfs")


def _parse_coord(value: str, label: str) -> Tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise ValueError(
            f"'{label}' must be in 'x,y' format, got: '{value}'"
        )
    try:
        x, y = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise ValueError(
            f"'{label}' coordinates must be integers, got: '{value}'"
        )
    if x < 0 or y < 0:
        raise ValueError(
            f"'{label}' coordinates must be non-negative, got: ({x}, {y})"
        )
    return (x, y)


def load_config(path: str) -> MazeConfig:
    raw: dict[str, str] = {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise ValueError(
                        f"Line {lineno}: expected 'KEY=VALUE', got: '{line}'"
                    )
                key, _, value = line.partition("=")
                raw[key.strip().upper()] = value.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: '{path}'")

    mandatory = ["WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"]
    for key in mandatory:
        if key not in raw:
            raise KeyError(f"Mandatory key '{key}' is missing from config.")

    try:
        width = int(raw["WIDTH"])
        height = int(raw["HEIGHT"])
    except ValueError as exc:
        raise ValueError(f"WIDTH/HEIGHT must be integers: {exc}") from exc

    if width < 2 or height < 2:
        raise ValueError("WIDTH and HEIGHT must both be >= 2.")

    entry = _parse_coord(raw["ENTRY"], "ENTRY")
    exit_ = _parse_coord(raw["EXIT"], "EXIT")

    if entry == exit_:
        raise ValueError("ENTRY and EXIT must be different cells.")
    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError(f"ENTRY {entry} is outside the maze bounds"
                         f"({width}x{height}).")
    if not (0 <= exit_[0] < width and 0 <= exit_[1] < height):
        raise ValueError(f"EXIT {exit_} is outside the maze"
                         f"bounds ({width}x{height}).")

    perfect_raw = raw["PERFECT"].lower()
    if perfect_raw not in ("true", "false", "1", "0"):
        raise ValueError(f"PERFECT must be"
                         f"True/False, got: '{raw['PERFECT']}'")
    perfect = perfect_raw in ("true", "1")

    output_file = raw["OUTPUT_FILE"]
    if not output_file:
        raise ValueError("OUTPUT_FILE must not be empty.")

    seed: Optional[int] = None
    if "SEED" in raw:
        try:
            seed = int(raw["SEED"])
        except ValueError as exc:
            raise ValueError(f"SEED must be an integer: {exc}") from exc

    algorithm = raw.get("ALGORITHM", "dfs").lower()

    return MazeConfig(
        width=width,
        height=height,
        entry=entry,
        exit_=exit_,
        output_file=output_file,
        perfect=perfect,
        seed=seed,
        algorithm=algorithm,
    )
