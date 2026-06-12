# import streamlit as st
# import asyncio
# import os
# import sys

# # Add project root to path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from rag.ingestion import process_filing, fetch_latest_10k_filing
# from rag.vector_store import add_documents_to_store, get_vector_store
# from analysis.gemini_engine import GeminiAnalysisEngine
# from compliance.linguistics import analyze_linguistic_fraud_indicators
# from compliance.beneish import calculate_beneish_m_score
# # Using edgartools for financial data fetching to keep it sync/simple for the UI
# from edgar import Company

# st.set_page_config(page_title="Financial Compliance AI", layout="wide")

# st.title("📊 Intelligent Financial Document Q&A & Compliance")

# # Sidebar
# st.sidebar.header("Configuration")
# api_key = st.sidebar.text_input("Google API Key", type="password")
# if api_key:
#     os.environ["GOOGLE_API_KEY"] = api_key

# ticker = st.sidebar.text_input("Enter Ticker Symbol (e.g. AAPL)", "AAPL")

# if st.sidebar.button("Analyze Filing"):
#     if not api_key:
#         st.error("Please enter a Google API Key.")
#     else:
#         with st.spinner(f"Fetching and processing 10-K for {ticker}..."):
#             try:
#                 # 1. Ingestion
#                 docs = process_filing(ticker)
#                 st.success(f"Successfully processed {len(docs)} chunks from 10-K.")
                
#                 # 2. Vector Store
#                 add_documents_to_store(docs, persist_directory=f"chroma_db_{ticker}")
#                 st.session_state['vector_store_path'] = f"chroma_db_{ticker}"
#                 st.session_state['processed_ticker'] = ticker
                
#                 # 3. Compliance Analysis
#                 # Get full text for linguistic analysis (concat chunks or use original)
#                 full_text = " ".join([d.page_content for d in docs])  
                
#                 # Linguistic
#                 st.subheader("🚩 Fraud Detection & Compliance Report")
#                 col1, col2 = st.columns(2)
                
#                 with col1:
#                     st.markdown("### Linguistic Indicators")
#                     ling_results = analyze_linguistic_fraud_indicators(full_text[:100000]) # Limit for performance
#                     st.json(ling_results)
#                     if ling_results['red_flags']:
#                         st.error(f"Red Flags Detected: {', '.join(ling_results['red_flags'])}")
#                     else:
#                         st.success("No linguistic red flags detected.")

#                 with col2:
#                     st.markdown("### Earnings Manipulation (Beneish M-Score)")
#                     # Mocking prior/current data for demo purposes since extracting
#                     # structured financials from raw text is complex without the specific XBRL parser active.
#                     # In a full prod app, we would query the XBRL API here.
#                     st.info("Fetching financial data for M-Score...")
#                     try:
#                         # Attempt to get financials via edgartools
#                         company = Company(ticker)
#                         financials = company.get_financials()
#                         # This is a placeholder as getting exact fields for Beneish requires mapping
#                         # For the portfolio demo, we define a dummy result or need the raw XBRL values
#                         # Let's show the logic usage:
#                         m_score_result = calculate_beneish_m_score(
#                             {"receivables": 100, "revenue": 1000}, # Dummy
#                             {"receivables": 90, "revenue": 900}    # Dummy
#                         )
#                         st.write("M-Score (Demo Data):", m_score_result['m_score'])
#                         st.caption("Note: Connected to live parser, but using demo values for calculation safety in this UI.")
#                     except Exception as e:
#                         st.error(f"Could not calculate M-Score: {e}")

#             except Exception as e:
#                 st.error(f"An error occurred: {str(e)}")

# # Q&A Section
# st.divider()
# st.header("💬 Document Q&A")

# if 'vector_store_path' in st.session_state:
#     query = st.text_input("Ask a question about the filing:")
#     if query:
#         with st.spinner("Analyzing..."):
#             engine = GeminiAnalysisEngine()
#             vector_store = get_vector_store(st.session_state['vector_store_path'])
#             qa_chain = engine.get_qa_chain(vector_store)
            
#             response = qa_chain.invoke({"input": query})
            
#             st.markdown("### Answer")
#             st.write(response["answer"])
            
#             with st.expander("View Sources"):
#                 for i, doc in enumerate(response["context"]):
#                     st.markdown(f"**Source {i+1}** (Section: {doc.metadata.get('section', 'N/A')})")
#                     st.text(doc.page_content[:300] + "...")
# else:
#     st.info("Please analyze a filing first to enable Q&A.")






import re
import streamlit as st
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.ingestion import process_filing, fetch_latest_10k_filing, fetch_10k_text
from rag.vector_store import add_documents_to_store, get_vector_store
from analysis.gemini_engine import GeminiAnalysisEngine
from compliance.linguistics import analyze_linguistic_fraud_indicators
from compliance.beneish import calculate_beneish_m_score_with_ticker
from compliance.discrepancy import (
    detect_discrepancies,
    extract_claims_from_text,
    build_financials_for_discrepancy,
)
from edgar import Company

st.set_page_config(page_title="Financial Compliance AI", layout="wide", page_icon="📊")

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
    .success-box { background-color: #d4edda; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; }
    .warning-box { background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; }
    .error-box { background-color: #f8d7da; padding: 15px; border-radius: 5px; border-left: 4px solid #dc3545; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Intelligent Financial Document Q&A & Compliance")

# Sidebar
st.sidebar.header("Configuration")
api_key = os.getenv("GOOGLE_API_KEY", "")
if api_key:
    st.sidebar.success("✓ API key loaded")
else:
    api_key = st.sidebar.text_input("Google API Key", type="password")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    else:
        st.sidebar.warning("⚠️ Enter your Google API key to continue")

ticker = st.sidebar.text_input("Enter Ticker Symbol (e.g. AAPL)", "AAPL").upper()

def _clean_latex_artifacts(text: str) -> str:
    text = re.sub(r'\*\*(\$[\d,\.]+)', r'\1', text)
    text = re.sub(r'([\d,\.]+\s*(?:million|billion|trillion))\*\*', r'\1', text)
    return text


def is_metric_query(query: str) -> bool:
    """Detect metric-focused queries with better accuracy"""
    query_lower = query.lower()
    
    # ✅ Explicit metric patterns
    metric_patterns = [
        'what was', 'what is the', 'how much', 'how many',
        'total revenue', 'net income', 'net sales',
        'cash', 'debt', 'assets', 'liabilities',
        'revenue in', 'income in', 'sales in',
        'price', 'cost', 'expense'
    ]
    
    # ❌ Exclude strategy/analysis questions (higher priority)
    strategy_patterns = [
        'strategy', 'approach', 'plan', 'initiative',
        'why', 'how does', 'how is', 'how are',
        'what are the', 'explain', 'describe',
        'risk', 'threat', 'challenge', 'opportunity',
        'compete', 'competition', 'market',
        'affect', 'impact', 'influence'
    ]
    
    # Check for strategy patterns first (disqualifies as metric query)
    if any(pattern in query_lower for pattern in strategy_patterns):
        return False
    
    # Then check for metric patterns
    has_metric_pattern = any(pattern in query_lower for pattern in metric_patterns)
    
    # Only classify as metric if:
    # 1. Has metric pattern AND
    # 2. Query is short (< 15 words) AND
    # 3. No strategy keywords
    return has_metric_pattern and len(query.split()) < 15

if st.sidebar.button("🔍 Analyze Filing", use_container_width=True):
    if not api_key:
        st.error("Please enter a Google API Key.")
    else:
        with st.spinner(f"Fetching and processing 10-K for {ticker}..."):
            try:
                # 1. Ingestion
                docs = process_filing(ticker)
                
                if not docs or len(docs) == 0:
                    st.error(f"No documents extracted for {ticker}. The filing structure may not be supported.")
                    st.info("Try a different ticker like: AAPL, MSFT, GOOGL, JPM, NFLX, WMT")
                    st.stop()
                
                st.success(f"Successfully processed {len(docs)} chunks from 10-K.")
                
                # 2. Vector Store
                with st.spinner("Building vector store..."):
                    add_documents_to_store(docs, persist_directory=f"chroma_db_{ticker}")
                    st.session_state['vector_store_path'] = f"chroma_db_{ticker}"
                    st.session_state['processed_ticker'] = ticker
                    st.session_state['docs_count'] = len(docs)
                    st.success("✓ Vector store created")
                
                # 3. Compliance Analysis
                st.divider()
                st.header("🚩 Fraud Detection & Compliance Report")
                
                # Get full text for linguistic analysis
                full_text = " ".join([d.page_content for d in docs])  
                
                col1, col2 = st.columns(2)
                
                # === LINGUISTIC ANALYSIS ===
                with col1:
                    st.subheader("📝 Linguistic Indicators")
                    with st.spinner("Analyzing language patterns..."):
                        try:
                            ling_results = analyze_linguistic_fraud_indicators(full_text[:100000])
                            
                            # Display metrics
                            metrics = ling_results.get('metrics', {})
                            
                            m1, m2, m3 = st.columns(3)
                            with m1:
                                st.metric("Lexical Diversity", f"{metrics.get('lexical_diversity', 0):.2%}")
                            with m2:
                                st.metric("Passive Voice", f"{metrics.get('passive_voice_ratio', 0):.2%}")
                            with m3:
                                st.metric("Hedging", f"{metrics.get('hedging_ratio', 0):.2%}")
                            
                            # Show red flags
                            red_flags = ling_results.get('red_flags', [])
                            if red_flags:
                                st.warning(f"⚠️ Red Flags: {', '.join(red_flags)}")
                            else:
                                st.success("✓ No linguistic red flags detected")
                            
                            with st.expander("View Detailed Metrics"):
                                st.json(ling_results)
                                
                        except Exception as e:
                            st.error(f"Linguistic analysis error: {str(e)}")

                # === BENEISH M-SCORE ===
                with col2:
                    st.subheader("📊 Earnings Manipulation (Beneish M-Score)")
                    with st.spinner("Fetching financial data from SEC..."):
                        try:
                            beneish_result = calculate_beneish_m_score_with_ticker(ticker, current_year=2024)
                            st.session_state['beneish_result'] = beneish_result

                            m_score    = beneish_result.get('m_score')
                            data_source = beneish_result.get('data_source', 'unknown')
                            risk_level  = beneish_result.get('risk_level', 'UNKNOWN')

                            if data_source == 'unavailable':
                                st.warning("SEC XBRL data unavailable for this company")
                                st.caption(beneish_result.get('message', ''))
                                st.info(
                                    "M-Score requires two consecutive years of XBRL financial data "
                                    "from SEC EDGAR. Try a larger company or a different year."
                                )
                            else:
                                st.success("✓ Using real SEC financial data")

                                if m_score is None:
                                    st.error("M-Score calculation failed")
                                    if 'error' in beneish_result:
                                        st.caption(f"Error: {beneish_result['error']}")
                                else:
                                    score_color = "🔴" if m_score > -1.78 else ("🟡" if m_score > -2.22 else "🟢")
                                    st.metric(
                                        f"{score_color} M-Score",
                                        f"{m_score:.3f}",
                                        delta=f"Risk: {risk_level}"
                                    )
                                    if beneish_result.get('manipulation_likely'):
                                        st.error("🚨 M-Score indicates potential earnings manipulation (> -2.22)")
                                    else:
                                        st.success("✓ M-Score within normal range (< -2.22)")

                                with st.expander("📋 View M-Score Components"):
                                    components    = beneish_result.get('components', {})
                                    interpretations = beneish_result.get('interpretation', {})
                                    if components:
                                        for key, value in components.items():
                                            interp = interpretations.get(key, '')
                                            flag = "⚠️" if any(w in interp for w in ["Inflating", "Deteriorating", "Aggressive", "Lower quality"]) else "✓"
                                            st.write(f"{flag} **{key.upper()}**: {value} — {interp}")
                                        st.markdown("---")
                                        st.markdown("""
**M-Score Guide:** < -2.50 very low · -2.50→-2.22 low · -2.22→-1.78 moderate ⚠️ · > -1.78 high 🔴
                                        """)
                                    else:
                                        st.info("Component details not available")

                        except Exception as e:
                            st.error(f"M-Score calculation error: {str(e)}")

                # === DISCREPANCY DETECTION (full width, below the two columns) ===
                st.markdown("---")
                st.subheader("🔍 MD&A Narrative vs. Financial Data")
                with st.spinner("Checking for narrative discrepancies..."):
                    try:
                        mda_docs = [
                            d for d in docs
                            if "Item 7" in d.metadata.get("section", "")
                        ]
                        mda_text = " ".join(d.page_content for d in mda_docs)

                        beneish_result = st.session_state.get('beneish_result', {})
                        raw_data = beneish_result.get('raw_data')

                        if not mda_text.strip():
                            st.info("No MD&A text found in the processed chunks.")
                        elif raw_data is None:
                            st.warning(
                                "Discrepancy check skipped — requires real SEC financial data "
                                "(Beneish M-Score data unavailable for this company)."
                            )
                        else:
                            claims     = extract_claims_from_text(mda_text)
                            financials = build_financials_for_discrepancy(
                                raw_data['current'], raw_data['prior']
                            )
                            discrepancies = detect_discrepancies(claims, financials)

                            if not claims:
                                st.info("No directional financial claims detected in MD&A text.")
                            elif not discrepancies:
                                st.success(f"✓ No discrepancies found across {len(claims)} MD&A claim(s)")
                                with st.expander("View extracted claims"):
                                    for c in claims:
                                        st.write(f"**{c['metric']}** — {c['direction']} | {c['sentence']}")
                            else:
                                high = [d for d in discrepancies if d['severity'] == 'HIGH']
                                med  = [d for d in discrepancies if d['severity'] == 'MEDIUM']
                                if high:
                                    st.error(f"🚨 {len(high)} HIGH-severity discrepancy(ies) detected")
                                if med:
                                    st.warning(f"⚠️ {len(med)} MEDIUM-severity discrepancy(ies) detected")

                                for disc in discrepancies:
                                    icon = "🚨" if disc['severity'] == 'HIGH' else "⚠️"
                                    with st.expander(f"{icon} {disc['type']} — {disc['claim']['metric']}"):
                                        st.markdown(f"**Description:** {disc['description']}")
                                        st.markdown(f"**MD&A claim:** _{disc['claim']['sentence']}_")
                                        actual = disc['actual']
                                        st.markdown(
                                            f"**Reported data:** value = {actual.get('value', 'N/A'):,.0f}, "
                                            f"change = {actual.get('change', 'N/A'):+,.0f}"
                                            if isinstance(actual.get('value'), (int, float))
                                            else f"**Reported data:** {actual}"
                                        )

                    except Exception as e:
                        st.error(f"Discrepancy check error: {str(e)}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())

# === TABS: Q&A + COMPARE YEARS + COMPARE COMPANIES ===
st.divider()

# Status bar — only shown when a single-company analysis has been run via sidebar
if 'vector_store_path' in st.session_state:
    ticker_info = st.session_state.get('processed_ticker', 'Unknown')
    docs_count  = st.session_state.get('docs_count', 0)
    _sb1, _sb2 = st.columns([3, 1])
    with _sb1:
        st.info(f"📄 Currently analyzing: **{ticker_info}** 10-K filing ({docs_count} chunks indexed)")
    with _sb2:
        if st.button("🔄 Clear Analysis", use_container_width=True):
            for key in ['vector_store_path', 'processed_ticker', 'docs_count', 'beneish_result']:
                st.session_state.pop(key, None)
            st.rerun()

tab_qa, tab_compare, tab_compare_co = st.tabs(
    ["💬 Document Q&A", "📅 Compare Years", "⚖️ Compare Companies"]
)

# ── TAB 1: Q&A (streaming) ──────────────────────────────────────────────
with tab_qa:
    if 'vector_store_path' not in st.session_state:
        st.info("👆 Please analyze a filing first using the sidebar to enable Q&A.")
        st.markdown("### 📈 Suggested Companies to Analyze:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
**Technology:**
- **AAPL** - Apple Inc.
- **MSFT** - Microsoft
- **GOOGL** - Alphabet/Google
- **META** - Meta/Facebook
- **NVDA** - NVIDIA
            """)
        with col2:
            st.markdown("""
**Retail & Consumer:**
- **WMT** - Walmart
- **AMZN** - Amazon
- **COST** - Costco
- **TGT** - Target
- **HD** - Home Depot
            """)
        with col3:
            st.markdown("""
**Financial & Other:**
- **JPM** - JPMorgan Chase
- **BAC** - Bank of America
- **JNJ** - Johnson & Johnson
- **PFE** - Pfizer
- **XOM** - Exxon Mobil
            """)
        st.info("💡 **Note:** Some companies like Nike (NKE) use different fiscal years and may file 10-K/A instead of standard 10-K.")
    else:
        query = st.text_input(
            "Ask a question about the filing:",
            placeholder="e.g., What was the total revenue in fiscal 2024?"
        )

        with st.expander("💡 Example Questions"):
            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown("**Financial Metrics:**")
                st.markdown("- What was the total revenue in fiscal 2024?")
                st.markdown("- What is the net income?")
                st.markdown("- How much cash does the company have?")
                st.markdown("- What are the capital expenditures?")
            with ec2:
                st.markdown("**Strategic & Risk:**")
                st.markdown("- What are the primary risk factors?")
                st.markdown("- What is the company's e-commerce strategy?")
                st.markdown("- What are the biggest competitive threats?")
                st.markdown("- How is climate change affecting operations?")

        if query:
            try:
                engine       = GeminiAnalysisEngine()
                vector_store = get_vector_store(st.session_state['vector_store_path'])

                use_metric = is_metric_query(query)
                if use_metric:
                    st.caption("🎯 Using focused metric extraction...")
                    raw_stream = engine.stream_metric_qa(query, vector_store)
                else:
                    st.caption("🔍 Using comprehensive analysis...")
                    raw_stream = engine.stream_qa(query, vector_store)

                context_docs: list = []

                def token_stream():
                    for chunk_type, data in raw_stream:
                        if chunk_type == "docs":
                            context_docs.extend(data)
                        else:
                            yield data

                st.markdown("### 💡 Answer")
                st.write_stream(token_stream())

                with st.expander("📚 View Source Documents", expanded=False):
                    if context_docs:
                        unique_sections = {d.metadata.get('section', 'N/A') for d in context_docs}
                        st.caption(f"Retrieved {len(context_docs)} sources from {len(unique_sections)} section(s)")
                        for i, doc in enumerate(context_docs, 1):
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.markdown(f"**Source {i}** — {doc.metadata.get('section', 'N/A')}")
                            with c2:
                                st.caption(f"📅 {doc.metadata.get('filing_date', 'N/A')}")
                            preview = doc.page_content[:500]
                            st.text(preview + ("..." if len(doc.page_content) > 500 else ""))
                            if len(doc.page_content) > 500:
                                with st.expander(f"View full content (Source {i})"):
                                    st.text(doc.page_content)
                            if i < len(context_docs):
                                st.divider()
                    else:
                        st.info("No source documents available")

            except Exception as e:
                st.error(f"Error generating answer: {str(e)}")
                with st.expander("View error details"):
                    import traceback
                    st.code(traceback.format_exc())

# ── TAB 2: COMPARE YEARS ────────────────────────────────────────────────
with tab_compare:
    if 'vector_store_path' not in st.session_state:
        st.info("👆 Please analyze a filing first using the sidebar to enable year-over-year comparison.")
    else:
        st.markdown(
            "Compare two consecutive 10-K filings to surface financial changes, "
            "new/removed risks, and strategic shifts."
        )
        st.info(
            "This fetches **two full filings** from SEC EDGAR and sends them to Gemini. "
            "Expect 1–3 minutes for the download + analysis."
        )

        compare_type = st.radio(
            "What to compare:",
            ["Financial Changes + Strategic Shifts", "Risk Factor Analysis", "Both"],
            horizontal=True,
        )

        if st.button("Run Year-over-Year Comparison", use_container_width=True):
            ticker_to_compare = st.session_state.get('processed_ticker', ticker)

            with st.spinner(f"Fetching latest 10-K for {ticker_to_compare}..."):
                try:
                    text_current, year_current = fetch_10k_text(ticker_to_compare, index=0)
                except Exception as e:
                    st.error(f"Could not fetch current filing: {e}")
                    st.stop()

            with st.spinner(f"Fetching prior-year 10-K for {ticker_to_compare}..."):
                try:
                    text_prior, year_prior = fetch_10k_text(ticker_to_compare, index=1)
                except Exception as e:
                    st.error(
                        f"Could not fetch prior-year filing: {e}. "
                        "The company may only have one 10-K on EDGAR."
                    )
                    st.stop()

            st.success(f"Comparing FY{year_current} vs FY{year_prior} for {ticker_to_compare}")

            text_current_trimmed = text_current[:80_000]
            text_prior_trimmed   = text_prior[:80_000]

            try:
                engine = GeminiAnalysisEngine()

                if compare_type in ["Financial Changes + Strategic Shifts", "Both"]:
                    with st.spinner("Generating financial comparison..."):
                        comparison = engine.compare_filings(
                            ticker_to_compare,
                            year_current, text_current_trimmed,
                            year_prior,   text_prior_trimmed,
                        )
                    st.markdown(f"## Financial & Strategic Comparison: FY{year_current} vs FY{year_prior}")
                    st.markdown(comparison)
                    st.divider()

                if compare_type in ["Risk Factor Analysis", "Both"]:
                    with st.spinner("Analyzing risk factor changes..."):
                        risks = engine.analyze_risks(
                            year_current, text_current_trimmed,
                            year_prior,   text_prior_trimmed,
                        )
                    st.markdown(f"## Risk Factor Analysis: FY{year_current} vs FY{year_prior}")
                    st.markdown(risks)

            except Exception as e:
                st.error(f"Comparison failed: {str(e)}")
                with st.expander("View error details"):
                    import traceback
                    st.code(traceback.format_exc())

# ── TAB 3: COMPARE COMPANIES ────────────────────────────────────────────
with tab_compare_co:
    st.markdown(
        "Analyze and compare two companies side-by-side using their latest SEC 10-K filings. "
        "Companies are automatically processed if not already available — no sidebar step required."
    )

    if not api_key:
        st.warning("⚠️ Please enter your Google API Key in the sidebar before comparing companies.")
    else:
        inp_a, inp_b = st.columns(2)
        with inp_a:
            co_ticker_a = st.text_input("Company A ticker", "AAPL", key="co_ticker_a").upper().strip()
        with inp_b:
            co_ticker_b = st.text_input("Company B ticker", "MSFT", key="co_ticker_b").upper().strip()

        _tickers_valid = co_ticker_a and co_ticker_b and co_ticker_a != co_ticker_b
        if co_ticker_a == co_ticker_b and co_ticker_a:
            st.warning("Please enter two different ticker symbols.")

        if _tickers_valid and st.button("⚖️ Compare Companies", use_container_width=True, key="btn_compare_co"):
            # ---- Process Company A if not cached ----
            if f'vs_{co_ticker_a}' not in st.session_state:
                with st.spinner(f"Processing 10-K for {co_ticker_a}..."):
                    try:
                        _docs_a = process_filing(co_ticker_a)
                        if not _docs_a:
                            st.error(f"No documents found for {co_ticker_a}. Check the ticker symbol.")
                            st.stop()
                        _vs_path_a = f"chroma_db_{co_ticker_a}"
                        add_documents_to_store(_docs_a, persist_directory=_vs_path_a)
                        st.session_state[f'vs_{co_ticker_a}']   = _vs_path_a
                        st.session_state[f'text_{co_ticker_a}'] = " ".join(d.page_content for d in _docs_a)[:200_000]
                        st.success(f"✓ {co_ticker_a} processed ({len(_docs_a)} chunks)")
                    except Exception as _e:
                        st.error(f"Error processing {co_ticker_a}: {_e}")
                        st.stop()
            else:
                st.success(f"✓ {co_ticker_a} already cached")

            # ---- Process Company B if not cached ----
            if f'vs_{co_ticker_b}' not in st.session_state:
                with st.spinner(f"Processing 10-K for {co_ticker_b}..."):
                    try:
                        _docs_b = process_filing(co_ticker_b)
                        if not _docs_b:
                            st.error(f"No documents found for {co_ticker_b}. Check the ticker symbol.")
                            st.stop()
                        _vs_path_b = f"chroma_db_{co_ticker_b}"
                        add_documents_to_store(_docs_b, persist_directory=_vs_path_b)
                        st.session_state[f'vs_{co_ticker_b}']   = _vs_path_b
                        st.session_state[f'text_{co_ticker_b}'] = " ".join(d.page_content for d in _docs_b)[:200_000]
                        st.success(f"✓ {co_ticker_b} processed ({len(_docs_b)} chunks)")
                    except Exception as _e:
                        st.error(f"Error processing {co_ticker_b}: {_e}")
                        st.stop()
            else:
                st.success(f"✓ {co_ticker_b} already cached")

            # ---- Beneish M-Score for both ----
            for _t in [co_ticker_a, co_ticker_b]:
                if f'beneish_{_t}' not in st.session_state:
                    with st.spinner(f"Fetching Beneish M-Score for {_t}..."):
                        try:
                            st.session_state[f'beneish_{_t}'] = calculate_beneish_m_score_with_ticker(_t, current_year=2024)
                        except Exception as _e:
                            st.session_state[f'beneish_{_t}'] = {
                                'data_source': 'error', 'm_score': None,
                                'risk_level': 'UNKNOWN', 'error': str(_e),
                            }

            # ---- Linguistic analysis for both ----
            for _t in [co_ticker_a, co_ticker_b]:
                if f'ling_{_t}' not in st.session_state:
                    with st.spinner(f"Analyzing linguistic indicators for {_t}..."):
                        try:
                            _full_text = st.session_state.get(f'text_{_t}', '')
                            if not _full_text:
                                _vs_tmp = get_vector_store(st.session_state[f'vs_{_t}'])
                                _tmp_docs = _vs_tmp.similarity_search("revenue income operations", k=30)
                                _full_text = " ".join(d.page_content for d in _tmp_docs)
                            st.session_state[f'ling_{_t}'] = analyze_linguistic_fraud_indicators(_full_text[:100_000])
                        except Exception as _e:
                            st.session_state[f'ling_{_t}'] = {'metrics': {}, 'red_flags': [], 'error': str(_e)}

            st.session_state['co_compare_pair'] = (co_ticker_a, co_ticker_b)

        # ── Display results ──────────────────────────────────────────────
        _pair = st.session_state.get('co_compare_pair')
        if _pair and f'vs_{_pair[0]}' in st.session_state and f'vs_{_pair[1]}' in st.session_state:
            _ta, _tb = _pair

            st.divider()
            st.subheader(f"📊 {_ta}  vs  {_tb} — Financial Metrics")

            # ── M-Score side by side ─────────────────────────────────────
            st.markdown("#### Beneish M-Score (Earnings Manipulation Risk)")

            def _mscore_emoji(score):
                if score is None:
                    return "⚪"
                return "🔴" if score > -1.78 else ("🟡" if score > -2.22 else "🟢")

            _bres_a = st.session_state.get(f'beneish_{_ta}', {})
            _bres_b = st.session_state.get(f'beneish_{_tb}', {})

            mcol_a, mcol_b = st.columns(2)
            for _col, _bres, _t in [(mcol_a, _bres_a, _ta), (mcol_b, _bres_b, _tb)]:
                with _col:
                    st.markdown(f"**{_t}**")
                    _ms   = _bres.get('m_score')
                    _rl   = _bres.get('risk_level', 'N/A')
                    _dsrc = _bres.get('data_source', 'unknown')
                    if _dsrc in ('unavailable', 'error'):
                        st.warning(f"M-Score unavailable — {_bres.get('message', _bres.get('error', ''))}")
                    else:
                        st.metric(
                            f"{_mscore_emoji(_ms)} M-Score",
                            f"{_ms:.3f}" if _ms is not None else "N/A",
                            delta=f"Risk: {_rl}",
                        )
                        _comps = _bres.get('components', {})
                        if _comps:
                            with st.expander("Key Components (DSRI · GMI · AQI · SGI)"):
                                for _ck in ['dsri', 'gmi', 'aqi', 'sgi']:
                                    if _ck in _comps:
                                        st.write(f"**{_ck.upper()}**: {_comps[_ck]:.4f}")

            # ── Linguistic indicators side by side ────────────────────────
            st.markdown("#### 📝 Linguistic Fraud Indicators")
            _lres_a = st.session_state.get(f'ling_{_ta}', {})
            _lres_b = st.session_state.get(f'ling_{_tb}', {})

            lcol_a, lcol_b = st.columns(2)
            for _col, _lres, _t in [(lcol_a, _lres_a, _ta), (lcol_b, _lres_b, _tb)]:
                with _col:
                    st.markdown(f"**{_t}**")
                    _met = _lres.get('metrics', {})
                    _lm1, _lm2, _lm3 = st.columns(3)
                    with _lm1:
                        st.metric("Lexical Diversity", f"{_met.get('lexical_diversity', 0):.2%}")
                    with _lm2:
                        st.metric("Passive Voice", f"{_met.get('passive_voice_ratio', 0):.2%}")
                    with _lm3:
                        st.metric("Hedging", f"{_met.get('hedging_ratio', 0):.2%}")
                    _flags = _lres.get('red_flags', [])
                    if _flags:
                        st.warning(f"⚠️ Red Flags ({len(_flags)}): {', '.join(_flags)}")
                    else:
                        st.success("✓ No linguistic red flags")

            # ── Fraud risk summary table ──────────────────────────────────
            st.divider()
            st.subheader("📋 Fraud Risk Summary")

            import pandas as pd

            def _winner_label(val_a, val_b, t_a, t_b, lower_is_better=True):
                if val_a is None or val_b is None:
                    return "—"
                if val_a == val_b:
                    return "Tie"
                better = t_a if (val_a < val_b) == lower_is_better else t_b
                return f"{better} ✅"

            _risk_rank = {'LOW': 0, 'MODERATE': 1, 'HIGH': 2, 'UNKNOWN': 3, 'N/A': 3}
            _ma  = _bres_a.get('m_score')
            _mb  = _bres_b.get('m_score')
            _ra  = _bres_a.get('risk_level', 'N/A')
            _rb  = _bres_b.get('risk_level', 'N/A')
            _fla = len(_lres_a.get('red_flags', []))
            _flb = len(_lres_b.get('red_flags', []))

            _summary_rows = [
                {
                    "Metric":  "M-Score",
                    _ta:       f"{_ma:.3f}" if _ma is not None else "N/A",
                    _tb:       f"{_mb:.3f}" if _mb is not None else "N/A",
                    "Better":  _winner_label(_ma, _mb, _ta, _tb, lower_is_better=True),
                },
                {
                    "Metric":  "Manipulation Risk",
                    _ta:       _ra,
                    _tb:       _rb,
                    "Better":  _winner_label(_risk_rank.get(_ra, 3), _risk_rank.get(_rb, 3), _ta, _tb, lower_is_better=True),
                },
                {
                    "Metric":  "Linguistic Red Flags",
                    _ta:       str(_fla),
                    _tb:       str(_flb),
                    "Better":  _winner_label(_fla, _flb, _ta, _tb, lower_is_better=True),
                },
            ]
            st.table(pd.DataFrame(_summary_rows).set_index("Metric"))

            # ── AI narrative comparison ───────────────────────────────────
            st.divider()
            st.subheader("🤖 AI Narrative Comparison")
            st.caption(
                "Retrieves relevant excerpts from both filings and asks Gemini to compare "
                "revenue growth, profitability, risk factors, and strategic priorities."
            )

            _ai_cache_key = f'ai_compare_{_ta}_{_tb}'

            if st.button("Generate AI Comparison", use_container_width=True, key="btn_ai_compare"):
                try:
                    _engine = GeminiAnalysisEngine()
                    _vs_a   = get_vector_store(st.session_state[f'vs_{_ta}'])
                    _vs_b   = get_vector_store(st.session_state[f'vs_{_tb}'])
                    _raw    = _engine.stream_compare_companies(_ta, _vs_a, _tb, _vs_b)

                    _accumulated: list = []
                    _stream_placeholder = st.empty()

                    def _ai_token_stream():
                        for _type, _data in _raw:
                            if _type == "token":
                                _accumulated.append(_data)
                                yield _data

                    _stream_placeholder.write_stream(_ai_token_stream())
                    _clean_result = _clean_latex_artifacts("".join(_accumulated))
                    st.session_state[_ai_cache_key] = _clean_result
                    _stream_placeholder.markdown(_clean_result)
                except Exception as _e:
                    st.error(f"AI comparison failed: {_e}")
                    with st.expander("View error details"):
                        import traceback
                        st.code(traceback.format_exc())
            elif _ai_cache_key in st.session_state:
                st.markdown(_clean_latex_artifacts(st.session_state[_ai_cache_key]))

# Footer with stats
st.divider()
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("Built with LangChain, Gemini, and edgartools | Financial document analysis with fraud detection")
with footer_col2:
    if 'processed_ticker' in st.session_state:
        st.caption(f"✓ Active: {st.session_state['processed_ticker']}")
