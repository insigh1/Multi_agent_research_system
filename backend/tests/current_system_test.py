#!/usr/bin/env python3
"""
Current System Test for Multi-Agent Research System
==================================================

Tests the current UV-based system with:
- Core research functionality
- PDF generation with WeasyPrint
- Web UI endpoints
- CLI functionality
"""

import asyncio
import json
import time
import os
import tempfile
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

def test_weasyprint():
    """Test WeasyPrint PDF generation"""
    try:
        from weasyprint import HTML
        
        html_content = """
        <html>
        <head><title>Test PDF</title></head>
        <body>
            <h1>Multi-Agent Research System</h1>
            <p>PDF generation is working correctly!</p>
        </body>
        </html>
        """
        
        # Generate PDF in memory
        html_doc = HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()
        
        return {
            "success": True, 
            "message": f"PDF generated successfully ({len(pdf_bytes)} bytes)"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_core_imports():
    """Test that all core modules import correctly"""
    try:
        from main import EnhancedResearchSystem, cli
        from config import Settings
        from enhanced_research_system import DatabaseManager
        
        return {
            "success": True,
            "message": "All core modules imported successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_settings_validation():
    """Test settings and configuration"""
    try:
        from config import Settings
        
        # Test with environment variables
        settings = Settings()
        
        return {
            "success": True,
            "message": f"Settings loaded: {len(settings.model_dump())} configuration items"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_research_system():
    """Test the core research system"""
    try:
        from main import EnhancedResearchSystem
        from config import Settings
        
        settings = Settings()
        
        async with EnhancedResearchSystem(settings) as system:
            # Test health check
            health = await system.health_check()
            
            return {
                "success": True,
                "message": f"Research system healthy: {health['status']}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_web_ui_imports():
    """Test that web UI can be imported"""
    try:
        from web_ui import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        return {
            "success": response.status_code == 200,
            "message": f"Web UI health check: {response.status_code}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_database_manager():
    """Test database functionality"""
    try:
        from enhanced_research_system import DatabaseManager
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            db = DatabaseManager(db_path)
            db.initialize()
            
            # Test session creation
            session_id = "test-session-123"
            query = "test query"
            status = "completed"
            data = {"test": "data"}
            
            db.save_session(session_id, query, status, data)
            loaded_data = db.load_session(session_id)
            
            success = loaded_data is not None and loaded_data["data"]["test"] == "data"
            
            return {
                "success": success,
                "message": "Database operations working correctly"
            }
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)
                
    except Exception as e:
        return {"success": False, "error": str(e)}

async def run_all_tests():
    """Run all tests and display results"""
    
    console.print(Panel.fit(
        "🧪 Multi-Agent Research System - Current System Test",
        style="bold blue"
    ))
    
    tests = [
        ("Core Module Imports", test_core_imports),
        ("Settings Validation", test_settings_validation),
        ("WeasyPrint PDF Generation", test_weasyprint),
        ("Database Manager", test_database_manager),
        ("Web UI Imports", test_web_ui_imports),
        ("Research System Health", test_research_system),
    ]
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for test_name, test_func in tests:
            task = progress.add_task(f"Running {test_name}...", total=None)
            
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                results.append((test_name, result))
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                progress.update(task, description=f"{status} {test_name}")
                
            except Exception as e:
                result = {"success": False, "error": str(e)}
                results.append((test_name, result))
                progress.update(task, description=f"❌ FAIL {test_name}")
            
            progress.remove_task(task)
    
    # Display results table
    table = Table(title="Test Results Summary")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message", style="dim")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        if result["success"]:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        
        message = result.get("message", result.get("error", ""))
        table.add_row(test_name, status, message)
    
    console.print(table)
    
    # Summary
    console.print(f"\n📊 Summary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        console.print("🎉 All tests passed! System is working correctly.", style="bold green")
    else:
        console.print(f"⚠️  {total-passed} tests failed. Check the errors above.", style="bold yellow")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 