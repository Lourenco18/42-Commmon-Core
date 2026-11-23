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
    """Identifica as telas e etapas possíveis do fluxo da partida."""
    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    NAME_ENTRY = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Game:
    """Coordena o ciclo do jogo, telas, comandos e progressão dos níveis."""
    MENU_ITEMS: int = 4

    def __init__(self, config: Config) -> None:
        """Inicializa Pygame, recordes, renderizador e estado inicial do menu.

        Args:
            config: Configurações validadas para esta partida.

        É chamado pelo ponto de entrada após carregar a configuração; a tela
        inicial que o jogador verá é o menu principal.
        """
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
        """Redimensiona a janela e atualiza a superfície usada para desenhar.

        Args:
            width: Nova largura em pixels.
            height: Nova altura em pixels.

        É chamada ao abrir um nível para acomodar seu labirinto.
        """
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.display.quit()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pac-Man")
        self.renderer.screen = self.screen

    def _set_menu_window(self) -> None:
        """Restaura o tamanho padrão das telas de menu.

        É chamada ao voltar ao menu ou ao terminar uma partida.
        """
        self._set_window_size(MENU_WIN_WIDTH, MENU_WIN_HEIGHT)

    def run(self) -> None:
        """Executa continuamente entrada, atualização e desenho da tela.

        É iniciada por ``main`` e mantém o jogo ativo até ``_quit`` encerrar
        o processo.
        """
        logger.info("Game started")
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
            self.tick += 1

    def _handle_events(self) -> None:
        """Lê eventos de janela e teclado e os encaminha aos tratadores.

        É chamada em cada iteração do loop, antes da atualização do jogo.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                self._on_key(event.key, event.unicode, event.mod)

    def _on_key(self, key: int, unicode: str, mod: int = 0) -> None:
        """Encaminha uma tecla conforme a tela ou etapa atual da partida.

        Args:
            key: Código da tecla reconhecido pelo Pygame.
            unicode: Caractere produzido pela tecla.
            mod: Modificadores ativos, como Shift.

        É chamada para cada tecla pressionada e direciona o comando ao menu,
        jogo, pausa ou entrada de nome.
        """
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
        """Move a seleção do menu ou abre a opção escolhida.

        Args:
            key: Código da tecla pressionada.

        É chamada por ``_on_key`` enquanto o menu principal está visível.
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

    def _key_playing(self, key: int, mod: int = 0) -> None:
        """Aplica comandos de movimento, pausa e trapaça durante o jogo.

        Args:
            key: Código da tecla pressionada.
            mod: Modificadores ativos, usado para reconhecer Shift+C.

        É chamada por ``_on_key`` no estado PLAYING; movimento é enfileirado
        no jogador e outros comandos alteram o nível.
        """
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
        """Retoma a partida ou abandona-a e retorna ao menu.

        Args:
            key: Código da tecla pressionada.

        É chamada por ``_on_key`` quando a tela de pausa está ativa.
        """
        if key in (pygame.K_RETURN, pygame.K_p):
            self.state = GameState.PLAYING
        elif key == pygame.K_ESCAPE:
            self.level = None
            self._set_menu_window()
            self.state = GameState.MAIN_MENU

    def _key_name_entry(self, key: int, unicode: str) -> None:
        """Edita o nome digitado ou salva a pontuação final confirmada.

        Args:
            key: Código da tecla pressionada.
            unicode: Caractere produzido para acrescentar ao nome.

        É chamada depois de vitória ou derrota quando o jogador informa
        o nome para a tabela de recordes.
        """
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
        """Atualiza o nível ativo ou avança o temporizador das telas finais.

        Args:
            dt: Tempo transcorrido desde o quadro anterior, em segundos.

        É chamada a cada iteração do loop; encaminha vitórias e derrotas do
        nível para suas transições de estado.
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
        """Carrega o próximo nível ou inicia a sequência de vitória final.

        É chamada quando ``Level`` sinaliza que todas as Pacgums foram comidas;
        vidas e pontuação são preservadas entre níveis.
        """
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
        """Registra o resultado e inicia a tela de derrota.

        É chamada quando acabam as vidas ou o tempo do nível.
        """
        assert self.level is not None
        self.final_score = self.level.player.score
        self._victory = False
        logger.info("Game over. Final score: %d", self.final_score)
        self._set_menu_window()
        self.state = GameState.GAME_OVER
        self._end_timer = FPS * 3
        self.level = None

    def _draw(self) -> None:
        """Escolhe a tela adequada ao estado atual e solicita seu desenho.

        É chamada em todos os quadros depois de processar eventos e atualizar
        a partida.
        """
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
        """Reinicia pontuação e progressão e prepara o primeiro nível.

        É chamada quando o jogador escolhe iniciar uma nova partida no menu.
        """
        self.level_index = 0
        self._load_level(0, self.config.lives, 0, seed=self.config.seed)

    def _load_level(self, index: int, lives: int, score: int,
                    seed: Optional[int]) -> None:
        """Cria o nível solicitado e ajusta a janela ao tamanho do labirinto.

        Args:
            index: Índice do nível, começando em zero.
            lives: Vidas que o jogador manterá.
            score: Pontuação que o jogador manterá.
            seed: Semente opcional para geração reproduzível.

        É chamada ao iniciar a partida e após vencer um nível; em caso de
        falha na geração, retorna ao menu principal.
        """
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
        """Salva os recordes e encerra os recursos do Pygame.

        É acionada pela opção Sair do menu ou pelo fechamento da janela.
        """
        self.highscores.save()
        pygame.quit()
        sys.exit(0)
