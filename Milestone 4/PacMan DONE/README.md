*This project has been created as part of the 42 curriculum by dasantos, fjose-hi.*

# Pac-Man
https://lourenco18.itch.io/pacman-42
## Description

A playable Pac-Man game written in Python with **pygame**. The player navigates a generated maze, collects pacgums, avoids or eats ghosts, and progresses through multiple timed levels.

Key features:
- At least 10 levels, with maze dimensions and game settings configurable in a JSON file.
- Level 1 uses the configured fixed seed; later levels use newly generated random seeds.
- Four ghosts move through corridors, chase the player, flee while edible, and return to their home corners after being eaten.
- Pacgums and corner power pellets award configurable points. Eating a power pellet makes ghosts edible for a limited time.
- Remaining lives and score carry forward between levels. Losing all lives or running out of level time ends the game.
- Main menu, instructions, pause screen, in-game HUD, highscore table, name entry, game-over screen, and victory screen.
- Persistent JSON highscore table containing the top 10 entries.
- Cheat mode for peer evaluation, with invincibility, level skip, ghost freeze, life and time adjustments, and a speed boost.

---

## Instructions

### Requirements

- Python 3.10 or later
- `pip` package manager
- The assigned A-Maze-ing wheel in `Pac-Man/mazegenerator-2.1.0-py3-none-any.whl`

Use a Python version with a compatible Pygame wheel when possible. If `pip` tries to compile Pygame from source, use a supported Python version or install the SDL development dependencies for your operating system.

### Installation

```bash
make install
```
The Makefile creates a local `.venv`, then installs the Python requirements and the assigned maze-generator wheel into that environment. On macOS with Homebrew Python 3.15, Pygame 2.6.1 may be built from source and require SDL headers; install Python 3.13 and select it explicitly if needed:

```bash
brew install python@3.13
rm -rf .venv
make install PYTHON3=python3.13
```

### Running the game

```bash
make run
```

The command above uses `config.json`. To select another JSON configuration, run the main script with exactly one config path:

```bash
.venv/bin/python pac-man.py my_config.json
```

### Other Makefile targets

| Target | Description |
|--------|-------------|
| `make install` | Install dependencies |
| `make run` | Launch the game with `config.json` |
| `make debug` | Launch with Python debugger (pdb) |
| `make clean` | Remove `__pycache__`, `.mypy_cache`, `.pyc` |
| `make lint` | Run `flake8` + `mypy` (standard) |
| `make lint-strict` | Run `flake8` + `mypy --strict` |

---

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move Pac-Man |
| P / ESC (during play) | Pause the game |
| ENTER / P (while paused) | Resume the game |
| ESC (while paused) | Abandon the current game and return to the main menu |
| ENTER | Confirm a menu selection or submit the highscore name |

### Cheat Mode (for peer evaluation)

During gameplay, press Shift+C to enable cheat mode, then use the keys below. Press Shift+C again to disable it; continuous cheats are reset.

| Key | Effect |
|-----|--------|
| Shift+C | Toggle cheat mode |
| I | Toggle invincibility (ghosts can't kill you) |
| F | Freeze / unfreeze all ghosts |
| L / R | Add / remove a life |
| + / - | Add / remove 10 seconds |
| T | Freeze / unfreeze the timer |
| B | Toggle speed boost |
| X | Skip current level (immediately win) |

---

## Configuration

The game reads a JSON configuration file passed as a command-line argument.

### File format

The file is JSON with support for full-line comments beginning with `#` or `//`.

```json
{
    # These are examples; omitted values use the defaults below.
    "highscore_filename": "data/highscores.json",
    "lives": 3,
    "pacgum": 42,
    "points_per_pacgum": 10,
    "points_per_super_pacgum": 50,
    "points_per_ghost": 200,
    "seed": 42,
    "level_max_time": 90,
    "level": [
        {"width": 21, "height": 21},
        {"width": 23, "height": 23}
    ]
}
```

### Fields and defaults

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `highscore_filename` | string | `"data/highscores.json"` | Path to highscore storage file |
| `lives` | int | `3` | Starting lives (clamped to 1–99) |
| `pacgum` | int | `42` | Maximum regular pacgums per level (clamped to 1–2500) |
| `points_per_pacgum` | int | `10` | Points per regular pacgum (clamped to 1–10000) |
| `points_per_super_pacgum` | int | `50` | Points per power pellet (clamped to 1–10000) |
| `points_per_ghost` | int | `200` | Points per edible ghost (clamped to 1–10000) |
| `seed` | int | `42` | Fixed seed for level 1 (clamped to 0–4294967295) |
| `level_max_time` | int | `224` | Base seconds for level 1 (clamped to 10–999) |
| `level` | array | 10 × 17×17 | Array of `{"width": N, "height": N}` objects; at least 10 levels are used |

### Faulty config handling

- **Missing keys**: safe defaults are used automatically.
- **Invalid/out-of-range values**: clamped to the nearest valid value.
- **Unknown keys**: silently ignored.
- **Non-JSON file or missing file**: clean error message printed, program exits without traceback.
- **Dimensions**: widths are clamped to 11–61 and heights to 11–31, then rounded up to odd values. Missing or invalid dimensions use 17×17. If fewer than 10 levels are supplied, 17×17 levels are appended.
- **Comments**: only full lines beginning with `#` or `//` are removed before JSON parsing; inline comments are not supported.

---

## Highscore System

Highscores are stored as a JSON array in the file specified by `highscore_filename` (default: `data/highscores.json`).

### Format

```json
[
  {"name": "Alice",  "score": 4200},
  {"name": "Bob",    "score": 3100}
]
```

### Behaviour

- **Load**: read on game start; a missing file starts with an empty list. Corrupt, unreadable, or incorrectly structured data is reset to an empty list and logged as a warning.
- **Save**: written after the player enters their name at game end.
- **Top 10**: only the top 10 scores are kept.
- **Name rules**: 1–10 characters, alphanumeric and spaces only. Invalid names default to `"Player"`.
- **Score rules**: non-negative integers only.

### Why JSON?

JSON is human-readable (scores can be inspected or reset by hand), requires no external database, and Python's `json` module handles it without extra dependencies. The entire I/O is wrapped in try/except so the game never crashes due to a missing or corrupt highscore file.

---

## Maze Generation

Mazes are generated using the **A-Maze-ing** package (`mazegenerator`) provided by another group. The project adapts to its interface:

```python
from mazegenerator import MazeGenerator

mg = MazeGenerator(size=(width, height), perfect=False, seed=seed)
mg.generate(seed=seed)
grid = mg.maze  # list[list[int]], each value is a bitmask
```

- **`perfect=False`**: produces corridors with loops, suitable for Pac-Man (multiple paths, no dead-ends-only maze).
- **Bitmask encoding**: each cell is an integer where `bit0=North, bit1=East, bit2=South, bit3=West`. A **set** bit means a wall is present in that direction (verified empirically against the assigned package); a clear bit means the corridor is open.
- **Level 1**: uses the fixed `seed` from config for reproducibility.
- **Subsequent levels**: use a seed from `random.SystemRandom().randint(0, 2^32 - 1)` so each maze is newly randomized.
- **Failure handling**: if `MazeGenerator` raises any exception, it is caught, logged, and propagated cleanly without a traceback reaching the user.

The wrapper in `src/maze.py` adapts the raw grid, ensuring the row/column ordering is consistent with the renderer and entity system.

**Robustness note**: the assigned generator occasionally produces a handful of cells that end up walled off from the rest of the maze (normal for a `perfect=False` maze with random extra wall removal). To guarantee every level is always fully completable, pacgums are only placed in cells reachable (via BFS over the maze corridors) from the player's starting position.

---

## Implementation

### Architecture overview

```
pac-man.py          ← entry point, argument parsing
src/
  config.py         ← JSON config loader, validation, safe defaults
  maze.py           ← A-Maze-ing wrapper, Maze class, wall queries
  entities.py       ← Entity (Player, Ghost) & Collectible (Pacgum, SuperPacgum)
  level.py          ← Level init, update, collision, win/loss, cheats
  highscore.py      ← HighscoreSystem (load/save/add/query)
  renderer.py       ← Pygame drawing: maze, entities, all UI screens
  game.py           ← Top-level state machine, event loop, level transitions
```

### Key design decisions

- **Object-oriented hierarchy**: `Player` and `Ghost` inherit shared grid coordinates, movement interpolation, and wall-collision checks (`can_move()`) from `Entity`, while `Pacgum` and `SuperPacgum` inherit common item state from `Collectible`.
- **No pygame in the domain layer** (`config`, `maze`, `entities`, `level`, `highscore`): these modules are pure Python and independently testable.
- **State machine** (`GameState` enum in `game.py`): all screen transitions are explicit enum values — no ad-hoc flags.
- **Ghost AI**: classic individual chase targeting without reversing direction at intersections — **Red (Blinky)** pursues the player directly, **Pink (Pinky)** ambushes 4 tiles ahead of the player's direction, **Cyan (Inky)** uses a doubled vector from Blinky through a pivot 2 tiles ahead of the player, and **Orange (Clyde)** chases when more than 8 tiles away or retreats to its home corner when closer. When edible, ghosts flee away from the player with slight random jitter; when eaten, eyes return to their home corner via BFS pathfinding before reviving.
- **Type hints everywhere**: all functions and class attributes carry type annotations; compatible with `mypy`.
- **Docstrings**: Google-style docstrings document every project function and class, including private helpers (PEP 257).
- **Exception handling**: try/except guards all I/O (config, highscores) and the maze generator call.

---

## General Software Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         pac-man.py (entry)                         │
│               parse args → load_config → Game.run()                │
└────────────────────────────┬───────────────────────────────────────┘
                             │
              ┌──────────────▼─────────────┐
              │         Game               │  ← state machine, event loop
              │  state: GameState enum     │
              │  owns: Config, Level,       │
              │        Highscores, Renderer │
              └──────┬────────┬────────────┘
                     │        │
          ┌──────────▼──┐  ┌──▼──────────────┐
          │   Level     │  │   Renderer       │
          │  (domain)   │  │  (presentation)  │
          │             │  │  pygame only     │
          │ owns: Maze  │  └─────────────────-┘
          │       Player│
          │       Ghosts│
          │       Items │
          └──────┬──────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
  ┌──▼──┐   ┌───▼────┐  ┌────▼──────┐
  │Maze │   │ Entity │  │Collectible│
  │     │   │ ├Player│  │ ├Pacgum   │
  │grid │   │ └Ghost │  │ └SuperPgm │
  └──▲──┘   └────────┘  └───────────┘
     │
  MazeGenerator
  (external pkg)
```

**Module responsibilities:**

| Module | Responsibility |
|--------|---------------|
| `config.py` | Parse and validate JSON config; safe defaults |
| `maze.py` | Wrap mazegenerator; expose `is_wall()`, `neighbours()` |
| `entities.py` | Base `Entity` (`Player`, `Ghost` state machine) and `Collectible` (`Pacgum`, `SuperPacgum`) |
| `level.py` | Level lifecycle: init, update, collision detection, cheats |
| `highscore.py` | Load/save JSON highscores; validate names and scores |
| `renderer.py` | All pygame drawing (maze, entities, menus, HUD) |
| `game.py` | Event loop, state transitions, window management |

---

## Project Packaging

The root `pacman.spec` builds a one-file executable and bundles the game sprites. `make package` also places `config.json` and `README.md` beside the executable and creates an OS-specific ZIP in the project root:

- macOS build: `pacman-macos.zip`
- Linux build: `pacman-linux.zip`

The executable is `dist/pacman`. After extracting the release ZIP, run the packaged binary from that folder with a configuration file argument:

```bash
./pacman config.json
```

PyInstaller builds for the operating system and architecture on which it runs; create the Linux ZIP on a compatible Linux machine (for example, Linux x86_64 for x86_64 evaluation PCs). A macOS build cannot be used as the Linux package. Build artefacts in `build/` and `dist/` are intentionally untracked — see `.gitignore`.

Upload the platform ZIP to the project's itch.io downloadable page.

## Project Management

See [`project_management/00_project_management_overview.md`](project_management/00_project_management_overview.md) for:
- Full timeline and Gantt breakdown
- Technical choices and rationale
- Risk analysis and mitigations
- Acceptance test plan

---

## Resources

### References
- [The Pac-Man Dossier by Jamey Pittman](https://www.gamedeveloper.com/design/the-pac-man-dossier) — in-depth ghost AI analysis
- [pygame documentation](https://www.pygame.org/docs/) — rendering, events, clock

### AI usage
AI assistance was used for architecture discussions, code and docstring drafting, README drafting and review, and troubleshooting the build setup. The project authors are responsible for reviewing, understanding, and testing all AI-assisted changes before submission.
