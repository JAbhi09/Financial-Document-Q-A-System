# Intelligent Financial Document Q&A System with Regulatory Compliance

An advanced RAG-based system for analyzing financial documents (10-K, 10-Q, 8-K), performing fraud detection, and ensuring regulatory compliance using Gemini 2.5 Flash and SEC EDGAR data.

## System Architecture

The system comprises four integrated layers:

1.  **Data Ingestion Layer**: Fetches filings from SEC EDGAR via a custom MCP server. Handles rate limiting and specific form parsing (10-K, 10-Q).
2.  **RAG Processing Layer**: Uses section-aware chunking (Element-based) and ChromaDB for vector storage. Optimized for financial documents.
3.  **Analysis Layer**: Powered by **Gemini 2.5 Flash** (1M token context) for long-document understanding and Year-over-Year comparisons.
4.  **Compliance Layer**: Detects fraud signals using:
    *   **Linguistic Analysis**: Passive voice, hedging, lexical diversity (Humpherys et al. 2011).
    *   **Quantitative Analyis**: Beneish M-Score for earnings manipulation detection.
    *   **Discrepancy Detection**: Cross-referencing MD&A narratives with financial tables.

## Key Features

*   **Long-Context Analysis**: Analyze entire 10-K filings without information loss.
*   **Audit Trails**: Every answer includes strict citations to the source document (Page & Section).
*   **Fraud Detection**: Automated "Red Flag" reports based on academic research.
*   **Comparison**: Instantly compare risk factors and financial metrics across fiscal years.

## Prerequisites

*   Python 3.10+
*   Google Gemini API Key
*   Basic understanding of financial filings

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up environment variables:
    ```bash
    export GOOGLE_API_KEY="your_api_key"
    export USER_AGENT="YourName email@domain.com" # Required for SEC EDGAR
    ```

## Usage

Start the web interface:
```bash
streamlit run ui/app.py
```

Enter a ticker (e.g., AAPL) and your API key to begin analysis.

## Roadmap

*   [x] **Phase 1**: SEC EDGAR MCP Server & Data Pipeline
*   [x] **Phase 2**: RAG Pipeline & Gemini Integration
*   [x] **Phase 3**: Compliance & Fraud Detection Layer
*   [x] **Phase 4**: User Interface & Verification

## Research Foundations

Based on research by Humpherys et al. (2011), Purda & Skillicorn (2012), and the FinanceBench evaluation dataset.
