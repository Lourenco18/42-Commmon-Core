import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)
MAX_ENTRIES: int = 10
NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9 ]{1,10}$")


def _validate_name(name: str) -> str:
    """Normaliza o nome e substitui valores inválidos por ``Player``.

    Args:
        name: Nome digitado na tela de recorde.

    Returns:
        Nome com até dez caracteres alfanuméricos ou o padrão seguro.

    É usada sempre que um novo recorde é criado ou carregado do arquivo.
    """
    name = name.strip()[:10]
    if not name or not NAME_PATTERN.match(name):
        return "Player"
    return name


class HighscoreEntry:
    """Store a validated player name and score."""
    def __init__(self, name: str, score: int) -> None:
        """Cria um registro de pontuação com nome e valor normalizados.

        Args:
            name: Nome do jogador.
            score: Pontuação acumulada na partida.

        É chamado ao carregar ou inserir uma pontuação na tabela.
        """
        self.name: str = _validate_name(name)
        self.score: int = max(0, int(score))

    def to_dict(self) -> dict[str, object]:
        """Converte o registro para os campos salvos no arquivo JSON.

        Returns:
            Dicionário com ``name`` e ``score``.

        É usado por ``save`` ao persistir a tabela de recordes.
        """
        return {"name": self.name, "score": self.score}


class HighscoreSystem:
    """Load, rank, display, and persist highscore entries."""
    def __init__(self, filename: str) -> None:
        """Prepara a tabela de recordes e carrega os dados existentes.

        Args:
            filename: Caminho do arquivo de recordes.

        É criado junto com ``Game``, antes de exibir o menu inicial.
        """
        self.filename: str = filename
        self.entries: list[HighscoreEntry] = []
        self.load()

    def load(self) -> None:
        """Lê o arquivo e mantém apenas os dez melhores registros válidos.

        É chamado ao iniciar o sistema de recordes; se o arquivo não existe
        ou não pode ser lido, começa com uma tabela vazia.
        """
        if not os.path.exists(self.filename):
            self.entries = []
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                raw: object = json.load(f)
            if not isinstance(raw, list):
                raise ValueError("Root must be a list")
            loaded: list[HighscoreEntry] = []
            for item in raw:
                if isinstance(item, dict):
                    try:
                        name = str(item.get("name", "Player"))
                        score = int(item.get("score", 0))
                        loaded.append(HighscoreEntry(name, score))
                    except (TypeError, ValueError):
                        pass
            self.entries = sorted(
                loaded,
                key=lambda e: e.score,
                reverse=True)[
                :MAX_ENTRIES]
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("Could not load highscores: %s", exc)
            self.entries = []

    def save(self) -> None:
        """Grava a tabela de recordes atual em formato JSON.

        É chamada ao confirmar o nome do jogador e ao encerrar o jogo.
        """
        try:
            os.makedirs(os.path.dirname(self.filename) or ".", exist_ok=True)
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
        except OSError as exc:
            logger.warning("Could not save highscores: %s", exc)

    def add(self, name: str, score: int) -> Optional[int]:
        """Insere uma pontuação, ordena a tabela e conserva os dez primeiros.

        Args:
            name: Nome informado após a partida.
            score: Pontuação final.

        Returns:
            Posição do novo registro, ou ``None`` se ficou fora do top 10.

        É chamada quando o jogador confirma a tela de entrada do nome.
        """
        entry = HighscoreEntry(name, score)
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.score, reverse=True)
        self.entries = self.entries[:MAX_ENTRIES]
        if entry in self.entries:
            return self.entries.index(entry) + 1
        return None

    def is_highscore(self, score: int) -> bool:
        """Verifica se uma pontuação entraria na tabela dos dez melhores.

        Args:
            score: Pontuação a comparar.

        Returns:
            ``True`` se ainda há vagas ou se supera o menor recorde atual.

        Pode ser usada antes de solicitar o nome de um jogador.
        """
        return len(
            self.entries) < MAX_ENTRIES or score > self.entries[-1].score

    def get_top(self, n: int = MAX_ENTRIES) -> list[HighscoreEntry]:
        """Retorna o início da tabela já ordenada por pontuação.

        Args:
            n: Quantidade máxima de registros solicitada.

        Returns:
            Até ``n`` recordes, do maior para o menor.

        É usada para o resumo do menu e para a tela completa de recordes.
        """
        return self.entries[:n]
