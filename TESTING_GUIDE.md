# Testing Guide

This document explains how to run tests for the Intelligent Financial Document Q&A System.

## Test Structure

```
tests/
├── __init__.py
├── unit/                      # Unit tests for individual components
│   ├── __init__.py
│   ├── test_mcp_server.py    # MCP server tests
│   ├── test_rag.py           # RAG module tests
│   └── test_compliance.py    # Compliance module tests
└── integration/               # Integration tests for workflows
    ├── __init__.py
    └── test_end_to_end.py    # End-to-end workflow tests
```

## Installation

Install test dependencies:

```bash
pip install -r requirements.txt
```

This includes:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-asyncio` - Async test support

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Exclude tests requiring API access
pytest -m "not requires_api"
```

### Run Specific Test Files

```bash
# Test MCP server only
pytest tests/unit/test_mcp_server.py

# Test RAG module only
pytest tests/unit/test_rag.py

# Test compliance module only
pytest tests/unit/test_compliance.py

# Test end-to-end workflows
pytest tests/integration/test_end_to_end.py
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/unit/test_mcp_server.py::TestTickerValidation

# Run specific test function
pytest tests/unit/test_rag.py::TestDocumentChunking::test_chunk_document_basic
```

## Test Markers

Tests are categorized with markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, multiple components)
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.requires_api` - Tests requiring external API access
- `@pytest.mark.requires_network` - Tests requiring network connectivity

## Coverage Reports

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=mcp_server --cov=rag --cov=compliance --cov=analysis

# Generate HTML coverage report
pytest --cov=mcp_server --cov=rag --cov=compliance --cov=analysis --cov-report=html

# View HTML report
# Open htmlcov/index.html in your browser
```

### Coverage Thresholds

Aim for:
- **Unit tests**: 80%+ coverage
- **Integration tests**: 60%+ coverage
- **Overall**: 70%+ coverage

## Test Configuration

Configuration is in `pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = -v --strict-markers --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    requires_api: Tests requiring API access
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch

class TestYourComponent:
    """Test description."""
    
    @pytest.mark.unit
    def test_your_function(self):
        """Test specific behavior."""
        # Arrange
        input_data = "test"
        
        # Act
        result = your_function(input_data)
        
        # Assert
        assert result == expected_output
```

### Integration Test Template

```python
import pytest
from unittest.mock import patch

class TestYourWorkflow:
    """Test workflow description."""
    
    @pytest.mark.integration
    @patch('module.external_dependency')
    def test_complete_workflow(self, mock_dependency):
        """Test end-to-end workflow."""
        # Setup
        mock_dependency.return_value = "mocked_value"
        
        # Execute workflow
        result = execute_workflow()
        
        # Verify
        assert result is not None
```

## Mocking External Dependencies

### Mock SEC EDGAR API

```python
@patch('mcp_server.server.Company')
def test_with_mocked_edgar(mock_company):
    mock_instance = MagicMock()
    mock_filing = MagicMock()
    mock_filing.text = "Mock content"
    mock_instance.get_filings.return_value = [mock_filing]
    mock_company.return_value = mock_instance
    
    # Your test code here
```

### Mock Gemini API

```python
@patch('analysis.gemini_engine.GeminiEngine')
def test_with_mocked_gemini(mock_gemini):
    mock_instance = MagicMock()
    mock_instance.generate_answer.return_value = {
        'answer': 'Mock answer',
        'sources': [1, 2]
    }
    mock_gemini.return_value = mock_instance
    
    # Your test code here
```

### Mock ChromaDB

```python
@patch('rag.vector_store.chromadb.Client')
def test_with_mocked_chromadb(mock_client):
    mock_collection = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.get_or_create_collection.return_value = mock_collection
    mock_client.return_value = mock_client_instance
    
    # Your test code here
```

## Environment Variables for Testing

Some tests require environment variables:

```bash
# For tests requiring API access
export GOOGLE_API_KEY="your_test_api_key"
export USER_AGENT="TestUser test@example.com"
```

Or create a `.env.test` file:

```env
GOOGLE_API_KEY=your_test_api_key
USER_AGENT=TestUser test@example.com
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest -m "not requires_api" --cov
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Ensure you're in the project root
cd d:\Int_fin_doc

# Install in development mode
pip install -e .
```

### Mock Not Working

Ensure you're patching the right location:

```python
# Patch where it's used, not where it's defined
# Wrong: @patch('mcp_server.utils.Company')
# Right: @patch('mcp_server.server.Company')
```

### Fixtures Not Found

Ensure fixtures are in the same file or in `conftest.py`:

```python
# conftest.py
import pytest

@pytest.fixture
def shared_fixture():
    return "shared data"
```

## Best Practices

1. **Test Naming**: Use descriptive names (`test_calculate_dsri_with_zero_sales`)
2. **One Assert Per Test**: Focus each test on one behavior
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Dependencies**: Keep tests fast and isolated
5. **Use Fixtures**: Share common setup across tests
6. **Test Edge Cases**: Empty inputs, None values, division by zero
7. **Document Tests**: Add docstrings explaining what's being tested

## Test Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| MCP Server | TBD | 80% |
| RAG | TBD | 80% |
| Compliance | TBD | 75% |
| Analysis | TBD | 70% |
| UI | TBD | 60% |

## Next Steps

1. Run the test suite: `pytest`
2. Review coverage: `pytest --cov --cov-report=html`
3. Add tests for uncovered code
4. Set up CI/CD pipeline
5. Add performance benchmarks

---

*For questions or issues, refer to the main [USER_GUIDE.md](USER_GUIDE.md)*
