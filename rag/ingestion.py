    # import os
    # from typing import List
    # from edgar import Company, set_identity
    # from langchain_core.documents import Document
    # from langchain_text_splitters import RecursiveCharacterTextSplitter

    # # Ensure User-Agent is set for edgartools
    # identity = os.environ.get("USER_AGENT", "FinancialResearchProject email@example.com")
    # set_identity(identity)

    # def fetch_latest_10k_filing(ticker: str):
    #     """
    #     Fetches the latest 10-K filing object for a given ticker.
    #     """
    #     company = Company(ticker)
    #     filings = company.get_filings(form="10-K")
    #     if not filings:
    #         raise ValueError(f"No 10-K filings found for {ticker}")
        
    #     return filings.latest().obj()

    # def extract_key_sections(filing) -> dict:
    #     """
    #     Extracts key sections (Item 1A, 7, 7A, 8, 9A) from the filing object.
        
    #     Returns:
    #         dict: Mapping of section name to text content.
    #     """
    #     sections = {}
        
    #     # edgartools provides property accessors for standard sections
    #     # Note: Availability depends on the filing's HTML structure quality
        
    #     try:
    #         sections['Item 1A'] = filing.risk_factors or ""
    #     except:
    #         sections['Item 1A'] = ""
            
    #     try:
    #         sections['Item 7'] = filing.management_discussion or ""
    #     except:
    #         sections['Item 7'] = ""
            
    #     try:
    #         # Some properties might not be directly available as named attributes
    #         # and might need to be accessed differently depending on edgardtools version
    #         # For now, we wrap in try-except blocks
    #         sections['Item 7A'] = filing['Item 7A'] if 'Item 7A' in filing else "" 
    #         sections['Item 8'] = filing.financial_statements or ""
    #         sections['Item 9A'] = filing['Item 9A'] if 'Item 9A' in filing else ""
    #     except:
    #         pass

    #     return sections

    # def process_filing(ticker: str) -> List[Document]:
    #     """
    #     Orchestrates fetching, extraction, and chunking of the 10-K.
    #     """
    #     print(f"Fetching 10-K for {ticker}...")
    #     filing = fetch_latest_10k_filing(ticker)
        
    #     # Get metadata
    #     fiscal_year = str(filing.filing_date)[:4] # Approximate FY from filing date
    #     company_name = ticker # Or filing.company if available
        
    #     print(f"Extracting sections for {ticker} (Filed: {filing.filing_date})...")
    #     sections = extract_key_sections(filing)
        
    #     # Chunking Strategy
    #     # We use a larger chunk size for financial documents to capture context
    #     text_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=1024,
    #         chunk_overlap=200,
    #         separators=["\n\n", "\n", ". ", " ", ""]
    #     )
        
    #     documents = []
        
    #     for section_name, content in sections.items():
    #         if not content:
    #             continue
                
    #         print(f"Processing {section_name} ({len(content)} chars)...")
    #         # Split text into chunks
    #         chunks = text_splitter.create_documents([content])
            
    #         # Enrich metadata
    #         for i, chunk in enumerate(chunks):
    #             chunk.metadata.update({
    #                 "source": ticker,
    #                 "section": section_name,
    #                 "fiscal_year": fiscal_year,
    #                 "chunk_id": f"{ticker}_{fiscal_year}_{section_name}_{i}"
    #             })
            
    #         documents.extend(chunks)
            
    #     print(f"Created {len(documents)} document chunks for {ticker}.")
    #     return documents

import os
import hashlib
from typing import List
from edgar import Company, set_identity
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Ensure User-Agent is set for edgartools
identity = os.environ.get("USER_AGENT", "FinancialResearchProject email@example.com")
set_identity(identity)

def fetch_latest_10k_filing(ticker: str):
    """
    Fetches the latest 10-K filing object for a given ticker.
    """
    company = Company(ticker)
    filings = company.get_filings(form="10-K")
    if not filings:
        raise ValueError(f"No 10-K filings found for {ticker}")
    
    return filings.latest().obj()

def extract_key_sections(filing) -> dict:
    """
    Extracts key sections (Item 1A, 7, 7A, 8, 9A) from the filing object.
    
    Returns:
        dict: Mapping of section name to text content.
    """
    sections = {}
    
    # edgartools provides property accessors for standard sections
    try:
        sections['Item 1A'] = filing.risk_factors or ""
    except:
        sections['Item 1A'] = ""
        
    try:
        sections['Item 7'] = filing.management_discussion or ""
    except:
        sections['Item 7'] = ""
        
    try:
        sections['Item 7A'] = filing['Item 7A'] if 'Item 7A' in filing else "" 
        sections['Item 8'] = filing.financial_statements or ""
        sections['Item 9A'] = filing['Item 9A'] if 'Item 9A' in filing else ""
    except:
        pass

    return sections

def fetch_10k_text(ticker: str, index: int = 0) -> tuple:
    """
    Fetch the full text of a specific 10-K filing by recency index.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL")
        index:  0 = latest filing, 1 = prior year, 2 = two years ago, …

    Returns:
        (full_text: str, fiscal_year: str)

    Raises:
        ValueError if the filing or index is unavailable.
    """
    company = Company(ticker)
    filings = company.get_filings(form="10-K")
    if not filings:
        raise ValueError(f"No 10-K filings found for {ticker}")

    try:
        filing_obj = filings[index].obj()
    except (IndexError, TypeError, AttributeError):
        raise ValueError(
            f"Filing index {index} is not available for {ticker}. "
            "The company may have fewer historical filings than requested."
        )

    fiscal_year = str(filing_obj.filing_date)[:4]
    sections = extract_key_sections(filing_obj)

    full_text = "\n\n".join(
        f"=== {name} ===\n{content}"
        for name, content in sections.items()
        if content and len(content.strip()) > 100
    )

    if not full_text.strip():
        raise ValueError(f"No extractable text in {ticker} filing at index {index}.")

    return full_text, fiscal_year


def process_filing(ticker: str) -> List[Document]:
    """
    Orchestrates fetching, extraction, and chunking of the 10-K.
    """
    print(f"Fetching 10-K for {ticker}...")
    filing = fetch_latest_10k_filing(ticker)
    
    # Get metadata
    fiscal_year = str(filing.filing_date)[:4]
    company_name = ticker
    
    print(f"Extracting sections for {ticker} (Filed: {filing.filing_date})...")
    sections = extract_key_sections(filing)
    
    # ✅ IMPROVED: Larger chunks for financial documents with better structure preservation
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,  # ✅ Increased from 1024 - captures more context
        chunk_overlap=400,  # ✅ Increased from 200 - better continuity
        separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""],  # ✅ Prioritize paragraph breaks
        length_function=len,
    )
    
    documents = []
    seen_hashes = {}  # ✅ Track by content hash instead of preview
    duplicate_count = 0
    
    for section_name, content in sections.items():
        if not content or len(content.strip()) < 100:  # ✅ Skip empty/tiny sections
            continue
        
        # ✅ Clean up the content
        content = content.strip()
        
        print(f"Processing {section_name} ({len(content)} chars)...")
        
        # Split text into chunks
        chunks = text_splitter.create_documents([content])
        
        # ✅ Deduplicate and enrich metadata
        for i, chunk in enumerate(chunks):
            # ✅ Create hash of full content for accurate deduplication
            content_hash = hashlib.md5(chunk.page_content.encode('utf-8')).hexdigest()
            
            # ✅ Skip if we've seen this exact content before
            if content_hash in seen_hashes:
                prev_section = seen_hashes[content_hash]
                print(f"  ⚠️  Skipping duplicate chunk (already in {prev_section})")
                duplicate_count += 1
                continue
            
            seen_hashes[content_hash] = section_name
            
            # ✅ Add section context to chunk content for better retrieval
            enhanced_content = f"Section: {section_name}\n\n{chunk.page_content}"
            chunk.page_content = enhanced_content
            
            chunk.metadata.update({
                "source": ticker,
                "company": company_name,
                "section": section_name,
                "fiscal_year": fiscal_year,
                "filing_date": str(filing.filing_date),
                "chunk_id": f"{ticker}_{fiscal_year}_{section_name}_{i}",
                "chunk_index": i,
                "total_chunks_in_section": len(chunks),
                "content_hash": content_hash  # ✅ Store hash for debugging
            })
            
            documents.append(chunk)
    
    print(f"Created {len(documents)} unique document chunks for {ticker}.")
    if duplicate_count > 0:
        print(f"  ℹ️  Skipped {duplicate_count} duplicate chunks")
    
    return documents