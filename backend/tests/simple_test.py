#!/usr/bin/env python3
"""
Simple Test Script for Enhanced Multi-Agent Research System
==========================================================

This script demonstrates the enhanced system without PDF dependencies.
"""

import asyncio
import json
import time
import os
from pathlib import Path
import sys

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import only the core components we need
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import structlog
import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Simplified settings without PDF dependencies
class Settings(BaseSettings):
    """Application settings with validation"""
    # API Keys
    fireworks_api_key: str = Field(..., min_length=10)
    brave_api_key: str = Field(None, min_length=10)
    
    # API settings
    fireworks_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    max_tokens: int = Field(800, ge=100, le=4000)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    
    # Rate limiting and performance
    max_concurrent_requests: int = Field(5, ge=1, le=20)
    requests_per_minute: int = Field(60, ge=10, le=300)
    api_timeout: int = Field(30, ge=10, le=120)
    brave_timeout: int = Field(15, ge=5, le=60)
    
    # Caching
    redis_url: str = Field("redis://localhost:6379", min_length=1)
    cache_ttl: int = Field(1800, ge=300, le=86400)  # 30 minutes default
    
    # Database
    db_path: str = Field("research_sessions.db", min_length=1)
    
    # Monitoring
    metrics_port: int = Field(8000, ge=1024, le=65535)
    log_level: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Input validation models
class QueryRequest(BaseModel):
    """Validated research query request"""
    query: str = Field(..., min_length=3, max_length=1000)
    max_sub_questions: int = Field(5, ge=1, le=10)
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Query must be at least 3 characters long')
        # Basic content filtering
        forbidden_terms = ['hack', 'exploit', 'illegal']
        if any(term in v.lower() for term in forbidden_terms):
            raise ValueError('Query contains forbidden terms')
        return v

class SimpleResearchSystem:
    """Simplified research system for testing"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
    
    async def test_api_connection(self):
        """Test API connection"""
        headers = {
            "Authorization": f"Bearer {self.settings.fireworks_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.settings.fireworks_model,
            "messages": [{"role": "user", "content": "Hello, this is a test. Please respond with 'API connection successful'."}],
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        return {"success": True, "response": content}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def conduct_simple_research(self, request: QueryRequest):
        """Conduct simplified research"""
        console.print(f"🔍 Processing query: '{request.query}'")
        
        # Generate research plan
        plan_prompt = f"""You are a research planning specialist. Create a research plan for: "{request.query}"

Generate exactly {request.max_sub_questions} focused sub-questions that provide comprehensive coverage.

Respond with ONLY a JSON object in this format:
{{
    "research_strategy": "brief strategy description",
    "sub_questions": [
        "specific question 1",
        "specific question 2",
        "specific question 3"
    ]
}}"""
        
        headers = {
            "Authorization": f"Bearer {self.settings.fireworks_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.settings.fireworks_model,
            "messages": [{"role": "user", "content": plan_prompt}],
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=60) as response:
                    response.raise_for_status()
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        # Extract JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            plan_data = json.loads(json_match.group())
                        else:
                            raise ValueError("No JSON found in response")
                        
                        return {
                            "success": True,
                            "original_query": request.query,
                            "research_strategy": plan_data.get("research_strategy", "AI-assisted research"),
                            "sub_questions": plan_data.get("sub_questions", []),
                            "total_questions": len(plan_data.get("sub_questions", [])),
                            "processing_time": 0.0
                        }
                    except (json.JSONDecodeError, ValueError) as e:
                        # Fallback plan
                        return {
                            "success": True,
                            "original_query": request.query,
                            "research_strategy": "Fallback comprehensive research",
                            "sub_questions": [
                                f"What is the current state of {request.query}?",
                                f"What are the key developments in {request.query}?",
                                f"What are the main challenges related to {request.query}?",
                                f"What are the practical applications of {request.query}?",
                                f"What are the future trends for {request.query}?"
                            ][:request.max_sub_questions],
                            "total_questions": min(5, request.max_sub_questions),
                            "processing_time": 0.0,
                            "note": f"Used fallback plan due to parsing error: {str(e)}"
                        }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_query": request.query
            }

async def main():
    """Main test function"""
    console.print(Panel("🧪 Enhanced Research System - Simple Test", style="bold blue"))
    
    # Check for API keys
    if not os.getenv('FIREWORKS_API_KEY'):
        console.print("❌ FIREWORKS_API_KEY not found in environment", style="red")
        console.print("💡 Make sure to set your API key: export FIREWORKS_API_KEY=your_key", style="yellow")
        return
    
    try:
        # Initialize settings
        settings = Settings()
        console.print("✅ Settings loaded successfully", style="green")
        
        # Initialize system
        system = SimpleResearchSystem(settings)
        console.print("✅ Research system initialized", style="green")
        
        # Test API connection
        console.print("\n🔌 Testing API connection...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Connecting to Fireworks AI...", total=None)
            connection_result = await system.test_api_connection()
            
            if connection_result["success"]:
                progress.update(task, description="✅ API connection successful")
                console.print(f"📝 API Response: {connection_result['response']}", style="green")
            else:
                progress.update(task, description="❌ API connection failed")
                console.print(f"❌ Error: {connection_result['error']}", style="red")
                return
        
        # Test input validation
        console.print("\n🔒 Testing input validation...")
        test_cases = [
            ("What are the latest developments in AI agents?", True),
            ("", False),
            ("hack the system", False),
        ]
        
        for query, should_pass in test_cases:
            try:
                request = QueryRequest(query=query)
                if should_pass:
                    console.print(f"✅ Valid query accepted: '{query[:50]}...'", style="green")
                else:
                    console.print(f"❌ Invalid query should have been rejected: '{query}'", style="red")
            except Exception as e:
                if not should_pass:
                    console.print(f"✅ Invalid query correctly rejected: '{query}' ({type(e).__name__})", style="green")
                else:
                    console.print(f"❌ Valid query incorrectly rejected: '{query}' ({str(e)})", style="red")
        
        # Test research functionality
        console.print("\n🔍 Testing research functionality...")
        test_query = "What are the latest developments in AI agents and multi-agent systems?"
        
        try:
            request = QueryRequest(query=test_query, max_sub_questions=3)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Conducting research...", total=None)
                
                start_time = time.time()
                result = await system.conduct_simple_research(request)
                duration = time.time() - start_time
                
                progress.update(task, description="✅ Research completed")
            
            if result["success"]:
                console.print(f"\n📊 Research Results (completed in {duration:.2f}s):")
                console.print(Panel(f"Query: {result['original_query']}", style="cyan"))
                console.print(f"📋 Strategy: {result['research_strategy']}")
                console.print(f"🔢 Generated {result['total_questions']} sub-questions:")
                
                for i, question in enumerate(result['sub_questions'], 1):
                    console.print(f"  {i}. {question}")
                
                if 'note' in result:
                    console.print(f"\n💡 Note: {result['note']}", style="yellow")
                
                console.print("\n🎉 Research system test completed successfully!", style="bold green")
            else:
                console.print(f"❌ Research failed: {result['error']}", style="red")
        
        except Exception as e:
            console.print(f"❌ Research test failed: {str(e)}", style="red")
            import traceback
            console.print(traceback.format_exc(), style="dim red")
    
    except Exception as e:
        console.print(f"❌ Test failed: {str(e)}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="dim red")

if __name__ == "__main__":
    asyncio.run(main()) 