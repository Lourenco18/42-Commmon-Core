"""Level management for Pac-Man."""
import logging
import random
from typing import Optional

from src.config import Config
from src.entities import Ghost, GhostState, Pacgum, Player, SuperPacgum
from src.maze import Maze, generate_maze

logger = logging.getLogger(__name__)
GHOST_COLORS: list[str] = ["red", "pink", "cyan", "orange"]


class Level:
    """Single game level state."""

    def __init__(self, config: Config, level_index: int, player_lives: int,
                 player_score: int, seed: Optional[int] = None) -> None:
        """Initialize level."""
        self.config = config
        self.level_index = level_index
        spec = config.levels[min(level_index, len(config.levels) - 1)]
        self.width = spec["width"]
        self.height = spec["height"]
        self.time_remaining: float = float(config.level_max_time)
        self.level_won = False
        self.level_lost = False

        try:
            self.maze: Maze = generate_maze(self.width, self.height, seed)
        except RuntimeError as exc:
            logger.error(
                "Level %d maze generation failed: %s",
                level_index,
                exc)
            raise

        center_row = self.maze.height // 2
        center_col = self.maze.width // 2
        self.player: Player = Player(center_row, center_col, player_lives)
        self.player.score = player_score

        corners = [
            (0, 0),
            (0, self.maze.width - 1),
            (self.maze.height - 1, 0),
            (self.maze.height - 1, self.maze.width - 1),
        ]
        self.ghosts: list[Ghost] = [
            Ghost(r, c, r, c, GHOST_COLORS[i])
            for i, (r, c) in enumerate(corners)
        ]
        self.pacgums: list[Pacgum] = []
        self.super_pacgums: list[SuperPacgum] = []
        self._place_items()

    def _reachable_cells(self, start: tuple[int, int]) -> set[tuple[int, int]]:
        """Return all cells reachable from `start` via maze corridors.

        The assigned A-Maze-ing generator can occasionally produce a few
        cells that are walled off from the rest of the maze. Restricting
        pacgum placement to this reachable set guarantees the level can
        always be fully cleared by the player.
        """
        visited: set[tuple[int, int]] = {start}
        queue: list[tuple[int, int]] = [start]
        while queue:
            cur = queue.pop()
            for nxt in self.maze.neighbours(*cur):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return visited

    def _place_items(self) -> None:
        """Place pacgums and super-pacgums."""
        corner_cells = {
            (0, 0),
            (0, self.maze.width - 1),
            (self.maze.height - 1, 0),
            (self.maze.height - 1, self.maze.width - 1),
        }
        for r, c in corner_cells:
            self.super_pacgums.append(SuperPacgum(r, c))
        center = (self.player.row, self.player.col)
        reachable = self._reachable_cells(center)
        skip = corner_cells | {center}
        all_cells = [
            cell for cell in reachable if cell not in skip
        ]
        target = min(len(all_cells), self.config.pacgum)
        for r, c in random.sample(all_cells, k=min(target, len(all_cells))):
            self.pacgums.append(Pacgum(r, c))

    def update(self, dt: float) -> None:
        """Advance level by dt seconds."""
        if self.level_won or self.level_lost:
            return
        self.time_remaining -= dt
        if self.time_remaining <= 0:
            self.time_remaining = 0
            self.level_lost = True
            return
        self.player.update(self.maze)
        for ghost in self.ghosts:
            ghost.update(self.maze, self.player.row, self.player.col)
        self._check_pacgum_collision()
        self._check_ghost_collision()
        self._check_win()

    def _check_pacgum_collision(self) -> None:
        pr, pc = self.player.row, self.player.col
        for pg in self.pacgums:
            if not pg.eaten and pg.row == pr and pg.col == pc:
                pg.eaten = True
                self.player.score += self.config.points_per_pacgum
        for spg in self.super_pacgums:
            if not spg.eaten and spg.row == pr and spg.col == pc:
                spg.eaten = True
                self.player.score += self.config.points_per_super_pacgum
                for ghost in self.ghosts:
                    ghost.make_edible()

    def _check_ghost_collision(self) -> None:
        pr, pc = self.player.row, self.player.col
        for ghost in self.ghosts:
            if ghost.row == pr and ghost.col == pc:
                if ghost.state == GhostState.EDIBLE:
                    ghost.eat()
                    self.player.score += self.config.points_per_ghost
                elif (
                    ghost.state == GhostState.CHASING
                    and not self.player.invincible
                ):
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.level_lost = True
                    else:
                        self.player.respawn()

    def _check_win(self) -> None:
        if self.pacgums and all(pg.eaten for pg in self.pacgums):
            self.level_won = True

    def toggle_invincibility(self) -> None:
        """Toggle invincibility cheat."""
        self.player.invincible = not self.player.invincible

    def skip_level(self) -> None:
        """Skip current level cheat."""
        self.level_won = True

    def toggle_ghost_freeze(self) -> None:
        """Toggle ghost freeze cheat."""
        all_frozen = all(g.state == GhostState.FROZEN for g in self.ghosts
                         if g.state != GhostState.RESPAWNING)
        for ghost in self.ghosts:
            if all_frozen:
                ghost.unfreeze()
            else:
                ghost.freeze()

    def add_extra_life(self) -> None:
        """Add extra life cheat."""
        self.player.lives += 1

    def toggle_speed_boost(self) -> None:
        """Toggle speed boost cheat."""
        self.player.speed_boost = not self.player.speed_boost
