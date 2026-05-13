from __future__ import annotations

import math
import os
import random
import sys
import time
from typing import Optional

from config_parser import MazeConfig
from mazegen.generator import MazeGenerator
from mazegen.maze import EAST, NORTH, SOUTH, WEST, MazeGrid
from mazegen.solver import MazeSolver, NoPathError


ANSI_RESET = "\033[0m"


def _ansi_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


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
SOLUTION_COLOUR = (50, 200, 220)
PATTERN_42_COLOUR = (100, 80, 180)
DUCK_COLOUR = (250, 220, 90)

ANIMATE_SPEEDS = [0.005, 0.12, 0.5]

CELL_W = 3


class AsciiRenderer:
    def __init__(
        self,
        grid: MazeGrid | None = None,
        generator: MazeGenerator | None = None,
        cfg: MazeConfig | None = None,
    ) -> None:
        self.grid = grid
        self.generator = generator
        self.cfg = cfg

    def render(
        self,
        grid: MazeGrid | None = None,
        show_path: bool = False,
        path_cells: list[tuple[int, int]] | None = None,
    ) -> None:
        current_grid = grid or self.grid
        if current_grid is None:
            raise ValueError(
                "No maze grid provided to AsciiRenderer.render()."
            )

        if (
            self.generator is not None
            and self.cfg is not None
            and self.cfg.seed_slideshow
        ):
            self._slideshow_loop(current_grid)
            return

        if self.generator is not None and self.cfg is not None:
            self._interactive_loop(
                current_grid,
                show_path=show_path,
                path_cells=path_cells,
            )
        else:
            palettes = _get_palettes(self.cfg)
            duck_cells: set[tuple[int, int]] = set()
            ducks_enabled, ducks_count, _ = _get_duck_config(self.cfg)
            if ducks_enabled:
                duck_cells = _pick_duck_cells(
                    current_grid,
                    ducks_count,
                    _get_duck_rng(self.cfg),
                    None,
                    set(path_cells or []),
                )
            lines = _build_display_lines(
                current_grid,
                show_solution=show_path,
                palette_idx=0,
                palettes=palettes,
                duck_cells=duck_cells,
                path_cells=path_cells,
                pattern_cells=None,
                show_pattern=True,
                now=time.monotonic(),
                pulse_entry_exit=False,
                pattern_fade=False,
                dead_end_shimmer=False,
            )
            _print_maze(lines)

    def _interactive_loop(
        self,
        grid: MazeGrid,
        show_path: bool = False,
        path_cells: list[tuple[int, int]] | None = None,
    ) -> None:
        cfg = self.cfg
        show_solution = show_path
        show_pattern = True
        palette_idx = 0
        rng_counter = 0
        path_speed_idx = 1
        fx_speed_idx = 1
        palettes = _get_palettes(cfg)
        duck_rng = _get_duck_rng(cfg)
        ducks_enabled, ducks_count, ducks_animate = _get_duck_config(
            cfg
        )
        auto_palette = cfg.auto_palette if cfg is not None else False
        pulse_entry_exit = cfg.pulse_entry_exit if cfg is not None else False
        pattern_fade = cfg.pattern_fade if cfg is not None else False
        dead_end_shimmer = cfg.dead_end_shimmer if cfg is not None else False
        stats_ticker = cfg.stats_ticker if cfg is not None else False
        seed_slideshow = cfg.seed_slideshow if cfg is not None else False
        duck_cells: set[tuple[int, int]] = set()

        current_grid = grid
        current_gen = self.generator
        current_path = path_cells or _solve_path_cells(current_grid)

        if cfg is not None and cfg.animate:
            pattern_cells = (
                current_gen.pattern_cells if current_gen is not None else None
            )
            _animate_solution(
                current_grid,
                current_path,
                palette_idx,
                palettes,
                duck_cells,
                pattern_cells,
                show_pattern,
                ANIMATE_SPEEDS[path_speed_idx],
                pulse_entry_exit=pulse_entry_exit,
                pattern_fade=pattern_fade,
                dead_end_shimmer=dead_end_shimmer,
            )
            show_solution = True
            {fx_speed_idx, seed_slideshow}
        while True:
            pattern_cells = (
                current_gen.pattern_cells if current_gen is not None else None
            )
            if ducks_enabled:
                if ducks_animate or not duck_cells:
                    duck_cells = _pick_duck_cells(
                        current_grid,
                        ducks_count,
                        duck_rng,
                        pattern_cells,
                        set(current_path),
                    )
            lines = _build_display_lines(
                current_grid,
                show_solution=show_solution,
                palette_idx=palette_idx,
                palettes=palettes,
                duck_cells=duck_cells,
                path_cells=current_path,
                pattern_cells=pattern_cells,
                show_pattern=show_pattern,
                now=time.monotonic(),
                pulse_entry_exit=pulse_entry_exit,
                pattern_fade=pattern_fade,
                dead_end_shimmer=dead_end_shimmer,
            )
            _print_maze(lines)
            if stats_ticker:
                _print_stats_line(current_grid, current_path)
            _print_menu()

            choice = _get_choice()

            if auto_palette:
                palette_idx = (palette_idx + 1) % len(palettes)

            if choice == "1":
                rng_counter += 1
                cfg = self.cfg
                if cfg is None:
                    print("No configuration available for regeneration.")
                    continue
                new_seed: Optional[int]
                if cfg.seed is not None:
                    new_seed = cfg.seed + rng_counter
                else:
                    new_seed = random.randint(0, 2**31 - 1)

                try:
                    new_gen = MazeGenerator(
                        width=cfg.width,
                        height=cfg.height,
                        seed=new_seed,
                        perfect=cfg.perfect,
                        algorithm=cfg.algorithm,
                    )
                    new_grid = new_gen.generate(
                        entry=cfg.entry,
                        exit_=cfg.exit_,
                    )
                    new_path = _solve_path_cells(new_grid)
                    current_gen = new_gen
                    current_grid = new_grid
                    current_path = new_path
                    if ducks_enabled:
                        duck_cells = _pick_duck_cells(
                            current_grid,
                            ducks_count,
                            duck_rng,
                            new_gen.pattern_cells,
                            set(current_path),
                        )
                    if cfg.animate:
                        pattern_cells = new_gen.pattern_cells
                        _animate_solution(
                            current_grid,
                            current_path,
                            palette_idx,
                            palettes,
                            duck_cells,
                            pattern_cells,
                            show_pattern,
                            ANIMATE_SPEEDS[path_speed_idx],
                            pulse_entry_exit=pulse_entry_exit,
                            pattern_fade=pattern_fade,
                            dead_end_shimmer=dead_end_shimmer,
                        )
                        show_solution = True
                    else:
                        show_solution = False
                except (ValueError, RuntimeError, NoPathError) as exc:
                    print(f"Re-generation error: {exc}", file=sys.stderr)

            elif choice == "2":
                show_solution = not show_solution

            elif choice == "3":
                palette_idx = (palette_idx + 1) % len(palettes)

            elif choice == "4":
                show_pattern = not show_pattern

            elif choice == "5":
                ducks_enabled = not ducks_enabled
                if not ducks_enabled:
                    duck_cells = set()

            elif choice == "6":
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Please enter 1-19.")

    def _slideshow_loop(self, grid: MazeGrid) -> None:
        cfg = self.cfg
        if cfg is None:
            return
        palette_idx = 0
        fx_speed_idx = 1
        palettes = _get_palettes(cfg)
        duck_rng = _get_duck_rng(cfg)
        ducks_enabled, ducks_count, ducks_animate = _get_duck_config(
            cfg
        )
        if self.generator is not None:
            pattern_cells = self.generator.pattern_cells
        else:
            pattern_cells = None

        current_grid = grid
        while True:
            duck_cells: set[tuple[int, int]] = set()
            if ducks_enabled:
                if ducks_animate or not duck_cells:
                    duck_cells = _pick_duck_cells(
                        current_grid,
                        ducks_count,
                        duck_rng,
                        pattern_cells,
                        None,
                    )

            lines = _build_display_lines(
                current_grid,
                show_solution=False,
                palette_idx=palette_idx,
                palettes=palettes,
                duck_cells=duck_cells,
                path_cells=None,
                pattern_cells=pattern_cells,
                show_pattern=True,
                now=time.monotonic(),
                pulse_entry_exit=cfg.pulse_entry_exit,
                pattern_fade=cfg.pattern_fade,
                dead_end_shimmer=cfg.dead_end_shimmer,
            )
            _print_maze(lines)

            if cfg.auto_palette:
                palette_idx = (palette_idx + 1) % len(palettes)

            time.sleep(ANIMATE_SPEEDS[fx_speed_idx] * 60.0)
            fx_speed_idx = (fx_speed_idx + 1) % len(ANIMATE_SPEEDS)

            try:
                new_gen = MazeGenerator(
                    width=cfg.width,
                    height=cfg.height,
                    seed=random.randint(0, 2**31 - 1),
                    perfect=cfg.perfect,
                    algorithm=cfg.algorithm,
                )
                current_grid = new_gen.generate(
                    entry=cfg.entry,
                    exit_=cfg.exit_,
                )
                pattern_cells = new_gen.pattern_cells
            except (ValueError, RuntimeError, NoPathError):
                continue


def _solve_path_cells(grid: MazeGrid) -> list[tuple[int, int]]:
    solver = MazeSolver(grid)
    solver.solve()
    return solver.get_path_cells()


def _build_display_lines(
    grid: MazeGrid,
    show_solution: bool,
    palette_idx: int,
    palettes: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
    duck_cells: set[tuple[int, int]] | None,
    path_cells: list[tuple[int, int]] | None,
    pattern_cells: set[tuple[int, int]] | None,
    show_pattern: bool,
    now: float,
    pulse_entry_exit: bool,
    pattern_fade: bool,
    dead_end_shimmer: bool,
) -> list[str]:
    w, h = grid.width, grid.height
    wall_col, pass_col = palettes[palette_idx % len(palettes)]

    solution_cells: set[tuple[int, int]] = set(path_cells or [])

    wall_bg = _ansi_bg(*wall_col)
    pass_bg = _ansi_bg(*pass_col)
    sol_bg = _ansi_bg(*SOLUTION_COLOUR)
    e42_bg = _ansi_bg(*PATTERN_42_COLOUR)
    duck_bg = _ansi_bg(*DUCK_COLOUR)
    pulse_factor = _pulse_factor(now)
    entry_bg = _ansi_bg(*_scale_colour(ENTRY_COLOUR, pulse_factor))
    exit_bg = _ansi_bg(*_scale_colour(EXIT_COLOUR, pulse_factor))
    if not pulse_entry_exit:
        entry_bg = _ansi_bg(*ENTRY_COLOUR)
        exit_bg = _ansi_bg(*EXIT_COLOUR)

    if pattern_fade:
        e42_bg = _ansi_bg(*_scale_colour(PATTERN_42_COLOUR, pulse_factor))

    shimmer_phase = int(now / 0.5)

    wall_h = wall_bg + " " * CELL_W + ANSI_RESET
    lines: list[str] = []

    for gy in range(2 * h + 1):
        line = ""
        for gx in range(2 * w + 1):
            is_corner = (gy % 2 == 0) and (gx % 2 == 0)
            is_h_wall = (gy % 2 == 0) and (gx % 2 == 1)
            is_v_wall = (gy % 2 == 1) and (gx % 2 == 0)

            cx = gx // 2
            cy = gy // 2

            if is_corner:
                line += wall_bg + " " + ANSI_RESET
            elif is_h_wall:
                cell_y = cy
                cell_y_above = cy - 1
                wall_present = True
                if cell_y < h:
                    wall_present = grid.has_wall(cx, cell_y, NORTH)
                elif cell_y_above >= 0:
                    wall_present = grid.has_wall(cx, cell_y_above, SOUTH)
                if wall_present:
                    line += wall_h
                else:
                    line += pass_bg + " " * CELL_W + ANSI_RESET
            elif is_v_wall:
                cell_x = cx
                cell_x_left = cx - 1
                wall_present = True
                if cell_x < w:
                    wall_present = grid.has_wall(cell_x, cy, WEST)
                elif cell_x_left >= 0:
                    wall_present = grid.has_wall(cell_x_left, cy, EAST)
                if wall_present:
                    line += wall_bg + " " + ANSI_RESET
                else:
                    line += pass_bg + " " + ANSI_RESET
            else:
                coord = (cx, cy)
                if coord == grid.entry:
                    bg = entry_bg
                elif coord == grid.exit_:
                    bg = exit_bg
                elif show_solution and coord in solution_cells:
                    bg = sol_bg
                elif (
                    show_pattern
                    and pattern_cells is not None
                    and coord in pattern_cells
                ):
                    bg = e42_bg
                elif duck_cells is not None and coord in duck_cells:
                    bg = duck_bg
                elif dead_end_shimmer and _is_dead_end(grid, cx, cy):
                    if ((cx + cy + shimmer_phase) % 6) == 0:
                        bg = _ansi_bg(255, 255, 255)
                    else:
                        bg = pass_bg
                else:
                    bg = pass_bg
                line += bg + " " * CELL_W + ANSI_RESET

        lines.append(line)

    return lines


def _animate_solution(
    grid: MazeGrid,
    path_cells: list[tuple[int, int]],
    palette_idx: int,
    palettes: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
    duck_cells: set[tuple[int, int]] | None,
    pattern_cells: set[tuple[int, int]] | None,
    show_pattern: bool,
    delay: float,
    pulse_entry_exit: bool,
    pattern_fade: bool,
    dead_end_shimmer: bool,
) -> None:
    if not path_cells:
        return

    for step in range(1, len(path_cells) + 1):
        lines = _build_display_lines(
            grid,
            show_solution=True,
            palette_idx=palette_idx,
            palettes=palettes,
            duck_cells=duck_cells,
            path_cells=path_cells[:step],
            pattern_cells=pattern_cells,
            show_pattern=show_pattern,
            now=time.monotonic(),
            pulse_entry_exit=pulse_entry_exit,
            pattern_fade=pattern_fade,
            dead_end_shimmer=dead_end_shimmer,
        )
        _print_maze(lines)
        time.sleep(delay)


def _get_palettes(
    cfg: MazeConfig | None,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    if cfg is not None and cfg.palette == "colorblind":
        return COLORBLIND_PALETTES
    return COLOUR_PALETTES


def _get_duck_rng(cfg: MazeConfig | None) -> random.Random:
    if cfg is not None and cfg.seed is not None:
        return random.Random(cfg.seed)
    return random.Random()


def _get_duck_config(cfg: MazeConfig | None) -> tuple[bool, int, bool]:
    if cfg is None:
        return False, 0, False
    enabled = bool(cfg.ducks or cfg.ducks_count > 0)
    count = cfg.ducks_count if cfg.ducks_count > 0 else (5 if enabled else 0)
    return enabled, count, cfg.ducks_animate


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


def _pulse_factor(now: float) -> float:
    return 0.5 + 0.5 * math.sin(now * math.tau)


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


def _is_dead_end(grid: MazeGrid, x: int, y: int) -> bool:
    walls = 0
    if grid.has_wall(x, y, NORTH):
        walls += 1
    if grid.has_wall(x, y, EAST):
        walls += 1
    if grid.has_wall(x, y, SOUTH):
        walls += 1
    if grid.has_wall(x, y, WEST):
        walls += 1
    return walls >= 3


def _print_maze(lines: list[str]) -> None:
    os.system("clear" if os.name != "nt" else "cls")
    for line in lines:
        print(line)


def _print_menu() -> None:
    print()
    print("==== A-Maze-ing ====")
    print("1. Re-generate a new maze")
    print("2. Show/Hide path from entry to exit")
    print("3. Rotate maze wall colours")
    print("4. Toggle 42 pattern highlight")
    print("5. Toggle ducks")
    print("6. Quit")
    print("Choice (1-6): ", end="", flush=True)


def _get_choice() -> str:
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return "6"


def _print_stats_line(
    grid: MazeGrid,
    path_cells: list[tuple[int, int]],
) -> None:
    dead_ends = 0
    for y in range(grid.height):
        for x in range(grid.width):
            if _is_dead_end(grid, x, y):
                dead_ends += 1
    steps = max(0, len(path_cells) - 1)
    print(f"[stats] dead-ends {dead_ends} | path {steps} steps")
