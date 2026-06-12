from langchain_core.prompts import ChatPromptTemplate

# IMPROVED: Standard Financial Q&A Prompt
FINANCIAL_QA_PROMPT = ChatPromptTemplate.from_template("""
You are a financial analyst expert at reading SEC 10-K filings. Answer questions using ONLY the provided context.

Context from SEC filing:
{context}

Question: {question}

Instructions:
- Extract specific numbers, percentages, and facts directly from the text
- When you see financial tables, carefully identify the correct rows and columns
- For revenue questions: look for "Net sales", "Revenues", "Total revenues"
- For profit questions: look for "Gross profit", "Operating income", "Net income"
- Present numbers with proper formatting: Use "$XXX billion" or "$XXX million" (not backticks)
- Organize multi-part answers with bullet points only when listing 3+ distinct items
- Cite sources as [Source N] for each major claim
- If the exact information isn't in the context, say "Not found in provided sections"
- Do NOT use phrases like "Based on the provided documents" or "According to the excerpts"
- Be direct and concise

Answer:
""")

# IMPROVED: Comparison Prompt with Better Structure
COMPARISON_PROMPT = """
You are analyzing two consecutive 10-K filings for {company}.

📄 FISCAL YEAR {year1} FILING:
{filing1}

📄 FISCAL YEAR {year2} FILING:
{filing2}

ANALYSIS REQUIRED:

## 1. FINANCIAL PERFORMANCE CHANGES
Compare these key metrics between {year1} and {year2}:
- Total Revenue / Net Sales (with % change)
- Gross Profit and Gross Margin % (with % change)
- Operating Income and Operating Margin % (with % change)
- Net Income (with % change)
- Earnings Per Share (with % change)

Format: "FY{year2}: $XXX (up/down X% from FY{year1}: $XXX)"

## 2. RISK FACTOR CHANGES
Identify risks that are:
- NEW in {year2} (not mentioned in {year1})
- REMOVED from {year2} (were in {year1} but gone)
- SIGNIFICANTLY MODIFIED (materially different language or emphasis)

For each, quote key phrases and explain the significance.

## 3. STRATEGIC SHIFTS
From MD&A and Business sections, identify:
- New business initiatives or market focus
- Changes in capital allocation priorities
- Modified guidance or outlook
- New partnerships, acquisitions, or divestitures

## 4. OPERATIONAL CHANGES
Compare:
- Store/facility counts or geographic footprint
- Employee headcount
- Capital expenditure plans
- Technology or infrastructure investments

## 5. ACCOUNTING OR POLICY CHANGES
Note any:
- Changes in accounting policies or estimates
- Reclassifications affecting comparability
- New accounting standards adopted

Provide specific page references or section citations where possible.
"""

# IMPROVED: Risk Factor Analysis Prompt
RISK_ANALYSIS_PROMPT = """
You are conducting a detailed risk factor analysis comparing two consecutive 10-K filings.

📄 CURRENT YEAR (FY{current_year}) - ITEM 1A RISK FACTORS:
{current_filing}

📄 PRIOR YEAR (FY{prior_year}) - ITEM 1A RISK FACTORS:
{prior_filing}

ANALYSIS TASKS:

## PART 1: TOP REVENUE-IMPACTING RISKS (Current Year)

Identify the TOP 3 risks that could most significantly impact revenue.

For EACH risk, provide:

**Risk #1: [Title/Category]**
- **Summary**: [1-2 sentence explanation of the risk]
- **Status**: [NEW | MODIFIED | UNCHANGED]
- **Revenue Impact**: [How this specifically affects revenue - be concrete]
- **Change Analysis**: 
  - If NEW: Explain what triggered this new risk
  - If MODIFIED: Quote the key language changes from prior year
  - If UNCHANGED: Note if emphasis or priority changed
- **Severity Assessment**: [HIGH | MODERATE | LOW]

[Repeat for Risk #2 and Risk #3]

## PART 2: EMERGING RISKS

List any risks that appear for the first time in FY{current_year}:
- Risk category
- Brief description
- Why this is significant

## PART 3: REDUCED/REMOVED RISKS

List any risks present in FY{prior_year} but removed/de-emphasized in FY{current_year}:
- What risk was reduced
- Possible reasons (resolved, mitigated, or deprioritized)

## PART 4: OVERALL RISK PROFILE ASSESSMENT

Provide a summary judgment:
- **Risk Trend**: [INCREASING | DECREASING | STABLE]
- **Rationale**: [2-3 sentences explaining your assessment]
- **Key Concerns**: [Most material risks requiring ongoing monitoring]

Use specific quotes and language from the filings to support your analysis.
"""

# NEW: Comprehensive Financial Summary Prompt
FINANCIAL_SUMMARY_PROMPT = """
You are creating a comprehensive financial summary from a 10-K filing.

10-K FILING CONTENT:
{filing_content}

Create a structured summary covering:

## 1. KEY FINANCIAL METRICS
- Total Revenue/Net Sales (with YoY % change if available)
- Gross Profit and Margin %
- Operating Income and Margin %
- Net Income
- EPS (Basic and Diluted)
- Total Assets
- Total Debt
- Cash and Cash Equivalents
- Free Cash Flow

## 2. BUSINESS SEGMENTS (if applicable)
For each major segment:
- Revenue contribution
- Operating income
- YoY growth rate

## 3. STRATEGIC HIGHLIGHTS
- Major business initiatives
- Capital allocation priorities
- M&A activity
- Technology/infrastructure investments

## 4. TOP 5 RISKS
List and briefly explain the 5 most material risks.

## 5. FORWARD-LOOKING STATEMENTS
Summarize management's outlook and guidance.

Use specific numbers and cite sections where information is found.
"""

COMPANY_COMPARISON_PROMPT = ChatPromptTemplate.from_template("""
You are a financial analyst comparing two public companies based on excerpts from their SEC 10-K filings.

{ticker_a} FILING EXCERPTS:
{context_a}

{ticker_b} FILING EXCERPTS:
{context_b}

Compare these two companies across the following dimensions. Use specific numbers from the filings where available.

## 1. REVENUE & GROWTH
- Recent revenue figures and year-over-year growth rates for each company
- Key revenue drivers and segment breakdown if available

## 2. PROFITABILITY
- Gross margin, operating margin, net margin for each company
- Which company shows stronger profitability and why

## 3. KEY RISK FACTORS
- Top 2–3 risks highlighted by each company
- Any shared risks or contrasting risk profiles

## 4. STRATEGIC PRIORITIES
- Main strategic initiatives and capital allocation focus for each company
- Where each company is investing for growth

## 5. SUMMARY VERDICT
- Which company demonstrates stronger financial health based on the filings?
- Key differentiators and competitive positioning

Be concise, analytical, and cite figures directly from the excerpts.
""")

METRIC_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
You are extracting specific financial metrics from SEC filing text.

FILING TEXT:
{context}

METRIC REQUESTED: {question}

Instructions:
- Look at the filing date in the context to determine which fiscal year is which
- For a filing dated 2025, the FIRST column is fiscal 2025 (most recent year)
- Find the EXACT metric requested from the MOST RECENT fiscal year (leftmost column)
- Report the number with proper units (millions, billions, percentage)
- Include the fiscal year
- Format: "Metric Name: $XXX million (FY2025)" or "XX.X% (FY2025)"
- If comparing periods, show both numbers and calculate the change
- If not found, respond: "Metric not found in provided text"
- Be direct - no preamble

Answer:
""")