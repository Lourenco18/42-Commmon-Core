import logging
import math
import random
from collections import deque
from enum import Enum, auto
from typing import Optional

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
    """Represent the ghost behavior states."""
    CHASING = auto()
    EDIBLE = auto()
    RESPAWNING = auto()


class Player:
    """Track the player position, movement, score, and lives."""
    BASE_INTERVAL: int = 16
    FAST_INTERVAL: int = 11
    RESPAWN_IMMUNITY_DURATION: int = 180

    def __init__(self, row: int, col: int, lives: int) -> None:
        """Initialize a Player instance.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.
            lives: Number of player lives."""
        self.row = row
        self.col = col
        self.prev_row: int = row
        self.prev_col: int = col
        self.start_row = row
        self.start_col = col
        self.direction: tuple[int, int] = DIR_LEFT
        self.next_direction: tuple[int, int] = DIR_LEFT
        self.lives = lives
        self.score = 0
        self.invincible = False
        self.respawn_immunity_timer: int = 0
        self.speed_boost = False
        self.move_interval = self.BASE_INTERVAL
        self.move_timer = self.move_interval - 1

    @property
    def is_immune(self) -> bool:
        """Report whether the player currently cannot be harmed.

        Returns:
            Result of the operation."""
        return self.invincible or self.respawn_immunity_timer > 0

    def respawn(self) -> None:
        """Return the player to the starting cell with temporary immunity."""
        self.row = self.start_row
        self.col = self.start_col
        self.prev_row = self.start_row
        self.prev_col = self.start_col
        self.direction = DIR_LEFT
        self.next_direction = DIR_LEFT
        self.move_timer = self.move_interval - 1
        self.respawn_immunity_timer = self.RESPAWN_IMMUNITY_DURATION

    def set_direction(self, direction: tuple[int, int]) -> None:
        """Queue a direction for the next available player move.

        Args:
            direction: Direction or wall bit to inspect."""
        self.next_direction = direction

    def visual_pos(self) -> tuple[float, float]:
        """Return an interpolated position for smooth rendering.

        Returns:
            Result of the operation."""
        t = min(1.0, self.move_timer / max(1, self.move_interval))
        v_row = self.prev_row + (self.row - self.prev_row) * t
        v_col = self.prev_col + (self.col - self.prev_col) * t
        return (v_row, v_col)

    def update(self, maze: Maze) -> None:
        """Advance the entity or game state by one update step.

        Args:
            maze: Maze used for movement or collision checks."""
        if self.respawn_immunity_timer > 0:
            self.respawn_immunity_timer -= 1

        new_interval = (
            self.FAST_INTERVAL if self.speed_boost else self.BASE_INTERVAL
        )
        if new_interval != self.move_interval:
            ratio = self.move_timer / max(1, self.move_interval)
            self.move_interval = new_interval
            self.move_timer = round(ratio * self.move_interval)

        self.move_timer += 1
        if self.move_timer < self.move_interval:
            return

        self.prev_row, self.prev_col = self.row, self.col
        for direction in (self.next_direction, self.direction):
            bit = DIR_TO_BIT.get(direction, 0)
            if not maze.is_wall(self.row, self.col, bit):
                nr, nc = self.row + direction[0], self.col + direction[1]
                if maze.passable(nr, nc):
                    self.row, self.col = nr, nc
                    self.direction = direction
                    self.move_timer = 0
                    return

        self.move_timer = self.move_interval - 1


class Ghost:
    """Track a ghost and its movement and behavior state."""
    NORMAL_INTERVAL: int = 32
    EDIBLE_INTERVAL: int = 48
    RESPAWN_DELAY: int = 600
    EDIBLE_DURATION: int = 720
    EYES_INTERVAL: int = 8
    EYES_WANDER_DURATION: int = 300
    EYES_WANDER_RADIUS: float = 4.0
    EYES_WANDER_INTERVAL: int = 14

    def __init__(
        self,
        row: int,
        col: int,
        corner_row: int,
        corner_col: int,
        color_name: str,
        normal_interval: int = NORMAL_INTERVAL,
        edible_interval: int = EDIBLE_INTERVAL,
        respawn_delay: int = RESPAWN_DELAY,
        edible_duration: int = EDIBLE_DURATION,
        eyes_interval: int = EYES_INTERVAL,
        eyes_wander_duration: int = EYES_WANDER_DURATION,
        eyes_wander_radius: float = EYES_WANDER_RADIUS,
        eyes_wander_interval: int = EYES_WANDER_INTERVAL,
    ) -> None:
        """Initialize a Ghost instance.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.
            corner_row: Home-corner row coordinate.
            corner_col: Home-corner column coordinate.
            color_name: Ghost color and behavior identity.
            normal_interval: Movement interval while chasing.
            edible_interval: Movement interval while edible.
            respawn_delay: Delay before a ghost respawns.
            edible_duration: Duration of the edible state.
            eyes_interval: Movement interval while returning.
            eyes_wander_duration: Duration of the eyes wandering phase.
            eyes_wander_radius: Maximum wandering distance from home.
            eyes_wander_interval: Movement interval while wandering."""
        self.row = row
        self.col = col
        self.prev_row: int = row
        self.prev_col: int = col
        self.ai_prev_row: int = row
        self.ai_prev_col: int = col
        self.corner_row = corner_row
        self.corner_col = corner_col
        self.color_name = color_name
        self.direction: tuple[int, int] = DIR_LEFT
        self.state: GhostState = GhostState.CHASING
        self.frozen: bool = False
        self.edible_timer = 0
        self.respawn_timer = 0
        self.move_timer = 0
        self.normal_interval: int = max(5, normal_interval)
        self.edible_interval: int = max(8, edible_interval)
        self.respawn_delay: int = max(0, respawn_delay)
        self.edible_duration: int = max(1, edible_duration)
        self.eyes_interval: int = max(2, eyes_interval)
        self.eyes_path: list[tuple[int, int]] = []
        self.eyes_wander_duration: int = max(0, eyes_wander_duration)
        self.eyes_wander_radius: float = max(0.0, eyes_wander_radius)
        self.eyes_wander_interval: int = max(3, eyes_wander_interval)
        self.eyes_phase: str = ""
        self.eyes_wander_timer: int = 0
        self.move_interval: int = self.normal_interval

    def _set_interval(self, new_interval: int) -> None:
        """Change movement timing while preserving step progress.

        Args:
            new_interval: Value used to new interval."""
        if new_interval != self.move_interval:
            ratio = self.move_timer / max(1, self.move_interval)
            self.move_interval = new_interval
            self.move_timer = round(ratio * self.move_interval)

    def make_edible(self) -> None:
        """Make the ghost edible for the configured duration."""
        if self.state != GhostState.RESPAWNING:
            self.state = GhostState.EDIBLE
            self.edible_timer = self.edible_duration
            self._set_interval(self.edible_interval)
            self.ai_prev_row, self.ai_prev_col = self.row, self.col

    def eat(self, maze: Maze) -> None:
        """Begin the ghost eaten and respawning sequence.

        Args:
            maze: Maze used for movement or collision checks."""
        self.state = GhostState.RESPAWNING
        self.respawn_timer = self.respawn_delay
        self.edible_timer = 0
        self.eyes_path = self._path_to_corner(maze)
        self.eyes_phase = "go"
        self.eyes_wander_timer = 0
        self._set_interval(self.eyes_interval)

    def _path_to_corner(self, maze: Maze) -> list[tuple[int, int]]:
        """Find a route from the ghost to its home corner.

        Args:
            maze: Maze used for movement or collision checks.

        Returns:
            Result of the operation."""
        start = (self.row, self.col)
        goal = (self.corner_row, self.corner_col)
        if start == goal:
            return []
        parent: dict[tuple[int, int], Optional[tuple[int, int]]] = {
            start: None
        }
        queue: deque[tuple[int, int]] = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            for nxt in maze.neighbours(*cur):
                if nxt not in parent:
                    parent[nxt] = cur
                    queue.append(nxt)
        if goal not in parent:
            return []
        path: list[tuple[int, int]] = []
        node: Optional[tuple[int, int]] = goal
        while node is not None and node != start:
            path.append(node)
            node = parent[node]
        path.reverse()
        return path

    def _revive(self) -> None:
        """Restore the ghost to its normal chasing state."""
        self.state = GhostState.CHASING
        self.eyes_path = []
        self.eyes_phase = ""
        self.eyes_wander_timer = 0
        self.prev_row, self.prev_col = self.row, self.col
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self._set_interval(self.normal_interval)
        self.move_timer = 0

    def _step_along_path(self) -> None:
        """Move the ghost one step along its return path."""
        next_row, next_col = self.eyes_path.pop(0)
        self.direction = (next_row - self.row, next_col - self.col)
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self.row, self.col = next_row, next_col

    def _wander_step(self, maze: Maze) -> None:
        """Move the ghost eyes near its home corner.

        Args:
            maze: Maze used for movement or collision checks."""
        near = [
            pos
            for pos in maze.neighbours(self.row, self.col)
            if math.hypot(pos[0] - self.corner_row,
                          pos[1] - self.corner_col) <= self.eyes_wander_radius
        ]
        if not near:
            return
        forward = [
            pos for pos in near
            if pos != (self.ai_prev_row, self.ai_prev_col)
        ]
        next_row, next_col = random.choice(forward or near)
        self.direction = (next_row - self.row, next_col - self.col)
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self.row, self.col = next_row, next_col

    def _move_eyes(self, maze: Maze) -> None:
        """Advance the ghost eyes return and revival behavior.

        Args:
            maze: Maze used for movement or collision checks."""
        self.prev_row, self.prev_col = self.row, self.col
        if self.eyes_phase == "go":
            if self.eyes_path:
                self._step_along_path()
                return
            if self.eyes_wander_duration <= 0:
                self._revive()
                return
            self.eyes_phase = "wander"
            self.eyes_wander_timer = 0
            self._set_interval(self.eyes_wander_interval)

        if self.eyes_phase == "wander":
            if self.eyes_wander_timer < self.eyes_wander_duration:
                self._wander_step(maze)
                return
            self.eyes_phase = "return"
            self.eyes_path = self._path_to_corner(maze)
            self._set_interval(self.eyes_interval)

        if self.eyes_phase == "return":
            if self.eyes_path:
                self._step_along_path()
                return
            self._revive()

    def freeze(self) -> None:
        """Stop the ghost from moving."""
        self.frozen = True

    def unfreeze(self) -> None:
        """Allow the ghost to move again."""
        self.frozen = False

    def visual_pos(self) -> tuple[float, float]:
        """Return an interpolated position for smooth rendering.

        Returns:
            Result of the operation."""
        t = min(1.0, self.move_timer / max(1, self.move_interval))
        v_row = self.prev_row + (self.row - self.prev_row) * t
        v_col = self.prev_col + (self.col - self.prev_col) * t
        return (v_row, v_col)

    def update(
        self,
        maze: Maze,
        player_row: int,
        player_col: int,
        player_dir: tuple[int, int] = DIR_LEFT,
        blinky_pos: Optional[tuple[int, int]] = None,
    ) -> None:
        """Advance the entity or game state by one update step.

        Args:
            maze: Maze used for movement or collision checks.
            player_row: Player row coordinate.
            player_col: Player column coordinate.
            player_dir: Player movement direction.
            blinky_pos: Position of the red ghost, if available."""
        if self.frozen:
            return
        if self.state == GhostState.RESPAWNING:
            if self.eyes_phase == "wander":
                self.eyes_wander_timer += 1
            self.move_timer += 1
            if self.move_timer < self.move_interval:
                return
            self.move_timer = 0
            self._move_eyes(maze)
            return
        if self.state == GhostState.EDIBLE:
            self.edible_timer -= 1
            if self.edible_timer <= 0:
                self.state = GhostState.CHASING
                self._set_interval(self.normal_interval)
        self.move_timer += 1
        if self.move_timer < self.move_interval:
            return
        self.move_timer = 0
        self._move(maze, player_row, player_col, player_dir, blinky_pos)

    def _get_target_tile(
        self,
        player_row: int,
        player_col: int,
        player_dir: tuple[int, int],
        blinky_pos: Optional[tuple[int, int]],
    ) -> tuple[int, int]:
        """Choose a chase target based on ghost identity.

        Args:
            player_row: Player row coordinate.
            player_col: Player column coordinate.
            player_dir: Player movement direction.
            blinky_pos: Position of the red ghost, if available.

        Returns:
            Result of the operation."""
        if self.color_name == "red":
            return (player_row, player_col)

        if self.color_name == "pink":
            return (
                player_row + 4 * player_dir[0],
                player_col + 4 * player_dir[1],
            )

        if self.color_name == "cyan":
            pivot_r = player_row + 2 * player_dir[0]
            pivot_c = player_col + 2 * player_dir[1]
            if blinky_pos is None:
                return (pivot_r, pivot_c)
            br, bc = blinky_pos
            return (pivot_r + (pivot_r - br), pivot_c + (pivot_c - bc))

        if self.color_name == "orange":
            dist = math.hypot(self.row - player_row, self.col - player_col)
            if dist > 8.0:
                return (player_row, player_col)
            return (self.corner_row, self.corner_col)

        return (player_row, player_col)

    def _move(
        self,
        maze: Maze,
        player_row: int,
        player_col: int,
        player_dir: tuple[int, int],
        blinky_pos: Optional[tuple[int, int]],
    ) -> None:
        """Choose a corridor step according to the ghost state.

        Args:
            maze: Maze used for movement or collision checks.
            player_row: Player row coordinate.
            player_col: Player column coordinate.
            player_dir: Player movement direction.
            blinky_pos: Position of the red ghost, if available."""
        self.prev_row, self.prev_col = self.row, self.col
        neighbours = maze.neighbours(self.row, self.col)
        if not neighbours:
            return

        candidates = [
            pos
            for pos in neighbours
            if pos != (self.ai_prev_row, self.ai_prev_col)
        ]
        if not candidates:
            candidates = neighbours

        if self.state == GhostState.CHASING:
            target_r, target_c = self._get_target_tile(
                player_row, player_col, player_dir, blinky_pos
            )

            def key(pos: tuple[int, int]) -> float:
                """Measure candidate distance from the chase target."""
                return math.hypot(pos[0] - target_r, pos[1] - target_c)
        else:
            def key(pos: tuple[int, int]) -> float:
                """Rank candidate cells by distance from the player."""
                return (
                    -math.hypot(pos[0] - player_row, pos[1] - player_col)
                    + random.uniform(0, 1.5)
                )

        next_row, next_col = min(candidates, key=key)
        self.direction = (next_row - self.row, next_col - self.col)
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self.row, self.col = next_row, next_col


class Pacgum:

    """Represent a regular collectible in the maze."""
    def __init__(self, row: int, col: int) -> None:
        """Initialize a Pacgum instance.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate."""
        self.row = row
        self.col = col
        self.eaten = False


class SuperPacgum:

    """Represent a power pellet in the maze."""
    def __init__(self, row: int, col: int) -> None:
        """Initialize a SuperPacgum instance.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate."""
        self.row = row
        self.col = col
        self.eaten = False
