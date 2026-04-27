from __future__ import annotations

import sys

from config_parser import ConfigParser
from mazegen.generator import MazeGenerator
from mazegen.solver import MazeSolver, NoPathError
from output_writer import OutputWriter
from export_svg import write_svg


def main(config_path: str) -> int:
    # configuration file
    try:
        parser = ConfigParser(config_path)
        cfg = parser.parse()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[config] Error: {exc}", file=sys.stderr)
        return 1

    # generate maze
    try:
        gen = MazeGenerator(
            width=cfg.width,
            height=cfg.height,
            seed=cfg.seed,
            perfect=cfg.perfect,
            algorithm=cfg.algorithm,
        )
        grid = gen.generate(entry=cfg.entry, exit_=cfg.exit_)
    except (ValueError, RuntimeError) as exc:
        print(f"[generator] Error: {exc}", file=sys.stderr)
        return 1

    # path
    try:
        solver = MazeSolver(grid)
        directions = solver.solve()
    except NoPathError as exc:
        print(f"[solver] Error: {exc}", file=sys.stderr)
        return 1

    # output file
    try:
        writer = OutputWriter()
        writer.write(grid, directions, cfg.output_file)
        print(f"[output] Maze written to '{cfg.output_file}'.")
    except (OSError, ValueError) as exc:
        print(f"[output] Error writing file: {exc}", file=sys.stderr)
        return 1

    if cfg.export_svg is not None:
        try:
            write_svg(
                grid,
                cfg.export_svg,
                cell_size=cfg.export_cell_size,
                wall_thickness=cfg.export_wall_thickness,
            )
            print(f"[export] SVG written to '{cfg.export_svg}'.")
        except (OSError, ValueError) as exc:
            print(f"[export] Error writing SVG: {exc}", file=sys.stderr)

    # visual rendering
    path_cells = solver.get_path_cells()

    if cfg.display_mode in ("ascii", "both"):
        try:
            from renderer_ascii import AsciiRenderer
            renderer_a = AsciiRenderer(
                grid=grid,
                generator=gen,
                cfg=cfg,
            )
            renderer_a.render(grid, show_path=False, path_cells=path_cells)
        except ImportError:
            print(
                "[renderer] ASCII renderer not yet available.",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"[renderer] ASCII error: {exc}", file=sys.stderr)

    if cfg.display_mode in ("mlx", "both"):
        try:
            from renderer_mlx import MlxRenderer
            renderer_m = MlxRenderer(
                grid=grid,
                generator=gen,
                cfg=cfg,
            )
            renderer_m.render(grid, show_path=False, path_cells=path_cells)
        except ImportError:
            print(
                "[renderer] MLX renderer not yet available.",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"[renderer] MLX error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            f"Usage: python3 {sys.argv[0]} config.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.exit(main(sys.argv[1]))
