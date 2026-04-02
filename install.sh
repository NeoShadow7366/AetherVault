#!/usr/bin/env bash
set -e

echo "==========================================="
echo "Generative AI Manager Bootstrap (Unix)"
echo "==========================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BIN_DIR="$ROOT_DIR/bin"
PYTHON_DIR="$BIN_DIR/python"

mkdir -p "$BIN_DIR"
mkdir -p "$ROOT_DIR/Global_Vault"
mkdir -p "$ROOT_DIR/packages"

if [ ! -f "$PYTHON_DIR/bin/python3" ]; then
    OS_NAME=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH_NAME=$(uname -m)

    if [ "$OS_NAME" = "darwin" ]; then
        if [ "$ARCH_NAME" = "arm64" ] || [ "$ARCH_NAME" = "aarch64" ]; then
            DOWNLOAD_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-apple-darwin-install_only.tar.gz"
        else
            DOWNLOAD_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-apple-darwin-install_only.tar.gz"
        fi
    else
        if [ "$ARCH_NAME" = "aarch64" ]; then
            DOWNLOAD_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-unknown-linux-gnu-install_only.tar.gz"
        else
            DOWNLOAD_URL="https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-unknown-linux-gnu-install_only.tar.gz"
        fi
    fi

    echo "[1/3] Downloading Portable Python ($OS_NAME $ARCH_NAME)..."
    curl -L "$DOWNLOAD_URL" -o "$BIN_DIR/python.tar.gz"
    echo "Extracting Python..."
    tar -xf "$BIN_DIR/python.tar.gz" -C "$BIN_DIR"
    rm "$BIN_DIR/python.tar.gz"
    chmod +x "$PYTHON_DIR/bin/python3"
    echo "Python installed successfully."
else
    echo "[1/3] Portable Python found."
fi

echo "[2/3] Fetching latest backend resources..."
if [ -f "$PYTHON_DIR/bin/python3" ]; then
    "$PYTHON_DIR/bin/python3" "$ROOT_DIR/.backend/bootstrap.py"
else
    echo "[Note] Skipping python execution because portable python was not found. Please install the python binaries and re-run."
fi

echo "[3/3] Bootstrap complete. Run the manager to start."
