from __future__ import annotations

from dataclasses import dataclass, field

NORTH: int = 0
EAST: int = 1
SOUTH: int = 2
WEST: int = 3

OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    EAST: WEST,
    SOUTH: NORTH,
    WEST: EAST,
}

DELTAS: dict[int, tuple[int, int]] = {
    NORTH: (0, -1),
    EAST:  (1,  0),
    SOUTH: (0,  1),
    WEST:  (-1, 0),
}


@dataclass
class Cell:
    x: int
    y: int
    mask: int = field(default=0xF)

    def has_wall(self, direction: int) -> bool:
        return bool(self.mask & (1 << direction))

    def hex_char(self) -> str:
        return format(self.mask, 'X')

    def __repr__(self) -> str:
        return f"Cell(x={self.x}, y={self.y}, mask=0x{self.mask:X})"


class MazeGrid:
    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit_: tuple[int, int],
    ) -> None:
        if width < 2 or height < 2:
            raise ValueError(
                f"Maze dimensions must be at least 2x2, got {width}x{height}."
            )
        self._validate_coord("entry", entry, width, height)
        self._validate_coord("exit", exit_, width, height)
        if entry == exit_:
            raise ValueError("Entry and exit coordinates must be different.")

        self.width: int = width
        self.height: int = height
        self.entry: tuple[int, int] = entry
        self.exit_: tuple[int, int] = exit_

        self.cells: list[list[Cell]] = [
            [Cell(x=c, y=r) for c in range(width)]
            for r in range(height)
        ]

    def has_wall(self, x: int, y: int, direction: int) -> bool:
        return self.cells[y][x].has_wall(direction)

    def remove_wall(self, x: int, y: int, direction: int) -> None:
        self.cells[y][x].mask &= ~(1 << direction)

        dx, dy = DELTAS[direction]
        nx, ny = x + dx, y + dy
        if 0 <= nx < self.width and 0 <= ny < self.height:
            self.cells[ny][nx].mask &= ~(1 << OPPOSITE[direction])

    def set_wall(self, x: int, y: int, direction: int) -> None:
        self.cells[y][x].mask |= (1 << direction)

        dx, dy = DELTAS[direction]
        nx, ny = x + dx, y + dy
        if 0 <= nx < self.width and 0 <= ny < self.height:
            self.cells[ny][nx].mask |= (1 << OPPOSITE[direction])

    def to_hex_grid(self) -> list[list[str]]:
        return [
            [cell.hex_char() for cell in row]
            for row in self.cells
        ]

    def is_valid(self) -> bool:
        for r in range(self.height):
            for c in range(self.width):
                v = self.cells[r][c].mask
                if r > 0 and (v & 1) != ((self.cells[r - 1][c].mask >> 2) & 1):
                    return False
                if (
                    c < self.width - 1
                    and (v >> 1) & 1
                    != (self.cells[r][c + 1].mask >> 3) & 1
                ):
                    return False
                if (
                    r < self.height - 1
                    and (v >> 2) & 1 != self.cells[r + 1][c].mask & 1
                ):
                    return False
                if (
                    c > 0
                    and (v >> 3) & 1
                    != (self.cells[r][c - 1].mask >> 1) & 1
                ):
                    return False
        return True

    @staticmethod
    def _validate_coord(
        name: str,
        coord: tuple[int, int],
        width: int,
        height: int,
    ) -> None:
        x, y = coord
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError(
                f"{name} coordinate {coord} is outside the "
                f"{width}x{height} grid."
            )

    def __repr__(self) -> str:
        return (
            f"MazeGrid(width={self.width}, height={self.height}, "
            f"entry={self.entry}, exit={self.exit_})"
        )
