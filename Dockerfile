# # Use Python 3.11 slim image for smaller size
# FROM python:3.11-slim

# # Set working directory
# WORKDIR /app

# # Set environment variables
# ENV PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements first for better caching
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Download NLTK data (required for linguistic analysis)
# RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('stopwords')"

# # Copy application code
# COPY analysis/ ./analysis/
# COPY compliance/ ./compliance/
# COPY rag/ ./rag/
# COPY ui/ ./ui/
# COPY requirements.txt ./requirements.txt

# # Create directories for persistent data
# RUN mkdir -p /app/chroma_db /app/analysis

# # Expose Streamlit default port
# EXPOSE 8501

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# # Run Streamlit app
# CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]




# # Multi-stage build for smaller image
# FROM python:3.11-slim as builder

# WORKDIR /app

# # Install build dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# # Copy and install Python dependencies
# COPY requirements.txt .
# RUN pip install --user --no-cache-dir --upgrade pip && \
#     pip install --user --no-cache-dir -r requirements.txt

# # Download NLTK data
# RUN python -c "import nltk; \
#     nltk.download('punkt', download_dir='/root/nltk_data'); \
#     nltk.download('punkt_tab', download_dir='/root/nltk_data'); \
#     nltk.download('averaged_perceptron_tagger', download_dir='/root/nltk_data'); \
#     nltk.download('averaged_perceptron_tagger_eng', download_dir='/root/nltk_data'); \
#     nltk.download('stopwords', download_dir='/root/nltk_data')"

# # ============================================
# # Stage 2: Runtime
# # ============================================
# FROM python:3.11-slim

# WORKDIR /app

# # Install runtime dependencies
# RUN apt-get update && apt-get install -y \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # Copy Python packages from builder
# COPY --from=builder /root/.local /root/.local
# COPY --from=builder /root/nltk_data /root/nltk_data

# # ✅ Copy ONLY necessary application code (explicit)
# COPY analysis/ ./analysis/
# COPY compliance/ ./compliance/
# COPY rag/ ./rag/
# COPY ui/ ./ui/

# # Set environment variables
# ENV PATH=/root/.local/bin:$PATH \
#     PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     STREAMLIT_SERVER_PORT=8501 \
#     STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
#     STREAMLIT_SERVER_HEADLESS=true \
#     STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
#     NLTK_DATA=/root/nltk_data

# # Create non-root user
# RUN useradd -m -u 1000 appuser && \
#     chown -R appuser:appuser /app && \
#     mkdir -p /app/chroma_db && \
#     chown -R appuser:appuser /app/chroma_db

# USER appuser

# # Expose port
# EXPOSE 8501

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# # Run app
# CMD ["streamlit", "run", "ui/app.py", \
#      "--server.port", "8501", \
#      "--server.address", "0.0.0.0", \
#      "--server.headless", "true"]


# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .

# Install packages without model downloads
RUN pip install --no-cache-dir --prefix=/install \
    langchain>=0.1.0 \
    langchain-google-genai>=0.0.5 \
    langchain-community>=0.0.10 \
    chromadb>=0.4.22 \
    pinecone-client>=3.0.0 \
    edgartools>=0.0.45 \
    sec-edgar-api>=0.5.0 \
    mcp>=0.1.0 \
    httpx>=0.25.0 \
    nltk>=3.8.1 \
    streamlit>=1.30.0 \
    pandas>=2.0.0 \
    pydantic>=2.5.0 \
    uvicorn>=0.25.0 \
    fastapi>=0.109.0 \
    python-multipart>=0.0.6

# Install ML packages separately (these are heavy)
RUN pip install --no-cache-dir --prefix=/install \
    transformers>=4.36.0 \
    sentence-transformers>=2.2.2

# Download NLTK data (small ~83MB)
RUN python -c "import sys; sys.path.insert(0, '/install/lib/python3.11/site-packages'); \
    import nltk; \
    nltk.download('punkt', download_dir='/nltk_data'); \
    nltk.download('punkt_tab', download_dir='/nltk_data'); \
    nltk.download('averaged_perceptron_tagger', download_dir='/nltk_data'); \
    nltk.download('averaged_perceptron_tagger_eng', download_dir='/nltk_data'); \
    nltk.download('stopwords', download_dir='/nltk_data')"

# ============================================
# Stage 2: Runtime (keep the rest the same)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY the installed packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /nltk_data /usr/local/share/nltk_data

# Copy application code
COPY analysis/ ./analysis/
COPY compliance/ ./compliance/
COPY mcp_server/ ./mcp_server/
COPY rag/ ./rag/
COPY ui/ ./ui/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    NLTK_DATA=/usr/local/share/nltk_data \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

# Create non-root user and cache directories
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/chroma_db /app/.cache/huggingface /app/.cache/sentence-transformers && \
    chown -R appuser:appuser /app/chroma_db /app/.cache

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "ui/app.py", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true"]