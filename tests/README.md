# Test Suite for Financial Document Q&A System

This directory contains comprehensive tests for all system components.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

## Test Structure

- **`unit/`** - Fast, isolated tests for individual functions and classes
  - `test_mcp_server.py` - SEC EDGAR integration tests
  - `test_rag.py` - Document processing and vector store tests
  - `test_compliance.py` - Fraud detection and linguistic analysis tests

- **`integration/`** - End-to-end workflow tests
  - `test_end_to_end.py` - Complete user journey tests

## Test Coverage

Run tests with coverage reporting:

```bash
pytest --cov=mcp_server --cov=rag --cov=compliance --cov=analysis --cov-report=html
```

View coverage report: `htmlcov/index.html`

## Documentation

See [TESTING_GUIDE.md](../TESTING_GUIDE.md) for detailed information on:
- Running specific tests
- Writing new tests
- Mocking external dependencies
- Best practices
- Troubleshooting

## Test Markers

- `@pytest.mark.unit` - Unit tests (fast)
- `@pytest.mark.integration` - Integration tests (slower)
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.requires_api` - Tests requiring API keys
- `@pytest.mark.requires_network` - Tests requiring internet

## Example Commands

```bash
# Run fast tests only
pytest -m "unit and not slow"

# Run without API tests
pytest -m "not requires_api"

# Run specific test file
pytest tests/unit/test_mcp_server.py -v

# Run specific test
pytest tests/unit/test_rag.py::TestDocumentChunking::test_chunk_document_basic
```

## CI/CD Integration

Tests are designed to work with CI/CD pipelines. See TESTING_GUIDE.md for GitHub Actions example.
