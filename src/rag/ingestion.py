"""
Document Ingestion Pipeline

Handles:
    1. Reading document content (PDF, TXT, MD, CSV, DOCX)
    2. Splitting documents into chunks
    3. Generating embeddings for each chunk

Why chunk documents?
    - LLMs have a context window limit (e.g. 200K tokens for Claude)
    - Smaller chunks are more precise — the LLM gets exactly the relevant part
    - Embedding models work best on paragraph-sized text (not whole documents)
    - Smaller chunks = more targeted retrieval = better answers

Chunking strategy:
    - We use "recursive character text splitter" from LangChain
    - It splits on: paragraph breaks → sentence breaks → word breaks
    - Each chunk has overlap with the next (so sentences aren't cut in half)
"""

import io
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger


def read_document(filename: str, content: bytes) -> str:
    """
    Read document content based on file extension.

    Supports: .pdf, .txt, .md, .csv, .docx

    Args:
        filename: Original filename (used to detect format).
        content: Raw file bytes.

    Returns:
        Extracted text content as a string.
    """
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return _read_pdf(content)
    elif extension in (".txt", ".md", ".csv"):
        return content.decode("utf-8", errors="replace")
    elif extension == ".docx":
        return _read_docx(content)
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def _read_pdf(content: bytes) -> str:
    """
    Extract text from a PDF file.

    Uses pypdf — a pure Python PDF library (no system dependencies).
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    text_parts = []
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(f"[Page {page_num}]\n{page_text}")
    return "\n\n".join(text_parts)


def _read_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())


def chunk_document(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split document text into overlapping chunks.

    Args:
        text: The full document text.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Characters of overlap between consecutive chunks.

    Returns:
        List of text chunks.

    Example:
        text = "Alice went to the store. She bought milk. Then she went home. ..."

        With chunk_size=50, chunk_overlap=10:
        Chunk 1: "Alice went to the store. She bought milk."
        Chunk 2: "bought milk. Then she went home."
                   ^^^^^^^^^^^ overlap
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)
    logger.info(f"Document split into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks
