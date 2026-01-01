#!/bin/bash

# SRE Autonomous Agent - API Server Launcher
# This script starts the FastAPI backend server

echo "🚀 Starting SRE Autonomous Agent API Server..."
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
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Create necessary directories
mkdir -p postmortems
mkdir -p alerts
mkdir -p examples

# Start API server
echo "🚀 API Server running on http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn ui.api:app --host 0.0.0.0 --port 8000 --reload
