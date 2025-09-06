# Knowledge Injester Test Suite

This directory contains comprehensive unit and integration tests for the knowledge injester system.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/                 # Test data fixtures
│   ├── __init__.py
│   └── sample_data.py       # Sample data for testing
├── unit/                    # Unit tests
│   ├── test_core_hashing.py
│   ├── test_core_storage.py
│   ├── test_core_types.py
│   ├── test_crawler_services.py
│   ├── test_extractor_services.py
│   └── test_vectorizer_services.py
├── integration/             # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_database_models.py
│   ├── test_full_pipeline.py
│   └── test_crawl_api.py    # Standalone API test script
└── README.md               # This file
```

## Running Tests

### Prerequisites

1. **Activate Virtual Environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Install Test Dependencies:**
   ```bash
   pip install pytest pytest-django pytest-cov
   ```

3. **Setup Test Database:**
   ```bash
   python manage.py migrate
   ```

### Test Commands

#### Run All Tests
```bash
pytest tests/ -v
```

#### Run Unit Tests Only
```bash
pytest tests/unit/ -v
```

#### Run Integration Tests Only
```bash
pytest tests/integration/ -v
```

#### Run Tests with Coverage
```bash
pytest tests/ -v --cov=apps --cov-report=html --cov-report=term-missing
```

#### Run Specific Test File
```bash
pytest tests/unit/test_core_hashing.py -v
```

#### Run Tests with Markers
```bash
pytest tests/ -m "unit" -v
pytest tests/ -m "integration" -v
pytest tests/ -m "api" -v
```

### Using Management Scripts

#### Run Complete Test Suite
```bash
python scripts/management/run_tests.py
```

#### Setup Development Environment
```bash
python scripts/management/setup_dev.py
```

### Standalone API Testing

For testing against a running server:

```bash
# Start Django server
python manage.py runserver

# In another terminal, run API tests
python tests/integration/test_crawl_api.py
```

## Test Categories

### Unit Tests (`tests/unit/`)

- **Core Utilities**: Hashing, storage, logging, environment
- **Type Definitions**: Pydantic models and validation
- **Service Functions**: Individual service layer functions
- **Business Logic**: Isolated business logic testing

### Integration Tests (`tests/integration/`)

- **API Endpoints**: Full HTTP request/response testing
- **Database Models**: Django model integration
- **Full Pipeline**: End-to-end workflow testing
- **External Services**: Mocked external service integration

## Test Fixtures

### Database Fixtures
- `test_organization`: Sample organization
- `test_data_source`: Sample data source
- `test_crawl_job`: Sample crawl job
- `test_ingest_job`: Sample ingest job

### Data Fixtures
- `sample_page_raw`: Sample PageRaw object
- `sample_doc`: Sample Doc object
- `sample_chunk`: Sample Chunk object

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Django settings: `knowledgeinjester.test_settings`
- Coverage requirements: 80% minimum
- Test markers for categorization
- Output formatting and verbosity

### Test Settings (`knowledgeinjester/test_settings.py`)
- In-memory SQLite database
- Disabled migrations for speed
- Mock external services
- Test-specific logging configuration

## Coverage Requirements

- **Minimum Coverage**: 80%
- **Coverage Reports**: HTML and terminal output
- **Excluded Files**: Migration files, test files
- **Included Apps**: All custom apps in `apps/`

## Continuous Integration

### GitHub Actions (`.github/workflows/test.yml`)
- Runs on Python 3.10, 3.11, 3.12
- Installs dependencies
- Runs all test categories
- Generates coverage reports
- Uploads to Codecov

### Local CI
```bash
# Run full CI pipeline locally
python scripts/management/run_tests.py
```

## Best Practices

### Writing Tests
1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: One test per behavior
3. **Arrange-Act-Assert**: Clear test structure
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include error conditions and boundary cases

### Test Data
1. **Use Fixtures**: Leverage pytest fixtures for common data
2. **Isolated Data**: Each test should be independent
3. **Cleanup**: Clean up after tests (handled by fixtures)
4. **Realistic Data**: Use realistic test data when possible

### Performance
1. **Fast Unit Tests**: Keep unit tests fast (< 1s each)
2. **Slow Integration Tests**: Mark slow tests with `@pytest.mark.slow`
3. **Database Optimization**: Use in-memory database for tests
4. **Parallel Execution**: Use `pytest-xdist` for parallel test execution

## Debugging Tests

### Verbose Output
```bash
pytest tests/ -v -s
```

### Debug Specific Test
```bash
pytest tests/unit/test_core_hashing.py::TestHashing::test_sha256_hash_string -v -s
```

### Show Coverage Details
```bash
pytest tests/ --cov=apps --cov-report=html
# Open htmlcov/index.html in browser
```

### Django Debug
```bash
# Enable Django debug in test settings
DEBUG = True
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Database Errors**: Run migrations before tests
3. **Permission Errors**: Check file system permissions
4. **Memory Issues**: Use in-memory database for tests

### Test Database Issues
```bash
# Reset test database
rm db.sqlite3
python manage.py migrate
```

### Coverage Issues
```bash
# Check coverage configuration
pytest --cov=apps --cov-report=term-missing
```

## Contributing

When adding new tests:

1. **Follow Naming Conventions**: `test_*.py` files
2. **Add to Appropriate Category**: Unit vs Integration
3. **Update Fixtures**: Add new fixtures if needed
4. **Document New Tests**: Update this README
5. **Maintain Coverage**: Ensure coverage stays above 80%

## Test Metrics

- **Total Tests**: 50+ tests
- **Coverage Target**: 80%+
- **Test Categories**: 6 categories
- **CI Pipeline**: 3 Python versions
- **Execution Time**: < 30 seconds for full suite


