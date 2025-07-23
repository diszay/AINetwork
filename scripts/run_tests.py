#!/usr/bin/env python3
"""Run tests with various configurations for NetArchon.

This script provides different test execution modes including unit tests,
integration tests, performance tests, and coverage reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, cwd=None):
    """Run a command and return the result.
    
    Args:
        command: Command to run as a list of strings
        cwd: Working directory for the command
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    print(f"Running: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def run_unit_tests(coverage=False, verbose=False):
    """Run unit tests.
    
    Args:
        coverage: Whether to run with coverage reporting
        verbose: Whether to run in verbose mode
        
    Returns:
        Exit code from pytest
    """
    cmd = ["python", "-m", "pytest", "tests/unit/"]
    
    if coverage:
        cmd.extend(["--cov=netarchon", "--cov-report=html", "--cov-report=term"])
    
    if verbose:
        cmd.append("-v")
    
    # Add markers to exclude integration and performance tests
    cmd.extend(["-m", "not integration and not performance"])
    
    return_code, stdout, stderr = run_command(cmd)
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    return return_code


def run_integration_tests(verbose=False):
    """Run integration tests.
    
    Args:
        verbose: Whether to run in verbose mode
        
    Returns:
        Exit code from pytest
    """
    # Check if integration tests are enabled
    if os.environ.get('NETARCHON_INTEGRATION_TESTS') != 'true':
        print("Integration tests are disabled.")
        print("Set NETARCHON_INTEGRATION_TESTS=true to enable.")
        return 0
    
    cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    return_code, stdout, stderr = run_command(cmd)
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    return return_code


def run_performance_tests(verbose=False):
    """Run performance tests.
    
    Args:
        verbose: Whether to run in verbose mode
        
    Returns:
        Exit code from pytest
    """
    # Check if performance tests are enabled
    if os.environ.get('NETARCHON_PERFORMANCE_TESTS') != 'true':
        print("Performance tests are disabled.")
        print("Set NETARCHON_PERFORMANCE_TESTS=true to enable.")
        return 0
    
    cmd = ["python", "-m", "pytest", "tests/performance/", "-m", "performance"]
    
    if verbose:
        cmd.append("-v")
    
    return_code, stdout, stderr = run_command(cmd)
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    return return_code


def run_all_tests(coverage=False, verbose=False):
    """Run all tests.
    
    Args:
        coverage: Whether to run with coverage reporting
        verbose: Whether to run in verbose mode
        
    Returns:
        Exit code (0 if all tests pass, non-zero otherwise)
    """
    print("Running unit tests...")
    unit_result = run_unit_tests(coverage=coverage, verbose=verbose)
    
    print("\nRunning integration tests...")
    integration_result = run_integration_tests(verbose=verbose)
    
    print("\nRunning performance tests...")
    performance_result = run_performance_tests(verbose=verbose)
    
    # Return non-zero if any test suite failed
    if unit_result != 0:
        print("Unit tests failed!")
        return unit_result
    
    if integration_result != 0:
        print("Integration tests failed!")
        return integration_result
    
    if performance_result != 0:
        print("Performance tests failed!")
        return performance_result
    
    print("All tests passed!")
    return 0


def run_linting():
    """Run code linting checks.
    
    Returns:
        Exit code (0 if all checks pass, non-zero otherwise)
    """
    print("Running flake8...")
    flake8_result, stdout, stderr = run_command([
        "python", "-m", "flake8", "src/", "tests/", "scripts/", "examples/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    print("\nRunning mypy...")
    mypy_result, stdout, stderr = run_command([
        "python", "-m", "mypy", "src/netarchon/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    print("\nRunning bandit...")
    bandit_result, stdout, stderr = run_command([
        "python", "-m", "bandit", "-r", "src/", "-f", "text"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    # Return non-zero if any linting failed
    if flake8_result != 0:
        print("Flake8 checks failed!")
        return flake8_result
    
    if mypy_result != 0:
        print("MyPy checks failed!")
        return mypy_result
    
    if bandit_result != 0:
        print("Bandit security checks failed!")
        return bandit_result
    
    print("All linting checks passed!")
    return 0


def run_formatting_check():
    """Check code formatting.
    
    Returns:
        Exit code (0 if formatting is correct, non-zero otherwise)
    """
    print("Checking code formatting with black...")
    black_result, stdout, stderr = run_command([
        "python", "-m", "black", "--check", "--diff", "src/", "tests/", "scripts/", "examples/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    print("\nChecking import sorting with isort...")
    isort_result, stdout, stderr = run_command([
        "python", "-m", "isort", "--check-only", "--diff", "src/", "tests/", "scripts/", "examples/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    # Return non-zero if any formatting check failed
    if black_result != 0:
        print("Black formatting check failed!")
        return black_result
    
    if isort_result != 0:
        print("Isort formatting check failed!")
        return isort_result
    
    print("All formatting checks passed!")
    return 0


def fix_formatting():
    """Fix code formatting.
    
    Returns:
        Exit code (0 if successful, non-zero otherwise)
    """
    print("Fixing code formatting with black...")
    black_result, stdout, stderr = run_command([
        "python", "-m", "black", "src/", "tests/", "scripts/", "examples/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    print("\nFixing import sorting with isort...")
    isort_result, stdout, stderr = run_command([
        "python", "-m", "isort", "src/", "tests/", "scripts/", "examples/"
    ])
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    # Return non-zero if any formatting fix failed
    if black_result != 0:
        print("Black formatting failed!")
        return black_result
    
    if isort_result != 0:
        print("Isort formatting failed!")
        return isort_result
    
    print("Code formatting fixed!")
    return 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run tests and code quality checks for NetArchon")
    parser.add_argument(
        "command",
        choices=["unit", "integration", "performance", "all", "lint", "format-check", "format-fix"],
        help="Test or check type to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting (unit tests only)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Run in verbose mode"
    )
    
    args = parser.parse_args()
    
    if args.command == "unit":
        return run_unit_tests(coverage=args.coverage, verbose=args.verbose)
    elif args.command == "integration":
        return run_integration_tests(verbose=args.verbose)
    elif args.command == "performance":
        return run_performance_tests(verbose=args.verbose)
    elif args.command == "all":
        return run_all_tests(coverage=args.coverage, verbose=args.verbose)
    elif args.command == "lint":
        return run_linting()
    elif args.command == "format-check":
        return run_formatting_check()
    elif args.command == "format-fix":
        return fix_formatting()
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())