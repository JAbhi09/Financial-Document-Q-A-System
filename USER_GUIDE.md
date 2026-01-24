# User Guide: Intelligent Financial Document Q&A System

## Table of Contents
1. [Overview](#1-overview)
2. [System Requirements](#2-system-requirements)
3. [Installation & Setup](#3-installation--setup)
4. [Running the Application](#4-running-the-application)
5. [Using the System](#5-using-the-system)
6. [Advanced Features](#6-advanced-features)
7. [Troubleshooting](#7-troubleshooting)
8. [Architecture Overview](#8-architecture-overview)
9. [FAQ](#9-faq)

---

## 1. Overview

The **Intelligent Financial Document Q&A System** is an AI-powered platform that helps you analyze SEC 10-K filings using natural language queries. The system combines:

- **SEC EDGAR Integration**: Automatically fetches official financial filings
- **RAG (Retrieval-Augmented Generation)**: Finds relevant information in documents
- **Gemini AI**: Provides intelligent analysis and answers
- **Compliance Analysis**: Detects potential financial fraud indicators
- **Interactive UI**: User-friendly Streamlit interface

### What Can You Do?
- Ask questions about company financials in plain English
- Extract and compare financial metrics across years
- Identify risk factors and business strategies
- Detect potential earnings manipulation using the Beneish M-Score
- Analyze linguistic patterns that may indicate fraud

---

## 2. System Requirements

### Operating System
- **Windows**: Windows 10 or higher
- **macOS**: macOS 10.14 (Mojave) or higher
- **Linux**: Ubuntu 20.04+ or equivalent

### Software Prerequisites
- **Python**: Version 3.10 or higher (3.11 recommended)
  - Check your version: `python --version` or `python3 --version`
- **pip**: Python package manager (usually included with Python)
- **Git**: For cloning the repository (optional)

### API Keys Required
1. **Google Gemini API Key** (Required)
   - Get your free API key from [Google AI Studio](https://aistudio.google.com/)
   - Click on "Get API Key" → Create or select a project → Copy the key
   - Note: Free tier has usage limits; consider upgrading for heavy use

2. **Email Address for SEC EDGAR** (Required)
   - The SEC requires a valid email in the User-Agent header
   - Format: `YourName your_email@example.com`
   - This is **mandatory** for compliance with SEC policies

### Hardware Recommendations
- **RAM**: Minimum 4GB, 8GB+ recommended for better performance
- **Disk Space**: At least 2GB free space for dependencies and cached data
- **Internet**: Stable broadband connection for API calls and document downloads

---

## 3. Installation & Setup

### Step 1: Clone or Download the Repository

```bash
# Using Git
git clone <repository-url>
cd Int_fin_doc

# Or download and extract the ZIP file, then navigate to the folder
cd path/to/Int_fin_doc
```

### Step 2: Create a Virtual Environment

Using a virtual environment is **strongly recommended** to avoid dependency conflicts.

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> **Note**: When the virtual environment is active, you'll see `(venv)` at the beginning of your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- `streamlit` - Web UI framework
- `langchain` & `langchain-google-genai` - LLM orchestration
- `chromadb` - Vector database for document embeddings
- `edgartools` - SEC EDGAR API wrapper
- `pandas` - Data manipulation
- `nltk` - Natural language processing
- `sentence-transformers` - Text embeddings
- And more...

**Installation time**: Typically 2-5 minutes depending on your internet speed.

### Step 4: Download NLTK Data

Some linguistic analysis features require NLTK resources:

```python
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
```

### Step 5: Configure Environment Variables

You have two options:

#### Option A: Use a `.env` File (Recommended)

Create a file named `.env` in the project root directory:

```env
GOOGLE_API_KEY=your_actual_api_key_here
USER_AGENT=YourName your_email@example.com
```

#### Option B: Set Temporary Environment Variables

**Windows (PowerShell):**
```powershell
$env:GOOGLE_API_KEY="your_actual_api_key_here"
$env:USER_AGENT="YourName your_email@example.com"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_API_KEY=your_actual_api_key_here
set USER_AGENT=YourName your_email@example.com
```

**macOS/Linux:**
```bash
export GOOGLE_API_KEY="your_actual_api_key_here"
export USER_AGENT="YourName your_email@example.com"
```

> **Important**: Replace placeholders with your actual values. Never share your API key publicly!

---

## 4. Running the Application

### Starting the Server

From the project root directory, run:

```bash
streamlit run ui/app.py
```

### What Happens Next

1. **Server Initialization**: Streamlit will start a local web server
2. **Auto-Launch**: Your default browser should automatically open to `http://localhost:8501`
3. **Manual Access**: If the browser doesn't open, manually navigate to the URL shown in the terminal

### Stopping the Application

- Press `Ctrl+C` in the terminal where Streamlit is running
- Close the terminal window

### Port Already in Use?

If port 8501 is already occupied:

```bash
streamlit run ui/app.py --server.port 8502
```

---

## 5. Using the System

### Initial Configuration (Sidebar)

When you first open the application, configure these settings in the left sidebar:

1. **Gemini API Key**: 
   - Enter your API key here if you didn't set it as an environment variable
   - The application will save this for the current session

2. **Company Ticker Symbol**:
   - Enter a valid stock ticker (e.g., `AAPL`, `MSFT`, 'WMT')
   - Must be a company that files 10-K reports with the SEC

3. **Load Documents**:
   - Click the "Load/Process Documents" button
   - The system will:
     - Fetch the latest 10-K filing from SEC EDGAR
     - Parse the document into sections
     - Create embeddings and store them in ChromaDB
     - **First-time processing may take 2-5 minutes**

### Analysis Modes

#### 1. Q&A Chat Mode

**Use Case**: Ask specific questions about the company's filing

**How to Use**:
1. Navigate to the "Q&A (Chat)" tab
2. Type your question in natural language
3. Examples:
   - "What are the company's main revenue streams?"
   - "Summarize the risk factors section"
   - "What does the company say about supply chain challenges?"
   - "Compare revenue growth between 2023 and 2024"

**Features**:
- **Context-Aware**: Uses RAG to find relevant document sections
- **Citations**: Click "Sources" to see exact page numbers and excerpts
- **Conversational**: Ask follow-up questions for deeper analysis
- **Streaming Responses**: Watch answers generate in real-time

**Tips**:
- Be specific in your questions for better results
- Reference specific sections (e.g., "In the MD&A section...")
- Ask comparative questions across years

---

#### 2. Financial Analysis Mode

**Use Case**: Extract and visualize key financial metrics

**What You'll See**:
- **Revenue Trends**: Year-over-year comparisons
- **Profitability Metrics**: Net income, margins, EPS
- **Cash Flow Analysis**: Operating, investing, financing activities
- **Balance Sheet Highlights**: Assets, liabilities, equity

**How It Works**:
- The system uses Gemini AI to extract structured data from financial tables
- Automatically calculates percentage changes
- Highlights significant trends (e.g., >10% change)

**Limitations**:
- Accuracy depends on document parsing quality
- Complex footnotes may not be fully captured
- Always verify critical numbers with the original 10-K

---

#### 3. Compliance & Fraud Detection

**Use Case**: Identify potential red flags in financial reporting

##### A. Red Flag Analysis

The system checks for linguistic patterns that may indicate attempts to obscure poor performance:

**Vagueness Indicators**:
- Excessive use of hedging words ("may", "could", "possibly")
- Ambiguous references ("certain items", "various factors")
- Lack of specific quantitative data

**Hedging Language**:
- Conditional statements that avoid commitment
- Qualifiers that dilute statements

**Output**:
- Red flag score (0-100, higher = more suspicious)
- Specific examples from the document
- Context around flagged phrases

##### B. Beneish M-Score

**What Is It?**
The Beneish M-Score is a mathematical model that estimates the probability of earnings manipulation based on financial ratios.

**How It Works**:
1. Extracts financial data from multiple years
2. Calculates 8 key ratios:
   - **DSRI**: Days Sales in Receivables Index
   - **GMI**: Gross Margin Index
   - **AQI**: Asset Quality Index
   - **SGI**: Sales Growth Index
   - **DEPI**: Depreciation Index
   - **SGAI**: Sales, General & Administrative Expenses Index
   - **LVGI**: Leverage Index
   - **TATA**: Total Accruals to Total Assets

3. Applies the Beneish formula
4. Interprets the result:
   - **M-Score > -1.78**: High likelihood of manipulation (Red Zone)
   - **M-Score ≤ -1.78**: Low likelihood of manipulation (Safe Zone)

**Caveats**:
- Not a definitive fraud detector
- Industry-specific factors may affect accuracy
- Should be used alongside other due diligence
- Historical data quality impacts results

---

## 6. Advanced Features

### Document Caching

**How It Works**:
- After first processing, documents are cached in the `chroma_db_<TICKER>` folder
- Subsequent loads are much faster (usually < 10 seconds)
- Each ticker has its own isolated database

**Force Refresh**:
If you want to re-fetch and re-process documents:
1. Delete the `chroma_db_<TICKER>` folder manually
2. Click "Load/Process Documents" again

### Multi-Company Analysis

To analyze multiple companies:
1. Enter the first ticker and process documents
2. Ask your questions
3. Change the ticker in the sidebar
4. Click "Load/Process Documents" for the new company
5. The system maintains separate databases for each

### Exporting Data

Currently, the UI doesn't have built-in export. To save results:
- **Copy/Paste**: Highlight and copy text from the UI
- **Screenshot**: Use your OS screenshot tool
- **Browser Save**: Right-click → Save Page As (HTML)

### Custom Prompts (Developers)

Advanced users can modify prompt templates in:
- `ui/app.py` - Main application prompts
- `rag/ingestion.py` - Document processing prompts
- `compliance/*.py` - Compliance analysis prompts

---

## 7. Troubleshooting

### Common Issues and Solutions

#### Problem: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
1. Ensure your virtual environment is activated
2. Run `pip install -r requirements.txt` again
3. If still failing, try: `pip install <missing-module-name>`

---

#### Problem: `Resource 'punkt_tab' not found`

**Solution**:
```python
python -c "import nltk; nltk.download('punkt_tab')"
```

---

#### Problem: `404 Not Found: models/gemini-2.5-flash`

**Cause**: The API key doesn't have access to Gemini 2.5 Flash

**Solution**:
1. Verify your API key is correct
2. Check if the model is available in your region
3. Try using `gemini-1.5-flash` instead (modify `ui/app.py`)

---

#### Problem: SEC Rate Limiting / Access Denied

**Symptoms**:
- `403 Forbidden` errors
- `Your request rate is too high`

**Solution**:
1. Verify your `USER_AGENT` environment variable is set correctly
2. Wait 10-15 minutes before retrying
3. Ensure format is: `Name email@example.com`
4. Check [SEC Fair Access Policy](https://www.sec.gov/os/webmaster-faq#code-support)

---

#### Problem: ChromaDB Errors / Corrupted Database

**Solution**:
Delete the problematic database and re-process:
```bash
# Windows
rmdir /s chroma_db_<TICKER>

# macOS/Linux
rm -rf chroma_db_<TICKER>
```

Then reload documents in the UI.

---

#### Problem: Slow Performance / Timeouts

**Possible Causes**:
- Large documents (>500 pages)
- Slow internet connection
- API rate limiting

**Solutions**:
- Be patient on first load (can take 5+ minutes for large filings)
- Check your internet speed
- Reduce chunk size in `rag/ingestion.py` (advanced)

---

#### Problem: Streamlit Won't Start

**Error**: `command not found: streamlit`

**Solution**:
```bash
# Reinstall Streamlit
pip install --upgrade streamlit

# Verify installation
streamlit --version
```

---

### Getting Additional Help

1. **Check the Logs**: Streamlit shows detailed errors in the terminal
2. **Inspect the Document**: Download the 10-K manually from SEC EDGAR to verify it exists
3. **Test API Key**: Try a simple API call in Python to verify your Gemini key works
4. **Community Support**: Search for similar issues on Stack Overflow or GitHub

---

## 8. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI (ui/app.py)                │
│            User Interface & Application Logic               │
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

### Module Descriptions

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **UI** | Web interface, user interaction | `ui/app.py` |
| **MCP Server** | Fetch documents from SEC EDGAR | `mcp_server/server.py`, `mcp_server/utils.py` |
| **RAG** | Document ingestion, embedding, retrieval | `rag/ingestion.py`, `rag/vector_store.py` |
| **Compliance** | Fraud detection, linguistic analysis | `compliance/beneish.py`, `compliance/linguistics.py` |
| **Analysis** | Integration with Gemini for Q&A | Embedded in `ui/app.py` |

### Data Flow

1. **User enters ticker** → MCP Server fetches 10-K from SEC EDGAR
2. **Document parsed** → RAG module chunks and embeds text
3. **User asks question** → RAG retrieves relevant chunks
4. **Chunks sent to Gemini** → AI generates answer with context
5. **Answer displayed** → User sees response with citations

---

## 9. FAQ

### Q: Is my API key stored securely?
**A**: API keys are stored in environment variables or the `.env` file locally on your machine. They are never transmitted except to Google's Gemini API. Ensure `.env` is in `.gitignore` if using version control.

### Q: Can I analyze companies outside the US?
**A**: The system is designed for US companies that file with the SEC. International companies with ADRs (American Depositary Receipts) that file 10-Ks can be analyzed.

### Q: How accurate is the Beneish M-Score?
**A**: Studies show ~76% accuracy in detecting manipulators. It's a screening tool, not definitive proof. Always conduct thorough due diligence.

### Q: Can I use this for real-time stock trading?
**A**: **No**. This system analyzes historical 10-K filings (annual reports). It does not provide real-time data or investment advice. Consult a licensed financial advisor.

### Q: What's the cost of using Gemini API?
**A**: Google AI Studio offers a free tier with rate limits. For production use, check [Gemini API Pricing](https://ai.google.dev/pricing).

### Q: How often are 10-K filings updated?
**A**: Companies file annual 10-Ks once per year, typically within 60-90 days after fiscal year-end. The system always fetches the most recent filing available.

### Q: Can I run this on a server?
**A**: Yes! Deploy Streamlit to cloud platforms like:
- Google Cloud Run
- AWS EC2
- Heroku
- Streamlit Cloud (free for public repos)

Ensure environment variables are configured in the deployment environment.

### Q: Is this open source?
**A**: Check the project's `LICENSE` file. Ensure compliance with SEC policies and API terms of service when distributing.

---

## Quick Reference Commands

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt_tab')"

# Run the application
streamlit run ui/app.py

# Deactivate virtual environment
deactivate
```

---

## Support and Feedback

For issues, improvements, or questions:
- Review the troubleshooting section above
- Check the project's issue tracker (if available)
- Consult the codebase documentation in individual files

**Remember**: This tool is for educational and analytical purposes. Always verify critical financial information with official SEC filings.

---

*Last Updated: January 2026*
