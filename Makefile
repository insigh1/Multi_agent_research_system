.PHONY: help setup install clean test web cli format lint check dev-install

# Default target
help:
	@echo "🔬 Multi-Agent Research System - UV Package Manager"
	@echo "=================================================="
	@echo ""
	@echo "Available commands:"
	@echo "  setup      - Initial project setup with uv"
	@echo "  install    - Install dependencies"
	@echo "  dev-install - Install with development dependencies"
	@echo "  web        - Start web UI"
	@echo "  cli        - Start CLI (requires QUERY='your question')"
	@echo "  test       - Run tests"
	@echo "  format     - Format code with black and isort"
	@echo "  lint       - Run linting checks"
	@echo "  check      - Run all checks (format, lint, test)"
	@echo "  clean      - Clean up build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make setup"
	@echo "  make web"
	@echo "  make cli QUERY='Latest AI developments'"
	@echo "  make test"

# Setup project
setup:
	@echo "🚀 Setting up Multi-Agent Research System..."
	@chmod +x setup.sh run-web.sh run-cli.sh test.sh
	@./setup.sh

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@uv pip install -e .

# Install with development dependencies
dev-install:
	@echo "📦 Installing with development dependencies..."
	@uv pip install -e ".[dev]"

# Start web UI
web:
	@echo "🌐 Starting web UI..."
	@chmod +x run-web.sh
	@./run-web.sh

# Start CLI
cli:
	@if [ -z "$(QUERY)" ]; then \
		echo "❌ Please provide a query: make cli QUERY='your question'"; \
		exit 1; \
	fi
	@echo "🔍 Running CLI research..."
	@chmod +x run-cli.sh
	@./run-cli.sh "$(QUERY)"

# Run tests
test:
	@echo "🧪 Running tests..."
	@chmod +x test.sh
	@./test.sh

# Format code
format:
	@echo "🎨 Formatting code..."
	@uv run black .
	@uv run isort .

# Run linting
lint:
	@echo "🔍 Running linting..."
	@uv run flake8 .
	@uv run mypy . --ignore-missing-imports

# Run all checks
check: format lint test
	@echo "✅ All checks completed!"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .mypy_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

# Quick development setup
dev: setup dev-install
	@echo "🎉 Development environment ready!"

# Health check
health:
	@echo "🏥 Running health check..."
	@uv run python main.py health 