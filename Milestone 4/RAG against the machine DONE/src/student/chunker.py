import ast
import os
from typing import List, Tuple


def _hard_split(
    text: str, base_offset: int, max_chunk_size: int
) -> List[Tuple[str, int, int]]:
    chunks: List[Tuple[str, int, int]] = []
    pos = 0
    while pos < len(text):
        end = min(pos + max_chunk_size, len(text))
        chunk = text[pos:end]
        if chunk.strip():
            chunks.append((chunk, base_offset + pos, base_offset + end))
        pos = end
    return chunks


def _split_by_size(
    text: str, base_offset: int, max_chunk_size: int
) -> List[Tuple[str, int, int]]:
    chunks: List[Tuple[str, int, int]] = []
    lines = text.split('\n')
    current = ''
    current_offset = base_offset

    for line in lines:
        if len(line) > max_chunk_size:
            if current.strip():
                end = current_offset + len(current)
                chunks.append((current, current_offset, end))
                current_offset = end + 1
                current = ''
            line_offset = current_offset
            chunks.extend(_hard_split(line, line_offset, max_chunk_size))
            current_offset = line_offset + len(line) + 1
            continue

        if current and len(current) + len(line) + 1 > max_chunk_size:
            end = current_offset + len(current)
            chunks.append((current, current_offset, end))
            current_offset = end + 1
            current = line
        else:
            if current:
                current += '\n' + line
            else:
                current = line

    if current.strip():
        end = current_offset + len(current)
        chunks.append((current, current_offset, end))

    return chunks if chunks else _hard_split(text, base_offset, max_chunk_size)


def _enforce_max_size(
    chunks: List[Tuple[str, int, int]], max_chunk_size: int
) -> List[Tuple[str, int, int]]:
    result: List[Tuple[str, int, int]] = []
    for chunk_text, start, end in chunks:
        if len(chunk_text) <= max_chunk_size:
            result.append((chunk_text, start, end))
        else:
            result.extend(_hard_split(chunk_text, start, max_chunk_size))
    return result


def chunk_python_file(
    content: str, file_path: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return _enforce_max_size(
            chunk_text_file(content, max_chunk_size),
            max_chunk_size,
        )

    lines = content.splitlines(keepends=True)

    # Character offsets of top-level class/function definitions.
    boundaries: List[int] = [0]

    offset = 0
    line_offsets: List[int] = []
    for line in lines:
        line_offsets.append(offset)
        offset += len(line)

    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            if node.lineno > 0:
                start = line_offsets[node.lineno - 1]
                if start not in boundaries:
                    boundaries.append(start)

    boundaries.append(len(content))
    boundaries = sorted(set(boundaries))

    chunks: List[Tuple[str, int, int]] = []

    for start, end in zip(boundaries, boundaries[1:]):
        chunk_text = content[start:end]

        if not chunk_text.strip():
            continue

        if len(chunk_text) <= max_chunk_size:
            chunks.append((chunk_text, start, end))
        else:
            chunks.extend(
                _split_by_size(
                    chunk_text,
                    start,
                    max_chunk_size,
                )
            )

    if not chunks:
        return chunk_text_file(content, max_chunk_size)

    return _enforce_max_size(chunks, max_chunk_size)


def chunk_text_file(
    content: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    chunks: List[Tuple[str, int, int]] = []
    paragraphs: List[Tuple[str, int]] = []

    current_idx = 0
    for para in content.split('\n\n'):
        if para.strip():
            paragraphs.append((para, current_idx))
        current_idx += len(para) + 2

    if not paragraphs:
        return _enforce_max_size(
            [(content, 0, len(content))] if content.strip() else [],
            max_chunk_size,
        )

    current_chunk = ''
    current_start = paragraphs[0][1]

    for para_text, para_start in paragraphs:
        if len(para_text) > max_chunk_size:
            if current_chunk.strip():
                end = current_start + len(current_chunk)
                chunks.append((current_chunk, current_start, end))
                current_chunk = ''
            chunks.extend(
                _split_by_size(para_text, para_start, max_chunk_size)
            )
            current_start = para_start + len(para_text) + 2
            continue

        if (
            current_chunk
            and len(current_chunk) + len(para_text) + 2 > max_chunk_size
        ):
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

    if current_chunk.strip():
        end = current_start + len(current_chunk)
        chunks.append((current_chunk, current_start, end))

    return _enforce_max_size(chunks, max_chunk_size)


def get_file_chunks(
    file_path: str, content: str, max_chunk_size: int = 2000
) -> List[Tuple[str, int, int]]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.py':
        return chunk_python_file(content, file_path, max_chunk_size)
    return chunk_text_file(content, max_chunk_size)
