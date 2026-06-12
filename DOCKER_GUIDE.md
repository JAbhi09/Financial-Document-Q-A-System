# Docker Deployment Guide

This guide explains how to use Docker to containerize and run the **Intelligent Financial Document Q&A System**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [File Explanations](#file-explanations)
  - [Dockerfile](#dockerfile)
  - [docker-compose.yaml](#docker-composeyaml)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Overview

The Docker setup provides:
- **Containerized environment** with all dependencies pre-installed
- **Persistent storage** for vector databases and analysis results
- **Easy deployment** across different platforms (Windows, macOS, Linux)
- **Isolated environment** preventing conflicts with system packages

---

## Prerequisites

1. **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
   - Download: https://www.docker.com/products/docker-desktop
   - Verify installation: `docker --version`

2. **Docker Compose** (included with Docker Desktop)
   - Verify: `docker-compose --version`

3. **Google Gemini API Key**
   - Get one at: https://makersuite.google.com/app/apikey

4. **SEC EDGAR User Agent** (your name and email)
   - Required by SEC for API access compliance

---

## File Explanations

### Dockerfile

The `Dockerfile` defines how to build the container image for the application.

#### Key Components:

```dockerfile
FROM python:3.11-slim
```
- **Base Image**: Uses Python 3.11 slim variant (smaller size, ~150MB vs 1GB for full image)
- **Why Python 3.11**: Compatible with all dependencies and provides performance improvements

```dockerfile
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
```
- **PYTHONUNBUFFERED=1**: Ensures Python output is sent directly to terminal (better logging)
- **PYTHONDONTWRITEBYTECODE=1**: Prevents `.pyc` file creation (cleaner container)

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git
```
- **build-essential**: C compiler needed for some Python packages (e.g., chromadb)
- **curl**: Used for health checks
- **git**: May be needed by some dependencies

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- **Layer Caching**: Copies `requirements.txt` first so dependencies are cached
- **--no-cache-dir**: Reduces image size by not storing pip cache

```dockerfile
RUN python -c "import nltk; nltk.download('punkt'); ..."
```
- **Pre-downloads NLTK data** required for linguistic fraud analysis
- Prevents runtime downloads and ensures offline capability

```dockerfile
EXPOSE 8501
```
- **Port 8501**: Streamlit's default port
- Makes the port available for mapping to host

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s ...
```
- **Health Monitoring**: Docker checks if app is running every 30 seconds
- **Auto-restart**: Container restarts if health check fails 3 times

```dockerfile
CMD ["streamlit", "run", "ui/app.py", ...]
```
- **Startup Command**: Runs Streamlit in headless mode
- **--server.address=0.0.0.0**: Allows external connections (not just localhost)

---

### docker-compose.yaml

The `docker-compose.yaml` orchestrates the container deployment with configuration.

#### Key Components:

```yaml
version: '3.8'
```
- **Compose File Version**: Uses modern syntax with all features
- Compatible with Docker Engine 19.03.0+

```yaml
services:
  financial-qa-app:
```
- **Service Definition**: Defines one service (the Streamlit app)
- Can be extended to add databases, reverse proxies, etc.

```yaml
build:
  context: .
  dockerfile: Dockerfile
```
- **Build Context**: Uses current directory (`.`) as build context
- **Dockerfile Location**: Specifies which Dockerfile to use

```yaml
ports:
  - "8501:8501"
```
- **Port Mapping**: Maps host port 8501 to container port 8501
- Format: `"<host_port>:<container_port>"`
- Access app at: `http://localhost:8501`

```yaml
environment:
  - GOOGLE_API_KEY=${GOOGLE_API_KEY}
  - USER_AGENT=${USER_AGENT:-YourName email@example.com}
```
- **Environment Variables**: Passed from host to container
- **${VAR}**: Reads from `.env` file or system environment
- **${VAR:-default}**: Uses default value if not set

```yaml
volumes:
  - ./chroma_db:/app/chroma_db
  - ./analysis:/app/analysis
```
- **Volume Mounts**: Persist data between container restarts
- **Format**: `<host_path>:<container_path>`
- **Why Important**: Vector databases and analysis results survive container recreation

```yaml
restart: unless-stopped
```
- **Restart Policy**: Auto-restart container if it crashes
- **unless-stopped**: Won't restart if manually stopped

```yaml
networks:
  financial-qa-network:
```
- **Custom Network**: Isolates container communication
- **Bridge Driver**: Default network type for single-host deployments

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
```
- **Health Check**: Verifies Streamlit is responding
- **start_period: 40s**: Gives app time to start before checking

---

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key_here
USER_AGENT=YourName your.email@example.com
```

> **Security Note**: Never commit `.env` to version control! It's already in `.gitignore`.

### 2. Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d
```

The `-d` flag runs containers in detached mode (background).

### 3. Access the Application

Open your browser and navigate to:
```
http://localhost:8501
```

### 4. Stop the Application

```bash
# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (deletes all data!)
docker-compose down -v
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | ✅ Yes | - | Your Google Gemini API key |
| `USER_AGENT` | ✅ Yes | - | Your name and email for SEC compliance |
| `LOG_LEVEL` | ❌ No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Port Configuration

To use a different port (e.g., 8080):

```yaml
ports:
  - "8080:8501"  # Access at http://localhost:8080
```

### Volume Persistence

The following directories are persisted:
- **chroma_db_***: Vector databases for each analyzed ticker
- **analysis/**: Generated analysis reports
- **.env**: Environment variables

To reset all data:
```bash
docker-compose down -v
rm -rf chroma_db_* analysis/
```

---

## Usage

### Basic Workflow

1. **Start the application**:
   ```bash
   docker-compose up -d
   ```

2. **View logs**:
   ```bash
   docker-compose logs -f financial-qa-app
   ```

3. **Access the UI**: Open `http://localhost:8501`

4. **Analyze a company**:
   - Enter ticker symbol (e.g., AAPL, MSFT, TSLA)
   - Click "🔍 Analyze Filing"
   - Wait for processing (may take 1-3 minutes)

5. **Ask questions**:
   - Use the Q&A section to query the 10-K filing
   - View fraud detection metrics

### Viewing Container Status

```bash
# List running containers
docker-compose ps

# View resource usage
docker stats financial-qa-system

# Check health status
docker inspect --format='{{.State.Health.Status}}' financial-qa-system
```

### Accessing Container Shell

```bash
# Open interactive shell
docker-compose exec financial-qa-app /bin/bash

# Run Python commands
docker-compose exec financial-qa-app python -c "import nltk; print(nltk.__version__)"
```

---

## Troubleshooting

### Issue: Container Fails to Start

**Symptoms**: `docker-compose up` exits immediately

**Solutions**:
```bash
# Check logs
docker-compose logs financial-qa-app

# Verify .env file exists
cat .env

# Rebuild without cache
docker-compose build --no-cache
```

### Issue: "GOOGLE_API_KEY not set" Error

**Cause**: Environment variable not passed to container

**Solutions**:
1. Verify `.env` file exists in project root
2. Check `.env` format (no quotes needed):
   ```
   GOOGLE_API_KEY=AIzaSyABC123...
   ```
3. Restart containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Issue: Port 8501 Already in Use

**Symptoms**: `Bind for 0.0.0.0:8501 failed: port is already allocated`

**Solutions**:
```bash
# Option 1: Stop conflicting process
# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8501 | xargs kill -9

# Option 2: Use different port
# Edit docker-compose.yaml
ports:
  - "8502:8501"
```

### Issue: NLTK Data Not Found

**Symptoms**: `Resource punkt_tab not found`

**Solution**:
```bash
# Rebuild image (NLTK data downloads during build)
docker-compose build --no-cache
docker-compose up -d
```

### Issue: ChromaDB Permission Errors

**Symptoms**: `PermissionError: [Errno 13] Permission denied: '/app/chroma_db'`

**Solution**:
```bash
# Fix permissions (Linux/macOS)
sudo chown -R $USER:$USER chroma_db_*

# Windows: Run Docker Desktop as Administrator
```

### Issue: Out of Memory

**Symptoms**: Container crashes when processing large filings

**Solution**:
```bash
# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory → 8GB+

# Or limit in docker-compose.yaml:
services:
  financial-qa-app:
    deploy:
      resources:
        limits:
          memory: 4G
```

---

## Advanced Topics

### Multi-Stage Builds (Optimization)

For production, use multi-stage builds to reduce image size:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["streamlit", "run", "ui/app.py"]
```

### Using Docker Secrets (Production)

For secure API key management:

```yaml
# docker-compose.yaml
services:
  financial-qa-app:
    secrets:
      - google_api_key
    environment:
      - GOOGLE_API_KEY_FILE=/run/secrets/google_api_key

secrets:
  google_api_key:
    file: ./secrets/google_api_key.txt
```

### Adding Nginx Reverse Proxy

```yaml
# docker-compose.yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - financial-qa-app

  financial-qa-app:
    # Remove ports section (internal only)
    expose:
      - "8501"
```

### CI/CD Integration

```yaml
# .github/workflows/docker.yml
name: Build and Push Docker Image
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build image
        run: docker-compose build
      - name: Push to registry
        run: docker-compose push
```

### Monitoring with Prometheus

```yaml
# docker-compose.yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

---

## Best Practices

1. **Always use `.env` for secrets** - Never hardcode API keys
2. **Pin dependency versions** - Update `requirements.txt` with exact versions
3. **Use health checks** - Ensures container reliability
4. **Persist important data** - Mount volumes for databases and results
5. **Monitor logs** - Use `docker-compose logs -f` during development
6. **Clean up regularly** - Run `docker system prune` to free space

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Streamlit Docker Deployment](https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker)
- [SEC EDGAR API Guidelines](https://www.sec.gov/os/webmaster-faq#code-support)

---

## Support

For issues specific to this application, refer to:
- [USER_GUIDE.md](./USER_GUIDE.md) - Application usage guide
- [README.md](./README.md) - Project overview

For Docker issues:
- Docker Community Forums: https://forums.docker.com/
- Stack Overflow: https://stackoverflow.com/questions/tagged/docker
