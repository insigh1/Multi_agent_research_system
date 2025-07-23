#!/bin/bash

# Script to run tests for Multi-Agent Research System

set -e

echo "🧪 Running Multi-Agent Research System Tests"
echo "============================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Install test dependencies if not already installed
echo "📦 Installing test dependencies..."
uv pip install pytest pytest-asyncio pytest-mock httpx

# Run tests
echo "🔍 Running tests..."

if [ -f "tests/simple_test.py" ]; then
    echo "Running simple test..."
    uv run python tests/simple_test.py
fi

if [ -f "tests/full_system_test.py" ]; then
    echo "Running full system test..."
    uv run python tests/full_system_test.py
fi

# Run pytest if available
if command -v pytest &> /dev/null; then
    echo "Running pytest..."
    uv run pytest tests/ -v
fi

echo "✅ Tests completed!" 