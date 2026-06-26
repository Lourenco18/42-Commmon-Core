"""Maze management for Pac-Man — wraps the A-Maze-ing mazegenerator package."""
import logging
import random
from typing import Optional

try:
    from mazegenerator import MazeGenerator
except ImportError as exc:
    raise ImportError("mazegenerator package not found.") from exc

logger = logging.getLogger(__name__)

NORTH: int = 1
EAST: int = 2
SOUTH: int = 4
WEST: int = 8


class Maze:
    """Represents a generated maze grid."""
    def __init__(self, width: int, height: int, grid: list[list[int]]) -> None:
        """Initialize Maze."""
        self.width: int = width
        self.height: int = height
        self.grid: list[list[int]] = grid

    def is_wall(self, row: int, col: int, direction: int) -> bool:
        """Return True if there is a wall in the given direction."""
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return True
        return not bool(self.grid[row][col] & direction)

    def passable(self, row: int, col: int) -> bool:
        """Return True if cell is within bounds."""
        return 0 <= row < self.height and 0 <= col < self.width

    def neighbours(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return reachable adjacent cells."""
        result: list[tuple[int, int]] = []
        for direction, dr, dc in [(NORTH, -1, 0), (EAST, 0, 1), (SOUTH, 1, 0), (WEST, 0, -1)]:
            nr, nc = row + dr, col + dc
            if self.passable(nr, nc) and not self.is_wall(row, col, direction):
                result.append((nr, nc))
        return result


def generate_maze(width: int, height: int, seed: Optional[int] = None) -> Maze:
    """Generate a Pac-Man compatible maze."""
    if width % 2 == 0: width += 1
    if height % 2 == 0: height += 1
    actual_seed: int = seed if seed is not None else random.randint(0, 2**32 - 1)
    try:
        mg = MazeGenerator(size=(width, height), perfect=False, seed=actual_seed)
        mg.generate(seed=actual_seed)
        raw_grid: list[list[int]] = mg.maze
    except Exception as exc:
        logger.error("Maze generator failed: %s", exc)
        raise RuntimeError(f"Maze generation failed: {exc}") from exc

    rows = height
    cols = width
    grid: list[list[int]] = []
    for r in range(rows):
        row_data: list[int] = []
        for c in range(cols):
            try:
                val = raw_grid[c][r] if len(raw_grid) == cols else raw_grid[r][c]
                row_data.append(int(val))
            except (IndexError, TypeError):
                row_data.append(0)
        grid.append(row_data)

    logger.info("Generated %dx%d maze with seed %d", width, height, actual_seed)
    return Maze(width=cols, height=rows, grid=grid)
