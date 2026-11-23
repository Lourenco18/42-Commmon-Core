import logging
import random
from typing import Optional

from src.config import Config, INT_CLAMPS
from src.entities import Ghost, GhostState, Pacgum, Player, SuperPacgum
from src.maze import Maze, generate_maze

logger = logging.getLogger(__name__)
GHOST_COLORS: list[str] = ["red", "pink", "cyan", "orange"]


class Level:
    """Coordena o labirinto, personagens, itens, cronômetro e resultado de um nível."""
    def __init__(self, config: Config, level_index: int, player_lives: int,
                 player_score: int, seed: Optional[int] = None) -> None:
        """Monta o labirinto e prepara todos os elementos de um nível.

        Args:
            config: Configurações validadas da partida.
            level_index: Índice do nível, começando em zero.
            player_lives: Vidas preservadas do nível anterior.
            player_score: Pontuação preservada do nível anterior.
            seed: Semente opcional para repetir a geração.

        É chamado por ``Game`` no início da partida ou ao avançar de nível.
        """
        self.config = config
        self.level_index = level_index
        spec = config.levels[min(level_index, len(config.levels) - 1)]
        self.width = spec["width"]
        self.height = spec["height"]
        self.time_remaining: float = self._compute_level_time()
        self.time_frozen: bool = False
        self.cheat_mode: bool = False
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

        spawn_row, spawn_col = self._find_spawn_cell()
        self.player: Player = Player(spawn_row, spawn_col, player_lives)
        self.player.score = player_score

        corners = [
            (0, 0),
            (0, self.maze.width - 1),
            (self.maze.height - 1, 0),
            (self.maze.height - 1, self.maze.width - 1),
        ]
        progress = self._level_progress()
        start_normal = Ghost.NORMAL_INTERVAL
        end_normal = Player.BASE_INTERVAL
        normal_interval = round(
            start_normal - (start_normal - end_normal) * progress
        )
        edible_ratio = Ghost.EDIBLE_INTERVAL / max(1, Ghost.NORMAL_INTERVAL)
        edible_interval = round(normal_interval * edible_ratio)

        respawn_delay = round(Ghost.RESPAWN_DELAY * (1.0 - progress))
        edible_duration = round(
            Ghost.EDIBLE_DURATION - (Ghost.EDIBLE_DURATION - 300) * progress
        )
        eyes_interval = round(
            Ghost.EYES_INTERVAL - (Ghost.EYES_INTERVAL - 2) * progress
        )
        eyes_wander_duration = round(
            Ghost.EYES_WANDER_DURATION * (1.0 - progress)
        )
        self.ghosts: list[Ghost] = [
            Ghost(
                r,
                c,
                r,
                c,
                GHOST_COLORS[i],
                normal_interval=normal_interval,
                edible_interval=edible_interval,
                respawn_delay=respawn_delay,
                edible_duration=edible_duration,
                eyes_interval=eyes_interval,
                eyes_wander_duration=eyes_wander_duration,
            )
            for i, (r, c) in enumerate(corners)
        ]
        self.pacgums: list[Pacgum] = []
        self.super_pacgums: list[SuperPacgum] = []
        self._place_items()

    def _reachable_cells(self, start: tuple[int, int]) -> set[tuple[int, int]]:
        """Percorre os corredores conectados a partir de uma célula inicial.

        Args:
            start: Célula de origem (linha, coluna).

        Returns:
            Conjunto com todas as células alcançáveis.

        É usado para distribuir itens sem colocá-los em áreas inacessíveis.
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

    def _find_spawn_cell(self) -> tuple[int, int]:
        """Procura um ponto inicial válido próximo ao centro do labirinto.

        Returns:
            Coordenadas da célula onde Pac-Man começará.

        É chamado durante a criação do nível, logo após gerar o labirinto.
        """
        center = (self.maze.height // 2, self.maze.width // 2)
        if self.maze.neighbours(*center):
            return center
        visited: set[tuple[int, int]] = {center}
        queue: list[tuple[int, int]] = [center]
        idx = 0
        while idx < len(queue):
            r, c = queue[idx]
            idx += 1
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if self.maze.passable(nr, nc) and (nr, nc) not in visited:
                    if self.maze.neighbours(nr, nc):
                        return (nr, nc)
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return center

    def _place_items(self) -> None:
        """Distribui itens de poder nos cantos e itens comuns nos corredores.

        É executada uma vez durante a preparação do nível, após definir
        a posição inicial do jogador.
        """
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
        """Avança o cronômetro, os personagens e as regras do nível.

        Args:
            dt: Tempo transcorrido desde a atualização anterior, em segundos.

        É chamada pelo loop do jogo enquanto a partida está ativa. Após mover
        todos os personagens, verifica itens coletados, colisões e vitória.
        """
        if self.level_won or self.level_lost:
            return
        if not self.time_frozen:
            self.time_remaining -= dt
            if self.time_remaining <= 0:
                self.time_remaining = 0
                self.level_lost = True
                return
        old_player_pos = (self.player.row, self.player.col)
        old_ghost_positions = [(g.row, g.col) for g in self.ghosts]
        self.player.update(self.maze)
        blinky_pos = (
            (self.ghosts[0].row, self.ghosts[0].col) if self.ghosts else None
        )
        for ghost in self.ghosts:
            ghost.update(
                self.maze,
                self.player.row,
                self.player.col,
                self.player.direction,
                blinky_pos,
            )
        self._check_pacgum_collision()
        self._check_ghost_collision(old_player_pos, old_ghost_positions)
        self._check_win()

    def _check_pacgum_collision(self) -> None:
        """Marca itens na célula de Pac-Man como coletados e aplica seus efeitos.

        É chamada a cada atualização depois do movimento: Pacgums dão pontos
        e Super Pacgums também deixam os fantasmas vulneráveis.
        """
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

    def _check_ghost_collision(
        self,
        old_player_pos: tuple[int, int],
        old_ghost_positions: list[tuple[int, int]],
    ) -> None:
        """Resolve colisões entre Pac-Man e fantasmas, inclusive cruzamentos.

        Args:
            old_player_pos: Posição de Pac-Man antes deste passo.
            old_ghost_positions: Posições dos fantasmas antes deste passo.

        É chamada após o movimento. Comer um fantasma vulnerável dá pontos;
        tocar um fantasma perseguidor remove vida e pode encerrar o nível.
        """
        pr, pc = self.player.row, self.player.col
        for ghost, old_ghost_pos in zip(self.ghosts, old_ghost_positions):
            same_cell = ghost.row == pr and ghost.col == pc
            swapped = (
                (ghost.row, ghost.col) == old_player_pos
                and old_ghost_pos == (pr, pc)
            )
            if same_cell or swapped:
                if ghost.state == GhostState.EDIBLE:
                    ghost.eat(self.maze)
                    self.player.score += self.config.points_per_ghost
                elif (
                    ghost.state == GhostState.CHASING
                    and not self.player.is_immune
                ):
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.level_lost = True
                    else:
                        self.player.respawn()
                    return

    def _level_progress(self) -> float:
        """Calcula a fração de progresso entre o primeiro e o último nível.

        Returns:
            Valor entre zero e um, usado para ajustar a dificuldade.

        É usada na preparação dos fantasmas para escalar seus tempos.
        """
        total = len(self.config.levels)
        if total <= 1:
            return 0.0
        return min(1.0, self.level_index / (total - 1))

    def _compute_level_time(self) -> float:
        """Calcula o limite de tempo do nível conforme a progressão da partida.

        Returns:
            Tempo disponível em segundos, limitado a 999.

        É chamada ao criar cada nível para definir seu cronômetro.
        """
        total = len(self.config.levels)
        start_time = float(self.config.level_max_time)
        if total <= 1:
            return float(min(999.0, start_time))
        if self.level_index >= total - 1:
            return 999.0
        level_nine_time = max(start_time, 600.0)
        if total == 2:
            return float(min(999.0, start_time))
        progress = min(1.0, self.level_index / (total - 2))
        span = level_nine_time - start_time
        scaled = round(start_time + span * progress)
        return float(min(999.0, scaled))

    def _check_win(self) -> None:
        """Marca vitória quando todas as Pacgums comuns foram coletadas.

        É chamada ao fim da atualização do nível para que ``Game`` possa
        carregar a próxima fase ou apresentar a tela de vitória final.
        """
        if self.pacgums and all(pg.eaten for pg in self.pacgums):
            self.level_won = True

    def toggle_cheat_mode(self) -> None:
        """Ativa/desativa as trapaças e limpa efeitos contínuos ao desativar.

        É acionada pelo atalho Shift+C durante a partida.
        """
        self.cheat_mode = not self.cheat_mode
        if not self.cheat_mode:
            self.player.invincible = False
            self.player.speed_boost = False
            self.time_frozen = False
            for ghost in self.ghosts:
                ghost.unfreeze()

    def toggle_invincibility(self) -> None:
        """Alterna a invencibilidade de Pac-Man se o modo de trapaça estiver ativo.

        É chamada pela tecla I enquanto a partida está em andamento.
        """
        if not self.cheat_mode:
            return
        self.player.invincible = not self.player.invincible

    def skip_level(self) -> None:
        """Marca o nível como vencido imediatamente, se trapaças estiverem ativas.

        É acionada pela tecla X; o fluxo normal do jogo então carrega a fase
        seguinte ou mostra a vitória final.
        """
        if not self.cheat_mode:
            return
        self.level_won = True

    def toggle_ghost_freeze(self) -> None:
        """Alterna o congelamento dos fantasmas, sem afetar os que retornam.

        É chamada pela tecla F no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        all_frozen = all(
            g.frozen for g in self.ghosts
            if g.state != GhostState.RESPAWNING
        )
        for ghost in self.ghosts:
            if all_frozen:
                ghost.unfreeze()
            else:
                ghost.freeze()

    def add_extra_life(self) -> None:
        """Adiciona uma vida sem ultrapassar o limite permitido.

        É chamada pela tecla L no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        _, max_lives = INT_CLAMPS["lives"]
        self.player.lives = min(max_lives, self.player.lives + 1)

    def remove_life(self) -> None:
        """Remove uma vida e encerra o nível se não restar nenhuma.

        É chamada pela tecla R no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        self.player.lives -= 1
        if self.player.lives <= 0:
            self.level_lost = True

    def add_time(self, seconds: float = 10.0) -> None:
        """Acrescenta segundos ao cronômetro, respeitando o limite de 999.

        É chamada pelo atalho de adicionar tempo no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        self.time_remaining = min(999.0, self.time_remaining + seconds)

    def remove_time(self, seconds: float = 10.0) -> None:
        """Subtrai segundos do cronômetro e perde o nível se ele zerar.

        É chamada pelo atalho de remover tempo no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        self.time_remaining = max(0.0, self.time_remaining - seconds)
        if self.time_remaining <= 0:
            self.level_lost = True

    def toggle_time_freeze(self) -> None:
        """Alterna a pausa do cronômetro do nível.

        É chamada pela tecla T no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        self.time_frozen = not self.time_frozen

    def toggle_speed_boost(self) -> None:
        """Alterna o aumento de velocidade de Pac-Man.

        É chamada pela tecla B no modo de trapaça.
        """
        if not self.cheat_mode:
            return
        self.player.speed_boost = not self.player.speed_boost
