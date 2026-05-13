from __future__ import annotations

import math
import os
import sys
import time
import zipfile
from typing import Any

try:
    import mlx
    _mlx_available = True
except ImportError:
    _mlx_available = False
    _root = os.path.dirname(os.path.abspath(__file__))
    _wheel_candidates = [
        os.path.join(_root, "mlx-2.2-py3-ubuntu-any.whl"),
        os.path.join(_root, "mlx-2.2-py3-fedora-any.whl"),
    ]
    for _wheel in _wheel_candidates:
        if os.path.isfile(_wheel):
            _extract_root = os.path.join(_root, ".mlx_cache")
            _extract_dir = os.path.join(
                _extract_root,
                os.path.basename(_wheel).replace(".whl", ""),
            )
            if not os.path.isdir(_extract_dir):
                os.makedirs(_extract_dir, exist_ok=True)
                try:
                    with zipfile.ZipFile(_wheel, "r") as zf:
                        zf.extractall(_extract_dir)
                except (OSError, zipfile.BadZipFile):
                    continue

            sys.path.insert(0, _extract_dir)
            try:
                import mlx  # noqa: F401
                _mlx_available = True
            except ImportError:
                _mlx_available = False
            finally:
                if sys.path[0] == _extract_dir:
                    sys.path.pop(0)
            if _mlx_available:
                break

import random

from config_parser import MazeConfig
from mazegen.generator import MazeGenerator
from mazegen.maze import EAST, NORTH, SOUTH, WEST, MazeGrid
from mazegen.solver import MazeSolver, NoPathError


COLOUR_PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((220, 220, 220), (30, 30, 30)),
    ((180, 120, 40), (20, 20, 20)),
    ((0, 150, 80), (0, 20, 10)),
    ((60, 120, 200), (10, 10, 40)),
    ((200, 60, 60), (30, 0, 0)),
]

COLORBLIND_PALETTES: list[
    tuple[tuple[int, int, int], tuple[int, int, int]]
] = [
    ((230, 230, 230), (20, 20, 20)),
    ((255, 230, 120), (10, 10, 10)),
    ((120, 200, 255), (10, 10, 10)),
    ((170, 240, 160), (10, 10, 10)),
    ((255, 180, 180), (10, 10, 10)),
]

ENTRY_COLOUR = (200, 50, 200)
EXIT_COLOUR = (200, 50, 50)
DUCK_COLOUR = (250, 220, 90)

ANIMATE_INTERVALS = [0.005, 0.12, 0.5]

UI_HEIGHT = 56
WALL_THICKNESS = 2

KEY_QUIT = {53, 65307, 113}
KEY_REGEN = {15, 114}
KEY_PATH = {35, 112, 49}
KEY_PALETTE = {8, 99, 50}
KEY_PATTERN = {4, 104, 51}
KEY_SPEED_PATH = {1, 115}
KEY_SPEED_EFFECTS = {14, 101}
KEY_PATH_SPEED_SLOW = {91}
KEY_PATH_SPEED_FAST = {93}
KEY_FX_SPEED_SLOW = {45}
KEY_FX_SPEED_FAST = {61}
KEY_DUCKS = {2, 100}
KEY_DUCKS_ANIM = {32, 117}
KEY_AUTO_PALETTE = {0, 97}
KEY_PULSE = {31, 111}
KEY_PATTERN_FADE = {3, 102}
KEY_SHIMMER = {46, 109}
KEY_STATS = {17, 116}
KEY_SLIDESHOW = {37, 108}


class MlxRenderer:
    def __init__(
        self,
        grid: MazeGrid | None = None,
        cell_size: int = 28,
        generator: MazeGenerator | None = None,
        cfg: MazeConfig | None = None,
    ) -> None:
        if not _mlx_available:
            raise ImportError(
                "mlx is not installed. Run 'make install' to install the "
                "bundled wheel."
            )
        self.grid = grid
        self.cell_size = cell_size
        self.generator = generator
        self.cfg = cfg

        self._mlx: Any = None
        self._mlx_ptr: Any = None
        self._win_ptr: Any = None
        self._img_ptr: Any = None
        self._img_data: Any = None
        self._img_stride = 0
        self._img_format = 0
        self._win_w = 0
        self._win_h = 0
        self._show_path = False
        self._palette_idx = 0
        self._palettes = _get_palettes(cfg)
        self._path_cells: list[tuple[int, int]] = []
        self._pattern_cells: set[tuple[int, int]] = set()
        self._show_pattern = True
        self._animate = False
        self._animating = False
        self._anim_visible_count = 0
        self._last_anim_time = 0.0
        self._path_speed_idx = 1
        self._fx_speed_idx = 1
        self._solution_colour = _random_colour()
        self._pattern_colour = _random_colour()
        self._ducks_enabled = bool(
            cfg is not None and (cfg.ducks or cfg.ducks_count > 0)
        )
        self._duck_count = cfg.ducks_count if cfg is not None else 0
        self._ducks_animate = cfg.ducks_animate if cfg is not None else False
        self._duck_rng = random.Random(
            cfg.seed if cfg is not None and cfg.seed is not None else None
        )
        self._duck_cells: set[tuple[int, int]] = set()
        self._duck_last_time = 0.0
        self._duck_interval = 0.25
        self._auto_palette = cfg.auto_palette if cfg is not None else False
        self._pulse_entry_exit = (
            cfg.pulse_entry_exit if cfg is not None else False
        )
        self._pattern_fade = cfg.pattern_fade if cfg is not None else False
        self._dead_end_shimmer = (
            cfg.dead_end_shimmer if cfg is not None else False
        )
        self._seed_slideshow = (
            cfg.seed_slideshow if cfg is not None else False
        )
        self._stats_ticker = cfg.stats_ticker if cfg is not None else False
        self._dead_end_cells: list[tuple[int, int]] = []
        self._palette_last_time = 0.0
        self._pulse_last_time = 0.0
        self._shimmer_last_time = 0.0
        self._slideshow_last_time = 0.0
        self._stats_last_time = 0.0
        self._base_interval = ANIMATE_INTERVALS[self._fx_speed_idx]
        self._palette_interval = self._base_interval * 12.0
        self._pulse_interval = self._base_interval * 8.0
        self._shimmer_interval = self._base_interval * 6.0
        self._slideshow_interval = self._base_interval * 60.0
        self._stats_interval = self._base_interval * 20.0
        self._update_animation_intervals()

    def render(
        self,
        grid: MazeGrid | None = None,
        show_path: bool = False,
        path_cells: list[tuple[int, int]] | None = None,
    ) -> None:
        current_grid = grid or self.grid
        if current_grid is None:
            raise ValueError("No maze grid provided to MlxRenderer.render().")

        self._show_path = show_path
        self._path_cells = path_cells or _solve_path_cells(current_grid)
        if self.generator is not None:
            self._pattern_cells = self.generator.pattern_cells
        if self.cfg is not None:
            self._animate = self.cfg.animate

        self._mlx = mlx.Mlx()
        self._mlx_ptr = self._mlx.mlx_init()
        if not self._mlx_ptr:
            raise RuntimeError("mlx_init() failed.")

        win_w = current_grid.width * self.cell_size + 2
        win_h = current_grid.height * self.cell_size + 2 + UI_HEIGHT
        self._win_w = win_w
        self._win_h = win_h
        self._win_ptr = self._mlx.mlx_new_window(
            self._mlx_ptr,
            win_w,
            win_h,
            "A-Maze-ing",
        )
        if not self._win_ptr:
            raise RuntimeError("mlx_new_window() failed.")

        self._img_ptr = self._mlx.mlx_new_image(self._mlx_ptr, win_w, win_h)
        if not self._img_ptr:
            raise RuntimeError("mlx_new_image() failed.")

        data, _bpp, stride, fmt = self._mlx.mlx_get_data_addr(self._img_ptr)
        self._img_data = data
        self._img_stride = stride
        self._img_format = fmt

        self._randomize_bonus_colours()
        self._reset_ducks(current_grid)
        self._update_dead_ends(current_grid)

        print(
            "MLX controls: R regen | P path | C colors | H 42 | S path | "
            "| D ducks | "
            "| Q quit"
        )

        self._redraw(current_grid)

        if self._animate:
            self._start_animation()

        self._mlx.mlx_key_hook(self._win_ptr, _mlx_key_dispatch, self)
        self._mlx.mlx_hook(self._win_ptr, 33, 0, _mlx_close_dispatch, self)
        self._mlx.mlx_loop_hook(self._mlx_ptr, _mlx_loop_dispatch, self)

        self._mlx.mlx_loop(self._mlx_ptr)

    def _redraw(self, grid: MazeGrid) -> None:
        if self._img_data is None:
            return
        self._clear_image()
        self._draw_maze(grid)
        self._mlx.mlx_put_image_to_window(
            self._mlx_ptr,
            self._win_ptr,
            self._img_ptr,
            0,
            0,
        )
        self._draw_ui()

    def _clear_image(self) -> None:
        self._fill_rect(0, 0, self._win_w, self._win_h, (10, 10, 10))

    def _draw_maze(self, grid: MazeGrid) -> None:
        wall_col, pass_col = self._palettes[
            self._palette_idx % len(self._palettes)
        ]
        now = time.monotonic()
        pulse_factor = _pulse_factor(now, self._pulse_interval)
        shimmer_phase = int(now / max(self._shimmer_interval, 0.001))
        if self._animating:
            solution_cells = set(
                self._path_cells[: self._anim_visible_count]
            )
        else:
            solution_cells = set(self._path_cells)

        for y in range(grid.height):
            for x in range(grid.width):
                cell_px = x * self.cell_size + 1
                cell_py = y * self.cell_size + 1

                if (x, y) == grid.entry:
                    fill = (
                        _scale_colour(ENTRY_COLOUR, pulse_factor)
                        if self._pulse_entry_exit
                        else ENTRY_COLOUR
                    )
                elif (x, y) == grid.exit_:
                    fill = (
                        _scale_colour(EXIT_COLOUR, pulse_factor)
                        if self._pulse_entry_exit
                        else EXIT_COLOUR
                    )
                elif self._show_path and (x, y) in solution_cells:
                    fill = self._solution_colour
                elif self._show_pattern and (x, y) in self._pattern_cells:
                    if self._pattern_fade:
                        fade_factor = _pulse_factor(
                            now + 0.5,
                            self._pulse_interval,
                        )
                        fill = _scale_colour(self._pattern_colour, fade_factor)
                    else:
                        fill = self._pattern_colour
                elif (x, y) in self._duck_cells:
                    fill = DUCK_COLOUR
                elif self._dead_end_shimmer and (x, y) in self._dead_end_cells:
                    if ((x + y + shimmer_phase) % 6) == 0:
                        fill = (255, 255, 255)
                    else:
                        fill = pass_col
                else:
                    fill = pass_col

                self._fill_rect(
                    cell_px,
                    cell_py,
                    self.cell_size,
                    self.cell_size,
                    fill,
                )

                if grid.has_wall(x, y, NORTH):
                    self._fill_rect(
                        cell_px,
                        cell_py,
                        self.cell_size,
                        WALL_THICKNESS,
                        wall_col,
                    )
                if grid.has_wall(x, y, SOUTH):
                    self._fill_rect(
                        cell_px,
                        cell_py + self.cell_size - WALL_THICKNESS,
                        self.cell_size,
                        WALL_THICKNESS,
                        wall_col,
                    )
                if grid.has_wall(x, y, WEST):
                    self._fill_rect(
                        cell_px,
                        cell_py,
                        WALL_THICKNESS,
                        self.cell_size,
                        wall_col,
                    )
                if grid.has_wall(x, y, EAST):
                    self._fill_rect(
                        cell_px + self.cell_size - WALL_THICKNESS,
                        cell_py,
                        WALL_THICKNESS,
                        self.cell_size,
                        wall_col,
                    )

    def _draw_ui(self) -> None:
        if self._mlx is None:
            return
        text_y = self.cell_size * (self.grid.height if self.grid else 0) + 10
        self._mlx.mlx_string_put(
            self._mlx_ptr,
            self._win_ptr,
            10,
            text_y,
            0xFFFFFF,
            "R regen | P path | C colors | H 42 | S path | Q quit",
        )

    def _fill_rect(self, x: int, y: int, w: int, h: int,
                   color: tuple[int, int, int]) -> None:
        if self._img_data is None:
            return
        r, g, b = color
        for py in range(y, y + h):
            row = py * self._img_stride
            for px in range(x, x + w):
                idx = row + px * 4
                if self._img_format == 0:
                    self._img_data[idx] = b
                    self._img_data[idx + 1] = g
                    self._img_data[idx + 2] = r
                    self._img_data[idx + 3] = 255
                else:
                    self._img_data[idx] = 255
                    self._img_data[idx + 1] = r
                    self._img_data[idx + 2] = g
                    self._img_data[idx + 3] = b

    def _randomize_bonus_colours(self) -> None:
        self._solution_colour = _random_colour()
        self._pattern_colour = _random_colour()

    def _reset_ducks(self, grid: MazeGrid) -> None:
        if not self._ducks_enabled or self._duck_count <= 0:
            self._duck_cells = set()
            return
        self._duck_cells = _pick_duck_cells(
            grid,
            self._duck_count,
            self._duck_rng,
            self._pattern_cells,
            set(self._path_cells),
        )

    def _update_dead_ends(self, grid: MazeGrid) -> None:
        self._dead_end_cells = _find_dead_ends(grid)

    def _update_animation_intervals(self) -> None:
        self._base_interval = ANIMATE_INTERVALS[self._fx_speed_idx]
        self._duck_interval = self._base_interval * 6.0
        self._palette_interval = self._base_interval * 12.0
        self._pulse_interval = self._base_interval * 8.0
        self._shimmer_interval = self._base_interval * 6.0
        self._slideshow_interval = self._base_interval * 60.0
        self._stats_interval = self._base_interval * 20.0

    def _handle_key(self, keynum: int) -> None:
        if keynum in KEY_QUIT:
            self._mlx.mlx_loop_exit(self._mlx_ptr)
            return

        if keynum in KEY_REGEN:
            self._randomize_bonus_colours()
            self._regenerate()
            return

        if keynum in KEY_PATH:
            self._show_path = not self._show_path
            self._animating = False
            if self._show_path:
                self._anim_visible_count = len(self._path_cells)
            else:
                self._anim_visible_count = 0
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_PALETTE:
            self._palette_idx = (self._palette_idx + 1) % len(self._palettes)
            self._randomize_bonus_colours()
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_PATTERN:
            self._show_pattern = not self._show_pattern
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_SPEED_PATH:
            self._path_speed_idx = (self._path_speed_idx + 1) % len(
                ANIMATE_INTERVALS
            )
            if self._show_path and self.grid is not None:
                self._animating = True
                self._anim_visible_count = 1
                self._last_anim_time = 0.0
                self._redraw(self.grid)
            return

        if keynum in KEY_SPEED_EFFECTS:
            self._fx_speed_idx = (self._fx_speed_idx + 1) % len(
                ANIMATE_INTERVALS
            )
            self._update_animation_intervals()
            return

        if keynum in KEY_PATH_SPEED_SLOW:
            self._path_speed_idx = _clamp_speed(self._path_speed_idx + 1)
            return

        if keynum in KEY_PATH_SPEED_FAST:
            self._path_speed_idx = _clamp_speed(self._path_speed_idx - 1)
            return

        if keynum in KEY_FX_SPEED_SLOW:
            self._fx_speed_idx = _clamp_speed(self._fx_speed_idx + 1)
            self._update_animation_intervals()
            return

        if keynum in KEY_FX_SPEED_FAST:
            self._fx_speed_idx = _clamp_speed(self._fx_speed_idx - 1)
            self._update_animation_intervals()
            return

        if keynum in KEY_DUCKS:
            self._ducks_enabled = not self._ducks_enabled
            if self.grid is not None:
                self._reset_ducks(self.grid)
                self._redraw(self.grid)
            return

        if keynum in KEY_DUCKS_ANIM:
            self._ducks_animate = not self._ducks_animate
            return

        if keynum in KEY_AUTO_PALETTE:
            self._auto_palette = not self._auto_palette
            return

        if keynum in KEY_PULSE:
            self._pulse_entry_exit = not self._pulse_entry_exit
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_PATTERN_FADE:
            self._pattern_fade = not self._pattern_fade
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_SHIMMER:
            self._dead_end_shimmer = not self._dead_end_shimmer
            if self.grid is not None:
                self._redraw(self.grid)
            return

        if keynum in KEY_STATS:
            self._stats_ticker = not self._stats_ticker
            return

        if keynum in KEY_SLIDESHOW:
            self._seed_slideshow = not self._seed_slideshow
            return

    def _loop_hook(self) -> int:
        now = time.monotonic()

        if (
            self._ducks_animate
            and (now - self._duck_last_time) >= self._duck_interval
        ):
            self._duck_last_time = now
            if self.grid is not None:
                self._reset_ducks(self.grid)
                self._redraw(self.grid)

        if (
            self._auto_palette
            and (now - self._palette_last_time) >= self._palette_interval
        ):
            self._palette_last_time = now
            self._palette_idx = (self._palette_idx + 1) % len(self._palettes)
            if self.grid is not None:
                self._redraw(self.grid)

        if (
            self._seed_slideshow
            and (now - self._slideshow_last_time) >= self._slideshow_interval
        ):
            self._slideshow_last_time = now
            self._regenerate()

        if (
            self._stats_ticker
            and (now - self._stats_last_time) >= self._stats_interval
        ):
            self._stats_last_time = now
            if self.grid is not None:
                _print_stats_ticker(
                    self.grid,
                    self._path_cells,
                    self._dead_end_cells,
                )

        if not self._animating:
            return 0

        interval = ANIMATE_INTERVALS[self._path_speed_idx]
        if now - self._last_anim_time < interval:
            return 0

        self._last_anim_time = now

        if self._anim_visible_count < len(self._path_cells):
            self._anim_visible_count += 1
            if self.grid is not None:
                self._redraw(self.grid)
        else:
            self._animating = False

        return 0

    def _regenerate(self) -> None:
        if self.cfg is None:
            return
        seed = self.cfg.seed
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        else:
            seed += random.randint(1, 9999)

        try:
            new_gen = MazeGenerator(
                width=self.cfg.width,
                height=self.cfg.height,
                seed=seed,
                perfect=self.cfg.perfect,
                algorithm=self.cfg.algorithm,
            )
            new_grid = new_gen.generate(
                entry=self.cfg.entry,
                exit_=self.cfg.exit_,
            )
            self.generator = new_gen
            self.grid = new_grid
            self._pattern_cells = new_gen.pattern_cells
            self._path_cells = _solve_path_cells(new_grid)
            self._randomize_bonus_colours()
            self._reset_ducks(new_grid)
            self._update_dead_ends(new_grid)
            if self._animate:
                self._start_animation()
            else:
                self._animating = False
                self._anim_visible_count = len(self._path_cells)
            self._redraw(new_grid)
        except (ValueError, RuntimeError, NoPathError) as exc:
            print(f"[mlx] Re-generation error: {exc}", file=sys.stderr)

    def _start_animation(self) -> None:
        if not self._path_cells:
            return
        self._show_path = True
        self._animating = True
        self._anim_visible_count = 1
        self._last_anim_time = 0.0


def _solve_path_cells(grid: MazeGrid) -> list[tuple[int, int]]:
    solver = MazeSolver(grid)
    solver.solve()
    return solver.get_path_cells()


def _random_colour() -> tuple[int, int, int]:
    return (
        random.randint(50, 230),
        random.randint(50, 230),
        random.randint(50, 230),
    )


def _pulse_factor(now: float, interval: float) -> float:
    if interval <= 0:
        return 1.0
    phase = (now % interval) / interval
    return 0.5 + 0.5 * math.sin(phase * math.tau)


def _scale_colour(
    colour: tuple[int, int, int],
    factor: float,
) -> tuple[int, int, int]:
    factor = max(0.2, min(1.0, factor))
    return (
        int(colour[0] * factor),
        int(colour[1] * factor),
        int(colour[2] * factor),
    )


def _clamp_speed(idx: int) -> int:
    return max(0, min(len(ANIMATE_INTERVALS) - 1, idx))


def _find_dead_ends(grid: MazeGrid) -> list[tuple[int, int]]:
    dead_ends: list[tuple[int, int]] = []
    for y in range(grid.height):
        for x in range(grid.width):
            walls = 0
            if grid.has_wall(x, y, NORTH):
                walls += 1
            if grid.has_wall(x, y, EAST):
                walls += 1
            if grid.has_wall(x, y, SOUTH):
                walls += 1
            if grid.has_wall(x, y, WEST):
                walls += 1
            if walls >= 3:
                dead_ends.append((x, y))
    return dead_ends


def _print_stats_ticker(
    grid: MazeGrid,
    path_cells: list[tuple[int, int]] | None,
    dead_end_cells: list[tuple[int, int]],
) -> None:
    steps = max(0, len(path_cells or []) - 1)
    print(
        f"[stats] dead-ends {len(dead_end_cells)} | path {steps} steps | "
        f"palette {grid.width}x{grid.height}"
    )


def _pick_duck_cells(
    grid: MazeGrid,
    count: int,
    rng: random.Random,
    pattern_cells: set[tuple[int, int]] | None,
    path_cells: set[tuple[int, int]] | None,
) -> set[tuple[int, int]]:
    if count <= 0:
        return set()

    avoid = set(pattern_cells or [])
    avoid.update(path_cells or [])
    avoid.add(grid.entry)
    avoid.add(grid.exit_)

    candidates: list[tuple[int, int]] = []
    for y in range(grid.height):
        for x in range(grid.width):
            coord = (x, y)
            if coord in avoid:
                continue
            candidates.append(coord)

    if not candidates:
        return set()

    if count >= len(candidates):
        return set(candidates)

    return set(rng.sample(candidates, count))


def _get_palettes(
    cfg: MazeConfig | None,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    if cfg is not None and cfg.palette == "colorblind":
        return COLORBLIND_PALETTES
    return COLOUR_PALETTES


def _mlx_key_dispatch(keynum: int, renderer: "MlxRenderer") -> None:
    renderer._handle_key(keynum)


def _mlx_loop_dispatch(renderer: "MlxRenderer") -> int:
    return renderer._loop_hook()


def _mlx_close_dispatch(renderer: "MlxRenderer") -> None:
    if renderer._mlx is not None and renderer._mlx_ptr is not None:
        renderer._mlx.mlx_loop_exit(renderer._mlx_ptr)
