"""Game entities: Player, Ghost, Pacgum, SuperPacgum."""
import logging
import math
import random
from enum import Enum, auto

from src.maze import Maze, NORTH, EAST, SOUTH, WEST

logger = logging.getLogger(__name__)

DIR_UP: tuple[int, int] = (-1, 0)
DIR_DOWN: tuple[int, int] = (1, 0)
DIR_LEFT: tuple[int, int] = (0, -1)
DIR_RIGHT: tuple[int, int] = (0, 1)

DIR_TO_BIT: dict[tuple[int, int], int] = {
    DIR_UP: NORTH, DIR_DOWN: SOUTH, DIR_LEFT: WEST, DIR_RIGHT: EAST,
}


class GhostState(Enum):
    """Ghost states."""
    CHASING = auto()
    EDIBLE = auto()
    RESPAWNING = auto()
    FROZEN = auto()


class Player:
    """Pac-Man player entity."""
    BASE_INTERVAL: int = 8
    FAST_INTERVAL: int = 4

    def __init__(self, row: int, col: int, lives: int) -> None:
        """Initialize player."""
        self.row = row
        self.col = col
        self.start_row = row
        self.start_col = col
        self.direction: tuple[int, int] = DIR_LEFT
        self.next_direction: tuple[int, int] = DIR_LEFT
        self.lives = lives
        self.score = 0
        self.invincible = False
        self.speed_boost = False
        self.move_timer = 0
        self.move_interval = self.BASE_INTERVAL

    def respawn(self) -> None:
        """Respawn at start position."""
        self.row = self.start_row
        self.col = self.start_col
        self.direction = DIR_LEFT
        self.next_direction = DIR_LEFT
        self.move_timer = 0

    def set_direction(self, direction: tuple[int, int]) -> None:
        """Queue a movement direction."""
        self.next_direction = direction

    def update(self, maze: Maze) -> None:
        """Advance player by one frame."""
        self.move_interval = (
            self.FAST_INTERVAL if self.speed_boost else self.BASE_INTERVAL
        )
        self.move_timer += 1
        if self.move_timer < self.move_interval:
            return
        self.move_timer = 0
        for direction in (self.next_direction, self.direction):
            bit = DIR_TO_BIT.get(direction, 0)
            if not maze.is_wall(self.row, self.col, bit):
                nr, nc = self.row + direction[0], self.col + direction[1]
                if maze.passable(nr, nc):
                    self.row, self.col = nr, nc
                    self.direction = direction
                    return


class Ghost:
    """A ghost enemy."""
    NORMAL_INTERVAL: int = 12
    EDIBLE_INTERVAL: int = 20
    RESPAWN_DELAY: int = 300
    EDIBLE_DURATION: int = 360

    def __init__(self, row: int, col: int, corner_row: int,
                 corner_col: int, color_name: str) -> None:
        """Initialize ghost."""
        self.row = row
        self.col = col
        self.corner_row = corner_row
        self.corner_col = corner_col
        self.color_name = color_name
        self.state: GhostState = GhostState.CHASING
        self.edible_timer = 0
        self.respawn_timer = 0
        self.move_timer = 0
        self.move_interval = self.NORMAL_INTERVAL

    def make_edible(self) -> None:
        """Make ghost vulnerable."""
        if self.state not in (GhostState.RESPAWNING, GhostState.FROZEN):
            self.state = GhostState.EDIBLE
            self.edible_timer = self.EDIBLE_DURATION
            self.move_interval = self.EDIBLE_INTERVAL

    def eat(self) -> None:
        """Ghost was eaten."""
        self.state = GhostState.RESPAWNING
        self.respawn_timer = self.RESPAWN_DELAY
        self.edible_timer = 0

    def freeze(self) -> None:
        """Freeze ghost (cheat)."""
        self.state = GhostState.FROZEN

    def unfreeze(self) -> None:
        """Unfreeze ghost."""
        if self.state == GhostState.FROZEN:
            self.state = GhostState.CHASING

    def update(self, maze: Maze, player_row: int, player_col: int) -> None:
        """Advance ghost by one frame."""
        if self.state == GhostState.FROZEN:
            return
        if self.state == GhostState.RESPAWNING:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.row, self.col = self.corner_row, self.corner_col
                self.state = GhostState.CHASING
                self.move_interval = self.NORMAL_INTERVAL
            return
        if self.state == GhostState.EDIBLE:
            self.edible_timer -= 1
            if self.edible_timer <= 0:
                self.state = GhostState.CHASING
                self.move_interval = self.NORMAL_INTERVAL
        self.move_timer += 1
        if self.move_timer < self.move_interval:
            return
        self.move_timer = 0
        self._move(maze, player_row, player_col)

    def _move(self, maze: Maze, player_row: int, player_col: int) -> None:
        """Move ghost towards/away from player."""
        neighbours = maze.neighbours(self.row, self.col)
        if not neighbours:
            return
        if self.state == GhostState.CHASING:
            def key(pos: tuple[int, int]) -> float:
                dr, dc = pos[0] - player_row, pos[1] - player_col
                return math.sqrt(dr * dr + dc * dc) + random.uniform(0, 1.5)
        else:
            def key(pos: tuple[int, int]) -> float:
                dr, dc = pos[0] - player_row, pos[1] - player_col
                return -math.sqrt(dr * dr + dc * dc) + random.uniform(0, 1.5)
        self.row, self.col = min(neighbours, key=key)


class Pacgum:
    """Small collectible dot."""

    def __init__(self, row: int, col: int) -> None:
        """Initialize pacgum."""
        self.row = row
        self.col = col
        self.eaten = False


class SuperPacgum:
    """Power pellet."""

    def __init__(self, row: int, col: int) -> None:
        """Initialize super-pacgum."""
        self.row = row
        self.col = col
        self.eaten = False
