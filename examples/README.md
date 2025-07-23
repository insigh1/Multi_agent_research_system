# 📄 Examples

This directory contains example outputs and usage demonstrations of the Multi-Agent Research System.

## 📁 Directory Structure

- `reports/` - Sample research reports in HTML and PDF formats

## 🔍 Sample Reports

The reports in this directory demonstrate the system's capabilities across different research topics and complexity levels. Each report showcases:

- **Comprehensive Research**: Multi-stage analysis with quality evaluation
- **Source Diversity**: Information gathered from various authoritative sources
- **Quality Metrics**: Confidence scores and reliability assessments
- **Structured Output**: Well-organized findings with proper citations

## 📊 Report Formats

- **HTML Reports**: Interactive web-friendly format with embedded metrics and styling
- **PDF Reports**: Print-ready documents with professional formatting
- **JSON Data**: Available through CLI with `--output-format json` option

## 🚀 Generating Your Own Examples

To generate similar reports:

```bash
# Web UI (recommended)
python start_web_ui.py

# CLI - HTML format
python main.py research "Your research topic" --output-format html --save-session

# CLI - PDF format  
python main.py research "Your research topic" --output-format pdf --save-session

# CLI - JSON format
python main.py research "Your research topic" --output-format json --save-session
```

Generated reports are automatically saved with unique session IDs and will appear in this directory when using the `--save-session` flag. 