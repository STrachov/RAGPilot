# Authentication Integration Tests

This directory contains integration tests for the authentication and user management system. These tests verify that user registration, authentication, authorization, and security features work correctly.

## Structure

```
tests/
│
├── integration/
│   └── user/
│       ├── test_registration.py    # User registration tests
│       ├── test_authentication.py  # Authentication and token tests
│       ├── test_authorization.py   # Role-based access control tests
│       └── test_security.py        # Security-related tests
│
├── run_auth_tests.py               # Script to run all auth tests
├── run_single_test.py              # Script to run individual tests
└── README.md                       # This file
```

## Running Tests

### Prerequisites

1. Make sure you have all dependencies installed:
   ```
   pip install -r requirements-dev.txt
   ```

2. Make sure your environment variables are properly set up. You may need to set:
   ```
   export TEST_DATABASE_URL=sqlite:///./test.db
   export SECRET_KEY=testsecretkey
   ```

### Running All Auth Tests

To run all authentication tests:

```bash
python tests/run_auth_tests.py
```

### Running Specific Tests

To run a specific test file:

```bash
python tests/run_single_test.py tests/integration/user/test_authentication.py
```

To run a specific test function:

```bash
python tests/run_single_test.py tests/integration/user/test_authentication.py::test_login_success
```

### Using pytest Directly

You can also use pytest directly:

```bash
# Run all tests
pytest tests/integration/user/

# Run a specific test file
pytest tests/integration/user/test_authentication.py

# Run a specific test
pytest tests/integration/user/test_authentication.py::test_login_success
```

## Writing New Tests

When adding new tests, follow these guidelines:

1. Place tests in the appropriate file based on functionality
2. Use descriptive test names that indicate what's being tested
3. Use fixtures from conftest.py for common setup
4. Keep tests independent of each other
5. Clean up after tests to maintain isolation

## Mocking External Dependencies

The tests use pytest's monkeypatch fixture to mock dependencies. This allows you to test the system without calling external services.

Example:

```python
def test_some_external_service(client, monkeypatch):
    # Mock the external service
    def mock_service(*args, **kwargs):
        return {"success": True}
    
    monkeypatch.setattr("app.services.external_service.call", mock_service)
    
    # Test the endpoint that uses the external service
    response = client.post("/api/endpoint")
    assert response.status_code == 200
``` 