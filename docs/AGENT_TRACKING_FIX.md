# Agent Tracking & Enhanced Stage Data Display Fix

## Issues Fixed

### 1. ❌ **Agent showing as "Unknown"**
The progress callbacks weren't passing agent information, so all stages showed "Unknown" agent.

### 2. ❌ **Limited stage data display**
Stages only showed basic information without meaningful metrics like model used, cost, sources found, etc.

## Root Cause
1. **Progress callback signature mismatch**: The web UI expected agent info but main.py wasn't passing it
2. **Incomplete metrics tracking**: Rich stage data wasn't being collected and displayed meaningfully

## Solutions Implemented

### ✅ **Backend Progress Callback Enhancement**

#### **Updated Progress Callback Signature**
```python
# OLD: async def progress_callback(stage, percentage, operation, stage_index=None, research_plan=None)
# NEW: async def progress_callback(stage, percentage, operation, stage_index=None, research_plan=None, agent=None)
```

#### **Enhanced Stage Data Collection** (`web_ui.py`)
```python
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
```

#### **Updated Main.py Progress Calls**
```python
# Research Planning
await progress_callback("research_planning", 10, "Creating research plan...", 0, None, "ResearchPlannerAgent")
await progress_callback("research_planning", 20, "Research plan created successfully", 0, research_plan_dict, "ResearchPlannerAgent")

# Information Gathering  
await progress_callback("information_gathering", 25, "Gathering information from web sources...", 1, None, "WebSearchRetrieverAgent")

# Quality Evaluation
await progress_callback("quality_evaluation", 50, "Evaluating information quality and relevance...", 2, None, "QualityEvaluationAgent")

# Content Summarization
await progress_callback("content_summarization", 70, "Analyzing and summarizing content...", 3, None, "ContentSummarizerAgent")

# Report Assembly
await progress_callback("report_assembly", 85, "Assembling final research report...", 4, None, "ReportSynthesizerAgent")
```

### ✅ **Frontend Enhanced Stage Display**

#### **Rich StageCard Component** (`App.jsx`)

**Now Shows:**
- **Agent Information**: 🤖 ResearchPlanner (instead of "Unknown")
- **Performance Metrics**: Color-coded cards for tokens, API calls, duration, cost
- **Additional Details**: Model used, sources found
- **Progress Visualization**: Per-stage progress bars
- **Timestamps**: Last updated times

#### **Three-Tier Information Display:**

1. **Primary Details**
   - Current Operation  
   - Progress Percentage with visual bar
   - Agent with robot icon
   - Last Updated timestamp

2. **Performance Metrics** (color-coded cards)
   - 🟢 **Tokens**: Green cards showing token usage
   - 🟣 **API Calls**: Purple cards showing call count  
   - 🔵 **Duration**: Blue cards showing time elapsed
   - 🟡 **Cost**: Yellow cards showing cost so far

3. **Additional Details**
   - **Model Used**: Shows the actual model (e.g., `llama-v3p1-405b-instruct`)
   - **Sources Found**: Number of sources discovered
   - **Other metrics**: Expandable for future additions

#### **Visual Improvements**
- ✅ Robot icons for agents
- ✅ Color-coded metric cards  
- ✅ Progress bars per stage
- ✅ Expandable/collapsible details
- ✅ Clean, organized layout
- ✅ Proper agent name formatting (removes "Agent" suffix)

## Agent Mapping

| Stage | Agent | Purpose |
|-------|-------|---------|
| Research Planning | ResearchPlannerAgent | Creates research strategy & sub-questions |
| Information Gathering | WebSearchRetrieverAgent | Searches web sources for information |  
| Quality Evaluation | QualityEvaluationAgent | Evaluates information quality & relevance |
| Content Summarization | ContentSummarizerAgent | Analyzes and summarizes content |
| Report Assembly | ReportSynthesizerAgent | Assembles final research report |

## Example Enhanced Display

**Before:**
```
Research Planning
Agent: Unknown
Progress: 20%
```

**After:**
```
🤖 Research Planner
Current Operation: Research plan created successfully  
Progress: [████████████████████] 20%
Last Updated: 12:20:22 AM

Performance Metrics:
🟢 1,234 Tokens  🟣 3 API Calls  🔵 2.3s Duration  🟡 $0.0045 Cost

Additional Details:
Model Used: llama-v3p1-405b-instruct
Sources Found: 15 sources
```

## Result: Rich, Meaningful Stage Data! 🎉

Users now see:
- ✅ **Real agent names** instead of "Unknown"
- ✅ **Detailed performance metrics** in organized, color-coded cards
- ✅ **Model information** showing which AI model is being used
- ✅ **Cost tracking** showing real-time expenses
- ✅ **Source counts** showing research progress
- ✅ **Professional presentation** with icons and proper formatting

The research pipeline now provides comprehensive, real-time visibility into what each agent is doing and how the research is progressing! 