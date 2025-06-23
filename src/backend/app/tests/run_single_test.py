#!/usr/bin/env python
"""
Runner for a single test or test class.

Usage:
    python tests/run_single_test.py <test_path>::<test_function>
    
Example:
    python tests/run_single_test.py tests/integration/user/test_authentication.py::test_login_success
    python tests/run_single_test.py tests/integration/user/test_security.py
"""
import os
import sys
import pytest


def main():
    """Run a specific test or test file."""
    # Add the src directory to the path so imports work
    src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    sys.path.insert(0, src_path)
    
    # Get test path from command line arguments
    if len(sys.argv) < 2:
        print("Error: Please specify a test path.")
        print(__doc__)
        return 1
    
    test_path = sys.argv[1]
    
    # Additional pytest arguments can be passed after the test path
    pytest_args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    # Run the test
    return pytest.main([
        "-v",                      # Verbose output
        "--showlocals",            # Show local variables in tracebacks
        "-xvs",                    # Exit on first failure, verbose, don't capture output
        test_path,                 # The test file or specific test to run
        *pytest_args               # Any additional pytest arguments
    ])


if __name__ == "__main__":
    sys.exit(main()) 