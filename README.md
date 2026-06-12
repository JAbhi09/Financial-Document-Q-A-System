# Intelligent Financial Document Q&A System

An AI-powered platform for analyzing SEC 10-K filings using RAG (Retrieval-Augmented Generation), earnings manipulation detection, and narrative discrepancy analysis. Ask plain-English questions about any US-listed company and get cited, accurate answers in seconds.

## Features

### Document Q&A
- Natural language questions answered directly from SEC filings
- Every answer cites its source section (Item 1A, Item 7 MD&A, etc.)
- Smart routing: short metric queries use focused extraction; strategy questions use full RAG chain
- Streaming responses with real-time token output

### Year-over-Year Comparison
- Fetches two consecutive 10-K filings automatically
- Compares revenue, margins, EPS, operating income with % change
- Surfaces new/removed/modified risk factors between years
- Identifies strategic shifts in MD&A and capital allocation

### Company Comparison
- Side-by-side analysis of any two companies from their latest 10-K
- Beneish M-Score and linguistic fraud indicators shown for both
- AI narrative comparison across revenue, profitability, risk, and strategy
- Fraud risk summary table with winner labels

### Compliance & Fraud Detection (runs automatically on filing load)
- **Beneish M-Score**: Calculates 8 financial ratios (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) from real SEC XBRL data. M > −2.22 flags potential earnings manipulation (~76% accuracy per academic studies).
- **Linguistic Analysis**: Measures passive voice, hedging language, and lexical diversity based on Humpherys et al. (2011). Flags evasiveness and uncertainty patterns common in fraudulent filings.
- **Discrepancy Detection**: Cross-references MD&A narrative claims ("revenue increased 15%") against actual reported financials. Flags directional mismatches (HIGH) and magnitude discrepancies >10% (MEDIUM).

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Streamlit UI  (ui/app.py)               │
│   Tab 1: Q&A  │  Tab 2: Compare Years  │  Tab 3: Compare  │
└───────┬────────────────┬──────────────────────┬───────────┘
        │                │                      │
┌───────▼──────┐  ┌──────▼────────┐  ┌──────────▼──────────┐
│  MCP Server  │  │  RAG Pipeline │  │  Compliance Module  │
│  SEC EDGAR   │  │  ChromaDB +   │  │  Beneish · Ling ·   │
│  integration │  │  Embeddings   │  │  Discrepancy        │
└───────┬──────┘  └──────┬────────┘  └─────────────────────┘
        │                │
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Gemini 2.5    │
        │  Flash (1M ctx)│
        └────────────────┘
```

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| LLM | Google Gemini 2.5 Flash | 1M token context — reads an entire 10-K without chunking loss |
| Orchestration | LangChain | Standard RAG chain assembly |
| Vector DB | ChromaDB | Local disk, no external service, fast for per-company isolation |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) | Lightweight, strong financial-English semantics |
| Data source | edgartools + SEC EDGAR | Understands 10-K HTML structure, extracts named sections |
| UI | Streamlit | Pure Python, no frontend code |
| MCP server | FastMCP | Standardized SEC API wrapper |

## Prerequisites

- Python 3.10+
- Google Gemini API key ([get one here](https://aistudio.google.com/))

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/JAbhi09/Financial-Document-Q-A-System.git
cd Financial-Document-Q-A-System

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
echo GOOGLE_API_KEY=your_key_here > .env
echo USER_AGENT=YourName your@email.com >> .env
```

## Usage

```bash
streamlit run ui/app.py
# Opens at http://localhost:8501
```

1. Enter a ticker in the sidebar (e.g. `AAPL`, `MSFT`, `JPM`)
2. Click **Analyze Filing** — first run takes 3–7 min to download and embed; subsequent loads are instant
3. Use the three tabs to ask questions, compare years, or compare two companies

## Docker

```bash
docker-compose up -d
# App available at http://localhost:8501
```

See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for full deployment instructions.

## Tested Companies

AAPL · MSFT · TSLA · WMT · NFLX · JPM · JNJ · GOOGL · META · NVDA

## Roadmap

- [x] Phase 1 — SEC EDGAR MCP server and data pipeline
- [x] Phase 2 — RAG pipeline and Gemini integration
- [x] Phase 3 — Compliance and fraud detection layer
- [x] Phase 4 — Streamlit UI with streaming responses
- [x] Phase 5 — Docker deployment and documentation
- [x] Phase 6 — Post-launch fixes (discrepancy tuning, rendering cleanup, dedup improvements)
- [ ] 10-Q quarterly report support
- [ ] Export to PDF/Excel
- [ ] 8-K real-time event monitoring
- [ ] Multi-user authentication and saved sessions

## Research Foundations

- Humpherys et al. (2011) — "Identification of Fraudulent Financial Statements Using Linguistic Credibility Analysis"
- Purda & Skillicorn (2012) — "Accounting Variables, Deception, and a Bag of Words"
- Beneish (1999) — "The Detection of Earnings Manipulation"

## License

See [LICENSE](LICENSE) for details.
