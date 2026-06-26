"""Chunking strategies for different file types.

This module provides intelligent chunking for Python code files
and text/Markdown documentation files, as required by the project.
"""

import ast
import os
from typing import List, Tuple


def chunk_python_file(
    content: str, file_path: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    """Chunk a Python file using AST-based splitting.

    Splits Python files by top-level definitions (functions, classes).
    Falls back to line-based chunking if AST parsing fails.

    Args:
        content: The full text content of the Python file.
        file_path: Path to the file (used for logging only).
        max_chunk_size: Maximum character size per chunk.

    Returns:
        List of tuples (chunk_text, start_char_index, end_char_index).
    """
    chunks: List[Tuple[str, int, int]] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return chunk_text_file(content, max_chunk_size)

    # Collect top-level node boundaries
    boundaries: List[int] = [0]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            # Only top-level (parent is Module)
            for child in ast.iter_child_nodes(tree):
                if child is node:
                    if hasattr(node, 'lineno'):
                        # Convert line number to char index
                        lines = content.split('\n')
                        char_idx = sum(
                            len(lines[i]) + 1 for i in range(node.lineno - 1)
                        )
                        if char_idx > 0 and char_idx not in boundaries:
                            boundaries.append(char_idx)

    boundaries.append(len(content))
    boundaries = sorted(set(boundaries))

    # Create chunks from boundaries
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        chunk_text = content[start:end]

        if not chunk_text.strip():
            continue

        # If chunk is too large, split further
        if len(chunk_text) > max_chunk_size:
            sub_chunks = _split_by_size(chunk_text, start, max_chunk_size)
            chunks.extend(sub_chunks)
        else:
            chunks.append((chunk_text, start, end))

    if not chunks:
        chunks = chunk_text_file(content, max_chunk_size)

    return chunks


def chunk_text_file(
    content: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    """Chunk a text or Markdown file using paragraph-based splitting.

    Splits on double newlines (paragraphs/sections), respecting
    max_chunk_size. Adjacent small paragraphs are merged.

    Args:
        content: The full text content.
        max_chunk_size: Maximum character size per chunk.

    Returns:
        List of tuples (chunk_text, start_char_index, end_char_index).
    """
    chunks: List[Tuple[str, int, int]] = []
    paragraphs: List[Tuple[str, int]] = []

    # Split on double newlines to get paragraphs
    current_idx = 0
    for para in content.split('\n\n'):
        if para.strip():
            paragraphs.append((para, current_idx))
        current_idx += len(para) + 2  # +2 for '\n\n'

    if not paragraphs:
        return [(content, 0, len(content))] if content.strip() else []

    # Merge paragraphs up to max_chunk_size
    current_chunk = ''
    current_start = paragraphs[0][1]

    for para_text, para_start in paragraphs:
        if current_chunk and len(current_chunk) + len(para_text) + 2 > max_chunk_size:
            end = current_start + len(current_chunk)
            chunks.append((current_chunk, current_start, end))
            current_chunk = para_text
            current_start = para_start
        else:
            if current_chunk:
                current_chunk += '\n\n' + para_text
            else:
                current_chunk = para_text
                current_start = para_start

    if current_chunk:
        end = current_start + len(current_chunk)
        chunks.append((current_chunk, current_start, end))

    return chunks


def _split_by_size(
    text: str, base_offset: int, max_chunk_size: int
) -> List[Tuple[str, int, int]]:
    """Split a text block by character size along line boundaries.

    Args:
        text: Text to split.
        base_offset: Character offset of the text in the original file.
        max_chunk_size: Maximum chunk size in characters.

    Returns:
        List of tuples (chunk_text, start_char_index, end_char_index).
    """
    chunks: List[Tuple[str, int, int]] = []
    lines = text.split('\n')
    current = ''
    current_offset = base_offset

    for line in lines:
        if current and len(current) + len(line) + 1 > max_chunk_size:
            end = current_offset + len(current)
            chunks.append((current, current_offset, end))
            current_offset = end + 1  # +1 for newline
            current = line
        else:
            if current:
                current += '\n' + line
            else:
                current = line

    if current:
        end = current_offset + len(current)
        chunks.append((current, current_offset, end))

    return chunks if chunks else [(text, base_offset, base_offset + len(text))]


def get_file_chunks(
    file_path: str, content: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    """Dispatch to the appropriate chunking strategy based on file extension.

    Args:
        file_path: Path to the file, used to determine file type.
        content: Full text content of the file.
        max_chunk_size: Maximum character size per chunk.

    Returns:
        List of tuples (chunk_text, start_char_index, end_char_index).
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.py':
        return chunk_python_file(content, file_path, max_chunk_size)
    else:
        return chunk_text_file(content, max_chunk_size)
