import random
from collections import deque
from typing import List, Optional, Tuple


NORTH: int = 0b0001
EAST: int = 0b0010
SOUTH: int = 0b0100
WEST: int = 0b1000

OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    EAST: WEST,
    SOUTH: NORTH,
    WEST: EAST,
}

DELTA: dict[int, Tuple[int, int]] = {
    NORTH: (0, -1),
    EAST: (1, 0),
    SOUTH: (0, 1),
    WEST: (-1, 0),
}

DIR_NAME: dict[str, int] = {
    "N": NORTH,
    "E": EAST,
    "S": SOUTH,
    "W": WEST,
}

DIR_LETTER: dict[int, str] = {v: k for k, v in DIR_NAME.items()}


class MazeGenerator:
    def __init__(
        self,
        width: int = 20,
        height: int = 15,
        seed: Optional[int] = None,
        entry: Optional[Tuple[int, int]] = None,
        exit_: Optional[Tuple[int, int]] = None,
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError("Width and height must both be >= 2.")

        self.width: int = width
        self.height: int = height
        self.seed: Optional[int] = seed
        self.entry: Tuple[int, int] = entry if entry is not None else (0, 0)
        self.exit: Tuple[int, int] = (exit_ if exit_ is not
                                      None else (width - 1, height - 1))
        self._validate_coords(self.entry, "entry")
        self._validate_coords(self.exit, "exit")
        if self.entry == self.exit:
            raise ValueError("Entry and exit must be different cells.")

        self._maze: List[List[int]] = []
        self._solution: List[str] = []
        self._generated: bool = False

    def generate(self, perfect: bool = True) -> None:

        rng = random.Random(self.seed)
        self._init_grid()
        self._carve_dfs(rng)
        self._apply_border_walls()
        self._enforce_no_large_open_areas()
        if not perfect:
            self._add_loops(rng)
        self._embed_42_pattern()
        self._solution = self._bfs_solve()
        self._generated = True

    def get_maze(self) -> List[List[int]]:

        self._assert_generated()
        return [row[:] for row in self._maze]

    def get_solution(self) -> List[str]:

        self._assert_generated()
        return list(self._solution)

    def get_solution_string(self) -> str:
        self._assert_generated()
        return "".join(self._solution)

    def _validate_coords(self, coords: Tuple[int, int], label: str) -> None:

        x, y = coords
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(
                f"{label} coordinates {coords} are outside the maze "
                f"bounds ({self.width}x{self.height})."
            )

    def _assert_generated(self) -> None:

        if not self._generated:
            raise RuntimeError(
                "Maze has not been generated. Call generate() first."
            )

    def _init_grid(self) -> None:

        self._maze = [[0xF] * self.width for _ in range(self.height)]

    def _remove_wall(self, x: int, y: int, direction: int) -> None:

        dx, dy = DELTA[direction]
        nx, ny = x + dx, y + dy
        self._maze[y][x] &= ~direction
        self._maze[ny][nx] &= ~OPPOSITE[direction]

    def _carve_dfs(self, rng: random.Random) -> None:

        visited = [[False] * self.width for _ in range(self.height)]
        stack: List[Tuple[int, int]] = []

        sx, sy = self.entry
        visited[sy][sx] = True
        stack.append((sx, sy))

        while stack:
            cx, cy = stack[-1]
            directions = [NORTH, EAST, SOUTH, WEST]
            rng.shuffle(directions)
            moved = False
            for d in directions:
                dx, dy = DELTA[d]
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < self.width and 0
                        <= ny < self.height and not visited[ny][nx]):
                    self._remove_wall(cx, cy, d)
                    visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    def _apply_border_walls(self) -> None:
        for x in range(self.width):
            self._maze[0][x] |= NORTH
            self._maze[self.height - 1][x] |= SOUTH
        for y in range(self.height):
            self._maze[y][0] |= WEST
            self._maze[y][self.width - 1] |= EAST

        ex, ey = self.entry
        if ey == 0:
            self._maze[ey][ex] &= ~NORTH
        elif ey == self.height - 1:
            self._maze[ey][ex] &= ~SOUTH
        elif ex == 0:
            self._maze[ey][ex] &= ~WEST
        elif ex == self.width - 1:
            self._maze[ey][ex] &= ~EAST

        ex2, ey2 = self.exit
        if ey2 == 0:
            self._maze[ey2][ex2] &= ~NORTH
        elif ey2 == self.height - 1:
            self._maze[ey2][ex2] &= ~SOUTH
        elif ex2 == 0:
            self._maze[ey2][ex2] &= ~WEST
        elif ex2 == self.width - 1:
            self._maze[ey2][ex2] &= ~EAST

    def _add_loops(self, rng: random.Random, ratio: float = 0.1) -> None:
        count = int(self.width * self.height * ratio)
        for _ in range(count):
            x = rng.randint(0, self.width - 2)
            y = rng.randint(0, self.height - 1)
            if self._maze[y][x] & EAST:
                self._remove_wall(x, y, EAST)
                count -= 1
                if count <= 0:
                    break

    def _bfs_solve(self) -> List[str]:

        start = self.entry
        end = self.exit
        parent: dict[Tuple[int, int],
                     Optional[Tuple[Tuple[int, int], str]]] = {start: None}
        queue: deque[Tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == end:
                break
            for d in [NORTH, EAST, SOUTH, WEST]:
                if self._maze[cy][cx] & d:
                    continue  # wall is closed
                dx, dy = DELTA[d]
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in parent:
                        parent[(nx, ny)] = ((cx, cy), DIR_LETTER[d])
                        queue.append((nx, ny))

        if end not in parent:
            raise RuntimeError("No path found between entry and exit.")

        path: List[str] = []
        cur: Tuple[int, int] = end
        while parent[cur] is not None:
            prev_info = parent[cur]
            assert prev_info is not None
            cur, letter = prev_info
            path.append(letter)
        path.reverse()
        return path

    def _get_42_pattern(self) -> Optional[Tuple[int, int, List[List[int]]]]:

        four = [
            [1, 0, 0, 1, 0],
            [1, 0, 0, 1, 0],
            [1, 1, 1, 1, 1],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0],
        ]
        two = [
            [1, 1, 1, 1, 0],
            [0, 0, 0, 0, 1],
            [0, 0, 0, 0, 1],
            [0, 1, 1, 1, 0],
            [1, 0, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1],
        ]
        pattern: List[List[int]] = []
        for r in range(7):
            pattern.append(four[r] + [0] + two[r])

        pat_w = 11
        pat_h = 7
        pad = 1
        needed_w = pat_w + 2 * pad
        needed_h = pat_h + 2 * pad

        if self.width < needed_w or self.height < needed_h:
            return None

        start_x = (self.width - pat_w) // 2
        start_y = (self.height - pat_h) // 2
        return (start_x, start_y, pattern)

    def _embed_42_pattern(self) -> None:
        result = self._get_42_pattern()
        if result is None:
            return

        start_x, start_y, pattern = result
        pat_h = len(pattern)
        pat_w = len(pattern[0])

        cells_42: set[Tuple[int, int]] = set()
        for row in range(pat_h):
            for col in range(pat_w):
                if pattern[row][col]:
                    cells_42.add((start_x + col, start_y + row))

        for (x, y) in cells_42:
            self._maze[y][x] = 0xF
            for d in [NORTH, EAST, SOUTH, WEST]:
                dx2, dy2 = DELTA[d]
                nx, ny = x + dx2, y + dy2
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self._maze[ny][nx] |= OPPOSITE[d]

        self._reconnect_non42(cells_42)

    def _reconnect_non42(
        self,
        cells_42: "set[Tuple[int, int]]",
    ) -> None:
        from collections import deque as _deque

        def reachable() -> "set[Tuple[int, int]]":
            start = self.entry
            vis: set[Tuple[int, int]] = {start}
            q: "deque[Tuple[int, int]]" = _deque([start])
            while q:
                cx, cy = q.popleft()
                for d in [NORTH, EAST, SOUTH, WEST]:
                    if self._maze[cy][cx] & d:
                        continue
                    dx2, dy2 = DELTA[d]
                    nx, ny = cx + dx2, cy + dy2
                    if (0 <= nx < self.width and 0 <= ny < self.height
                            and (nx, ny) not in cells_42
                            and (nx, ny) not in vis):
                        vis.add((nx, ny))
                        q.append((nx, ny))
            return vis

        max_iters = self.width * self.height
        for _ in range(max_iters):
            reach = reachable()

            found = False
            for yy in range(self.height):
                for xx in range(self.width):
                    if (xx, yy) in cells_42 or (xx, yy) in reach:
                        continue
                    for d in [NORTH, EAST, SOUTH, WEST]:
                        dx2, dy2 = DELTA[d]
                        nx, ny = xx + dx2, yy + dy2
                        if (0 <= nx < self.width and 0 <= ny < self.height
                                and (nx, ny) not in cells_42
                                and (nx, ny) in reach):
                            self._maze[yy][xx] &= ~d
                            self._maze[ny][nx] &= ~OPPOSITE[d]
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            if not found:
                for yy in range(self.height):
                    for xx in range(self.width):
                        if (xx, yy) in cells_42 or (xx, yy) in reach:
                            continue
                        for d in [NORTH, EAST, SOUTH, WEST]:
                            dx2, dy2 = DELTA[d]
                            nx, ny = xx + dx2, yy + dy2
                            if (0 <= nx < self.width and 0 <= ny < self.height
                                    and (nx, ny) not in cells_42):
                                self._maze[yy][xx] &= ~d
                                self._maze[ny][nx] &= ~OPPOSITE[d]
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break

            if not found:
                break

            if len(reachable()) == (
                self.width * self.height - len(cells_42)
            ):
                break

    def _reachable_cells(
        self,
        blocked: "set[Tuple[int, int]]",
    ) -> "set[Tuple[int, int]]":

        from collections import deque as _deque
        start = self.entry
        if start in blocked:
            return set()
        visited: set[Tuple[int, int]] = {start}
        queue: "deque[Tuple[int, int]]" = _deque([start])
        while queue:
            cx, cy = queue.popleft()
            for d in [NORTH, EAST, SOUTH, WEST]:
                if self._maze[cy][cx] & d:
                    continue
                dx2, dy2 = DELTA[d]
                nx, ny = cx + dx2, cy + dy2
                if (0 <= nx < self.width and 0 <= ny < self.height
                        and (nx, ny) not in blocked
                        and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return visited

    def _is_42_cell(self, x: int, y: int) -> bool:
        """Return True if (x, y) is part of the embedded '42' pattern."""
        result = self._get_42_pattern()
        if result is None:
            return False
        start_x, start_y, pattern = result
        pat_h = len(pattern)
        pat_w = len(pattern[0])
        col = x - start_x
        row = y - start_y
        if 0 <= row < pat_h and 0 <= col < pat_w:
            return bool(pattern[row][col])
        return False

    def _enforce_no_large_open_areas(self) -> None:

        for y in range(self.height - 2):
            for x in range(self.width - 2):
                if self._is_3x3_open(x, y):
                    cx, cy = x + 1, y + 1
                    self._maze[cy][cx] |= EAST
                    self._maze[cy][cx + 1] |= WEST

    def _is_3x3_open(self, x: int, y: int) -> bool:
        for row in range(y, y + 3):
            for col in range(x, x + 3):
                cell = self._maze[row][col]
                if col < x + 2:
                    if cell & EAST:
                        return False
                if row < y + 2:
                    if cell & SOUTH:
                        return False
        return True
