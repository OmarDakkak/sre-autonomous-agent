#!/bin/bash

# SRE Autonomous Agent - UI Launcher
# This script starts the Streamlit web interface

echo "🤖 Starting SRE Autonomous Agent UI..."
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "Please activate your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if dependencies are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please create a .env file with your configuration:"
    echo "  OPENAI_API_KEY=your-key-here"
    echo "  PROMETHEUS_URL=http://your-prometheus:9090"
    echo "  LOKI_URL=http://your-loki:3100"
    echo ""
fi

# Create necessary directories
mkdir -p postmortems
mkdir -p alerts
mkdir -p examples

# Start Streamlit
echo "🚀 Launching UI on http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run ui/app.py --server.port 8501 --server.address localhost
