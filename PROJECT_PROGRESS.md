# Project Progress Report: Intelligent Financial Document Q&A System

**Project Name**: Financial Document Q&A System with Regulatory Compliance  
**Repository**: JAbhi09/Financial-Document-Q-A-System  
**Last Updated**: June 12, 2026  
**Status**: ✅ **Production Ready — Actively Maintained**

---

## Executive Summary

An **AI-powered financial analysis platform** combining SEC EDGAR data retrieval, RAG (Retrieval-Augmented Generation), and fraud detection. Users query 10-K filings in natural language and get citation-backed answers, along with automated earnings manipulation detection and narrative discrepancy analysis.

### Current State
- All core features implemented and tested
- Three analysis tabs: Document Q&A, Year-over-Year Comparison, Company Comparison
- Post-launch quality fixes applied across discrepancy tuning, retrieval diversity, and rendering cleanup
- 107 tests passing, 73% code coverage

---

## Project Milestones

### Phase 1: Foundation & Data Pipeline (Jan 18–21, 2026)

**Goal:** Build SEC EDGAR integration and document processing pipeline.

- Custom MCP server for SEC EDGAR (`mcp_server/server.py`, `utils.py`)
- Rate limiting and User-Agent compliance with SEC policies
- 10-K ingestion for multiple companies via `edgartools`

**Challenges overcome:**
- `datetime.date` subscriptability error in EDGAR parser
- SEC rate limiting — implemented request throttling and retry logic
- Document format variations across companies

---

### Phase 2: RAG Pipeline & AI Integration (Jan 21–22, 2026)

**Goal:** Implement chunking, vector storage, and Gemini API integration.

- Section-aware document chunking (preserves Item 1A, Item 7, etc.)
- ChromaDB vector store with per-company isolation (`chroma_db_<TICKER>`)
- Gemini 2.5 Flash integration (1M token context, streaming responses)
- Citation system referencing source sections

**Key files:** `rag/ingestion.py`, `rag/vector_store.py`, `analysis/gemini_engine.py`, `analysis/prompts.py`

**Challenges overcome:**
- NLTK `punkt_tab` tokenizer missing — added to setup docs
- LangChain module import conflicts — updated `requirements.txt`
- TSLA 10-K producing 0 chunks — fixed legacy parser compatibility

---

### Phase 3: Compliance & Fraud Detection (Jan 21–22, 2026)

**Goal:** Implement three independent fraud detection signals.

- **Beneish M-Score**: 8-ratio formula from Beneish (1999), sourced from real SEC XBRL data
- **Linguistic Analysis**: Passive voice, hedging, lexical diversity metrics (Humpherys et al. 2011)
- **Discrepancy Detection**: Cross-references MD&A narrative claims against reported financials

**Key files:** `compliance/beneish.py`, `compliance/linguistics.py`, `compliance/discrepancy.py`

---

### Phase 4: User Interface & Experience (Jan 22, 2026)

**Goal:** Build production-quality Streamlit web app.

- Multi-tab navigation: Document Q&A, Compare Years, Compare Companies
- Real-time streaming token output
- Compliance report with side-by-side metric cards
- Session state caching — processed companies load in ~5 seconds on repeat visits
- Smart query routing (metric extraction vs. full RAG chain)

**Key file:** `ui/app.py`

**Tested companies:** AAPL · MSFT · TSLA · WMT · NFLX · JPM · JNJ

---

### Phase 5: Documentation & Deployment (Jan 24, 2026)

**Goal:** Package, document, and prepare for production deployment.

- Docker and Docker Compose configuration
- `USER_GUIDE.md` (564 lines), `DOCKER_GUIDE.md`, `HOW_IT_WORKS.md`
- `.gitignore` / `.dockerignore` — secrets and cache excluded from repo

---

### Phase 6: Post-Launch Fixes & Quality Improvements (Jan 29 – Jun 12, 2026)

This phase covers incremental quality improvements applied after the initial release.

#### Beneish & Discrepancy Fixes

**commit `2689dc7` — Discrepancy checker unit mismatch**
- Filtered out table artifacts (page numbers, column headers) from dollar extraction
- Normalized dollar values before comparing narrative claims to financial data
- Prevents false HIGH-severity flags from formatting noise in filing text

**commit `10d3a5e` — Discrepancy false positive reduction**
- Required explicit unit keyword in dollar extractions (e.g. "million", "billion")
- Excluded gross margin percentage claims from dollar-value matching logic
- Result: cleaner, higher-confidence discrepancy alerts

**commit `b378fc6` — Net income metric matching**
- Excluded operating cash flow sentences from net income claim matching
- Fixes a class of false positives where cash flow narrative was matched against net income financial data

#### UI & Configuration

**commit `54e36d4` — API key UX**
- Hides the API key text input when a key is already present in `.env`
- Shows a "✓ API key loaded" confirmation instead
- Prevents confusion when the key is set but the input appears empty

#### Retrieval Quality

**commit `403ef78` — Dedup and MMR diversity**
- Strengthened chunk deduplication: normalizes whitespace and casing before MD5 hashing, catches near-duplicate chunks that were previously stored separately
- Increased MMR diversity parameter (λ from 0.7 → 0.3): retrieved chunks are now more topically diverse, reducing cases where all 5 chunks came from the same paragraph

#### Rendering & Output Cleanup

**commit `aca5891` — LaTeX/markdown rendering fix**

*Root cause:* Gemini formatted dollar amounts as `**$414,340 million**`. Inside a number, the `**` delimiters confused Streamlit's markdown renderer into treating the content as LaTeX math.

*Fix — two layers:*
1. `COMPANY_COMPARISON_PROMPT` now includes explicit formatting rules:
   - Never place `**` inside or around dollar amounts
   - End bold before the dollar sign: `**Revenue:** $391 billion`
   - Never use LaTeX, math notation, or asterisks inside financial figures
2. `_clean_latex_artifacts()` in `ui/app.py` strips residual patterns with regex before rendering

**commit `61e680f` — Backtick code rendering fix**

*Root cause:* Gemini wrapped multi-word financial phrases in backticks (e.g. `` `414,340 million in 2025 and` ``), which Streamlit rendered as green monospace code font.

*Fix:*
1. Added to prompt: "NEVER use backticks anywhere in your response"
2. Replaced two narrow backtick regexes with a single broad pattern:
   ```python
   text = re.sub(r'`([^`]+)`', r'\1', text)  # strips any `anything`
   ```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Streamlit UI (ui/app.py)                   │
│   Tab 1: Q&A  │  Tab 2: Compare Years  │  Tab 3: Compare   │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴──────────┬──────────────┬─────────────┐
        │                      │              │             │
┌───────▼────────┐  ┌──────────▼─────┐ ┌─────▼──────┐ ┌────▼─────────┐
│  MCP Server    │  │   RAG Module   │ │ Compliance │ │  Gemini AI   │
│   (SEC Data)   │  │  (ChromaDB +   │ │   Module   │ │   (Analysis) │
│                │  │   Embeddings)  │ │            │ │              │
└────────────────┘  └────────────────┘ └────────────┘ └──────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Web UI framework |
| AI/LLM | Google Gemini 2.5 Flash | Question answering & analysis |
| Orchestration | LangChain | LLM workflow management |
| Vector DB | ChromaDB | Document embeddings & retrieval |
| Embeddings | Sentence Transformers | Text vectorization |
| Data Source | SEC EDGAR (edgartools) | Financial filings |
| NLP | NLTK | Linguistic analysis |
| Data Processing | Pandas | Financial data manipulation |
| Containerization | Docker & Docker Compose | Deployment |

---

## Testing & Validation

### Coverage

- **107 tests passing**, 3 skipped, 73% overall coverage
- Unit tests: compliance modules, MCP server, RAG pipeline (no network required)
- Integration tests: end-to-end flow against real SEC EDGAR

### Validated Scenarios

- Q&A across revenue, risk, strategy, and specific section queries
- YoY comparison for financial metrics and risk factor deltas
- Company comparison across M-Score, linguistic indicators, and AI narrative
- Discrepancy detection with HIGH and MEDIUM severity cases
- Edge cases: large documents (TSLA 400+ pages), missing XBRL data, rate limits

---

## Known Issues Resolved

| Issue | Fix | Commit |
|-------|-----|--------|
| Discrepancy false positives from table artifacts | Unit normalization, filter table noise | `2689dc7` |
| Gross margin % matched as dollar discrepancy | Exclude percentage-only claims | `10d3a5e` |
| Cash flow sentences matched as net income | Exclude operating cash flow from net income matcher | `b378fc6` |
| API key input shown when .env key exists | Hide input, show confirmation when key loaded | `54e36d4` |
| Near-duplicate chunks stored separately | Normalize before MD5 hash | `403ef78` |
| All retrieved chunks from same paragraph | Increase MMR diversity λ: 0.7 → 0.3 | `403ef78` |
| `**$number**` renders as LaTeX in Streamlit | Prompt rules + regex cleanup | `aca5891` |
| `` `number` `` renders as code in Streamlit | Prompt rules + broad backtick regex | `61e680f` |

---

## Known Limitations

1. **US companies only** — SEC EDGAR coverage
2. **Annual data** — 10-Q quarterly support not yet implemented
3. **Data freshness** — sourced from last 10-K (filed 60–90 days after fiscal year end)
4. **AI accuracy** — answers should be verified against shown source sections
5. **M-Score accuracy** — ~76% per academic studies, not a guarantee of fraud
6. **First run is slow** — embedding 200+ chunks takes 3–7 minutes locally

---

## Performance Metrics

| Task | First Run | Cached |
|------|-----------|--------|
| Document download | 10–30s | N/A |
| Chunking & embedding | 2–5 min | N/A |
| Total first load | 3–7 min | 5–10s |
| Q&A query | 5–15s | 5–15s |
| Compliance report | 30–60s | 30–60s |
| YoY comparison | 1–3 min | 1–3 min |
| Company comparison (AI) | 30–90s | instant |

**Disk per company:** 50–200 MB | **RAM during processing:** 2–4 GB | **RAM idle:** 1–2 GB

---

## Deployment Options

### Local
```bash
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
streamlit run ui/app.py
```

### Docker
```bash
docker-compose up -d
# http://localhost:8501
```

Compatible with: Google Cloud Run · AWS ECS/Fargate · Azure Container Instances · Streamlit Cloud

---

## Future Roadmap

- [ ] 10-Q quarterly report support
- [ ] Export to PDF/Excel
- [ ] 8-K real-time event monitoring
- [ ] Multi-user authentication with saved sessions
- [ ] RESTful API endpoint
- [ ] Redis caching layer for repeated queries
- [ ] Interactive financial charts

---

## Documentation Inventory

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview, quick start, feature list |
| `HOW_IT_WORKS.md` | Full architecture walkthrough with data flow diagrams |
| `USER_GUIDE.md` | End-user manual with installation and troubleshooting |
| `DOCKER_GUIDE.md` | Containerization and production deployment |
| `TESTING_GUIDE.md` | How to run and extend the test suite |
| `PROJECT_PROGRESS.md` | This file — development history and changelog |

---

## Research Foundations

- Beneish (1999) — "The Detection of Earnings Manipulation"
- Humpherys et al. (2011) — "Identification of Fraudulent Financial Statements Using Linguistic Credibility Analysis"
- Purda & Skillicorn (2012) — "Accounting Variables, Deception, and a Bag of Words"
- FinanceBench evaluation dataset

---

**Last Updated**: June 12, 2026  
**Version**: 1.1.0  
**Status**: Production Ready — Actively Maintained
