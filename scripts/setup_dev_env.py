#!/usr/bin/env python3
"""Setup development environment for NetArchon.

This script sets up a development environment for NetArchon by creating
virtual environments, installing dependencies, and configuring pre-commit hooks.
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


def run_command(command, cwd=None, exit_on_error=True):
    """Run a shell command and return the output.
    
    Args:
        command: Command to run as a list of strings
        cwd: Working directory for the command
        exit_on_error: Whether to exit on error
        
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
    
    if process.returncode != 0 and exit_on_error:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Error: {stderr.strip()}")
        sys.exit(process.returncode)
        
    return process.returncode, stdout, stderr


def create_virtual_env(venv_path, python_executable=None):
    """Create a virtual environment.
    
    Args:
        venv_path: Path where to create the virtual environment
        python_executable: Python executable to use
        
    Returns:
        Path to the created virtual environment
    """
    venv_path = Path(venv_path).absolute()
    
    if venv_path.exists():
        print(f"Virtual environment already exists at {venv_path}")
        return venv_path
    
    print(f"Creating virtual environment at {venv_path}")
    
    cmd = [sys.executable, "-m", "venv", str(venv_path)]
    if python_executable:
        cmd = [python_executable, "-m", "venv", str(venv_path)]
        
    run_command(cmd)
    return venv_path


def install_dependencies(venv_path, dev_mode=True):
    """Install dependencies in the virtual environment.
    
    Args:
        venv_path: Path to the virtual environment
        dev_mode: Whether to install development dependencies
    """
    venv_path = Path(venv_path).absolute()
    
    # Determine pip executable path
    if platform.system() == "Windows":
        pip_path = venv_path / "Scripts" / "pip"
    else:
        pip_path = venv_path / "bin" / "pip"
    
    # Upgrade pip
    run_command([str(pip_path), "install", "--upgrade", "pip"])
    
    # Install dependencies
    requirements_file = "requirements-dev.txt" if dev_mode else "requirements.txt"
    if not Path(requirements_file).exists():
        print(f"Warning: {requirements_file} not found, falling back to requirements.txt")
        requirements_file = "requirements.txt"
        
    run_command([str(pip_path), "install", "-r", requirements_file])
    
    # Install package in development mode
    run_command([str(pip_path), "install", "-e", "."])


def setup_pre_commit(venv_path):
    """Set up pre-commit hooks.
    
    Args:
        venv_path: Path to the virtual environment
    """
    venv_path = Path(venv_path).absolute()
    
    # Determine pre-commit executable path
    if platform.system() == "Windows":
        pre_commit_path = venv_path / "Scripts" / "pre-commit"
    else:
        pre_commit_path = venv_path / "bin" / "pre-commit"
    
    # Check if pre-commit config exists
    if not Path(".pre-commit-config.yaml").exists():
        print("Warning: .pre-commit-config.yaml not found, skipping pre-commit setup")
        return
    
    # Install pre-commit
    if platform.system() == "Windows":
        pip_path = venv_path / "Scripts" / "pip"
    else:
        pip_path = venv_path / "bin" / "pip"
        
    run_command([str(pip_path), "install", "pre-commit"])
    
    # Install pre-commit hooks
    run_command([str(pre_commit_path), "install"])
    
    # Run pre-commit once to set up the hooks
    run_command([str(pre_commit_path), "run", "--all-files"], exit_on_error=False)


def setup_test_environment(venv_path):
    """Set up test environment.
    
    Args:
        venv_path: Path to the virtual environment
    """
    # Create test directories if they don't exist
    for test_dir in ["tests/unit", "tests/integration", "tests/data"]:
        os.makedirs(test_dir, exist_ok=True)
    
    # Create test directories for backups and metrics
    os.makedirs("backups", exist_ok=True)
    os.makedirs("metrics", exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Setup development environment for NetArchon")
    parser.add_argument(
        "--venv", 
        default=".venv", 
        help="Path to create virtual environment (default: .venv)"
    )
    parser.add_argument(
        "--python", 
        default=None, 
        help="Python executable to use (default: current Python)"
    )
    parser.add_argument(
        "--no-dev", 
        action="store_true", 
        help="Don't install development dependencies"
    )
    parser.add_argument(
        "--no-pre-commit", 
        action="store_true", 
        help="Don't set up pre-commit hooks"
    )
    
    args = parser.parse_args()
    
    # Create virtual environment
    venv_path = create_virtual_env(args.venv, args.python)
    
    # Install dependencies
    install_dependencies(venv_path, not args.no_dev)
    
    # Setup pre-commit hooks
    if not args.no_pre_commit:
        setup_pre_commit(venv_path)
    
    # Setup test environment
    setup_test_environment(venv_path)
    
    print("\nDevelopment environment setup complete!")
    print(f"Virtual environment created at: {venv_path}")
    print("\nTo activate the virtual environment:")
    
    if platform.system() == "Windows":
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print(f"  source {venv_path}/bin/activate")
    
    print("\nTo run tests:")
    print("  pytest tests/")
    print("\nTo run with coverage:")
    print("  pytest --cov=netarchon tests/")


if __name__ == "__main__":
    main()