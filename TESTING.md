# 🧪 Knowledge Injester Testing Guide

## Quick Start

### 1. Setup Development Environment
```bash
# Activate virtual environment
source .venv/bin/activate

# Run development setup
python scripts/management/setup_dev.py
```

### 2. Run All Tests
```bash
# Option 1: Use the test runner script (recommended)
python scripts/management/run_tests.py

# Option 2: Use the shell script
./run_tests.sh

# Option 3: Run directly with pytest (Django settings auto-configured)
pytest tests/ -v --cov=apps
```

### 3. Test API Endpoints
```bash
# Start Django server
python manage.py runserver

# In another terminal, test API
python tests/integration/test_crawl_api.py
```

## Test Structure Overview

```
knowledgeinjester/
├── tests/                          # 🧪 Comprehensive test suite
│   ├── conftest.py                # Pytest configuration & fixtures
│   ├── fixtures/                  # Test data fixtures
│   ├── unit/                      # Unit tests (50+ tests)
│   │   ├── test_core_hashing.py   # Core hashing utilities
│   │   ├── test_core_storage.py   # File storage utilities
│   │   ├── test_core_types.py     # Pydantic models
│   │   ├── test_crawler_services.py
│   │   ├── test_extractor_services.py
│   │   └── test_vectorizer_services.py
│   ├── integration/               # Integration tests
│   │   ├── test_api_endpoints.py  # API endpoint testing
│   │   ├── test_database_models.py # Django model testing
│   │   ├── test_full_pipeline.py  # End-to-end pipeline
│   │   └── test_crawl_api.py      # Standalone API test
│   └── README.md                  # Detailed test documentation
│
├── scripts/                       # 🔧 Management scripts
│   ├── workers/
│   │   └── worker.py              # Background worker (refactored)
│   └── management/
│       ├── run_tests.py           # Test runner script
│       └── setup_dev.py           # Development setup
│
├── pytest.ini                    # Pytest configuration
├── .github/workflows/test.yml     # CI/CD pipeline
└── TESTING.md                     # This guide
```

## Test Categories

### 🔬 Unit Tests (`tests/unit/`)
- **Core Utilities**: Hashing, storage, logging, environment
- **Type Definitions**: Pydantic model validation
- **Service Functions**: Individual service layer functions
- **Business Logic**: Isolated business logic testing

### 🔗 Integration Tests (`tests/integration/`)
- **API Endpoints**: Full HTTP request/response testing
- **Database Models**: Django model integration
- **Full Pipeline**: End-to-end workflow testing
- **External Services**: Mocked external service integration

## Key Features

### ✅ Comprehensive Coverage
- **50+ Tests**: Unit and integration tests
- **80%+ Coverage**: Enforced minimum coverage
- **6 Test Categories**: Organized by functionality
- **3 Python Versions**: CI testing on 3.10, 3.11, 3.12

### ✅ Professional Test Structure
- **Pytest Framework**: Modern Python testing
- **Django Integration**: Proper Django test setup
- **Fixtures & Mocks**: Reusable test data and mocking
- **CI/CD Pipeline**: GitHub Actions automation

### ✅ Developer Experience
- **Management Scripts**: Easy test execution
- **Detailed Documentation**: Comprehensive test guide
- **Fast Execution**: Optimized for speed
- **Clear Organization**: Logical test structure

## Running Tests

### Quick Commands
```bash
# All tests with coverage
pytest tests/ -v --cov=apps

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_core_hashing.py -v

# With markers
pytest tests/ -m "unit" -v
```

### Management Scripts
```bash
# Complete test suite
python scripts/management/run_tests.py

# Development setup
python scripts/management/setup_dev.py

# Background worker
python scripts/workers/worker.py
```

## Test Configuration

### Pytest Settings (`pytest.ini`)
- Django settings: `knowledgeinjester.test_settings`
- Coverage: 80% minimum requirement
- Markers: `unit`, `integration`, `api`, `crawler`, etc.
- Output: Verbose with short tracebacks

### Test Settings (`knowledgeinjester/test_settings.py`)
- Database: In-memory SQLite for speed
- Migrations: Disabled for faster execution
- Logging: Minimal logging during tests
- External Services: Mocked for isolation

## CI/CD Pipeline

### GitHub Actions (`.github/workflows/test.yml`)
- **Triggers**: Push to main/develop, pull requests
- **Matrix**: Python 3.10, 3.11, 3.12
- **Steps**: Install → Check → Migrate → Test → Coverage
- **Reports**: Coverage uploaded to Codecov

### Local CI
```bash
# Run full CI pipeline locally
python scripts/management/run_tests.py
```

## Test Data & Fixtures

### Database Fixtures
- `test_organization`: Sample organization
- `test_data_source`: Sample data source  
- `test_crawl_job`: Sample crawl job
- `test_ingest_job`: Sample ingest job

### Data Fixtures
- `sample_page_raw`: Sample PageRaw object
- `sample_doc`: Sample Doc object
- `sample_chunk`: Sample Chunk object

## Best Practices

### Writing Tests
1. **Descriptive Names**: Clear, behavior-focused test names
2. **Single Responsibility**: One test per behavior
3. **Arrange-Act-Assert**: Clear test structure
4. **Mock External Dependencies**: Isolate units under test
5. **Test Edge Cases**: Include error conditions

### Performance
1. **Fast Unit Tests**: < 1s each
2. **Slow Tests Marked**: Use `@pytest.mark.slow`
3. **In-Memory Database**: Fast test execution
4. **Parallel Execution**: Use `pytest-xdist`

## Troubleshooting

### Common Issues

#### Django Settings Module Error
If you see `DJANGO_SETTINGS_MODULE` errors:
```bash
# The test configuration should handle this automatically, but if not:
export DJANGO_SETTINGS_MODULE=knowledgeinjester.test_settings

# Or use the provided scripts:
python scripts/management/run_tests.py
./run_tests.sh
```

#### Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Database Issues
```bash
# Run migrations
python manage.py migrate

# For test database issues
rm db.sqlite3
python manage.py migrate
```

#### Permission Errors
```bash
# Make scripts executable
chmod +x scripts/workers/worker.py
chmod +x run_tests.sh
chmod +x scripts/management/*.py
```

#### Coverage Issues
```bash
# Check coverage configuration
pytest --cov=apps --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Debug Commands
```bash
# Verbose output
pytest tests/ -v -s

# Debug specific test
pytest tests/unit/test_core_hashing.py::TestHashing::test_sha256_hash_string -v -s

# Show coverage details
pytest tests/ --cov=apps --cov-report=html
```

## Contributing

### Adding New Tests
1. **Follow Naming**: `test_*.py` files
2. **Choose Category**: Unit vs Integration
3. **Add Fixtures**: If needed for new data
4. **Update Documentation**: Keep this guide current
5. **Maintain Coverage**: Stay above 80%

### Test Standards
- **Coverage**: Minimum 80%
- **Speed**: Unit tests < 1s each
- **Isolation**: Tests don't depend on each other
- **Clarity**: Easy to understand and maintain

## Metrics & Goals

- **Total Tests**: 50+ tests
- **Coverage**: 80%+ (enforced)
- **Categories**: 6 test categories
- **CI Versions**: 3 Python versions
- **Execution Time**: < 30s for full suite
- **Reliability**: 99%+ test stability

---

## 🚀 Ready for Production!

Your knowledge injester now has a comprehensive, professional test suite that:
- ✅ Ensures code quality and reliability
- ✅ Catches regressions early
- ✅ Supports continuous integration
- ✅ Provides excellent developer experience
- ✅ Scales with your project growth

**Next Steps:**
1. Run the test suite: `python scripts/management/run_tests.py`
2. Set up CI/CD with GitHub Actions
3. Add more tests as you develop new features
4. Monitor coverage and maintain quality standards

