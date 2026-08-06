"""Chinese-aware text chunker using RecursiveCharacterTextSplitter."""

from dataclasses import dataclass, field
from typing import Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Chinese punctuation hierarchy for clean chunk boundaries
CHINESE_SEPARATORS = [
    "\n\n",     # paragraph break
    "\n",       # line break
    "。",       # Chinese period
    "！",       # Chinese exclamation
    "？",       # Chinese question mark
    "；",       # Chinese semicolon
    "，",       # Chinese comma
    "、",       # Chinese enumeration comma
    " ",        # space
    "",         # character-level (last resort)
]


@dataclass
class Chunk:
    """A single text chunk with metadata."""
    text: str
    chunk_index: int
    file_id: int
    title: str
    department: str
    date: str

    # Stored as metadata, used to reconstruct citations
    metadata: dict = field(default_factory=dict)


def chunk_text(
    text: str,
    file_id: int,
    title: str,
    department: str = "",
    date: str = "",
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """
    Split text into overlapping chunks using Chinese-aware separators.

    Args:
        text: Clean plain text to split.
        file_id: The gxu-wjxt file ID this text came from.
        title: File title (for citation).
        department: Issuing department.
        date: File date (YYYY-MM-DD).
        chunk_size: Max characters per chunk.
        chunk_overlap: Overlap between adjacent chunks.

    Returns:
        List of Chunk objects, each with metadata for citation.
    """
    splitter = RecursiveCharacterTextSplitter(
        separators=CHINESE_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )

    chunks: list[Chunk] = []
    texts = splitter.split_text(text)

    # Build heading hierarchy from text structure
    heading_stack = _extract_heading_stack(text)

    for i, chunk_text in enumerate(texts):
        # Find which headings are relevant for this chunk
        heading = _find_heading_for_chunk(chunk_text, heading_stack)

        chunks.append(Chunk(
            text=chunk_text,
            chunk_index=i,
            file_id=file_id,
            title=title,
            department=department,
            date=date,
            metadata={
                "file_id": file_id,
                "title": title,
                "department": department,
                "date": date,
                "chunk_index": i,
                "heading": heading,
            },
        ))

    return chunks


def _extract_heading_stack(text: str) -> list[tuple[str, str]]:
    """
    Extract lines that look like headings and return (heading_text, content_start).
    Simple heuristic: lines that are short, don't end with punctuation.
    """
    headings = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) <= 40 and not stripped[-1] in "。！？；，、.":
            headings.append((stripped, i))
    return headings


def _find_heading_for_chunk(chunk_text: str, heading_stack: list[tuple[str, str]]) -> str:
    """Return the most recent heading before this chunk, or empty string."""
    # Simple approach: return the first heading-like line in the chunk
    lines = chunk_text.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) <= 40 and not stripped[-1] in "。！？；，、.":
            return stripped
    return ""
