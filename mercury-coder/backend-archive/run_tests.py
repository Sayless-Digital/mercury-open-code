#!/usr/bin/env python3
"""Simple test runner to execute and display test results."""
import sys
import pytest

if __name__ == "__main__":
    # Run pytest with verbose output
    args = [
        "tests/test_agent_improvements.py",
        "-v",
        "--tb=short",
        "-s",
        "--color=yes"
    ]
    
    exit_code = pytest.main(args)
    print(f"\n{'='*60}")
    print(f"Tests completed with exit code: {exit_code}")
    print(f"{'='*60}\n")
    sys.exit(exit_code)