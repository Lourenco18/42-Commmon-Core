"""Main CLI entry point for the RAG against the machine project.

Provides commands for indexing, searching, answering, and evaluating
using Python Fire as the CLI framework.

Usage:
    uv run python -m student index [--data_dir DATA_DIR] [--max_chunk_size N]
    uv run python -m student search QUERY [--k K]
    uv run python -m student search_dataset --dataset_path PATH [--k K] ...
    uv run python -m student answer QUERY [--k K]
    uv run python -m student answer_dataset --student_search_results_path P ...
    uv run python -m student evaluate --student_results_path P --dataset_path P
"""

import json
import os
import sys
from typing import Any, Dict, List

import fire
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

# Default paths
DEFAULT_DATA_DIR = "data/raw"
DEFAULT_INDEX_DIR = "data/processed/bm25_index"
DEFAULT_REPO_SUBDIR = "vllm-0.10.1"
DEFAULT_MAX_CHUNK_SIZE = 2000


def _load_index(index_dir: str = DEFAULT_INDEX_DIR) -> BM25Index:
    """Load the BM25 index from disk.

    Args:
        index_dir: Directory containing the saved index.

    Returns:
        Loaded BM25Index instance.

    Raises:
        SystemExit: If index files are not found.
    """
    if not os.path.exists(os.path.join(index_dir, 'bm25.pkl')):
        print(
            f"Index not found at '{index_dir}'. "
            "Run 'index' command first.",
            file=sys.stderr
        )
        sys.exit(1)
    return BM25Index.load(index_dir)


class RAGSystem:
    """CLI for the RAG against the machine system.

    Provides commands: index, search, search_dataset, answer,
    answer_dataset, evaluate.
    """

    def index(
        self,
        data_dir: str = DEFAULT_DATA_DIR,
        index_dir: str = DEFAULT_INDEX_DIR,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    ) -> None:
        """Index the repository files for retrieval.

        Args:
            data_dir: Directory containing the vLLM repository.
            index_dir: Directory where the index will be saved.
            max_chunk_size: Maximum characters per chunk.
        """
        repo_path = os.path.join(data_dir, DEFAULT_REPO_SUBDIR)

        if not os.path.exists(repo_path):
            # Try data_dir directly
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
        """Search for a single query and print results.

        Args:
            query: The search query string.
            k: Number of results to return.
            index_dir: Directory containing the saved index.
        """
        idx = _load_index(index_dir)
        results = idx.search(query, k=k)

        if not results:
            print("No results found.")
            return

        print(f"\nTop {len(results)} results for: '{query}'\n")
        for i, r in enumerate(results, 1):
            print(
                f"{i}. [{r['file_path']}] "
                f"chars {r['first_character_index']}-{r['last_character_index']}"
                f" (score: {r['score']:.3f})"
            )

    def search_dataset(
        self,
        dataset_path: str,
        save_directory: str = "data/output/search_results",
        k: int = 10,
        index_dir: str = DEFAULT_INDEX_DIR,
    ) -> None:
        """Process a dataset of questions and save search results.

        Args:
            dataset_path: Path to the JSON dataset file.
            save_directory: Directory where results will be saved.
            k: Number of results per question.
            index_dir: Directory containing the saved index.
        """
        idx = _load_index(index_dir)

        with open(dataset_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        dataset = RagDataset.model_validate(raw)
        search_results: List[MinimalSearchResults] = []

        for q in tqdm(dataset.rag_questions, desc="Searching"):
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
                question=question_str,
                retrieved_sources=sources,
            ))

        output = StudentSearchResults(search_results=search_results, k=k)
        os.makedirs(save_directory, exist_ok=True)
        out_filename = os.path.basename(dataset_path)
        out_path = os.path.join(save_directory, out_filename)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output.model_dump_json(indent=2))

        print(f"Saved student_search_results to {out_path}")

    def answer(
        self,
        query: str,
        k: int = 10,
        index_dir: str = DEFAULT_INDEX_DIR,
    ) -> None:
        """Answer a single query using retrieved context and LLM.

        Args:
            query: The question to answer.
            k: Number of context chunks to retrieve.
            index_dir: Directory containing the saved index.
        """
        from student.generator import AnswerGenerator

        idx = _load_index(index_dir)
        results = idx.search(query, k=k)

        if not results:
            print("No relevant context found.")
            return

        print(f"Loading LLM ({DEFAULT_MAX_CHUNK_SIZE} chars max context)...")
        gen = AnswerGenerator()
        gen.load()

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
    ) -> None:
        """Generate answers for all search results in a file.

        Args:
            student_search_results_path: Path to JSON search results.
            save_directory: Directory where answers will be saved.
            index_dir: Directory containing the saved index.
        """
        from student.generator import AnswerGenerator

        idx = _load_index(index_dir)

        with open(student_search_results_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        student_results = StudentSearchResults.model_validate(raw)

        print(f"Loaded {len(student_results.search_results)} questions "
              f"from {student_search_results_path}")
        print("Loading LLM...")

        gen = AnswerGenerator()
        gen.load()

        answered: List[MinimalAnswer] = []

        for i, sr in enumerate(
            tqdm(student_results.search_results, desc="Answering")
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
                question=sr.question,
                sources=sources_dicts,
                repo_path=idx.repo_path,
            )
            answered.append(MinimalAnswer(
                question_id=sr.question_id,
                question=sr.question,
                retrieved_sources=sr.retrieved_sources,
                answer=answer_text,
            ))
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1} of "
                      f"{len(student_results.search_results)} questions")

        print(f"Processed {len(answered)} of "
              f"{len(student_results.search_results)} questions")

        output = StudentSearchResultsAndAnswer(
            search_results=answered,
            k=student_results.k,
        )
        os.makedirs(save_directory, exist_ok=True)
        out_filename = os.path.basename(student_search_results_path)
        out_path = os.path.join(save_directory, out_filename)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output.model_dump_json(indent=2))

        print(f"Saved student_search_results_and_answer to {out_path}")

    def evaluate(
        self,
        student_results_path: str,
        dataset_path: str,
        k: int = 10,
        max_context_length: int = 2000,
    ) -> None:
        """Evaluate search results against ground truth using Recall@k.

        Args:
            student_results_path: Path to student search results JSON.
            dataset_path: Path to ground truth dataset JSON.
            k: Maximum number of sources per question to consider.
            max_context_length: Maximum context length per source.
        """
        with open(student_results_path, 'r', encoding='utf-8') as f:
            student_raw = json.load(f)

        with open(dataset_path, 'r', encoding='utf-8') as f:
            gt_raw = json.load(f)

        student_data = StudentSearchResults.model_validate(student_raw)
        gt_dataset = RagDataset.model_validate(gt_raw)

        # Build ground truth lookup by question_id
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
        print(f"Total number of questions: {total_questions}")
        print(f"Total number of questions with sources: {questions_with_sources}")
        print(f"Total number of questions with student sources: "
              f"{questions_with_student}")

        recall_at_k: Dict[int, float] = {}
        for k_val in [1, 3, 5, 10]:
            recall_at_k[k_val] = _compute_recall_at_k(
                student_data.search_results,
                gt_lookup,
                k=k_val,
                max_context_length=max_context_length,
            )

        evaluated = min(len(student_data.search_results), total_questions)
        print("\nEvaluation Results")
        print("=" * 40)
        print(f"Questions evaluated: {evaluated}")
        for k_val in [1, 3, 5, 10]:
            print(f"Recall@{k_val}: {recall_at_k[k_val]:.3f}")


def _overlap_fraction(
    retrieved_start: int, retrieved_end: int,
    gt_start: int, gt_end: int,
) -> float:
    """Compute overlap fraction between a retrieved chunk and a GT source.

    As per the subject specification: a source is considered "found" if
    there is at least 5% overlap. The overlap is measured relative to
    the ground-truth source length (i.e. how much of the GT source
    is covered by the retrieved chunk).

    Args:
        retrieved_start: Start character index of the retrieved chunk.
        retrieved_end: End character index of the retrieved chunk.
        gt_start: Start character index of the ground truth source.
        gt_end: End character index of the ground truth source.

    Returns:
        Fraction of the GT source covered by the retrieved chunk (0.0-1.0).
    """
    overlap_start = max(retrieved_start, gt_start)
    overlap_end = min(retrieved_end, gt_end)
    if overlap_end <= overlap_start:
        return 0.0
    overlap_len = overlap_end - overlap_start
    gt_len = gt_end - gt_start
    if gt_len <= 0:
        return 0.0
    return overlap_len / gt_len


def _source_found(
    retrieved: List[MinimalSource],
    gt_source: MinimalSource,
    k: int,
) -> bool:
    """Check if a ground truth source is found in the top-k retrieved results.

    A source is considered found if there is at least 5% overlap.

    Args:
        retrieved: List of retrieved sources.
        gt_source: The ground truth source to check.
        k: Maximum number of top retrieved sources to consider.

    Returns:
        True if the source is found, False otherwise.
    """
    for src in retrieved[:k]:
        if src.file_path == gt_source.file_path:
            frac = _overlap_fraction(
                src.first_character_index,
                src.last_character_index,
                gt_source.first_character_index,
                gt_source.last_character_index,
            )
            if frac >= 0.05:
                return True
    return False


def _compute_recall_at_k(
    search_results: List[MinimalSearchResults],
    gt_lookup: Dict[str, Any],
    k: int,
    max_context_length: int,
) -> float:
    """Compute the mean Recall@k over all evaluated questions.

    Args:
        search_results: Student search results.
        gt_lookup: Dict mapping question_id to AnsweredQuestion.
        k: Maximum number of retrieved sources to consider.
        max_context_length: Maximum context length (unused here, for compat).

    Returns:
        Mean recall@k as a float between 0 and 1.
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
    """Entry point for the RAG CLI."""
    fire.Fire(RAGSystem)


if __name__ == '__main__':
    main()
