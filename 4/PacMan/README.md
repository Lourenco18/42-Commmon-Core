*This project has been created as part of the 42 curriculum.*

# Pac-Man

## Description

A complete, playable recreation of the classic Pac-Man arcade game, built in Python using **pygame**.  
The player navigates a maze eating dots, avoids (or eats) ghosts, and tries to clear all levels before time runs out.

Key features:
- Procedurally generated mazes (via the external A-Maze-ing package)
- Full ghost AI (chase and flee behaviors)
- Persistent highscore system (top 10, player names, JSON storage)
- All menus: main menu, pause, highscores, instructions, game over, victory
- Cheat mode for peer evaluation
- Configurable via a JSON file

---

## Instructions

### Requirements

- Python 3.10 or later
- `pip` package manager
- The `mazegenerator` wheel included in this repository (`Pac-Man/mazegenerator-00001-py3-none-any.whl`)

### Installation

```bash
make install
```

This installs `pygame` and the maze generator package.  
Alternatively:
```bash
pip install -r requirements.txt
pip install Pac-Man/mazegenerator-00001-py3-none-any.whl
```

### Running the game

```bash
make run
# or
python3 pac-man.py config.json
```

Pass any config file as the single argument:
```bash
python3 pac-man.py my_config.json
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
| P / ESC (in game) | Pause |
| ENTER | Confirm / select menu item |

### Cheat Mode (for peer evaluation)

| Key | Effect |
|-----|--------|
| I | Toggle invincibility (ghosts can't kill you) |
| F | Freeze / unfreeze all ghosts |
| L | Add an extra life |
| B | Toggle speed boost |
| X | Skip current level (immediately win) |

---

## Configuration

The game reads a JSON configuration file passed as a command-line argument.

### File format

```json
{
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
| `lives` | int | `3` | Starting lives (clamped 1–10) |
| `pacgum` | int | `42` | Max pacgums placed per level (clamped 1–500) |
| `points_per_pacgum` | int | `10` | Score per pacgum eaten |
| `points_per_super_pacgum` | int | `50` | Score per power pellet eaten |
| `points_per_ghost` | int | `200` | Score per edible ghost eaten |
| `seed` | int | `42` | Fixed seed for level 1 maze |
| `level_max_time` | int | `90` | Seconds per level (clamped 10–600) |
| `level` | array | 10 × 21×21 | Array of `{"width": N, "height": N}` objects |

### Faulty config handling

- **Missing keys**: safe defaults are used automatically.
- **Invalid/out-of-range values**: clamped to the nearest valid value.
- **Unknown keys**: silently ignored.
- **Non-JSON file or missing file**: clean error message printed, program exits without traceback.
- **Dimensions**: must be odd numbers for proper corridor generation; even values are bumped up by 1 automatically.

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

- **Load**: read on game start; on any file error (missing, corrupt, wrong type) the list is silently reset to empty.
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
- **Bitmask encoding**: each cell is an integer where `bit0=North open, bit1=East open, bit2=South open, bit3=West open`. A wall exists when the corresponding bit is **not** set.
- **Level 1**: uses the fixed `seed` from config for reproducibility.
- **Subsequent levels**: use `random.randint(0, 2^32-1)` for variety.
- **Failure handling**: if `MazeGenerator` raises any exception, it is caught, logged, and propagated cleanly without a traceback reaching the user.

The wrapper in `src/maze.py` adapts the raw grid, ensuring the row/column ordering is consistent with the renderer and entity system.

---

## Implementation

### Architecture overview

```
pac-man.py          ← entry point, argument parsing
src/
  config.py         ← JSON config loader, validation, safe defaults
  maze.py           ← A-Maze-ing wrapper, Maze class, wall queries
  entities.py       ← Player, Ghost (state machine), Pacgum, SuperPacgum
  level.py          ← Level init, update, collision, win/loss, cheats
  highscore.py      ← HighscoreSystem (load/save/add/query)
  renderer.py       ← Pygame drawing: maze, entities, all UI screens
  game.py           ← Top-level state machine, event loop, level transitions
```

### Key design decisions

- **No pygame in the domain layer** (`config`, `maze`, `entities`, `level`, `highscore`): these modules are pure Python and independently testable.
- **State machine** (`GameState` enum in `game.py`): all screen transitions are explicit enum values — no ad-hoc flags.
- **Ghost AI**: greedy distance-based with a small random jitter, producing natural-looking but imperfect chase behavior. Ghosts switch to flee mode when edible.
- **Type hints everywhere**: all functions and class attributes carry type annotations; compatible with `mypy`.
- **Docstrings**: Google-style docstrings on all public functions and classes (PEP 257).
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
  ┌──▼──┐   ┌───▼──┐   ┌────▼────┐
  │Maze │   │Player│   │ Ghosts  │
  │     │   │Ghost │   │Pacgum   │
  │grid │   │lives │   │SuperPgm │
  └──▲──┘   └──────┘   └─────────┘
     │
  MazeGenerator
  (external pkg)
```

**Module responsibilities:**

| Module | Responsibility |
|--------|---------------|
| `config.py` | Parse and validate JSON config; safe defaults |
| `maze.py` | Wrap mazegenerator; expose `is_wall()`, `neighbours()` |
| `entities.py` | Player movement, Ghost state machine, item dataclasses |
| `level.py` | Level lifecycle: init, update, collision detection, cheats |
| `highscore.py` | Load/save JSON highscores; validate names and scores |
| `renderer.py` | All pygame drawing (maze, entities, menus, HUD) |
| `game.py` | Event loop, state transitions, window management |

---

## Project Management

See [`project_management/PROJECT_MANAGEMENT.md`](project_management/PROJECT_MANAGEMENT.md) for:
- Full timeline and Gantt breakdown
- Technical choices and rationale
- Risk analysis and mitigations
- Acceptance test plan

---

## Resources

### Classic references
- [Pac-Man on Wikipedia](https://en.wikipedia.org/wiki/Pac-Man) — history and original mechanics
- [The Pac-Man Dossier by Jamey Pittman](https://www.gamedeveloper.com/design/the-pac-man-dossier) — in-depth ghost AI analysis
- [pygame documentation](https://www.pygame.org/docs/) — rendering, events, clock
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)

### AI usage
AI assistance (Claude) was used for the following tasks in this project:
- **Initial architecture planning**: discussing module boundaries and the separation of domain vs. presentation layers.
- **Boilerplate generation**: class skeletons, docstring templates, and type hint patterns.
- **Debugging assistance**: explaining maze bitmask encoding and helping reason through ghost-player collision edge cases.
- **README drafting**: first draft of section structure, then reviewed and rewritten.

All AI-generated content was reviewed, understood, tested, and adapted before inclusion. No code was copied without full comprehension of its behaviour.
