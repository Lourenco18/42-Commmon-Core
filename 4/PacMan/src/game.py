"""Main game controller for Pac-Man.

State machine that manages transitions between menus, gameplay,
pause, name entry, and end screens.
"""

import logging
import sys
from enum import Enum, auto
from typing import Optional

import pygame

from src.config import Config
from src.entities import DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT
from src.highscore import HighscoreSystem
from src.level import Level
from src.renderer import Renderer, CELL_SIZE, HUD_HEIGHT

logger = logging.getLogger(__name__)

FPS: int = 60
MIN_WIN_WIDTH: int = 500
MIN_WIN_HEIGHT: int = 560


class GameState(Enum):
    """All possible game states.

    Attributes:
        MAIN_MENU: Main menu screen.
        PLAYING: Active gameplay.
        PAUSED: Game paused.
        HIGHSCORES: Highscore table screen.
        INSTRUCTIONS: Instructions/controls screen.
        NAME_ENTRY: Player enters name after game ends.
        GAME_OVER: Brief game-over display.
        VICTORY: Brief victory display.
    """

    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    NAME_ENTRY = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    """Top-level game loop and state machine.

    Attributes:
        config: Loaded game configuration.
        highscores: Persistent highscore system.
        state: Current GameState.
        level: Active Level (None when in menus).
        level_index: Current 0-based level number.
        screen: Pygame display surface.
        renderer: Rendering subsystem.
        clock: Pygame clock for FPS capping.
        menu_selection: Highlighted menu item index.
        name_buffer: Text typed during name entry.
        final_score: Score captured when game ended.
        tick: Frame counter for animations.
    """

    MENU_ITEMS: int = 4

    def __init__(self, config: Config) -> None:
        """Initialize the game.

        Args:
            config: Validated game configuration.
        """
        self.config: Config = config
        self.highscores: HighscoreSystem = HighscoreSystem(config.highscore_filename)

        pygame.init()
        # Start with a minimum-size window; resized when a level loads
        self.screen: pygame.Surface = pygame.display.set_mode(
            (MIN_WIN_WIDTH, MIN_WIN_HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption("Pac-Man")
        self.clock: pygame.Clock = pygame.time.Clock()
        self.renderer: Renderer = Renderer(self.screen)

        self.state: GameState = GameState.MAIN_MENU
        self.level: Optional[Level] = None
        self.level_index: int = 0
        self.menu_selection: int = 0
        self.name_buffer: str = ""
        self.final_score: int = 0
        self.tick: int = 0
        self._end_timer: int = 0   # brief delay before name entry prompt

    # ── Public entry point ──────────────────────────────────────────────────

    def run(self) -> None:
        """Start and run the main game loop until exit."""
        logger.info("Game started")
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
            self.tick += 1

    # ── Event handling ──────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        """Process all pending pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                self._on_key(event.key, event.unicode)

    def _on_key(self, key: int, unicode: str) -> None:
        """Dispatch a key press to the appropriate state handler.

        Args:
            key: pygame key constant.
            unicode: Unicode character string.
        """
        if self.state == GameState.MAIN_MENU:
            self._key_menu(key)
        elif self.state == GameState.PLAYING:
            self._key_playing(key)
        elif self.state == GameState.PAUSED:
            self._key_paused(key)
        elif self.state == GameState.HIGHSCORES:
            if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.state = GameState.MAIN_MENU
        elif self.state == GameState.INSTRUCTIONS:
            if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.state = GameState.MAIN_MENU
        elif self.state == GameState.NAME_ENTRY:
            self._key_name_entry(key, unicode)
        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            pass  # handled by timer

    def _key_menu(self, key: int) -> None:
        """Handle key in main menu.

        Args:
            key: pygame key constant.
        """
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_selection = (self.menu_selection - 1) % self.MENU_ITEMS
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_selection = (self.menu_selection + 1) % self.MENU_ITEMS
        elif key == pygame.K_RETURN:
            if self.menu_selection == 0:
                self._start_game()
            elif self.menu_selection == 1:
                self.state = GameState.HIGHSCORES
            elif self.menu_selection == 2:
                self.state = GameState.INSTRUCTIONS
            elif self.menu_selection == 3:
                self._quit()

    def _key_playing(self, key: int) -> None:
        """Handle key during gameplay (movement + cheats + pause).

        Args:
            key: pygame key constant.
        """
        if self.level is None:
            return

        # Movement
        if key in (pygame.K_UP, pygame.K_w):
            self.level.player.set_direction(DIR_UP)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.level.player.set_direction(DIR_DOWN)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.level.player.set_direction(DIR_LEFT)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.level.player.set_direction(DIR_RIGHT)

        # Pause
        elif key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = GameState.PAUSED

        # Cheat mode
        elif key == pygame.K_i:
            self.level.toggle_invincibility()
        elif key == pygame.K_f:
            self.level.toggle_ghost_freeze()
        elif key == pygame.K_l:
            self.level.add_extra_life()
        elif key == pygame.K_b:
            self.level.toggle_speed_boost()
        elif key == pygame.K_x:
            self.level.skip_level()

    def _key_paused(self, key: int) -> None:
        """Handle key while paused.

        Args:
            key: pygame key constant.
        """
        if key in (pygame.K_RETURN, pygame.K_p):
            self.state = GameState.PLAYING
        elif key == pygame.K_ESCAPE:
            self.level = None
            self.state = GameState.MAIN_MENU

    def _key_name_entry(self, key: int, unicode: str) -> None:
        """Handle key during name entry.

        Args:
            key: pygame key constant.
            unicode: Typed character.
        """
        if key == pygame.K_RETURN:
            name = self.name_buffer.strip() or "Player"
            self.highscores.add(name, self.final_score)
            self.highscores.save()
            self.name_buffer = ""
            self.state = GameState.MAIN_MENU
        elif key == pygame.K_BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
        else:
            if len(self.name_buffer) < 10 and (unicode.isalnum() or unicode == " "):
                self.name_buffer += unicode

    # ── Update ──────────────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        """Advance game logic by dt seconds.

        Args:
            dt: Delta time in seconds.
        """
        if self.state == GameState.PLAYING and self.level is not None:
            self.level.update(dt)
            if self.level.level_won:
                self._on_level_won()
            elif self.level.level_lost:
                self._on_level_lost()

        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            self._end_timer -= 1
            if self._end_timer <= 0:
                self.state = GameState.NAME_ENTRY

    def _on_level_won(self) -> None:
        """Handle completion of a level."""
        assert self.level is not None
        lives = self.level.player.lives
        score = self.level.player.score
        self.level_index += 1

        if self.level_index >= len(self.config.levels):
            logger.info("All levels completed! Final score: %d", score)
            self.final_score = score
            self.state = GameState.VICTORY
            self._end_timer = FPS * 2
            self.level = None
        else:
            logger.info("Loading level %d", self.level_index + 1)
            self._load_level(self.level_index, lives, score, seed=None)

    def _on_level_lost(self) -> None:
        """Handle game over condition."""
        assert self.level is not None
        self.final_score = self.level.player.score
        logger.info("Game over. Final score: %d", self.final_score)
        self.state = GameState.GAME_OVER
        self._end_timer = FPS * 2
        self.level = None

    # ── Draw ────────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        """Render the current state to the screen."""
        if self.state == GameState.MAIN_MENU:
            self.renderer.draw_main_menu(self.menu_selection, self.highscores.get_top(3))
        elif self.state == GameState.PLAYING and self.level is not None:
            self.renderer.draw_game(self.level, self.tick)
        elif self.state == GameState.PAUSED and self.level is not None:
            self.renderer.draw_pause(self.level)
        elif self.state == GameState.HIGHSCORES:
            self.renderer.draw_highscores(self.highscores.get_top())
        elif self.state == GameState.INSTRUCTIONS:
            self.renderer.draw_instructions()
        elif self.state == GameState.NAME_ENTRY:
            prompt = "VICTORY!" if self.final_score > 0 else "GAME OVER"
            self.renderer.draw_name_entry(self.final_score, self.name_buffer, prompt)
        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_game_over(self.final_score)
        elif self.state == GameState.VICTORY:
            self.renderer.draw_victory(self.final_score)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _start_game(self) -> None:
        """Start a new game from level 1."""
        self.level_index = 0
        self._load_level(0, self.config.lives, 0, seed=self.config.seed)

    def _load_level(self, index: int, lives: int, score: int,
                    seed: Optional[int]) -> None:
        """Load and start a level.

        Args:
            index: 0-based level index.
            lives: Player's current lives.
            score: Player's current score.
            seed: Maze seed (None = random).
        """
        try:
            self.level = Level(self.config, index, lives, score, seed=seed)
        except RuntimeError as exc:
            logger.error("Failed to load level %d: %s", index + 1, exc)
            self.state = GameState.MAIN_MENU
            return

        # Resize window to fit maze
        spec = self.config.levels[min(index, len(self.config.levels) - 1)]
        w, h = Renderer.compute_window_size(spec["width"], spec["height"])
        w = max(w, MIN_WIN_WIDTH)
        h = max(h, MIN_WIN_HEIGHT)
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.renderer.screen = self.screen
        self.state = GameState.PLAYING
        logger.info("Level %d loaded (seed=%s)", index + 1, seed)

    def _quit(self) -> None:
        """Save highscores and exit cleanly."""
        self.highscores.save()
        pygame.quit()
        sys.exit(0)
