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






import streamlit as st
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.ingestion import process_filing, fetch_latest_10k_filing
from rag.vector_store import add_documents_to_store, get_vector_store
from analysis.gemini_engine import GeminiAnalysisEngine
from compliance.linguistics import analyze_linguistic_fraud_indicators
from compliance.beneish import calculate_beneish_m_score_with_ticker  
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
api_key = st.sidebar.text_input("Google API Key", type="password", value=os.getenv("GOOGLE_API_KEY", ""))
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key

ticker = st.sidebar.text_input("Enter Ticker Symbol (e.g. AAPL)", "AAPL").upper()

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
                            result = calculate_beneish_m_score_with_ticker(ticker, current_year=2024)
                            
                            m_score = result.get('m_score', -999)
                            data_source = result.get('data_source', 'unknown')
                            risk_level = result.get('risk_level', 'UNKNOWN')
                            
                            # Show data source indicator
                            if data_source == 'real':
                                st.success("✓ Using real SEC financial data")
                            elif data_source == 'demo':
                                st.warning("⚠️ Using demo data - real data unavailable")
                            else:
                                st.info("ℹ️ Data source: " + data_source)
                            
                            # Display M-Score with color coding
                            if m_score == -999 or m_score is None:
                                st.error("❌ M-Score calculation failed")
                                if 'error' in result:
                                    st.caption(f"Error: {result['error']}")
                            else:
                                if m_score > -1.78:
                                    score_color = "🔴"
                                    alert_type = "error"
                                elif m_score > -2.22:
                                    score_color = "🟡"
                                    alert_type = "warning"
                                else:
                                    score_color = "🟢"
                                    alert_type = "success"
                                
                                st.metric(
                                    f"{score_color} M-Score", 
                                    f"{m_score:.3f}",
                                    delta=f"Risk: {risk_level}"
                                )
                                
                                # Interpretation
                                if result.get('manipulation_likely'):
                                    st.error("🚨 M-Score indicates potential earnings manipulation (>-2.22)")
                                else:
                                    st.success("✓ M-Score within normal range (<-2.22)")
                            
                            # Component breakdown
                            with st.expander("📋 View M-Score Components"):
                                components = result.get('components', {})
                                interpretations = result.get('interpretation', {})
                                
                                if components:
                                    st.markdown("**Component Breakdown:**")
                                    for key, value in components.items():
                                        interp = interpretations.get(key, '')
                                        status = "⚠️" if any(word in interp for word in ["Inflating", "Deteriorating", "Aggressive", "Lower quality"]) else "✓"
                                        st.write(f"{status} **{key.upper()}**: {value} - {interp}")
                                    
                                    st.markdown("---")
                                    st.markdown("""
                                    **M-Score Interpretation Guide:**
                                    - **< -2.50**: Very low manipulation risk
                                    - **-2.50 to -2.22**: Low risk (normal range)
                                    - **-2.22 to -1.78**: Moderate risk ⚠️
                                    - **-1.78 to 0**: High risk 🔴
                                    - **> 0**: Very high risk 🚨
                                    """)
                                else:
                                    st.info("Component details not available")
                                
                        except Exception as e:
                            st.error(f"M-Score calculation error: {str(e)}")
                            st.info("This may occur if SEC financial data is unavailable for this company.")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())

# === Q&A SECTION ===
st.divider()
st.header("💬 Document Q&A")

if 'vector_store_path' in st.session_state:
    ticker_info = st.session_state.get('processed_ticker', 'Unknown')
    docs_count = st.session_state.get('docs_count', 0)
    
    # ✅ Show current analysis status
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📄 Currently analyzing: **{ticker_info}** 10-K filing ({docs_count} chunks indexed)")
    with col2:
        if st.button("🔄 Clear Analysis", use_container_width=True):
            for key in ['vector_store_path', 'processed_ticker', 'docs_count']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # ✅ Query input with example questions
    query = st.text_input(
        "Ask a question about the filing:", 
        placeholder="e.g., What was the total revenue in fiscal 2024?"
    )
    
    # ✅ Example questions
    with st.expander("💡 Example Questions"):
        example_col1, example_col2 = st.columns(2)
        
        with example_col1:
            st.markdown("**Financial Metrics:**")
            st.markdown("- What was the total revenue in fiscal 2024?")
            st.markdown("- What is the net income?")
            st.markdown("- How much cash does the company have?")
            st.markdown("- What are the capital expenditures?")
        
        with example_col2:
            st.markdown("**Strategic & Risk:**")
            st.markdown("- What are the primary risk factors?")
            st.markdown("- What is the company's e-commerce strategy?")
            st.markdown("- What are the biggest competitive threats?")
            st.markdown("- How is climate change affecting operations?")
    
    if query:
        with st.spinner("Generating answer..."):
            try:
                engine = GeminiAnalysisEngine()
                vector_store = get_vector_store(st.session_state['vector_store_path'])
                
                # ✅ Choose appropriate chain based on query type
                if is_metric_query(query):
                    st.caption("🎯 Using focused metric extraction...")
                    qa_chain = engine.get_metric_extraction_chain(vector_store)
                else:
                    st.caption("🔍 Using comprehensive analysis...")
                    qa_chain = engine.get_qa_chain(vector_store)
                
                response = qa_chain.invoke({"input": query})
                
                # ✅ Display answer with better formatting
                st.markdown("### 💡 Answer")
                answer_text = response["answer"]
                
                # Clean up answer formatting
                if answer_text.startswith("```") and answer_text.endswith("```"):
                    answer_text = answer_text.strip("`").strip()
                
                st.markdown(answer_text)
                
                # ✅ Show sources with better presentation
                with st.expander("📚 View Source Documents", expanded=False):
                    context_docs = response.get("context", [])
                    if context_docs:
                        # Check for diversity
                        unique_sections = set(doc.metadata.get('section', 'N/A') for doc in context_docs)
                        st.caption(f"Retrieved {len(context_docs)} sources from {len(unique_sections)} sections")
                        
                        for i, doc in enumerate(context_docs, 1):
                            with st.container():
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**Source {i}** - Section: {doc.metadata.get('section', 'N/A')}")
                                with col2:
                                    filing_date = doc.metadata.get('filing_date', 'N/A')
                                    st.caption(f"📅 {filing_date}")
                                
                                # Show preview with expand option
                                preview = doc.page_content[:500]
                                if len(doc.page_content) > 500:
                                    preview += "..."
                                
                                st.text(preview)
                                
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
else:
    st.info("👆 Please analyze a filing first using the sidebar to enable Q&A.")
    
    # ✅ Better suggestions with descriptions
    # Replace your suggested companies section with this:
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
# Footer with stats
st.divider()
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption("Built with LangChain, Gemini, and edgartools | Financial document analysis with fraud detection")
with footer_col2:
    if 'processed_ticker' in st.session_state:
        st.caption(f"✓ Active: {st.session_state['processed_ticker']}")
