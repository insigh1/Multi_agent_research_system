# 🚀 UV Setup Guide - Multi-Agent Research System

This guide shows you how to set up and run the Multi-Agent Research System using **UV** - the fastest Python package manager and project manager.

## ⚡ Why UV?

UV is **10-100x faster** than pip and provides:
- ⚡ **Lightning fast** dependency resolution and installation
- 🔒 **Reliable** dependency locking and reproducible builds  
- 🐍 **Python version management** built-in
- 📦 **Modern project management** with pyproject.toml
- 🔄 **Compatible** with existing pip/setuptools workflows

## 🛠️ Quick Setup (Recommended)

### 1. Automated Setup
```bash
# Clone and setup in one command
git clone <your-repo-url>
cd Multi_agent_research_system
./setup.sh
```

The setup script will:
- ✅ Install UV if not present
- ✅ Create virtual environment with Python 3.11
- ✅ Install all dependencies
- ✅ Create `.env` file from template
- ✅ Set up project directories

### 2. Configure API Keys
Edit the `.env` file with your API keys:
```bash
# Required API Keys
FIREWORKS_API_KEY=your_fireworks_api_key_here
BRAVE_API_KEY=your_brave_search_api_key_here
```

### 3. Start Using
```bash
# Start web UI
./run-web.sh

# Or use CLI
./run-cli.sh "Your research question"

# Or use Make commands
make web
make cli QUERY="Your research question"
```

## 📋 Manual Setup

### 1. Install UV
```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create Environment
```bash
# Create virtual environment with Python 3.11
uv venv --python 3.11

# Activate environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
# Install project in editable mode
uv pip install -e .

# Or install with development dependencies
uv pip install -e ".[dev]"
```

### 4. Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit with your API keys
nano .env  # or your preferred editor
```

## 🎯 Usage Commands

### Web Interface
```bash
# Method 1: Direct command
uv run python web_ui.py --port 8080

# Method 2: Script
./run-web.sh

# Method 3: Make
make web
```

### CLI Interface
```bash
# Method 1: Direct command
uv run python main.py research "Your question"

# Method 2: Script
./run-cli.sh "Your question"

# Method 3: Make
make cli QUERY="Your question"
```

### Testing
```bash
# Method 1: Script
./test.sh

# Method 2: Make
make test

# Method 3: Direct
uv run pytest tests/
```

## 📦 Available Make Commands

```bash
make help          # Show all available commands
make setup          # Initial project setup
make install        # Install dependencies
make dev-install    # Install with dev dependencies
make web            # Start web UI
make cli QUERY="..."# Start CLI with query
make test           # Run tests
make format         # Format code (black, isort)
make lint           # Run linting (flake8, mypy)
make check          # Run all checks
make clean          # Clean build artifacts
make health         # Run health check
```

## 🏗️ Project Structure

```
Multi_agent_research_system/
├── pyproject.toml          # UV/Python project configuration
├── setup.sh               # Automated setup script
├── run-web.sh             # Web UI launcher
├── run-cli.sh             # CLI launcher  
├── test.sh                # Test runner
├── Makefile               # Make commands
├── UV_SETUP.md            # This guide
├── .env                   # Environment variables (create from env.example)
├── .venv/                 # Virtual environment (created by UV)
└── ... (rest of project files)
```

## 🔧 Development Setup

For development work:

```bash
# Full development setup
make dev

# Or manually:
uv pip install -e ".[dev]"

# Format code
make format

# Run linting
make lint

# Run all checks
make check
```

## 🚀 Deployment Options

### 1. Docker (Coming Soon)
```dockerfile
# Dockerfile using UV
FROM python:3.11-slim
RUN pip install uv
COPY . /app
WORKDIR /app
RUN uv pip install -e .
CMD ["python", "web_ui.py"]
```

### 2. Production Install
```bash
# Install without development dependencies
uv pip install -e . --no-dev
```

### 3. Build Distribution
```bash
# Build wheel and source distribution
uv build

# Install from wheel
uv pip install dist/*.whl
```

## ⚡ Performance Benefits

UV provides significant performance improvements:

| Operation | pip | UV | Speedup |
|-----------|-----|----|---------| 
| Install dependencies | ~45s | ~3s | **15x faster** |
| Create virtual env | ~8s | ~1s | **8x faster** |
| Dependency resolution | ~20s | ~0.5s | **40x faster** |

## 📋 System Dependencies

### PDF Generation (WeasyPrint)
PDF generation is now fully supported! The setup script automatically installs WeasyPrint, but system dependencies are required:

#### macOS (Homebrew)
```bash
# Install system dependencies (automatically handled by setup.sh)
brew install cairo pango gdk-pixbuf libffi gobject-introspection gtk+3 glib
```

#### Ubuntu/Debian
```bash
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

#### Other Systems
See [WeasyPrint installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

## 🔍 Troubleshooting

### UV Not Found
```bash
# Add UV to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Virtual Environment Issues
```bash
# Remove and recreate
rm -rf .venv
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

### Dependency Conflicts
```bash
# Clear UV cache
uv cache clean

# Reinstall from scratch
rm -rf .venv
./setup.sh
```

### API Key Issues
```bash
# Check .env file exists and has correct format
cat .env

# Verify environment variables are loaded
uv run python -c "import os; print(os.getenv('FIREWORKS_API_KEY'))"
```

## 📚 Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub](https://github.com/astral-sh/uv)
- [Project Documentation](./docs/)
- [API Key Setup Guide](./docs/API_SETUP.md)

## 🆘 Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review the main [README.md](./README.md)
3. Check existing [GitHub issues](../../issues)
4. Create a new issue with:
   - UV version: `uv --version`
   - Python version: `python --version`
   - Operating system
   - Error messages and logs

---

**Happy researching with UV! ⚡🔬** 