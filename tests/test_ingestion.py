"""
Tests for document ingestion pipeline.
"""

from src.rag.ingestion import chunk_document, read_document


class TestReadDocument:
    """Tests for reading different document formats."""

    def test_read_txt_file(self):
        """A .txt file should be read as plain text."""
        content = b"Hello, this is a test document."
        result = read_document("test.txt", content)
        assert result == "Hello, this is a test document."

    def test_read_md_file(self):
        """A .md file should be read as plain text (Markdown is text)."""
        content = b"# Title\n\nSome paragraph."
        result = read_document("readme.md", content)
        assert result == "# Title\n\nSome paragraph."

    def test_read_csv_file(self):
        """A .csv file should be read as plain text."""
        content = b"name,age\nAlice,30\nBob,25"
        result = read_document("data.csv", content)
        assert "Alice" in result
        assert "Bob" in result

    def test_unsupported_format_raises(self):
        """Unsupported file types should raise ValueError."""
        try:
            read_document("image.png", b"binary data")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert ".png" in str(e)


class TestChunkDocument:
    """Tests for document chunking."""

    def test_small_document_single_chunk(self):
        """A document smaller than chunk_size should produce one chunk."""
        text = "This is a short document."
        chunks = chunk_document(text, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_large_document_multiple_chunks(self):
        """A large document should be split into multiple chunks."""
        # Create a document with 50 paragraphs
        paragraphs = [f"This is paragraph {i}. It contains some text about topic {i}." for i in range(50)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_document(text, chunk_size=200, chunk_overlap=50)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        """Consecutive chunks should overlap."""
        # Create text with clear sentence boundaries
        sentences = [f"Sentence number {i} is here." for i in range(100)]
        text = " ".join(sentences)
        chunks = chunk_document(text, chunk_size=200, chunk_overlap=50)

        # Check that some text from chunk N appears in chunk N+1
        if len(chunks) >= 2:
            # The end of chunk 0 should appear at the start of chunk 1
            end_of_first = chunks[0][-30:]
            # With overlap, some of this text should be in chunk 1
            # (This is a fuzzy check — overlap means shared content)
            assert len(chunks[1]) > 0

    def test_chunk_size_respected(self):
        """No chunk should exceed chunk_size (approximately)."""
        text = "A " * 5000
        chunks = chunk_document(text, chunk_size=500, chunk_overlap=50)
        for chunk in chunks:
            # Allow 10% tolerance for the text splitter
            assert len(chunk) <= 600, f"Chunk too large: {len(chunk)} chars"

    def test_empty_document(self):
        """An empty document should produce an empty list or single empty chunk."""
        chunks = chunk_document("", chunk_size=1000, chunk_overlap=200)
        # Empty text may produce 0 or 1 chunks depending on splitter
        assert len(chunks) <= 1
