"""
NetArchon Setup Configuration
"""

from setuptools import setup, find_packages
import os

# Read the README file for the long description
def read_file(filename):
    """Read a file and return its contents."""
    with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
        return f.read()

# Read requirements from requirements.txt
def read_requirements(filename):
    """Read requirements from a file."""
    requirements = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove version constraints for setup.py
                    if '>=' in line:
                        pkg_name = line.split('>=')[0]
                    elif '==' in line:
                        pkg_name = line.split('==')[0]
                    elif '<' in line:
                        pkg_name = line.split('<')[0]
                    else:
                        pkg_name = line
                    requirements.append(pkg_name.strip())
    except FileNotFoundError:
        pass
    return requirements

setup(
    name="netarchon",
    version="1.0.0",
    description="NetArchon AI Network Engineer - Autonomous network monitoring and management",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="NetArchon Development Team",
    author_email="dev@netarchon.ai",
    url="https://github.com/diszay/AINetwork",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9,<4.0",
    install_requires=[
        "paramiko>=2.9.0",
        "pytest>=7.0.0", 
        "pytest-cov>=4.0.0",
        "pytest-asyncio>=0.21.0",
        "pyyaml>=6.0",
        "requests>=2.25.0",
        "cryptography>=3.4.0",
        "streamlit>=1.28.0",
        "pandas>=1.3.0",
        "plotly>=5.0.0",
        "keyring>=23.0.0",
    ],
    extras_require={
        "dev": [
            "black>=22.0.0",
            "flake8>=4.0.0", 
            "mypy>=1.0.0",
            "pytest-mock>=3.6.0",
        ],
        "web": [
            "streamlit>=1.28.0",
            "pandas>=1.3.0",
            "plotly>=5.0.0",
            "altair>=4.2.0",
        ],
        "security": [
            "keyring>=23.0.0",
            "cryptography>=3.4.0",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="network monitoring automation ssh device management",
    entry_points={
        "console_scripts": [
            "netarchon=netarchon.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "netarchon": [
            "config/*.yaml",
            "web/pages/*.py",
            "templates/*.html",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/diszay/AINetwork/issues",
        "Source": "https://github.com/diszay/AINetwork",
        "Documentation": "https://github.com/diszay/AINetwork/docs",
    },
)