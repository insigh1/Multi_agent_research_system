"""
Vercel serverless function entry point for the Multi-Agent Research System
"""
import sys
import os
from pathlib import Path

# Add the current directory and backend directory to Python path for imports
current_dir = Path(__file__).parent
backend_dir = current_dir.parent / 'backend'
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(backend_dir))

# Import the FastAPI app from web_ui
try:
    from web_ui import app
except ImportError:
    # Alternative import strategies
    try:
        import web_ui
        app = web_ui.app
    except ImportError:
        # Last resort - try with absolute path
        sys.path.append(str(backend_dir.absolute()))
        from web_ui import app

# Export the FastAPI app for Vercel (no handler function needed)
app = app

# For local development, run:
# uvicorn backend.web_ui:app --host 0.0.0.0 --port 8000 --reload 