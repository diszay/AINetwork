#!/usr/bin/env python3
"""Deployment script for NetArchon.

This script handles building and deploying NetArchon packages
to various targets including PyPI, Docker, and local installations.
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run a command and return the result.
    
    Args:
        command: Command to run as a list of strings
        cwd: Working directory for the command
        check: Whether to raise an exception on non-zero exit code
        
    Returns:
        CompletedProcess object
    """
    print(f"Running: {' '.join(command)}")
    return subprocess.run(command, cwd=cwd, check=check)


def clean_build_artifacts():
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    
    artifacts = [
        "build/",
        "dist/",
        "*.egg-info/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/"
    ]
    
    for artifact in artifacts:
        if "*" in artifact:
            # Handle glob patterns
            import glob
            for path in glob.glob(artifact):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        else:
            if os.path.exists(artifact):
                if os.path.isdir(artifact):
                    shutil.rmtree(artifact)
                else:
                    os.remove(artifact)
    
    # Clean Python cache files
    for root, dirs, files in os.walk("."):
        for dir_name in dirs[:]:
            if dir_name == "__pycache__":
                shutil.rmtree(os.path.join(root, dir_name))
                dirs.remove(dir_name)
        for file_name in files:
            if file_name.endswith(".pyc"):
                os.remove(os.path.join(root, file_name))


def run_tests():
    """Run all tests before deployment."""
    print("Running tests...")
    
    # Run unit tests
    result = run_command([
        "python", "scripts/run_tests.py", "unit", "--coverage"
    ], check=False)
    
    if result.returncode != 0:
        print("Unit tests failed!")
        return False
    
    # Run linting
    result = run_command([
        "python", "scripts/run_tests.py", "lint"
    ], check=False)
    
    if result.returncode != 0:
        print("Linting failed!")
        return False
    
    # Run formatting check
    result = run_command([
        "python", "scripts/run_tests.py", "format-check"
    ], check=False)
    
    if result.returncode != 0:
        print("Formatting check failed!")
        return False
    
    print("All tests passed!")
    return True


def build_package():
    """Build the package."""
    print("Building package...")
    
    # Ensure build tools are installed
    run_command(["python", "-m", "pip", "install", "--upgrade", "build", "twine"])
    
    # Build the package
    run_command(["python", "-m", "build"])
    
    # Check the package
    run_command(["python", "-m", "twine", "check", "dist/*"])
    
    print("Package built successfully!")


def deploy_to_pypi(test=False):
    """Deploy to PyPI or TestPyPI.
    
    Args:
        test: Whether to deploy to TestPyPI instead of PyPI
    """
    if test:
        print("Deploying to TestPyPI...")
        repository = "--repository testpypi"
    else:
        print("Deploying to PyPI...")
        repository = ""
    
    # Check for required environment variables
    if test:
        username_var = "TESTPYPI_USERNAME"
        password_var = "TESTPYPI_PASSWORD"
    else:
        username_var = "PYPI_USERNAME"
        password_var = "PYPI_PASSWORD"
    
    username = os.environ.get(username_var)
    password = os.environ.get(password_var)
    
    if not username or not password:
        print(f"Error: {username_var} and {password_var} environment variables must be set")
        return False
    
    # Upload to PyPI
    cmd = ["python", "-m", "twine", "upload"]
    if repository:
        cmd.extend(repository.split())
    cmd.extend([
        "--username", username,
        "--password", password,
        "dist/*"
    ])
    
    try:
        run_command(cmd)
        print("Package deployed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("Deployment failed!")
        return False


def create_docker_image():
    """Create Docker image."""
    print("Creating Docker image...")
    
    # Check if Dockerfile exists
    if not os.path.exists("Dockerfile"):
        print("Creating basic Dockerfile...")
        dockerfile_content = '''FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    openssh-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY setup.py .
COPY README.md .

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 netarchon
USER netarchon

# Set default command
CMD ["python", "-m", "netarchon"]
'''
        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)
    
    # Build Docker image
    run_command(["docker", "build", "-t", "netarchon:latest", "."])
    
    print("Docker image created successfully!")


def install_locally():
    """Install the package locally."""
    print("Installing package locally...")
    
    # Install in development mode
    run_command(["python", "-m", "pip", "install", "-e", "."])
    
    print("Package installed locally!")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Deploy NetArchon")
    parser.add_argument(
        "target",
        choices=["local", "pypi", "testpypi", "docker", "all"],
        help="Deployment target"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests before deployment"
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleaning build artifacts"
    )
    
    args = parser.parse_args()
    
    # Clean build artifacts
    if not args.skip_clean:
        clean_build_artifacts()
    
    # Run tests
    if not args.skip_tests:
        if not run_tests():
            print("Tests failed, aborting deployment")
            return 1
    
    # Build package for most targets
    if args.target in ["pypi", "testpypi", "local", "all"]:
        build_package()
    
    # Deploy to target
    if args.target == "local" or args.target == "all":
        install_locally()
    
    if args.target == "pypi" or args.target == "all":
        if not deploy_to_pypi(test=False):
            return 1
    
    if args.target == "testpypi":
        if not deploy_to_pypi(test=True):
            return 1
    
    if args.target == "docker" or args.target == "all":
        create_docker_image()
    
    print("Deployment completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())