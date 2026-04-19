import os
import sys
import random
from typing import List, Optional, Tuple
from maze_config import MazeConfig
from mazegen.generator import MazeGenerator
from mazegen.generator import NORTH, EAST, SOUTH, WEST

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mazegen_src"))

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"


def _ansi_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


def _ansi_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


COLOUR_PALETTES: List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = [
    ((220, 220, 220), (30, 30, 30)),
    ((180, 120, 40), (20, 20, 20)),
    ((0, 150, 80), (0, 20, 10)),
    ((60, 120, 200), (10, 10, 40)),
    ((200, 60, 60), (30, 0, 0)),
]

ENTRY_COLOUR = (200, 50, 200)
EXIT_COLOUR = (200, 50, 50)
SOLUTION_COLOUR = (50, 200, 220)
PATTERN_42_COLOUR = (100, 80, 180)


CELL_W = 3
CELL_H = 1


def _cell_is_42(gen: MazeGenerator, x: int, y: int) -> bool:
    return gen._is_42_cell(x, y)


def _build_display_lines(
    gen: MazeGenerator,
    show_solution: bool,
    palette_idx: int,
    show_42_colour: bool = True,
) -> List[str]:
    maze = gen.get_maze()
    w, h = gen.width, gen.height
    wall_col, pass_col = COLOUR_PALETTES[palette_idx % len(COLOUR_PALETTES)]

    solution_cells: set[Tuple[int, int]] = set()
    if show_solution:
        cx, cy = gen.entry
        solution_cells.add((cx, cy))
        for letter in gen.get_solution():
            if letter == "N":
                cy -= 1
            elif letter == "E":
                cx += 1
            elif letter == "S":
                cy += 1
            elif letter == "W":
                cx -= 1
            solution_cells.add((cx, cy))

    wall_bg = _ansi_bg(*wall_col)
    pass_bg = _ansi_bg(*pass_col)
    sol_bg = _ansi_bg(*SOLUTION_COLOUR)
    e42_bg = _ansi_bg(*PATTERN_42_COLOUR)
    entry_bg = _ansi_bg(*ENTRY_COLOUR)
    exit_bg = _ansi_bg(*EXIT_COLOUR)

    wall_h = wall_bg + " " * CELL_W + ANSI_RESET

    lines: List[str] = []

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
                    wall_present = bool(maze[cell_y][cx] & NORTH)
                elif cell_y_above >= 0:
                    wall_present = bool(maze[cell_y_above][cx] & SOUTH)
                if wall_present:
                    line += wall_h
                else:
                    line += pass_bg + " " * CELL_W + ANSI_RESET
            elif is_v_wall:
                cell_x = cx
                cell_x_left = cx - 1
                wall_present = True
                if cell_x < w:
                    wall_present = bool(maze[cy][cell_x] & WEST)
                elif cell_x_left >= 0:
                    wall_present = bool(maze[cy][cell_x_left] & EAST)
                if wall_present:
                    line += wall_bg + " " + ANSI_RESET
                else:
                    line += pass_bg + " " + ANSI_RESET
            else:
                if (cx, cy) == gen.entry:
                    bg = entry_bg
                elif (cx, cy) == gen.exit:
                    bg = exit_bg
                elif (cx, cy) in solution_cells:
                    bg = sol_bg
                elif show_42_colour and _cell_is_42(gen, cx, cy):
                    bg = e42_bg
                else:
                    bg = pass_bg
                line += bg + " " * CELL_W + ANSI_RESET

        lines.append(line)

    return lines


def _print_maze(lines: List[str]) -> None:
    os.system("clear" if os.name != "nt" else "cls")
    for line in lines:
        print(line)


def display_maze(gen: MazeGenerator, cfg: MazeConfig) -> None:
    show_solution = False
    palette_idx = 0
    current_gen = gen
    rng_counter = 0

    while True:
        lines = _build_display_lines(current_gen, show_solution, palette_idx)
        _print_maze(lines)
        _print_menu()

        choice = _get_choice()

        if choice == "1":
            rng_counter += 1
            new_seed: Optional[int] = (
                (cfg.seed + rng_counter) if cfg.seed is not None
                else random.randint(0, 2**31)
            )
            try:
                new_gen = MazeGenerator(
                    width=cfg.width,
                    height=cfg.height,
                    seed=new_seed,
                    entry=cfg.entry,
                    exit_=cfg.exit_,
                )
                new_gen.generate(perfect=cfg.perfect)
                current_gen = new_gen
                show_solution = False
            except (ValueError, RuntimeError) as exc:
                print(f"Re-generation error: {exc}", file=sys.stderr)

        elif choice == "2":
            show_solution = not show_solution

        elif choice == "3":
            palette_idx = (palette_idx + 1) % len(COLOUR_PALETTES)

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1–4.")


def _print_menu() -> None:
    print()
    print("==== A-Maze-ing ====")
    print("1. Re-generate a new maze")
    print("2. Show/Hide path from entry to exit")
    print("3. Rotate maze wall colours")
    print("4. Quit")
    print("Choice (1-4): ", end="", flush=True)


def _get_choice() -> str:
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        return "4"
