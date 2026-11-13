import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "highscore_filename": "data/highscores.json",
    "lives": 3,
    "pacgum": 42,
    "points_per_pacgum": 10,
    "points_per_super_pacgum": 50,
    "points_per_ghost": 200,
    "seed": 42,
    "level_max_time": 90,
    "level": [{"width": 21, "height": 21}] * 10,
}

INT_CLAMPS: dict[str, tuple[int, int]] = {
    "lives": (1, 10),
    "pacgum": (1, 500),
    "points_per_pacgum": (1, 10000),
    "points_per_super_pacgum": (1, 10000),
    "points_per_ghost": (1, 10000),
    "seed": (0, 2**32 - 1),
    "level_max_time": (10, 600),
}


def _get_int(data: dict[str, Any], key: str) -> int:
    default = DEFAULTS[key]
    if key not in data:
        logger.warning("Config: '%s' missing, using default %s", key, default)
        return int(default)
    raw = data.get(key, default)
    try:
        val = int(raw)
    except (TypeError, ValueError, OverflowError):
        logger.warning("Config: '%s' invalid, using default %s", key, default)
        return int(default)
    lo, hi = INT_CLAMPS[key]
    if val < lo or val > hi:
        clamped = max(lo, min(hi, val))
        logger.warning("Config: '%s' clamped %d -> %d", key, val, clamped)
        return clamped
    return val


def _parse_levels(raw_levels: Any) -> list[dict[str, int]]:
    if not isinstance(raw_levels, list) or len(raw_levels) == 0:
        logger.warning("Config: 'level' missing/empty, using 10 defaults")
        return [{"width": 21, "height": 21}] * 10
    parsed: list[dict[str, int]] = []
    for i, lvl in enumerate(raw_levels):
        if not isinstance(lvl, dict):
            logger.warning(
                "Config: 'level[%d]' invalid, using default 21x21", i + 1)
            parsed.append({"width": 21, "height": 21})
            continue
        missing_dimensions = [
            dimension for dimension in ("width", "height")
            if dimension not in lvl
        ]
        if missing_dimensions:
            logger.warning(
                "Config: 'level[%d]' missing %s, using 21 for missing "
                "dimension(s)",
                i + 1,
                ", ".join(missing_dimensions))
        try:
            raw_width = int(lvl.get("width", 21))
            raw_height = int(lvl.get("height", 21))
        except (TypeError, ValueError, OverflowError):
            logger.warning(
                "Config: 'level[%d]' has invalid dimensions, using 21x21",
                i + 1)
            w, h = 21, 21
        else:
            w = max(11, min(51, raw_width))
            h = max(11, min(51, raw_height))
            if w != raw_width:
                logger.warning(
                    "Config: 'level[%d].width' clamped %d -> %d",
                    i + 1,
                    raw_width,
                    w)
            if h != raw_height:
                logger.warning(
                    "Config: 'level[%d].height' clamped %d -> %d",
                    i + 1,
                    raw_height,
                    h)
            if w % 2 == 0:
                logger.warning(
                    "Config: 'level[%d].width' rounded up %d -> %d",
                    i + 1,
                    w,
                    w + 1)
                w += 1
            if h % 2 == 0:
                logger.warning(
                    "Config: 'level[%d].height' rounded up %d -> %d",
                    i + 1,
                    h,
                    h + 1)
                h += 1
        parsed.append({"width": w, "height": h})
    while len(parsed) < 10:
        parsed.append({"width": 21, "height": 21})
    return parsed


class Config:

    def __init__(self, highscore_filename: str, lives: int, pacgum: int,
                 points_per_pacgum: int, points_per_super_pacgum: int,
                 points_per_ghost: int, seed: int, level_max_time: int,
                 levels: list[dict[str, int]]) -> None:
        self.highscore_filename = highscore_filename
        self.lives = lives
        self.pacgum = pacgum
        self.points_per_pacgum = points_per_pacgum
        self.points_per_super_pacgum = points_per_super_pacgum
        self.points_per_ghost = points_per_ghost
        self.seed = seed
        self.level_max_time = level_max_time
        self.levels = levels


def _strip_comment_lines(text: str) -> str:
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def load_config(path: str) -> Config:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except OSError as exc:
        raise SystemExit(f"Error: could not read config file '{path}': {exc}")
    try:
        data: dict[str, Any] = json.loads(_strip_comment_lines(raw_text))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Error: config file '{path}' is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(
            "Error: config file must contain a JSON object at the root.")
    if "highscore_filename" not in data:
        logger.warning(
            "Config: 'highscore_filename' missing, using default %s",
            DEFAULTS["highscore_filename"])
    hf = data.get("highscore_filename", DEFAULTS["highscore_filename"])
    if not isinstance(hf, str) or not hf.strip():
        logger.warning(
            "Config: 'highscore_filename' invalid, using default %s",
            DEFAULTS["highscore_filename"])
        hf = str(DEFAULTS["highscore_filename"])
    return Config(
        highscore_filename=str(hf),
        lives=_get_int(data, "lives"),
        pacgum=_get_int(data, "pacgum"),
        points_per_pacgum=_get_int(data, "points_per_pacgum"),
        points_per_super_pacgum=_get_int(data, "points_per_super_pacgum"),
        points_per_ghost=_get_int(data, "points_per_ghost"),
        seed=_get_int(data, "seed"),
        level_max_time=_get_int(data, "level_max_time"),
        levels=_parse_levels(data.get("level")),
    )
