#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_ROOT="$PROJECT_ROOT/desktop"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"

step() { printf "\n==> %s\n" "$1"; }
die() { printf "\nERROR: %s\n\n" "$1" >&2; exit 1; }

find_python() {
  for candidate in python3.11 python3 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

require() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is missing. $2"
}

cd "$PROJECT_ROOT"

step "Checking macOS prerequisites"
require npm "Install Node.js LTS from https://nodejs.org/ or run: brew install node"

if [ -x "$VENV_PY" ]; then
  PYTHON="$VENV_PY"
else
  PYTHON="$(find_python)" || die "Python 3.11+ not found. Install via Homebrew: brew install python@3.11"
fi
echo "Using Python: $PYTHON"

if [ ! -x "$VENV_PY" ]; then
  step "Creating Python virtual environment"
  "$PYTHON" -m venv "$VENV_DIR"
fi

step "Installing Python dependencies"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -e "."

step "Installing desktop dependencies"
cd "$DESKTOP_ROOT"
npm install

step "Preparing Electron"
npm run ensure-electron

step "Running desktop smoke check"
npm run smoke

echo ""
echo "SourceHero AI setup completed. Start it with:"
echo "   Double-click Start-SourceHero.command"
echo "   or run: bash scripts/start-macos.sh"
