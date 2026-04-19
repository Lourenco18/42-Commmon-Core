import sys
import os
from mazegen.generator import MazeGenerator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mazegen_src"))


def write_output(gen: MazeGenerator, output_path: str) -> None:
    maze = gen.get_maze()
    solution_str = gen.get_solution_string()
    entry = gen.entry
    exit_ = gen.exit

    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        for row in maze:
            fh.write("".join(format(cell, "X") for cell in row) + "\n")
        fh.write("\n")
        fh.write(f"{entry[0]},{entry[1]}\n")
        fh.write(f"{exit_[0]},{exit_[1]}\n")
        fh.write(solution_str + "\n")
