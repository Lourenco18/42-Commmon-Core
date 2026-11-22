import logging
import math
import os
import sys
from typing import Optional
import pygame
from src.entities import GhostState
from src.highscore import HighscoreEntry
from src.level import Level

logger = logging.getLogger(__name__)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 0)
BLUE = (30, 60, 180)
CORRIDOR_COLOR = (10, 10, 30)
PACGUM_COLOR = (220, 180, 100)
SUPER_PACGUM_COLOR = (255, 255, 180)
HUD_BG = (10, 10, 10)

LEVEL_WALL_COLORS: list[tuple[int, int, int]] = [
    (20, 80, 220),
    (150, 50, 230),
    (20, 190, 90),
    (230, 110, 20),
    (0, 195, 215),
    (225, 45, 145),
    (145, 215, 30),
    (215, 45, 45),
    (105, 90, 245),
    (255, 255, 255),
]

GHOST_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (230, 40, 40),
    "pink": (255, 130, 180),
    "cyan": (0, 210, 210),
    "orange": (240, 140, 20),
    "edible": (30, 60, 200),
    "flashing": (200, 200, 255),
}

DIR_NAMES: dict[tuple[int, int], str] = {
    (-1, 0): "up",
    (1, 0): "down",
    (0, -1): "left",
    (0, 1): "right",
}

CELL_SIZE: int = 31
HUD_HEIGHT: int = 50
ASSET_DIR: str = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__))),
    "assets",
)


class Renderer:
    """Draw the game world, interface screens, and game entities."""
    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize a Renderer instance.

        Args:
            screen: Pygame surface used for drawing."""
        self.screen: pygame.Surface = screen
        self.cell_size: int = CELL_SIZE
        pygame.font.init()
        self.font_large: pygame.font.Font = pygame.font.SysFont(
            "monospace", 36, bold=True)
        self.font_med: pygame.font.Font = pygame.font.SysFont(
            "monospace", 21, bold=True)
        self.font_small: pygame.font.Font = pygame.font.SysFont(
            "monospace", 16)
        self._pacman_angle: float = 0.0
        self._mouth_open: float = 0.3
        self._mouth_dir: int = 1
        self._offset_x: int = 0
        self._pacman_sprites: dict[str, list[pygame.Surface]] = {}
        self._load_pacman_sprites(self.cell_size - 2)
        self._ghost_sprites: dict[str, list[pygame.Surface]] = {}
        self._load_ghost_sprites(self.cell_size - 2)
        self._eyes_sprites: dict[str, list[pygame.Surface]] = {}
        self._load_eyes_sprites(self.cell_size - 2)
        self._pacgum_sprite: Optional[pygame.Surface] = None
        self._super_pacgum_sprites: list[pygame.Surface] = []
        self._load_item_sprites()

    def draw_game(self, level: Level, tick: int) -> None:
        """Draw the maze, actors, items, and in-game HUD.

        Args:
            level: Current level to render.
            tick: Current game frame count."""
        self.screen.fill(BLACK)
        maze_px_w = level.maze.width * self.cell_size
        self._offset_x = max(0, (self.screen.get_width() - maze_px_w) // 2)
        self._animate_pacman(tick)
        self._draw_maze(level)
        self._draw_pacgums(level)
        self._draw_super_pacgums(level, tick)
        self._draw_ghosts(level, tick)
        self._draw_player(level, tick)
        self._draw_hud(level)

    def draw_main_menu(self, selected: int,
                       highscores: list[HighscoreEntry]) -> None:
        """Draw the main menu and its highscore preview.

        Args:
            selected: Selected menu item index.
            highscores: Highscore entries to display."""
        self.screen.fill(BLACK)
        self._draw_title("PAC-MAN", YELLOW, y=60)

        items = ["Start Game", "View Highscores", "Instructions", "Exit"]
        for i, item in enumerate(items):
            color = YELLOW if i == selected else WHITE
            self._draw_centered(item, self.font_med, color, y=180 + i * 44)

        if highscores:
            self._draw_centered(
                "── Top Scores ──", self.font_small, (150, 150, 150), y=380)
            for j, entry in enumerate(highscores[:3]):
                text = f"{j + 1}. {entry.name:<10} {entry.score:>8}"
                self._draw_centered(
                    text, self.font_small, (180, 180, 120), y=402 + j * 20)

        self._draw_centered("↑↓ Navigate   ENTER Select",
                            self.font_small, (100, 100, 100), y=500)

    def draw_highscores(self, entries: list[HighscoreEntry]) -> None:
        """Draw the highscore table.

        Args:
            entries: Highscore entries to display."""
        self.screen.fill(BLACK)
        self._draw_title("HIGH SCORES", YELLOW, y=40)
        if not entries:
            self._draw_centered("No scores yet!", self.font_med, WHITE, y=200)
        else:
            header = f"{'Rank':<5} {'Name':<12} {'Score':>8}"
            self._draw_centered(
                header, self.font_small, (150, 200, 150), y=110)
            for i, entry in enumerate(entries):
                color = YELLOW if i == 0 else WHITE
                line = f"{i + 1:<5} {entry.name:<12} {entry.score:>8}"
                font = self.font_med if i < 3 else self.font_small
                self._draw_centered(line, font, color, y=136 + i * 30)
        self._draw_centered("Press ESC or ENTER to return",
                            self.font_small, (100, 100, 100), y=510)

    def draw_instructions(self) -> None:
        """Draw controls and game instructions."""
        self.screen.fill(BLACK)
        self._draw_title("INSTRUCTIONS", YELLOW, y=40)
        lines = [
            "Move: Arrow keys or WASD",
            "Pause: P or ESC",
            "",
            "Eat all dots to complete the level.",
            "Eat a Power Pellet to make ghosts",
            "vulnerable — then eat them for bonus!",
            "",
            "── Cheat Mode (for evaluation) ──",
            "Shift+C : Toggle Cheat Mode",
            "I  : Toggle Invincibility",
            "X  : Skip Level",
            "F  : Freeze/Unfreeze Ghosts",
            "L / R : Add / Remove Life",
            "+ / - : Add / Remove 10s Time",
            "T   : Freeze/Unfreeze Timer",
            "B  : Toggle Speed Boost",
        ]
        for i, line in enumerate(lines):
            if line.startswith("──"):
                color = (200, 200, 100)
            elif "Toggle Cheat Mode" in line:
                color = (230, 60, 60)
            elif ":" in line:
                color = (65, 125, 235)
            else:
                color = WHITE
            self._draw_centered(line, self.font_small, color, y=105 + i * 24)
        self._draw_centered("Press ESC or ENTER to return",
                            self.font_small, (100, 100, 100), y=510)

    def draw_pause(self, level: Level) -> None:
        """Draw the pause screen and available actions.

        Args:
            level: Current level to render."""
        self.draw_game(level, 0)
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cy = self.screen.get_height() // 2
        self._draw_title("PAUSED", WHITE, y=cy - 70)
        self._draw_centered(
            "ENTER / P  → Resume   ",
            self.font_med,
            YELLOW,
            y=cy + 10)
        self._draw_centered(
            "ESC        → Main Menu",
            self.font_med,
            WHITE,
            y=cy + 54)

    def draw_name_entry(self, score: int, name_buf: str, prompt: str) -> None:
        """Draw the final score and name-entry prompt.

        Args:
            score: Non-negative score value.
            name_buf: Current player-name input.
            prompt: Message shown above the name-entry prompt."""
        self.screen.fill(BLACK)
        self._draw_title(prompt, YELLOW, y=100)
        self._draw_centered(
            f"Final Score: {score}",
            self.font_med,
            WHITE,
            y=190)
        self._draw_centered(
            "Enter your name:", self.font_med, (180, 180, 180), y=240)

        box_w, box_h = 260, 42
        bx = self.screen.get_width() // 2 - box_w // 2
        by = 278
        pygame.draw.rect(self.screen, (40, 40, 80), (bx, by, box_w, box_h))
        pygame.draw.rect(self.screen, YELLOW, (bx, by, box_w, box_h), 2)
        name_surf = self.font_med.render(name_buf + "_", True, WHITE)
        self.screen.blit(name_surf, (bx + 10, by + 7))

        self._draw_centered(
            "ENTER to confirm", self.font_small, (120, 120, 120), y=340)

    def draw_game_over(self, score: int) -> None:
        """Draw the game-over screen and final score.

        Args:
            score: Non-negative score value."""
        self.screen.fill(BLACK)
        self._draw_title("GAME OVER", (230, 40, 40), y=160)
        self._draw_centered(f"Score: {score}", self.font_med, WHITE, y=250)
        self._draw_centered(
            "Press ENTER or SPACE to continue",
            self.font_small,
            (120, 120, 120),
            y=350,
        )

    def draw_victory(self, score: int) -> None:
        """Draw the victory screen and final score.

        Args:
            score: Non-negative score value."""
        self.screen.fill(BLACK)
        self._draw_title("YOU WIN!", YELLOW, y=160)
        self._draw_centered("Congratulations!", self.font_med, WHITE, y=240)
        self._draw_centered(
            f"Final Score: {score}",
            self.font_med,
            YELLOW,
            y=280)
        self._draw_centered(
            "Press ENTER or SPACE to continue",
            self.font_small,
            (120, 120, 120),
            y=350,
        )

    def _animate_pacman(self, tick: int) -> None:
        """Update the Pac-Man animation for the current frame.

        Args:
            tick: Current game frame count."""
        speed = 0.08
        self._mouth_open += speed * self._mouth_dir
        if self._mouth_open > 0.55:
            self._mouth_dir = -1
        elif self._mouth_open < 0.05:
            self._mouth_dir = 1

    def _cell_rect(self, row: float, col: float) -> pygame.Rect:
        """Return the screen rectangle for a maze cell.

        Args:
            row: Maze row coordinate.
            col: Maze column coordinate.

        Returns:
            Result of the operation."""
        x = round(self._offset_x + col * self.cell_size)
        y = round(row * self.cell_size + HUD_HEIGHT)
        return pygame.Rect(x, y, self.cell_size, self.cell_size)

    def _get_wall_color(self, level: Level) -> tuple[int, int, int]:
        """Choose the wall color for the current level.

        Args:
            level: Current level to render.

        Returns:
            Result of the operation."""
        return LEVEL_WALL_COLORS[level.level_index % len(LEVEL_WALL_COLORS)]

    def _draw_maze(self, level: Level) -> None:
        """Draw maze corridors and walls.

        Args:
            level: Current level to render."""
        maze = level.maze
        wall_thickness = 3
        wall_color = self._get_wall_color(level)

        for r in range(maze.height):
            for c in range(maze.width):
                rect = self._cell_rect(r, c)
                pygame.draw.rect(self.screen, CORRIDOR_COLOR, rect)

                cell = maze.grid[r][c]
                if cell & 1:  # N wall
                    pygame.draw.line(
                        self.screen, wall_color,
                        (rect.left, rect.top), (rect.right, rect.top),
                        wall_thickness)
                if cell & 2:  # E wall
                    pygame.draw.line(
                        self.screen, wall_color,
                        (rect.right, rect.top), (rect.right, rect.bottom),
                        wall_thickness)
                if cell & 4:  # S wall
                    pygame.draw.line(
                        self.screen, wall_color,
                        (rect.left, rect.bottom), (rect.right, rect.bottom),
                        wall_thickness)
                if cell & 8:  # W wall
                    pygame.draw.line(
                        self.screen, wall_color,
                        (rect.left, rect.top), (rect.left, rect.bottom),
                        wall_thickness)

    def _load_sprite(
        self, path: str, size: int
    ) -> Optional[pygame.Surface]:
        """Load and scale a sprite, returning None on file errors.

        Args:
            path: Path to the file or resource.
            size: Target sprite width in pixels.

        Returns:
            Result of the operation."""
        if not os.path.exists(path):
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(image, (size, size))
        except (pygame.error, OSError) as exc:
            logger.warning("Failed to load sprite %s: %s", path, exc)
            return None

    def _load_pacman_sprites(self, size: int) -> None:
        """Load Pac-Man animation sprites for each direction.

        Args:
            size: Target sprite width in pixels."""
        base_dir = os.path.join(ASSET_DIR, "player")
        dirs = ("up", "down", "left", "right")

        for d_name in dirs:
            normal_frames = [
                self._load_sprite(
                    os.path.join(base_dir, f"pacman_{d_name}_{i}.png"), size
                )
                for i in range(5)
            ]
            valid_normal = [f for f in normal_frames if f is not None]
            if len(valid_normal) == 5:
                self._pacman_sprites[d_name] = valid_normal

            inv_frames = [
                self._load_sprite(
                    os.path.join(
                        base_dir, f"pacman_invincible_{d_name}_{i}.png"
                    ),
                    size,
                )
                for i in range(5)
            ]
            valid_inv = [f for f in inv_frames if f is not None]
            if len(valid_inv) == 5:
                self._pacman_sprites[f"invincible_{d_name}"] = valid_inv

    def _draw_player(self, level: Level, tick: int) -> None:
        """Draw the player at its interpolated maze position.

        Args:
            level: Current level to render.
            tick: Current game frame count."""
        p = level.player
        v_row, v_col = p.visual_pos()
        rect = self._cell_rect(v_row, v_col)
        dir_name = DIR_NAMES.get(p.direction, "left")
        is_invincible_look = p.invincible
        prefix = "invincible_" if is_invincible_look else ""
        sprite_key = f"{prefix}{dir_name}"
        anim_idx = [0, 1, 2, 3, 4, 3, 2, 1][(tick // 3) % 8]
        if (
            not p.invincible
            and getattr(p, "is_immune", False)
            and (tick // 4) % 2 == 0
        ):
            return
        sprites = self._pacman_sprites.get(sprite_key)
        if sprites and len(sprites) == 5:
            sprite = sprites[anim_idx]
            sx = rect.centerx - sprite.get_width() // 2
            sy = rect.centery - sprite.get_height() // 2
            self.screen.blit(sprite, (sx, sy))
        else:
            cx, cy = rect.centerx, rect.centery
            r = self.cell_size // 2 - 2
            color = (0, 200, 0) if is_invincible_look else YELLOW
            pygame.draw.circle(self.screen, color, (cx, cy), r)

    def _load_ghost_sprites(self, size: int) -> None:
        """Load ghost sprites for colors and behavior states.

        Args:
            size: Target sprite width in pixels."""
        base_dir = os.path.join(ASSET_DIR, "ghosts")
        colors = ("red", "pink", "cyan", "orange")
        dirs = ("up", "down", "left", "right")

        for color in colors:
            for d_name in dirs:
                frames = [
                    self._load_sprite(
                        os.path.join(base_dir, f"{color}_{d_name}_{i}.png"),
                        size,
                    )
                    for i in (0, 1)
                ]
                valid = [f for f in frames if f is not None]
                if valid:
                    self._ghost_sprites[f"{color}_{d_name}"] = valid

            base_frames = [
                self._load_sprite(
                    os.path.join(base_dir, f"{color}_{i}.png"), size
                )
                for i in (0, 1)
            ]
            valid_base = [f for f in base_frames if f is not None]
            if valid_base:
                self._ghost_sprites[color] = valid_base

        for state_name in ("edible", "flashing"):
            frames = [
                self._load_sprite(
                    os.path.join(base_dir, f"{state_name}_{i}.png"), size
                )
                for i in (0, 1)
            ]
            valid = [f for f in frames if f is not None]
            if valid:
                self._ghost_sprites[state_name] = valid

    def _load_eyes_sprites(self, width: int) -> None:
        """Load directional sprites for returning ghost eyes.

        Args:
            width: Maze width in cells."""
        base_dir = os.path.join(ASSET_DIR, "ghosts")
        for d_name in ("up", "down", "left", "right"):
            frames: list[pygame.Surface] = []
            for i in (0, 1):
                path = os.path.join(base_dir, f"eyes_{d_name}_{i}.png")
                if not os.path.exists(path):
                    continue
                try:
                    image = pygame.image.load(path).convert_alpha()
                    ratio = image.get_height() / image.get_width()
                    size = (width, max(1, round(width * ratio)))
                    frames.append(pygame.transform.scale(image, size))
                except (pygame.error, OSError) as exc:
                    logger.warning("Failed to load sprite %s: %s", path, exc)
            if frames:
                self._eyes_sprites[d_name] = frames

    def _draw_eyes(self, ghost: object, rect: pygame.Rect,
                   dir_name: str, anim_frame: int) -> None:
        """Draw ghost eyes during the return sequence.

        Args:
            ghost: Ghost whose eyes are being drawn.
            rect: Destination rectangle in pixels.
            dir_name: Name of the direction to display.
            anim_frame: Current animation frame index."""
        frames = self._eyes_sprites.get(dir_name)
        if frames:
            sprite = frames[anim_frame % len(frames)]
            sx = rect.centerx - sprite.get_width() // 2
            sy = rect.centery - sprite.get_height() // 2
            self.screen.blit(sprite, (sx, sy))
            return

        direction = getattr(ghost, "direction", (0, -1))
        r = max(3, self.cell_size // 6)
        for off in (-r - 1, r + 1):
            cx, cy = rect.centerx + off, rect.centery
            pygame.draw.circle(self.screen, WHITE, (cx, cy), r)
            pygame.draw.circle(
                self.screen, BLUE,
                (cx + direction[1] * r // 2, cy + direction[0] * r // 2),
                max(1, r // 2))

    def _draw_ghosts(self, level: Level, tick: int) -> None:
        """Draw ghosts according to their states and animation frame.

        Args:
            level: Current level to render.
            tick: Current game frame count."""
        anim_frame = (tick // 10) % 2
        for ghost in level.ghosts:
            v_row, v_col = ghost.visual_pos()
            rect = self._cell_rect(v_row, v_col)
            dir_name = DIR_NAMES.get(ghost.direction, "left")

            if ghost.state == GhostState.RESPAWNING:
                self._draw_eyes(ghost, rect, dir_name, anim_frame)
                continue

            sprite = self._get_ghost_sprite(ghost, dir_name, anim_frame)
            if sprite is not None:
                sx = rect.centerx - sprite.get_width() // 2
                sy = rect.centery - sprite.get_height() // 2
                self.screen.blit(sprite, (sx, sy))
                continue

            cx, cy = rect.centerx, rect.centery
            r = self.cell_size // 2 - 2
            if ghost.state == GhostState.EDIBLE:
                if ghost.edible_timer < 180 and (tick // 8) % 2 == 0:
                    color = GHOST_COLORS["flashing"]
                else:
                    color = GHOST_COLORS["edible"]
            else:
                color = GHOST_COLORS.get(ghost.color_name, WHITE)

            pygame.draw.circle(self.screen, color, (cx, cy - r // 4), r)
            pygame.draw.rect(
                self.screen, color, (cx - r, cy - r // 4, r * 2, r + r // 4)
            )
            eye_color = (
                WHITE if ghost.state != GhostState.EDIBLE else (200, 50, 50)
            )
            dx = ghost.direction[1] * 2
            dy = ghost.direction[0] * 2
            pygame.draw.circle(
                self.screen,
                eye_color,
                (cx - r // 3 + dx, cy - r // 3 + dy),
                r // 5,
            )
            pygame.draw.circle(
                self.screen,
                eye_color,
                (cx + r // 3 + dx, cy - r // 3 + dy),
                r // 5,
            )

    def _get_ghost_sprite(
        self, ghost: object, dir_name: str, frame: int
    ) -> Optional[pygame.Surface]:
        """Choose the sprite matching a ghost state and direction.

        Args:
            ghost: Ghost whose eyes are being drawn.
            dir_name: Name of the direction to display.
            frame: Animation frame index.

        Returns:
            Result of the operation."""
        state = getattr(ghost, "state", None)
        if state == GhostState.EDIBLE:
            edible_timer = getattr(ghost, "edible_timer", 0)
            key = (
                "flashing"
                if edible_timer < 120 and frame == 1
                else "edible"
            )
            frames = self._ghost_sprites.get(key)
            if frames:
                return frames[frame % len(frames)]
            return None

        color_name = str(getattr(ghost, "color_name", "red"))
        dir_frames = self._ghost_sprites.get(f"{color_name}_{dir_name}")
        if dir_frames:
            return dir_frames[frame % len(dir_frames)]

        base_frames = self._ghost_sprites.get(color_name)
        if base_frames:
            sprite = base_frames[frame % len(base_frames)]
            if dir_name == "left":
                return pygame.transform.flip(sprite, True, False)
            return sprite
        return None

    def _load_item_sprites(self) -> None:
        """Load regular and power pellet sprites."""
        base_dir = os.path.join(ASSET_DIR, "items")
        pacgum_size = max(8, self.cell_size // 3)
        self._pacgum_sprite = self._load_sprite(
            os.path.join(base_dir, "pacgum.png"), pacgum_size
        )

        super_size = max(14, (self.cell_size * 2) // 3)
        frames = [
            self._load_sprite(
                os.path.join(base_dir, f"super_pacgum_{i}.png"), super_size
            )
            for i in range(3)
        ]
        valid = [f for f in frames if f is not None]
        if len(valid) == 3:
            self._super_pacgum_sprites = valid

    def _draw_pacgums(self, level: Level) -> None:
        """Draw regular collectibles that remain uneaten.

        Args:
            level: Current level to render."""
        r = max(2, self.cell_size // 8)
        for pg in level.pacgums:
            if pg.eaten:
                continue
            rect = self._cell_rect(pg.row, pg.col)
            if self._pacgum_sprite is not None:
                sx = rect.centerx - self._pacgum_sprite.get_width() // 2
                sy = rect.centery - self._pacgum_sprite.get_height() // 2
                self.screen.blit(self._pacgum_sprite, (sx, sy))
            else:
                pygame.draw.circle(
                    self.screen, PACGUM_COLOR, (rect.centerx, rect.centery), r
                )

    def _draw_super_pacgums(self, level: Level, tick: int) -> None:
        """Draw uneaten power pellets with their animation.

        Args:
            level: Current level to render.
            tick: Current game frame count."""
        anim_idx = [0, 1, 2, 1][(tick // 8) % 4]
        base_r = self.cell_size // 4
        pulse = int(2 * math.sin(tick * 0.1))
        r = max(3, base_r + pulse)
        for spg in level.super_pacgums:
            if spg.eaten:
                continue
            rect = self._cell_rect(spg.row, spg.col)
            if len(self._super_pacgum_sprites) == 3:
                sprite = self._super_pacgum_sprites[anim_idx]
                sx = rect.centerx - sprite.get_width() // 2
                sy = rect.centery - sprite.get_height() // 2
                self.screen.blit(sprite, (sx, sy))
            else:
                pygame.draw.circle(
                    self.screen,
                    SUPER_PACGUM_COLOR,
                    (rect.centerx, rect.centery),
                    r,
                )

    def _draw_hud(self, level: Level) -> None:
        """Draw the score, lives, level, and remaining time.

        Args:
            level: Current level to render."""
        p = level.player
        w = self.screen.get_width()
        wall_color = self._get_wall_color(level)
        pygame.draw.rect(self.screen, HUD_BG, (0, 0, w, HUD_HEIGHT))
        pygame.draw.line(self.screen, wall_color,
                         (0, HUD_HEIGHT), (w, HUD_HEIGHT), 2)

        score_surf = self.font_med.render(f"Score: {p.score}", True, YELLOW)
        lives_surf = self.font_med.render(
            f"Lives: {p.lives}", True, (200, 80, 80))
        level_surf = self.font_small.render(
            f"Level {level.level_index + 1}", True, WHITE)
        time_val = max(0, int(level.time_remaining))
        if level.time_frozen:
            time_color = (0, 210, 210)
        elif time_val <= 15:
            time_color = (230, 60, 60)
        else:
            time_color = WHITE
        time_surf = self.font_med.render(
            f"Time: {time_val}s", True, time_color)

        self.screen.blit(score_surf, (10, 8))
        self.screen.blit(lives_surf, (w // 2 - 60, 8))
        self.screen.blit(time_surf, (w - 160, 8))
        self.screen.blit(level_surf, (w // 2 - 38, 30))

        if level.cheat_mode:
            cm_label = self.font_small.render(
                "CHEAT MODE: ", True, (65, 125, 235))
            cm_state = self.font_small.render(
                "ON", True, (230, 50, 50))
            self.screen.blit(cm_label, (10, 30))
            self.screen.blit(cm_state, (10 + cm_label.get_width(), 30))

        cheats = []
        if p.invincible:
            cheats.append("INV")
        if p.speed_boost:
            cheats.append("SPD")
        if any(g.frozen for g in level.ghosts):
            cheats.append("FRZ")
        if level.time_frozen:
            cheats.append("CLK")
        if cheats:
            c_surf = self.font_small.render(
                " ".join(cheats), True, (100, 255, 100))
            self.screen.blit(c_surf, (w - c_surf.get_width() - 10, 30))

    def _draw_title(self, text: str,
                    color: tuple[int, int, int], y: int) -> None:
        """Draw a centered game title.

        Args:
            text: Text to process.
            color: RGB color for the title.
            y: Vertical position in pixels."""
        surf = self.font_large.render(text, True, color)
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))

    def _draw_centered(self, text: str, font: pygame.font.Font,
                       color: tuple[int, int, int], y: int) -> None:
        """Draw text horizontally centered at the requested height.

        Args:
            text: Text to process.
            font: Font used to render the text.
            color: RGB color for the title.
            y: Vertical position in pixels."""
        surf = font.render(text, True, color)
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))

    @staticmethod
    def compute_window_size(
            maze_width: int, maze_height: int) -> tuple[int, int]:
        """Calculate the window dimensions for a maze.

        Args:
            maze_width: Maze width in cells.
            maze_height: Maze height in cells.

        Returns:
            Result of the operation."""
        return (maze_width * CELL_SIZE, maze_height * CELL_SIZE + HUD_HEIGHT)
