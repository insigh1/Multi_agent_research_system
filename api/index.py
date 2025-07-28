"""
Vercel serverless function entry point for the Multi-Agent Research System
"""
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Import the FastAPI app from web_ui
try:
    from web_ui import app
except ImportError:
    # Alternative import path
    sys.path.append(str(backend_dir))
    from web_ui import app

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 