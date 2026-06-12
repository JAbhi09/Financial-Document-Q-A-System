"""
Unit tests for Compliance module (Fraud Detection).

Tests Beneish M-Score calculation, linguistic analysis, and red flag detection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from compliance.beneish import (
    calculate_beneish_m_score,
    calculate_beneish_m_score_with_ticker,
    calculate_beneish_m_score_demo,
    get_financial_data_for_year,
    safe_div,
)
from compliance.discrepancy import (
    extract_claims_from_text,
    build_financials_for_discrepancy,
    detect_discrepancies,
)


class TestBeneishMScore:
    """Test Beneish M-Score calculation."""
    
    @pytest.mark.unit
    def test_safe_div_normal(self):
        """Test safe division with normal values."""
        assert safe_div(10, 2) == 5.0
        assert safe_div(100, 4) == 25.0
    
    @pytest.mark.unit
    def test_safe_div_zero(self):
        """Test safe division with zero denominator."""
        # Should return default value (1.0) when dividing by zero
        assert safe_div(10, 0) == 1.0
        assert safe_div(10, 0, default=2.0) == 2.0
    
    @pytest.mark.unit
    def test_safe_div_none(self):
        """Test safe division with None values."""
        # None should be converted to 0 for numerator, 1 for denominator
        assert safe_div(None, 5) == 0.0
        assert safe_div(10, None) == 10.0
    
    @pytest.mark.unit
    def test_safe_div_infinity(self):
        """Test safe division returns default for infinity."""
        # Very large numbers that might produce infinity
        result = safe_div(float('inf'), 1)
        assert result == 1.0  # Should return default
    
    @pytest.mark.unit
    def test_calculate_m_score_basic(self):
        """Test basic M-Score calculation with proper structure."""
        current_data = {
            'receivables': 1500,
            'revenue': 6000,
            'cogs': 3600,
            'total_assets': 20000,
            'current_assets': 8000,
            'ppe': 6000,
            'depreciation': 800,
            'sga': 1200,
            'total_debt': 3000,
            'net_income': 1000,
            'operating_cash_flow': 1200
        }
        
        prior_data = {
            'receivables': 1200,
            'revenue': 5000,
            'cogs': 3000,
            'total_assets': 18000,
            'current_assets': 7000,
            'ppe': 5500,
            'depreciation': 750,
            'sga': 1000,
            'total_debt': 2800,
            'net_income': 900,
            'operating_cash_flow': 1000
        }
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        # Check that result is a dictionary with expected keys
        assert isinstance(result, dict)
        assert 'm_score' in result
        assert 'risk_level' in result
        assert 'components' in result
        assert isinstance(result['m_score'], (int, float))
        assert result['risk_level'] in ['HIGH', 'MODERATE', 'LOW']
    
    @pytest.mark.unit
    def test_calculate_m_score_all_ratios(self):
        """Test that all M-Score ratio components are calculated."""
        current_data = {
            'receivables': 2000,
            'revenue': 5000,
            'cogs': 3500,
            'total_assets': 15000,
            'current_assets': 5000,
            'ppe': 4000,
            'depreciation': 500,
            'sga': 800,
            'total_debt': 2000,
            'net_income': 800,
            'operating_cash_flow': 1000
        }
        
        prior_data = {
            'receivables': 1000,
            'revenue': 4000,
            'cogs': 2400,
            'total_assets': 12000,
            'current_assets': 4000,
            'ppe': 3500,
            'depreciation': 600,
            'sga': 600,
            'total_debt': 1800,
            'net_income': 700,
            'operating_cash_flow': 850
        }
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        # Check all components exist
        components = result['components']
        expected_components = ['dsri', 'gmi', 'aqi', 'sgi', 'depi', 'sgai', 'lvgi', 'tata']
        
        for component in expected_components:
            assert component in components
            assert isinstance(components[component], (int, float))
            assert not (components[component] != components[component])  # Check for NaN
    
    @pytest.mark.unit
    def test_calculate_m_score_interpretation(self):
        """Test that interpretation is provided for key ratios."""
        current_data = {
            'receivables': 2000,
            'revenue': 5000,
            'cogs': 3500,
            'total_assets': 15000,
            'current_assets': 5000,
            'ppe': 4000,
            'depreciation': 500,
            'sga': 800,
            'total_debt': 2000,
            'net_income': 800,
            'operating_cash_flow': 1000
        }
        
        prior_data = {
            'receivables': 1000,
            'revenue': 4000,
            'cogs': 2400,
            'total_assets': 12000,
            'current_assets': 4000,
            'ppe': 3500,
            'depreciation': 600,
            'sga': 600,
            'total_debt': 1800,
            'net_income': 700,
            'operating_cash_flow': 850
        }
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        # Check interpretation exists
        assert 'interpretation' in result
        interpretation = result['interpretation']
        
        # Check that key ratios have interpretations
        assert 'dsri' in interpretation
        assert 'gmi' in interpretation
        assert 'sgi' in interpretation
        assert 'tata' in interpretation
    
    @pytest.mark.unit
    def test_m_score_high_risk(self):
        """Test M-Score indicating high manipulation risk."""
        # Create data that should indicate HIGH risk (M-Score > -1.78)
        current_data = {
            'receivables': 3000,  # Large increase in receivables
            'revenue': 5000,
            'cogs': 4000,  # Deteriorating margins
            'total_assets': 15000,
            'current_assets': 3000,
            'ppe': 3000,
            'depreciation': 300,
            'sga': 1200,  # Rising SG&A
            'total_debt': 5000,  # Rising debt
            'net_income': 500,
            'operating_cash_flow': 100  # Low cash flow vs income
        }
        
        prior_data = {
            'receivables': 1000,
            'revenue': 4500,
            'cogs': 2500,
            'total_assets': 12000,
            'current_assets': 4000,
            'ppe': 3500,
            'depreciation': 500,
            'sga': 800,
            'total_debt': 2000,
            'net_income': 600,
            'operating_cash_flow': 550
        }
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        assert isinstance(result, dict)
        assert 'm_score' in result
        # With these red flags, should likely be HIGH or MODERATE risk
        assert result['risk_level'] in ['HIGH', 'MODERATE']
    
    @pytest.mark.unit
    def test_m_score_low_risk(self):
        """Test M-Score indicating low manipulation risk."""
        # Create healthy financial data
        current_data = {
            'receivables': 1100,  # Modest increase
            'revenue': 5000,
            'cogs': 2500,  # Good margins
            'total_assets': 20000,
            'current_assets': 8000,
            'ppe': 6000,
            'depreciation': 800,
            'sga': 1000,
            'total_debt': 2000,
            'net_income': 1500,
            'operating_cash_flow': 1600  # Strong cash flow
        }
        
        prior_data = {
            'receivables': 1000,
            'revenue': 4800,
            'cogs': 2400,
            'total_assets': 19000,
            'current_assets': 7500,
            'ppe': 5800,
            'depreciation': 750,
            'sga': 950,
            'total_debt': 1900,
            'net_income': 1400,
            'operating_cash_flow': 1500
        }
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        assert isinstance(result, dict)
        assert result['m_score'] < -1.78  # Should be below manipulation threshold
    
    @pytest.mark.unit
    def test_m_score_handles_missing_data(self):
        """Test that M-Score handles missing/None values gracefully."""
        current_data = {
            'receivables': 1500,
            'revenue': 6000,
            'cogs': None,  # Missing data
            'total_assets': 20000,
            'current_assets': 8000,
            'ppe': None,  # Missing data
            'depreciation': 800,
            'sga': 1200,
            'total_debt': 3000,
            'net_income': 1000,
            'operating_cash_flow': 1200
        }
        
        prior_data = {
            'receivables': 1200,
            'revenue': 5000,
            'cogs': 3000,
            'total_assets': 18000,
            'current_assets': 7000,
            'ppe': 5500,
            'depreciation': 750,
            'sga': 1000,
            'total_debt': 2800,
            'net_income': 900,
            'operating_cash_flow': 1000
        }
        
        # Should not crash with missing data
        result = calculate_beneish_m_score(current_data, prior_data)
        
        assert isinstance(result, dict)
        assert 'm_score' in result
    
    @pytest.mark.unit
    def test_m_score_exception_handling(self):
        """Test exception handling in M-Score calculation."""
        # Pass invalid data that might cause exceptions
        current_data = {}
        prior_data = {}
        
        result = calculate_beneish_m_score(current_data, prior_data)
        
        # Should return error dict
        assert isinstance(result, dict)
        # Either successful calculation with defaults or error
        assert 'm_score' in result or 'error' in result
    
    @pytest.mark.unit
    def test_calculate_m_score_demo(self):
        """Test demo calculation function."""
        result = calculate_beneish_m_score_demo()
        
        assert isinstance(result, dict)
        assert 'm_score' in result
        assert result['data_source'] == 'demo'
        assert 'components' in result
        assert 'note' in result


class TestFinancialDataRetrieval:
    """Test financial data retrieval from SEC API."""
    
    @pytest.mark.unit
    @patch('compliance.beneish.requests.get')
    @patch('compliance.beneish.Company')
    def test_get_financial_data_success(self, mock_company, mock_get):
        """Test successful financial data retrieval."""
        # Mock Company
        mock_company_instance = MagicMock()
        mock_company_instance.cik = 320193
        mock_company.return_value = mock_company_instance
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'facts': {
                'us-gaap': {
                    'AccountsReceivableNet': {
                        'units': {
                            'USD': [
                                {'val': 1000, 'fy': 2024, 'form': '10-K', 'end': '2024-12-31'}
                            ]
                        }
                    },
                    'Revenues': {
                        'units': {
                            'USD': [
                                {'val': 5000, 'fy': 2024, 'form': '10-K', 'fp': 'FY', 
                                 'start': '2024-01-01', 'end': '2024-12-31'}
                            ]
                        }
                    },
                    'CostOfRevenue': {
                        'units': {
                            'USD': [
                                {'val': 3000, 'fy': 2024, 'form': '10-K', 'fp': 'FY',
                                 'start': '2024-01-01', 'end': '2024-12-31'}
                            ]
                        }
                    },
                    'AssetsCurrent': {
                        'units': {
                            'USD': [
                                {'val': 8000, 'fy': 2024, 'form': '10-K', 'end': '2024-12-31'}
                            ]
                        }
                    },
                    'PropertyPlantAndEquipmentNet': {
                        'units': {
                            'USD': [
                                {'val': 6000, 'fy': 2024, 'form': '10-K', 'end': '2024-12-31'}
                            ]
                        }
                    },
                    'Assets': {
                        'units': {
                            'USD': [
                                {'val': 20000, 'fy': 2024, 'form': '10-K', 'end': '2024-12-31'}
                            ]
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = get_financial_data_for_year('AAPL', 2024)
        
        assert result is not None
        assert isinstance(result, dict)
        assert 'receivables' in result or result is None
    
    @pytest.mark.unit
    @patch('compliance.beneish.requests.get')
    @patch('compliance.beneish.Company')
    def test_get_financial_data_api_failure(self, mock_company, mock_get):
        """Test handling of API request failure."""
        mock_company_instance = MagicMock()
        mock_company_instance.cik = 320193
        mock_company.return_value = mock_company_instance
        
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = get_financial_data_for_year('AAPL', 2024)
        
        assert result is None
    
    @pytest.mark.unit
    @patch('compliance.beneish.requests.get')
    @patch('compliance.beneish.Company')
    def test_get_financial_data_no_gaap(self, mock_company, mock_get):
        """Test handling when no US-GAAP data exists."""
        mock_company_instance = MagicMock()
        mock_company_instance.cik = 320193
        mock_company.return_value = mock_company_instance
        
        # Mock response with no us-gaap data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'facts': {}}
        mock_get.return_value = mock_response
        
        result = get_financial_data_for_year('AAPL', 2024)
        
        assert result is None
    
    @pytest.mark.unit
    @patch('compliance.beneish.requests.get')
    @patch('compliance.beneish.Company')
    def test_get_financial_data_insufficient_metrics(self, mock_company, mock_get):
        """Test handling when insufficient metrics are found."""
        mock_company_instance = MagicMock()
        mock_company_instance.cik = 320193
        mock_company.return_value = mock_company_instance
        
        # Mock response with only 2 metrics (< 5 required)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'facts': {
                'us-gaap': {
                    'Revenues': {
                        'units': {
                            'USD': [{'val': 5000, 'fy': 2024, 'form': '10-K', 'fp': 'FY',
                                   'start': '2024-01-01', 'end': '2024-12-31'}]
                        }
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        result = get_financial_data_for_year('AAPL', 2024)
        
        # Should return None if insufficient data
        assert result is None


class TestMScoreWithTicker:
    """Test M-Score calculation with ticker symbol."""
    
    @pytest.mark.unit
    @patch('compliance.beneish.get_financial_data_for_year')
    @patch('compliance.beneish.Company')
    def test_calculate_m_score_with_ticker_success(self, mock_company, mock_get_data):
        """Test M-Score calculation with ticker when data is available."""
        # Mock company
        mock_company_instance = MagicMock()
        mock_company_instance.name = "Test Company Inc."
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
        
        result = calculate_beneish_m_score_with_ticker('TEST', 2024)
        
        assert isinstance(result, dict)
        assert 'm_score' in result
        assert result.get('ticker') == 'TEST' or result.get('data_source') == 'demo'
    
    @pytest.mark.unit
    @patch('compliance.beneish.get_financial_data_for_year')
    @patch('compliance.beneish.Company')
    def test_calculate_m_score_with_ticker_returns_unavailable_when_no_data(self, mock_company, mock_get_data):
        """When SEC data is absent, result must be data_source='unavailable' — never fake numbers."""
        mock_company_instance = MagicMock()
        mock_company_instance.name = "Test Company Inc."
        mock_company.return_value = mock_company_instance

        mock_get_data.return_value = None

        result = calculate_beneish_m_score_with_ticker('TEST', 2024)

        assert isinstance(result, dict)
        assert result['data_source'] == 'unavailable', (
            "Must not silently fall back to demo data — users must know the score is unavailable"
        )
        assert result['m_score'] is None, "m_score must be None, not a fabricated value"
        assert 'message' in result, "A user-facing explanation must be present"
    
    @pytest.mark.unit
    @patch('compliance.beneish.get_financial_data_for_year')
    @patch('compliance.beneish.Company')
    def test_calculate_m_score_with_ticker_fallback_year(self, mock_company, mock_get_data):
        """Test M-Score falls back to previous year if current unavailable."""
        mock_company_instance = MagicMock()
        mock_company_instance.name = "Test Company Inc."
        mock_company.return_value = mock_company_instance
        
        # First 2 calls return None (2024 current, 2023 prior)
        # Next 2 calls return data (2023 current, 2022 prior)
        mock_prior_year_data = {
            'receivables': 1200, 'revenue': 5000, 'cogs': 3000,
            'total_assets': 18000, 'current_assets': 7000, 'ppe': 5500,
            'depreciation': 750, 'sga': 1000, 'total_debt': 2800,
            'net_income': 900, 'operating_cash_flow': 1000
        }
        
        mock_get_data.side_effect = [None, None, mock_prior_year_data, mock_prior_year_data]
        
        result = calculate_beneish_m_score_with_ticker('TEST', 2024)
        
        assert isinstance(result, dict)


# Fixtures
@pytest.fixture
def sample_financial_data():
    """Sample financial data for testing."""
    return {
        'current': {
            'receivables': 1500,
            'revenue': 6000,
            'cogs': 3600,
            'total_assets': 20000,
            'current_assets': 8000,
            'ppe': 6000,
            'depreciation': 800,
            'sga': 1200,
            'total_debt': 3000,
            'net_income': 1000,
            'operating_cash_flow': 1200
        },
        'prior': {
            'receivables': 1200,
            'revenue': 5000,
            'cogs': 3000,
            'total_assets': 18000,
            'current_assets': 7000,
            'ppe': 5500,
            'depreciation': 750,
            'sga': 1000,
            'total_debt': 2800,
            'net_income': 900,
            'operating_cash_flow': 1000
        }
    }


class TestDiscrepancyDetection:
    """Tests for the discrepancy checker and claim extractor."""

    @pytest.mark.unit
    def test_extract_claims_increase(self):
        text = "Revenue increased 12% to $394 billion driven by strong iPhone sales."
        claims = extract_claims_from_text(text)
        assert any(c['metric'] == 'revenue' and c['direction'] == 'increase' for c in claims)

    @pytest.mark.unit
    def test_extract_claims_decrease(self):
        # Avoid words from the increase pattern ("higher", "grew", etc.) in the test sentence
        text = "Net income decreased in fiscal 2024 compared to the prior year."
        claims = extract_claims_from_text(text)
        assert any(c['metric'] == 'net_income' and c['direction'] == 'decrease' for c in claims)

    @pytest.mark.unit
    def test_extract_claims_empty_text(self):
        assert extract_claims_from_text("") == []

    @pytest.mark.unit
    def test_extract_claims_no_financial_keywords(self):
        text = "The weather was sunny and employees enjoyed the company picnic."
        assert extract_claims_from_text(text) == []

    @pytest.mark.unit
    def test_extract_claims_deduplicates_per_metric(self):
        text = (
            "Revenue increased 10%. Total revenues also increased in all regions. "
            "Revenue growth was strong across all segments."
        )
        claims = extract_claims_from_text(text)
        revenue_claims = [c for c in claims if c['metric'] == 'revenue']
        assert len(revenue_claims) == 1, "Each metric should appear at most once"

    @pytest.mark.unit
    def test_detect_directional_mismatch(self):
        claims = [{'metric': 'revenue', 'direction': 'increase', 'value': None, 'sentence': 'Revenue increased.'}]
        financials = {'revenue': {'value': 1000, 'change': -50}}  # actually decreased
        discrepancies = detect_discrepancies(claims, financials)
        assert len(discrepancies) == 1
        assert discrepancies[0]['type'] == 'DIRECTIONAL_MISMATCH'
        assert discrepancies[0]['severity'] == 'HIGH'

    @pytest.mark.unit
    def test_detect_no_discrepancy_when_consistent(self):
        claims = [{'metric': 'revenue', 'direction': 'increase', 'value': None, 'sentence': 'Revenue increased.'}]
        financials = {'revenue': {'value': 1100, 'change': 100}}  # genuinely increased
        discrepancies = detect_discrepancies(claims, financials)
        assert discrepancies == []

    @pytest.mark.unit
    def test_detect_magnitude_mismatch(self):
        claims = [{'metric': 'revenue', 'direction': 'increase', 'value': 500, 'sentence': 'Revenue was 500.'}]
        financials = {'revenue': {'value': 1000, 'change': 100}}  # 100% off
        discrepancies = detect_discrepancies(claims, financials)
        types = [d['type'] for d in discrepancies]
        assert 'MAGNITUDE_MISMATCH' in types

    @pytest.mark.unit
    def test_build_financials_from_raw(self):
        current = {'revenue': 1100, 'net_income': 200, 'cogs': 600, 'operating_cash_flow': 300}
        prior   = {'revenue': 1000, 'net_income': 180, 'cogs': 550, 'operating_cash_flow': 280}
        financials = build_financials_for_discrepancy(current, prior)
        assert financials['revenue']['change'] == 100
        assert financials['net_income']['change'] == 20
        assert financials['gross_profit']['value'] == 500   # 1100 - 600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])