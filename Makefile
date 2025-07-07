.PHONY: help install install-dev test lint format type-check build publish clean run check setup-env

# Variables
PYTHON = poetry run python
PACKAGE_NAME = svg_viewer

# Help
help:
	@echo "SVG Viewer - Makefile"
	@echo "======================"
	@echo "Available targets:"
	@echo "  setup-env   Set up development environment"
	@echo "  install     Install production dependencies"
	@echo "  install-dev Install development dependencies"
	@echo "  test        Run tests with coverage"
	@echo "  lint        Run code linters (flake8)"
	@echo "  format      Format code (black, isort)"
	@echo "  type-check  Run type checking (mypy)"
	@echo "  check       Run all checks (lint, format, type-check, test)"
	@echo "  build       Build the package"
	@echo "  publish     Publish to PyPI"
	@echo "  run         Run the SVG viewer"
	@echo "  clean       Clean build artifacts"

# Setup and Installation
setup-env:
	@echo "Setting up development environment..."
	sudo dnf install -y python3-qt5 python3-qt5-qtwebengine python3-qt5-qtwebkit python3-gobject || \
	sudo apt-get install -y python3-pyqt5 python3-pyqt5.qtwebengine python3-pyqt5.qtwebkit python3-gi

install:
	@echo "Installing production dependencies..."
	poetry install --only main --no-root

install-dev:
	@echo "Installing development dependencies..."
	poetry install --with dev

# Testing
test:
	@echo "Running tests..."
	poetry run pytest -v --cov=$(PACKAGE_NAME) --cov-report=term-missing --cov-report=html
	@echo "\nCoverage report generated. Open htmlcov/index.html in your browser."

# Linting
lint:
	@echo "Running flake8..."
	poetry run flake8 $(PACKAGE_NAME) tests

# Formatting
format:
	@echo "Running black..."
	poetry run black $(PACKAGE_NAME) tests
	@echo "Running isort..."
	poetry run isort $(PACKAGE_NAME) tests

# Run the application
run:
	@echo "Starting SVG Viewer..."
	poetry run python -m $(PACKAGE_NAME) img.svg

# Type checking
type-check:
	@echo "Running mypy..."
	poetry run mypy $(PACKAGE_NAME) tests

# Run all checks
check: lint format type-check test
	@echo "All checks completed!"

# Build and publish
build:
	@echo "Building package..."
	poetry build

publish: build
	@echo "Publishing to PyPI..."
	poetry publish

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/
	@echo "Clean complete!"
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +

# Default target
.DEFAULT_GOAL := help
