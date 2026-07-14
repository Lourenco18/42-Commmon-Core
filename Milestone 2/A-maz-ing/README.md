*This project has been created as part of the 42 curriculum by dsilva-c, dasantos.*

# A-Maze-ing

## Description

A-Maze-ing is a Python maze generator that builds a valid maze from a
configuration file, writes the required hex-encoded output, and provides a
visual frontend in the terminal or with MiniLibX. The program supports seeded
generation, perfect and non-perfect modes, and an embedded "42" pattern when
the maze size allows it.

## Instructions

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

### Run

```bash
python3 a_maze_ing.py config.txt
```

### MLX (Ubuntu)

```bash
pip install ./mlx-2.2-py3-ubuntu-any.whl
```

### MLX (Fedora)

```bash
pip install ./mlx-2.2-py3-fedora-any.whl
```

### Visual controls

Required controls (subject):

ASCII menu:
- 1: Re-generate a new maze
- 2: Show/Hide path from entry to exit
- 3: Rotate maze wall colours
- 4: Toggle 42 pattern highlight
- 7: Toggle ducks

MLX keys (window focused):
- R: Re-generate a new maze
- P: Show/Hide path from entry to exit
- C: Cycle wall colours
- H: Toggle 42 pattern highlight
- D: Toggle ducks
- Q or Esc: Quit

Bonus controls (extra commands):

- `D`/`U`: ducks on/off and duck animation (MLX)
- `A`/`O`/`F`/`M`: palette, pulse, fade, shimmer (MLX)
- `T`/`L`: stats ticker and seed slideshow (MLX)
- Menu options 7–14: duck/effect toggles (ASCII)
- Menu options 15–18: faster/slower path and effects (ASCII)

Notes:
- `S` replays the path reveal so speed changes are immediately visible.
- `[`/`]` and `-`/`=` give slower/faster adjustments without cycling.
- Ducks never spawn on the solution path or inside the 42 pattern.

---

## Maze Generation Algorithm

A-Maze-ing uses the **DFS Recursive Backtracker** (also known as the
Randomised Depth-First Search) algorithm to generate the maze.

Additional algorithms are available via `ALGORITHM`:
- `prims` uses randomized Prim's to grow a maze from a frontier.
- `kruskals` uses randomized Kruskal's with union-find to build a spanning tree.

### How it works

The algorithm treats the grid as a graph where every cell is a node. It
starts from a random (or seeded) cell and explores the graph with a
depth-first search, carving passages as it goes.

```
Initialise:   mark every cell as unvisited, all walls closed
Choose start: push start cell onto the stack, mark as visited

Loop:
  current ← top of stack
  neighbours ← unvisited adjacent cells of current (in random order)

  if neighbours is not empty:
      choose a random unvisited neighbour
      remove the wall between current and that neighbour
      push the neighbour onto the stack
      mark the neighbour as visited
  else:
      pop current from the stack   ← backtrack

Stop when the stack is empty (all reachable cells have been visited)
```

After the spanning tree is complete, the **"42" pixel pattern** is
pre-burned into the grid: a set of cells whose combined silhouette spells
"42" in a 5×7 pixel font are locked to all-walls-closed (`0xF`) and
skipped entirely by the DFS. Isolated regions created by the pattern are
reconnected by a greedy bridge pass.

In **non-perfect** mode, 15 % of remaining internal walls are opened at
random, creating loops, then a final repair pass eliminates any fully-open
3×3 block (which would be trivially solved and score-penalised).

### Why DFS Recursive Backtracker?

| Property | Reason it matters here |
|---|---|
| **Simplicity** | Easy to implement iteratively (no recursion-limit risk). |
| **Perfect maze guarantee** | Every cell is reachable from every other — exactly one path between any pair. Trivially extendable to non-perfect by reopening random walls. |
| **Deterministic with seed** | Set `SEED=N` in `config.txt` and reproduce any maze exactly. |
| **Good visual aesthetic** | DFS produces long, winding corridors — visually interesting in both ASCII and MLX renders. |
| **Pattern-friendly** | The iterative stack makes it straightforward to pre-mark the "42" cells as off-limits and reconnect any orphaned regions. |

---

## Reusable Library — `mazegen`

The core generation logic is packaged as a standalone, PEP 561-typed Python
library (`mazegen/`). It can be imported and used independently of the
project's entry point.

### Installation

```bash
# From the project root — installs in editable mode (no wheel needed):
pip install -e .

# Or install the built wheel:
pip install mazegen-1.0.0-py3-none-any.whl
```

### Quick-start example

```python
from mazegen import MazeGenerator, MazeSolver

# Generate a 20×15 perfect maze, reproducible with seed 42
gen = MazeGenerator(width=20, height=15, seed=42)
grid = gen.generate(entry=(0, 0), exit_=(19, 14))

# Access the hex grid
for row in grid.cells:
    print("".join(cell.hex_char() for cell in row))

# BFS shortest path (list of 'N'/'E'/'S'/'W' direction strings)
solver = MazeSolver(grid)
directions = solver.solve()
print("Path:", "".join(directions))

# Cell coordinates along the path
path_cells = solver.get_path_cells()
```

### Custom parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `width` | `int` | — | Number of columns (≥ 2). |
| `height` | `int` | — | Number of rows (≥ 2). |
| `seed` | `int \| None` | `None` | RNG seed for reproducibility. `None` = non-deterministic. |
| `perfect` | `bool` | `True` | Perfect maze (spanning tree). `False` adds random extra passages. |
| `algorithm` | `str` | `"dfs"` | Generation algorithm. Allowed: `"dfs"`, `"prims"`, `"kruskals"`. |
| `entry` | `tuple[int, int]` | `(0, 0)` | Entry cell (must be on the border). |
| `exit_` | `tuple[int, int]` | `(w-1, h-1)` | Exit cell (must be on the border, ≠ entry). |

### Wall encoding

Each cell is encoded as a single hex digit (`0`–`f`):

| Bit | Direction | Value 1 (wall closed) | Value 0 (wall open) |
|---|---|---|---|
| 0 (LSB) | North | Wall present | Passage |
| 1 | East | Wall present | Passage |
| 2 | South | Wall present | Passage |
| 3 (MSB) | West | Wall present | Passage |

Example: `0b0110` = `0x6` means East and South walls are closed; North and West walls are open.

---

## Configuration File

The program reads a plain-text `KEY=VALUE` file (default: `config.txt`).
Lines starting with `#` and blank lines are ignored.

### Mandatory keys

| Key | Type | Constraint | Example |
|---|---|---|---|
| `WIDTH` | `int` | ≥ 2 | `WIDTH=20` |
| `HEIGHT` | `int` | ≥ 2 | `HEIGHT=15` |
| `ENTRY` | `x,y` | On border of grid, ≠ EXIT | `ENTRY=0,0` |
| `EXIT` | `x,y` | On border of grid, ≠ ENTRY | `EXIT=19,14` |
| `OUTPUT_FILE` | `str` | Any writable path | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | `True`/`False` | Exact spelling | `PERFECT=True` |

### Optional keys

| Key | Type | Default | Allowed values | Example |
|---|---|---|---|---|
| `SEED` | `int` or `None` | `None` | Any integer or `None` | `SEED=42` |
| `ALGORITHM` | `str` | `dfs` | `dfs`, `prims`, `kruskals` | `ALGORITHM=dfs` |
| `DISPLAY_MODE` | `str` | `ascii` | `ascii`, `mlx`, `both` | `DISPLAY_MODE=both` |
| `ANIMATE` | `True`/`False` | `False` | Exact spelling | `ANIMATE=False` |
| `PALETTE` | `str` | `default` | `default`, `colorblind` | `PALETTE=colorblind` |
| `EXPORT_SVG` | `str` | `None` | SVG output path | `EXPORT_SVG=maze.svg` |
| `EXPORT_CELL_SIZE` | `int` | `24` | ≥ 1 | `EXPORT_CELL_SIZE=24` |
| `EXPORT_WALL` | `int` | `2` | ≥ 1 | `EXPORT_WALL=2` |
| `DUCKS` | `True`/`False` | `False` | Exact spelling | `DUCKS=True` |
| `DUCKS_COUNT` | `int` | `0` | ≥ 1 | `DUCKS_COUNT=5` |
| `DUCKS_ANIMATE` | `True`/`False` | `False` | Exact spelling | `DUCKS_ANIMATE=True` |
| `AUTO_PALETTE` | `True`/`False` | `False` | Exact spelling | `AUTO_PALETTE=True` |
| `PULSE_ENTRY_EXIT` | `True`/`False` | `False` | Exact spelling | `PULSE_ENTRY_EXIT=True` |
| `PATTERN_FADE` | `True`/`False` | `False` | Exact spelling | `PATTERN_FADE=True` |
| `DEAD_END_SHIMMER` | `True`/`False` | `False` | Exact spelling | `DEAD_END_SHIMMER=True` |
| `SEED_SLIDESHOW` | `True`/`False` | `False` | Exact spelling | `SEED_SLIDESHOW=True` |
| `STATS_TICKER` | `True`/`False` | `False` | Exact spelling | `STATS_TICKER=True` |

When `ANIMATE=True`, the solution path animates on startup and after
regenerating a maze.

Display modes (`ascii`, `mlx`, `both`) and animation are optional bonus
features that do not change the required output file format.

### Example `config.txt`

```ini
WIDTH=20
HEIGHT=15
ENTRY=0,0
EXIT=19,14
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
ALGORITHM=dfs
DISPLAY_MODE=ascii
ANIMATE=False
PALETTE=default
# Optional SVG export (bonus)
# EXPORT_SVG=maze.svg
# EXPORT_CELL_SIZE=24
# EXPORT_WALL=2
# Optional rubber ducks overlay (bonus)
# DUCKS=True
# DUCKS_COUNT=5
# DUCKS_ANIMATE=False
# Optional animations (bonus)
# AUTO_PALETTE=True
# PULSE_ENTRY_EXIT=True
# PATTERN_FADE=True
# DEAD_END_SHIMMER=True
# SEED_SLIDESHOW=True
# STATS_TICKER=True
```

---

---

## Team and project management

Work was split into two streams: engine (maze generation, output format,
packaging) and visual (ASCII/MLX frontends and user interaction). Both members
reviewed each other's code and integrated changes through feature branches and
pull requests.

### Roles

- dsilva-c: engine, config parsing, generator, output writer, packaging.
- dasantos: solver, ASCII/MLX frontends, user interactions, README lead.

### Planning and evolution

- Initial plan: agree on the MazeGrid API early, then work in parallel.
- Mid-project: tightened validation (entry/exit on borders) and output format.
- Final phase: integrated frontends, stabilized UI controls, and refreshed docs.

### What worked well

- Clear stream ownership and frequent code reviews.
- Early contract on MazeGrid and output format reduced merge conflicts.

### What could be improved

- Earlier end-to-end testing on real MLX environments.
- More automated tests for renderers.

### Tools used

- Git/GitHub with feature branches and PR reviews.
- pytest, flake8, mypy for validation.
- MiniLibX for the graphical frontend.

## Resources

- 42 MiniLibX documentation (mlx.h and manpages bundled in the wheel).
- Graph theory and BFS references for shortest-path solving.
- DFS Recursive Backtracker references for maze generation.

### AI usage

AI assistance was used for:

- Adapting the terminal/MLX frontend interaction logic to the project layout.
- Cross-checking output format requirements and config key constraints.
- Drafting README sections and then refining them manually.

All generated changes were reviewed, tested, and adjusted by the team.
