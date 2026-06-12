import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from .prompts import (
    FINANCIAL_QA_PROMPT, 
    COMPARISON_PROMPT, 
    RISK_ANALYSIS_PROMPT,
    METRIC_EXTRACTION_PROMPT,
    FINANCIAL_SUMMARY_PROMPT
)

class GeminiAnalysisEngine:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        # Ensure API Key
        if "GOOGLE_API_KEY" not in os.environ:
             raise ValueError("GOOGLE_API_KEY environment variable not set")
             
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.3,  # Low temperature for factual analysis
            convert_system_message_to_human=True
        )

    def preprocess_query(self, query: str) -> str:
        """
        Enhance query for better retrieval by adding relevant financial terms.
        """
        query_lower = query.lower()
        enhanced_terms = []
        
        # Revenue-related queries
        if any(term in query_lower for term in ['revenue', 'sales', 'top line']):
            enhanced_terms.extend(['net sales', 'revenues', 'total revenue'])
        
        # Profit-related queries
        if any(term in query_lower for term in ['profit', 'income', 'earnings']):
            enhanced_terms.extend(['gross profit', 'operating income', 'net income', 'earnings'])
        
        # Risk-related queries
        if 'risk' in query_lower:
            enhanced_terms.append('Item 1A Risk Factors')
        
        # Strategy-related queries
        if any(term in query_lower for term in ['strategy', 'plan', 'initiative', 'focus']):
            enhanced_terms.append('Item 7 Management Discussion MD&A')
        
        # Combine original query with enhanced terms
        if enhanced_terms:
            return f"{query} {' '.join(enhanced_terms)}"
        return query

    def get_qa_chain(self, vector_store):
        """
        Creates a RAG chain for answering questions based on vector store retrieved context.
        Uses LCEL (LangChain Expression Language) with query preprocessing.
        """
        retriever = vector_store.as_retriever(
            search_type="mmr", 
            search_kwargs={
                "k": 5, 
                "fetch_k": 20,
                "lambda_mult": 0.7 
            }
        )
        
        def format_docs(docs):
            return "\n\n".join([
                f"[Source {i}] (Section: {doc.metadata.get('section', 'N/A')})\n{doc.page_content}"
                for i, doc in enumerate(docs)
            ])

        # LCEL Chain
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | FINANCIAL_QA_PROMPT
            | self.llm
            | StrOutputParser()
        )
        
        # Wrap with enhanced invoke interface
        class ChainWrapper:
            def __init__(self, chain, vector_store, engine):
                self.chain = chain
                self.vector_store = vector_store
                self.engine = engine  # Reference to parent engine for preprocessing
            
            def invoke(self, input_dict):
                query = input_dict["input"]
                
                # ✅ Preprocess query for better retrieval
                enhanced_query = self.engine.preprocess_query(query)
                
                # ✅ Get documents using enhanced query
                docs = self.vector_store.similarity_search(enhanced_query, k=5)
                
                # ✅ Generate answer using original query (for context)
                answer = self.chain.invoke(query)
                
                return {
                    "answer": answer,
                    "context": docs
                }

        return ChainWrapper(rag_chain, vector_store, self)

    def get_metric_extraction_chain(self, vector_store):
        """
        Creates a specialized chain for extracting specific financial metrics.
        Uses fewer documents (k=3) for more focused retrieval.
        """
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 3,  # Fewer docs for focused queries
                "fetch_k": 10,
                "lambda_mult": 0.5  # Higher relevance weight
            }
        )
        
        def format_docs(docs):
            return "\n\n".join([
                f"[Source {i}]\n{doc.page_content}"
                for i, doc in enumerate(docs)
            ])
        
        metric_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | METRIC_EXTRACTION_PROMPT
            | self.llm
            | StrOutputParser()
        )
        
        class MetricChainWrapper:
            def __init__(self, chain, vector_store, engine):
                self.chain = chain
                self.vector_store = vector_store
                self.engine = engine
            
            def invoke(self, input_dict):
                query = input_dict["input"]
                enhanced_query = self.engine.preprocess_query(query)
                
                docs = self.vector_store.similarity_search(enhanced_query, k=3)
                answer = self.chain.invoke(query)
                
                return {
                    "answer": answer,
                    "context": docs
                }
        
        return MetricChainWrapper(metric_chain, vector_store, self)

    def compare_filings(self, company: str, year1: str, filing1_text: str, year2: str, filing2_text: str):
        """
        Performs a full-text comparison of two filings using Gemini's long context window.
        """
        prompt = COMPARISON_PROMPT.format(
            company=company,
            year1=year1,
            filing1=filing1_text,  # CAUTION: potentially very large
            year2=year2,
            filing2=filing2_text
        )
        
        response = self.llm.invoke(prompt)
        return response.content

    def analyze_risks(self, current_year: str, current_filing_text: str, prior_year: str, prior_filing_text: str):
        """
        Analyzes risk factors specifically using the enhanced prompt.
        """
        prompt = RISK_ANALYSIS_PROMPT.format(
            current_year=current_year,
            current_filing=current_filing_text,
            prior_year=prior_year,
            prior_filing=prior_filing_text
        )
        
        response = self.llm.invoke(prompt)
        return response.content

    def generate_financial_summary(self, filing_text: str):
        """
        NEW: Generates a comprehensive financial summary from a 10-K filing.
        Useful for executive overviews.
        """
        prompt = FINANCIAL_SUMMARY_PROMPT.format(filing_content=filing_text)
        
        response = self.llm.invoke(prompt)
        return response.content

    def answer_with_web_context(self, query: str, vector_store, include_web: bool = False):
        """
        NEW: Answer questions with optional web search for current context.
        Useful for questions about recent events or market conditions.
        """
        # Get filing context
        docs = vector_store.similarity_search(self.preprocess_query(query), k=5)
        
        filing_context = "\n\n".join([
            f"[Filing Source {i}]\n{doc.page_content}"
            for i, doc in enumerate(docs)
        ])
        
        # Build prompt
        if include_web:
            prompt = f"""
You are a financial analyst with access to both SEC filings and current market information.

SEC FILING CONTEXT:
{filing_context}

QUESTION: {query}

Instructions:
- Answer using the SEC filing context provided
- If the question asks about recent developments or market conditions, note that you may need current information
- Be clear about what information comes from the filing vs what requires current data
- Provide specific numbers and facts from the filing
"""
        else:
            prompt = f"""
SEC FILING CONTEXT:
{filing_context}

QUESTION: {query}

Answer based strictly on the filing context provided. Include specific numbers and cite sources.
"""
        
        response = self.llm.invoke(prompt)
        
        return {
            "answer": response.content,
            "context": docs,
            "used_web": include_web
        }