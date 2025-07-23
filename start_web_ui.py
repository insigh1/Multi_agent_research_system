#!/usr/bin/env python3
"""
Multi-Agent Research System - Web UI Entry Point
Copyright (c) 2025 David Lee (@insigh1) - Fireworks AI
MIT License - see LICENSE file for details

This is the web UI entry point for the Multi-Agent Research System.
It imports and runs the backend web UI.
"""

import sys
from pathlib import Path

# Add the current directory to Python path to enable backend imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and run the web UI from backend
try:
    from backend.start_web_ui import main
except ImportError:
    # Fallback: Add backend to path and import directly
    backend_path = current_dir / "backend"
    sys.path.insert(0, str(backend_path))
    from start_web_ui import main

if __name__ == "__main__":
    main() 