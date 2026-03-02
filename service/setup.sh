#!/usr/bin/env bash
# AI Groove Writer — Service setup script
# Creates/updates virtual environment and installs dependencies.
# Run from the service/ directory: ./setup.sh
#
# Works for first-time setup and ongoing updates (re-run anytime).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON=${PYTHON:-python}
VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "=== AI Groove Writer Service Setup ==="
echo ""

# Check Python version
echo "Checking Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: Python not found. Set PYTHON env var to your Python 3.12+ path."
    echo "  Example: PYTHON=/path/to/python3.12 ./setup.sh"
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

echo "  Found Python $PY_VERSION"

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]); then
    echo "ERROR: Python 3.12+ required, found $PY_VERSION"
    exit 1
fi

# Create or verify virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    echo "  Created $VENV_DIR/"
else
    echo "  Virtual environment exists at $VENV_DIR/"
fi

# Determine venv Python path (Windows vs Unix)
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
elif [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
else
    echo "ERROR: Could not find python in virtual environment"
    exit 1
fi

# Upgrade pip (use python -m pip for Windows compatibility)
echo ""
echo "Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

# Install/update dependencies
echo ""
echo "Installing dependencies from $REQ_FILE..."
"$VENV_PYTHON" -m pip install -r "$REQ_FILE" --quiet
echo "  Done."

# Create .env from example if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  Created .env — edit it with your API credentials."
fi

# Run tests to verify
echo ""
echo "Running tests..."
"$VENV_PYTHON" -m pytest tests/ -v --tb=short

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the service:"
echo "  cd service"
echo "  source .venv/Scripts/activate   # or .venv\\Scripts\\activate on Windows cmd"
echo "  uvicorn app:app --host 127.0.0.1 --port 8787"
