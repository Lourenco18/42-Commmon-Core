from mazegen.generator import MazeGenerator
from mazegen.maze import (
    EAST,
    NORTH,
    OPPOSITE,
    SOUTH,
    WEST,
    Cell,
    MazeGrid,
)
from mazegen.solver import MazeSolver, NoPathError

__all__ = [
    # Main classes
    "MazeGenerator",
    "MazeGrid",
    "MazeSolver",
    "Cell",
    # Exceptions
    "NoPathError",
    # Direction constants
    "NORTH",
    "EAST",
    "SOUTH",
    "WEST",
    "OPPOSITE",
]

__version__ = "1.0.0"
__author__ = "dsilva-c, dasantos"
