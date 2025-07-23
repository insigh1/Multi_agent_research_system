#!/bin/bash

# Quick script to run the Multi-Agent Research System Web UI

set -e

echo "🚀 Starting Multi-Agent Research System Web UI..."

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

# Set environment variables for WeasyPrint on macOS
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# Use UV to run with proper environment
uv run python start_web_ui.py

echo "🎉 Web UI started at http://localhost:8080" 