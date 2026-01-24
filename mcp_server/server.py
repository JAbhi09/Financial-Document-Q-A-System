from mcp.server.fastmcp import FastMCP
import httpx
import os
import json
from .utils import limiter, fetch_with_retry


# Initialize FastMCP
mcp = FastMCP("sec-edgar")

# SEC Configuration
SEC_BASE = "https://data.sec.gov"
# IMPORTANT: You must define a proper User-Agent
USER_AGENT = os.environ.get("USER_AGENT", "FinancialResearchProject email@example.com")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}


async def lookup_cik(ticker: str, client: httpx.AsyncClient) -> str:
    """
    Look up CIK (Central Index Key) for a given ticker symbol.
    Uses the SEC's company tickers JSON.
    """
    # This file maps all tickers to CIKs.
    # In a production app, we should cache this file locally.
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    
    # We don't rate limit this heavily as it's a static file, but good practice to respect it.
    await limiter.wait() 
    response = await client.get(tickers_url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    
    ticker_upper = ticker.upper()
    for _, company_data in data.items():
        if company_data["ticker"] == ticker_upper:
            # CIK must be 10 digits, zero-padded
            return str(company_data["cik_str"]).zfill(10)
    
    raise ValueError(f"Ticker {ticker} not found in SEC database.")


@mcp.tool()
async def get_company_filings(ticker: str, form_type: str = "10-K", limit: int = 5) -> str:
    """
    Fetch a list of recent SEC filings for a company.
    
    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        form_type: Filing type (e.g. 10-K, 10-Q, 8-K)
        limit: Number of filings to return (default: 5)
    """
    async with httpx.AsyncClient() as client:
        try:
            cik = await lookup_cik(ticker, client)
        except Exception as e:
            return f"Error looking up CIK for {ticker}: {str(e)}"
            
        url = f"{SEC_BASE}/submissions/CIK{cik}.json"
        
        try:
            response = await fetch_with_retry(client, url, HEADERS)
            data = response.json()
        except Exception as e:
            return f"Error fetching filings: {str(e)}"
            
        # Parse filings from the "filings" -> "recent" structure
        recent = data.get("filings", {}).get("recent", {})
        if not recent:
             return "No recent filings found."

        results = []
        count = 0
        
        # Iterate through the lists in 'recent'
        # The SEC API returns parallel arrays for accessionNumber, filingDate, form, etc.
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_documents = recent.get("primaryDocument", [])
        
        for i, form in enumerate(forms):
            if form == form_type:
                acc_num = accession_numbers[i]
                # Format: https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_no_dashes}/{primary_document}
                acc_num_no_dash = acc_num.replace("-", "")
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num_no_dash}/{primary_documents[i]}"
                
                results.append({
                    "date": dates[i],
                    "form": form,
                    "accession_number": acc_num,
                    "url": doc_url
                })
                count += 1
                if count >= limit:
                    break
        
        return json.dumps(results, indent=2)


@mcp.tool()
async def get_financial_statements(ticker: str, concept: str = "NetIncomeLoss", taxonomy: str = "us-gaap") -> str:
    """
    Get specific XBRL financial concept history (e.g. Revenue, Net Income).
    Useful for obtaining raw numbers for the M-Score.
    
    Args:
        ticker: Stock ticker
        concept: XBRL concept name (e.g. Revenues, NetIncomeLoss, Assets)
        taxonomy: XBRL taxonomy (default: us-gaap)
    """
    async with httpx.AsyncClient() as client:
        try:
            cik = await lookup_cik(ticker, client)
        except Exception as e:
            return f"Error looking up CIK for {ticker}: {str(e)}"
            
        # url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        # We use the companyconcept endpoint for specific metric history
        url = f"{SEC_BASE}/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json"
        
        try:
            response = await fetch_with_retry(client, url, HEADERS)
            data = response.json()
        except Exception as e:
            return f"Error fetching financial concept: {str(e)}"
            
        # Extract annual data (10-K)
        units = data.get("units", {})
        results = []
        
        # Usually currency is USD
        for currency, events in units.items():
            for event in events:
                # Filter for annual reports (form 10-K) to get yearly data
                if event.get("form") == "10-K":
                    results.append({
                        "fy": event.get("fy"),
                        "fp": event.get("fp"), # Fiscal period
                        "val": event.get("val"),
                        "filed": event.get("filed")
                    })
        
        # Sort by year
        results.sort(key=lambda x: x.get("filed", ""), reverse=True)
        
        return json.dumps(results[:10], indent=2) # Return last 10 entries

if __name__ == "__main__":
    mcp.run()
