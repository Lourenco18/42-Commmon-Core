from __future__ import annotations

import random
import sys
from collections import deque
from typing import Optional

from mazegen.maze import (
    DELTAS,
    EAST,
    NORTH,
    SOUTH,
    WEST,
    MazeGrid,
)

_DIGIT_4: list[list[int]] = [
    [1, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 0, 1],
    [0, 0, 1],
]

_DIGIT_2: list[list[int]] = [
    [1, 1, 1],
    [0, 0, 1],
    [0, 1, 1],
    [1, 0, 0],
    [1, 1, 1],
]

_DIGIT_GAP: int = 1

_PATTERN_PADDING: int = 1

_PATTERN: list[list[int]] = [
    row4 + [0] * _DIGIT_GAP + row2
    for row4, row2 in zip(_DIGIT_4, _DIGIT_2)
]

PATTERN_ROWS: int = len(_PATTERN)
PATTERN_COLS: int = len(_PATTERN[0])
MIN_WIDTH_FOR_42: int = PATTERN_COLS + 2 * _PATTERN_PADDING + 2
MIN_HEIGHT_FOR_42: int = PATTERN_ROWS + 2 * _PATTERN_PADDING + 2


class MazeGenerator:
    def __init__(
        self,
        width: int,
        height: int,
        seed: Optional[int] = None,
        perfect: bool = True,
        algorithm: str = "dfs",
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError(
                f"Maze dimensions must be at least 2×2, got {width}×{height}."
            )
        self.width: int = width
        self.height: int = height
        self.seed: Optional[int] = seed
        self.perfect: bool = perfect
        self.algorithm: str = algorithm.lower()

        self._rng: random.Random = random.Random(seed)
        self._grid: Optional[MazeGrid] = None
        self._solution: Optional[list[tuple[int, int]]] = None
        self._42_cells: set[tuple[int, int]] = set()

    def generate(
        self,
        entry: tuple[int, int] = (0, 0),
        exit_: Optional[tuple[int, int]] = None,
    ) -> MazeGrid:
        if exit_ is None:
            exit_ = (self.width - 1, self.height - 1)

        grid = MazeGrid(self.width, self.height, entry, exit_)

        # Burn the 42 pattern
        self._42_cells = self._place_42_pattern(grid)

        # Carve passages with chosen algorithm
        if self.algorithm == "dfs":
            self._carve_dfs(grid, self._42_cells)
        elif self.algorithm == "prims":
            self._carve_prims(grid, self._42_cells)
        elif self.algorithm == "kruskals":
            self._carve_kruskals(grid, self._42_cells)
        else:
            raise ValueError(
                f"Unsupported algorithm '{self.algorithm}'. "
                "Use 'dfs', 'prims', or 'kruskals'."
            )

        # add random extra passages
        if not self.perfect:
            self._add_extra_passages(grid, self._42_cells)

        # Fix any 3×3 open areas
        self._fix_3x3_open_areas(grid, self._42_cells)

        # Enforce perfect maze (tree) if requested
        if self.perfect:
            self._ensure_perfect_tree(grid, self._42_cells)

        # Open borders at entry and exit
        self._open_border(grid, entry)
        self._open_border(grid, exit_)

        # Validate
        if not grid.is_valid():
            raise RuntimeError(
                "Maze generation produced inconsistent wall data. "
                "Please report this as a bug."
            )

        self._grid = grid
        # Pre-compute solution
        self._solution = self._bfs_path(grid)

        return grid

    def get_grid(self) -> MazeGrid:
        if self._grid is None:
            raise RuntimeError("Call generate() before get_grid().")
        return self._grid

    def get_solution(self) -> list[tuple[int, int]]:
        if self._solution is None:
            raise RuntimeError("Call generate() before get_solution().")
        return list(self._solution)

    @property
    def pattern_cells(self) -> set[tuple[int, int]]:
        return set(self._42_cells)

    def _place_42_pattern(self, grid: MazeGrid) -> set[tuple[int, int]]:
        if (
            grid.width < MIN_WIDTH_FOR_42
            or grid.height < MIN_HEIGHT_FOR_42
        ):
            print(
                f"[42 pattern] Maze {grid.width}×{grid.height} is too small "
                f"to embed the '42' pattern (minimum {MIN_WIDTH_FOR_42}×"
                f"{MIN_HEIGHT_FOR_42}). Pattern omitted.",
                file=sys.stderr,
            )
            return set()

        origin_x = (grid.width - PATTERN_COLS) // 2
        origin_y = (grid.height - PATTERN_ROWS) // 2

        pattern_cells: set[tuple[int, int]] = set()
        for pr, row in enumerate(_PATTERN):
            for pc, bit in enumerate(row):
                if bit:
                    gx = origin_x + pc
                    gy = origin_y + pr
                    grid.cells[gy][gx].mask = 0xF
                    pattern_cells.add((gx, gy))

        return pattern_cells

    def _carve_dfs(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        visited: set[tuple[int, int]] = set(pattern_cells)

        start = self._random_non_pattern(grid, pattern_cells)
        self._dfs_from(grid, start, visited, pattern_cells)

        self._connect_isolated(grid, visited, pattern_cells)

    def _carve_prims(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        visited: set[tuple[int, int]] = set(pattern_cells)
        start = self._random_non_pattern(grid, pattern_cells)
        visited.add(start)

        frontier: list[tuple[int, int, int]] = []

        def add_frontier(cx: int, cy: int) -> None:
            for d in [NORTH, EAST, SOUTH, WEST]:
                dx, dy = DELTAS[d]
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                if (nx, ny) in visited or (nx, ny) in pattern_cells:
                    continue
                frontier.append((cx, cy, d))

        add_frontier(*start)

        while frontier:
            idx = self._rng.randrange(len(frontier))
            x, y, d = frontier.pop(idx)
            dx, dy = DELTAS[d]
            nx, ny = x + dx, y + dy
            if (nx, ny) in visited:
                continue
            grid.remove_wall(x, y, d)
            visited.add((nx, ny))
            add_frontier(nx, ny)

        self._connect_isolated(grid, visited, pattern_cells)

    def _carve_kruskals(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        nodes = [
            (x, y)
            for y in range(grid.height)
            for x in range(grid.width)
            if (x, y) not in pattern_cells
        ]
        if not nodes:
            return

        parent: dict[tuple[int, int], tuple[int, int]] = {
            node: node for node in nodes
        }
        rank: dict[tuple[int, int], int] = {node: 0 for node in nodes}

        def find(node: tuple[int, int]) -> tuple[int, int]:
            root = node
            while parent[root] != root:
                root = parent[root]
            while parent[node] != node:
                nxt = parent[node]
                parent[node] = root
                node = nxt
            return root

        def union(a: tuple[int, int], b: tuple[int, int]) -> bool:
            ra = find(a)
            rb = find(b)
            if ra == rb:
                return False
            if rank[ra] < rank[rb]:
                parent[ra] = rb
            elif rank[ra] > rank[rb]:
                parent[rb] = ra
            else:
                parent[rb] = ra
                rank[ra] += 1
            return True

        edges: list[tuple[int, int, int]] = []
        for y in range(grid.height):
            for x in range(grid.width):
                if (x, y) in pattern_cells:
                    continue
                for d in (EAST, SOUTH):
                    dx, dy = DELTAS[d]
                    nx, ny = x + dx, y + dy
                    if (
                        0 <= nx < grid.width
                        and 0 <= ny < grid.height
                        and (nx, ny) not in pattern_cells
                    ):
                        edges.append((x, y, d))

        self._rng.shuffle(edges)

        for x, y, d in edges:
            dx, dy = DELTAS[d]
            nx, ny = x + dx, y + dy
            if union((x, y), (nx, ny)):
                grid.remove_wall(x, y, d)

        start = self._random_non_pattern(grid, pattern_cells)
        visited = self._reachable_cells(grid, pattern_cells, start)
        self._connect_isolated(grid, visited, pattern_cells)

    def _dfs_from(
        self,
        grid: MazeGrid,
        start: tuple[int, int],
        visited: set[tuple[int, int]],
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        visited.add(start)
        stack: list[tuple[int, int]] = [start]

        while stack:
            x, y = stack[-1]
            dirs = [NORTH, EAST, SOUTH, WEST]
            self._rng.shuffle(dirs)

            moved = False
            for d in dirs:
                dx, dy = DELTAS[d]
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < grid.width
                    and 0 <= ny < grid.height
                    and (nx, ny) not in visited
                ):
                    grid.remove_wall(x, y, d)
                    visited.add((nx, ny))
                    stack.append((nx, ny))
                    moved = True
                    break

            if not moved:
                stack.pop()

    def _connect_isolated(
        self,
        grid: MazeGrid,
        visited: set[tuple[int, int]],
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        all_cells = {
            (x, y)
            for y in range(grid.height)
            for x in range(grid.width)
            if (x, y) not in pattern_cells
        }
        changed = True
        while changed:
            changed = False
            unvisited = all_cells - visited
            if not unvisited:
                break
            for cell in sorted(unvisited):
                cx, cy = cell
                for d in [NORTH, EAST, SOUTH, WEST]:
                    dx, dy = DELTAS[d]
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in visited and (nx, ny) not in pattern_cells:
                        grid.remove_wall(cx, cy, d)
                        visited.add(cell)
                        self._dfs_from(grid, cell, visited, pattern_cells)
                        changed = True
                        break
                if cell in visited:
                    break

    def _add_extra_passages(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
        extra_ratio: float = 0.15,
    ) -> None:
        candidates: list[tuple[int, int, int]] = []
        for y in range(grid.height):
            for x in range(grid.width):
                if (x, y) in pattern_cells:
                    continue
                for d in (EAST, SOUTH):
                    dx, dy = DELTAS[d]
                    nx, ny = x + dx, y + dy
                    if (
                        0 <= nx < grid.width
                        and 0 <= ny < grid.height
                        and (nx, ny) not in pattern_cells
                        and grid.has_wall(x, y, d)
                    ):
                        candidates.append((x, y, d))

        num_extra = max(1, int(len(candidates) * extra_ratio))
        self._rng.shuffle(candidates)
        for x, y, d in candidates[:num_extra]:
            grid.remove_wall(x, y, d)

    def _fix_3x3_open_areas(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        changed = True
        while changed:
            changed = False
            for y in range(grid.height - 2):
                for x in range(grid.width - 2):
                    if self._is_3x3_open(grid, x, y):
                        cx, cy = x + 1, y + 1
                        grid.set_wall(cx, cy, SOUTH)
                        changed = True

    def _ensure_perfect_tree(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> None:
        nodes = grid.width * grid.height - len(pattern_cells)
        if nodes <= 1:
            return

        edges = self._count_open_edges(grid, pattern_cells)
        if edges <= nodes - 1:
            return

        open_edges = set(self._list_open_edges(grid, pattern_cells))
        tree_edges = self._bfs_tree_edges(grid, pattern_cells)
        extra_edges = list(open_edges - tree_edges)
        self._rng.shuffle(extra_edges)

        for x, y, d in extra_edges:
            if edges <= nodes - 1:
                break
            grid.set_wall(x, y, d)
            edges -= 1

    @staticmethod
    def _count_open_edges(
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> int:
        count = 0
        for y in range(grid.height):
            for x in range(grid.width):
                if (x, y) in pattern_cells:
                    continue
                if x + 1 < grid.width and (x + 1, y) not in pattern_cells:
                    if not grid.has_wall(x, y, EAST):
                        count += 1
                if y + 1 < grid.height and (x, y + 1) not in pattern_cells:
                    if not grid.has_wall(x, y, SOUTH):
                        count += 1
        return count

    @staticmethod
    def _list_open_edges(
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> list[tuple[int, int, int]]:
        edges: list[tuple[int, int, int]] = []
        for y in range(grid.height):
            for x in range(grid.width):
                if (x, y) in pattern_cells:
                    continue
                if x + 1 < grid.width and (x + 1, y) not in pattern_cells:
                    if not grid.has_wall(x, y, EAST):
                        edges.append((x, y, EAST))
                if y + 1 < grid.height and (x, y + 1) not in pattern_cells:
                    if not grid.has_wall(x, y, SOUTH):
                        edges.append((x, y, SOUTH))
        return edges

    @staticmethod
    def _bfs_tree_edges(
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> set[tuple[int, int, int]]:
        def canonical_edge(x: int, y: int, d: int) -> tuple[int, int, int]:
            if d == EAST:
                return (x, y, EAST)
            if d == SOUTH:
                return (x, y, SOUTH)
            if d == WEST:
                return (x - 1, y, EAST)
            return (x, y - 1, SOUTH)

        start = grid.entry
        if start in pattern_cells:
            return set()

        visited: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])
        tree_edges: set[tuple[int, int, int]] = set()

        while queue:
            cx, cy = queue.popleft()
            for d in [NORTH, EAST, SOUTH, WEST]:
                if grid.has_wall(cx, cy, d):
                    continue
                dx, dy = DELTAS[d]
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                nxt = (nx, ny)
                if nxt in pattern_cells or nxt in visited:
                    continue
                visited.add(nxt)
                queue.append(nxt)
                tree_edges.add(canonical_edge(cx, cy, d))

        return tree_edges

    @staticmethod
    def _is_fully_connected(
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> bool:
        start = grid.entry
        if start in pattern_cells:
            return False

        total = grid.width * grid.height - len(pattern_cells)
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([start])
        visited.add(start)

        while queue:
            cx, cy = queue.popleft()
            for d in [NORTH, EAST, SOUTH, WEST]:
                if grid.has_wall(cx, cy, d):
                    continue
                dx, dy = DELTAS[d]
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                nxt = (nx, ny)
                if nxt in pattern_cells or nxt in visited:
                    continue
                visited.add(nxt)
                queue.append(nxt)

        return len(visited) == total

    @staticmethod
    def _reachable_cells(
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
        start: tuple[int, int],
    ) -> set[tuple[int, int]]:
        if start in pattern_cells:
            return set()

        visited: set[tuple[int, int]] = {start}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            for d in [NORTH, EAST, SOUTH, WEST]:
                if grid.has_wall(cx, cy, d):
                    continue
                dx, dy = DELTAS[d]
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                nxt = (nx, ny)
                if nxt in pattern_cells or nxt in visited:
                    continue
                visited.add(nxt)
                queue.append(nxt)

        return visited

    @staticmethod
    def _is_3x3_open(grid: MazeGrid, x: int, y: int) -> bool:
        for row in range(y, y + 3):
            for col in range(x, x + 3):
                if col < x + 2 and grid.has_wall(col, row, EAST):
                    return False
                if row < y + 2 and grid.has_wall(col, row, SOUTH):
                    return False
        return True

    def _open_border(
        self,
        grid: MazeGrid,
        coord: tuple[int, int],
    ) -> None:
        x, y = coord
        if x == 0:
            direction = WEST
        elif x == grid.width - 1:
            direction = EAST
        elif y == 0:
            direction = NORTH
        else:
            direction = SOUTH

        grid.cells[y][x].mask &= ~(1 << direction)

    def _bfs_path(
        self,
        grid: MazeGrid,
    ) -> list[tuple[int, int]]:
        start = grid.entry
        goal = grid.exit_
        if start == goal:
            return [start]

        prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == goal:
                break
            for d in [NORTH, EAST, SOUTH, WEST]:
                if not grid.has_wall(cx, cy, d):
                    dx, dy = DELTAS[d]
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                        continue
                    nxt = (nx, ny)
                    if nxt not in prev:
                        prev[nxt] = (cx, cy)
                        queue.append(nxt)

        if goal not in prev:
            return []

        path: list[tuple[int, int]] = []
        node: tuple[int, int] | None = goal
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
        return path

    def _random_non_pattern(
        self,
        grid: MazeGrid,
        pattern_cells: set[tuple[int, int]],
    ) -> tuple[int, int]:
        candidates = [
            (x, y)
            for y in range(grid.height)
            for x in range(grid.width)
            if (x, y) not in pattern_cells
        ]
        if not candidates:
            raise RuntimeError("No non-pattern cells available in the maze.")
        return self._rng.choice(candidates)
