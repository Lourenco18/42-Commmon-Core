from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MazeConfig:

    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int] = field(default=None)
    algorithm: str = field(default="dfs")
    display_mode: str = field(default="ascii")
    animate: bool = field(default=False)
    palette: str = field(default="default")
    export_svg: Optional[str] = field(default=None)
    export_cell_size: int = field(default=24)
    export_wall_thickness: int = field(default=2)
    ducks: bool = field(default=False)
    ducks_count: int = field(default=0)
    ducks_animate: bool = field(default=False)
    auto_palette: bool = field(default=False)
    pulse_entry_exit: bool = field(default=False)
    pattern_fade: bool = field(default=False)
    dead_end_shimmer: bool = field(default=False)
    seed_slideshow: bool = field(default=False)
    stats_ticker: bool = field(default=False)


class ConfigParser:
    _MANDATORY_KEYS: frozenset[str] = frozenset(
        {"WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"}
    )

    def __init__(self, filepath: str) -> None:
        self.filepath: str = filepath

    def parse(self) -> MazeConfig:
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(
                f"Configuration file not found: '{self.filepath}'"
            )

        raw = self._read_raw(self.filepath)
        self._check_mandatory(raw)
        return self._build_config(raw)

    @staticmethod
    def _read_raw(filepath: str) -> dict[str, str]:
        raw: dict[str, str] = {}
        with open(filepath, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    raise ValueError(
                        f"Line {lineno}: invalid format (expected KEY=VALUE):"
                        f" '{stripped}'"
                    )
                key, _, value = stripped.partition("=")
                raw[key.strip().upper()] = value.strip()
        return raw

    def _check_mandatory(self, raw: dict[str, str]) -> None:
        missing = self._MANDATORY_KEYS - raw.keys()
        if missing:
            raise ValueError(
                f"Missing mandatory configuration keys: "
                f"{', '.join(sorted(missing))}"
            )

    def _build_config(self, raw: dict[str, str]) -> MazeConfig:
        width = self._parse_positive_int("WIDTH", raw["WIDTH"])
        height = self._parse_positive_int("HEIGHT", raw["HEIGHT"])
        entry = self._parse_coord("ENTRY", raw["ENTRY"], width, height)
        exit_ = self._parse_coord("EXIT", raw["EXIT"], width, height)

        if entry == exit_:
            raise ValueError("ENTRY and EXIT coordinates must be different.")

        if not self._is_border_cell(entry, width, height):
            raise ValueError(
                f"ENTRY {entry} must be on the maze border."
            )
        if not self._is_border_cell(exit_, width, height):
            raise ValueError(
                f"EXIT {exit_} must be on the maze border."
            )

        perfect = self._parse_bool("PERFECT", raw["PERFECT"])

        # keys
        seed: Optional[int] = None
        if "SEED" in raw and raw["SEED"].upper() not in ("", "NONE", "NULL"):
            seed = self._parse_int("SEED", raw["SEED"])

        algorithm = raw.get("ALGORITHM", "dfs").lower()
        display_mode = raw.get("DISPLAY_MODE", "ascii").lower()
        if display_mode not in ("ascii", "mlx", "both"):
            raise ValueError(
                f"DISPLAY_MODE must be 'ascii', 'mlx', or 'both', "
                f"got '{display_mode}'."
            )

        animate = False
        if "ANIMATE" in raw:
            animate = self._parse_bool("ANIMATE", raw["ANIMATE"])

        palette = raw.get("PALETTE", "default").lower()
        if palette not in ("default", "colorblind"):
            raise ValueError(
                "PALETTE must be 'default' or 'colorblind', "
                f"got '{palette}'."
            )

        export_svg = None
        if "EXPORT_SVG" in raw and raw["EXPORT_SVG"].strip():
            export_svg = raw["EXPORT_SVG"].strip()

        export_cell_size = 24
        if "EXPORT_CELL_SIZE" in raw:
            export_cell_size = self._parse_positive_int(
                "EXPORT_CELL_SIZE",
                raw["EXPORT_CELL_SIZE"],
            )

        export_wall_thickness = 2
        if "EXPORT_WALL" in raw:
            export_wall_thickness = self._parse_positive_int(
                "EXPORT_WALL",
                raw["EXPORT_WALL"],
            )

        ducks = False
        if "DUCKS" in raw:
            ducks = self._parse_bool("DUCKS", raw["DUCKS"])

        ducks_count = 0
        if "DUCKS_COUNT" in raw:
            ducks_count = self._parse_positive_int(
                "DUCKS_COUNT",
                raw["DUCKS_COUNT"],
            )
        elif ducks:
            ducks_count = 5

        ducks_animate = False
        if "DUCKS_ANIMATE" in raw:
            ducks_animate = self._parse_bool(
                "DUCKS_ANIMATE",
                raw["DUCKS_ANIMATE"],
            )

        auto_palette = False
        if "AUTO_PALETTE" in raw:
            auto_palette = self._parse_bool(
                "AUTO_PALETTE",
                raw["AUTO_PALETTE"],
            )

        pulse_entry_exit = False
        if "PULSE_ENTRY_EXIT" in raw:
            pulse_entry_exit = self._parse_bool(
                "PULSE_ENTRY_EXIT",
                raw["PULSE_ENTRY_EXIT"],
            )

        pattern_fade = False
        if "PATTERN_FADE" in raw:
            pattern_fade = self._parse_bool(
                "PATTERN_FADE",
                raw["PATTERN_FADE"],
            )

        dead_end_shimmer = False
        if "DEAD_END_SHIMMER" in raw:
            dead_end_shimmer = self._parse_bool(
                "DEAD_END_SHIMMER",
                raw["DEAD_END_SHIMMER"],
            )

        seed_slideshow = False
        if "SEED_SLIDESHOW" in raw:
            seed_slideshow = self._parse_bool(
                "SEED_SLIDESHOW",
                raw["SEED_SLIDESHOW"],
            )

        stats_ticker = False
        if "STATS_TICKER" in raw:
            stats_ticker = self._parse_bool(
                "STATS_TICKER",
                raw["STATS_TICKER"],
            )

        return MazeConfig(
            width=width,
            height=height,
            entry=entry,
            exit_=exit_,
            output_file=raw["OUTPUT_FILE"],
            perfect=perfect,
            seed=seed,
            algorithm=algorithm,
            display_mode=display_mode,
            animate=animate,
            palette=palette,
            export_svg=export_svg,
            export_cell_size=export_cell_size,
            export_wall_thickness=export_wall_thickness,
            ducks=ducks,
            ducks_count=ducks_count,
            ducks_animate=ducks_animate,
            auto_palette=auto_palette,
            pulse_entry_exit=pulse_entry_exit,
            pattern_fade=pattern_fade,
            dead_end_shimmer=dead_end_shimmer,
            seed_slideshow=seed_slideshow,
            stats_ticker=stats_ticker,
        )

    @staticmethod
    def _parse_int(key: str, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                f"Key {key}: expected an integer, got '{value}'."
            )

    @staticmethod
    def _parse_positive_int(key: str, value: str) -> int:
        try:
            n = int(value)
        except ValueError:
            raise ValueError(
                f"Key {key}: expected a positive integer, got '{value}'."
            )
        if n < 1:
            raise ValueError(
                f"Key {key}: value must be >= 1, got {n}."
            )
        return n

    @staticmethod
    def _parse_bool(key: str, value: str) -> bool:
        normalised = value.strip().lower()
        if normalised == "true":
            return True
        if normalised == "false":
            return False
        raise ValueError(
            f"Key {key}: expected True/False, got '{value}'."
        )

    @staticmethod
    def _parse_coord(
        key: str,
        value: str,
        width: int,
        height: int,
    ) -> tuple[int, int]:
        parts = value.split(",")
        if len(parts) != 2:
            raise ValueError(
                f"Key {key}: expected format 'x,y', got '{value}'."
            )
        try:
            x, y = int(parts[0].strip()), int(parts[1].strip())
        except ValueError:
            raise ValueError(
                f"Key {key}: coordinates must be integers, got '{value}'."
            )
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(
                f"Key {key}: coordinate ({x},{y}) is outside the "
                f"{width}×{height} grid."
            )
        return (x, y)

    @staticmethod
    def _is_border_cell(
        coord: tuple[int, int],
        width: int,
        height: int,
    ) -> bool:
        x, y = coord
        return x == 0 or x == width - 1 or y == 0 or y == height - 1
