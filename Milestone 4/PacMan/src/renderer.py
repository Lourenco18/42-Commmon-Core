import math
import logging
import pygame
from src.entities import GhostState
from src.highscore import HighscoreEntry
from src.level import Level

logger = logging.getLogger(__name__)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 0)
BLUE = (30, 60, 180)
WALL_COLOR = (20, 80, 200)
CORRIDOR_COLOR = (10, 10, 30)
PACGUM_COLOR = (220, 180, 100)
SUPER_PACGUM_COLOR = (255, 255, 180)
HUD_BG = (10, 10, 10)

GHOST_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (230, 40, 40),
    "pink": (255, 130, 180),
    "cyan": (0, 210, 210),
    "orange": (240, 140, 20),
    "edible": (30, 60, 200),
    "flashing": (200, 200, 255),
}

CELL_SIZE: int = 24
HUD_HEIGHT: int = 50


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen: pygame.Surface = screen
        self.cell_size: int = CELL_SIZE
        pygame.font.init()
        self.font_large: pygame.font.Font = pygame.font.SysFont(
            "monospace", 36, bold=True)
        self.font_med: pygame.font.Font = pygame.font.SysFont(
            "monospace", 24, bold=True)
        self.font_small: pygame.font.Font = pygame.font.SysFont(
            "monospace", 16)
        self._pacman_angle: float = 0.0
        self._mouth_open: float = 0.3
        self._mouth_dir: int = 1

    def draw_game(self, level: Level, tick: int) -> None:
        self.screen.fill(BLACK)
        self._animate_pacman(tick)
        self._draw_maze(level)
        self._draw_pacgums(level)
        self._draw_super_pacgums(level, tick)
        self._draw_ghosts(level, tick)
        self._draw_player(level)
        self._draw_hud(level)

    def draw_main_menu(self, selected: int,
                       highscores: list[HighscoreEntry]) -> None:
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
            "I  : Toggle Invincibility",
            "X  : Skip Level",
            "F  : Freeze/Unfreeze Ghosts",
            "L  : Add Extra Life",
            "B  : Toggle Speed Boost",
        ]
        for i, line in enumerate(lines):
            color = (200, 200, 100) if line.startswith("──") else WHITE
            self._draw_centered(line, self.font_small, color, y=110 + i * 26)
        self._draw_centered("Press ESC or ENTER to return",
                            self.font_small, (100, 100, 100), y=510)

    def draw_pause(self, level: Level) -> None:
        self.draw_game(level, 0)
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        self._draw_title("PAUSED", WHITE, y=180)
        self._draw_centered(
            "ENTER / P  → Resume",
            self.font_med,
            YELLOW,
            y=260)
        self._draw_centered(
            "ESC        → Main Menu",
            self.font_med,
            WHITE,
            y=304)

    def draw_name_entry(self, score: int, name_buf: str, prompt: str) -> None:
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
        self.screen.fill(BLACK)
        self._draw_title("GAME OVER", (230, 40, 40), y=160)
        self._draw_centered(f"Score: {score}", self.font_med, WHITE, y=250)

    def draw_victory(self, score: int) -> None:
        self.screen.fill(BLACK)
        self._draw_title("YOU WIN!", YELLOW, y=160)
        self._draw_centered("Congratulations!", self.font_med, WHITE, y=240)
        self._draw_centered(
            f"Final Score: {score}",
            self.font_med,
            YELLOW,
            y=280)

    def _animate_pacman(self, tick: int) -> None:
        speed = 0.08
        self._mouth_open += speed * self._mouth_dir
        if self._mouth_open > 0.55:
            self._mouth_dir = -1
        elif self._mouth_open < 0.05:
            self._mouth_dir = 1

    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        x = col * self.cell_size
        y = row * self.cell_size + HUD_HEIGHT
        return pygame.Rect(x, y, self.cell_size, self.cell_size)

    def _draw_maze(self, level: Level) -> None:
        maze = level.maze
        wall_thickness = 3

        for r in range(maze.height):
            for c in range(maze.width):
                rect = self._cell_rect(r, c)
                pygame.draw.rect(self.screen, CORRIDOR_COLOR, rect)

                cell = maze.grid[r][c]
                if cell & 1:  # N wall
                    pygame.draw.line(
                        self.screen, WALL_COLOR,
                        (rect.left, rect.top), (rect.right, rect.top),
                        wall_thickness)
                if cell & 2:  # E wall
                    pygame.draw.line(
                        self.screen, WALL_COLOR,
                        (rect.right, rect.top), (rect.right, rect.bottom),
                        wall_thickness)
                if cell & 4:  # S wall
                    pygame.draw.line(
                        self.screen, WALL_COLOR,
                        (rect.left, rect.bottom), (rect.right, rect.bottom),
                        wall_thickness)
                if cell & 8:  # W wall
                    pygame.draw.line(
                        self.screen, WALL_COLOR,
                        (rect.left, rect.top), (rect.left, rect.bottom),
                        wall_thickness)

    def _draw_pacgums(self, level: Level) -> None:
        r = self.cell_size // 8
        for pg in level.pacgums:
            if not pg.eaten:
                rect = self._cell_rect(pg.row, pg.col)
                cx = rect.centerx
                cy = rect.centery
                pygame.draw.circle(
                    self.screen, PACGUM_COLOR, (cx, cy), max(
                        2, r))

    def _draw_super_pacgums(self, level: Level, tick: int) -> None:
        base_r = self.cell_size // 4
        pulse = int(2 * math.sin(tick * 0.1))
        r = max(3, base_r + pulse)
        for spg in level.super_pacgums:
            if not spg.eaten:
                rect = self._cell_rect(spg.row, spg.col)
                pygame.draw.circle(self.screen, SUPER_PACGUM_COLOR,
                                   (rect.centerx, rect.centery), r)

    def _draw_ghosts(self, level: Level, tick: int) -> None:
        for ghost in level.ghosts:
            if ghost.state == GhostState.RESPAWNING:
                continue
            rect = self._cell_rect(ghost.row, ghost.col)
            cx, cy = rect.centerx, rect.centery
            r = self.cell_size // 2 - 2

            if ghost.state == GhostState.EDIBLE:
                # Flash when nearly worn off
                if ghost.edible_timer < 120 and (tick // 8) % 2 == 0:
                    color = GHOST_COLORS["flashing"]
                else:
                    color = GHOST_COLORS["edible"]
            else:
                color = GHOST_COLORS.get(ghost.color_name, WHITE)

            pygame.draw.circle(self.screen, color, (cx, cy - r // 4), r)
            pygame.draw.rect(self.screen, color,
                             (cx - r, cy - r // 4, r * 2, r + r // 4))

            eye_color = WHITE if ghost.state != GhostState.EDIBLE else (
                200, 50, 50)
            pygame.draw.circle(
                self.screen, eye_color, (cx - r // 3, cy - r // 3), r // 5)
            pygame.draw.circle(
                self.screen, eye_color, (cx + r // 3, cy - r // 3), r // 5)

    def _draw_player(self, level: Level) -> None:
        p = level.player
        rect = self._cell_rect(p.row, p.col)
        cx, cy = rect.centerx, rect.centery
        r = self.cell_size // 2 - 2
        dir_angles: dict[tuple[int, int], float] = {
            (-1, 0): 270.0,   # UP
            (1, 0): 90.0,     # DOWN
            (0, -1): 180.0,   # LEFT
            (0, 1): 0.0,      # RIGHT
        }
        angle = dir_angles.get(p.direction, 0.0)
        mouth_rad = self._mouth_open

        start_angle = math.radians(angle) + mouth_rad
        end_angle = math.radians(angle + 360) - mouth_rad
        color = YELLOW if not p.invincible else (180, 255, 180)

        points: list[tuple[float, float]] = [(float(cx), float(cy))]
        steps = 30
        for i in range(steps + 1):
            a = start_angle + (end_angle - start_angle) * i / steps
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a)
            points.append((px, py))
        if len(points) >= 3:
            pygame.draw.polygon(self.screen, color, points)

    def _draw_hud(self, level: Level) -> None:
        p = level.player
        w = self.screen.get_width()
        pygame.draw.rect(self.screen, HUD_BG, (0, 0, w, HUD_HEIGHT))
        pygame.draw.line(self.screen, WALL_COLOR,
                         (0, HUD_HEIGHT), (w, HUD_HEIGHT), 2)

        score_surf = self.font_med.render(f"Score: {p.score}", True, YELLOW)
        lives_surf = self.font_med.render(
            f"Lives: {p.lives}", True, (200, 80, 80))
        level_surf = self.font_small.render(
            f"Level {level.level_index + 1}", True, WHITE)
        time_val = max(0, int(level.time_remaining))
        time_color = (230, 60, 60) if time_val <= 15 else WHITE
        time_surf = self.font_med.render(
            f"Time: {time_val}s", True, time_color)

        self.screen.blit(score_surf, (10, 8))
        self.screen.blit(lives_surf, (w // 2 - 60, 8))
        self.screen.blit(time_surf, (w - 160, 8))
        self.screen.blit(level_surf, (w // 2 - 38, 30))

        cheats = []
        if p.invincible:
            cheats.append("INV")
        if p.speed_boost:
            cheats.append("SPD")
        if cheats:
            c_surf = self.font_small.render(
                " ".join(cheats), True, (100, 255, 100))
            self.screen.blit(c_surf, (10, 30))

    def _draw_title(self, text: str,
                    color: tuple[int, int, int], y: int) -> None:
        surf = self.font_large.render(text, True, color)
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))

    def _draw_centered(self, text: str, font: pygame.font.Font,
                       color: tuple[int, int, int], y: int) -> None:
        surf = font.render(text, True, color)
        x = self.screen.get_width() // 2 - surf.get_width() // 2
        self.screen.blit(surf, (x, y))

    @staticmethod
    def compute_window_size(
            maze_width: int, maze_height: int) -> tuple[int, int]:
        return (maze_width * CELL_SIZE, maze_height * CELL_SIZE + HUD_HEIGHT)
