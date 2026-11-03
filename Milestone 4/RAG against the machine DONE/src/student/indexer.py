import json
import os
import pickle
import re
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi
from tqdm import tqdm

from student.chunker import get_file_chunks

INDEXABLE_EXTENSIONS = {
    '.py', '.md', '.rst', '.txt', '.yaml', '.yml',
    '.toml', '.cfg', '.ini', '.sh'
}

SKIP_DIRS = {
    '__pycache__', '.git', '.github', 'node_modules',
    'build', 'dist', '.mypy_cache', '.pytest_cache',
    'csrc', '.buildkite', '.gemini', 'benchmarks'
}


def tokenize(text: str) -> List[str]:
    """Divide o texto em termos para a busca BM25.

    Recebe um texto e devolve palavras e partes separadas por ``_``,
    ignorando itens com menos de dois caracteres.
    Exemplo: ``"index_file"`` vira ``["index_file", "index", "file"]``.
    """
    tokens = re.split(r'[^\w_]+', text.lower())
    expanded: List[str] = []
    for token in tokens:
        if len(token) > 1:
            parts = re.sub(r'([A-Z][a-z]+)', r' \1', token).split()
            for part in parts:
                sub = [p for p in part.split('_') if len(p) > 1]
                expanded.extend(sub)
            expanded.append(token)
    return [t for t in expanded if len(t) > 1]


def should_skip_file(file_path: str) -> bool:
    """Indica se um caminho deve ficar fora do índice.

    Recebe o caminho de um arquivo. Devolve ``True`` para pastas ignoradas,
    caminhos ocultos ou extensões não suportadas; caso contrário, devolve
    ``False``. Exemplo: ``"src/main.py"`` devolve ``False``.
    """
    parts = file_path.replace('\\', '/').split('/')
    for part in parts:
        if part in SKIP_DIRS or part.startswith('.'):
            return True
    ext = os.path.splitext(file_path)[1].lower()
    return ext not in INDEXABLE_EXTENSIONS


def collect_files(repo_path: str) -> List[str]:
    """Encontra os arquivos do projeto que podem ser indexados.

    Recebe o caminho da pasta do repositório e devolve uma lista com os
    caminhos completos dos arquivos aceitos. Passo a passo: percorre
    ``repo_path``, ignora pastas como ``.git`` e inclui arquivos ``.py``.
    Exemplo: se existir ``meu_projeto/src/main.py``, esse caminho entra
    na lista devolvida.
    """
    files: List[str] = []
    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS and not d.startswith('.')
        ]
        for fname in filenames:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, repo_path)
            if not should_skip_file(rel_path):
                files.append(full_path)
    return files


class BM25Index:
    """Constrói, consulta e guarda o índice de busca do repositório."""

    def __init__(
        self, repo_path: str, max_chunk_size: int = 2000
    ) -> None:
        """Prepara um índice vazio para um repositório.

        Recebe a pasta do repositório e o tamanho máximo de cada trecho.
        Por exemplo, ``BM25Index("projeto", 2000)`` guarda essas opções e
        inicia sem trechos; não devolve um valor (retorna ``None``).
        """
        self.repo_path = repo_path
        self.max_chunk_size = max_chunk_size
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Tuple[str, int, int, str]] = []

    def build(self) -> None:
        """Lê e divide os arquivos para montar o índice BM25.

        Não recebe argumentos adicionais e não devolve um valor. Passo a
        passo: encontra arquivos aceitos, lê o conteúdo, cria trechos com
        ``get_file_chunks``, guarda caminho e posições em ``self.chunks`` e
        calcula o índice BM25. Arquivos vazios ou que não podem ser lidos
        são ignorados. Exemplo: depois de ``build()``, ``search()`` pode
        procurar termos nos trechos carregados.
        """
        files = collect_files(self.repo_path)
        corpus: List[List[str]] = []

        for fpath in tqdm(files, desc="Indexing files"):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except OSError:
                continue

            if not content.strip():
                continue

            rel_path = os.path.relpath(fpath)
            file_chunks = get_file_chunks(
                fpath, content, self.max_chunk_size
            )

            for chunk_text, start, end in file_chunks:
                if chunk_text.strip():
                    self.chunks.append((rel_path, start, end, chunk_text))
                    corpus.append(tokenize(chunk_text))

        if corpus:
            self.bm25 = BM25Okapi(corpus)

    def search(
        self, query: str, k: int = 10
    ) -> List[Dict[str, Any]]:
        """Busca os trechos mais relevantes para uma pergunta.

        Recebe o texto da busca e a quantidade máxima de resultados ``k``.
        Devolve uma lista ordenada de dicionários com caminho, posições dos
        caracteres e pontuação BM25. Passo a passo: tokeniza a pergunta,
        calcula as pontuações, seleciona até ``k`` trechos com pontuação
        positiva e remove repetições. Sem índice ou resultados, devolve
        ``[]``. Exemplo: ``search("index", k=1)`` pode devolver
        ``[{"file_path": "...", "first_character_index": 0,
        "last_character_index": 20, "score": 1.2}]``; a pontuação depende
        dos arquivos indexados.
        """
        if self.bm25 is None or not self.chunks:
            return []

        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        top_k = sorted( 
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:k]

        results: List[Dict[str, Any]] = []
        seen: set[Tuple[str, int, int]] = set()

        for idx in top_k:
            if scores[idx] <= 0:
                continue
            file_path, start, end, _ = self.chunks[idx]
            key = (file_path, start, end)
            if key not in seen:
                seen.add(key)
                results.append({
                    'file_path': file_path,
                    'first_character_index': start,
                    'last_character_index': end,
                    'score': float(scores[idx]),
                })

        return results

    def save(self, index_dir: str) -> None:
        """Guarda o índice e os trechos em disco para uso posterior.

        Recebe a pasta onde salvar os dados. Não devolve um valor
        (retorna ``None``). Exemplo: ``save("data/processed/bm25_index")``
        cria os arquivos do BM25, metadados e textos dos trechos; também
        atualiza o manifesto em ``data/processed/chunks/manifest.json``.
        """
        os.makedirs(index_dir, exist_ok=True)

        with open(os.path.join(index_dir, 'bm25.pkl'), 'wb') as f:
            pickle.dump(self.bm25, f)

        chunks_meta = [
            {'file_path': c[0], 'start': c[1], 'end': c[2]}
            for c in self.chunks
        ]
        with open(os.path.join(index_dir, 'chunks_meta.json'), 'w') as f:
            json.dump({
                'repo_path': self.repo_path,
                'max_chunk_size': self.max_chunk_size,
                'chunks': chunks_meta,
            }, f)

        chunk_texts = [c[3] for c in self.chunks]
        with open(os.path.join(index_dir, 'chunk_texts.pkl'), 'wb') as f:
            pickle.dump(chunk_texts, f)

        processed_dir = os.path.dirname(index_dir)
        chunks_dir = os.path.join(processed_dir, 'chunks')
        os.makedirs(chunks_dir, exist_ok=True)
        manifest_path = os.path.join(chunks_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump({
                'total_chunks': len(self.chunks),
                'repo_path': self.repo_path,
                'max_chunk_size': self.max_chunk_size,
                'source_files': list(
                    sorted(set(c[0] for c in self.chunks))
                ),
            }, f, indent=2)

    @classmethod
    def load(cls, index_dir: str) -> 'BM25Index':
        """Carrega do disco um índice salvo anteriormente.

        Recebe a pasta usada em ``save()`` e devolve um ``BM25Index``
        pronto para busca, com modelo BM25 e trechos restaurados. Passo a
        passo: lê o modelo, os metadados e os textos, cria a instância e
        recompõe cada trecho. Exemplo: ``BM25Index.load("data/processed/"
        "bm25_index")`` devolve um índice que pode receber ``search()``.
        """
        with open(os.path.join(index_dir, 'bm25.pkl'), 'rb') as f:
            bm25 = pickle.load(f)

        with open(os.path.join(index_dir, 'chunks_meta.json'), 'r') as f:
            meta = json.load(f)

        with open(os.path.join(index_dir, 'chunk_texts.pkl'), 'rb') as f:
            chunk_texts = pickle.load(f)

        instance = cls(
            repo_path=meta['repo_path'],
            max_chunk_size=meta['max_chunk_size']
        )
        instance.bm25 = bm25
        instance.chunks = [
            (c['file_path'], c['start'], c['end'], chunk_texts[i])
            for i, c in enumerate(meta['chunks'])
        ]
        return instance
