#!/bin/bash
cd "$(dirname "$0")/.."
export PATH="$(pwd)/ffmpeg/bin:$PATH"
source .venv/bin/activate
echo "Starting server on http://0.0.0.0:8000 ..."
echo "Press Ctrl+C to stop"
echo
python3 src/core/server.py
