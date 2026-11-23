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

ALL_DIRECTIONS: tuple[tuple[int, int], ...] = (
    DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT
)

DIR_TO_BIT: dict[tuple[int, int], int] = {
    DIR_UP: NORTH, DIR_DOWN: SOUTH, DIR_LEFT: WEST, DIR_RIGHT: EAST,
}


class GhostState(Enum):
    """Represent the ghost behavior states."""
    CHASING = auto()
    EDIBLE = auto()
    RESPAWNING = auto()


class Entity:
    """Base para personagens que se movem pela grade do labirinto."""

    def __init__(self, row: int, col: int) -> None:
        """Prepara posição e temporizadores comuns de movimento.

        Args:
            row: Linha inicial no labirinto.
            col: Coluna inicial no labirinto.

        É chamado ao criar Pac-Man ou um fantasma para definir sua posição.
        """
        self.row: int = row
        self.col: int = col
        self.prev_row: int = row
        self.prev_col: int = col
        self.direction: tuple[int, int] = DIR_LEFT
        self.move_interval: int = 1
        self.move_timer: int = 0

    def can_move(self, maze: Maze, direction: tuple[int, int]) -> bool:
        """Verifica se o próximo passo na direção escolhida está livre.

        Args:
            maze: Labirinto que contém o personagem.
            direction: Deslocamento (linha, coluna) do movimento.

        Returns:
            ``True`` se não há parede e a célula seguinte está dentro da grade.

        É consultada antes de Pac-Man ou fantasma avançar uma célula.
        """
        bit = DIR_TO_BIT.get(direction, 0)
        if bit == 0 or maze.is_wall(self.row, self.col, bit):
            return False
        nr = self.row + direction[0]
        nc = self.col + direction[1]
        return maze.passable(nr, nc)

    def available_moves(self, maze: Maze) -> list[tuple[int, int]]:
        """Obtém as células adjacentes para as quais o personagem pode ir.

        Args:
            maze: Labirinto onde o personagem está se movendo.

        Returns:
            Lista de coordenadas (linha, coluna) acessíveis.

        É usada pela inteligência dos fantasmas para escolher a próxima rota.
        """
        moves: list[tuple[int, int]] = []
        for dr, dc in ALL_DIRECTIONS:
            if self.can_move(maze, (dr, dc)):
                moves.append((self.row + dr, self.col + dc))
        return moves

    def visual_pos(self) -> tuple[float, float]:
        """Calcula a posição intermediária entre duas células para desenhar.

        Returns:
            Coordenadas fracionárias entre a posição anterior e a atual.

        O renderizador usa esse valor para animar movimentos sem saltos.
        """
        t = min(1.0, self.move_timer / max(1, self.move_interval))
        v_row = self.prev_row + (self.row - self.prev_row) * t
        v_col = self.prev_col + (self.col - self.prev_col) * t
        return (v_row, v_col)


class Player(Entity):
    """Controla posição, direção, pontuação, vidas e poderes de Pac-Man."""
    BASE_INTERVAL: int = 16
    FAST_INTERVAL: int = 11
    RESPAWN_IMMUNITY_DURATION: int = 180

    def __init__(self, row: int, col: int, lives: int) -> None:
        """Cria Pac-Man no ponto inicial e configura seu estado da partida.

        Args:
            row: Linha inicial no labirinto.
            col: Coluna inicial no labirinto.
            lives: Vidas disponíveis ao começar o nível.

        É chamado pela criação de ``Level`` após a geração do labirinto.
        """
        super().__init__(row, col)
        self.start_row: int = row
        self.start_col: int = col
        self.next_direction: tuple[int, int] = DIR_LEFT
        self.lives: int = lives
        self.score: int = 0
        self.invincible: bool = False
        self.respawn_immunity_timer: int = 0
        self.speed_boost: bool = False
        self.move_interval = self.BASE_INTERVAL
        self.move_timer = self.move_interval - 1

    @property
    def is_immune(self) -> bool:
        """Indica se Pac-Man está protegido contra colisões fatais.

        Returns:
            ``True`` durante invencibilidade ou imunidade após reaparecer.

        É consultada quando o nível resolve contato com um fantasma.
        """
        return self.invincible or self.respawn_immunity_timer > 0

    def respawn(self) -> None:
        """Recoloca Pac-Man no início e concede alguns instantes de proteção.

        É chamada depois que um fantasma o atinge e ainda restam vidas.
        """
        self.row = self.start_row
        self.col = self.start_col
        self.prev_row = self.start_row
        self.prev_col = self.start_col
        self.direction = DIR_LEFT
        self.next_direction = DIR_LEFT
        self.move_timer = self.move_interval - 1
        self.respawn_immunity_timer = self.RESPAWN_IMMUNITY_DURATION

    def set_direction(self, direction: tuple[int, int]) -> None:
        """Guarda a direção pressionada para a próxima oportunidade de andar.

        Args:
            direction: Deslocamento (linha, coluna) escolhido pelo jogador.

        É chamada pelo tratamento dos controles; o movimento ocorre em
        ``update`` assim que o passo atual termina e o corredor permite.
        """
        self.next_direction = direction

    def update(self, maze: Maze) -> None:
        """Atualiza proteção, velocidade e movimento de Pac-Man em um passo.

        Args:
            maze: Labirinto usado para impedir que atravesse paredes.

        É chamada a cada quadro durante o jogo; tenta primeiro a direção
        pressionada e, se bloqueada, continua na direção atual.
        """
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
            if self.can_move(maze, direction):
                self.row += direction[0]
                self.col += direction[1]
                self.direction = direction
                self.move_timer = 0
                return

        self.move_timer = self.move_interval - 1


class Ghost(Entity):
    """Controla movimento, perseguição, vulnerabilidade e retorno do fantasma."""
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
        """Cria um fantasma e configura seus tempos e canto de origem.

        Args:
            row: Linha inicial no labirinto.
            col: Coluna inicial no labirinto.
            corner_row: Linha do canto para o qual retorna.
            corner_col: Coluna do canto para o qual retorna.
            color_name: Cor que define a identidade e estratégia.
            normal_interval: Quadros entre passos enquanto persegue.
            edible_interval: Quadros entre passos enquanto está vulnerável.
            respawn_delay: Espera antes de voltar à perseguição.
            edible_duration: Duração da vulnerabilidade.
            eyes_interval: Ritmo de movimento durante o retorno.
            eyes_wander_duration: Duração da exploração junto ao canto.
            eyes_wander_radius: Distância máxima dessa exploração.
            eyes_wander_interval: Ritmo de movimento durante a exploração.

        É chamado ao montar cada nível para criar seus quatro fantasmas.
        """
        super().__init__(row, col)
        self.ai_prev_row: int = row
        self.ai_prev_col: int = col
        self.corner_row: int = corner_row
        self.corner_col: int = corner_col
        self.color_name: str = color_name
        self.state: GhostState = GhostState.CHASING
        self.frozen: bool = False
        self.edible_timer: int = 0
        self.respawn_timer: int = 0
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
        self.move_interval = self.normal_interval

    def _set_interval(self, new_interval: int) -> None:
        """Altera o ritmo do fantasma sem reiniciar o passo em andamento.

        Args:
            new_interval: Quadros desejados entre movimentos.

        É usado ao entrar ou sair do estado vulnerável e durante o retorno.
        """
        if new_interval != self.move_interval:
            ratio = self.move_timer / max(1, self.move_interval)
            self.move_interval = new_interval
            self.move_timer = round(ratio * self.move_interval)

    def make_edible(self) -> None:
        """Torna o fantasma vulnerável e reinicia a duração desse estado.

        É chamado quando Pac-Man coleta uma Super Pacgum, exceto para
        fantasmas que já estão retornando ao ponto de origem.
        """
        if self.state != GhostState.RESPAWNING:
            self.state = GhostState.EDIBLE
            self.edible_timer = self.edible_duration
            self._set_interval(self.edible_interval)
            self.ai_prev_row, self.ai_prev_col = self.row, self.col

    def eat(self, maze: Maze) -> None:
        """Inicia o retorno do fantasma ao canto depois que Pac-Man o come.

        Args:
            maze: Labirinto usado para calcular o caminho de retorno.

        É chamado na colisão entre Pac-Man e um fantasma vulnerável.
        """
        self.state = GhostState.RESPAWNING
        self.respawn_timer = self.respawn_delay
        self.edible_timer = 0
        self.eyes_path = self._path_to_corner(maze)
        self.eyes_phase = "go"
        self.eyes_wander_timer = 0
        self._set_interval(self.eyes_interval)

    def _path_to_corner(self, maze: Maze) -> list[tuple[int, int]]:
        """Calcula um caminho de células até o canto de origem do fantasma.

        Args:
            maze: Labirinto onde a rota será procurada.

        Returns:
            Células ordenadas do próximo passo até o canto, ou lista vazia.

        É usada ao comer o fantasma e ao terminar sua breve exploração.
        """
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
        """Reativa a perseguição e reinicia posição e temporizador do fantasma.

        É chamado ao terminar o retorno e a exploração junto ao canto.
        """
        self.state = GhostState.CHASING
        self.eyes_path = []
        self.eyes_phase = ""
        self.eyes_wander_timer = 0
        self.prev_row, self.prev_col = self.row, self.col
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self._set_interval(self.normal_interval)
        self.move_timer = 0

    def _step_along_path(self) -> None:
        """Avança o fantasma-olhos para a próxima célula do caminho calculado.

        É chamado durante as fases de ida e volta ao canto de origem.
        """
        next_row, next_col = self.eyes_path.pop(0)
        self.direction = (next_row - self.row, next_col - self.col)
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self.row, self.col = next_row, next_col

    def _wander_step(self, maze: Maze) -> None:
        """Move os olhos do fantasma por corredores próximos ao seu canto.

        Args:
            maze: Labirinto que limita os passos possíveis.

        É chamado temporariamente depois que os olhos alcançam o canto.
        """
        near = [
            pos
            for pos in self.available_moves(maze)
            if math.hypot(
                pos[0] - self.corner_row,
                pos[1] - self.corner_col,
            ) <= self.eyes_wander_radius
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
        """Avança as fases de retorno, passeio local e reaparecimento.

        Args:
            maze: Labirinto usado para seguir ou recalcular a rota.

        É chamado em cada movimento enquanto o fantasma está no estado
        ``RESPAWNING``.
        """
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
        """Marca o fantasma como congelado para interromper seu movimento.

        É acionado pelo comando de congelamento no modo de trapaça.
        """
        self.frozen = True

    def unfreeze(self) -> None:
        """Libera o fantasma para voltar a se mover.

        É acionado ao desativar o congelamento ou sair do modo de trapaça.
        """
        self.frozen = False

    def update(
        self,
        maze: Maze,
        player_row: int,
        player_col: int,
        player_dir: tuple[int, int] = DIR_LEFT,
        blinky_pos: Optional[tuple[int, int]] = None,
    ) -> None:
        """Atualiza temporizadores e executa o próximo movimento do fantasma.

        Args:
            maze: Labirinto usado para movimentação.
            player_row: Linha atual de Pac-Man.
            player_col: Coluna atual de Pac-Man.
            player_dir: Direção atual de Pac-Man.
            blinky_pos: Posição do fantasma vermelho, se disponível.

        É chamada a cada atualização do nível; trata congelamento,
        vulnerabilidade e retorno antes da perseguição normal.
        """
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
        """Define o alvo estratégico da perseguição conforme a cor do fantasma.

        Args:
            player_row: Linha de Pac-Man.
            player_col: Coluna de Pac-Man.
            player_dir: Direção em que Pac-Man está andando.
            blinky_pos: Posição do fantasma vermelho, se disponível.

        Returns:
            Célula-alvo usada para escolher o próximo corredor.

        É consultada por ``_move`` quando o fantasma está perseguindo.
        """
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
        """Escolhe e executa o próximo passo conforme o estado do fantasma.

        Args:
            maze: Labirinto usado para obter corredores acessíveis.
            player_row: Linha de Pac-Man.
            player_col: Coluna de Pac-Man.
            player_dir: Direção atual de Pac-Man.
            blinky_pos: Posição do fantasma vermelho, se disponível.

        É chamada por ``update`` quando o temporizador permite movimento:
        fantasmas perseguidores aproximam-se de seu alvo e os vulneráveis
        tentam se afastar de Pac-Man.
        """
        self.prev_row, self.prev_col = self.row, self.col
        neighbours = self.available_moves(maze)
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
                """Mede a distância de um corredor ao alvo da perseguição."""
                return math.hypot(pos[0] - target_r, pos[1] - target_c)
        else:
            def key(pos: tuple[int, int]) -> float:
                """Prioriza corredores afastados de Pac-Man com variação aleatória."""
                return (
                    -math.hypot(pos[0] - player_row, pos[1] - player_col)
                    + random.uniform(0, 1.5)
                )

        next_row, next_col = min(candidates, key=key)
        self.direction = (next_row - self.row, next_col - self.col)
        self.ai_prev_row, self.ai_prev_col = self.row, self.col
        self.row, self.col = next_row, next_col


class Collectible:
    """Representa um item coletável e seu estado de consumo no labirinto."""
    def __init__(self, row: int, col: int) -> None:
        """Registra a posição do item e marca-o como ainda não coletado.

        Args:
            row: Linha da célula que contém o item.
            col: Coluna da célula que contém o item.

        É usado ao posicionar itens na preparação de cada nível.
        """
        self.row: int = row
        self.col: int = col
        self.eaten: bool = False


class Pacgum(Collectible):
    """Represent a regular collectible in the maze."""
    def __init__(self, row: int, col: int) -> None:
        """Cria uma Pacgum comum, que concede pontos ao ser coletada.

        Args:
            row: Linha da célula do item.
            col: Coluna da célula do item.

        É chamada ao distribuir as Pacgums pelos corredores alcançáveis.
        """
        super().__init__(row, col)


class SuperPacgum(Collectible):
    """Represent a power pellet in the maze."""
    def __init__(self, row: int, col: int) -> None:
        """Cria uma Super Pacgum, que também torna os fantasmas vulneráveis.

        Args:
            row: Linha da célula do item.
            col: Coluna da célula do item.

        É chamada ao colocar itens de poder nos cantos do labirinto.
        """
        super().__init__(row, col)
