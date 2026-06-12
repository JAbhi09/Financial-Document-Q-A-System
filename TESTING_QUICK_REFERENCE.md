# Testing Quick Reference Card

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=html
```

## 📁 Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `tests/unit/test_mcp_server.py` | 15+ | SEC EDGAR integration |
| `tests/unit/test_rag.py` | 18+ | Document processing & RAG |
| `tests/unit/test_compliance.py` | 20+ | Fraud detection & M-Score |
| `tests/integration/test_end_to_end.py` | 12+ | Complete workflows |

## 🎯 Common Commands

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Exclude API tests
pytest -m "not requires_api"

# Specific file
pytest tests/unit/test_mcp_server.py -v

# Specific test
pytest tests/unit/test_rag.py::TestDocumentChunking::test_chunk_document_basic

# With coverage
pytest --cov=mcp_server --cov=rag --cov=compliance --cov=analysis

# HTML coverage report
pytest --cov --cov-report=html
# Then open: htmlcov/index.html
```

## 🏷️ Test Markers

```bash
-m unit              # Fast unit tests
-m integration       # Integration tests
-m slow              # Long-running tests
-m requires_api      # Tests needing API keys
-m requires_network  # Tests needing internet
```

## 📊 Test Statistics

- **Total Tests**: 65+
- **Test Classes**: 22
- **Test Files**: 4
- **Code Coverage Target**: 70%+

## 📚 Documentation

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Complete testing guide
- **[tests/README.md](tests/README.md)** - Quick reference
- **[TESTING_IMPLEMENTATION_SUMMARY.md](TESTING_IMPLEMENTATION_SUMMARY.md)** - Implementation details

## ✅ Pre-Commit Checklist

```bash
# 1. Run all tests
pytest

# 2. Check coverage
pytest --cov

# 3. Run linting (if configured)
# flake8 .
# black --check .

# 4. Run type checking (if configured)
# mypy .
```

## 🐛 Troubleshooting

```bash
# Import errors?
pip install -e .

# Fixture not found?
# Check conftest.py or move fixture to same file

# Mock not working?
# Patch where it's used, not where it's defined
```

## 🎓 Writing Tests

```python
import pytest
from unittest.mock import patch

class TestYourFeature:
    @pytest.mark.unit
    def test_your_function(self):
        # Arrange
        input_data = "test"
        
        # Act
        result = your_function(input_data)
        
        # Assert
        assert result == expected
```

## 🔧 Configuration

- **pytest.ini** - Main configuration
- **requirements.txt** - Test dependencies
- **.env.test** - Test environment variables (optional)

---

**Need Help?** See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed documentation.
