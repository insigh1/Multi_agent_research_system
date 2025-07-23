# Multi-Agent Research System - Course Examples

This directory contains **comprehensive working code examples** that demonstrate every aspect of building a production-ready Multi-Agent Research System using Fireworks AI.

## 📚 Complete Course Structure

### **Core Foundation (Modules 1-4)**
- **Module 1**: Basic LLM Agent Implementation
- **Module 2**: Cost Optimization & Model Management  
- **Module 3**: Multi-Agent Pipeline Coordination
- **Module 4**: Real-time Progress Tracking & WebSocket Integration

### **Advanced Implementation (Modules 5-10)**
- **Module 5**: Advanced Pipeline Orchestration
- **Module 6**: Comprehensive Metrics & Monitoring
- **Module 7**: Production Deployment & Scaling
- **Module 8**: Advanced Features & Performance Optimization
- **Module 9**: Testing & Quality Assurance Framework
- **Module 10**: Real-world Applications & Case Studies

### **🏢 Enterprise Tier 1 (Modules 11-13)** - *Based on Production Implementation*
- **Module 11**: Enterprise Security & Authentication
- **Module 12**: Data Privacy & Compliance
- **Module 13**: DevOps & CI/CD

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- API Keys: Fireworks AI + (Brave Search OR Firecrawl)
- Redis (optional, for advanced modules)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd Multi_agent_research_system/courses/examples

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp ../../env.example .env
# Edit .env with your API keys

# Run any example
python module1_basic_llm_agent.py
```

## 📋 Module Details

### Module 1: Basic LLM Agent (`module1_basic_llm_agent.py`)
**Foundation of multi-agent systems**
- Basic `LLMAgent` class with Fireworks AI integration
- Cost tracking and budget management
- Error handling and retry logic
- Simple web search integration

**Key Concepts:**
- Agent initialization and configuration
- API cost calculation
- Basic error handling patterns
- Async/await patterns for AI operations

### Module 2: Cost Optimization (`module2_cost_optimization.py`)
**Smart model selection and budget management**
- Cost-aware model selection strategies
- Budget monitoring and alerts
- Model performance vs cost analysis
- Automated fallback mechanisms

**Key Concepts:**
- Dynamic model selection based on cost/performance
- Real-time budget tracking
- Cost optimization algorithms
- Model efficiency metrics

### Module 3: Multi-Agent Pipeline (`module3_multi_agent_pipeline.py`)
**Coordinated multi-agent workflows**
- Specialized agents (Research Planner, Web Search, Quality Evaluator)
- Agent communication and coordination
- Pipeline orchestration
- Information quality assessment

**Key Concepts:**
- Agent specialization patterns
- Inter-agent communication
- Pipeline state management
- Quality control mechanisms

### Module 4: Real-time Progress (`module4_real_time_progress.py`)
**Live progress tracking and WebSocket integration**
- Real-time progress updates
- WebSocket communication simulation
- Session management
- Status broadcasting

**Key Concepts:**
- WebSocket patterns for real-time updates
- Progress tracking architectures
- Session state management
- Event-driven updates

### Module 5: Advanced Pipeline (`module5_advanced_pipeline.py`)
**Sophisticated orchestration with resilience**
- Parallel processing and optimization
- Circuit breaker patterns
- Advanced error recovery
- Performance monitoring

**Key Concepts:**
- Parallel execution strategies
- Fault tolerance patterns
- Performance optimization
- Resource management

### Module 6: Metrics & Monitoring (`module6_metrics_monitoring.py`)
**Comprehensive system observability**
- Prometheus metrics integration
- SQLite-based analytics storage
- Performance dashboards
- Alerting systems

**Key Concepts:**
- Metrics collection and storage
- Performance analytics
- Alerting and monitoring
- Data visualization

### Module 7: Production Deployment (`module7_production_deployment.py`)
**Scalable production deployment**
- Docker containerization
- Load balancing strategies
- Health checks and monitoring
- Production-ready HTTP API

**Key Concepts:**
- Containerization strategies
- Load balancing patterns
- Production monitoring
- Scalability planning

### Module 8: Advanced Features (`module8_advanced_features.py`)
**Performance optimization and caching**
- Multi-layer caching (Memory + Redis + Disk)
- Smart retry mechanisms
- Parallel processing optimization
- Advanced error handling

**Key Concepts:**
- Caching architectures
- Performance optimization
- Retry strategies
- Resource optimization

### Module 9: Testing & Quality (`module9_testing_quality.py`)
**Comprehensive testing framework**
- Unit and integration testing
- Performance benchmarking
- Quality scoring systems
- Mocking and test automation

**Key Concepts:**
- Testing strategies
- Quality assurance
- Performance benchmarking
- Test automation

### Module 10: Real-world Applications (`module10_real_world_applications.py`)
**Complete production use cases**
- Academic research automation
- Market analysis systems
- Competitive intelligence
- Business process automation

**Key Concepts:**
- End-to-end application development
- Business process integration
- Data export and reporting
- Production workflow automation

---

## 🏢 **Enterprise Tier 1 Modules (Production Implementation)**

### Module 11: Enterprise Security & Authentication (`module11_enterprise_security.py`)
**Production security implementation from the main app**
- `SecurityManager` with Fernet encryption (from `utils.py`)
- Session ID generation and management
- API key validation for multiple services
- Input sanitization and XSS prevention
- Rate limiting with backoff strategies
- CORS middleware configuration

**Key Features:**
- ✅ Fernet encryption for sensitive data
- ✅ Cryptographically secure session IDs
- ✅ Multi-service API key validation
- ✅ Comprehensive input validation
- ✅ Production rate limiting
- ✅ Security event logging

**Based on Production Code:**
- `SecurityManager` class from `utils.py`
- `SimpleRateLimiter` from `enhanced_research_system.py`
- CORS middleware from `web_ui.py`
- Custom exceptions from `exceptions.py`

### Module 12: Data Privacy & Compliance (`module12_data_privacy_compliance.py`)
**Production data privacy implementation from the main app**
- Database session management (SQLite)
- Data encryption at rest
- Audit logging for compliance
- Data retention policies
- User data export (data portability)
- Data deletion (right to be forgotten)

**Key Features:**
- ✅ Encrypted PII storage
- ✅ Comprehensive audit trails
- ✅ Data retention automation
- ✅ GDPR compliance features
- ✅ Data anonymization techniques
- ✅ Compliance reporting

**Based on Production Code:**
- Database schema from `research_sessions.db`
- Security encryption from `utils.py`
- Session management from `enhanced_research_system.py`

### Module 13: DevOps & CI/CD (`module13_devops_cicd.py`)
**Production DevOps implementation from the main app**
- Docker containerization
- Health check systems
- Setup automation (`setup.sh`, `Makefile`)
- CI/CD pipeline configuration
- Infrastructure as code
- Monitoring integration

**Key Features:**
- ✅ Multi-stage Docker builds
- ✅ Docker Compose orchestration
- ✅ Comprehensive health checks
- ✅ Automated setup scripts
- ✅ GitHub Actions workflows
- ✅ Production monitoring

**Based on Production Code:**
- Docker examples from `module7_production_deployment.py`
- Health checks from `main.py`
- Setup scripts: `setup.sh`, `Makefile`
- Production configurations

---

## 🔧 Configuration

### Environment Variables
```bash
# Required API Keys
FIREWORKS_API_KEY=your_fireworks_key
BRAVE_API_KEY=your_brave_key  # OR Firecrawl
FIRECRAWL_API_KEY=your_firecrawl_key

# Optional Services
REDIS_URL=redis://localhost:6379

# Security (Tier 1 modules)
RESEARCH_ENCRYPTION_KEY=your_encryption_key
RESEARCH_REQUESTS_PER_MINUTE=60
```

### Model Configuration
Each example supports different model selection strategies:
- **Single**: Use one model for all agents
- **Adaptive**: Agent-specific models with fallback
- **Cost-optimized**: Cheapest models meeting quality requirements
- **Performance-optimized**: Best models within budget

## 🚀 Running Examples

### Individual Modules
```bash
# Basic examples
python module1_basic_llm_agent.py
python module2_cost_optimization.py

# Advanced examples
python module5_advanced_pipeline.py
python module6_metrics_monitoring.py

# Enterprise examples (Tier 1)
python module11_enterprise_security.py
python module12_data_privacy_compliance.py
python module13_devops_cicd.py
```

### With Custom Configuration
```bash
# Set specific models
export RESEARCH_MODEL="accounts/fireworks/models/llama-v3p1-70b-instruct"
python module3_multi_agent_pipeline.py

# Enable advanced features
export ENABLE_REDIS_CACHE=true
export ENABLE_METRICS=true
python module8_advanced_features.py
```

## 📊 Example Outputs

Each module generates comprehensive output showing:
- **Real API calls** with actual costs
- **Performance metrics** and timing
- **Error handling** demonstrations
- **Quality scores** and confidence levels
- **Progress tracking** with detailed status updates

## 🔄 Integration with Main App

These examples demonstrate the **actual implementations** used in the main Multi-Agent Research System:

- **Security**: Same `SecurityManager` and encryption used in production
- **Data Privacy**: Same database schema and retention policies
- **DevOps**: Same Docker configurations and health checks
- **Models**: Same Fireworks AI integration and cost tracking
- **Agents**: Same agent classes and coordination patterns

## 🆘 Troubleshooting

### Common Issues
1. **Missing API Keys**: Check `.env` file configuration
2. **Module Import Errors**: Install dependencies with `pip install -r requirements.txt`
3. **Redis Connection**: Redis is optional for basic modules
4. **Rate Limiting**: Some examples include intentional delays

### Getting Help
- Check the main app's health check: `python ../../main.py health`
- Review the setup guide: `../../UV_SETUP.md`
- Examine the actual production code for reference

---

**Built with ❤️ using Fireworks AI, FastAPI, and Production-Ready Architecture**

*These examples demonstrate real-world, production-ready implementations that you can use immediately in your own projects.* 