#!/bin/bash
#
# Start the Alertmanager webhook server
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting SRE Agent Webhook Server${NC}"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Please run: python -m venv venv${NC}"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Set default environment variables if not set
export WEBHOOK_HOST=${WEBHOOK_HOST:-"0.0.0.0"}
export WEBHOOK_PORT=${WEBHOOK_PORT:-9000}

echo ""
echo "Webhook Server Configuration:"
echo "  Host: $WEBHOOK_HOST"
echo "  Port: $WEBHOOK_PORT"
echo ""
echo "Endpoints:"
echo "  - Alertmanager: http://localhost:$WEBHOOK_PORT/webhook/alertmanager"
echo "  - PagerDuty:    http://localhost:$WEBHOOK_PORT/webhook/pagerduty"
echo "  - Generic:      http://localhost:$WEBHOOK_PORT/webhook/alert"
echo "  - Health:       http://localhost:$WEBHOOK_PORT/health"
echo ""
echo -e "${GREEN}Starting server...${NC}"
echo ""

# Start webhook server
python -m app.webhook.server
