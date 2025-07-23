# 🔬 Multi-Agent Research System

A sophisticated AI-powered research platform that orchestrates multiple specialized agents with **multi-model architecture** to conduct comprehensive research on any topic. Built with FastAPI and modern React frontend, featuring real-time progress tracking, comprehensive cost tracking, and advanced AI model management.

## ✨ Key Features

### 🚀 **Modern Architecture (Recently Optimized)**
- **Modular Agent Architecture**: Complete agent system refactoring with individual agent files in `agents/` package
- **Refactored Backend**: 90% complexity reduction in main research pipeline (600+ line monolith → clean orchestration)
- **Separated Frontend**: Modern React + Vite build system for 5-10x performance improvement
- **Centralized State Management**: ResearchContext with useReducer pattern for predictable state updates
- **Production-Ready Code**: Clean, maintainable architecture following professional best practices
- **Component-Based UI**: Modular, maintainable frontend architecture
- **Real-time WebSocket**: Live progress tracking and model usage display
- **Recent Bug Fix**: Fixed sub-question count issue - user dropdown selection now properly respected

### 🤖 Multi-Model Architecture
- **Agent-Specific AI Models**: Each agent uses optimized models for their specific tasks
- **Centralized Pricing System**: Unified cost calculation across all models and agents
- **ModelManager**: Comprehensive cost tracking and budget monitoring per agent/model
- **Model Selection Strategies**: Single, adaptive, cost-optimized, or performance-optimized
- **Real-time Cost Tracking**: Accurate token usage and API costs with budget limits
- **18+ Supported Models**: Including Llama, Qwen, DeepSeek, Mistral, and more (Fireworks AI)

### 🎯 Specialized AI Agents (Modular Architecture)
- **Research Planner Agent**: Creates strategic research plans (uses reasoning-optimized models) - `backend/agents/research_planner.py`
- **Web Search Retriever Agent**: Gathers information from multiple sources (uses fast, efficient models) - `backend/agents/web_search_retriever.py`
- **Quality Evaluator Agent**: Validates and scores information quality (uses analytical models) - `backend/agents/quality_evaluator.py`
- **Summarizer Agent**: Processes and synthesizes findings (uses synthesis-optimized models) - `backend/agents/summarizer.py`
- **Report Synthesizer Agent**: Generates comprehensive final reports (uses writing-optimized models) - `backend/agents/report_synthesizer.py`
- **Base Agent**: Common functionality and model management - `backend/agents/base_agent.py`

### 🚀 Advanced Capabilities
- **Adaptive Source Filtering**: Intelligent filtering with 5 strategies (recently fixed 0% filtering bug - now properly filters 20-40% of sources)
- **Real-time Progress Tracking**: WebSocket-based live updates with model usage display
- **Comprehensive Metrics**: Token usage, costs, performance analytics per agent and model
- **Multiple Output Formats**: JSON, HTML, PDF reports with organized file structure
- **Intelligent Caching**: Redis-based performance optimization with semantic similarity
- **Smart Rate Limiting**: Dynamic throttling to prevent API overload
- **Session Persistence**: SQLite database for session management and resumption

### 🎯 Key Highlights
- **5-Stage Pipeline**: Planning → Gathering → Quality Check → Analysis → Synthesis
- **Dynamic Research Plans**: AI-generated sub-questions and strategies
- **Quality Assessment**: Comprehensive evaluation of information reliability with LLM integration
- **Professional Report Generation**: Comprehensive final reports with executive summaries, detailed findings, recommendations, and methodology (2500+ token synthesis)
- **Modern Web UI**: React-based interface with real-time model selection, cost monitoring, and beautiful report display
- **Advanced CLI**: Comprehensive command-line interface with model management
- **Performance Optimized**: Intelligent parallel processing with rate-limit safety

## 🏗️ Architecture

### High-Level Overview
```
    📝 Query Input
         │
    ┌────▼────┐
    │ 🧠 Plan │ ──→ Research Strategy + Sub-questions
    └────┬────┘
         │
    ┌────▼────┐
    │ 🔍 Gather│ ──→ Multi-source Web Search + AI Filtering  
    └────┬────┘
         │
    ┌────▼────┐
    │ ✅ Evaluate│ ──→ Quality Assessment + Reliability Scoring
    └────┬────┘
         │
    ┌────▼────┐
    │ 📊 Analyze│ ──→ Content Summarization + Key Insights
    └────┬────┘
         │
    ┌────▼────┐
    │ 📝 Synthesize│ ──→ Final Research Report
    └─────────┘

🤖 Multi-Model AI: Each stage uses specialized models optimized for the task
💰 Centralized Pricing: Unified cost calculation and real-time budget monitoring
🎯 Quality Control: Adaptive filtering and validation at every step
```

### Modern Frontend Architecture
```
🌐 Frontend (React + Vite)
├── 📱 Modern UI Components
│   ├── Research Form & Model Selection
│   ├── Real-time Progress Tracking
│   ├── Cost Monitoring Dashboard
│   └── Results Display & Export
├── 🔄 Real-time Updates (WebSocket)
├── 🏗️ Centralized State Management (ResearchContext)
├── 📊 Performance Optimized (Production Build)
└── 🎯 Component-Based Architecture

🔗 FastAPI Backend
├── 🤖 Multi-Agent Pipeline
├── 💰 Centralized Pricing System
├── 📊 Metrics Collection
└── 🗄️ Session Management
```

### Detailed Technical Architecture
<details>
<summary>Click to expand technical details</summary>

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    🌐 Modern React Frontend + CLI Interface                     │
│  • Component-based UI  • Real-time WebSocket  • Cost monitoring               │
│  • Model selection     • Progress tracking    • 5-10x performance             │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────────────────────┐
│                      🎯 Enhanced Research System                                │
│  • Session management  • Progress tracking  • Error handling                   │
│  • WebSocket integration  • Real-time updates  • Performance optimization     │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
┌─────────▼─┐  ┌──────▼──────┐  ┌▼─────────────┐
│🤖 Model   │  │📊 Metrics   │  │🔒 Security   │
│Manager    │  │Collector    │  │Manager       │
│           │  │             │  │              │
│• 18+ Models│  │• Token Usage│  │• Encryption  │
│• Cost Track│  │• API Costs  │  │• Validation  │
│• Budget Mon│  │• Performance│  │• Rate Limits │
│• Pricing.py│  │• Real-time  │  │• 404 Handling│
└─────────┬─┘  └──────┬──────┘  └┬─────────────┘
          │           │           │
          └───────────┼───────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │         🎭 AI Agent Pipeline      │
    │                                   │
    │  ┌──────────────────────────────┐ │
    │  │ 🧠 Research Planner Agent    │ │ ──→ Llama-v3p3-70B (Default)
    │  │   • Query analysis           │ │
    │  │   • Strategy creation        │ │
    │  │   • Sub-question generation  │ │
    │  └──────────────────────────────┘ │
    │              │                    │
    │  ┌───────────▼──────────────────┐ │
    │  │ 🔍 Web Search Retriever      │ │ ──→ Llama-v3p1-8B (Default)
    │  │   • Multi-source search      │ │
    │  │   • Intelligent parallel     │ │
    │  │   • Adaptive filtering       │ │
    │  └──────────────────────────────┘ │
    │              │                    │
    │  ┌───────────▼──────────────────┐ │
    │  │ ✅ Quality Evaluation Agent  │ │ ──→ Llama-v3p3-70B (Default)
    │  │   • Information validation   │ │
    │  │   • Reliability scoring      │ │
    │  │   • Confidence assessment    │ │
    │  └──────────────────────────────┘ │
    │              │                    │
    │  ┌───────────▼──────────────────┐ │
    │  │ 📊 Summarizer Agent          │ │ ──→ Llama-v3p3-70B (Default)
    │  │   • Data processing          │ │
    │  │   • Key insight extraction   │ │
    │  │   • Parallel summarization   │ │
    │  └──────────────────────────────┘ │
    │              │                    │
    │  ┌───────────▼──────────────────┐ │
    │  │ 📝 Report Synthesizer Agent  │ │ ──→ Llama-v3p3-70B (Default)
    │  │   • Final report assembly    │ │
    │  │   • Executive summary        │ │
    │  │   • Recommendations          │ │
    │  └──────────────────────────────┘ │
    └─────────────────┬─────────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │      🗄️ Infrastructure Layer      │
    │                                   │
    │ ┌─────────┐ ┌─────────┐ ┌───────┐ │
    │ │📚 Cache │ │🗃️ SQLite│ │🌐 APIs│ │
    │ │ System  │ │Database │ │       │ │
    │ │         │ │         │ │• Brave│ │
    │ │• Redis  │ │• Sessions│ │• FW AI│ │
    │ │• Local  │ │• Reports │ │• Rate │ │
    │ │• Smart  │ │• Metrics │ │  Limit│ │
    │ └─────────┘ └─────────┘ └───────┘ │
    └───────────────────────────────────┘

🎯 Recent Enhancements:
• Modern React + Vite frontend with 5-10x performance improvement
• Major code cleanup & optimization in v2.1.0 (9.3% line reduction, unified patterns)
• Centralized pricing system (pricing.py) for unified cost calculation
• Enhanced error handling for model availability (404 errors)
• Real-time WebSocket updates with live progress tracking
• Improved model management with 18+ Fireworks AI models
• Consistent $X.XXXX cost formatting across all interfaces
• Component-based UI architecture for better maintainability
• New core/ module architecture with unified response parsing, error handling, and quality assessment

**🔧 Model Configuration:**
- **Default Models**: As shown in diagram above (configured in `config.py`)
- **Fallback Model**: `llama-v3p1-8b-instruct` (used when agent-specific models fail)
- **Strategy**: `adaptive` - Uses agent-specific models with intelligent fallback
- **User Override**: Models can be changed via UI dropdown for individual research sessions
```
</details>

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for frontend development)
- Redis (optional, for caching)
- API Keys: Fireworks AI, and either Brave Search or Firecrawl (Firecrawl preferred)
- Firecrawl MCP tools (optional, for enhanced content extraction - install via MCP if using with Claude/Cursor)

### ⚡ UV Installation (Recommended - 10x Faster!)

1. **One-command setup**
   ```bash
   git clone <your-repo-url>
   cd Multi_agent_research_system
   ./setup.sh
   ```

2. **Configure API keys**
   ```bash
   # Edit .env with your API keys
   nano .env
   ```

3. **Start using**
   ```bash
   # Web UI with modern React frontend
   make web
   # or ./run-web.sh
   
   # CLI with cost tracking
   make cli QUERY="Your research question"
   # or ./run-cli.sh "Your research question"
   ```

📖 **[Complete UV Setup Guide](./UV_SETUP.md)** - Detailed instructions and troubleshooting

> **✨ Modern Tech Stack**: This project uses React + Vite for the frontend and `pyproject.toml` for Python dependency management, providing optimal performance and developer experience.

### Frontend Development

```bash
# Frontend development (if modifying UI)
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run build:prod   # Optimized production build
```

### Traditional pip Installation

1. **Clone and install**
   ```bash
   git clone <your-repo-url>
   cd Multi_agent_research_system
   pip install -e .
   ```

2. **Build frontend**
   ```bash
   cd frontend
   npm install && npm run build:prod
   cd ..
   ```

3. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and model preferences
   ```

4. **Start the system**
   ```bash
   # Web UI (Recommended)
   python start_web_ui.py
   
   # CLI
   python main.py research "Your research question"
   ```

> **Note**: The frontend is pre-built and included in the repository. You only need Node.js if you plan to modify the UI components.

## 📖 Usage

### Web Interface
1. Navigate to `http://localhost:8080`
2. **Select AI models** for each agent type (Research Planner, Web Search, etc.)
3. **Set budget limits** and monitor costs in real-time
4. Enter your research query
5. Watch real-time progress through the 5-stage pipeline
6. View comprehensive results with **model usage breakdown** and cost analysis

### Command Line Interface

#### Basic Research
```bash
# Basic research with default models
python main.py research "Latest developments in AI"

# Advanced options with model optimization
python main.py research "Climate change impacts" \
  --max-questions 7 \
  --output-format pdf \
  --save-session \
  --executive-summary-style comprehensive
```

#### Model Management
```bash
# View current model configuration
python main.py models --show-config

# View model pricing information
python main.py models --show-costs

# View recent usage statistics
python main.py models --show-usage
```

#### Advanced Features
```bash
# Test adaptive source filtering
python main.py test-filtering --query "AI safety research" --test-strategies

# Health check with model status
python main.py health

# Session management
python main.py sessions --list-sessions
python main.py sessions --session-id <session-id>

# Report management
python main.py reports --summary
python main.py reports --list-reports --format pdf
python main.py reports --cleanup 30  # Clean reports older than 30 days
```

#### Development Commands
```bash
# Using Makefile (recommended)
make setup          # Initial setup
make web            # Start web UI
make cli QUERY="AI trends"  # Run CLI research
make test           # Run tests
make health         # Health check
make clean          # Clean up build artifacts
```

## 📊 Pipeline Stages

1. **🧠 Research Planning** - Query analysis and strategy creation with reasoning-optimized AI
2. **🔍 Information Gathering** - **Dual search engine support** with intelligent fallback:
   - **Firecrawl** (preferred): Full content extraction, markdown format, main content filtering
   - **Brave Search** (fallback): Fast API-based search with snippet extraction
   - **Auto-switching**: Uses Firecrawl when available, falls back to Brave Search automatically
3. **✅ Quality Evaluation** - Information validation and reliability scoring with analytical AI
4. **📊 Content Summarization** - Data processing and synthesis with synthesis-optimized AI
5. **📝 Report Assembly** - Final report generation with writing-optimized AI

## 🔧 Configuration

### Multi-Model Configuration
```env
# Model Selection Strategy
RESEARCH_MODEL_SELECTION_STRATEGY=adaptive  # single|adaptive|cost_optimized|performance_optimized

# Cost and Budget Controls
RESEARCH_MAX_COST_PER_QUERY=0.50  # Maximum cost per research query (USD)
RESEARCH_PERFORMANCE_VS_COST_WEIGHT=0.7  # 1.0=max performance, 0.0=min cost

# Agent-Specific Model Overrides (optional)
RESEARCH_RESEARCH_PLANNER_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
RESEARCH_WEB_SEARCH_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct
RESEARCH_QUALITY_EVALUATION_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
RESEARCH_SUMMARIZATION_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
RESEARCH_REPORT_SYNTHESIS_MODEL=accounts/fireworks/models/llama-v3p1-70b-instruct
```

### 🎯 **NEW: Model Presets (Web UI)**
The Web UI now includes intelligent model presets that automatically configure optimal models for each agent based on cost-performance balance:

**🟢 Budget Preset** (~$0.20/1M tokens)
- Task-optimized budget models: `qwen3-8b`, `qwen2-7b-instruct`, `llama-v3p1-8b-instruct`
- Research Planner gets better reasoning model, Web Search stays fast

**🔵 Balanced Preset** (~$0.15-0.90/1M tokens)  
- Balanced performance: `qwen3-30b-a3b`, `llama4-scout-instruct-basic`, `qwen3-235b-a22b`
- Good cost-performance ratio with task specialization

**🟣 Performance Preset** (~$0.90/1M tokens)
- High-quality models: `qwq-32b`, `llama-v3p3-70b-instruct`, `qwen2p5-72b-instruct`
- Advanced reasoning models for complex research

**🔴 Premium Preset** ($1.20+ per 1M tokens)
- Best available models: `deepseek-r1-basic`, `deepseek-r1`, `llama-v3p1-405b-instruct`
- Maximum quality for critical research

**Usage**: Click preset buttons between "Max Sub-Questions" and "Agent Models" sections in the Web UI. Each preset assigns different models to different agents based on their specific tasks.

### Essential Settings
```env
# Required API Keys
FIREWORKS_API_KEY=your_fireworks_key

# Search Engine Configuration (Choose your preferred search engine)
BRAVE_API_KEY=your_brave_search_key                    # Optional: For Brave Search
FIRECRAWL_API_KEY=your_firecrawl_api_key              # Optional: For Firecrawl (preferred)

# Search Engine Preferences
PREFERRED_SEARCH_ENGINE=firecrawl     # firecrawl|brave|auto (auto tries Firecrawl first)
ENABLE_CONTENT_EXTRACTION=true       # Enable full content extraction (requires Firecrawl)
MAX_CONTENT_LENGTH=2500              # Maximum content length per source (optimized for performance)

# Firecrawl Configuration (when using Firecrawl) - Optimized Settings
FIRECRAWL_TIMEOUT=120                    # Search and scrape timeout (seconds)
FIRECRAWL_MAX_RESULTS=3                  # Maximum search results (optimized for quality)
FIRECRAWL_SCRAPE_TIMEOUT=15              # Individual page scraping timeout (optimized)
FIRECRAWL_CONTENT_LIMIT=2500             # Content limit per source (optimized)
FIRECRAWL_PARALLEL_SCRAPING=true         # Enable parallel scraping for 3x speed boost
FIRECRAWL_ENABLE_MARKDOWN=true           # Extract content as markdown
FIRECRAWL_ONLY_MAIN_CONTENT=true         # Filter out navigation/footer content

# Performance Settings
RESEARCH_MAX_PARALLEL_SEARCHES=3
RESEARCH_MAX_PARALLEL_SUMMARIES=2
RESEARCH_BATCH_SIZE=3

# Adaptive Source Filtering
RESEARCH_PREFERRED_FILTERING_STRATEGY=balanced  # conservative|balanced|aggressive|domain_diversity|percentile_based
RESEARCH_ENABLE_SOURCE_FILTERING=true

# Caching
REDIS_URL=redis://localhost:6379
ENABLE_CACHE=true

# Web UI
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=8080

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

## 📁 Project Structure

```
Multi_agent_research_system/
├── 🌐 Frontend (Modern React + Vite)
│   ├── src/
│   │   ├── components/          # UI components
│   │   ├── hooks/              # React hooks
│   │   ├── utils/              # Frontend utilities
│   │   └── constants/          # Constants and config
│   ├── dist/                   # Production build
│   ├── package.json           # Frontend dependencies
│   └── vite.config.js         # Build configuration
├── 🐍 Backend (Python)
│   ├── main.py                # CLI entry point
│   ├── web_ui.py              # Web API server
│   ├── enhanced_research_system.py  # Core agents and logic
│   ├── config.py              # Configuration management
│   ├── pricing.py             # Centralized pricing system
│   ├── utils.py               # Backend utilities
│   └── exceptions.py          # Custom exceptions
├── 🔧 Configuration & Setup
│   ├── pyproject.toml         # Python dependencies
│   ├── env.example           # Environment template
│   ├── setup.sh              # UV-based setup
│   ├── Makefile              # Development automation
│   └── UV_SETUP.md           # Setup guide
├── 📊 Data & Exports
│   ├── exports/              # Organized report outputs
│   ├── tests/                # Test files
│   ├── scripts/              # Utility scripts
│   └── examples/             # Example outputs
└── 📚 Documentation & Training
    ├── README.md             # This file
    ├── courses/              # Educational materials and courses
    │   └── COURSE_Multi_Agent_Research_Systems.md  # Complete implementation course
    └── docs/                 # Development notes and technical documentation
        ├── optimization_summary.md      # Recent system improvements
        ├── filtering_improvements.md    # Source filtering fixes
        ├── demo_enhanced_sources_ui.md  # UI enhancement details
        └── development-notes.md         # General development notes
```

## 🧪 Testing

```bash
# Run comprehensive tests
make test
# or
python tests/simple_test.py
python tests/full_system_test.py

# Test specific features
python main.py test-filtering --query "AI safety" --show-analysis
python main.py health
```

## 📈 Metrics & Monitoring

The system provides comprehensive metrics with multi-model tracking:

### Real-time Metrics
- **Centralized Cost Tracking**: Unified pricing system across all models and agents
- **Token Usage**: Detailed breakdown by agent and model
- **Performance**: Response times, throughput, cache efficiency
- **Quality Scores**: Information reliability and confidence metrics
- **Budget Monitoring**: Real-time cost tracking with limits

### Model Usage Analytics
- **Agent Performance**: Individual agent metrics and optimization
- **Model Efficiency**: Cost-per-token analysis across models
- **Usage Patterns**: Historical usage and optimization recommendations
- **Cache Efficiency**: Hit rates and performance gains

### Available Metrics Commands
```bash
python main.py models --show-usage    # Recent model usage
python main.py sessions --list-sessions  # Session history with costs
python main.py reports --summary      # Report generation statistics
```

## 🔍 Advanced Features

### Modern Frontend Performance
- **React Production Build**: Optimized bundle size and fast loading
- **Component Memoization**: Efficient re-rendering and memory usage
- **Real-time Updates**: WebSocket-based live progress tracking
- **Responsive Design**: Modern UI that works on all devices

### Centralized Pricing System
- **Unified Cost Calculation**: Single source of truth for all model pricing
- **DRY Principles**: Eliminated duplicate pricing dictionaries
- **Easy Maintenance**: Single file to update when model prices change
- **Accurate Cost Display**: Consistent $X.XXXX format across all interfaces

### Adaptive Source Filtering
- **5 Filtering Strategies**: Conservative, balanced, aggressive, domain diversity, percentile-based
- **Recently Fixed**: Resolved critical 0% filtering bug - now properly filters 20-40% of sources based on quality
- **Enhanced UI**: Shows accepted/rejected sources with clear explanations and visual tabs
- **Quality Integration**: Uses LLM quality assessment scores that properly flow to Summary confidence levels
- **Realistic Scoring**: Dynamic content quality calculation instead of hardcoded 90% scores
- **Safety Limits**: Prevents over-filtering with configurable minimums

### Multi-Model Optimization
- **Cost-Performance Balance**: Automatically selects optimal models based on budget and performance requirements
- **Agent Specialization**: Each agent uses models optimized for their specific tasks
- **Budget Management**: Real-time cost tracking with automatic fallback to cheaper models
- **Model Alternatives**: Automatic cost-optimized alternatives for expensive models

## 🚀 Recent Improvements

### ✅ **Phase 3 Complete: Model Presets & UI Polish (Latest)**
- **🎯 Model Presets**: Added intelligent model preset system with 4 cost-performance tiers (Budget, Balanced, Performance, Premium)
- **🧠 Task-Specific Assignment**: Each preset assigns optimal models to different agents based on their specific tasks and capabilities
- **💰 Cost-Optimized Selection**: Presets automatically select best available models with intelligent fallback system
- **🖥️ Modal Improvements**: Fixed modal positioning issues - modals now stay within screen bounds with proper scrolling on all devices
- **📱 Responsive Design**: Enhanced modal system with better viewport handling for mobile, tablet, and desktop
- **🎨 Better UX**: Preset buttons provide instant model configuration without manual dropdown selection

### ✅ **Phase 2 Complete: Enhanced Report Generation & UI Polish**
- **📋 Fixed Report Assembly Display**: Resolved critical issue where Report Assembly showed "N/A" and "0" values instead of proper final report data
- **📜 Executive Summary Integration**: Fixed missing executive summary display with enhanced fallback generation and robust AI response parsing
- **🎯 Enhanced Token Limits**: Increased report synthesis from 1000 to 2500 tokens for more comprehensive executive summaries, methodology, and recommendations
- **🎨 Streamlined User Interface**: Removed redundant raw JSON results section, renamed to "Performance Analytics" with clear separation from research findings
- **📱 Cleaner Stage View**: Research Pipeline stages now start collapsed by default for less overwhelming initial experience
- **💎 Beautiful Report Display**: Comprehensive final report UI with executive summary, detailed findings, recommendations, methodology, and limitations in professional layout
- **🔄 Improved Data Flow**: Enhanced progress callbacks and WebSocket communication to ensure final report data reaches frontend correctly

### ✅ **Phase 1 Complete: Critical System Fixes & Performance**
- **🔧 Fixed 0% Source Filtering Bug**: Resolved critical issue where no sources were being filtered despite poor quality (159-character content was passing through)
- **📊 Quality Assessment Integration**: Quality Assessment scores now properly flow into Summary confidence levels and final report quality scores
- **🎯 Enhanced Source Discovery UI**: Added comprehensive accepted/rejected source visualization with clear explanations and visual distinction
- **📈 Realistic Content Quality Scoring**: Replaced hardcoded 90% quality scores with dynamic calculation based on content length, structure, and relevance
- **📝 Content Summarization UI**: Enhanced UI displays with comprehensive summary statistics, confidence levels, and quality insights
- **⚡ Performance Optimizations**: Parallel scraping (3x speed improvement), stricter filtering thresholds, optimized timeouts  
- **🐛 Critical Bug Fixes**: Fixed MetricsCollector crashes, broken adaptive threshold logic, hardcoded quality inflation

### ✅ **Enhanced Backend Systems**
- **Centralized Pricing System**: Unified cost calculation across all models
- **Improved Cost Formatting**: Consistent $X.XXXX display format  
- **Model Management**: Better error handling for unavailable models
- **Performance Monitoring**: Enhanced metrics collection and display
- **Source Filtering**: Now actually filters sources with 20-40% typical filtering rates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run `make check` to ensure all checks pass
6. Submit a pull request

### Frontend Development
```bash
cd frontend
npm install
npm run dev     # Development server with hot reload
npm run build   # Production build
```

## 👨‍💻 Author

**David Lee** ([@insigh1](https://github.com/insigh1))  
**Company:** [Fireworks AI](https://fireworks.ai)

This Multi-Agent Research System was developed by David Lee as part of Fireworks AI's research infrastructure initiatives. The system leverages Fireworks AI's powerful model serving platform and cutting-edge AI models.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [UV Setup Guide](./UV_SETUP.md) - Comprehensive setup instructions
- [Complete Implementation Course](./courses/COURSE_Multi_Agent_Research_Systems.md) - Comprehensive course on building multi-agent research systems
- [Development Documentation](./docs/) - Technical improvements and development notes
  - [Optimization Summary](./docs/optimization_summary.md) - Recent system improvements
  - [Source Filtering Fixes](./docs/filtering_improvements.md) - Details on 0% filtering bug fix
  - [Enhanced UI Features](./docs/demo_enhanced_sources_ui.md) - Source discovery improvements
- [Examples](./examples/) - Example configurations and outputs
- [Test Files](./tests/) - Test suite and examples

## 🆘 Support

For issues and questions:
1. Check the [UV Setup Guide](./UV_SETUP.md) for common issues
2. Review the project structure and configuration examples
3. Test with the health check: `python main.py health`
4. Check model availability: `python main.py models --show-config`

---

**Built with ❤️ using FastAPI, Multi-Model AI Architecture, SQLite, Redis, and Fireworks AI**

*Featuring advanced multi-model architecture with cost optimization, intelligent source filtering, and comprehensive monitoring.*

- **🔍 Dual Search Engine Support**: Choose between Brave Search and Firecrawl for web search  
- **📖 Full Content Extraction**: Rich content extraction with Firecrawl for better quality evaluation
- **✅ Intelligent Source Filtering**: Recently enhanced to properly filter 20-40% of sources with realistic quality scoring
- **🎯 Enhanced Discovery UI**: Clear visualization of accepted/rejected sources with explanations
- **⚡ Performance Optimized**: 3x speed improvement with parallel scraping and optimized timeouts