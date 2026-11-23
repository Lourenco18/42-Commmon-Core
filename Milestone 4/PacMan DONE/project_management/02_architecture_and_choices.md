# Project Analysis and Technical Choices

## 1. Problem Decomposition

Recreating Pac-Man under the 42 project constraints requires balancing classic arcade responsiveness with strict software engineering rules:
- **Zero-crash resilience** against malformed command-line arguments, broken JSON files, missing highscore files, or maze generator exceptions.
- **Strict decoupling** from an externally authored maze generator (`A-Maze-ing`) that will be reinstalled during peer review.
- **Object-oriented reuse** across movable actors and collectible items.
- **Cross-platform packaging** suitable for distribution on a public gaming platform (Itch.io).

---

## 2. Layered Software Architecture

We divided the codebase into four distinct layers so that game rules remain testable and independent of the rendering backend:

1. **Entry & Configuration Layer (`pac-man.py`, `src/config.py`):**
   - Validates CLI invocation (`sys.argv` length == 2) and wraps execution in a global exception handler so Python tracebacks never reach standard output.
   - Strips full-line `#` and `//` comments before parsing JSON, clamps out-of-range numbers, enforces odd maze dimensions, and guarantees at least 10 levels.
2. **Domain Layer (`src/maze.py`, `src/entities.py`, `src/level.py`, `src/highscore.py`):**
   - Contains **zero `pygame` imports**.
   - Encapsulates grid queries, actor movement, ghost state machines, collision detection, scoring, cheat toggles, and Top-10 highscore persistence.
3. **Presentation Layer (`src/renderer.py`):**
   - Consumes domain state to render the maze, animated sprites (with geometric primitive fallbacks), HUD, and menus.
   - Resolves asset paths dynamically via `sys._MEIPASS` when frozen by PyInstaller.
4. **Controller Layer (`src/game.py`):**
   - Manages the 60 FPS clock, keyboard event routing, window resizing per level, and an explicit `GameState` finite state machine (`MAIN_MENU`, `PLAYING`, `PAUSED`, `HIGHSCORES`, `INSTRUCTIONS`, `NAME_ENTRY`, `GAME_OVER`, `VICTORY`).

---

## 3. Object-Oriented Design Choices

To avoid duplicated boundary and wall-collision logic, we established two inheritance hierarchies in `src/entities.py`:

- **`Entity` -> `Player` & `Ghost`:**
  - `Entity` owns grid coordinates (`row`, `col`, `prev_row`, `prev_col`), movement interpolation (`visual_pos()`), and wall validation (`can_move()` and `available_moves()`).
  - Both `Player` and `Ghost` inherit the exact same rule preventing movement through maze walls or outside grid bounds.
- **`Collectible` -> `Pacgum` & `SuperPacgum`:**
  - `Collectible` encapsulates shared cell coordinates and `eaten` state, allowing `Level` to manage regular dots and corner power pellets uniformly.

---

## 4. Key Technical Decisions

### Graphical Library (`pygame` with MLX-Equivalent Primitives)
- **Choice:** Python 3.10+ with `pygame`.
- **Rationale:** Every rendering operation used in `src/renderer.py` (filling surfaces, drawing lines, rectangles, circles, blitting sprites, rendering text, and polling keyboard events) maps directly to capabilities available in MiniLibX (MLX), while offering reliable cross-platform packaging on Linux and macOS.

### External Maze Generator Adapter (`src/maze.py`)
- **Choice:** Adapter pattern wrapping `mazegenerator.MazeGenerator(..., perfect=False, seed=...)`.
- **Rationale:** Setting `perfect=False` creates loops essential for Pac-Man gameplay (preventing unavoidable dead-end traps). Level 1 uses the fixed configuration seed for deterministic evaluation, while subsequent levels draw seeds from `random.SystemRandom()`.
- **Reachability Guarantee:** Because `perfect=False` mazes and central `"42"` wall patterns can isolate individual cells, `Level` runs a Breadth-First Search (BFS) both to locate a guaranteed open spawn cell near the center (`_find_spawn_cell`) and to place pacgums exclusively in reachable corridors (`_reachable_cells`).

### Ghost AI & State Machine
- **Choice:** Explicit `GhostState` enum (`CHASING`, `EDIBLE`, `RESPAWNING`) with four classic targeting heuristics:
  - **Red (Blinky):** Targets the player's current cell directly.
  - **Pink (Pinky):** Targets 4 cells ahead of the player's movement vector.
  - **Cyan (Inky):** Uses a 2-cell pivot ahead of the player reflected through Blinky's position.
  - **Orange (Clyde):** Chases directly when farther than 8 tiles away, retreating toward its home corner when closer.
- **Edible & Respawn Behavior:** When a super-pacgum is eaten, ghosts slow down and flee using a distance-maximizing heuristic with slight randomness. When eaten, ghosts switch to an eyes-only `RESPAWNING` state, follow a BFS shortest path back to their home corner, wander briefly, and revive.

### Highscore Persistence
- **Choice:** Local JSON file (`data/highscores.json`) managed by `HighscoreSystem`.
- **Rationale:** Human-readable, requires zero external database dependencies, and wraps all file operations in `try/except` blocks to recover cleanly from missing or corrupted files.