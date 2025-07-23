#!/bin/bash

# Quick script to run the Multi-Agent Research System CLI

set -e

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy env.example to .env and configure your API keys."
    exit 1
fi

# Check if query is provided
if [ $# -eq 0 ]; then
    echo "🔬 Multi-Agent Research System CLI"
    echo "Usage: $0 'your research question'"
    echo ""
    echo "Examples:"
    echo "  $0 'Latest developments in AI'"
    echo "  $0 'Climate change impacts on agriculture'"
    echo "  $0 'Quantum computing applications'"
    exit 1
fi

echo "🔍 Researching: $1"
echo "======================"

# Set environment variables for WeasyPrint on macOS
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# Use UV to run with proper environment
uv run python main.py research "$1" 