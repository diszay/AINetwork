# Contributing to NetArchon

**Want to help make NetArchon better?** We'd love your help! Whether you're a beginner who found a typo or an expert who wants to add new features, every contribution matters.

## 🎯 How You Can Help

**For Everyone:**
- **Report bugs** - Tell us when something doesn't work
- **Suggest improvements** - Share ideas for new features
- **Improve documentation** - Help make our guides clearer
- **Share your experience** - Tell others about NetArchon

**For Technical Contributors:**
- **Fix bugs** - Solve issues in the code
- **Add features** - Build new functionality
- **Write tests** - Help ensure quality
- **Review code** - Help other contributors

## Table of Contents

1. [Getting Started](#getting-started) - First steps for any contributor
2. [Ways to Contribute](#ways-to-contribute) - Different ways to help
3. [Development Setup](#development-setup) - Setting up your coding environment
4. [Code Guidelines](#code-guidelines) - How we write code
5. [Testing](#testing) - Making sure everything works
6. [Documentation](#documentation) - Writing helpful guides
7. [Submitting Changes](#submitting-changes) - How to share your work
8. [Community Guidelines](#community-guidelines) - Being respectful and helpful

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of network automation concepts
- Familiarity with SSH and network device management

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues in existing code
- **New features**: Add new functionality
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Examples**: Provide usage examples
- **Device support**: Add support for new device types

## Development Setup

### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/yourusername/netarchon.git
cd netarchon

# Add the upstream repository
git remote add upstream https://github.com/originalowner/netarchon.git
```

### 2. Set Up Development Environment

```bash
# Set up the development environment
python scripts/setup_dev_env.py

# Activate the virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files (optional)
pre-commit run --all-files
```

### 4. Verify Setup

```bash
# Run tests to verify everything is working
make test-unit

# Run linting checks
make lint

# Check code formatting
make format-check
```

## Code Style and Standards

### Python Code Style

We follow PEP 8 with some modifications:

- **Line length**: 88 characters (Black default)
- **Import sorting**: Use isort with Black profile
- **Type hints**: Required for all public functions and methods
- **Docstrings**: Google style docstrings for all public APIs

### Code Formatting

We use automated code formatting:

```bash
# Format code automatically
make format

# Check formatting without making changes
make format-check
```

### Linting

We use multiple linting tools:

```bash
# Run all linting checks
make lint

# Individual tools
flake8 src/ tests/
mypy src/netarchon/
bandit -r src/
```

### Example Code Style

```python
"""Module docstring describing the module purpose."""

import os
import sys
from typing import Dict, List, Optional, Union

from netarchon.utils.logger import get_logger
from netarchon.utils.exceptions import NetArchonError

logger = get_logger(__name__)


class ExampleClass:
    """Example class demonstrating code style.
    
    This class shows the expected code style including docstrings,
    type hints, and formatting.
    
    Attributes:
        name: The name of the example
        value: An optional value
    """
    
    def __init__(self, name: str, value: Optional[int] = None) -> None:
        """Initialize the example class.
        
        Args:
            name: The name for this example
            value: Optional value to store
            
        Raises:
            ValueError: If name is empty
        """
        if not name:
            raise ValueError("Name cannot be empty")
            
        self.name = name
        self.value = value
        logger.debug(f"Created ExampleClass with name: {name}")
    
    def process_data(self, data: List[Dict[str, Union[str, int]]]) -> Dict[str, int]:
        """Process a list of data dictionaries.
        
        Args:
            data: List of dictionaries containing data to process
            
        Returns:
            Dictionary with processed results
            
        Raises:
            NetArchonError: If processing fails
        """
        try:
            result = {}
            for item in data:
                if "key" in item and "value" in item:
                    result[str(item["key"])] = int(item["value"])
            return result
        except (KeyError, ValueError) as e:
            raise NetArchonError(f"Failed to process data: {e}") from e
```

## Testing

### Test Structure

Tests are organized in the `tests/` directory:

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── performance/    # Performance tests
└── data/          # Test data files
```

### Writing Tests

#### Unit Tests

```python
"""Unit tests for example module."""

import pytest
from unittest.mock import Mock, patch

from netarchon.core.example import ExampleClass
from netarchon.utils.exceptions import NetArchonError


class TestExampleClass:
    """Test cases for ExampleClass."""
    
    def test_init_success(self):
        """Test successful initialization."""
        example = ExampleClass("test", 42)
        assert example.name == "test"
        assert example.value == 42
    
    def test_init_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            ExampleClass("")
    
    @patch('netarchon.core.example.logger')
    def test_init_logs_creation(self, mock_logger):
        """Test that initialization logs creation."""
        ExampleClass("test")
        mock_logger.debug.assert_called_once_with("Created ExampleClass with name: test")
    
    def test_process_data_success(self):
        """Test successful data processing."""
        example = ExampleClass("test")
        data = [
            {"key": "item1", "value": 10},
            {"key": "item2", "value": 20}
        ]
        result = example.process_data(data)
        assert result == {"item1": 10, "item2": 20}
    
    def test_process_data_invalid_data_raises_error(self):
        """Test that invalid data raises NetArchonError."""
        example = ExampleClass("test")
        data = [{"invalid": "data"}]
        
        with pytest.raises(NetArchonError, match="Failed to process data"):
            example.process_data(data)
```

#### Integration Tests

```python
"""Integration tests for device operations."""

import os
import pytest
from unittest import mock

from netarchon.core.ssh_connector import SSHConnector
from netarchon.models.device import Device, DeviceType


# Skip if integration tests not enabled
pytestmark = pytest.mark.skipif(
    os.environ.get('NETARCHON_INTEGRATION_TESTS') != 'true',
    reason="Integration tests disabled"
)


@pytest.fixture
def test_device():
    """Create a test device."""
    return Device(
        name="test-device",
        hostname=os.environ.get('TEST_DEVICE_HOST', '192.168.1.1'),
        device_type=DeviceType.CISCO_IOS,
        connection_params=ConnectionParameters(
            username=os.environ.get('TEST_USERNAME', 'admin'),
            password=os.environ.get('TEST_PASSWORD', 'password')
        )
    )


class TestDeviceIntegration:
    """Integration tests for device operations."""
    
    def test_device_connection(self, test_device):
        """Test connecting to a real device."""
        ssh_connector = SSHConnector()
        
        try:
            result = ssh_connector.connect(test_device)
            assert result is True
            assert ssh_connector.is_connected(test_device.hostname)
        finally:
            ssh_connector.disconnect(test_device.hostname)
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-performance

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_ssh_connector.py -v

# Run specific test method
pytest tests/unit/test_ssh_connector.py::TestSSHConnector::test_connect_success -v
```

### Test Environment Variables

For integration tests, set these environment variables:

```bash
export NETARCHON_INTEGRATION_TESTS=true
export NETARCHON_TEST_HOST=192.168.1.1
export NETARCHON_TEST_USERNAME=admin
export NETARCHON_TEST_PASSWORD=password
export NETARCHON_TEST_DEVICE_TYPE=cisco_ios
```

## Documentation

### Documentation Types

1. **API Documentation**: Docstrings in code
2. **User Guide**: High-level usage documentation
3. **Examples**: Working code examples
4. **README**: Project overview and quick start

### Writing Documentation

#### Docstrings

Use Google-style docstrings:

```python
def connect_device(device: Device, timeout: int = 30) -> bool:
    """Connect to a network device.
    
    Establishes an SSH connection to the specified device with
    the given timeout value.
    
    Args:
        device: The device to connect to
        timeout: Connection timeout in seconds
        
    Returns:
        True if connection successful, False otherwise
        
    Raises:
        ConnectionError: If connection fails due to network issues
        AuthenticationError: If authentication fails
        
    Example:
        >>> device = Device("router1", "192.168.1.1", DeviceType.CISCO_IOS)
        >>> success = connect_device(device, timeout=60)
        >>> if success:
        ...     print("Connected successfully")
    """
```

#### User Documentation

- Write clear, concise explanations
- Include working code examples
- Cover common use cases
- Provide troubleshooting information

#### Examples

Create complete, runnable examples:

```python
#!/usr/bin/env python3
"""Example: Basic device connection and command execution."""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from netarchon.core.ssh_connector import SSHConnector
# ... rest of imports

def main():
    """Main function demonstrating basic usage."""
    # Create device
    device = Device(...)
    
    # Connect and execute commands
    ssh_connector = SSHConnector()
    try:
        if ssh_connector.connect(device):
            # ... example code
            pass
    finally:
        ssh_connector.disconnect(device.hostname)

if __name__ == "__main__":
    main()
```

## Submitting Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-juniper-support`
- `bugfix/fix-connection-timeout`
- `docs/update-user-guide`
- `test/add-monitoring-tests`

### Commit Messages

Write clear, descriptive commit messages:

```
Add support for Juniper JunOS devices

- Implement JunOS-specific command patterns
- Add device detection for Juniper devices
- Update documentation with JunOS examples
- Add unit tests for JunOS functionality

Fixes #123
```

### Pull Request Process

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   make test
   make lint
   make format-check
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Your descriptive commit message"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a pull request**:
   - Go to GitHub and create a pull request
   - Fill out the pull request template
   - Link any related issues

### Pull Request Template

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Test improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)

## Related Issues
Fixes #(issue number)
```

## Code Review Process

### Review Criteria

Reviewers will check for:

1. **Functionality**: Does the code work as intended?
2. **Code quality**: Is the code well-structured and readable?
3. **Testing**: Are there adequate tests?
4. **Documentation**: Is documentation updated?
5. **Performance**: Are there any performance implications?
6. **Security**: Are there any security concerns?

### Addressing Review Comments

1. **Read carefully**: Understand the reviewer's concerns
2. **Ask questions**: If something is unclear, ask for clarification
3. **Make changes**: Address the feedback appropriately
4. **Respond**: Reply to comments explaining your changes
5. **Request re-review**: Ask for another review when ready

### Review Timeline

- Initial review: Within 2-3 business days
- Follow-up reviews: Within 1-2 business days
- Merge: After approval from at least one maintainer

## Community Guidelines

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/):

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Pull Requests**: Code review and technical discussions

### Getting Help

If you need help:

1. Check existing documentation
2. Search GitHub issues and discussions
3. Ask questions in GitHub Discussions
4. Reach out to maintainers

## Development Tips

### Debugging

```python
# Use logging for debugging
from netarchon.utils.logger import get_logger
logger = get_logger(__name__)
logger.debug("Debug message")

# Use pdb for interactive debugging
import pdb; pdb.set_trace()
```

### Performance

```python
# Profile code performance
import time
start = time.time()
# ... your code
print(f"Execution time: {time.time() - start:.2f}s")

# Memory profiling
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

### Testing with Mock Devices

```python
# Use mock devices for testing
from unittest.mock import Mock

mock_device = Mock()
mock_device.hostname = "test-device"
mock_device.device_type = DeviceType.CISCO_IOS
```

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. Update version number
2. Update CHANGELOG.md
3. Run full test suite
4. Create release branch
5. Tag release
6. Build and publish packages
7. Update documentation

## Recognition

Contributors are recognized in:

- CONTRIBUTORS.md file
- Release notes
- GitHub contributor statistics

Thank you for contributing to NetArchon!