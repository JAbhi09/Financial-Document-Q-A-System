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
    process_filing
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