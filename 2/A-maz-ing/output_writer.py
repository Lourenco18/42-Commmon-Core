from __future__ import annotations

from mazegen.maze import MazeGrid


class OutputWriter:
    def write(
        self,
        grid: MazeGrid,
        directions: list[str],
        output_path: str,
    ) -> None:
        self._validate_directions(directions)

        entry_x, entry_y = grid.entry
        exit_x, exit_y = grid.exit_
        path_str = "".join(directions)

        with open(output_path, "w", encoding="utf-8", newline="") as fh:
            # Hex grid
            for row in grid.cells:
                fh.write("".join(cell.hex_char() for cell in row) + "\n")

            fh.write("\n")

            # Entry
            fh.write(f"{entry_x},{entry_y}\n")

            # Exit
            fh.write(f"{exit_x},{exit_y}\n")

            # Path direction string
            fh.write(path_str + "\n")

    @staticmethod
    def _validate_directions(directions: list[str]) -> None:
        valid = frozenset("NESW")
        for letter in directions:
            if letter not in valid:
                raise ValueError(
                    f"Invalid direction '{letter}' in path. "
                    f"Expected one of: N, E, S, W."
                )
