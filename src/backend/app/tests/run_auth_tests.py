#!/usr/bin/env python
"""
Test runner for auth-related integration tests.

This script runs the auth-related integration tests with proper configuration.
"""
import os
import sys
import pytest


def main():
    """Run the auth integration tests."""
    # Add the src directory to the path so imports work
    src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    sys.path.insert(0, src_path)
    
    # Define test paths
    test_paths = [
        "tests/integration/user/test_registration.py",
        "tests/integration/user/test_authentication.py",
        "tests/integration/user/test_authorization.py",
        "tests/integration/user/test_security.py",
    ]
    
    # Run the tests
    return pytest.main([
        "-v",                      # Verbose output
        "--no-header",             # No header
        "--no-summary",            # No summary
        "--showlocals",            # Show local variables in tracebacks
        "-xvs",                    # Exit on first failure, verbose, don't capture output
        *test_paths                # The test files to run
    ])


if __name__ == "__main__":
    sys.exit(main()) 