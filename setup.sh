#!/bin/bash

# Multi-Agent Research System Setup Script
# This script sets up the project using uv for fast dependency management

set -e  # Exit on any error

echo "🔬 Multi-Agent Research System Setup"
echo "===================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ uv installed successfully"
fi

echo "📦 Setting up virtual environment with uv..."

# Create virtual environment and install dependencies
uv venv --python 3.11
echo "✅ Virtual environment created"

# Install dependencies from pyproject.toml
uv pip install -e .
echo "✅ Dependencies installed from pyproject.toml"

# Copy environment template if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. Please edit it with your API keys."
    echo ""
    echo "Required API keys:"
    echo "  - FIREWORKS_API_KEY: Get from https://fireworks.ai"
    echo "  - BRAVE_API_KEY: Get from https://brave.com/search/api/"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p exports

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: source .venv/bin/activate"
echo "3. Start web UI: uv run python start_web_ui.py"
echo "4. Or use CLI: uv run python main.py research 'your question'"
echo ""
echo "Quick commands:"
echo "  ./run-web.sh    - Start web interface"
echo "  ./run-cli.sh    - Start CLI interface"
echo "  ./test.sh       - Run tests"
echo "" 