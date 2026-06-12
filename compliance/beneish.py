from edgar import Company, set_identity
from typing import Dict, Optional
import os
import requests

def safe_div(a, b, default=1.0):
    """Safe division that handles None and zero"""
    # ✅ Convert None to 0
    a = 0 if a is None else a
    b = 1 if b is None else b
    
    if b == 0:
        return default
    
    try:
        result = a / b
        # Check for inf/nan
        if not (result == result) or abs(result) == float('inf'):
            return default
        return result
    except:
        return default

def calculate_beneish_m_score(current: dict, prior: dict) -> dict:
    """Calculate Beneish M-Score from financial data dictionary."""
    
    def safe_get(d, key, default=0):
        """Safely get value, converting None to default"""
        val = d.get(key, default)
        return default if val is None else val
    
    try:
        # Extract values safely
        curr_recv = safe_get(current, 'receivables')
        curr_rev = safe_get(current, 'revenue', 1)  # Avoid div by zero
        prior_recv = safe_get(prior, 'receivables')
        prior_rev = safe_get(prior, 'revenue', 1)
        
        curr_cogs = safe_get(current, 'cogs')
        prior_cogs = safe_get(prior, 'cogs')
        
        curr_ca = safe_get(current, 'current_assets')
        curr_ppe = safe_get(current, 'ppe')
        curr_ta = safe_get(current, 'total_assets', 1)
        prior_ca = safe_get(prior, 'current_assets')
        prior_ppe = safe_get(prior, 'ppe')
        prior_ta = safe_get(prior, 'total_assets', 1)
        
        curr_dep = safe_get(current, 'depreciation')
        prior_dep = safe_get(prior, 'depreciation')
        
        curr_sga = safe_get(current, 'sga')
        prior_sga = safe_get(prior, 'sga')
        
        curr_debt = safe_get(current, 'total_debt')
        prior_debt = safe_get(prior, 'total_debt')
        
        curr_ni = safe_get(current, 'net_income')
        curr_ocf = safe_get(current, 'operating_cash_flow')
        
        # Days Sales in Receivables Index (DSRI)
        dsri = safe_div(safe_div(curr_recv, curr_rev),
                        safe_div(prior_recv, prior_rev))
        if dsri == 0:
            dsri = 1.0
        
        # Gross Margin Index (GMI)
        gmi = safe_div(safe_div(prior_rev - prior_cogs, prior_rev),
                       safe_div(curr_rev - curr_cogs, curr_rev))
        if gmi == 0:
            gmi = 1.0
        
        # Asset Quality Index (AQI)
        aqi = safe_div(1 - safe_div(curr_ca + curr_ppe, curr_ta),
                       1 - safe_div(prior_ca + prior_ppe, prior_ta))
        if aqi == 0:
            aqi = 1.0
        
        # Sales Growth Index (SGI)
        sgi = safe_div(curr_rev, prior_rev)
        if sgi == 0:
            sgi = 1.0
        
        # Depreciation Index (DEPI)
        # Handle missing depreciation gracefully
        depi = safe_div(
            safe_div(prior_dep, prior_dep + prior_ppe if prior_ppe else 1),
            safe_div(curr_dep, curr_dep + curr_ppe if curr_ppe else 1)
        )
        if depi == 0:
            depi = 1.0
        
        # SG&A Index (SGAI)
        sgai = safe_div(safe_div(curr_sga, curr_rev),
                        safe_div(prior_sga, prior_rev))
        if sgai == 0:
            sgai = 1.0
        
        # Leverage Index (LVGI)
        lvgi = safe_div(safe_div(curr_debt, curr_ta),
                        safe_div(prior_debt, prior_ta))
        if lvgi == 0:
            lvgi = 1.0
        
        # Total Accruals to Total Assets (TATA)
        tata = safe_div(curr_ni - curr_ocf, curr_ta)
        
        # M-Score calculation (Beneish 1999)
        m_score = -4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + \
                  0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi
        
        # Determine risk level
        if m_score > -1.78:
            risk_level = "HIGH"
        elif m_score > -2.22:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        return {
            "m_score": round(m_score, 3),
            "manipulation_likely": m_score > -2.22,
            "risk_level": risk_level,
            "components": {
                "dsri": round(dsri, 3),
                "gmi": round(gmi, 3),
                "aqi": round(aqi, 3),
                "sgi": round(sgi, 3),
                "depi": round(depi, 3),
                "sgai": round(sgai, 3),
                "lvgi": round(lvgi, 3),
                "tata": round(tata, 3)
            },
            "interpretation": {
                "dsri": "Higher = Inflating receivables" if dsri > 1.05 else "Normal",
                "gmi": "Higher = Deteriorating margins" if gmi > 1.05 else "Normal",
                "sgi": "Higher = Aggressive growth" if sgi > 1.2 else "Normal",
                "tata": "Higher = Lower quality earnings" if tata > 0.03 else "Normal"
            }
        }
        
    except Exception as e:
        import traceback
        print(f"  ❌ Exception during M-Score calculation:")
        print(traceback.format_exc())
        return {
            "error": str(e),
            "m_score": -999,
            "risk_level": "UNKNOWN",
            "data_source": "error"
        }

def get_financial_data_for_year(ticker: str, year: int) -> Optional[Dict]:
    """
    Extract financial data for a specific fiscal year directly from SEC API.
    
    Args:
        ticker: Stock ticker symbol
        year: Fiscal year (e.g., 2024)
    
    Returns:
        Dictionary with financial metrics or None
    """
    try:
        # Get company and CIK
        company = Company(ticker)
        cik = str(company.cik).zfill(10)
        
        # Fetch raw data from SEC API
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        headers = {"User-Agent": os.environ.get("USER_AGENT", "FinancialResearch research@northeastern.edu")}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"    ❌ API request failed: {response.status_code}")
            return None
        
        facts_data = response.json()
        us_gaap = facts_data.get('facts', {}).get('us-gaap', {})
        
        if not us_gaap:
            print(f"    ❌ No US-GAAP data found")
            return None
        
        def get_annual_value(concept_name: str, fiscal_year: int) -> Optional[float]:
            """Extract annual value for a specific concept and fiscal year"""
            try:
                if concept_name not in us_gaap:
                    return None
                
                metric_data = us_gaap[concept_name]
                
                # Get USD unit data
                if 'units' not in metric_data or 'USD' not in metric_data['units']:
                    return None
                
                usd_data = metric_data['units']['USD']
                
                # Find annual (10-K) data for the fiscal year
                for entry in usd_data:
                    if entry.get('fy') == fiscal_year and entry.get('form') == '10-K':
                        # For balance sheet items (instant), just return val
                        if 'end' in entry and 'start' not in entry:
                            return float(entry['val'])
                        # For income statement items (duration), return val
                        elif 'start' in entry and 'end' in entry:
                            # Make sure it's the full year (not quarterly)
                            start = entry['start']
                            end = entry['end']
                            # Check if it spans roughly a year
                            start_year = int(start[:4])
                            end_year = int(end[:4])
                            # Accept if end year matches and it's not a quarter
                            if end_year == fiscal_year and entry.get('fp') == 'FY':
                                return float(entry['val'])
                
                return None
                
            except Exception as e:
                return None
        
        # Map the concepts we need with multiple fallback options
        data = {
            'receivables': (
                get_annual_value('AccountsReceivableNetCurrent', year) or
                get_annual_value('AccountsReceivableNet', year) or
                get_annual_value('TradeReceivablesHeldForSaleAmount', year) or
                get_annual_value('OtherReceivablesNetCurrent', year)
            ),
            
            'revenue': (
                get_annual_value('Revenues', year) or
                get_annual_value('RevenueFromContractWithCustomerExcludingAssessedTax', year) or
                get_annual_value('SalesRevenueNet', year)
            ),
            
            'cogs': (
                get_annual_value('CostOfRevenue', year) or
                get_annual_value('CostOfGoodsAndServicesSold', year) or
                get_annual_value('CostOfGoodsSold', year)
            ),
            
            'current_assets': get_annual_value('AssetsCurrent', year),
            
            'ppe': (
                get_annual_value('PropertyPlantAndEquipmentNet', year) or
                get_annual_value('PropertyPlantAndEquipmentGross', year)
            ),
            
            'total_assets': get_annual_value('Assets', year),
            
            'depreciation': (
                get_annual_value('DepreciationDepletionAndAmortization', year) or
                get_annual_value('Depreciation', year) or
                get_annual_value('DepreciationAndAmortization', year)
            ),
            
            'sga': (
                get_annual_value('SellingGeneralAndAdministrativeExpense', year) or
                get_annual_value('GeneralAndAdministrativeExpense', year) or
                get_annual_value('OperatingExpenses', year)
            ),
            
            'total_debt': (
                get_annual_value('LongTermDebt', year) or
                get_annual_value('DebtLongTerm', year) or
                get_annual_value('LongTermDebtNoncurrent', year)
            ),
            
            'net_income': (
                get_annual_value('NetIncomeLoss', year) or
                get_annual_value('ProfitLoss', year)
            ),
            
            'operating_cash_flow': (
                get_annual_value('NetCashProvidedByUsedInOperatingActivities', year) or
                get_annual_value('CashProvidedByUsedInOperatingActivities', year)
            ),
        }
        
        # Count valid fields
        valid_count = sum(1 for v in data.values() if v is not None and v != 0)
        
        # Show what we found
        print(f"    Found {valid_count}/11 metrics for {year}:")
        for key, val in data.items():
            if val:
                print(f"      ✓ {key}: ${val:,.0f}")
        
        if valid_count < 5:
            return None
        
        return data
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_beneish_m_score_with_ticker(ticker: str, current_year: int = 2024) -> dict:
    """
    Calculate Beneish M-Score by fetching real financial data from SEC filings.
    
    Args:
        ticker: Stock ticker symbol (e.g., "NFLX", "AAPL")
        current_year: Current fiscal year to analyze
    
    Returns:
        Dictionary with M-Score, components, and interpretation
    """
    print(f"\nCalculating M-Score for {ticker}...")
    
    # Set identity if not already set
    identity = os.environ.get("USER_AGENT", "FinancialResearch research@northeastern.edu")
    set_identity(identity)
    
    try:
        company = Company(ticker)
        print(f"  Company: {company.name}")
        
        # Fetch data for current and prior year
        print(f"\n  Fetching {current_year} data from SEC API...")
        current = get_financial_data_for_year(ticker, current_year)
        
        print(f"\n  Fetching {current_year-1} data from SEC API...")
        prior = get_financial_data_for_year(ticker, current_year - 1)
        
        # If current year fails, try previous year
        if not current:
            print(f"\n  ⚠️ No sufficient data for {current_year}, trying {current_year-1}...")
            current = get_financial_data_for_year(ticker, current_year - 1)
            print(f"\n  Fetching {current_year-2} data...")
            prior = get_financial_data_for_year(ticker, current_year - 2)
            current_year = current_year - 1
        
        if not current or not prior:
            print("\n  ❌ Could not fetch sufficient real data, using demo values")
            return calculate_beneish_m_score_demo()
        
        print(f"\n  ✅ Successfully fetched real data!")
        
        # Calculate M-Score using existing function
        # from compliance.beneish import calculate_beneish_m_score
        result = calculate_beneish_m_score(current, prior)
        
        result['data_source'] = 'real'
        result['ticker'] = ticker
        result['year'] = current_year
        
        return result
        
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return calculate_beneish_m_score_demo()

def calculate_beneish_m_score_demo() -> dict:
    """Demo calculation with placeholder values"""
    return {
        "m_score": -1.997,
        "manipulation_likely": True,
        "risk_level": "MODERATE",
        "data_source": "demo",
        "components": {
            "dsri": 0.92, "gmi": 1.05, "aqi": 1.01, "sgi": 1.15,
            "depi": 0.98, "sgai": 1.02, "lvgi": 1.03, "tata": 0.02
        },
        "note": "⚠️ Using demo data - real financial data unavailable for this company/year",
        "interpretation": {}
    }