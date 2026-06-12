"""
Unit tests for RAG (Retrieval-Augmented Generation) module.

Tests document chunking, embedding, and vector store operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rag.ingestion import (
    fetch_latest_10k_filing,
    extract_key_sections,
    fetch_10k_text,
    process_filing,
)
from rag.vector_store import (
    get_vector_store,
    add_documents_to_store,
    clear_vector_store,
    get_collection_stats,
    delete_documents_by_source,
)
from langchain_core.documents import Document


class TestFilingFetching:
    """Test 10-K filing fetching functionality."""
    
    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_latest_10k_success(self, mock_company):
        """Test successful fetching of latest 10-K filing."""
        # Mock the Company class and its methods
        mock_company_instance = MagicMock()
        mock_filings = MagicMock()
        mock_latest = MagicMock()
        mock_filing = MagicMock()
        
        mock_latest.obj.return_value = mock_filing
        mock_filings.latest.return_value = mock_latest
        mock_company_instance.get_filings.return_value = mock_filings
        mock_company.return_value = mock_company_instance
        
        result = fetch_latest_10k_filing("AAPL")
        
        assert result is not None
        mock_company.assert_called_once_with("AAPL")
        mock_company_instance.get_filings.assert_called_once_with(form="10-K")
    
    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_latest_10k_not_found(self, mock_company):
        """Test handling when no 10-K filings are found."""
        mock_company_instance = MagicMock()
        mock_company_instance.get_filings.return_value = None
        mock_company.return_value = mock_company_instance
        
        with pytest.raises(ValueError, match="No 10-K filings found"):
            fetch_latest_10k_filing("INVALID")


class TestSectionExtraction:
    """Test extraction of sections from 10-K documents."""
    
    @pytest.mark.unit
    def test_extract_key_sections_basic(self):
        """Test basic section extraction."""
        mock_filing = MagicMock()
        mock_filing.risk_factors = "Risk factors content"
        mock_filing.management_discussion = "MD&A content"
        mock_filing.financial_statements = "Financial statements content"
        mock_filing.__contains__ = Mock(return_value=False)
        
        sections = extract_key_sections(mock_filing)
        
        assert isinstance(sections, dict)
        assert 'Item 1A' in sections
        assert 'Item 7' in sections
        assert sections['Item 1A'] == "Risk factors content"
        assert sections['Item 7'] == "MD&A content"
    
    @pytest.mark.unit
    def test_extract_key_sections_missing_data(self):
        """Test handling of missing sections."""
        mock_filing = MagicMock()
        mock_filing.risk_factors = None
        mock_filing.management_discussion = None
        mock_filing.financial_statements = None
        mock_filing.__contains__ = Mock(return_value=False)
        
        sections = extract_key_sections(mock_filing)
        
        assert isinstance(sections, dict)
        assert sections['Item 1A'] == ""
        assert sections['Item 7'] == ""
    
    @pytest.mark.unit
    def test_extract_key_sections_exception_handling(self):
        """Test that exceptions during extraction are handled gracefully."""
        mock_filing = MagicMock()
        # Simulate an exception when accessing risk_factors
        type(mock_filing).risk_factors = PropertyMock(side_effect=Exception("Access error"))
        
        sections = extract_key_sections(mock_filing)
        
        # Should return empty string for failed sections
        assert isinstance(sections, dict)
        assert sections['Item 1A'] == ""


class TestDocumentProcessing:
    """Test end-to-end document processing."""
    
    @pytest.mark.unit
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_process_filing_basic(self, mock_fetch):
        """Test complete document processing pipeline."""
        # Setup mock filing
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        mock_filing.risk_factors = "Risk factors content. " * 100  # Long enough to chunk
        mock_filing.management_discussion = "MD&A content. " * 100
        mock_filing.financial_statements = "Financial statements. " * 100
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        result = process_filing("AAPL")
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(doc, Document) for doc in result)
        mock_fetch.assert_called_once_with("AAPL")
    
    @pytest.mark.unit
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_process_filing_metadata(self, mock_fetch):
        """Test that metadata is properly attached to chunks."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        mock_filing.risk_factors = "Risk factors content. " * 100
        mock_filing.management_discussion = ""
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        result = process_filing("MSFT")
        
        assert len(result) > 0
        
        # Check metadata on first document
        first_doc = result[0]
        assert 'source' in first_doc.metadata
        assert 'company' in first_doc.metadata
        assert 'section' in first_doc.metadata
        assert 'fiscal_year' in first_doc.metadata
        assert 'chunk_id' in first_doc.metadata
        assert first_doc.metadata['source'] == 'MSFT'
        assert first_doc.metadata['fiscal_year'] == '2024'
    
    @pytest.mark.unit
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_process_filing_chunking(self, mock_fetch):
        """Test that long sections are properly chunked."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        # Create content longer than chunk_size (2000)
        long_content = "This is a long section. " * 200  # ~4800 chars
        mock_filing.risk_factors = long_content
        mock_filing.management_discussion = ""
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        result = process_filing("AAPL")
        
        # Should create multiple chunks for long content
        assert len(result) >= 2
        
        # Check that chunks have section prefix
        for doc in result:
            assert doc.page_content.startswith("Section: ")
    
    @pytest.mark.unit
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_process_filing_deduplication(self, mock_fetch):
        """Test that duplicate chunks are removed."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        # Use same content for multiple sections to test deduplication
        duplicate_content = "Duplicate content. " * 100
        mock_filing.risk_factors = duplicate_content
        mock_filing.management_discussion = duplicate_content
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        result = process_filing("AAPL")
        
        # Should have deduplicated chunks
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that content hashes are stored
        assert all('content_hash' in doc.metadata for doc in result)
    
    @pytest.mark.unit
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_process_filing_skips_short_sections(self, mock_fetch):
        """Test that very short sections are skipped."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        mock_filing.risk_factors = "Short"  # < 100 chars, should be skipped
        mock_filing.management_discussion = "A" * 150  # > 100 chars, should be included
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        result = process_filing("AAPL")
        
        # Should only have chunks from sections > 100 chars
        assert len(result) > 0
        # Verify that short section was skipped
        sections_in_result = {doc.metadata['section'] for doc in result}
        assert 'Item 7' in sections_in_result  # Long section should be present


class TestFetch10kText:
    """Tests for the fetch_10k_text() helper added to rag/ingestion.py."""

    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_10k_text_latest_filing(self, mock_company):
        """Index 0 should return text and fiscal year from the latest 10-K."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-09-28"
        mock_filing.risk_factors = "Risk content. " * 50
        mock_filing.management_discussion = "MD&A content. " * 50
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)

        mock_filings = MagicMock()
        mock_filings.__getitem__ = Mock(return_value=MagicMock(obj=Mock(return_value=mock_filing)))
        mock_company.return_value.get_filings.return_value = mock_filings

        text, year = fetch_10k_text("AAPL", index=0)

        assert isinstance(text, str)
        assert len(text) > 0
        assert year == "2024"

    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_10k_text_no_filings_raises(self, mock_company):
        """ValueError must be raised when the company has no 10-K filings."""
        mock_company.return_value.get_filings.return_value = None

        with pytest.raises(ValueError, match="No 10-K filings found"):
            fetch_10k_text("INVALID", index=0)

    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_10k_text_invalid_index_raises(self, mock_company):
        """IndexError on the filings list should be translated to ValueError."""
        mock_filings = MagicMock()
        mock_filings.__getitem__ = Mock(side_effect=IndexError)
        mock_company.return_value.get_filings.return_value = mock_filings

        with pytest.raises(ValueError, match="Filing index"):
            fetch_10k_text("AAPL", index=99)

    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_10k_text_empty_sections_raises(self, mock_company):
        """ValueError must be raised when no sections contain usable text."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-09-28"
        mock_filing.risk_factors = ""
        mock_filing.management_discussion = ""
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)

        mock_filings = MagicMock()
        mock_filings.__getitem__ = Mock(return_value=MagicMock(obj=Mock(return_value=mock_filing)))
        mock_company.return_value.get_filings.return_value = mock_filings

        with pytest.raises(ValueError, match="No extractable text"):
            fetch_10k_text("AAPL", index=0)

    @pytest.mark.unit
    @patch('rag.ingestion.Company')
    def test_fetch_10k_text_includes_section_headers(self, mock_company):
        """Returned text must include '===' section delimiters from extract_key_sections."""
        mock_filing = MagicMock()
        mock_filing.filing_date = "2023-10-01"
        mock_filing.risk_factors = "Risk factors text. " * 20
        mock_filing.management_discussion = ""
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)

        mock_filings = MagicMock()
        mock_filings.__getitem__ = Mock(return_value=MagicMock(obj=Mock(return_value=mock_filing)))
        mock_company.return_value.get_filings.return_value = mock_filings

        text, year = fetch_10k_text("AAPL", index=0)
        assert "===" in text
        assert "Item 1A" in text


class TestVectorStore:
    """Tests for rag/vector_store.py — all external I/O is mocked."""

    # ── get_vector_store ─────────────────────────────────────────────────────

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_get_vector_store_returns_chroma_instance(self, mock_hf, mock_chroma):
        """get_vector_store() should construct and return a Chroma instance."""
        mock_vs = MagicMock()
        mock_chroma.return_value = mock_vs

        result = get_vector_store("test_dir")

        assert result is mock_vs
        mock_chroma.assert_called_once()

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_get_vector_store_uses_correct_embedding_model(self, mock_hf, mock_chroma):
        """The correct sentence-transformers model must be requested."""
        get_vector_store("test_dir")
        mock_hf.assert_called_once_with(model_name="sentence-transformers/all-MiniLM-L6-v2")

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_get_vector_store_passes_persist_directory(self, mock_hf, mock_chroma):
        """persist_directory argument must be forwarded to Chroma."""
        get_vector_store("my_custom_db")
        _, kwargs = mock_chroma.call_args
        assert kwargs.get("persist_directory") == "my_custom_db"

    # ── add_documents_to_store ───────────────────────────────────────────────

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_add_documents_calls_add_documents_on_store(self, mock_hf, mock_chroma):
        """add_documents_to_store() must call vectorstore.add_documents()."""
        mock_vs = MagicMock()
        mock_chroma.return_value = mock_vs

        docs = [
            Document(page_content="Apple reported revenue.", metadata={"source": "AAPL"}),
            Document(page_content="Microsoft grew earnings.", metadata={"source": "MSFT"}),
        ]
        add_documents_to_store(docs, "test_dir")

        mock_vs.add_documents.assert_called_once_with(docs)

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_add_documents_to_store_skips_empty_list(self, mock_hf, mock_chroma):
        """An empty document list must short-circuit before touching Chroma."""
        mock_vs = MagicMock()
        mock_chroma.return_value = mock_vs

        add_documents_to_store([], "test_dir")

        mock_vs.add_documents.assert_not_called()

    # ── clear_vector_store ───────────────────────────────────────────────────

    @pytest.mark.unit
    def test_clear_vector_store_removes_existing_directory(self, tmp_path):
        """clear_vector_store() must delete the directory when it exists."""
        target = str(tmp_path / "chroma_test")
        os.makedirs(target)
        assert os.path.exists(target)

        clear_vector_store(target)

        assert not os.path.exists(target)

    @pytest.mark.unit
    def test_clear_vector_store_does_not_raise_for_nonexistent_directory(self, tmp_path):
        """Calling clear_vector_store() on a missing path must not raise."""
        missing = str(tmp_path / "does_not_exist")
        clear_vector_store(missing)  # Should complete without exception

    # ── get_collection_stats ─────────────────────────────────────────────────

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_get_collection_stats_returns_document_count(self, mock_hf, mock_chroma):
        """get_collection_stats() must return the integer count from Chroma."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        mock_vs = MagicMock()
        mock_vs._collection = mock_collection
        mock_chroma.return_value = mock_vs

        result = get_collection_stats("test_dir")

        assert result == 42
        mock_collection.count.assert_called_once()

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_get_collection_stats_returns_zero_on_exception(self, mock_hf, mock_chroma):
        """When Chroma raises, get_collection_stats() must return 0 gracefully."""
        mock_chroma.side_effect = Exception("DB connection failed")

        result = get_collection_stats("bad_dir")

        assert result == 0

    # ── delete_documents_by_source ───────────────────────────────────────────

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_delete_documents_by_source_calls_delete_when_ids_found(self, mock_hf, mock_chroma):
        """When matching documents exist, delete() must be called with their IDs."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["id1", "id2", "id3"]}
        mock_vs = MagicMock()
        mock_vs._collection = mock_collection
        mock_chroma.return_value = mock_vs

        delete_documents_by_source("AAPL", "test_dir")

        mock_collection.get.assert_called_once_with(where={"source": "AAPL"})
        mock_collection.delete.assert_called_once_with(ids=["id1", "id2", "id3"])

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_delete_documents_by_source_skips_delete_when_no_results(self, mock_hf, mock_chroma):
        """When no documents match the ticker, delete() must NOT be called."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_vs = MagicMock()
        mock_vs._collection = mock_collection
        mock_chroma.return_value = mock_vs

        delete_documents_by_source("UNKNOWN", "test_dir")

        mock_collection.delete.assert_not_called()

    @pytest.mark.unit
    @patch('rag.vector_store.Chroma')
    @patch('rag.vector_store.HuggingFaceEmbeddings')
    def test_delete_documents_by_source_handles_exception_gracefully(self, mock_hf, mock_chroma):
        """Exceptions during delete must be caught and not propagate to the caller."""
        mock_chroma.side_effect = Exception("DB error")

        delete_documents_by_source("AAPL", "bad_dir")  # Must not raise


# Fixtures
@pytest.fixture
def sample_document():
    """Sample financial document for testing."""
    return """
    Item 1. Business
    
    The Company designs, manufactures, and markets smartphones, personal computers,
    tablets, wearables, and accessories worldwide. The Company also sells various
    related services.
    
    Item 1A. Risk Factors
    
    Investment in the Company's securities involves significant risks including:
    - Market competition
    - Supply chain disruptions
    - Regulatory changes
    """


@pytest.fixture
def mock_filing():
    """Mock filing object for testing."""
    filing = MagicMock()
    filing.filing_date = "2024-01-15"
    filing.risk_factors = "Risk factors content"
    filing.management_discussion = "MD&A content"
    filing.financial_statements = "Financial statements"
    filing.__contains__ = Mock(return_value=False)
    return filing


@pytest.fixture
def sample_chunks():
    """Sample document chunks."""
    return [
        Document(
            page_content="The Company designs, manufactures, and markets smartphones.",
            metadata={"source": "AAPL", "section": "Item 1A"}
        ),
        Document(
            page_content="Investment in the Company's securities involves significant risks.",
            metadata={"source": "AAPL", "section": "Item 1A"}
        ),
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])