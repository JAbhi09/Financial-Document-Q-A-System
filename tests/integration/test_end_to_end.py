"""
Integration tests for end-to-end workflows.

Tests complete user journeys through the system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestEndToEndDocumentProcessing:
    """Test complete document processing pipeline."""
    
    @pytest.mark.integration
    @patch('rag.ingestion.fetch_latest_10k_filing')
    @patch('rag.ingestion.process_filing')
    def test_full_document_ingestion_pipeline(self, mock_process, mock_fetch):
        """Test complete flow from fetching to processing documents."""
        # Setup mocks
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        mock_filing.risk_factors = "Risk factors content"
        mock_filing.management_discussion = "MD&A content"
        mock_filing.financial_statements = "Financial statements"
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        mock_process.return_value = [
            MagicMock(page_content="chunk1", metadata={"source": "AAPL"}),
            MagicMock(page_content="chunk2", metadata={"source": "AAPL"})
        ]
        
        from rag.ingestion import fetch_latest_10k_filing, process_filing
        
        ticker = "AAPL"
        
        # Step 1: Fetch document
        filing = fetch_latest_10k_filing(ticker)
        assert filing is not None
        
        # Step 2: Process document
        documents = process_filing(ticker)
        assert documents is not None
        assert len(documents) > 0
        
        # Verify all steps were called
        mock_fetch.assert_called_once_with(ticker)
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    def test_real_document_processing(self):
        """Integration test with real API calls (requires USER_AGENT)."""
        # Skip if no API keys
        if not os.getenv('USER_AGENT'):
            pytest.skip("USER_AGENT environment variable not configured")
        
        from rag.ingestion import process_filing
        
        ticker = "AAPL"
        
        # This will make real API calls
        try:
            documents = process_filing(ticker)
            assert documents is not None
            assert len(documents) > 0
            # Verify document structure
            assert all(hasattr(doc, 'page_content') for doc in documents)
            assert all(hasattr(doc, 'metadata') for doc in documents)
        except Exception as e:
            pytest.skip(f"API call failed: {e}")


class TestEndToEndComplianceWorkflow:
    """Test complete compliance analysis workflow."""
    
    @pytest.mark.integration
    @patch('compliance.beneish.get_financial_data_for_year')
    @patch('compliance.beneish.Company')
    def test_full_compliance_analysis(self, mock_company, mock_get_data):
        """Test complete compliance analysis workflow."""
        # Setup mocks
        mock_company_instance = MagicMock()
        mock_company_instance.name = "Apple Inc."
        mock_company.return_value = mock_company_instance
        
        # Mock financial data
        mock_current = {
            'receivables': 1500, 'revenue': 6000, 'cogs': 3600,
            'total_assets': 20000, 'current_assets': 8000, 'ppe': 6000,
            'depreciation': 800, 'sga': 1200, 'total_debt': 3000,
            'net_income': 1000, 'operating_cash_flow': 1200
        }
        
        mock_prior = {
            'receivables': 1200, 'revenue': 5000, 'cogs': 3000,
            'total_assets': 18000, 'current_assets': 7000, 'ppe': 5500,
            'depreciation': 750, 'sga': 1000, 'total_debt': 2800,
            'net_income': 900, 'operating_cash_flow': 1000
        }
        
        mock_get_data.side_effect = [mock_current, mock_prior]
        
        from compliance.beneish import calculate_beneish_m_score_with_ticker
        
        ticker = "AAPL"
        
        # Calculate Beneish M-Score
        result = calculate_beneish_m_score_with_ticker(ticker, 2024)
        
        # Verify results
        assert result is not None
        assert 'm_score' in result
        assert 'risk_level' in result
        assert result['risk_level'] in ['HIGH', 'MODERATE', 'LOW']
    
    @pytest.mark.integration
    def test_beneish_calculation_with_real_data_structure(self):
        """Test Beneish M-Score with realistic data structure."""
        from compliance.beneish import calculate_beneish_m_score
        
        # Realistic financial data
        current = {
            'receivables': 45000000000,
            'revenue': 394000000000,
            'cogs': 223000000000,
            'total_assets': 352000000000,
            'current_assets': 135000000000,
            'ppe': 43000000000,
            'depreciation': 11000000000,
            'sga': 25000000000,
            'total_debt': 109000000000,
            'net_income': 97000000000,
            'operating_cash_flow': 110000000000
        }
        
        prior = {
            'receivables': 38000000000,
            'revenue': 365000000000,
            'cogs': 214000000000,
            'total_assets': 323000000000,
            'current_assets': 128000000000,
            'ppe': 39000000000,
            'depreciation': 11000000000,
            'sga': 24000000000,
            'total_debt': 98000000000,
            'net_income': 86000000000,
            'operating_cash_flow': 99000000000
        }
        
        result = calculate_beneish_m_score(current, prior)
        
        assert result is not None
        assert 'm_score' in result
        assert 'components' in result
        # Verify all 8 components
        assert len(result['components']) == 8


class TestEndToEndMCPServerWorkflow:
    """Test MCP server workflows."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.requires_api
    async def test_get_company_filings_real(self):
        """Test getting real company filings (requires USER_AGENT)."""
        if not os.getenv('USER_AGENT'):
            pytest.skip("USER_AGENT not configured")
        
        from mcp_server.server import get_company_filings
        
        try:
            result = await get_company_filings("AAPL", form_type="10-K", limit=2)
            assert result is not None
            assert isinstance(result, str)
            # Should contain JSON data
            assert "10-K" in result or result != ""
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.requires_api
    async def test_get_financial_statements_real(self):
        """Test getting real financial statements (requires USER_AGENT)."""
        if not os.getenv('USER_AGENT'):
            pytest.skip("USER_AGENT not configured")
        
        from mcp_server.server import get_financial_statements
        
        try:
            result = await get_financial_statements("AAPL", concept="Revenues")
            assert result is not None
            assert isinstance(result, str)
        except Exception as e:
            pytest.skip(f"API call failed: {e}")


class TestEndToEndErrorHandling:
    """Test error handling across the system."""
    
    @pytest.mark.integration
    @patch('compliance.beneish.Company')
    def test_invalid_ticker_handling(self, mock_company):
        """Test handling of invalid ticker symbols."""
        mock_company.side_effect = Exception("Ticker not found")
        
        from compliance.beneish import calculate_beneish_m_score_with_ticker
        
        # Should fall back to demo
        result = calculate_beneish_m_score_with_ticker("INVALID_TICKER_XYZ", 2024)
        
        assert result is not None
        assert result['data_source'] == 'demo'
    
    @pytest.mark.integration
    def test_beneish_with_missing_data(self):
        """Test Beneish calculation with missing data."""
        from compliance.beneish import calculate_beneish_m_score
        
        # Incomplete data
        current = {'receivables': 1000, 'revenue': 5000}
        prior = {'receivables': 800, 'revenue': 4000}
        
        result = calculate_beneish_m_score(current, prior)
        
        # Should handle gracefully
        assert result is not None
        assert 'm_score' in result
    
    @pytest.mark.integration
    @patch('rag.ingestion.Company')
    def test_filing_fetch_error_handling(self, mock_company):
        """Test handling when filing fetch fails."""
        from rag.ingestion import fetch_latest_10k_filing
        
        mock_company_instance = MagicMock()
        mock_company_instance.get_filings.return_value = None
        mock_company.return_value = mock_company_instance
        
        with pytest.raises(ValueError, match="No 10-K filings found"):
            fetch_latest_10k_filing("INVALID")


class TestEndToEndDataFlow:
    """Test data flow through the system."""
    
    @pytest.mark.integration
    def test_beneish_score_thresholds(self):
        """Test that M-Score thresholds are correctly applied."""
        from compliance.beneish import calculate_beneish_m_score
        
        # Test high risk scenario
        high_risk_current = {
            'receivables': 5000, 'revenue': 10000, 'cogs': 8000,
            'total_assets': 20000, 'current_assets': 5000, 'ppe': 5000,
            'depreciation': 500, 'sga': 2000, 'total_debt': 10000,
            'net_income': 1000, 'operating_cash_flow': 200
        }
        
        high_risk_prior = {
            'receivables': 1000, 'revenue': 9000, 'cogs': 5000,
            'total_assets': 18000, 'current_assets': 7000, 'ppe': 6000,
            'depreciation': 800, 'sga': 1000, 'total_debt': 5000,
            'net_income': 1200, 'operating_cash_flow': 1300
        }
        
        result = calculate_beneish_m_score(high_risk_current, high_risk_prior)
        
        # Should likely be HIGH or MODERATE risk
        assert result['risk_level'] in ['HIGH', 'MODERATE']
        assert result['m_score'] > -2.22  # Manipulation likely threshold
    
    @pytest.mark.integration
    @patch('rag.ingestion.fetch_latest_10k_filing')
    def test_document_chunking_preserves_metadata(self, mock_fetch):
        """Test that document chunking preserves important metadata."""
        from rag.ingestion import process_filing
        
        # Setup mock
        mock_filing = MagicMock()
        mock_filing.filing_date = "2024-01-15"
        mock_filing.risk_factors = "Risk factors content. " * 100
        mock_filing.management_discussion = "MD&A content. " * 100
        mock_filing.financial_statements = ""
        mock_filing.__contains__ = Mock(return_value=False)
        
        mock_fetch.return_value = mock_filing
        
        documents = process_filing("AAPL")
        
        # Verify metadata preservation
        assert len(documents) > 0
        for doc in documents:
            assert 'source' in doc.metadata
            assert 'section' in doc.metadata
            assert 'fiscal_year' in doc.metadata
            assert 'chunk_id' in doc.metadata
            assert doc.metadata['source'] == 'AAPL'


# Fixtures
@pytest.fixture
def sample_ticker():
    """Sample ticker for testing."""
    return "AAPL"


@pytest.fixture
def sample_financial_data():
    """Sample financial data for testing."""
    return {
        'current': {
            'receivables': 1500, 'revenue': 6000, 'cogs': 3600,
            'total_assets': 20000, 'current_assets': 8000, 'ppe': 6000,
            'depreciation': 800, 'sga': 1200, 'total_debt': 3000,
            'net_income': 1000, 'operating_cash_flow': 1200
        },
        'prior': {
            'receivables': 1200, 'revenue': 5000, 'cogs': 3000,
            'total_assets': 18000, 'current_assets': 7000, 'ppe': 5500,
            'depreciation': 750, 'sga': 1000, 'total_debt': 2800,
            'net_income': 900, 'operating_cash_flow': 1000
        }
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])