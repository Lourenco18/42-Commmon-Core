import json
import os
import pickle
import sys
from typing import Any, Dict, List, Optional, Type, TypeVar

import fire
from pydantic import BaseModel, ValidationError
from tqdm import tqdm

from student.indexer import BM25Index
from student.models import (
    MinimalAnswer,
    MinimalSearchResults,
    MinimalSource,
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)

DEFAULT_DATA_DIR = "data/raw"
DEFAULT_INDEX_DIR = "data/processed/bm25_index"
DEFAULT_REPO_SUBDIR = "vllm-0.10.1"
DEFAULT_MAX_CHUNK_SIZE = 2000

ModelT = TypeVar('ModelT', bound=BaseModel)


def _load_index(index_dir: str = DEFAULT_INDEX_DIR) -> BM25Index:
    """Carrega o índice salvo para os comandos de busca.

    Recebe a pasta do índice e devolve um ``BM25Index`` carregado. Primeiro
    verifica se o arquivo principal existe; depois lê o índice. Se os
    arquivos estiverem ausentes ou inválidos, mostra um erro e encerra o
    comando. Exemplo: ``_load_index("data/processed/bm25_index")`` devolve
    um índice pronto para ``search()``.
    """
    if not os.path.exists(os.path.join(index_dir, 'bm25.pkl')):
        print(
            f"Index not found at '{index_dir}'. "
            "Run 'index' command first.",
            file=sys.stderr
        )
        sys.exit(1)
    try:
        return BM25Index.load(index_dir)
    except (OSError, pickle.UnpicklingError, json.JSONDecodeError) as exc:
        print(f"Error: failed to load index at '{index_dir}': {exc}",
              file=sys.stderr)
        sys.exit(1)


def _load_json_model(path: str, model: Type[ModelT]) -> ModelT:
    """Lê um JSON e valida o conteúdo com um modelo Pydantic.

    Recebe o caminho do arquivo e a classe do modelo esperado. Devolve
    uma instância validada desse modelo. Passo a passo: abre o arquivo,
    converte o JSON e valida os campos; se o arquivo ou os dados forem
    inválidos, mostra um erro claro e encerra o comando. Exemplo:
    ``_load_json_model("perguntas.json", RagDataset)`` devolve um
    ``RagDataset``.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: '{path}'", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Error: could not read '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: '{path}' is not valid JSON ({exc}).", file=sys.stderr)
        sys.exit(1)

    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        print(
            f"Error: '{path}' does not match the expected format:\n{exc}",
            file=sys.stderr,
        )
        sys.exit(1)


def _validate_k(k: int) -> int:
    """Verifica se a quantidade de resultados pedida é positiva.

    Recebe ``k`` e devolve o mesmo valor se for maior que zero. Caso
    contrário, mostra uma mensagem de erro e encerra o comando. Exemplo:
    ``_validate_k(5)`` devolve ``5``.
    """
    if k <= 0:
        print(
            f"Error: --k must be a positive integer, got {k}.",
            file=sys.stderr,
        )
        sys.exit(1)
    return k


def _write_json(
    output: BaseModel, save_directory: str, source_path: str
) -> str:
    """Salva um modelo Pydantic como JSON na pasta de saída.

    Recebe os dados, a pasta onde salvar e o caminho usado para obter o
    nome do arquivo. Cria a pasta se necessário, grava o JSON formatado e
    devolve o caminho do arquivo criado. Exemplo: para
    ``source_path="data/questions.json"``, o arquivo salvo também se chama
    ``questions.json``.
    """
    try:
        os.makedirs(save_directory, exist_ok=True)
        out_filename = os.path.basename(source_path)
        out_path = os.path.join(save_directory, out_filename)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output.model_dump_json(indent=2))
        return out_path
    except OSError as exc:
        print(
            f"Error: could not write output to '{save_directory}': {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


class RAGSystem:
    """Oferece os comandos para indexar, pesquisar e avaliar o projeto."""

    def index(
        self,
        data_dir: str = DEFAULT_DATA_DIR,
        index_dir: str = DEFAULT_INDEX_DIR,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    ) -> None:
        """Cria e salva o índice de busca do repositório.

        Recebe a pasta dos dados, a pasta de saída do índice e o limite de
        caracteres por trecho. Passo a passo: localiza o repositório,
        constrói o índice BM25 e salva os arquivos para os comandos de
        busca. Não devolve um valor. Exemplo: ``index()`` usa as pastas e
        o limite padrão do projeto.
        """
        repo_path = os.path.join(data_dir, DEFAULT_REPO_SUBDIR)

        if not os.path.exists(repo_path):
            repo_path = data_dir

        print(f"Indexing repository at '{repo_path}'...")
        idx = BM25Index(repo_path=repo_path, max_chunk_size=max_chunk_size)
        idx.build()

        print(f"Indexed {len(idx.chunks)} chunks.")
        idx.save(index_dir)
        print(f"Ingestion complete! Indices saved under {index_dir}")

    def search(
        self,
        query: str,
        k: int = 10,
        index_dir: str = DEFAULT_INDEX_DIR,
    ) -> None:
        """Busca trechos relevantes para uma pergunta e mostra-os no terminal.

        Recebe a pergunta, o número máximo de resultados e a pasta do
        índice. Valida a entrada, consulta o BM25 e imprime os arquivos,
        posições e pontuações encontrados. Não devolve um valor. Exemplo:
        ``search("como funciona o chunking", k=3)`` mostra até três
        resultados.
        """
        k = _validate_k(k)
        if not query or not query.strip():
            print("Error: query must be a non-empty string.",
                  file=sys.stderr)
            sys.exit(1)
        idx = _load_index(index_dir)
        results = idx.search(query, k=k)

        if not results:
            print("No results found.")
            return

        print(f"\nTop {len(results)} results for: '{query}'\n")
        for i, r in enumerate(results, 1):
            print(
                f"{i}. [{r['file_path']}] "
                f"chars {r['first_character_index']}"
                f"-{r['last_character_index']}"
                f" (score: {r['score']:.3f})"
            )

    def search_dataset(
        self,
        dataset_path: str,
        save_directory: str = "data/output/search_results",
        k: int = 10,
        index_dir: str = DEFAULT_INDEX_DIR,
        limit: Optional[int] = None,
    ) -> None:
        """Busca fontes para as perguntas de um conjunto de dados.

        Recebe o JSON de perguntas, a pasta de saída, o número máximo de
        fontes por pergunta, o índice e um limite opcional de perguntas.
        Passo a passo: valida os dados, pesquisa cada pergunta, monta os
        resultados e grava um JSON ``StudentSearchResults``. Não devolve
        um valor. Exemplo: ``search_dataset("questions.json", k=5)``
        cria um arquivo com até cinco fontes para cada pergunta.
        """
        k = _validate_k(k)
        idx = _load_index(index_dir)
        dataset = _load_json_model(dataset_path, RagDataset)
        questions = dataset.rag_questions
        if limit is not None:
            if limit <= 0:
                print(
                    f"Error: --limit must be a positive integer, "
                    f"got {limit}.",
                    file=sys.stderr,
                )
                sys.exit(1)
            questions = questions[:limit]
            print(
                f"--limit={limit}: processing {len(questions)} of "
                f"{len(dataset.rag_questions)} questions "
                f"(dev/testing mode)."
            )
        search_results: List[MinimalSearchResults] = []

        for q in tqdm(questions, desc="Searching"):
            question_str = str(q.question)
            question_id = str(q.question_id)

            results = idx.search(question_str, k=k)
            sources = [
                MinimalSource(
                    file_path=r['file_path'],
                    first_character_index=r['first_character_index'],
                    last_character_index=r['last_character_index'],
                )
                for r in results
            ]
            search_results.append(MinimalSearchResults(
                question_id=question_id,
                question_str=question_str,
                retrieved_sources=sources,
            ))

        output = StudentSearchResults(search_results=search_results, k=k)
        out_path = _write_json(output, save_directory, dataset_path)

        print(f"Saved student_search_results to {out_path}")

    def answer(
        self,
        query: str,
        k: int = 10,
        index_dir: str = DEFAULT_INDEX_DIR,
        max_new_tokens: int = 256,
    ) -> None:
        """Procura fontes para uma pergunta e gera uma resposta com o modelo.

        Recebe a pergunta, o número de fontes, a pasta do índice e o limite
        de tokens a gerar. Primeiro recupera contexto com BM25; depois
        carrega o modelo e pede uma resposta baseada nesse contexto. Mostra
        pergunta e resposta no terminal, sem devolver um valor. Exemplo:
        ``answer("O que é RAG?", k=3)`` imprime a resposta no terminal;
        as fontes recuperadas são usadas como contexto para o modelo.
        """
        from student.generator import AnswerGenerator

        k = _validate_k(k)
        if not query or not query.strip():
            print("Error: query must be a non-empty string.",
                  file=sys.stderr)
            sys.exit(1)

        idx = _load_index(index_dir)
        results = idx.search(query, k=k)

        if not results:
            print("No relevant context found.")
            return

        print(f"Loading LLM ({DEFAULT_MAX_CHUNK_SIZE} chars max context)...")
        gen = AnswerGenerator(
            max_context_length=DEFAULT_MAX_CHUNK_SIZE,
            max_new_tokens=max_new_tokens,
        )
        try:
            gen.load()
        except (OSError, ValueError) as exc:
            print(f"Error: could not load model "
                  f"'{gen.model_name}': {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"\nQuestion: {query}\n")
        answer_text = gen.generate(
            question=query,
            sources=results,
            repo_path=idx.repo_path,
        )
        print(f"Answer: {answer_text}")

    def answer_dataset(
        self,
        student_search_results_path: str,
        save_directory: str = "data/output/search_results_and_answer",
        index_dir: str = DEFAULT_INDEX_DIR,
        limit: Optional[int] = None,
        max_new_tokens: int = 256,
    ) -> None:
        """Gera respostas para os resultados de busca de um conjunto.

        Recebe o JSON produzido pela busca em lote, a pasta de saída, o
        índice, um limite opcional de perguntas e o limite de tokens.
        Passo a passo: carrega os resultados e o modelo, gera uma resposta
        para cada pergunta e grava um JSON ``StudentSearchResultsAndAnswer``.
        Não devolve um valor. Exemplo: ``answer_dataset("search_results.json")``
        cria um arquivo com as fontes e respostas.
        """
        from student.generator import AnswerGenerator

        idx = _load_index(index_dir)
        student_results = _load_json_model(
            student_search_results_path, StudentSearchResults
        )
        results_to_answer = student_results.search_results
        if limit is not None:
            if limit <= 0:
                print(
                    f"Error: --limit must be a positive integer, "
                    f"got {limit}.",
                    file=sys.stderr,
                )
                sys.exit(1)
            results_to_answer = results_to_answer[:limit]
            print(
                f"--limit={limit}: generating answers for "
                f"{len(results_to_answer)} of "
                f"{len(student_results.search_results)} questions "
                f"(dev/testing mode)."
            )

        print(f"Loaded {len(student_results.search_results)} questions "
              f"from {student_search_results_path}")
        print("Loading LLM...")

        gen = AnswerGenerator(
            max_context_length=DEFAULT_MAX_CHUNK_SIZE,
            max_new_tokens=max_new_tokens,
        )
        try:
            gen.load()
        except (OSError, ValueError) as exc:
            print(f"Error: could not load model "
                  f"'{gen.model_name}': {exc}", file=sys.stderr)
            sys.exit(1)

        answered: List[MinimalAnswer] = []

        for i, sr in enumerate(
            tqdm(results_to_answer, desc="Answering")
        ):
            sources_dicts: List[Dict[str, Any]] = [
                {
                    'file_path': s.file_path,
                    'first_character_index': s.first_character_index,
                    'last_character_index': s.last_character_index,
                }
                for s in sr.retrieved_sources
            ]
            answer_text = gen.generate(
                question=sr.question_str,
                sources=sources_dicts,
                repo_path=idx.repo_path,
            )
            answered.append(MinimalAnswer(
                question_id=sr.question_id,
                question_str=sr.question_str,
                retrieved_sources=sr.retrieved_sources,
                answer=answer_text,
            ))
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1} of "
                      f"{len(results_to_answer)} questions")

        print(f"Processed {len(answered)} of "
              f"{len(results_to_answer)} questions")

        output = StudentSearchResultsAndAnswer(
            search_results=answered,
            k=student_results.k,
        )
        out_path = _write_json(
            output, save_directory, student_search_results_path
        )

        print(f"Saved student_search_results_and_answer to {out_path}")

    def evaluate(
        self,
        student_results_path: str,
        dataset_path: str,
        k: int = 10,
        max_context_length: int = 2000,
    ) -> None:
        """Compara fontes encontradas com fontes esperadas e imprime Recall@k.

        Recebe o JSON de resultados, o conjunto de referência e os
        parâmetros ``k`` e ``max_context_length``. Valida os arquivos,
        compara as fontes por arquivo e sobreposição das posições e mostra
        Recall@1, @3, @5 e @10. Não devolve um valor; o relatório aparece
        no terminal. Nota: nesta função, os valores impressos são sempre
        1, 3, 5 e 10; ``max_context_length`` não é usado no cálculo.
        Exemplo: ``evaluate("resultados.json", "referencia.json")`` imprime
        as métricas de recuperação.
        """
        k = _validate_k(k)
        student_data = _load_json_model(
            student_results_path, StudentSearchResults
        )
        gt_dataset = _load_json_model(dataset_path, RagDataset)

        gt_lookup: Dict[str, Any] = {}
        for q in gt_dataset.rag_questions:
            if hasattr(q, 'sources'):
                gt_lookup[q.question_id] = q

        total_questions = len(gt_lookup)
        questions_with_sources = sum(
            1 for q in gt_dataset.rag_questions
            if hasattr(q, 'sources') and getattr(q, 'sources', [])
        )
        questions_with_student = sum(
            1 for sr in student_data.search_results
            if sr.retrieved_sources
        )

        print("Student data is valid: True")
        print(f"Total number of questions:"
              f"{total_questions}")
        print(f"Total number of questions with sources:"
              f"{questions_with_sources}")
        print(f"Total number of questions with student sources: "
              f"{questions_with_student}")

        recall_at_k: Dict[int, float] = {}
        for k_val in [1, 3, 5, 10]:
            recall_at_k[k_val] = _compute_recall_at_k(
                student_data.search_results,
                gt_lookup,
                k=k_val,
            )

        evaluated = min(len(student_data.search_results), total_questions)
        print("\nEvaluation Results")
        print("=" * 40)
        print(f"Questions evaluated: {evaluated}")
        for k_val in [1, 3, 5, 10]:
            print(f"Recall@{k_val}: {recall_at_k[k_val]:.3f}")


def _iou(
    retrieved_start: int, retrieved_end: int,
    gt_start: int, gt_end: int,
) -> float:
    """Calcula a proporção de sobreposição entre duas posições de texto.

    Recebe início e fim do trecho encontrado e do trecho esperado.
    Devolve a interseção dividida pela união, entre ``0`` e ``1``; sem
    sobreposição, devolve ``0.0``. Exemplo: os intervalos ``[10, 20]`` e
    ``[15, 25]`` têm IoU de aproximadamente ``0.33``.
    """
    inter_start = max(retrieved_start, gt_start)
    inter_end = min(retrieved_end, gt_end)
    if inter_end <= inter_start:
        return 0.0
    intersection = inter_end - inter_start
    union = (
        (retrieved_end - retrieved_start)
        + (gt_end - gt_start)
        - intersection
    )
    if union <= 0:
        return 0.0
    return intersection / union


def _source_found(
    retrieved: List[MinimalSource],
    gt_source: MinimalSource,
    k: int,
) -> bool:
    """Verifica se uma fonte esperada aparece entre as primeiras ``k`` fontes.

    Recebe as fontes recuperadas, uma fonte de referência e o limite ``k``.
    Devolve ``True`` se encontrar o mesmo arquivo com IoU de pelo menos
    ``0.05``; caso contrário, devolve ``False``. Exemplo: uma fonte do
    mesmo arquivo com posições suficientemente sobrepostas conta como
    encontrada.
    """
    for src in retrieved[:k]:
        if src.file_path == gt_source.file_path:
            iou = _iou(
                src.first_character_index,
                src.last_character_index,
                gt_source.first_character_index,
                gt_source.last_character_index,
            )
            if iou >= 0.05:
                return True
    return False


def _compute_recall_at_k(
    search_results: List[MinimalSearchResults],
    gt_lookup: Dict[str, Any],
    k: int,
) -> float:
    """Calcula o Recall@k médio para perguntas com fontes de referência.

    Recebe os resultados de busca, um dicionário de perguntas de
    referência indexado por ID e o limite ``k``. Para cada pergunta válida,
    conta as fontes esperadas encontradas entre as primeiras ``k``;
    devolve a média dessas proporções. Devolve ``0.0`` se não houver
    perguntas avaliáveis. Exemplo: se a média das proporções for 0.75,
    devolve ``0.75``.
    """
    total_recall = 0.0
    count = 0

    for sr in search_results:
        if sr.question_id not in gt_lookup:
            continue

        gt_q = gt_lookup[sr.question_id]
        gt_sources: List[MinimalSource] = getattr(gt_q, 'sources', [])

        if not gt_sources:
            continue

        found = sum(
            1 for gs in gt_sources
            if _source_found(sr.retrieved_sources, gs, k)
        )
        recall = found / len(gt_sources)
        total_recall += recall
        count += 1

    return total_recall / count if count > 0 else 0.0


def main() -> None:
    """Inicia a interface de linha de comando do projeto.

    Não recebe argumentos diretamente nem devolve um valor. Usa Fire para
    expor os métodos de ``RAGSystem`` como comandos. Exemplo: executar
    ``python -m student search --query="RAG"`` encaminha a chamada ao
    método ``search``.
    """
    fire.Fire(RAGSystem)


if __name__ == '__main__':
    main()
