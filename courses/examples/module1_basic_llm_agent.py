#!/usr/bin/env python3
"""
Module 1 Example: Basic LLM Agent with Fireworks AI

This script demonstrates:
- Basic LLM agent implementation
- Fireworks AI integration
- Model configuration
- Simple cost tracking
- Error handling

Run: python module1_basic_llm_agent.py
"""

import asyncio
import os
import time
import json
from dataclasses import dataclass
from typing import Dict, Optional
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AgentConfig:
    """Configuration for an LLM agent"""
    name: str
    role: str
    model: str
    max_tokens: int
    temperature: float
    description: str

class BasicLLMAgent:
    """
    Basic LLM Agent demonstrating core concepts from the course
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.api_key = os.getenv("FIREWORKS_API_KEY")
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.total_cost = 0.0
        self.call_count = 0
        
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable not set")
        
        print(f"🤖 Initialized {self.config.name}")
        print(f"   Role: {self.config.role}")
        print(f"   Model: {self.config.model}")
        print(f"   Description: {self.config.description}")
    
    async def call_llm(self, prompt: str) -> Dict:
        """
        Make a call to Fireworks AI API
        """
        print(f"\n📡 Making API call to {self.config.model}...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API call failed: {response.status} - {error_text}")
                    
                    result = await response.json()
                    end_time = time.time()
                    
                    # Extract response and token usage
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    
                    # Simple cost calculation (using approximate costs)
                    cost = self._calculate_cost(usage)
                    self.total_cost += cost
                    self.call_count += 1
                    
                    print(f"✅ API call successful!")
                    print(f"   Duration: {end_time - start_time:.2f}s")
                    print(f"   Tokens used: {usage.get('total_tokens', 0)}")
                    print(f"   Cost: ${cost:.4f}")
                    print(f"   Total cost: ${self.total_cost:.4f}")
                    
                    return {
                        "content": content,
                        "usage": usage,
                        "cost": cost,
                        "duration": end_time - start_time
                    }
                    
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                raise
    
    def _calculate_cost(self, usage: Dict) -> float:
        """
        Simple cost calculation based on token usage
        Note: These are approximate costs - see pricing.py for exact costs
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Approximate costs (per 1M tokens)
        if "8b" in self.config.model:
            # Budget models
            cost_per_1m = 0.20
        elif "70b" in self.config.model:
            # Performance models  
            cost_per_1m = 0.90
        else:
            # Default estimate
            cost_per_1m = 0.50
        
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1_000_000) * cost_per_1m
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            "agent_name": self.config.name,
            "total_calls": self.call_count,
            "total_cost": self.total_cost,
            "average_cost_per_call": self.total_cost / max(1, self.call_count)
        }

async def main():
    """
    Demonstration of basic LLM agent concepts
    """
    print("🎓 Module 1: Basic LLM Agent with Fireworks AI")
    print("=" * 50)
    
    # Define different agent configurations
    agent_configs = [
        AgentConfig(
            name="Research Planner",
            role="Strategic research planning",
            model="accounts/fireworks/models/llama-v3p3-70b-instruct",
            max_tokens=800,
            temperature=0.2,
            description="Reasoning-optimized model for planning"
        ),
        AgentConfig(
            name="Content Summarizer", 
            role="Content summarization",
            model="accounts/fireworks/models/llama-v3p1-8b-instruct",
            max_tokens=400,
            temperature=0.3,
            description="Fast, efficient model for summarization"
        )
    ]
    
    # Test different agents
    for config in agent_configs:
        print(f"\n🧪 Testing {config.name}")
        print("-" * 30)
        
        agent = BasicLLMAgent(config)
        
        # Create role-specific prompt
        if "planner" in config.name.lower():
            prompt = """Create a brief research plan for the topic: "Impact of AI on healthcare"
            
Include:
1. 3 key research questions
2. Research strategy
3. Expected challenges

Keep it concise but comprehensive."""
        else:
            prompt = """Summarize the key benefits of AI in healthcare in 3 bullet points. 
            
Focus on practical applications and real-world impact."""
        
        try:
            result = await agent.call_llm(prompt)
            
            print(f"\n📝 {config.name} Response:")
            print("-" * 40)
            print(result["content"])
            print("-" * 40)
            
            # Show statistics
            stats = agent.get_stats()
            print(f"\n📊 Agent Statistics:")
            for key, value in stats.items():
                if "cost" in key:
                    print(f"   {key}: ${value:.4f}")
                else:
                    print(f"   {key}: {value}")
                    
        except Exception as e:
            print(f"❌ Failed to test {config.name}: {e}")
    
    print(f"\n🎯 Key Takeaways:")
    print("1. Different models have different strengths and costs")
    print("2. Temperature affects response creativity vs consistency")
    print("3. Token usage directly impacts cost")
    print("4. Agent specialization improves performance")
    print("\n✅ Module 1 complete! Try running with different models or prompts.")

if __name__ == "__main__":
    asyncio.run(main()) 