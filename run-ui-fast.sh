#!/bin/bash

# SRE Autonomous Agent - Optimized UI Launcher
# This script starts the Streamlit web interface with performance optimizations

echo "🤖 Starting SRE Autonomous Agent UI (Optimized)..."
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo ""
fi

# Create necessary directories
mkdir -p postmortems
mkdir -p alerts
mkdir -p approvals
mkdir -p examples

# Start Streamlit with performance optimizations
echo "🚀 Launching UI on http://localhost:8501"
echo ""
echo "Performance optimizations enabled:"
echo "  ✓ File watcher disabled (faster)"
echo "  ✓ Browser auto-open disabled"
echo "  ✓ Caching enabled"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Performance flags:
# --server.fileWatcherType=none : Disable file watching (faster startup)
# --server.runOnSave=false : Don't reload on file changes
# --browser.gatherUsageStats=false : Disable telemetry
streamlit run ui/app.py \
    --server.port 8501 \
    --server.address localhost \
    --server.fileWatcherType none \
    --server.runOnSave false \
    --browser.gatherUsageStats false
