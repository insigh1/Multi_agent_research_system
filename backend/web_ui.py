#!/usr/bin/env python3
"""
Multi-Agent Research System
Copyright (c) 2025 David Lee (@insigh1) - Fireworks AI
MIT License - see LICENSE file for details

Multi-Agent Research System - Web UI
====================================

Modern web interface for the Multi-Agent Research System with:
- Real-time progress tracking via WebSockets
- Interactive research configuration
- Beautiful results visualization
- Session management and history
- Export capabilities (PDF, HTML, JSON)
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our existing research system with fallback handling
# First try: assume we're being called as a module (from root entry point)
try:
    from backend.config import Settings, QueryRequest
    from backend.main import EnhancedResearchSystem
    from backend.utils import (
        SecurityManager, CacheManager, ProgressTracker, 
        setup_logging, start_metrics_server, managed_session,
        get_organized_report_path, create_report_index_entry
    )
except (ImportError, ModuleNotFoundError):
    # Second try: assume we're in the backend directory
    try:
        from config import Settings, QueryRequest
        from main import EnhancedResearchSystem
        from utils import (
            SecurityManager, CacheManager, ProgressTracker, 
            setup_logging, start_metrics_server, managed_session,
            get_organized_report_path, create_report_index_entry
        )
    except (ImportError, ModuleNotFoundError):
        # Third try: relative import (when imported as package)
        from .config import Settings, QueryRequest
        from .main import EnhancedResearchSystem
        from .utils import (
            SecurityManager, CacheManager, ProgressTracker, 
            setup_logging, start_metrics_server, managed_session,
            get_organized_report_path, create_report_index_entry
        )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class AgentModelConfig(BaseModel):
    agent_type: str
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class ResearchRequest(BaseModel):
    query: str
    max_questions: int = 5
    output_format: str = "json"
    save_session: bool = True
    session_id: Optional[str] = None
    selected_model: Optional[str] = None  # Legacy field for backward compatibility
    executive_summary_style: str = "comprehensive"  # brief, detailed, comprehensive
    agent_models: Optional[Dict[str, str]] = None  # New field: agent_type -> model_name mapping

class ResearchResponse(BaseModel):
    session_id: str
    status: str
    message: str

class ModelConfigUpdateRequest(BaseModel):
    agent_models: Dict[str, str]  # agent_type -> model_name mapping

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_progress_update(self, session_id: str, data: dict):
        """Send progress update to a specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Debug logging for completion updates
                if data.get("status") == "completed":
                    print(f"📡 WebSocket sending completion data:")
                    print(f"   Session: {session_id}")
                    print(f"   Steps completed: {data.get('steps_completed', 'NOT_FOUND')}")
                    print(f"   Final metrics steps: {data.get('final_metrics', {}).get('steps_completed', 'NOT_FOUND')}")
                    print(f"   Keep metrics visible: {data.get('keep_metrics_visible', 'NOT_FOUND')}")
                
                await websocket.send_text(json.dumps(data))
                logger.debug(f"Progress update sent to session {session_id}: {data.get('current_operation', 'No operation')}")
            except Exception as e:
                logger.error(f"Failed to send progress update to session {session_id}: {e}")
                # Remove the failed connection
                del self.active_connections[session_id]
        else:
            logger.warning(f"No active WebSocket connection for session {session_id}")

# Global instances
app = FastAPI(title="Multi-Agent Research System", version="2.0")
connection_manager = ConnectionManager()
active_research_tasks: Dict[str, asyncio.Task] = {}

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize settings
settings = Settings()

@app.on_event("startup")
async def startup_event():
    """Initialize the research system on startup"""
    logger.info("Starting Multi-Agent Research System Web UI")
    setup_logging(settings)

@app.get("/", response_class=HTMLResponse)
async def get_root():
    """Serve the optimized React frontend"""
    try:
        # Serve the built frontend from the dist directory
        frontend_path = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
        if frontend_path.exists():
            return FileResponse(frontend_path)
        else:
            # Fallback if built frontend doesn't exist
            return HTMLResponse(
                content="""
                <html>
                    <head><title>Multi-Agent Research System</title></head>
                    <body>
                        <h1>Frontend Build Not Found</h1>
                        <p>Please run: <code>cd frontend && npm run build</code></p>
                    </body>
                </html>
                """,
                status_code=503
            )
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error loading frontend: {e}</h1></body></html>",
            status_code=500
        )

# Serve static assets from the built frontend
@app.get("/assets/{path:path}")
async def serve_assets(path: str):
    """Serve static assets from the built frontend"""
    try:
        asset_path = Path(__file__).parent.parent / "frontend" / "dist" / "assets" / path
        if asset_path.exists() and asset_path.is_file():
            return FileResponse(asset_path)
        else:
            raise HTTPException(status_code=404, detail="Asset not found")
    except Exception as e:
        logger.error(f"Error serving asset {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API Routes
@app.post("/api/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research session"""
    try:
        # Generate session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create research task
        research_task = asyncio.create_task(
            run_research_with_progress(request, session_id)
        )
        active_research_tasks[session_id] = research_task
        
        return ResearchResponse(
            session_id=session_id,
            status="started",
            message="Research started successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to start research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{session_id}/results")
async def get_research_results(session_id: str):
    """Get research results for a session"""
    try:
        # Load results from database
        async with EnhancedResearchSystem(settings) as system:
            session_data = system.db_manager.load_session(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            
            return session_data
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{session_id}/metrics")
async def get_research_metrics(session_id: str):
    """Get detailed metrics for a research session"""
    try:
        # Load results from database
        async with EnhancedResearchSystem(settings) as system:
            session_data = system.db_manager.load_session(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Extract metrics from metadata
            metadata = session_data.get("metadata", {})
            metrics = metadata.get("metrics", {})
            
            if metrics and isinstance(metrics, dict) and len(metrics) > 1:
                # Format metrics for web UI consumption
                formatted_metrics = {
                    "session_id": session_id,
                    "total_duration": metrics.get("total_duration", 0),
                    "total_tokens": metrics.get("total_tokens", metrics.get("total_tokens_raw", 0)),
                    "total_cost": metrics.get("total_cost", metrics.get("total_cost_raw", 0.0)),
                    "total_api_calls": metrics.get("total_api_calls", 0),
                    "steps_completed": metrics.get("steps_completed", len(metrics.get("steps", []))),
                    "cache_hit_rate": metrics.get("cache_hit_rate", 0.0),
                    "model_usage": metrics.get("model_usage", {}),
                    "agent_performance": metrics.get("agent_performance", {}),
                    "steps": metrics.get("steps", []),
                    "api_calls": metrics.get("api_calls_detail", metrics.get("api_calls", [])),
                    "insights": metrics.get("insights", {}),
                    "completion_timestamp": metadata.get("completion_timestamp", ""),
                    "processing_time": metadata.get("processing_time", 0),
                    "quality_score": metadata.get("quality_score", 0),
                    "total_sources": metadata.get("sources_found", metadata.get("total_sources", 0))
                }
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "metrics": formatted_metrics
                }
            else:
                return {
                    "success": True,
                    "session_id": session_id,
                    "metrics": {"message": "No detailed metrics available for this session"}
                }
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await connection_manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)

async def run_research_with_progress(request: ResearchRequest, session_id: str):
    """Run research with enhanced progress updates via WebSocket"""
    try:
        # Import global metrics collector with fallback handling
        try:
            from backend.enhanced_research_system import metrics_collector
        except (ImportError, ModuleNotFoundError):
            try:
                from enhanced_research_system import metrics_collector
            except (ImportError, ModuleNotFoundError):
                from .enhanced_research_system import metrics_collector
        
        # Start pipeline tracking with global collector
        pipeline_metrics = metrics_collector.start_pipeline(session_id, request.query)
        
        # Define research stages for progress tracking (matching main.py pipeline exactly)
        research_stages = [
            {"name": "Research Planning", "status": "pending", "details": {}},
            {"name": "Information Gathering", "status": "pending", "details": {}},
            {"name": "Quality Evaluation", "status": "pending", "details": {}},
            {"name": "Content Summarization", "status": "pending", "details": {}},
            {"name": "Report Assembly", "status": "pending", "details": {}}
        ]
        
        # Send initial progress with stage breakdown
        await connection_manager.send_progress_update(session_id, {
            "status": "started",
            "stage": "initializing",
            "progress_percentage": 0,
            "current_operation": "Setting up research agents...",
            "tokens_used": 0,
            "estimated_cost": 0.0,
            "api_calls_made": 0,
            "stage_breakdown": research_stages
        })
        
        # Create query request with validation error handling
        try:
            query_request = QueryRequest(
                query=request.query,
                max_sub_questions=request.max_questions,
                session_id=session_id,
                save_session=request.save_session
            )
        except Exception as validation_error:
            # Handle validation errors gracefully
            error_message = str(validation_error)
            if "string_too_short" in error_message:
                error_message = f"Query must be at least 3 characters long. You entered: '{request.query}' ({len(request.query)} characters)"
            elif "string_too_long" in error_message:
                error_message = f"Query must be no more than 1000 characters long. You entered {len(request.query)} characters"
            else:
                error_message = f"Invalid query format: {error_message}"
            
            await connection_manager.send_progress_update(session_id, {
                "status": "error",
                "stage": "validation_error",
                "progress_percentage": 0,
                "current_operation": "Validation failed",
                "message": error_message,
                "error_type": "validation",
                "stage_breakdown": research_stages
            })
            logger.error(f"Query validation failed: {error_message}")
            return
        
        # Store research plan to persist across all progress updates
        stored_research_plan = None
        
        # Custom progress callback for detailed updates (matching main.py signature)
        async def progress_callback(stage: str, percentage: float, operation: str, stage_index: int = None, research_plan: dict = None, agent: str = None):
            nonlocal stored_research_plan
            
            # Store research plan when first received
            if research_plan:
                stored_research_plan = research_plan
            
            # Update stage breakdown
            if stage_index is not None and stage_index < len(research_stages):
                # ULTRA-SPECIFIC completion detection - only when percentage is exactly 100%
                # OR when we have explicit final completion indicators
                final_completion_keywords = [
                    "final research report completed",
                    "research completed successfully",
                    "all steps completed"
                ]
                
                # Standard completion keywords that indicate a stage is finishing but not necessarily the whole research
                stage_completion_keywords = [
                    "created successfully", 
                    "completed successfully", 
                    "evaluation completed", 
                    "summarization completed", 
                    "assembly completed",
                    "report completed"
                ]
                
                # Only mark as completed if:
                # 1. Percentage is exactly 100%, OR
                # 2. We have a final completion keyword (end of entire research), OR  
                # 3. We have stage completion keyword AND percentage is 100%
                has_final_completion = any(keyword in operation.lower() for keyword in final_completion_keywords)
                has_stage_completion = any(keyword in operation.lower() for keyword in stage_completion_keywords)
                
                # ULTRA-RESTRICTIVE: Only mark as completed at exactly 100% OR final completion
                # This ensures stages show spinning circles during progress (even at 95%)
                is_stage_completed = (percentage == 100) or has_final_completion
                
                # Debug logging for completion detection
                print(f"🎯 COMPLETION DEBUG: Stage={stage}, %={percentage}")
                print(f"   Operation: {operation}")
                print(f"   Has final completion: {has_final_completion}")
                print(f"   Has stage completion: {has_stage_completion}")
                print(f"   Is stage completed: {is_stage_completed}")
                
                # Mark stages appropriately based on progress
                for i, s in enumerate(research_stages):
                    if i < stage_index:
                        s["status"] = "completed"
                    elif i == stage_index:
                        # Mark as completed only with explicit completion signal
                        if is_stage_completed:
                            s["status"] = "completed"
                            print(f"   ✅ Stage {i} ({s['name']}) marked as COMPLETED")
                        else:
                            # Stage is actively being processed - show spinning circle
                            s["status"] = "in_progress"
                            print(f"   🔄 Stage {i} ({s['name']}) marked as IN_PROGRESS")
                        
                        # Get current metrics for the active stage
                        current_metrics = metrics_collector.get_metrics_summary()
                        current_stage = research_stages[stage_index]  # Safe to access here
                        
                        # Add current operation details for the active stage
                        current_stage["details"] = {
                            "current_operation": operation,
                            "progress_percentage": percentage,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Add stage-specific metrics
                        current_stage["details"].update({
                            "tokens_used": current_metrics.get("current_step_tokens", 0),
                            "api_calls": current_metrics.get("current_step_api_calls", 0),
                            "duration": current_metrics.get("current_step_duration", 0),
                            "agent": agent or current_metrics.get("current_agent", "Unknown"),
                            "model_used": current_metrics.get("current_model", ""),
                            "cost_so_far": current_metrics.get("current_step_cost", 0.0),
                            "sources_found": current_metrics.get("current_step_sources", 0),
                            "completion_percentage": percentage
                        })
                        
                        # Add stage-specific data
                        # Add source filtering data for Information Gathering stage
                        if stage == "Information Gathering":
                            sources_count = len(metrics_collector.current_sources) if metrics_collector.current_sources else 0
                            
                            if metrics_collector.source_filtering_data:
                                # Use enhanced filtering data if available
                                logger.info(f"Adding source filtering data to Information Gathering stage")
                                current_stage["details"]["source_filtering"] = metrics_collector.source_filtering_data
                            else:
                                # Fallback to basic sources data
                                logger.info(f"Adding sources to Information Gathering stage: {sources_count} sources found")
                                current_stage["details"]["sources"] = metrics_collector.current_sources
                            
                            # ALWAYS include both sources and filtering data for completeness
                            current_stage["details"]["sources"] = metrics_collector.current_sources
                            current_stage["details"]["sources_count"] = sources_count
                        
                        # Add quality evaluation data for Quality Evaluation stage
                        if stage == "Quality Evaluation":
                            quality_evals_count = len(metrics_collector.quality_evaluations) if metrics_collector.quality_evaluations else 0
                            logger.info(f"Adding quality evaluations to Quality Evaluation stage: {quality_evals_count} evaluations found")
                            print(f"🔍 DEBUG WebSocket: Stage={stage}, Quality evaluations count={quality_evals_count}")
                            if metrics_collector.quality_evaluations:
                                print(f"  First evaluation: {metrics_collector.quality_evaluations[0]['sub_question'][:50]}... -> {metrics_collector.quality_evaluations[0]['pass_fail_status']}")
                            else:
                                print(f"  metrics_collector.quality_evaluations is empty or None: {metrics_collector.quality_evaluations}")
                            logger.debug(f"Quality evaluation data: {metrics_collector.quality_evaluations[:1] if metrics_collector.quality_evaluations else []}")  # Log first evaluation for debugging
                            current_stage["details"]["quality_evaluations"] = metrics_collector.quality_evaluations
                        
                        # Add summaries data for Content Summarization stage
                        if stage == "Content Summarization":
                            summaries_count = len(metrics_collector.summaries) if metrics_collector.summaries else 0
                            logger.info(f"Adding summaries to Content Summarization stage: {summaries_count} summaries found")
                            print(f"📝 DEBUG WebSocket: Stage={stage}, Summaries count={summaries_count}")
                            if metrics_collector.summaries:
                                print(f"  First summary: {metrics_collector.summaries[0]['question'][:50]}... -> {metrics_collector.summaries[0]['confidence_level']:.2f}")
                            else:
                                print(f"  metrics_collector.summaries is empty or None: {metrics_collector.summaries}")
                            logger.debug(f"Summaries data: {metrics_collector.summaries[:1] if metrics_collector.summaries else []}")  # Log first summary for debugging
                            current_stage["details"]["summaries"] = metrics_collector.summaries
                        
                        # Add final report data for Report Assembly stage  
                        if stage == "Report Assembly":
                            # Check if we have final report data in metrics_collector
                            if metrics_collector.final_report:
                                logger.info(f"Adding final report to Report Assembly stage from metrics collector")
                                # Access detailed_findings from dictionary (converted by asdict in MetricsCollector)
                                detailed_findings_count = len(metrics_collector.final_report.get('detailed_findings', []))
                                print(f"📋 DEBUG WebSocket: Stage={stage}, Final report available with {detailed_findings_count} detailed findings")
                                current_stage["details"]["final_report"] = metrics_collector.final_report
                            else:
                                # Fallback: check if we have summaries to use as detailed findings  
                                if metrics_collector.summaries:
                                    logger.info(f"Adding in-progress final report data to Report Assembly stage")
                                    print(f"📋 DEBUG WebSocket: Stage={stage}, Using summaries as detailed findings: {len(metrics_collector.summaries)} summaries")
                                    current_stage["details"]["final_report"] = {
                                        "detailed_findings": metrics_collector.summaries,
                                        "status": "in_progress"
                                    }
                    else:
                        s["status"] = "pending"
            
            # Get current metrics from global collector
            current_metrics = metrics_collector.get_metrics_summary()
            
            # Calculate current step count (number of completed steps)
            completed_steps = sum(1 for stage in research_stages if stage["status"] == "completed")
            
            # Try to get model usage from ModelManager if available
            model_usage_breakdown = {}
            try:
                from enhanced_research_system import ModelManager
                # Use settings variable (research_settings may not be defined yet)
                model_manager = ModelManager(settings)
                cost_summary = model_manager.get_cost_summary()
                model_usage_breakdown = {
                    "total_cost": cost_summary.get("total_cost", 0.0),
                    "total_tokens": cost_summary.get("total_tokens", 0),
                    "agent_breakdown": cost_summary.get("agent_costs", {})
                }
            except Exception as e:
                logger.debug(f"Could not get model usage breakdown: {e}")
            
            # Prepare progress update data
            progress_data = {
                "status": "in_progress",
                "stage": stage,
                "progress_percentage": percentage,
                "current_operation": operation,
                "tokens_used": current_metrics.get("total_tokens", 0),
                "estimated_cost": current_metrics.get("estimated_cost", 0.0),
                "api_calls_made": current_metrics.get("total_api_calls", 0),
                "steps_completed": completed_steps,  # Add step count for frontend
                "total_steps": len(research_stages),  # Add total steps for context
                "stage_breakdown": research_stages,
                "parallel_operations": current_metrics.get("active_operations", []),
                "model_usage": model_usage_breakdown
            }
            
            # Debug logging for API calls tracking
            print(f"🔍 DEBUG WebSocket: Stage={stage}, API calls from metrics: {current_metrics.get('total_api_calls', 0)}")
            print(f"   Total tokens: {current_metrics.get('total_tokens', 0)}")
            print(f"   Estimated cost: {current_metrics.get('estimated_cost', 0.0)}")
            print(f"   Sending api_calls_made: {progress_data['api_calls_made']}")
            print(f"   Progress status: {progress_data['status']}")
            print(f"   Progress percentage: {progress_data['progress_percentage']}")
            
            # Count current stage statuses
            stage_status_counts = {}
            for stage_item in progress_data.get('stage_breakdown', []):
                status = stage_item.get('status', 'unknown')
                stage_status_counts[status] = stage_status_counts.get(status, 0) + 1
            print(f"   Stage status distribution: {stage_status_counts}")
            
            # Add research plan if available
            if stored_research_plan:
                progress_data["research_plan"] = stored_research_plan
            
            await connection_manager.send_progress_update(session_id, progress_data)
            
            # 🔧 FIX: Add delay to ensure frontend has time to render in-progress state
            # This prevents stages from jumping immediately to checkmarks
            await asyncio.sleep(0.2)
        
        # Run research with enhanced progress tracking
        # Create custom settings if model is specified or agent models are customized
        research_settings = settings
        settings_modified = False
        
        if request.selected_model:
            # Create a copy of settings and update the default model
            import copy
            research_settings = copy.deepcopy(settings)
            research_settings.fireworks_model = f"accounts/fireworks/models/{request.selected_model}"
            settings_modified = True
        
        if request.agent_models:
            # Create a copy of settings if not already copied
            if not settings_modified:
                import copy
                research_settings = copy.deepcopy(settings)
                settings_modified = True
            
            # Update agent-specific models
            for agent_type, model_name in request.agent_models.items():
                # Check if model_name already has the prefix to avoid double-prefixing
                if model_name.startswith("accounts/fireworks/models/"):
                    full_model_name = model_name
                else:
                    full_model_name = f"accounts/fireworks/models/{model_name}"
                
                if agent_type in research_settings.agent_models:
                    # Update the model while keeping other settings
                    research_settings.agent_models[agent_type]["model"] = full_model_name
                else:
                    # Create new agent configuration with defaults
                    research_settings.agent_models[agent_type] = {
                        "model": full_model_name,
                        "max_tokens": 800,
                        "temperature": 0.3,
                        "description": f"Custom configuration for {agent_type}"
                    }
        
        # Apply executive summary style setting
        if request.executive_summary_style:
            # Create a copy of settings if not already copied
            if not settings_modified:
                import copy
                research_settings = copy.deepcopy(settings)
                research_settings.executive_summary_style = request.executive_summary_style
        
        async with EnhancedResearchSystem(research_settings) as system:
            result = await system.conduct_research(query_request, progress_callback)
            
            # 🔧 Extract pipeline data from conduct_research result (captured before end_pipeline)
            pipeline_data = result.get("pipeline_data")
            print(f"🔍 PIPELINE DATA EXTRACTION:")
            print(f"   Pipeline data exists in result: {pipeline_data is not None}")
            if pipeline_data:
                print(f"   ✅ EXTRACTED: API calls={pipeline_data['total_api_calls']}, tokens={pipeline_data['total_tokens']}")
            else:
                print(f"   ❌ NO PIPELINE DATA in result")
            
            # Mark all stages as completed
            for stage in research_stages:
                stage["status"] = "completed"
            
            # Get final metrics from the global metrics collector (will be empty after end_pipeline)
            final_metrics = metrics_collector.get_metrics_summary()
            
            # Send final completion update with proper metrics (use captured data if available)
            final_completion_data = {
                "status": "completed", 
                "stage": "completed",  # Explicit stage completion
                "progress_percentage": 100,
                "current_operation": "Research completed successfully!",
                "tokens_used": pipeline_data["total_tokens"] if pipeline_data else final_metrics.get("total_tokens", 0),
                "estimated_cost": pipeline_data["estimated_cost"] if pipeline_data else final_metrics.get("estimated_cost", 0.0),
                "api_calls_made": pipeline_data["total_api_calls"] if pipeline_data else final_metrics.get("total_api_calls", 0),
                "steps_completed": len(research_stages),  # All 5 steps completed
                "total_steps": len(research_stages),
                "stage_breakdown": research_stages,
                "research_complete": True,  # Explicit completion flag
                "keep_metrics_visible": True,  # Ensure frontend keeps the completion data visible
                # 🔧 FIX: Research plan data should come from the research planning stage progress callback
                "research_plan": stored_research_plan,  # Access the stored research plan from progress callback
                "final_metrics": {
                    "steps_completed": len(research_stages),
                    "total_steps": len(research_stages),
                    "total_api_calls": pipeline_data["total_api_calls"] if pipeline_data else final_metrics.get("total_api_calls", 0),
                    "total_tokens": pipeline_data["total_tokens"] if pipeline_data else final_metrics.get("total_tokens", 0),
                    "estimated_cost": pipeline_data["estimated_cost"] if pipeline_data else final_metrics.get("estimated_cost", 0.0),
                    "success": True,
                    "completion_time": time.time()
                }
            }
            
            print(f"🏁 FINAL COMPLETION DEBUG - API CALLS:")
            print(f"   Pipeline data captured: {pipeline_data is not None}")
            if pipeline_data:
                print(f"   Captured API calls: {pipeline_data['total_api_calls']}")
                print(f"   Captured tokens: {pipeline_data['total_tokens']}")
                print(f"   Captured cost: {pipeline_data['estimated_cost']}")
            print(f"   Final metrics total_api_calls: {final_metrics.get('total_api_calls', 0)}")
            print(f"   Sending api_calls_made in completion: {final_completion_data['api_calls_made']}")
            print(f"   Total tokens: {final_metrics.get('total_tokens', 0)}")
            print(f"   Estimated cost: {final_metrics.get('estimated_cost', 0.0)}")
            
            print(f"🏁 FINAL COMPLETION DATA DEBUG:")
            print(f"   Status: {final_completion_data['status']}")
            print(f"   Steps Completed (top-level): {final_completion_data['steps_completed']}")
            print(f"   Steps Completed (final_metrics): {final_completion_data['final_metrics']['steps_completed']}")
            print(f"   Keep Metrics Visible: {final_completion_data['keep_metrics_visible']}")
            print(f"   Research Complete Flag: {final_completion_data['research_complete']}")
            print(f"Sending final completion update: status=completed, steps={len(research_stages)}/{len(research_stages)}")
            await connection_manager.send_progress_update(session_id, final_completion_data)
            
            # Give frontend time to process the completion update
            await asyncio.sleep(0.5)
            
            return result
    
    except Exception as e:
        logger.error(f"Research failed: {e}")
        await connection_manager.send_progress_update(session_id, {
            "status": "error",
            "message": str(e),
            "stage": "error"
        })
        raise

# Additional endpoints
@app.get("/favicon.ico")
async def get_favicon():
    """Return a simple favicon response"""
    return {"message": "No favicon"}

@app.get("/manifest.json")
async def get_manifest():
    """Return a simple web app manifest"""
    return {
        "name": "Multi-Agent Research System",
        "short_name": "Research System",
        "description": "AI-powered research system with parallel processing",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4f46e5"
    }

@app.get("/api/config")
async def get_config():
    """Return basic configuration for the frontend"""
    return {
        "websocket_url": f"ws://localhost:8080/ws",
        "max_questions_limit": 10,
        "supported_formats": ["json", "html", "pdf"],
        "search_engine": {
            "preferred": getattr(settings, 'preferred_search_engine', 'brave'),
            "firecrawl_available": bool(getattr(settings, 'firecrawl_api_key', None)),
            "brave_available": bool(getattr(settings, 'brave_api_key', None)),
            "content_extraction_enabled": getattr(settings, 'enable_content_extraction', True),
            "max_content_length": getattr(settings, 'max_content_length', 10000),
            "firecrawl_timeout": getattr(settings, 'firecrawl_timeout', 120),
            "firecrawl_max_results": getattr(settings, 'firecrawl_max_results', 10)
        }
    }

@app.get("/api/models")
async def get_available_models():
    """Get list of available models with pricing (legacy endpoint for backward compatibility)"""
    # Import with fallback handling
    try:
        from backend.enhanced_research_system import ModelManager
    except (ImportError, ModuleNotFoundError):
        try:
            from enhanced_research_system import ModelManager
        except (ImportError, ModuleNotFoundError):
            from .enhanced_research_system import ModelManager
    
    try:
        model_manager = ModelManager(settings)
        
        # Format models for the frontend
        formatted_models = []
        for model_id, pricing in model_manager.model_costs.items():
            # Determine category based on pricing
            input_cost = pricing["input"]
            if input_cost <= 0.3:
                category = "budget"
            elif input_cost <= 1.0:
                category = "mid-range"
            else:
                category = "premium"
            
            # Create display name from model ID
            display_name = model_id.replace("-", " ").title()
            
            formatted_models.append({
                "id": model_id,
                "display_name": display_name,
                "category": category,
                "pricing": {
                    "input": pricing["input"],
                    "output": pricing["output"],
                    "currency": "USD",
                    "unit": "per 1M tokens"
                }
            })
        
        # Sort by category and then by price
        category_order = {"budget": 1, "mid-range": 2, "premium": 3}
        formatted_models.sort(key=lambda x: (category_order.get(x["category"], 4), x["pricing"]["input"]))
        
        return {
            "models": formatted_models,
            "default_model": settings.fireworks_model.split('/')[-1]
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return {
            "models": [],
            "default_model": "llama-v3p1-8b-instruct",
            "error": str(e)
        }

@app.get("/api/models/config")
async def get_model_configuration():
    """Get the current multi-model configuration showing agent-specific assignments"""
    # Import with fallback handling
    try:
        from backend.enhanced_research_system import ModelManager
    except (ImportError, ModuleNotFoundError):
        try:
            from enhanced_research_system import ModelManager
        except (ImportError, ModuleNotFoundError):
            from .enhanced_research_system import ModelManager
    
    try:
        model_manager = ModelManager(settings)
        
        # Get agent model assignments
        agent_assignments = []
        for agent_type, config in settings.agent_models.items():
            model_name = config['model'].split('/')[-1]
            
            # Get pricing for this model
            pricing = model_manager.model_costs.get(model_name, {"input": 0, "output": 0})
            
            agent_assignments.append({
                "agent_type": agent_type,
                "agent_display_name": agent_type.replace('_', ' ').title(),
                "model": model_name,
                "model_display_name": model_name.replace("-", " ").title(),
                "model_name": model_name,  # Clean model name for frontend
                "max_tokens": config['max_tokens'],
                "temperature": config['temperature'],
                "description": config['description'],
                "pricing": pricing
            })
        
        # Get cost summary if available
        cost_summary = model_manager.get_cost_summary()
        
        # Get available models for dropdowns (only clean model names)
        available_models = sorted(list(model_manager.model_costs.keys()))
        
        # Agent assignments already include model_name field
        
        return {
            "success": True,  # Frontend expects this field
            "multi_model_enabled": True,
            "agent_assignments": agent_assignments,
            "available_models": available_models,  # Frontend expects this field
            "model_pricing": model_manager.model_costs,  # Frontend expects this field
            "default_model": settings.fireworks_model.split('/')[-1],
            "budget_limit": settings.max_cost_per_query,
            "cost_summary": cost_summary,
            "total_agents": len(agent_assignments)
        }
    except Exception as e:
        logger.error(f"Error getting model configuration: {e}")
        return {
            "success": False,  # Frontend expects this field
            "multi_model_enabled": False,
            "error": str(e),
            "agent_assignments": [],
            "available_models": [],
            "model_pricing": {},
            "default_model": settings.fireworks_model.split('/')[-1] if hasattr(settings, 'fireworks_model') else "unknown"
        }

@app.post("/api/models/config")
async def update_model_configuration(request: ModelConfigUpdateRequest):
    """Update the agent-specific model configuration"""
    # Import with fallback handling
    try:
        from backend.enhanced_research_system import ModelManager
    except (ImportError, ModuleNotFoundError):
        try:
            from enhanced_research_system import ModelManager
        except (ImportError, ModuleNotFoundError):
            from .enhanced_research_system import ModelManager
    
    try:
        # Validate that all provided models exist
        model_manager = ModelManager(settings)
        available_models = set(model_manager.model_costs.keys())
        
        invalid_models = []
        for agent_type, model_name in request.agent_models.items():
            # Remove prefix if present for validation
            clean_model_name = model_name.replace("accounts/fireworks/models/", "")
            if clean_model_name not in available_models:
                invalid_models.append(f"{agent_type}: {clean_model_name}")
        
        if invalid_models:
            return {
                "success": False,
                "error": f"Invalid models specified: {', '.join(invalid_models)}",
                "available_models": list(available_models)
            }
        
        # Update the agent model configurations
        for agent_type, model_name in request.agent_models.items():
            # Check if model_name already has the prefix to avoid double-prefixing
            if model_name.startswith("accounts/fireworks/models/"):
                full_model_name = model_name
            else:
                full_model_name = f"accounts/fireworks/models/{model_name}"
            
            if agent_type in settings.agent_models:
                # Update the model while keeping other settings
                settings.agent_models[agent_type]["model"] = full_model_name
            else:
                # Create new agent configuration with defaults
                settings.agent_models[agent_type] = {
                    "model": full_model_name,
                    "max_tokens": 800,
                    "temperature": 0.3,
                    "description": f"Custom configuration for {agent_type}"
                }
        
        # Get updated configuration
        updated_config = await get_model_configuration()
        
        return {
            "success": True,
            "message": "Model configuration updated successfully",
            "updated_config": updated_config
        }
        
    except Exception as e:
        logger.error(f"Error updating model configuration: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/research/{session_id}/export/html")
async def export_html(session_id: str):
    """Export research results as HTML"""
    try:
        # Load results from database
        async with EnhancedResearchSystem(settings) as system:
            session_data = system.db_manager.load_session(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Extract the final report from session data
            if 'data' in session_data and 'final_report' in session_data['data']:
                report_data = session_data['data']['final_report']
                
                # Generate HTML report using the function from main.py
                try:
                    from backend.main import generate_html_report
                except (ImportError, ModuleNotFoundError):
                    try:
                        from main import generate_html_report
                    except (ImportError, ModuleNotFoundError):
                        from .main import generate_html_report
                html_content = generate_html_report(report_data)
                
                # Save to organized directory structure
                query = session_data.get('query', 'research')
                html_filepath = get_organized_report_path(session_id, 'html', query)
                html_filepath.write_text(html_content, encoding='utf-8')
                
                # Create index entry
                create_report_index_entry(
                    html_filepath, session_id, query, 'html',
                    session_data.get('metadata', {})
                )
                
                return HTMLResponse(
                    content=html_content,
                    headers={
                        "Content-Disposition": f"attachment; filename={html_filepath.name}"
                    }
                )
            else:
                raise HTTPException(status_code=400, detail="Final report not found in session data")
    
    except Exception as e:
        logger.error(f"Failed to export HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/{session_id}/export/pdf")
async def export_pdf(session_id: str):
    """Export research results as PDF"""
    try:
        # Load results from database
        async with EnhancedResearchSystem(settings) as system:
            session_data = system.db_manager.load_session(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Extract the final report from session data
            if 'data' in session_data and 'final_report' in session_data['data']:
                report_data = session_data['data']['final_report']
                
                # Generate PDF report using the function from main.py
                try:
                    from backend.main import generate_pdf_report
                except (ImportError, ModuleNotFoundError):
                    try:
                        from main import generate_pdf_report
                    except (ImportError, ModuleNotFoundError):
                        from .main import generate_pdf_report
                query = session_data.get('query', 'research')
                pdf_filepath = generate_pdf_report(report_data, session_id, query)
                
                # Create index entry
                create_report_index_entry(
                    pdf_filepath, session_id, query, 
                    'pdf' if pdf_filepath.suffix == '.pdf' else 'html',
                    session_data.get('metadata', {})
                )
                
                # Check if the generated file is actually a PDF or HTML fallback
                if pdf_filepath.suffix == '.pdf':
                    # Read the PDF file and return it
                    with open(pdf_filepath, 'rb') as pdf_file:
                        pdf_content = pdf_file.read()
                    
                    return Response(
                        content=pdf_content,
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": f"attachment; filename={pdf_filepath.name}"
                        }
                    )
                else:
                    # PDF generation failed, fallback generated HTML
                    # Return HTML file with proper content type
                    with open(pdf_filepath, 'r', encoding='utf-8') as html_file:
                        html_content = html_file.read()
                    
                    return HTMLResponse(
                        content=html_content,
                        headers={
                            "Content-Disposition": f"attachment; filename={pdf_filepath.name}"
                        }
                    )
            else:
                raise HTTPException(status_code=400, detail="Final report not found in session data")
    
    except Exception as e:
        logger.error(f"Failed to export PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_web_ui(host: str = "0.0.0.0", port: int = 8080, reload: bool = False):
    """Run the web UI server"""
    uvicorn.run(
        "web_ui:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Agent Research System Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print(f"""
🚀 Multi-Agent Research System Web UI
=====================================

Starting server on http://{args.host}:{args.port}

Features:
✅ Real-time progress tracking
✅ Interactive research configuration  
✅ Beautiful results visualization
✅ Multiple export formats (PDF, HTML, JSON)
✅ Session management and history
✅ Intelligent parallel processing visualization

""")
    
    run_web_ui(host=args.host, port=args.port, reload=args.reload) 