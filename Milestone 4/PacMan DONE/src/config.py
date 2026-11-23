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
    "level_max_time": 224,
    "level": [{"width": 17, "height": 17}] * 10,
}

INT_CLAMPS: dict[str, tuple[int, int]] = {
    "lives": (1, 99),
    "pacgum": (1, 2500),
    "points_per_pacgum": (1, 10000),
    "points_per_super_pacgum": (1, 10000),
    "points_per_ghost": (1, 10000),
    "seed": (0, 2**32 - 1),
    "level_max_time": (10, 999),
}


def _get_int(data: dict[str, Any], key: str) -> int:
    """Lê, valida e limita uma opção numérica da configuração.

    Args:
        data: Opções carregadas do arquivo JSON.
        key: Nome da opção a validar.

    Returns:
        Valor inteiro padrão, convertido ou limitado ao intervalo permitido.

    É chamada durante a leitura da configuração, antes de criar a partida.
    """
    default = DEFAULTS[key]
    if key not in data:
        logger.warning(
            "Config: '%s' missing, using default %s", key, default
        )
        return int(default)
    raw = data[key]
    try:
        if isinstance(raw, bool):
            raise TypeError("Boolean value is not a valid integer")
        val = int(raw)
    except (TypeError, ValueError):
        logger.warning("Config: '%s' invalid, using default %s", key, default)
        return int(default)
    lo, hi = INT_CLAMPS[key]
    if val < lo or val > hi:
        clamped = max(lo, min(hi, val))
        logger.warning("Config: '%s' clamped %d -> %d", key, val, clamped)
        return clamped
    return val


def _parse_levels(raw_levels: Any) -> list[dict[str, int]]:
    """Valida dimensões dos labirintos e completa a lista até dez níveis.

    Args:
        raw_levels: Lista de dimensões recebida do arquivo JSON.

    Returns:
        Níveis com largura e altura válidas, sempre com pelo menos dez itens.

    É usada ao carregar a configuração para que cada etapa da partida tenha
    um labirinto utilizável.
    """
    if not isinstance(raw_levels, list) or len(raw_levels) == 0:
        logger.warning("Config: 'level' missing/empty, using 10 defaults")
        return [{"width": 17, "height": 17}] * 10
    parsed: list[dict[str, int]] = []
    for i, lvl in enumerate(raw_levels):
        if not isinstance(lvl, dict):
            logger.warning(
                "Config: level %d invalid, using default 17x17", i + 1
            )
            parsed.append({"width": 17, "height": 17})
            continue
        try:
            if "width" not in lvl or "height" not in lvl:
                logger.warning(
                    "Config: level %d missing dimension, using default 17",
                    i + 1,
                )
            raw_w = lvl.get("width", 17)
            raw_h = lvl.get("height", 17)
            if isinstance(raw_w, bool) or isinstance(raw_h, bool):
                raise TypeError("Boolean dimension not allowed")
            orig_w = int(raw_w)
            orig_h = int(raw_h)
            w = max(11, min(61, orig_w))
            h = max(11, min(31, orig_h))
            if w % 2 == 0:
                w += 1
            if h % 2 == 0:
                h += 1
            if (w, h) != (orig_w, orig_h):
                logger.warning(
                    "Config: level %d size %dx%d adjusted to %dx%d",
                    i + 1,
                    orig_w,
                    orig_h,
                    w,
                    h,
                )
        except (TypeError, ValueError):
            logger.warning(
                "Config: level %d invalid size, using default 17x17", i + 1
            )
            w, h = 17, 17
        parsed.append({"width": w, "height": h})
    if len(parsed) < 10:
        logger.warning(
            "Config: fewer than 10 levels (%d), padding to 10", len(parsed)
        )
        while len(parsed) < 10:
            parsed.append({"width": 17, "height": 17})
    return parsed


class Config:
    """Store validated configuration values for a game session."""
    def __init__(self, highscore_filename: str, lives: int, pacgum: int,
                 points_per_pacgum: int, points_per_super_pacgum: int,
                 points_per_ghost: int, seed: int, level_max_time: int,
                 levels: list[dict[str, int]]) -> None:
        """Guarda as opções já validadas para uma sessão de jogo.

        Args:
            highscore_filename: Caminho do arquivo de recordes.
            lives: Vidas iniciais do jogador.
            pacgum: Quantidade máxima de itens comuns por nível.
            points_per_pacgum: Pontos por item comum.
            points_per_super_pacgum: Pontos por item de poder.
            points_per_ghost: Pontos por fantasma comido.
            seed: Semente para geração reproduzível dos labirintos.
            level_max_time: Tempo base de cada nível.
            levels: Dimensões validadas dos labirintos.

        É construída por ``load_config`` antes de ``Game`` iniciar.
        """
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
    """Remove linhas de comentário antes de interpretar o JSON.

    Args:
        text: Conteúdo original do arquivo de configuração.

    Returns:
        Texto sem linhas iniciadas por ``#`` ou ``//``.

    É usada por ``load_config`` para aceitar comentários de linha inteira.
    """
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def load_config(path: str) -> Config:
    """Carrega o JSON e monta a configuração validada da partida.

    Args:
        path: Caminho do arquivo informado ao iniciar o programa.

    Returns:
        Objeto ``Config`` com valores padrão aplicados e opções verificadas.

    É chamada pelo ponto de entrada antes de construir a instância do jogo.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except OSError as exc:
        raise SystemExit(
            f"Error: could not read config file '{path}': {exc}"
        )
    try:
        data: dict[str, Any] = json.loads(_strip_comment_lines(raw_text))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Error: config file '{path}' is not valid JSON: {exc}"
        )
    if not isinstance(data, dict):
        raise SystemExit(
            "Error: config file must contain a JSON object at the root."
        )
    if "highscore_filename" not in data:
        logger.warning(
            "Config: 'highscore_filename' missing, using default '%s'",
            DEFAULTS["highscore_filename"],
        )
        hf: Any = DEFAULTS["highscore_filename"]
    else:
        hf = data["highscore_filename"]
        if not isinstance(hf, str) or not hf.strip():
            logger.warning(
                "Config: 'highscore_filename' invalid, using default '%s'",
                DEFAULTS["highscore_filename"],
            )
            hf = DEFAULTS["highscore_filename"]
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
