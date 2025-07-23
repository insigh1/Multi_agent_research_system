#!/usr/bin/env python3
"""
Module 4 Example: Real-Time Progress Tracking with WebSockets

This script demonstrates:
- Real-time progress tracking during LLM operations
- WebSocket-based communication patterns
- Progress callback system
- Session management
- Event-driven architecture

Run: python module4_real_time_progress.py
"""

import asyncio
import os
import time
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProgressState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressUpdate:
    step_name: str
    progress: float  # 0.0 to 1.0
    state: ProgressState
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)

@dataclass
class ResearchSession:
    session_id: str
    query: str
    start_time: str
    total_steps: int
    current_step: int = 0
    overall_progress: float = 0.0
    state: ProgressState = ProgressState.PENDING
    updates: List[ProgressUpdate] = field(default_factory=list)

class ProgressTracker:
    """
    Tracks progress of multi-step operations with real-time updates
    """
    
    def __init__(self, session_id: str, total_steps: int, 
                 callback: Optional[Callable] = None):
        self.session_id = session_id
        self.total_steps = total_steps
        self.current_step = 0
        self.callback = callback
        self.step_progress = {}
        self.start_time = time.time()
        
        print(f"📊 Progress Tracker initialized for session {session_id[:8]}...")
        print(f"   Total steps: {total_steps}")
    
    async def update_step(self, step_name: str, progress: float, 
                         message: str, state: ProgressState = ProgressState.IN_PROGRESS,
                         metadata: Dict = None):
        """Update progress for a specific step"""
        
        # Calculate overall progress
        self.step_progress[step_name] = progress
        completed_steps = sum(1 for p in self.step_progress.values() if p >= 1.0)
        overall_progress = (completed_steps + progress) / self.total_steps
        
        update = ProgressUpdate(
            step_name=step_name,
            progress=progress,
            state=state,
            message=message,
            metadata=metadata or {}
        )
        
        print(f"📈 {step_name}: {progress*100:.1f}% - {message}")
        
        # Call callback if provided (simulates WebSocket send)
        if self.callback:
            await self.callback({
                "type": "progress_update",
                "session_id": self.session_id,
                "step_name": step_name,
                "step_progress": progress,
                "overall_progress": overall_progress,
                "state": state.value,
                "message": message,
                "timestamp": update.timestamp,
                "metadata": update.metadata
            })
        
        return update
    
    async def complete_step(self, step_name: str, message: str = "Step completed"):
        """Mark a step as completed"""
        await self.update_step(step_name, 1.0, message, ProgressState.COMPLETED)
        self.current_step += 1
        
        if self.current_step >= self.total_steps:
            duration = time.time() - self.start_time
            await self.callback({
                "type": "research_complete",
                "session_id": self.session_id,
                "duration": duration,
                "message": "Research completed successfully"
            })
    
    async def fail_step(self, step_name: str, error_message: str):
        """Mark a step as failed"""
        await self.update_step(step_name, 0.0, error_message, ProgressState.FAILED)
        
        if self.callback:
            await self.callback({
                "type": "error",
                "session_id": self.session_id,
                "step_name": step_name,
                "error": error_message
            })

# Simulated WebSocket connection manager
class MockConnectionManager:
    """
    Simulates WebSocket connection management for demonstration
    """
    
    def __init__(self):
        self.active_connections = {}
        print("🔌 Mock WebSocket Connection Manager initialized")
    
    async def connect(self, session_id: str):
        """Simulate WebSocket connection"""
        self.active_connections[session_id] = {
            "connected_at": datetime.now().isoformat(),
            "message_count": 0
        }
        print(f"🔗 Client connected: {session_id[:8]}...")
    
    async def disconnect(self, session_id: str):
        """Simulate WebSocket disconnection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 Client disconnected: {session_id[:8]}...")
    
    async def send_message(self, session_id: str, message: Dict):
        """Simulate sending message to WebSocket client"""
        if session_id in self.active_connections:
            self.active_connections[session_id]["message_count"] += 1
            
            # Pretty print the message
            print(f"📤 WebSocket → {session_id[:8]}: {message['type']}")
            if message['type'] == 'progress_update':
                print(f"   Step: {message['step_name']}")
                print(f"   Progress: {message['step_progress']*100:.1f}%")
                print(f"   Overall: {message['overall_progress']*100:.1f}%")
                print(f"   Message: {message['message']}")
            elif message['type'] == 'research_complete':
                print(f"   Duration: {message['duration']:.2f}s")
                print(f"   Message: {message['message']}")
            elif message['type'] == 'error':
                print(f"   Error: {message['error']}")

class ProgressAwareLLMAgent:
    """
    LLM Agent with progress tracking capabilities
    """
    
    def __init__(self, name: str, model: str = "llama-v3p1-8b-instruct"):
        self.name = name
        self.model = model
        self.api_key = os.getenv("FIREWORKS_API_KEY")
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY environment variable not set")
        
        print(f"🤖 {name} Agent initialized with progress tracking")
    
    async def process_with_progress(self, prompt: str, progress_tracker: ProgressTracker,
                                  step_name: str) -> Dict:
        """Process a request with detailed progress tracking"""
        
        try:
            # Step 1: Initialize
            await progress_tracker.update_step(
                step_name, 0.1, f"{self.name}: Initializing API call..."
            )
            
            # Step 2: Prepare request
            await progress_tracker.update_step(
                step_name, 0.3, f"{self.name}: Preparing request data..."
            )
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": f"accounts/fireworks/models/{self.model}",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.3
            }
            
            # Step 3: Make API call
            await progress_tracker.update_step(
                step_name, 0.5, f"{self.name}: Making API call to Fireworks..."
            )
            
            async with aiohttp.ClientSession() as session:
                # Simulate some processing time
                await asyncio.sleep(0.5)
                
                await progress_tracker.update_step(
                    step_name, 0.7, f"{self.name}: Waiting for LLM response..."
                )
                
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await progress_tracker.fail_step(
                            step_name, f"API call failed: {response.status} - {error_text}"
                        )
                        raise Exception(f"API call failed: {response.status}")
                    
                    result = await response.json()
                    
                    # Step 4: Process response
                    await progress_tracker.update_step(
                        step_name, 0.9, f"{self.name}: Processing response..."
                    )
                    
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    
                    # Calculate cost
                    total_tokens = usage.get("total_tokens", 0)
                    cost_per_1m = 0.20 if "8b" in self.model else 0.90
                    cost = (total_tokens / 1_000_000) * cost_per_1m
                    
                    # Complete step
                    await progress_tracker.complete_step(
                        step_name, f"{self.name}: Processing complete"
                    )
                    
                    return {
                        "content": content,
                        "usage": usage,
                        "cost": cost,
                        "agent": self.name
                    }
                    
        except Exception as e:
            await progress_tracker.fail_step(step_name, f"{self.name}: {str(e)}")
            raise

class RealTimeResearchSystem:
    """
    Research system with real-time progress tracking
    """
    
    def __init__(self):
        self.connection_manager = MockConnectionManager()
        self.active_sessions = {}
        
        print("🚀 Real-Time Research System initialized")
    
    async def start_research_session(self, query: str) -> str:
        """Start a new research session with progress tracking"""
        session_id = str(uuid.uuid4())
        
        session = ResearchSession(
            session_id=session_id,
            query=query,
            start_time=datetime.now().isoformat(),
            total_steps=3,  # Planning, Research, Synthesis
            state=ProgressState.PENDING
        )
        
        self.active_sessions[session_id] = session
        await self.connection_manager.connect(session_id)
        
        print(f"\n🎯 Started research session: {session_id[:8]}...")
        print(f"   Query: {query}")
        
        return session_id
    
    async def conduct_research_with_progress(self, session_id: str):
        """Conduct research with real-time progress updates"""
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Create progress tracker with callback
        progress_tracker = ProgressTracker(
            session_id=session_id,
            total_steps=3,
            callback=lambda msg: self.connection_manager.send_message(session_id, msg)
        )
        
        try:
            session.state = ProgressState.IN_PROGRESS
            
            # Step 1: Research Planning
            planner_agent = ProgressAwareLLMAgent("Research Planner", "llama-v3p3-70b-instruct")
            
            planning_prompt = f"""Create a brief research plan for: "{session.query}"
            
Include:
1. 2-3 key research questions
2. Research approach
3. Expected outcomes

Keep it concise and focused."""
            
            plan_result = await planner_agent.process_with_progress(
                planning_prompt, progress_tracker, "research_planning"
            )
            
            # Step 2: Information Gathering
            searcher_agent = ProgressAwareLLMAgent("Web Searcher", "llama-v3p1-8b-instruct")
            
            search_prompt = f"""Based on this research plan, simulate finding key information:

RESEARCH PLAN:
{plan_result['content']}

Provide 2-3 key findings that would answer the research questions."""
            
            search_result = await searcher_agent.process_with_progress(
                search_prompt, progress_tracker, "information_gathering"
            )
            
            # Step 3: Report Synthesis
            synthesizer_agent = ProgressAwareLLMAgent("Report Synthesizer", "llama-v3p3-70b-instruct")
            
            synthesis_prompt = f"""Synthesize the research into a final report:

ORIGINAL QUERY: {session.query}

RESEARCH PLAN:
{plan_result['content']}

KEY FINDINGS:
{search_result['content']}

Create a concise final report with key insights and recommendations."""
            
            final_result = await synthesizer_agent.process_with_progress(
                synthesis_prompt, progress_tracker, "report_synthesis"
            )
            
            session.state = ProgressState.COMPLETED
            
            return {
                "session_id": session_id,
                "query": session.query,
                "plan": plan_result['content'],
                "findings": search_result['content'],
                "final_report": final_result['content'],
                "total_cost": plan_result['cost'] + search_result['cost'] + final_result['cost']
            }
            
        except Exception as e:
            session.state = ProgressState.FAILED
            await self.connection_manager.send_message(session_id, {
                "type": "error",
                "session_id": session_id,
                "error": str(e)
            })
            raise
        finally:
            await self.connection_manager.disconnect(session_id)
    
    def get_session_status(self, session_id: str) -> Optional[ResearchSession]:
        """Get current session status"""
        return self.active_sessions.get(session_id)

async def main():
    """Demonstrate real-time progress tracking"""
    print("🎓 Module 4: Real-Time Progress Tracking with WebSockets")
    print("=" * 60)
    print("This demonstrates how progress is tracked and communicated in real-time.")
    
    try:
        # Initialize system
        research_system = RealTimeResearchSystem()
        
        # Start research session
        query = "How does AI impact modern education?"
        session_id = await research_system.start_research_session(query)
        
        print(f"\n🔄 Starting real-time research...")
        print("=" * 40)
        
        # Conduct research with progress tracking
        result = await research_system.conduct_research_with_progress(session_id)
        
        # Display final results
        print(f"\n📋 FINAL RESULTS")
        print("=" * 30)
        print(f"Session: {session_id[:8]}...")
        print(f"Query: {result['query']}")
        print(f"Total Cost: ${result['total_cost']:.4f}")
        
        print(f"\n📝 Final Report:")
        print("-" * 20)
        print(result['final_report'][:300] + "..." if len(result['final_report']) > 300 else result['final_report'])
        
        # Show session status
        session = research_system.get_session_status(session_id)
        print(f"\n📊 Session Status:")
        print(f"   State: {session.state.value}")
        print(f"   Total Steps: {session.total_steps}")
        print(f"   Current Step: {session.current_step}")
        
        print(f"\n🎯 Key Takeaways:")
        print("1. Progress tracking provides real-time feedback to users")
        print("2. WebSocket connections enable live updates")
        print("3. Each step reports detailed progress (0-100%)")
        print("4. Error handling ensures graceful failure recovery")
        print("5. Session management tracks multiple concurrent operations")
        print("\n✅ Module 4 complete! This shows how to build responsive AI systems.")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        print("Make sure FIREWORKS_API_KEY is set in your environment")

if __name__ == "__main__":
    asyncio.run(main()) 