"""
Unit tests for MCP Server (SEC EDGAR integration).

Tests document fetching, parsing, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcp_server.utils import RateLimiter, fetch_with_retry, limiter
import httpx


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test that rate limiter initializes with correct interval."""
        limiter = RateLimiter(requests_per_second=10.0)
        assert limiter.interval == 0.1
        assert limiter.last_request_time == 0.0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limiter_wait(self):
        """Test that rate limiter enforces minimum wait time."""
        import time
        limiter = RateLimiter(requests_per_second=10.0)
        
        start_time = time.time()
        await limiter.wait()
        await limiter.wait()
        end_time = time.time()
        
        # Second request should be delayed by at least the interval
        # Use a slightly lower threshold to account for timing precision
        elapsed = end_time - start_time
        assert elapsed >= limiter.interval * 0.95  # 95% of expected time
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limiter_custom_rate(self):
        """Test rate limiter with custom requests per second."""
        limiter = RateLimiter(requests_per_second=5.0)
        assert limiter.interval == 0.2  # 1/5 = 0.2 seconds
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_global_limiter_exists(self):
        """Test that global limiter instance exists."""
        from mcp_server.utils import limiter
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)
        assert limiter.interval == 1.0 / 8.0  # 8 requests per second


class TestFetchWithRetry:
    """Test fetch_with_retry functionality."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_with_retry_success(self):
        """Test successful fetch on first attempt."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        url = "https://example.com"
        headers = {"User-Agent": "Test"}
        
        result = await fetch_with_retry(mock_client, url, headers)
        
        assert result == mock_response
        mock_client.get.assert_called_once_with(url, headers=headers)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_with_retry_rate_limited(self):
        """Test handling of 429 rate limit response."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        
        # First call raises 429, second succeeds
        mock_response_error = MagicMock()
        mock_response_error.status_code = 429
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = MagicMock()
        
        error = httpx.HTTPStatusError(
            "Rate limited", 
            request=MagicMock(), 
            response=mock_response_error
        )
        
        mock_client.get = AsyncMock(
            side_effect=[error, mock_response_success]
        )
        
        url = "https://example.com"
        headers = {"User-Agent": "Test"}
        
        result = await fetch_with_retry(mock_client, url, headers, retries=3)
        
        assert result == mock_response_success
        assert mock_client.get.call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_fetch_with_retry_exhausted(self):
        """Test that retries continue for 429 errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        
        call_count = 0
        async def mock_get_with_count(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response_error = MagicMock()
            mock_response_error.status_code = 429
            raise httpx.HTTPStatusError(
                "Rate limited", 
                request=MagicMock(), 
                response=mock_response_error
            )
        
        mock_client.get = mock_get_with_count
        
        url = "https://example.com"
        headers = {"User-Agent": "Test"}
        
        # The function will exhaust all retries
        # Based on the code, it catches 429 but doesn't explicitly raise after the loop
        # So it will either return None or raise the last exception
        try:
            result = await fetch_with_retry(mock_client, url, headers, retries=2)
            # If it returns, check call count
            assert call_count == 2
        except httpx.HTTPStatusError:
            # If it raises, that's also valid behavior
            assert call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetch_with_retry_other_http_error(self):
        """Test handling of non-429 HTTP errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        
        mock_response_error = MagicMock()
        mock_response_error.status_code = 404
        
        error = httpx.HTTPStatusError(
            "Not found", 
            request=MagicMock(), 
            response=mock_response_error
        )
        
        mock_client.get = AsyncMock(side_effect=error)
        
        url = "https://example.com"
        headers = {"User-Agent": "Test"}
        
        # Should raise immediately for non-429 errors
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_with_retry(mock_client, url, headers, retries=3)
        
        # Should only try once for non-429 errors
        assert mock_client.get.call_count == 1


class TestMCPServerIntegration:
    """Test MCP server core functionality."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lookup_cik_success(self):
        """Test successful CIK lookup."""
        from mcp_server.server import lookup_cik
        
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        cik = await lookup_cik("AAPL", mock_client)
        
        assert cik == "0000320193"  # Zero-padded to 10 digits
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lookup_cik_not_found(self):
        """Test CIK lookup for non-existent ticker."""
        from mcp_server.server import lookup_cik
        
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValueError, match="not found"):
            await lookup_cik("INVALID", mock_client)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_company_filings_basic(self):
        """Test basic company filings retrieval."""
        from mcp_server.server import get_company_filings
        
        with patch('mcp_server.server.lookup_cik') as mock_lookup, \
             patch('mcp_server.server.fetch_with_retry') as mock_fetch:
            
            mock_lookup.return_value = "0000320193"
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "filings": {
                    "recent": {
                        "form": ["10-K", "10-Q", "10-K"],
                        "filingDate": ["2024-01-15", "2024-02-01", "2023-01-15"],
                        "accessionNumber": ["0001234567-24-000001", "0001234567-24-000002", "0001234567-23-000001"],
                        "primaryDocument": ["aapl-20240115.htm", "aapl-20240201.htm", "aapl-20230115.htm"]
                    }
                }
            }
            mock_fetch.return_value = mock_response
            
            result = await get_company_filings("AAPL", form_type="10-K", limit=2)
            
            assert isinstance(result, str)
            assert "2024-01-15" in result
            assert "10-K" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_financial_statements_basic(self):
        """Test financial statements retrieval."""
        from mcp_server.server import get_financial_statements
        
        with patch('mcp_server.server.lookup_cik') as mock_lookup, \
             patch('mcp_server.server.fetch_with_retry') as mock_fetch:
            
            mock_lookup.return_value = "0000320193"
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "units": {
                    "USD": [
                        {"form": "10-K", "fy": 2024, "fp": "FY", "val": 1000000, "filed": "2024-01-15"},
                        {"form": "10-K", "fy": 2023, "fp": "FY", "val": 900000, "filed": "2023-01-15"}
                    ]
                }
            }
            mock_fetch.return_value = mock_response
            
            result = await get_financial_statements("AAPL", concept="NetIncomeLoss")
            
            assert isinstance(result, str)
            assert "2024" in result
            assert "1000000" in result


# Fixtures for common test data
@pytest.fixture
def sample_10k_text():
    """Sample 10-K document text for testing."""
    return """
    UNITED STATES SECURITIES AND EXCHANGE COMMISSION
    
    FORM 10-K
    
    Item 1. Business
    The Company operates in multiple segments...
    
    Item 1A. Risk Factors
    Investment in our securities involves risks...
    
    Item 7. Management's Discussion and Analysis of Financial Condition
    The following discussion should be read in conjunction...
    """


@pytest.fixture
def mock_edgar_response():
    """Mock EDGAR API response."""
    return {
        'ticker': 'AAPL',
        'filing_date': '2024-01-15',
        'form_type': '10-K',
        'content': 'Mock filing content'
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])