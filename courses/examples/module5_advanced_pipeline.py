#!/usr/bin/env python3
"""
Module 5: Advanced Pipeline Implementation
Demonstrates sophisticated multi-agent coordination, parallel processing, 
error recovery, and pipeline orchestration.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import uuid
from datetime import datetime

# External dependencies
import aiohttp
import structlog
from asyncio_throttle import Throttler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

class PipelineStage(Enum):
    PLANNING = "planning"
    GATHERING = "gathering" 
    EVALUATION = "evaluation"
    SUMMARIZATION = "summarization"
    SYNTHESIS = "synthesis"

class AgentType(Enum):
    PLANNER = "planner"
    RETRIEVER = "retriever"
    EVALUATOR = "evaluator"
    SUMMARIZER = "summarizer"
    SYNTHESIZER = "synthesizer"

@dataclass
class PipelineResult:
    stage: PipelineStage
    agent_type: AgentType
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    retry_count: int = 0

@dataclass
class ResearchContext:
    query: str
    session_id: str
    results: Dict[PipelineStage, PipelineResult] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    current_stage: Optional[PipelineStage] = None
    
class PipelineOrchestrator:
    """Advanced pipeline orchestrator with parallel processing and error recovery"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        self.session = None
        self.throttler = Throttler(rate_limit=10, period=1.0)  # 10 requests per second
        
        # Pipeline configuration
        self.stage_dependencies = {
            PipelineStage.PLANNING: [],
            PipelineStage.GATHERING: [PipelineStage.PLANNING],
            PipelineStage.EVALUATION: [PipelineStage.GATHERING],
            PipelineStage.SUMMARIZATION: [PipelineStage.EVALUATION],
            PipelineStage.SYNTHESIS: [PipelineStage.SUMMARIZATION]
        }
        
        # Agent configurations with specialized models
        self.agent_configs = {
            AgentType.PLANNER: {
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "max_tokens": 1000,
                "temperature": 0.2,
                "max_retries": 3
            },
            AgentType.RETRIEVER: {
                "model": "accounts/fireworks/models/llama-v3p1-8b-instruct", 
                "max_tokens": 800,
                "temperature": 0.1,
                "max_retries": 2
            },
            AgentType.EVALUATOR: {
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "max_tokens": 600,
                "temperature": 0.0,
                "max_retries": 3
            },
            AgentType.SUMMARIZER: {
                "model": "accounts/fireworks/models/qwen2p5-72b-instruct",
                "max_tokens": 1200,
                "temperature": 0.3,
                "max_retries": 2
            },
            AgentType.SYNTHESIZER: {
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "max_tokens": 2000,
                "temperature": 0.4,
                "max_retries": 3
            }
        }
        
        # Cost tracking (per 1M tokens)
        self.model_costs = {
            "accounts/fireworks/models/llama-v3p3-70b-instruct": 0.0009,
            "accounts/fireworks/models/llama-v3p1-8b-instruct": 0.0002,
            "accounts/fireworks/models/qwen2p5-72b-instruct": 0.0009
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def execute_agent(self, agent_type: AgentType, prompt: str, context: ResearchContext) -> PipelineResult:
        """Execute an agent with retry logic and error handling"""
        config = self.agent_configs[agent_type]
        start_time = time.time()
        
        for attempt in range(config["max_retries"]):
            try:
                async with self.throttler:
                    payload = {
                        "model": config["model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": config["max_tokens"],
                        "temperature": config["temperature"]
                    }
                    
                    async with self.session.post(self.base_url, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data["choices"][0]["message"]["content"]
                            tokens_used = data["usage"]["total_tokens"]
                            cost = (tokens_used / 1_000_000) * self.model_costs[config["model"]]
                            
                            execution_time = time.time() - start_time
                            
                            logger.info(
                                "Agent execution successful",
                                agent_type=agent_type.value,
                                tokens_used=tokens_used,
                                cost=f"${cost:.6f}",
                                execution_time=f"{execution_time:.2f}s",
                                attempt=attempt + 1
                            )
                            
                            return PipelineResult(
                                stage=self._get_stage_for_agent(agent_type),
                                agent_type=agent_type,
                                success=True,
                                data={"content": content, "raw_response": data},
                                execution_time=execution_time,
                                tokens_used=tokens_used,
                                cost=cost,
                                retry_count=attempt
                            )
                        else:
                            error_text = await response.text()
                            logger.warning(
                                "Agent execution failed",
                                agent_type=agent_type.value,
                                status=response.status,
                                error=error_text,
                                attempt=attempt + 1
                            )
                            
            except Exception as e:
                logger.error(
                    "Agent execution error",
                    agent_type=agent_type.value,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < config["max_retries"] - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        # All retries failed
        execution_time = time.time() - start_time
        return PipelineResult(
            stage=self._get_stage_for_agent(agent_type),
            agent_type=agent_type,
            success=False,
            error=f"Failed after {config['max_retries']} attempts",
            execution_time=execution_time,
            retry_count=config["max_retries"]
        )
        
    def _get_stage_for_agent(self, agent_type: AgentType) -> PipelineStage:
        """Map agent types to pipeline stages"""
        mapping = {
            AgentType.PLANNER: PipelineStage.PLANNING,
            AgentType.RETRIEVER: PipelineStage.GATHERING,
            AgentType.EVALUATOR: PipelineStage.EVALUATION,
            AgentType.SUMMARIZER: PipelineStage.SUMMARIZATION,
            AgentType.SYNTHESIZER: PipelineStage.SYNTHESIS
        }
        return mapping[agent_type]
        
    async def can_execute_stage(self, stage: PipelineStage, context: ResearchContext) -> bool:
        """Check if stage dependencies are satisfied"""
        dependencies = self.stage_dependencies[stage]
        for dep_stage in dependencies:
            if dep_stage not in context.results or not context.results[dep_stage].success:
                return False
        return True
        
    async def execute_pipeline_stage(self, stage: PipelineStage, context: ResearchContext) -> PipelineResult:
        """Execute a pipeline stage with proper context"""
        context.current_stage = stage
        
        if stage == PipelineStage.PLANNING:
            return await self.execute_planning_stage(context)
        elif stage == PipelineStage.GATHERING:
            return await self.execute_gathering_stage(context)
        elif stage == PipelineStage.EVALUATION:
            return await self.execute_evaluation_stage(context)
        elif stage == PipelineStage.SUMMARIZATION:
            return await self.execute_summarization_stage(context)
        elif stage == PipelineStage.SYNTHESIS:
            return await self.execute_synthesis_stage(context)
        else:
            raise ValueError(f"Unknown stage: {stage}")
            
    async def execute_planning_stage(self, context: ResearchContext) -> PipelineResult:
        """Execute planning stage with research strategy generation"""
        prompt = f"""
        As a Research Planning Agent, analyze this research query and create a comprehensive research strategy:
        
        Query: "{context.query}"
        
        Generate a structured research plan with:
        1. 3-5 key research questions to investigate
        2. Information gathering strategy
        3. Expected challenges and mitigation approaches
        4. Success criteria for the research
        
        Provide a detailed, actionable research plan in JSON format.
        """
        
        result = await self.execute_agent(AgentType.PLANNER, prompt, context)
        if result.success:
            try:
                # Try to parse JSON response
                plan_data = json.loads(result.data["content"])
                result.data["parsed_plan"] = plan_data
            except json.JSONDecodeError:
                # Fallback to raw content
                result.data["parsed_plan"] = {"raw_plan": result.data["content"]}
                
        context.results[PipelineStage.PLANNING] = result
        return result
        
    async def execute_gathering_stage(self, context: ResearchContext) -> PipelineResult:
        """Execute information gathering with parallel processing"""
        planning_result = context.results[PipelineStage.PLANNING]
        
        # Simulate parallel information gathering
        gather_tasks = []
        
        for i in range(3):  # Simulate 3 parallel search tasks
            prompt = f"""
            As a Web Search Retriever Agent, gather information for this research:
            
            Original Query: "{context.query}"
            Research Plan: {planning_result.data.get('parsed_plan', {})}
            
            Search Focus {i+1}: Find specific information about aspect {i+1} of the research query.
            Simulate gathering relevant information and provide 2-3 key findings with sources.
            """
            
            task = asyncio.create_task(
                self.execute_agent(AgentType.RETRIEVER, prompt, context)
            )
            gather_tasks.append(task)
            
        # Execute all gathering tasks in parallel
        gather_results = await asyncio.gather(*gather_tasks, return_exceptions=True)
        
        # Combine results
        successful_results = [r for r in gather_results if isinstance(r, PipelineResult) and r.success]
        failed_results = [r for r in gather_results if isinstance(r, Exception) or not r.success]
        
        combined_result = PipelineResult(
            stage=PipelineStage.GATHERING,
            agent_type=AgentType.RETRIEVER,
            success=len(successful_results) > 0,
            data={
                "successful_searches": len(successful_results),
                "failed_searches": len(failed_results),
                "search_results": [r.data for r in successful_results]
            },
            execution_time=sum(r.execution_time for r in successful_results),
            tokens_used=sum(r.tokens_used for r in successful_results),
            cost=sum(r.cost for r in successful_results)
        )
        
        context.results[PipelineStage.GATHERING] = combined_result
        return combined_result
        
    async def execute_evaluation_stage(self, context: ResearchContext) -> PipelineResult:
        """Execute quality evaluation of gathered information"""
        gathering_result = context.results[PipelineStage.GATHERING]
        
        prompt = f"""
        As a Quality Evaluation Agent, assess the quality and reliability of gathered information:
        
        Research Query: "{context.query}"
        Gathered Information: {gathering_result.data}
        
        Evaluate:
        1. Information quality and relevance (1-10 scale)
        2. Source reliability assessment
        3. Coverage completeness
        4. Identify gaps or inconsistencies
        5. Overall confidence score
        
        Provide structured evaluation with scores and recommendations.
        """
        
        result = await self.execute_agent(AgentType.EVALUATOR, prompt, context)
        context.results[PipelineStage.EVALUATION] = result
        return result
        
    async def execute_summarization_stage(self, context: ResearchContext) -> PipelineResult:
        """Execute content summarization with key insights"""
        evaluation_result = context.results[PipelineStage.EVALUATION]
        gathering_result = context.results[PipelineStage.GATHERING]
        
        prompt = f"""
        As a Summarization Agent, process and synthesize the evaluated information:
        
        Research Query: "{context.query}"
        Evaluation Results: {evaluation_result.data.get('content', 'N/A')}
        Raw Information: {gathering_result.data}
        
        Create:
        1. Executive summary of key findings
        2. Main insights and patterns
        3. Supporting evidence for each insight
        4. Limitations and uncertainties
        
        Provide a comprehensive but concise summary.
        """
        
        result = await self.execute_agent(AgentType.SUMMARIZER, prompt, context)
        context.results[PipelineStage.SUMMARIZATION] = result
        return result
        
    async def execute_synthesis_stage(self, context: ResearchContext) -> PipelineResult:
        """Execute final report synthesis"""
        summary_result = context.results[PipelineStage.SUMMARIZATION]
        evaluation_result = context.results[PipelineStage.EVALUATION]
        
        prompt = f"""
        As a Report Synthesis Agent, create the final comprehensive research report:
        
        Research Query: "{context.query}"
        Summary: {summary_result.data.get('content', 'N/A')}
        Quality Assessment: {evaluation_result.data.get('content', 'N/A')}
        
        Generate a complete research report with:
        1. Executive Summary
        2. Methodology
        3. Key Findings
        4. Analysis and Insights
        5. Recommendations
        6. Limitations and Future Research
        
        Make it professional and actionable.
        """
        
        result = await self.execute_agent(AgentType.SYNTHESIZER, prompt, context)
        context.results[PipelineStage.SYNTHESIS] = result
        return result
        
    async def execute_full_pipeline(self, query: str) -> ResearchContext:
        """Execute the complete research pipeline with advanced orchestration"""
        context = ResearchContext(
            query=query,
            session_id=str(uuid.uuid4())
        )
        
        logger.info("Starting advanced pipeline execution", query=query, session_id=context.session_id)
        
        # Execute stages in dependency order
        stages_to_execute = [
            PipelineStage.PLANNING,
            PipelineStage.GATHERING,
            PipelineStage.EVALUATION,
            PipelineStage.SUMMARIZATION,
            PipelineStage.SYNTHESIS
        ]
        
        for stage in stages_to_execute:
            if await self.can_execute_stage(stage, context):
                logger.info("Executing pipeline stage", stage=stage.value)
                
                result = await self.execute_pipeline_stage(stage, context)
                
                if result.success:
                    logger.info(
                        "Stage completed successfully",
                        stage=stage.value,
                        tokens_used=result.tokens_used,
                        cost=f"${result.cost:.6f}",
                        execution_time=f"{result.execution_time:.2f}s"
                    )
                else:
                    logger.error(
                        "Stage failed",
                        stage=stage.value,
                        error=result.error,
                        retry_count=result.retry_count
                    )
                    # Continue with next stage even if current fails (graceful degradation)
            else:
                logger.warning("Skipping stage due to unmet dependencies", stage=stage.value)
                
        # Calculate total metrics
        total_cost = sum(r.cost for r in context.results.values())
        total_tokens = sum(r.tokens_used for r in context.results.values())
        total_time = (datetime.now() - context.start_time).total_seconds()
        
        logger.info(
            "Pipeline execution completed",
            session_id=context.session_id,
            total_cost=f"${total_cost:.6f}",
            total_tokens=total_tokens,
            total_time=f"{total_time:.2f}s",
            successful_stages=sum(1 for r in context.results.values() if r.success),
            total_stages=len(context.results)
        )
        
        return context
        
    def get_pipeline_summary(self, context: ResearchContext) -> Dict[str, Any]:
        """Generate comprehensive pipeline execution summary"""
        total_cost = sum(r.cost for r in context.results.values())
        total_tokens = sum(r.tokens_used for r in context.results.values())
        total_time = (datetime.now() - context.start_time).total_seconds()
        
        stage_summary = {}
        for stage, result in context.results.items():
            stage_summary[stage.value] = {
                "success": result.success,
                "agent_type": result.agent_type.value,
                "execution_time": f"{result.execution_time:.2f}s",
                "tokens_used": result.tokens_used,
                "cost": f"${result.cost:.6f}",
                "retry_count": result.retry_count,
                "error": result.error
            }
            
        return {
            "session_id": context.session_id,
            "query": context.query,
            "total_cost": f"${total_cost:.6f}",
            "total_tokens": total_tokens,
            "total_execution_time": f"{total_time:.2f}s",
            "successful_stages": sum(1 for r in context.results.values() if r.success),
            "total_stages": len(context.results),
            "stage_details": stage_summary,
            "final_report_available": PipelineStage.SYNTHESIS in context.results and context.results[PipelineStage.SYNTHESIS].success
        }

async def main():
    """Demonstrate advanced pipeline implementation"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("FIREWORKS_API_KEY")
    
    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("Please set your Fireworks AI API key in .env file")
        return
        
    research_query = "What are the latest developments in quantum computing applications for AI?"
    
    print("🚀 Advanced Pipeline Implementation Demo")
    print("=" * 60)
    print(f"📝 Research Query: {research_query}")
    print(f"⏰ Starting pipeline execution at {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    async with PipelineOrchestrator(api_key) as orchestrator:
        # Execute the complete pipeline
        context = await orchestrator.execute_full_pipeline(research_query)
        
        # Display comprehensive results
        summary = orchestrator.get_pipeline_summary(context)
        
        print("📊 Pipeline Execution Summary")
        print("-" * 40)
        print(f"Session ID: {summary['session_id']}")
        print(f"Total Cost: {summary['total_cost']}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Execution Time: {summary['total_execution_time']}")
        print(f"Success Rate: {summary['successful_stages']}/{summary['total_stages']} stages")
        print()
        
        print("🔍 Stage-by-Stage Results:")
        for stage_name, details in summary['stage_details'].items():
            status_emoji = "✅" if details['success'] else "❌"
            print(f"{status_emoji} {stage_name.title()}")
            print(f"   Agent: {details['agent_type']}")
            print(f"   Time: {details['execution_time']}")
            print(f"   Cost: {details['cost']}")
            print(f"   Tokens: {details['tokens_used']}")
            if details['retry_count'] > 0:
                print(f"   Retries: {details['retry_count']}")
            if details['error']:
                print(f"   Error: {details['error']}")
            print()
            
        # Display final report if available
        if summary['final_report_available']:
            synthesis_result = context.results[PipelineStage.SYNTHESIS]
            print("📝 Final Research Report")
            print("=" * 50)
            print(synthesis_result.data.get('content', 'Report content not available'))
        else:
            print("❌ Final report generation failed")
            
        print("\n" + "=" * 60)
        print("🎉 Advanced Pipeline Implementation Demo Complete!")
        print("Key Features Demonstrated:")
        print("• Parallel processing for information gathering")
        print("• Sophisticated error handling and retry logic") 
        print("• Dynamic pipeline orchestration with dependencies")
        print("• Real-time cost and performance tracking")
        print("• Agent specialization with optimized models")
        print("• Graceful degradation on failures")

if __name__ == "__main__":
    asyncio.run(main()) 