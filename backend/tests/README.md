# 🧪 Tests

This directory contains test files for the Multi-Agent Research System.

## 📁 Test Files

- `simple_test.py` - Basic functionality and API tests
- `current_system_test.py` - Comprehensive system tests for current UV-based architecture

## 🚀 Running Tests

### Individual Tests
```bash
# Simple functionality test
uv run python tests/simple_test.py

# Current system comprehensive test
uv run python tests/current_system_test.py
```

### Using Make Commands
```bash
# Run all tests
make test
```

## 📋 Test Coverage

The tests cover:
- **Core Functionality**: Research system, API connections, health checks
- **PDF Generation**: WeasyPrint functionality and system dependencies
- **Web UI**: FastAPI endpoints and health checks
- **Database**: Session management and persistence
- **Configuration**: Settings validation and environment setup
- **Import Validation**: All core modules import correctly

## ⚙️ Test Configuration

Tests use the same configuration system as the main application. Ensure you have:
- Valid API keys in `.env` file (copy from `env.example`)
- Required dependencies installed via `./setup.sh`
- System dependencies for PDF generation (automatically installed on macOS)

## 📊 Test Results

Test results include:
- **Module Import Status**: Verification all core components load
- **PDF Generation**: WeasyPrint functionality with system dependencies  
- **Database Operations**: Session storage and retrieval
- **API Health**: Web UI and research system health checks
- **Configuration**: Settings validation and loading

## 🎯 Expected Results

All tests should pass on a properly configured system:
- ✅ Core Module Imports
- ✅ Settings Validation  
- ✅ WeasyPrint PDF Generation
- ✅ Database Manager
- ✅ Web UI Health Check
- ✅ Research System Health 