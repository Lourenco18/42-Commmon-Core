"""Maze solver — BFS shortest-path implementation.

This module is part of the *mazegen* reusable library and will be completed
by dasantos as part of the project's visual stream.

The :class:`MazeSolver` class provides a BFS-based shortest-path solver that
operates directly on a :class:`~mazegen.maze.MazeGrid` object.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from mazegen.maze import DELTAS, NORTH, EAST, SOUTH, WEST, MazeGrid


class NoPathError(Exception):
    """Raised when no path exists between entry and exit."""


class MazeSolver:
    """BFS shortest-path solver for a :class:`~mazegen.maze.MazeGrid`.

    Args:
        grid: The maze to solve.

    Example:
        >>> from mazegen.generator import MazeGenerator
        >>> from mazegen.solver import MazeSolver
        >>> grid = MazeGenerator(10, 10, seed=1).generate()
        >>> solver = MazeSolver(grid)
        >>> directions = solver.solve()
        >>> len(directions) > 0
        True
    """

    # Direction letter for each direction constant
    _DIR_LETTER: dict[int, str] = {
        NORTH: "N",
        EAST:  "E",
        SOUTH: "S",
        WEST:  "W",
    }

    def __init__(self, grid: MazeGrid) -> None:
        self._grid: MazeGrid = grid
        self._path_cells: Optional[list[tuple[int, int]]] = None
        self._directions: Optional[list[str]] = None

    def solve(
        self,
        entry: Optional[tuple[int, int]] = None,
        exit_: Optional[tuple[int, int]] = None,
    ) -> list[str]:
        """Find the shortest path and return it as a list of direction letters.

        Args:
            entry: Override the grid's entry coordinate.
            exit_: Override the grid's exit coordinate.

        Returns:
            Ordered list of direction strings (``'N'``, ``'E'``, ``'S'``,
            ``'W'``) that lead from *entry* to *exit_*.

        Raises:
            NoPathError: If no path connects entry and exit.
        """
        # TODO: This stub is intentionally minimal.
        # dasantos will expand this with the full BFS implementation.
        start = entry if entry is not None else self._grid.entry
        goal = exit_ if exit_ is not None else self._grid.exit_

        if start == goal:
            self._path_cells = [start]
            self._directions = []
            return []

        prev: dict[tuple[int, int], Optional[tuple[int, int]]] = {start: None}
        prev_dir: dict[tuple[int, int], Optional[int]] = {start: None}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == goal:
                break
            for d in [NORTH, EAST, SOUTH, WEST]:
                if not self._grid.has_wall(cx, cy, d):
                    dx, dy = DELTAS[d]
                    nx, ny = cx + dx, cy + dy
                    if not (
                        0 <= nx < self._grid.width
                        and 0 <= ny < self._grid.height
                    ):
                        continue
                    nxt = (nx, ny)
                    if nxt not in prev:
                        prev[nxt] = (cx, cy)
                        prev_dir[nxt] = d
                        queue.append(nxt)

        if goal not in prev:
            raise NoPathError(
                f"No path found from {start} to {goal}."
            )

        # Reconstruct
        cells: list[tuple[int, int]] = []
        dirs: list[str] = []
        node: Optional[tuple[int, int]] = goal
        while node is not None:
            cells.append(node)
            dir_value = prev_dir.get(node)
            if dir_value is not None:
                dirs.append(self._DIR_LETTER[dir_value])
            node = prev.get(node)

        cells.reverse()
        dirs.reverse()

        self._path_cells = cells
        self._directions = dirs
        return list(dirs)

    def get_path_cells(self) -> list[tuple[int, int]]:
        """Return the solution path as an ordered list of (x, y) coordinates.

        Returns:
            List of (x, y) tuples from entry to exit.

        Raises:
            RuntimeError: If :meth:`solve` has not been called yet.
        """
        if self._path_cells is None:
            raise RuntimeError("Call solve() before get_path_cells().")
        return list(self._path_cells)
