import logging
import os
import sys
from enum import Enum, auto
from typing import Optional

import pygame

from src.config import Config
from src.entities import DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT
from src.highscore import HighscoreSystem
from src.level import Level
from src.renderer import Renderer

logger = logging.getLogger(__name__)

FPS: int = 60
MENU_WIN_WIDTH: int = 500
MENU_WIN_HEIGHT: int = 560
MIN_WIN_WIDTH: int = 200
MIN_WIN_HEIGHT: int = 200


class GameState(Enum):
    """Represent the screens and modes in the game state machine."""
    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    NAME_ENTRY = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    """Coordinate the game loop, state transitions, and user input."""
    MENU_ITEMS: int = 4

    def __init__(self, config: Config) -> None:
        """Initialize a Game instance.

        Args:
            config: Validated game settings."""
        self.config: Config = config
        self.highscores: HighscoreSystem = HighscoreSystem(
            config.highscore_filename)
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode(
            (MENU_WIN_WIDTH, MENU_WIN_HEIGHT)
        )
        pygame.display.set_caption("Pac-Man")
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.renderer: Renderer = Renderer(self.screen)

        self.state: GameState = GameState.MAIN_MENU
        self.level: Optional[Level] = None
        self.level_index: int = 0
        self.menu_selection: int = 0
        self.name_buffer: str = ""
        self.final_score: int = 0
        self._victory: bool = False
        self.tick: int = 0
        self._end_timer: int = 0

    def _set_window_size(self, width: int, height: int) -> None:
        """Resize the game window and update the renderer surface.

        Args:
            width: New window width in pixels.
            height: New window height in pixels."""
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.display.quit()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pac-Man")
        self.renderer.screen = self.screen

    def _set_menu_window(self) -> None:
        """Restore the standard menu window dimensions."""
        self._set_window_size(MENU_WIN_WIDTH, MENU_WIN_HEIGHT)

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

    def _handle_events(self) -> None:
        """Read and dispatch pending Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                self._on_key(event.key, event.unicode, event.mod)

    def _on_key(self, key: int, unicode: str, mod: int = 0) -> None:
        """Route a key press to the handler for the current game state.

        Args:
            key: Pygame key code.
            unicode: Character produced by the key press.
            mod: Active Pygame modifier flags."""
        if self.state == GameState.MAIN_MENU:
            self._key_menu(key)
        elif self.state == GameState.PLAYING:
            self._key_playing(key, mod)
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
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = GameState.NAME_ENTRY

    def _key_menu(self, key: int) -> None:
        """Handle menu navigation and selection.

        Args:
            key: Name of the setting or value to inspect."""
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

    def _key_playing(self, key: int, mod: int = 0) -> None:
        """Handle movement, pause, and cheat keys during play.

        Args:
            key: Name of the setting or value to inspect.
            mod: Active Pygame modifier flags."""
        if self.level is None:
            return
        if key in (pygame.K_UP, pygame.K_w):
            self.level.player.set_direction(DIR_UP)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.level.player.set_direction(DIR_DOWN)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.level.player.set_direction(DIR_LEFT)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.level.player.set_direction(DIR_RIGHT)
        elif key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = GameState.PAUSED
        elif key == pygame.K_c and (mod & pygame.KMOD_SHIFT):
            self.level.toggle_cheat_mode()
        elif self.level.cheat_mode:
            if key == pygame.K_i:
                self.level.toggle_invincibility()
            elif key == pygame.K_f:
                self.level.toggle_ghost_freeze()
            elif key == pygame.K_l:
                self.level.add_extra_life()
            elif key == pygame.K_r:
                self.level.remove_life()
            elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.level.add_time()
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.level.remove_time()
            elif key == pygame.K_t:
                self.level.toggle_time_freeze()
            elif key == pygame.K_b:
                self.level.toggle_speed_boost()
            elif key == pygame.K_x:
                self.level.skip_level()

    def _key_paused(self, key: int) -> None:
        """Handle resume and return-to-menu keys while paused.

        Args:
            key: Name of the setting or value to inspect."""
        if key in (pygame.K_RETURN, pygame.K_p):
            self.state = GameState.PLAYING
        elif key == pygame.K_ESCAPE:
            self.level = None
            self._set_menu_window()
            self.state = GameState.MAIN_MENU

    def _key_name_entry(self, key: int, unicode: str) -> None:
        """Update the name entry or save the final score.

        Args:
            key: Name of the setting or value to inspect.
            unicode: Character produced by the key press."""
        if key == pygame.K_RETURN:
            name = self.name_buffer.strip() or "Player"
            self.highscores.add(name, self.final_score)
            self.highscores.save()
            self.name_buffer = ""
            self._set_menu_window()
            self.state = GameState.MAIN_MENU
        elif key == pygame.K_BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
        else:
            if (
                len(self.name_buffer) < 10
                and unicode.isascii()
                and (unicode.isalnum() or unicode == " ")
            ):
                self.name_buffer += unicode

    def _update(self, dt: float) -> None:
        """Advance gameplay or end-screen state by the elapsed time.

        Args:
            dt: Elapsed time in seconds."""
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
        """Advance to the next level or finish the game in victory."""
        assert self.level is not None
        lives = self.level.player.lives
        score = self.level.player.score
        cheat_active = self.level.cheat_mode
        self.level_index += 1

        if self.level_index >= len(self.config.levels):
            logger.info("All levels completed! Final score: %d", score)
            self.final_score = score
            self._victory = True
            self._set_menu_window()
            self.state = GameState.VICTORY
            self._end_timer = FPS * 3
            self.level = None
        else:
            logger.info("Loading level %d", self.level_index + 1)
            self._load_level(self.level_index, lives, score, seed=None)
            if self.level is not None:
                self.level.cheat_mode = cheat_active

    def _on_level_lost(self) -> None:
        """Finish the game after a level is lost."""
        assert self.level is not None
        self.final_score = self.level.player.score
        self._victory = False
        logger.info("Game over. Final score: %d", self.final_score)
        self._set_menu_window()
        self.state = GameState.GAME_OVER
        self._end_timer = FPS * 3
        self.level = None

    def _draw(self) -> None:
        """Draw the screen for the current game state."""
        if self.state == GameState.MAIN_MENU:
            self.renderer.draw_main_menu(
                self.menu_selection, self.highscores.get_top(3))
        elif self.state == GameState.PLAYING and self.level is not None:
            self.renderer.draw_game(self.level, self.tick)
        elif self.state == GameState.PAUSED and self.level is not None:
            self.renderer.draw_pause(self.level)
        elif self.state == GameState.HIGHSCORES:
            self.renderer.draw_highscores(self.highscores.get_top())
        elif self.state == GameState.INSTRUCTIONS:
            self.renderer.draw_instructions()
        elif self.state == GameState.NAME_ENTRY:
            prompt = "VICTORY!" if self._victory else "GAME OVER"
            self.renderer.draw_name_entry(
                self.final_score, self.name_buffer, prompt)
        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_game_over(self.final_score)
        elif self.state == GameState.VICTORY:
            self.renderer.draw_victory(self.final_score)

    def _start_game(self) -> None:
        """Reset progression and load the first level."""
        self.level_index = 0
        self._load_level(0, self.config.lives, 0, seed=self.config.seed)

    def _load_level(self, index: int, lives: int, score: int,
                    seed: Optional[int]) -> None:
        """Create a level and size the window for its maze.

        Args:
            index: Index of the requested item.
            lives: Number of player lives.
            score: Non-negative score value.
            seed: Optional seed for reproducible generation."""
        try:
            self.level = Level(self.config, index, lives, score, seed=seed)
        except RuntimeError as exc:
            logger.error("Failed to load level %d: %s", index + 1, exc)
            self._set_menu_window()
            self.state = GameState.MAIN_MENU
            return
        spec = self.config.levels[min(index, len(self.config.levels) - 1)]
        w, h = Renderer.compute_window_size(spec["width"], spec["height"])
        w = max(w, MIN_WIN_WIDTH)
        h = max(h, MIN_WIN_HEIGHT)
        self._set_window_size(w, h)
        self.state = GameState.PLAYING
        logger.info("Level %d loaded (seed=%s)", index + 1, seed)

    def _quit(self) -> None:
        """Save highscores and close Pygame cleanly."""
        self.highscores.save()
        pygame.quit()
        sys.exit(0)
