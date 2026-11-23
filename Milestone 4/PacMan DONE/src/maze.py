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
    """Expose dimensions, walls, and traversable neighboring cells."""
    def __init__(self, width: int, height: int, grid: list[list[int]]) -> None:
        """Initialize a Maze instance.

        Args:
            width: Maze width in cells.
            height: Maze height in cells.
            grid: Maze cells encoded as wall bitmasks."""
        self.width: int = width
        self.height: int = height
        self.grid: list[list[int]] = grid

    def is_wall(self, row: int, col: int, direction: int) -> bool:
        """Check whether a cell has a wall in the requested direction.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.
            direction: Direction or wall bit to inspect.

        Returns:
            Result of the operation."""
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return True
        return bool(self.grid[row][col] & direction)

    def passable(self, row: int, col: int) -> bool:
        """Check whether a cell is inside the maze bounds.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.

        Returns:
            Result of the operation."""
        return 0 <= row < self.height and 0 <= col < self.width

    def neighbours(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return adjacent cells reachable without crossing walls.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.

        Returns:
            Result of the operation."""
        result: list[tuple[int, int]] = []
        directions = [(NORTH, -1, 0), (EAST, 0, 1),
                      (SOUTH, 1, 0), (WEST, 0, -1)]
        for direction, dr, dc in directions:
            nr, nc = row + dr, col + dc
            if self.passable(nr, nc) and not self.is_wall(row, col, direction):
                result.append((nr, nc))
        return result


def generate_maze(width: int, height: int, seed: Optional[int] = None) -> Maze:
    """Generate a maze with the assigned package and adapt its grid.

    Args:
        width: Maze width in cells.
        height: Maze height in cells.
        seed: Optional seed for reproducible generation.

    Returns:
        Result of the operation."""
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1
    actual_seed: int = (
        seed
        if seed is not None
        else random.SystemRandom().randint(0, 2**32 - 1)
    )
    try:
        mg = MazeGenerator(
            size=(
                width,
                height),
            perfect=False,
            seed=actual_seed)
        mg.generate(seed=actual_seed)
        raw_grid: list[list[int]] = mg.maze
    except Exception as exc:
        logger.error("Maze generator failed: %s", exc)
        raise RuntimeError(f"Maze generation failed: {exc}") from exc
    grid: list[list[int]] = []
    for r in range(height):
        row_data: list[int] = []
        for c in range(width):
            try:
                row_data.append(int(raw_grid[r][c]))
            except (IndexError, TypeError):
                row_data.append(0)
        grid.append(row_data)

    logger.info(
        "Generated %dx%d maze with seed %d",
        width,
        height,
        actual_seed)
    return Maze(width=width, height=height, grid=grid)
