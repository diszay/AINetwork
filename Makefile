# Makefile for NetArchon development

.PHONY: help install install-dev test test-unit test-integration test-performance lint format format-check clean docs build

# Default target
help:
	@echo "NetArchon Development Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies and setup environment"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-coverage    Run unit tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run all linting checks"
	@echo "  format           Fix code formatting"
	@echo "  format-check     Check code formatting"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Build:"
	@echo "  build            Build distribution packages"
	@echo "  clean            Clean build artifacts"

# Installation targets
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	python scripts/setup_dev_env.py

# Testing targets
test:
	python scripts/run_tests.py all

test-unit:
	python scripts/run_tests.py unit

test-integration:
	python scripts/run_tests.py integration

test-performance:
	python scripts/run_tests.py performance

test-coverage:
	python scripts/run_tests.py unit --coverage

# Code quality targets
lint:
	python scripts/run_tests.py lint

format:
	python scripts/run_tests.py format-fix

format-check:
	python scripts/run_tests.py format-check

# Documentation targets
docs:
	@echo "Generating documentation..."
	@if [ -d "docs/_build" ]; then rm -rf docs/_build; fi
	@mkdir -p docs/_build
	@echo "Documentation generation not yet implemented"

# Build targets
build:
	@echo "Building distribution packages..."
	python -m build

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete