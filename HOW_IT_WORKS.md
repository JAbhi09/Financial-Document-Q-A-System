# How This Project Works — A Complete Guide

> A plain-English walkthrough of the system architecture, data flow, and real-world use cases for the **Intelligent Financial Document Q&A System**.

---

## The Problem It Solves

Every publicly traded US company must file a **10-K** (annual report) with the SEC each year. These documents are the most honest, legally required snapshot of a company's health — they contain revenue figures, risk disclosures, management commentary, fraud warnings, and forward-looking plans.

The problem: **10-K filings are enormous** (100–400 pages), written in dense legal and financial language, and buried in the SEC's EDGAR database. Reading one manually takes a financial analyst days. Reading five to compare companies takes weeks.

This project lets you ask plain-English questions about any US-listed company's 10-K and get cited, accurate answers in seconds — plus automated fraud detection signals.

---

## How It Works — End to End

Here is the full journey from a ticker symbol to an answer:

```
You type: "AAPL"
          │
          ▼
┌─────────────────────┐
│  1. DATA FETCHING   │  mcp_server/ + rag/ingestion.py
│                     │
│  SEC EDGAR API      │  → Looks up Apple's CIK number
│  edgartools library │  → Downloads the latest 10-K filing (HTML, ~150 pages)
│  Rate limiter       │  → Respects SEC's 10 req/sec limit
└────────┬────────────┘
         │  Raw HTML filing (~5–20 MB)
         ▼
┌─────────────────────┐
│  2. CHUNKING &      │  rag/ingestion.py
│     EMBEDDING       │
│                     │
│  Section extractor  │  → Splits filing into named sections
│  Text splitter      │     (Item 1A: Risk Factors, Item 7: MD&A, etc.)
│  Deduplicator       │  → Cuts each section into ~2000-char overlapping chunks
│                     │  → Removes duplicate chunks via normalized MD5 hash
│  Sentence-          │  → Converts each chunk into a 384-dimension vector
│  Transformers       │     (all-MiniLM-L6-v2 model)
└────────┬────────────┘
         │  ~200–300 vector-embedded Document objects
         ▼
┌─────────────────────┐
│  3. VECTOR STORE    │  rag/vector_store.py
│                     │
│  ChromaDB           │  → Saves vectors to disk (chroma_db_AAPL/)
│  Per-company DB     │  → Next time you open AAPL, this step is skipped
│                     │     (cached — loads in 5 seconds instead of 5 minutes)
└────────┬────────────┘
         │
         ▼  ← You're now ready to ask questions
         │
You type: "What are the main risks Apple faces?"
          │
          ▼
┌─────────────────────┐
│  4. QUERY ENGINE    │  analysis/gemini_engine.py
│                     │
│  Query Enhancer     │  → Expands your query with financial synonyms
│                     │     "risks" → adds "Item 1A Risk Factors"
│  MMR Retriever      │  → Searches ChromaDB for the 5 most relevant chunks
│                     │     (MMR = balances relevance AND diversity, λ=0.3)
│  Prompt Builder     │  → Wraps retrieved chunks + your question into a prompt
│                     │     from analysis/prompts.py
└────────┬────────────┘
         │  Formatted prompt with source citations
         ▼
┌─────────────────────┐
│  5. GEMINI AI       │  Google Gemini 2.5 Flash
│                     │
│  1M token context   │  → Reads the prompt and generates a cited answer
│  Low temperature    │  → Cites [Source 1], [Source 2] etc. from the chunks
│  (0.3)              │
└────────┬────────────┘
         │
         ▼
Answer + source sections streamed live in the Streamlit UI
```

---

## Tab 2 — Year-over-Year Comparison

Instead of asking one question, you can compare an entire company's current 10-K against last year's:

```
Click "Run Year-over-Year Comparison"
          │
          ▼
┌─────────────────────────────────────────────────────┐
│  Fetch current 10-K  (index 0 from EDGAR history)   │
│  Fetch prior-year 10-K  (index 1)                   │
│  Trim each to 80,000 chars for Gemini context        │
└───────────────────────┬─────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
   Financial + Strategic       Risk Factor
      Comparison               Analysis
   (COMPARISON_PROMPT)    (RISK_ANALYSIS_PROMPT)
            │                       │
            ▼                       ▼
   Revenue · Margin ·        New risks · Removed
   EPS changes with          risks · Modified
   % change calc             language · Severity
```

The comparison prompt includes structured headings (Revenue & Growth, Profitability, Risk Changes, Strategic Shifts, Operational Changes, Accounting Policy Changes) so the output is consistently organized.

---

## Tab 3 — Company Comparison

Side-by-side analysis of two companies without any prior sidebar setup:

```
Enter: "AAPL" vs "MSFT"
          │
          ▼
┌────────────────────────────────────────────────────────┐
│  Auto-process each company if not cached               │
│    process_filing(ticker) → embed → chroma_db_<TICKER> │
│                                                         │
│  Run Beneish M-Score for both  (SEC XBRL data)         │
│  Run Linguistic Analysis for both                       │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  Display panel                                          │
│  ├── Beneish M-Score side by side (metric cards)       │
│  ├── Linguistic indicators side by side (3 metrics)    │
│  ├── Fraud Risk Summary table (M-Score · Risk · Flags) │
│  └── AI Narrative Comparison (on demand)               │
│          │                                              │
│          ▼                                              │
│  stream_compare_companies()                             │
│    → retrieves top 10 chunks per company from ChromaDB  │
│    → builds COMPANY_COMPARISON_PROMPT                   │
│    → streams Gemini response token by token             │
│    → post-processes output to strip rendering artifacts │
└────────────────────────────────────────────────────────┘
```

### Output Rendering Cleanup

Gemini's markdown output occasionally includes formatting that Streamlit misinterprets — bold markers wrapped around dollar amounts render as LaTeX math, and backtick-wrapped numbers render as monospace code. The `_clean_latex_artifacts()` function in `ui/app.py` strips these before display:

```python
text = re.sub(r'\*\*(\$[\d,\.]+)', r'\1', text)          # **$414 → $414
text = re.sub(r'([\d,\.]+\s*(?:million|billion|trillion))\*\*', r'\1', text)
text = re.sub(r'`([^`]+)`', r'\1', text)                  # `any phrase` → any phrase
```

The `COMPANY_COMPARISON_PROMPT` also includes explicit formatting rules to prevent these patterns at the source.

---

## Fraud Detection — How It Works

When you click **"Analyze Filing"**, three independent fraud checks run:

### Check 1 — Beneish M-Score (Earnings Manipulation)
```
SEC XBRL API → fetches 8 financial metrics for current + prior year
             → calculates 8 ratios (receivables growth, margin change, etc.)
             → plugs into Beneish (1999) formula:
                M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI ...
             → M > -2.22 → potential manipulation flagged
```
Think of it as a "cooked books detector" — based on academic research with ~76% accuracy.

### Check 2 — Linguistic Analysis
```
Full filing text → tokenized
                → measures passive voice ratio     (>30% = evasiveness flag)
                → measures hedging language        (>4% = uncertainty flag)
                → measures lexical diversity       (<20% = repetition flag)
                → measures self-reference ("we")   (low = distancing flag)
```
Fraudulent filings tend to use more passive voice ("mistakes were made") and hedging ("results may vary") to obscure accountability.

### Check 3 — Narrative vs. Numbers Discrepancy
```
MD&A section text → claims extracted ("revenue increased 15%")
Financial tables  → actual numbers fetched
                  → directional mismatch?  → HIGH severity flag
                  → magnitude >10% off?    → MEDIUM severity flag
```
Catches cases where management's narrative contradicts the actual reported numbers.

The discrepancy checker is tuned to avoid false positives: it requires explicit units in dollar extractions, filters out operating cash flow sentences from net income matching, and normalizes dollar values before comparison.

---

## Project Structure — Annotated

```
Int_fin_doc/
│
├── ui/
│   └── app.py                  ← START HERE. The Streamlit web app.
│                                 Three tabs: Q&A, Compare Years, Compare Companies.
│
├── analysis/
│   ├── gemini_engine.py         ← The "brain". Manages all Gemini API calls,
│   │                              query enhancement, RAG chain assembly,
│   │                              streaming, and company comparison.
│   └── prompts.py               ← The "scripts". Carefully engineered prompts
│                                  for Q&A, YoY comparison, risk analysis,
│                                  company comparison, and metric extraction.
│
├── rag/
│   ├── ingestion.py             ← Downloads + parses 10-K filings,
│   │                              splits into chunks, enriches metadata,
│   │                              deduplicates via normalized MD5 hash.
│   └── vector_store.py          ← Manages ChromaDB — saving, loading,
│                                  and MMR searching the vector database.
│
├── compliance/
│   ├── beneish.py               ← Beneish M-Score calculator.
│   │                              Fetches real XBRL data from SEC API.
│   ├── linguistics.py           ← Linguistic fraud signal detector.
│   └── discrepancy.py           ← MD&A vs. financial data cross-checker.
│
├── mcp_server/
│   ├── server.py                ← SEC EDGAR API integration (FastMCP).
│   │                              Translates ticker → CIK → filing URLs.
│   └── utils.py                 ← Rate limiter + retry logic for SEC API.
│
├── tests/
│   ├── unit/                    ← Fast tests, no network required.
│   │   ├── test_compliance.py
│   │   ├── test_mcp_server.py
│   │   └── test_rag.py
│   └── integration/             ← End-to-end tests (hit real SEC EDGAR).
│       └── test_end_to_end.py
│
├── chroma_db_AAPL/              ← Cached vector database for Apple.
├── chroma_db_MSFT/              ← Cached vector database for Microsoft.
│   (one folder per company)       Skips re-processing on future visits.
│
├── Dockerfile                   ← Packages the app into a container.
├── docker-compose.yaml          ← Runs the container with volumes + env vars.
├── requirements.txt             ← All Python dependencies.
└── .env                         ← Your API keys (never committed to git).
```

---

## The Technology Stack — Why Each Tool Was Chosen

| Tool | Role | Why This One |
|---|---|---|
| **Google Gemini 2.5 Flash** | Answering questions | 1 million token context — can read an entire 10-K at once without chunking loss |
| **LangChain** | Wiring RAG together | Standard framework for connecting retriever → prompt → LLM |
| **ChromaDB** | Vector database | Runs locally on disk, no external service needed, fast for small-medium datasets |
| **Sentence Transformers** (`all-MiniLM-L6-v2`) | Converting text to vectors | Fast, lightweight, good semantic understanding for financial English |
| **edgartools** | Parsing 10-K HTML | Understands SEC filing structure — extracts named sections cleanly |
| **Streamlit** | Web UI | Pure Python, no frontend code needed, fast to build |
| **FastMCP** | SEC API wrapper | Model Context Protocol — standardized tool interface for AI systems |

---

## Real-Life Use Cases

### Use Case 1 — Individual Investor Due Diligence
**Scenario:** You're considering buying Tesla stock before earnings. You want to understand their key risks and whether management is being honest.

**What you do:**
1. Enter `TSLA` → system fetches the latest 10-K (takes ~5 min first time)
2. Ask: *"What are Tesla's biggest supply chain risks?"*
3. Ask: *"Has Tesla's gross margin been deteriorating?"*
4. Check the Beneish M-Score to see if earnings quality looks normal
5. Check linguistic flags to see if management language has become more evasive

**Without this tool:** You'd spend 3–4 hours reading a 400-page PDF and doing manual calculations.

---

### Use Case 2 — Competitive Analysis (Business Analyst / MBA Student)
**Scenario:** You're writing a competitive analysis comparing Apple vs. Microsoft.

**What you do:**
1. Go to the **Compare Companies** tab
2. Enter `AAPL` and `MSFT`
3. View the side-by-side M-Score, linguistic indicators, and fraud risk table
4. Click **Generate AI Comparison** for a narrative analysis of revenue, margins, risks, and strategy

**Value:** Gets cited figures directly from official filings with quantitative fraud signals alongside the narrative.

---

### Use Case 3 — Fraud / Forensic Accounting Research
**Scenario:** A finance researcher wants to study whether companies in a distressed sector show pre-bankruptcy fraud signals.

**What you do:**
1. Run M-Score calculations across multiple tickers
2. Look for HIGH risk ratings (M-Score > -1.78) alongside EXCESSIVE_HEDGING linguistic flags
3. Cross-reference with narrative discrepancies in MD&A

**Real example:** Enron's 10-K filings showed abnormal DSRI (receivables inflating faster than revenue) and excessive positive language — both signals this system detects automatically.

---

### Use Case 4 — Year-over-Year Risk Monitoring
**Scenario:** You want to see which new risks appeared in a company's latest 10-K that weren't in the prior year.

**What you do:**
1. Analyze the company via the sidebar
2. Go to the **Compare Years** tab → select "Risk Factor Analysis"
3. Get a structured breakdown of NEW, REMOVED, and MODIFIED risks with severity ratings

**Value:** Instant risk delta — no need to manually diff two 400-page documents.

---

### Use Case 5 — Academic / Teaching Tool
**Scenario:** A finance professor wants students to analyze real 10-K filings without spending the whole class decoding legal language.

**What you do:**
- Students enter any ticker and ask structured questions
- The system provides cited answers directly from the source document
- Students can verify each answer by expanding the source section
- Teaches students where to find information in real filings

---

## Performance Expectations

| Action | First Run | After Caching |
|---|---|---|
| Load a new company (download + embed) | 3–7 minutes | 5–10 seconds |
| Answer a Q&A question | 5–15 seconds | 5–15 seconds |
| Run full compliance report | 30–60 seconds | 30–60 seconds |
| Year-over-year comparison | 1–3 minutes | 1–3 minutes |
| Company comparison (AI narrative) | 30–90 seconds | instant (cached) |
| Disk space per company | 50–200 MB | (already used) |

Caching is per-company. Once AAPL is processed, it loads instantly every time. The vectors are saved in `chroma_db_AAPL/` locally.

---

## Limitations to Know

| Limitation | Why It Exists |
|---|---|
| US companies only | SEC EDGAR only covers SEC-registered companies |
| Annual data only (10-K) | System is optimized for annual reports; quarterly (10-Q) not yet supported |
| Data is as fresh as the last 10-K | 10-Ks are filed 60–90 days after fiscal year end |
| AI answers need verification | Gemini can misread numbers — always check sources shown |
| M-Score is ~76% accurate | Academic model, not a guarantee of fraud |
| First run is slow | Embedding 200+ chunks locally takes a few minutes |

---

## Quick Start (3 Steps)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API keys
# Create a .env file with:
GOOGLE_API_KEY=your_gemini_api_key_here
USER_AGENT=YourName your@email.com

# 3. Launch the app
streamlit run ui/app.py
# Opens at http://localhost:8501
```

Then enter any ticker (AAPL, MSFT, JPM, WMT, etc.) in the sidebar and click **Analyze Filing**.
