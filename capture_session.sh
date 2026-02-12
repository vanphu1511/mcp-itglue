#!/bin/bash
# Capture IT Glue session for document operations
# This activates the venv and runs the session capture script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Run capture script
python capture_session.py
