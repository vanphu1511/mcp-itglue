#!/bin/bash
# Setup script for JWT token capture
# Run from the mcp-itglue directory

set -e

cd "$(dirname "$0")"

# Activate the existing venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Run 'uv venv && uv pip install -e .' first."
    exit 1
fi

# Install playwright if not already installed
if ! python -c "import playwright" 2>/dev/null; then
    echo "Installing playwright..."
    uv pip install playwright
fi

# Install chromium browser if not already installed
echo "Ensuring Chromium browser is installed..."
python -m playwright install chromium

echo ""
echo "Setup complete. Running token capture..."
echo ""

python capture_jwt_token.py
