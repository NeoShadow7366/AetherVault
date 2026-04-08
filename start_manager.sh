#!/usr/bin/env bash
set -e

echo "==========================================="
echo "Generative AI Manager"
echo "==========================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BIN_DIR="$ROOT_DIR/bin"
PYTHON_DIR="$BIN_DIR/python"
PYTHON_EXE="$PYTHON_DIR/bin/python3"

if [ ! -f "$PYTHON_EXE" ]; then
    echo "[INFO] Portable Python not found. Defaulting to system python3..."
    PYTHON_EXE="python3"
    
    if ! command -v "$PYTHON_EXE" > /dev/null; then
        echo "[ERROR] python3 could not be found."
        echo "Please install python3 or run install.sh first."
        exit 1
    fi
fi

echo "[1/2] Launching local Web Dashboard..."
# Cross-platform default browser launch
if command -v xdg-open > /dev/null; then
  xdg-open "http://localhost:8080"
elif command -v open > /dev/null; then
  open "http://localhost:8080"
fi

echo "[2/2] Starting server (embedding engine launches automatically)..."
echo "Please keep this window open to serve UI packages!"
"$PYTHON_EXE" "$ROOT_DIR/.backend/server.py"
