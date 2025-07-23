#!/usr/bin/env python3
"""
Startup script for Multi-Agent Research System Web UI
=====================================================

Simple script to launch the web interface with proper configuration.
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Launch the web UI"""
    try:
        # Import run_web_ui with fallback handling
        run_web_ui = None
        
        # First try: assume we're being called as a module (from root entry point)
        try:
            from backend.web_ui import run_web_ui
        except (ImportError, ModuleNotFoundError):
            pass
        
        # Second try: assume we're in the backend directory
        if run_web_ui is None:
            try:
                from web_ui import run_web_ui
            except (ImportError, ModuleNotFoundError):
                pass
        
        # Third try: relative import (when imported as package)
        if run_web_ui is None:
            try:
                from .web_ui import run_web_ui
            except (ImportError, ModuleNotFoundError):
                pass
        
        if run_web_ui is None:
            raise ImportError("Could not import web_ui module from any location")
        
        print("""
🚀 Multi-Agent Research System Web UI
=====================================

Starting the web interface...

Features:
✅ Real-time progress tracking with WebSockets
✅ Interactive research configuration
✅ Beautiful results visualization  
✅ Multiple export formats (PDF, HTML, JSON)
✅ Session management and history
✅ Intelligent parallel processing visualization

""")
        
        # Check for environment file (look in parent directory)
        env_file = current_dir.parent / ".env"
        if not env_file.exists():
            print("⚠️  Warning: .env file not found. Using default settings.")
            print("   Create a .env file based on env.example for custom configuration.")
            print()
        
        # Default configuration
        host = os.getenv("WEB_UI_HOST", "0.0.0.0")
        port = int(os.getenv("WEB_UI_PORT", "8080"))
        reload = os.getenv("WEB_UI_RELOAD", "false").lower() == "true"
        
        print(f"🌐 Server will start at: http://{host}:{port}")
        print(f"🔄 Auto-reload: {'Enabled' if reload else 'Disabled'}")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the web UI
        run_web_ui(host=host, port=port, reload=reload)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n💡 Please install the required dependencies:")
        print("   pip install -e .")
        print("   or run: ./setup.sh")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Web UI stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting web UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 