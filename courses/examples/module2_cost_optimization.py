#!/usr/bin/env python3
"""
🎓 Module 2: Basic Cost Optimization & Budget Awareness
=====================================================

This module introduces basic cost tracking and budget awareness concepts.
We'll learn how to track API costs and implement simple budget controls.

Key Learning Objectives:
1. Understanding token-based pricing
2. Basic cost calculation
3. Simple budget tracking
4. Cost-aware API calls

Note: Advanced model selection strategies are covered in later modules.
"""

import asyncio
import aiohttp
import os
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass

# Simple pricing for basic models (Module 2 level)
BASIC_MODEL_COSTS = {
    "llama-v3p1-8b-instruct": {"input": 0.20, "output": 0.20},    # Fast, cheap
    "llama-v3p3-70b-instruct": {"input": 0.90, "output": 0.90},   # Better quality, more expensive
}

class SimpleBudgetManager:
    """
    Simple budget manager for tracking API costs
    """
    
    def __init__(self, budget_limit: float = 1.0):
        self.budget_limit = budget_limit
        self.current_spend = 0.0
        self.api_calls = 0
        self.api_key = os.getenv("FIREWORKS_API_KEY")
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable is required")
    
    def calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        costs = BASIC_MODEL_COSTS.get(model_name, {"input": 0.5, "output": 0.5})
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return input_cost + output_cost
    
    def can_afford(self, estimated_cost: float) -> bool:
        """Check if we can afford an operation"""
        return (self.current_spend + estimated_cost) <= self.budget_limit
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget"""
        return max(0, self.budget_limit - self.current_spend)
    
    async def make_budget_aware_call(self, prompt: str, model: str = "llama-v3p1-8b-instruct") -> Dict:
        """
        Make an API call with basic budget awareness
        """
        # Simple cost estimation (basic approach for Module 2)
        estimated_tokens = len(prompt.split()) * 2
        estimated_cost = self.calculate_cost(model, estimated_tokens // 2, estimated_tokens // 2)
        
        print(f"\n💰 Budget Check:")
        print(f"   Model: {model}")
        print(f"   Estimated cost: ${estimated_cost:.4f}")
        print(f"   Budget remaining: ${self.get_remaining_budget():.4f}")
        
        if not self.can_afford(estimated_cost):
            # Simple fallback: switch to cheaper model
            if model != "llama-v3p1-8b-instruct":
                print(f"⚠️  Switching to cheaper model: llama-v3p1-8b-instruct")
                model = "llama-v3p1-8b-instruct"
                estimated_cost = self.calculate_cost(model, estimated_tokens // 2, estimated_tokens // 2)
                
                if not self.can_afford(estimated_cost):
                    raise Exception(f"Budget exceeded! Need ${estimated_cost:.4f}, have ${self.get_remaining_budget():.4f}")
            else:
                raise Exception(f"Budget exceeded! Need ${estimated_cost:.4f}, have ${self.get_remaining_budget():.4f}")
        
        # Make the API call
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": f"accounts/fireworks/models/{model}",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,  # Keep it simple for Module 2
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API call failed: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # Calculate actual cost
                    usage = result.get("usage", {})
                    actual_cost = self.calculate_cost(
                        model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0)
                    )
                    
                    # Update tracking
                    self.current_spend += actual_cost
                    self.api_calls += 1
                    
                    print(f"✅ API call successful!")
                    print(f"   Actual cost: ${actual_cost:.4f}")
                    print(f"   Total spent: ${self.current_spend:.4f} / ${self.budget_limit:.2f}")
                    print(f"   Budget utilization: {(self.current_spend/self.budget_limit)*100:.1f}%")
                    
                    return {
                        "content": result["choices"][0]["message"]["content"],
                        "model_used": model,
                        "cost": actual_cost,
                        "usage": usage
                    }
                    
            except Exception as e:
                print(f"❌ API Error: {str(e)}")
                raise
    
    def get_usage_summary(self) -> Dict:
        """Get simple usage summary"""
        return {
            "total_budget": self.budget_limit,
            "total_spent": self.current_spend,
            "remaining_budget": self.get_remaining_budget(),
            "utilization_percent": (self.current_spend / self.budget_limit) * 100,
            "api_calls_made": self.api_calls,
            "average_cost_per_call": self.current_spend / max(1, self.api_calls)
        }

async def demonstrate_basic_cost_tracking():
    """
    Demonstrate basic cost tracking concepts
    """
    print("🎓 Module 2: Basic Cost Optimization & Budget Awareness")
    print("=" * 60)
    print("Learning basic cost tracking and budget awareness...")
    
    # Create budget manager with small budget for demonstration
    budget_manager = SimpleBudgetManager(budget_limit=0.05)
    
    # Test scenarios
    test_scenarios = [
        ("Cheap Model Test", "Explain AI in one sentence", "llama-v3p1-8b-instruct"),
        ("Expensive Model Test", "Explain AI in one sentence", "llama-v3p3-70b-instruct"),
        ("Another Call", "What is machine learning?", "llama-v3p1-8b-instruct"),
    ]
    
    for scenario_name, prompt, model in test_scenarios:
        print(f"\n🧪 {scenario_name}")
        print("-" * 40)
        
        try:
            result = await budget_manager.make_budget_aware_call(prompt, model)
            print(f"📝 Response: {result['content'][:100]}...")
            
        except Exception as e:
            print(f"❌ {scenario_name} failed: {e}")
        
        # Show current status
        summary = budget_manager.get_usage_summary()
        print(f"📊 Current Status: {summary['utilization_percent']:.1f}% budget used")
    
    # Final summary
    print(f"\n📊 Final Budget Summary:")
    print("-" * 30)
    summary = budget_manager.get_usage_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            if 'cost' in key or 'budget' in key or 'spent' in key:
                print(f"   {key}: ${value:.4f}")
            else:
                print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

async def demonstrate_cost_comparison():
    """
    Show cost differences between models
    """
    print(f"\n🔍 Model Cost Comparison")
    print("-" * 30)
    
    sample_usage = {"input_tokens": 100, "output_tokens": 50}
    
    for model, costs in BASIC_MODEL_COSTS.items():
        cost = (sample_usage["input_tokens"] / 1_000_000) * costs["input"] + \
               (sample_usage["output_tokens"] / 1_000_000) * costs["output"]
        
        print(f"💰 {model}:")
        print(f"   Cost for 100 input + 50 output tokens: ${cost:.6f}")
        print(f"   Input cost: ${costs['input']:.2f}/1M tokens")
        print(f"   Output cost: ${costs['output']:.2f}/1M tokens")

async def main():
    """Main demonstration function"""
    try:
        await demonstrate_cost_comparison()
        await demonstrate_basic_cost_tracking()
        
        print(f"\n🎯 Key Takeaways:")
        print("1. API costs are based on token usage")
        print("2. Different models have different costs")
        print("3. Budget tracking prevents overspending") 
        print("4. Simple fallbacks help stay within budget")
        print("5. Monitor usage to optimize costs")
        print("\n✅ Module 2 complete! Next: Multi-Agent Pipeline")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        print("Make sure FIREWORKS_API_KEY is set in your environment")

if __name__ == "__main__":
    asyncio.run(main()) 