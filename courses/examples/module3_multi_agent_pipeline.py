"""
🎓 Module 3: Basic Multi-Agent Pipeline
====================================

This module introduces the concept of multiple AI agents working together.
We'll learn how different agents can specialize in different tasks.

Key Learning Objectives:
1. Understanding agent specialization
2. Basic agent coordination
3. Simple pipeline flow
4. Cost tracking across agents

Note: Advanced JSON parsing and complex coordination comes in later modules.
"""

import asyncio
import aiohttp
import os
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass

@dataclass
class SimpleResearchResult:
    """Simple container for research results"""
    query: str
    research_plan: str
    search_results: str
    analysis: str
    total_cost: float

class AgentRole(Enum):
    RESEARCH_PLANNER = "research_planner"
    WEB_SEARCHER = "web_searcher"
    SUMMARIZER = "summarizer"

class SimpleAgent:
    """
    Simple agent that handles API calls and cost tracking
    """
    
    def __init__(self, role: AgentRole, model: str = "llama-v3p1-8b-instruct"):
        self.role = role
        self.model = model
        self.api_key = os.getenv("FIREWORKS_API_KEY")
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        
        # Simple cost tracking
        self.total_cost = 0.0
        self.call_count = 0
        
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable is required")
        
        print(f"🤖 Agent {self.role.value} initialized with model {self.model}")
    
    async def process(self, prompt: str, context: str = "") -> Dict:
        """
        Process a request and return simple text response
        """
        # Add context if provided
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": f"accounts/fireworks/models/{self.model}",
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {"content": f"Error: {response.status}", "cost": 0.0}
                    
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    
                    # Simple cost tracking
                    cost = self._estimate_cost(usage)
                    self.total_cost += cost
                    self.call_count += 1
                    
                    return {"content": content, "usage": usage, "cost": cost}
                    
            except Exception as e:
                print(f"❌ {self.role.value} API error: {e}")
                return {"content": f"Error: {str(e)}", "cost": 0.0}
    
    def _estimate_cost(self, usage: Dict) -> float:
        """Estimate cost based on model and token usage"""
        total_tokens = usage.get("total_tokens", 0)
        
        # Simple cost estimation
        if "8b" in self.model:
            cost_per_1m = 0.20
        elif "70b" in self.model:
            cost_per_1m = 0.90
        else:
            cost_per_1m = 0.50
        
        return (total_tokens / 1_000_000) * cost_per_1m

class ResearchPlannerAgent(SimpleAgent):
    """Agent specialized in creating research plans"""
    
    def __init__(self):
        # Use reasoning-optimized model for planning
        super().__init__(AgentRole.RESEARCH_PLANNER, "llama-v3p3-70b-instruct")
    
    async def create_research_plan(self, query: str) -> str:
        """Create a simple research plan"""
        print(f"\n🧠 Research Planner: Creating plan for '{query}'...")
        
        prompt = f"""As a research planning expert, create a simple research plan for: "{query}"

Please provide:
1. A brief research strategy (2-3 sentences)
2. 2-3 specific questions that would help answer this query
3. What type of sources would be most helpful

Keep the response clear and practical."""

        result = await self.process(prompt)
        
        if "Error:" in result["content"]:
            print(f"❌ Failed to create research plan: {result['content']}")
            return f"Simple plan: Research {query} by finding relevant sources and analyzing key information."
        else:
            print(f"✅ Research plan created")
            return result["content"]

class WebSearchAgent(SimpleAgent):
    """Agent specialized in web information gathering"""
    
    def __init__(self):
        # Use fast, efficient model for web search
        super().__init__(AgentRole.WEB_SEARCHER, "llama-v3p1-8b-instruct")
    
    async def simulate_web_search(self, query: str) -> str:
        """
        Simulate web search results (in real implementation, this would use APIs)
        """
        print(f"\n🔍 Web Searcher: Searching for '{query}'...")
        
        prompt = f"""You are simulating a web search for: "{query}"

Create 2-3 realistic search results that would help answer this query. For each result:
- Provide a brief title
- Give 2-3 sentences of relevant information
- Make it realistic and helpful

Format as simple text, not JSON."""
        
        result = await self.process(prompt)
        
        if "Error:" in result["content"]:
            print(f"❌ Web search failed: {result['content']}")
            return f"No search results found for: {query}"
        else:
            print(f"✅ Found search results")
            return result["content"]

class SummarizerAgent(SimpleAgent):
    """Agent specialized in summarizing and analyzing information"""
    
    def __init__(self):
        # Use synthesis-optimized model
        super().__init__(AgentRole.SUMMARIZER, "llama-v3p3-70b-instruct")
    
    async def analyze_information(self, query: str, research_plan: str, search_results: str) -> str:
        """Analyze and summarize the gathered information"""
        print(f"\n📊 Summarizer: Analyzing information...")
        
        prompt = f"""Based on the research plan and search results below, provide a clear analysis for the query: "{query}"

RESEARCH PLAN:
{research_plan}

SEARCH RESULTS:
{search_results}

Please provide:
1. Key findings (2-3 main points)
2. A brief conclusion
3. Any important insights

Keep it concise and practical."""
        
        context = f"Original query: {query}"
        result = await self.process(prompt, context)
        
        if "Error:" in result["content"]:
            print(f"❌ Analysis failed: {result['content']}")
            return f"Unable to analyze information for: {query}"
        else:
            print(f"✅ Analysis completed")
            return result["content"]

class SimpleMultiAgentSystem:
    """
    Simple multi-agent research system demonstrating basic coordination
    """
    
    def __init__(self):
        self.research_planner = ResearchPlannerAgent()
        self.web_searcher = WebSearchAgent()
        self.summarizer = SummarizerAgent()
        
        print(f"\n🎯 Simple Multi-Agent System initialized")
        print("   Agents: Research Planner, Web Searcher, Summarizer")
    
    async def conduct_simple_research(self, query: str) -> SimpleResearchResult:
        """
        Conduct research using the simple multi-agent pipeline
        """
        print(f"\n🔬 Starting research for: '{query}'")
        print("=" * 50)
        
        # Step 1: Research Planning
        research_plan = await self.research_planner.create_research_plan(query)
        
        # Step 2: Web Search (simulated)
        search_results = await self.web_searcher.simulate_web_search(query)
        
        # Step 3: Analysis and Summary
        analysis = await self.summarizer.analyze_information(query, research_plan, search_results)
        
        # Calculate total cost
        total_cost = (self.research_planner.total_cost + 
                     self.web_searcher.total_cost + 
                     self.summarizer.total_cost)
        
        return SimpleResearchResult(
            query=query,
            research_plan=research_plan,
            search_results=search_results,
            analysis=analysis,
            total_cost=total_cost
        )
    
    def get_agent_stats(self) -> Dict:
        """Get simple statistics for each agent"""
        return {
            "research_planner": {
                "calls": self.research_planner.call_count,
                "cost": self.research_planner.total_cost
            },
            "web_searcher": {
                "calls": self.web_searcher.call_count,
                "cost": self.web_searcher.total_cost
            },
            "summarizer": {
                "calls": self.summarizer.call_count,
                "cost": self.summarizer.total_cost
            }
        }

async def main():
    """
    Demonstrate basic multi-agent pipeline
    """
    print("🎓 Module 3: Basic Multi-Agent Pipeline")
    print("=" * 60)
    print("This demonstrates a simplified version of the multi-agent pipeline.")
    print("Each agent uses specialized models for their specific tasks.")
    
    try:
        # Create the multi-agent system
        system = SimpleMultiAgentSystem()
        
        # Test query
        query = "What are the benefits of renewable energy?"
        
        # Conduct research
        result = await system.conduct_simple_research(query)
        
        # Display results
        print(f"\n📋 Research Results")
        print("=" * 30)
        print(f"Query: {result.query}")
        print(f"\n🧠 Research Plan:")
        print(result.research_plan[:200] + "..." if len(result.research_plan) > 200 else result.research_plan)
        
        print(f"\n🔍 Search Results:")
        print(result.search_results[:200] + "..." if len(result.search_results) > 200 else result.search_results)
        
        print(f"\n📊 Analysis:")
        print(result.analysis[:200] + "..." if len(result.analysis) > 200 else result.analysis)
        
        # Show agent statistics
        stats = system.get_agent_stats()
        print(f"\n💰 Cost Summary:")
        total_cost = 0
        for agent_name, agent_stats in stats.items():
            print(f"{agent_name.replace('_', ' ').title()}: ${agent_stats['cost']:.4f} ({agent_stats['calls']} calls)")
            total_cost += agent_stats['cost']
        print(f"Total: ${total_cost:.4f}")
        
        print(f"\n🎯 Key Takeaways:")
        print("1. Each agent has a specialized role and optimized model")
        print("2. Agents work together in a coordinated pipeline")
        print("3. Different models are used for different tasks")
        print("4. Cost tracking provides transparency across agents")
        
        print(f"\n✅ Module 3 complete! Full pipeline includes Quality Evaluator, Summarizer, and Report Synthesizer.")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        print("Make sure FIREWORKS_API_KEY is set in your environment")

if __name__ == "__main__":
    asyncio.run(main()) 