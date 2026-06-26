# Pac-Man — Code & Technologies Documentation

A complete technical reference explaining every module, every class, and the technologies used in this Python Pac-Man implementation.

---

## 1. Technologies Used

### Python 3.10+
The entire project is written in Python 3.10 or later. Features used:
- **Structural pattern matching** — not directly, but `match/case` compatibility is ensured.
- **Type hints** with `dict[str, int]`, `list[tuple[int, int]]`, etc. (PEP 585 generics, available from 3.9+).
- **`from __future__ import annotations`** not needed since Python 3.10 already supports new-style hints.
- **`typing.Optional`** — for nullable return types and parameters.
- **`enum.Enum` / `enum.auto()`** — for state machine states.
- **`dataclasses`** — not used directly; plain classes with `__init__` are preferred for full control and docstrings.

### pygame 2.x
Used for all graphical and input operations.

| pygame subsystem | Purpose |
|-----------------|---------|
| `pygame.display` | Window creation and flipping |
| `pygame.draw` | Rendering circles, rects, lines, polygons |
| `pygame.font.SysFont` | Text rendering (monospace font) |
| `pygame.event` | Keyboard and quit event handling |
| `pygame.time.Clock` | FPS capping (60 FPS target) |
| `pygame.Surface` | Off-screen and on-screen buffers |
| `pygame.SRCALPHA` | Alpha-blended overlay for pause screen |

### mazegenerator (A-Maze-ing package, external)
Third-party package provided by another group. Used as-is without modification.

```python
from mazegenerator import MazeGenerator
mg = MazeGenerator(size=(width, height), perfect=False, seed=seed)
mg.generate(seed=seed)
grid = mg.maze  # list[list[int]]
```

- **`size`**: `(width, height)` tuple of the maze dimensions.
- **`perfect=False`**: produces a maze with loops and multiple paths, suitable for Pac-Man.
- **`seed`**: integer seed for reproducibility.
- **`mg.maze`**: 2D list where each integer is a bitmask encoding which directions have open passages (`bit0=N, bit1=E, bit2=S, bit3=W`).

### Standard library modules used

| Module | Usage |
|--------|-------|
| `json` | Config and highscore file serialisation |
| `logging` | Structured logging throughout all modules |
| `os` | File existence checks, `makedirs` for output dirs |
| `re` | Player name validation (alphanumeric + spaces) |
| `math` | Pac-Man arc rendering (`math.cos`, `math.sin`, `math.radians`) |
| `random` | Maze seeds for levels 2+, ghost AI jitter |
| `sys` | `sys.argv`, `sys.exit` |
| `enum` | `GameState`, `GhostState` enumerations |
| `typing` | `Optional` type annotation |

---

## 2. Project Structure

```
pacman/
├── pac-man.py                  ← Entry point
├── config.json                 ← Default configuration
├── requirements.txt            ← pip dependencies
├── Makefile                    ← Automation (install/run/lint/clean)
├── .gitignore
├── README.md                   ← Full project documentation
├── Pac-Man/
│   └── mazegenerator-*.whl     ← External maze generator (do not modify)
├── data/
│   └── highscores.json         ← Auto-created on first game end
├── project_management/
│   └── PROJECT_MANAGEMENT.md  ← Timeline, risks, test plan
└── src/
    ├── __init__.py
    ├── config.py               ← JSON config loader
    ├── maze.py                 ← Maze wrapper + Maze class
    ├── entities.py             ← Player, Ghost, Pacgum, SuperPacgum
    ├── level.py                ← Level lifecycle
    ├── highscore.py            ← Persistent highscore system
    ├── renderer.py             ← All pygame drawing
    └── game.py                 ← State machine + main loop
```

---

## 3. Module-by-Module Reference

---

### `pac-man.py` — Entry Point

**Purpose**: Parse the single command-line argument and launch the game.

```python
def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 pac-man.py <config.json>")
        sys.exit(1)
    config = load_config(sys.argv[1])
    Game(config).run()
```

**Key behaviour**:
- Validates that exactly one argument is passed.
- Delegates all logic to `load_config` and `Game`.
- `logging.basicConfig` sets up `INFO`-level console logging.

---

### `src/config.py` — Configuration Loader

**Purpose**: Load a JSON config file, validate every field, clamp out-of-range values, and return a `Config` object. Never crashes on bad input.

#### `Config` class
A plain data container (no methods beyond `__init__`). All fields are validated before construction.

| Attribute | Type | Description |
|-----------|------|-------------|
| `highscore_filename` | `str` | Path to highscore JSON |
| `lives` | `int` | Starting lives (1–10) |
| `pacgum` | `int` | Max pacgums per level (1–500) |
| `points_per_pacgum` | `int` | Score for pacgum (1–10000) |
| `points_per_super_pacgum` | `int` | Score for power pellet |
| `points_per_ghost` | `int` | Score for eating ghost |
| `seed` | `int` | Level 1 maze seed (0–2³²-1) |
| `level_max_time` | `int` | Seconds per level (10–600) |
| `levels` | `list[dict[str, int]]` | Array of `{width, height}` |

#### `load_config(path) → Config`
1. Opens file — `FileNotFoundError` → `SystemExit` with clean message.
2. Parses JSON — `json.JSONDecodeError` → `SystemExit` with clean message.
3. For each field: calls `_get_int` or `_parse_levels`.
4. Unknown keys in the JSON are silently ignored.

#### `_get_int(data, key) → int`
- Reads value or falls back to `DEFAULTS[key]`.
- Converts to `int`; on failure, uses default and logs a warning.
- Clamps to `[lo, hi]` from `INT_CLAMPS`; logs if clamped.

#### `_parse_levels(raw_levels) → list[dict[str, int]]`
- Validates it is a non-empty list.
- For each entry: reads `width` and `height`, clamps to `[11, 51]`.
- Forces odd dimensions (required by maze generator for proper corridors).
- Pads to at least 10 levels.

---

### `src/maze.py` — Maze Wrapper

**Purpose**: Wrap the external `mazegenerator` package and expose a clean `Maze` API for wall queries and neighbour lookups.

#### Constants
```python
NORTH = 1   # bit 0 — passage going north (up)
EAST  = 2   # bit 1 — passage going east  (right)
SOUTH = 4   # bit 2 — passage going south (down)
WEST  = 8   # bit 3 — passage going west  (left)
```

#### `Maze` class

| Attribute | Type | Description |
|-----------|------|-------------|
| `width` | `int` | Columns in the grid |
| `height` | `int` | Rows in the grid |
| `grid` | `list[list[int]]` | `grid[row][col]` = bitmask |

**`is_wall(row, col, direction) → bool`**  
Returns `True` if the given direction bit is NOT set in `grid[row][col]`, or if `(row, col)` is out of bounds. Used by entities for movement collision.

**`passable(row, col) → bool`**  
Returns `True` if `(row, col)` is within grid bounds.

**`neighbours(row, col) → list[tuple[int, int]]`**  
Returns all adjacent cells reachable without crossing a wall. Used by ghost AI.

#### `generate_maze(width, height, seed) → Maze`
1. Ensures odd dimensions.
2. Calls `MazeGenerator(size=..., perfect=False, seed=seed).generate(seed=seed)`.
3. Reads `mg.maze` — a 2D list indexed `[col][row]` by the external package.
4. **Transposes** to internal `[row][col]` convention.
5. Wraps any exception in a `RuntimeError` with a clean message.

**Why transpose?** The `mazegenerator` package indexes its grid as `[x][y]` (column-major), while the game uses `[row][col]` (row-major). The transpose normalises this difference.

---

### `src/entities.py` — Game Entities

**Purpose**: Define the movable and collectible entities with no pygame dependency.

#### Direction constants
```python
DIR_UP    = (-1,  0)   # row decreases
DIR_DOWN  = ( 1,  0)   # row increases
DIR_LEFT  = ( 0, -1)
DIR_RIGHT = ( 0,  1)
DIR_TO_BIT = { DIR_UP: NORTH, DIR_DOWN: SOUTH, ... }
```

#### `GhostState` enum
```
CHASING    → ghost is hunting the player
EDIBLE     → ghost is vulnerable (blue), fleeing player
RESPAWNING → ghost was eaten; waiting to respawn in its corner
FROZEN     → cheat mode: ghost does not move
```

#### `Player` class

**Movement system**: Frame-based with `move_timer` / `move_interval`.
- Every frame, `move_timer` increments.
- When `move_timer >= move_interval` (8 frames normal, 4 with speed boost), movement is attempted.
- `next_direction` (queued input) is tried first; falls back to `direction` (current). This allows "pre-turning" — a common Pac-Man feel improvement.

| Key attribute | Purpose |
|--------------|---------|
| `direction` | Current movement vector |
| `next_direction` | Input buffer for next turn |
| `invincible` | Cheat: ghosts can't kill player |
| `speed_boost` | Cheat: halves move interval |
| `score` | Accumulated points (carried between levels) |
| `lives` | Decremented on ghost touch; game over at 0 |

#### `Ghost` class

**State machine**:
```
CHASING ──[super-pacgum eaten]──► EDIBLE ──[timer expires]──► CHASING
EDIBLE  ──[player eats ghost]──► RESPAWNING ──[timer expires]──► CHASING
Any     ──[cheat F key]────────► FROZEN ──[cheat F again]──► CHASING
```

**AI movement** (`_move`):
- Gets `maze.neighbours(row, col)` — all reachable adjacent cells.
- **CHASING**: picks neighbour with smallest Euclidean distance to player, plus `random.uniform(0, 1.5)` jitter to avoid deterministic lock-in.
- **EDIBLE**: picks neighbour with largest distance (negated key) — flees player.
- The jitter makes ghosts occasionally make "mistakes", improving gameplay feel.

#### `Pacgum` / `SuperPacgum` classes
Simple data classes with `row`, `col`, and `eaten` flag. No methods — state changes are managed by `Level`.

---

### `src/level.py` — Level Lifecycle

**Purpose**: Own the complete state of a single level: maze, all entities, timing, collision detection, win/loss conditions, and cheat mode.

#### `Level.__init__`
1. Picks the level spec from `config.levels[level_index]`.
2. Calls `generate_maze` with `seed` (fixed for level 0, `None` for others).
3. Places player at `(height//2, width//2)`.
4. Spawns 4 ghosts at the 4 corners.
5. Calls `_place_items()`.

#### `_place_items()`
- Super-pacgums: one in each corner cell.
- Pacgums: `random.sample` up to `config.pacgum` items from all non-corner, non-center cells.

#### `update(dt)`
Called every frame with delta-time in seconds.

1. **Time countdown**: `time_remaining -= dt`. On expiry → `level_lost = True`.
2. **Player update**: `player.update(maze)`.
3. **Ghost updates**: `ghost.update(maze, player.row, player.col)` for each ghost.
4. **Collision checks**: pacgums, super-pacgums, ghost–player.
5. **Win check**: all pacgums eaten → `level_won = True`.

#### Collision detection
All collision checks are grid-cell exact matching: `ghost.row == player.row and ghost.col == player.col`. This is appropriate for a tile-based game.

#### Cheat mode methods
| Method | Effect |
|--------|--------|
| `toggle_invincibility()` | Flip `player.invincible` |
| `skip_level()` | Set `level_won = True` immediately |
| `toggle_ghost_freeze()` | Freeze all non-respawning ghosts (or unfreeze all) |
| `add_extra_life()` | Increment `player.lives` |
| `toggle_speed_boost()` | Flip `player.speed_boost` |

---

### `src/highscore.py` — Persistent Highscore System

**Purpose**: Load, maintain, and save the top 10 highscores with player names.

#### `HighscoreEntry` class
- `name`: sanitized by `_validate_name` — strips, truncates to 10 chars, rejects non-alphanumeric, defaults to `"Player"`.
- `score`: clamped to `max(0, int(score))`.
- `to_dict()`: serializes to `{"name": ..., "score": ...}` for JSON output.

#### `HighscoreSystem` class

**`load()`**:
- If file missing → empty list (not an error).
- Opens and parses JSON; on any exception → empty list + warning log.
- Validates each entry individually; silently skips malformed items.
- Sorts descending by score, keeps top 10.

**`save()`**:
- `os.makedirs` ensures parent directory exists.
- Writes JSON array with `indent=2` for readability.
- Any `OSError` logged and silently swallowed — game continues.

**`add(name, score) → Optional[int]`**:
- Appends new entry, re-sorts, trims to 10.
- Returns the 1-based rank if entry is in the final list, else `None`.

**`is_highscore(score) → bool`**:
- Returns `True` if fewer than 10 entries exist, or if `score` beats the lowest entry.

**`get_top(n) → list[HighscoreEntry]`**:
- Returns up to `n` entries (default 10), sorted best-first.

---

### `src/renderer.py` — Pygame Renderer

**Purpose**: Draw everything to the pygame surface. No game logic, no state changes.

#### Drawing architecture
All `draw_*` methods take the game objects as read-only inputs and produce pixel output. The renderer has no mutable game state of its own (except animation counters `_mouth_open`, `_mouth_dir`).

#### `draw_game(level, tick)`
Calls in order: fill black → animate Pac-Man → draw maze → draw pacgums → draw super-pacgums → draw ghosts → draw player → draw HUD.

#### `_draw_maze(level)`
Iterates every `(row, col)` cell:
1. Fills the cell rect with `CORRIDOR_COLOR` (dark blue-black).
2. For each of the 4 sides, draws a wall line if the corresponding passage bit is NOT set.

Wall thickness is 3px; this approach produces the classic Pac-Man connected-wall look.

#### `_draw_player(level)`
Draws a filled polygon approximating a pie slice (Pac-Man's open mouth):
- `start_angle = facing_angle + mouth_open_radians`
- `end_angle = facing_angle + 360° - mouth_open_radians`
- 30-step polygon approximating the arc, with the center point included.
- `_mouth_open` oscillates between 0.05 and 0.55 radians each frame → animation.

#### `_draw_ghosts(level, tick)`
Each ghost is rendered as:
- Top: filled circle for the head.
- Bottom: filled rectangle for the skirt.
- Eyes: two white circles (red when edible).
- Flashing effect: when `edible_timer < 120` and `(tick // 8) % 2 == 0`, color switches to a pale variant.

#### `_draw_hud(level)`
Fixed 50px bar at the top:
- Score (left), Lives (center-left), Level (center), Timer (right).
- Timer turns red when ≤ 15 seconds.
- Cheat indicators (`INV`, `SPD`) shown when active.

#### Fonts
Three SysFont sizes used:
- `font_large` (36px bold) — titles.
- `font_med` (24px bold) — menu items, scores.
- `font_small` (16px) — HUD labels, instructions.

All use `monospace` family for consistent alignment.

#### `compute_window_size(maze_width, maze_height) → (w, h)` (static method)
Returns `(maze_width * CELL_SIZE, maze_height * CELL_SIZE + HUD_HEIGHT)`.  
Called by `Game._load_level` to resize the window when switching levels.

---

### `src/game.py` — Game State Machine

**Purpose**: Top-level controller. Owns the pygame event loop, manages state transitions, and connects all subsystems.

#### `GameState` enum
```
MAIN_MENU     → main menu screen
PLAYING       → active gameplay
PAUSED        → gameplay frozen, pause overlay shown
HIGHSCORES    → highscore table
INSTRUCTIONS  → controls screen
NAME_ENTRY    → player types their name after game ends
GAME_OVER     → brief display before name entry
VICTORY       → brief display before name entry
```

#### `Game.run()` — Main Loop
```
while True:
    dt = clock.tick(FPS) / 1000
    handle_events()  → key dispatch
    update(dt)       → game logic / timer
    draw()           → render current state
    pygame.display.flip()
```

#### Event handling (`_on_key`)
Dispatched by state:

| State | Keys handled |
|-------|-------------|
| `MAIN_MENU` | ↑↓ to navigate, ENTER to select |
| `PLAYING` | Arrow/WASD to move, P/ESC to pause, I/F/L/B/X for cheats |
| `PAUSED` | ENTER/P resume, ESC back to menu |
| `HIGHSCORES` / `INSTRUCTIONS` | ENTER/ESC return to menu |
| `NAME_ENTRY` | Alphanumeric/space to type, BACKSPACE, ENTER to confirm |
| `GAME_OVER` / `VICTORY` | Timer-only (no key needed) |

#### Level transitions
- **Win**: `level_index++`. If `< len(config.levels)` → `_load_level` with carried lives + score. If all levels done → `VICTORY`.
- **Lose**: capture `final_score`, set `GAME_OVER`, start 2-second `_end_timer`.
- **End timer**: after 2 seconds in `GAME_OVER`/`VICTORY` → `NAME_ENTRY`.
- **Name confirmed**: `highscores.add(name, score)`, `highscores.save()`, back to `MAIN_MENU`.

#### Window resizing
Each level may have a different maze size. `_load_level` calls:
```python
self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
self.renderer.screen = self.screen
```
The renderer reference is updated so it draws to the new surface.

---

## 4. Data Flow Diagram

```
JSON file
    │
    ▼
load_config()  ──────────────────────────────────────────────► Config
                                                                  │
                              ┌───────────────────────────────────┤
                              │                                   │
                              ▼                                   ▼
                      HighscoreSystem                       Game.__init__
                      (loads JSON)                               │
                                                                 │
                         Key input ──────────────────────────► game._on_key
                                                                 │
                                                     ┌───────────┴──────────┐
                                                     │                      │
                                                     ▼                      ▼
                                              Level.update(dt)         Renderer.draw_*
                                                     │                      │
                                          ┌──────────┼──────────┐           │
                                          │          │          │           │
                                          ▼          ▼          ▼           ▼
                                       Player     Ghosts    Pacgums     pygame Surface
                                      .update    .update  (collision)
                                        │          │
                                        └────►  Maze.is_wall / .neighbours
```

---

## 5. Configuration & Defaults Reference

| Key | Default | Range | Notes |
|-----|---------|-------|-------|
| `highscore_filename` | `"data/highscores.json"` | any string | Parent dirs created automatically |
| `lives` | `3` | 1–10 | |
| `pacgum` | `42` | 1–500 | Max dots per level |
| `points_per_pacgum` | `10` | 1–10000 | |
| `points_per_super_pacgum` | `50` | 1–10000 | |
| `points_per_ghost` | `200` | 1–10000 | |
| `seed` | `42` | 0–2³²-1 | First level only |
| `level_max_time` | `90` | 10–600 | Seconds |
| `level[n].width` | `21` | 11–51 (odd) | Even values incremented |
| `level[n].height` | `21` | 11–51 (odd) | Even values incremented |

---

## 6. Coding Standards

- **PEP 8** via `flake8` — max line length 99, no trailing whitespace.
- **Type hints** — all function parameters, return types, and class attributes annotated.
- **Docstrings** — Google style on all public classes and functions (purpose, Args, Returns).
- **`mypy`** — runs with `--disallow-untyped-defs --check-untyped-defs --warn-return-any`.
- **Exception handling** — all I/O operations wrapped in `try/except`; no unhandled tracebacks reach the user.
- **Logging** — `logging.getLogger(__name__)` per module; `INFO` for normal events, `WARNING` for recoverable issues, `ERROR` for failures.
