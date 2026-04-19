*This project has been created as part of the 42 curriculum by dasantos and dsilva-c.*

# A-Maze-ing

## Description

**A-Maze-ing** is a Python maze generator that creates randomised mazes, writes them to a file in a standardised hexadecimal format, and provides an interactive terminal visualiser. The maze always embeds a visible **"42"** pattern made of fully-walled cells, and can generate either *perfect* mazes (exactly one path between entry and exit) or mazes with loops.

The generation logic is packaged as a reusable `mazegen` library (installable via `pip`) for use in future projects.

---

## Instructions

### Requirements

- Python 3.10 or later
- No third-party packages required for the core program

### Installation

```bash
# Clone or copy the project, then:
make install       # installs flake8, mypy, build
```

### Running

```bash
python3 a_maze_ing.py config.txt
# or
make run
```

### Debug mode

```bash
make debug
```

### Linting

```bash
make lint       
make lint-strict
```

### Clean

```bash
make clean
```

---

## Configuration File

The configuration file uses one `KEY=VALUE` pair per line. Lines starting with `#` are comments.

| Key | Mandatory | Description | Example |
|-----|-----------|-------------|---------|
| `WIDTH` | ✅ | Number of columns (≥ 2) | `WIDTH=20` |
| `HEIGHT` | ✅ | Number of rows (≥ 2) | `HEIGHT=15` |
| `ENTRY` | ✅ | Entry cell coordinates (x,y) | `ENTRY=0,0` |
| `EXIT` | ✅ | Exit cell coordinates (x,y) | `EXIT=19,14` |
| `OUTPUT_FILE` | ✅ | Path of the output file | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | ✅ | Generate a perfect maze | `PERFECT=True` |
| `SEED` | ➖ | RNG seed for reproducibility | `SEED=42` |
| `ALGORITHM` | ➖ | Generation algorithm (`dfs`) | `ALGORITHM=dfs` |

A default `config.txt` is included in the repository.

---

## Maze Generation Algorithm

**Recursive Backtracker (Iterative DFS)**

The algorithm maintains a stack and visits cells depth-first, removing walls between the current cell and an unvisited random neighbour. When no unvisited neighbours remain, it backtracks. This always produces a *spanning tree* of the grid — i.e. a perfect maze with exactly one path between any two cells.

### Why this algorithm?

- Simple to implement correctly with full control over the resulting structure.
- Produces mazes with long, winding corridors that feel very maze-like.
- Deterministic when seeded, supporting reproducible output.
- The iterative variant avoids Python recursion limits on large grids.
- Well-documented connection to spanning trees makes it easy to reason about correctness.

---

## Reusable `mazegen` Package

The `mazegen` package (located at the repository root as `mazegen-1.0.0-py3-none-any.whl` and `mazegen-1.0.0.tar.gz`) contains the `MazeGenerator` class.

### Install

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

### Basic example

```python
from mazegen.generator import MazeGenerator

gen = MazeGenerator(width=20, height=15, seed=42)
gen.generate(perfect=True)

maze = gen.get_maze()          # list[list[int]] — wall bitmasks
solution = gen.get_solution()  # list[str] — ['S','S','E',...]
print(gen.get_solution_string())  # 'SSE...'
print(gen.entry)               # (0, 0)
print(gen.exit)                # (19, 14)
```

### Custom parameters

```python
gen = MazeGenerator(
    width=30,
    height=20,
    seed=1234,           # reproducible seed
    entry=(0, 0),
    exit_=(29, 19),
)
gen.generate(perfect=False)   # allows loops
```

### Accessing the maze structure

`get_maze()` returns a 2-D list where each integer is a 4-bit wall bitmask:

| Bit | Direction | Set = wall closed |
|-----|-----------|-------------------|
| 0 (LSB) | North | 1 |
| 1 | East | 2 |
| 2 | South | 4 |
| 3 | West | 8 |

Example: `0xF` (15) = all walls closed (isolated cell).

### Building the package from source

```bash
cd mazegen_src
pip install build
python3 -m build --outdir ../
```

---

## Visual Display

The program renders the maze in the terminal using 24-bit ANSI colour codes:

| Colour | Meaning |
|--------|---------|
| Light grey | Wall |
| Dark / black | Passage |
| Magenta | Entry cell |
| Red | Exit cell |
| Cyan | Solution path |
| Purple | "42" pattern cells |

### Interactive menu

After generation, a menu lets you:
1. **Re-generate** – produce a new maze (different random seed)
2. **Show/Hide path** – toggle the shortest solution overlay
3. **Rotate colours** – cycle through 5 wall colour palettes
4. **Quit**

---

## Team and Project Management

### Team members

| Member | Role |
|--------|------|
| student_login | Solo project — all components |

### Planning

The project was planned in four phases:

1. Core maze generation (DFS algorithm, wall encoding, coherence) — 2 days
2. Output file format and validation — 0.5 days  
3. "42" pattern embedding with connectivity repair — 1 day
4. Terminal display, packaging, README — 1 day

The main unplanned work was the connectivity-repair algorithm after embedding the "42" pattern, which required an iterative BFS-based approach to reconnect orphaned cells.

### What worked well

- The DFS approach produced correct and clean mazes from the start.
- The hexadecimal output format was straightforward to implement.
- Separating the reusable `MazeGenerator` from display logic made testing easy.

### What could be improved

- The "42" connectivity repair is O(n³) in the worst case; a union-find approach would be faster.
- The terminal renderer could support wider cells and Unicode box-drawing characters.
- Only one algorithm (DFS) is implemented; Prim's and Kruskal's could be added as bonuses.

### Tools used

- **Python 3.12** — primary language
- **flake8** — style checking
- **mypy** — static type checking
- **build** — Python package builder

---

## Resources

- [Maze generation algorithms — Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Think Labyrinth: Maze Algorithms](https://www.astrolog.org/labyrnth/algrithm.htm)
- [Spanning trees and perfect mazes](https://en.wikipedia.org/wiki/Maze_generation_algorithm#Graph_theory_basis)
- [Python typing module docs](https://docs.python.org/3/library/typing.html)
- [PEP 257 — Docstring conventions](https://peps.python.org/pep-0257/)

### AI usage

AI (Claude) was used for:
- Brainstorming the connectivity-repair strategy after the "42" pattern insertion broke maze connectivity.
- Suggesting the iterative DFS pattern to avoid Python recursion limits.
- Reviewing the ANSI colour escape sequences for the terminal renderer.

All AI suggestions were reviewed, tested, and adapted by the author. No AI-generated code was submitted without full understanding and validation.
