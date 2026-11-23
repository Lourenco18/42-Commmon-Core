import logging
import random
from typing import Optional

try:
    from mazegenerator import MazeGenerator
except ImportError as exc:
    raise ImportError("mazegenerator package not found.") from exc

logger = logging.getLogger(__name__)

NORTH: int = 1
EAST: int = 2
SOUTH: int = 4
WEST: int = 8


class Maze:
    """Expose dimensions, walls, and traversable neighboring cells."""
    def __init__(self, width: int, height: int, grid: list[list[int]]) -> None:
        """Armazena dimensões e paredes do labirinto gerado.

        Args:
            width: Largura do labirinto em células.
            height: Altura do labirinto em células.
            grid: Células codificadas com bits que representam paredes.

        É chamado por ``generate_maze`` ao preparar cada novo nível.
        """
        self.width: int = width
        self.height: int = height
        self.grid: list[list[int]] = grid

    def is_wall(self, row: int, col: int, direction: int) -> bool:
        """Verifica se há uma parede na direção indicada a partir da célula.

        Args:
            row: Linha da célula atual.
            col: Coluna da célula atual.
            direction: Bit que identifica a direção a verificar.

        Returns:
            ``True`` se existe parede ou se a célula está fora do labirinto.

        É consultada durante o movimento de Pac-Man e dos fantasmas.
        """
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return True
        return bool(self.grid[row][col] & direction)

    def passable(self, row: int, col: int) -> bool:
        """Confirma que uma posição pertence aos limites do labirinto.

        Args:
            row: Linha a verificar.
            col: Coluna a verificar.

        Returns:
            ``True`` se a posição está dentro da grade.

        É usada na checagem de movimento e na busca de caminhos.
        """
        return 0 <= row < self.height and 0 <= col < self.width

    def neighbours(self, row: int, col: int) -> list[tuple[int, int]]:
        """Lista células vizinhas alcançáveis sem atravessar paredes.

        Args:
            row: Linha da célula de origem.
            col: Coluna da célula de origem.

        Returns:
            Coordenadas das células conectadas à origem por um corredor.

        É usada para posicionar itens, procurar rotas e orientar fantasmas.
        """
        result: list[tuple[int, int]] = []
        directions = [(NORTH, -1, 0), (EAST, 0, 1),
                      (SOUTH, 1, 0), (WEST, 0, -1)]
        for direction, dr, dc in directions:
            nr, nc = row + dr, col + dc
            if self.passable(nr, nc) and not self.is_wall(row, col, direction):
                result.append((nr, nc))
        return result


def generate_maze(width: int, height: int, seed: Optional[int] = None) -> Maze:
    """Gera um labirinto e converte a grade para o formato usado pelo jogo.

    Args:
        width: Largura solicitada em células.
        height: Altura solicitada em células.
        seed: Semente opcional para repetir a mesma geração.

    Returns:
        Labirinto pronto para ser usado na criação de um nível.

    É chamada no início de cada nível; ajusta dimensões para ímpares e gera
    uma semente aleatória quando nenhuma foi configurada.
    """
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1
    actual_seed: int = (
        seed
        if seed is not None
        else random.SystemRandom().randint(0, 2**32 - 1)
    )
    try:
        mg = MazeGenerator(
            size=(
                width,
                height),
            perfect=False,
            seed=actual_seed)
        mg.generate(seed=actual_seed)
        raw_grid: list[list[int]] = mg.maze
    except Exception as exc:
        logger.error("Maze generator failed: %s", exc)
        raise RuntimeError(f"Maze generation failed: {exc}") from exc
    grid: list[list[int]] = []
    for r in range(height):
        row_data: list[int] = []
        for c in range(width):
            try:
                row_data.append(int(raw_grid[r][c]))
            except (IndexError, TypeError):
                row_data.append(0)
        grid.append(row_data)

    logger.info(
        "Generated %dx%d maze with seed %d",
        width,
        height,
        actual_seed)
    return Maze(width=width, height=height, grid=grid)
