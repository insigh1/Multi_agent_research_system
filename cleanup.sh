#!/bin/bash

echo "🧹 Cleaning up repository before git push..."

# Remove runtime files
echo "Removing runtime files..."
rm -f research_system.log
rm -f research_sessions.db

# Remove backup files
echo "Removing backup files..."
rm -f web_ui_backup.py
rm -f web_ui_old.py

# Clean Python cache (if any leaked through .gitignore)
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Optional: Move development docs to docs folder
if [ -f "efficiency_improvements.md" ]; then
    echo "Moving development documentation..."
    mkdir -p docs/
    mv efficiency_improvements.md docs/development-notes.md
fi

echo "✅ Cleanup complete!"
echo ""
echo "Files removed:"
echo "  - research_system.log (runtime log)"
echo "  - research_sessions.db (runtime database)"
echo "  - web_ui_backup.py (backup file)"
echo "  - web_ui_old.py (backup file)"
echo ""
echo "Ready for git push! 🚀" 