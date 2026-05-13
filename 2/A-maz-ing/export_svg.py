from __future__ import annotations

from mazegen.maze import EAST, NORTH, SOUTH, WEST, MazeGrid


def write_svg(
    grid: MazeGrid,
    output_path: str,
    cell_size: int = 24,
    wall_thickness: int = 2,
) -> None:
    width = grid.width * cell_size
    height = grid.height * cell_size

    lines: list[str] = []
    lines.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    lines.append(
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" "
        f"width=\"{width}\" height=\"{height}\" "
        f"viewBox=\"0 0 {width} {height}\">"
    )
    lines.append("<rect width=\"100%\" height=\"100%\" fill=\"white\"/>")
    lines.append(
        f"<g stroke=\"#111\" stroke-width=\"{wall_thickness}\" "
        "stroke-linecap=\"square\">"
    )

    for y in range(grid.height):
        for x in range(grid.width):
            x0 = x * cell_size
            y0 = y * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            if grid.has_wall(x, y, NORTH):
                lines.append(
                    f"<line x1=\"{x0}\" y1=\"{y0}\" "
                    f"x2=\"{x1}\" y2=\"{y0}\"/>"
                )
            if grid.has_wall(x, y, SOUTH):
                lines.append(
                    f"<line x1=\"{x0}\" y1=\"{y1}\" "
                    f"x2=\"{x1}\" y2=\"{y1}\"/>"
                )
            if grid.has_wall(x, y, WEST):
                lines.append(
                    f"<line x1=\"{x0}\" y1=\"{y0}\" "
                    f"x2=\"{x0}\" y2=\"{y1}\"/>"
                )
            if grid.has_wall(x, y, EAST):
                lines.append(
                    f"<line x1=\"{x1}\" y1=\"{y0}\" "
                    f"x2=\"{x1}\" y2=\"{y1}\"/>"
                )

    lines.append("</g>")
    lines.append("</svg>")

    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")
