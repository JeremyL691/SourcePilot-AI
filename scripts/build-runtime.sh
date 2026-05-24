#!/usr/bin/env bash
# Build an embedded Python runtime for the Electron desktop bundle.
# Downloads python-build-standalone, installs SourceHero deps into it,
# and lays it out under desktop/runtime/python-<platform>/.
#
# Usage: bash scripts/build-runtime.sh [mac|linux]
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_ROOT="$PROJECT_ROOT/desktop"
TARGET_OS="${1:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
case "$TARGET_OS" in
  darwin|mac) TARGET="mac"; ARCH=$(uname -m) ;;
  linux)      TARGET="linux"; ARCH=$(uname -m) ;;
  *) echo "Unsupported target: $TARGET_OS"; exit 1 ;;
esac

# Pinned python-build-standalone release; bump as needed.
PBS_TAG="20251002"
PBS_VERSION="3.11.13"

case "$TARGET-$ARCH" in
  mac-arm64)   PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_VERSION}+${PBS_TAG}-aarch64-apple-darwin-install_only.tar.gz" ;;
  mac-x86_64)  PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_VERSION}+${PBS_TAG}-x86_64-apple-darwin-install_only.tar.gz" ;;
  linux-x86_64) PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_VERSION}+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz" ;;
  *) echo "No prebuilt Python for $TARGET-$ARCH"; exit 1 ;;
esac

RUNTIME_DIR="$DESKTOP_ROOT/runtime/python-$TARGET"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "==> Downloading python-build-standalone ($PBS_VERSION, $TARGET-$ARCH)"
curl -fL --progress-bar -o "$WORK_DIR/python.tar.gz" "$PBS_URL"

echo "==> Extracting runtime"
mkdir -p "$WORK_DIR/extract"
tar -xzf "$WORK_DIR/python.tar.gz" -C "$WORK_DIR/extract"

rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"
cp -R "$WORK_DIR/extract/python/." "$RUNTIME_DIR/"

PY="$RUNTIME_DIR/bin/python3"
[ -x "$PY" ] || { echo "Embedded python not executable at $PY"; exit 1; }

echo "==> Installing SourceHero dependencies into embedded runtime (no editable install — app/ is shipped as resources and added via PYTHONPATH at runtime)"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install \
  "beautifulsoup4>=4.12.3" "fastapi>=0.111.0" "feedparser>=6.0.11" "pandas>=2.2.2" \
  "pydantic>=2.7.0" "openai>=1.0.0" "pypdf>=4.2.0" "python-dotenv>=1.0.1" \
  "python-multipart>=0.0.9" "requests>=2.32.0" "sqlalchemy>=2.0.30" \
  "streamlit>=1.35.0" "uvicorn>=0.30.0" "platformdirs>=4.2.0"

echo ""
echo "✅ Embedded runtime ready at: $RUNTIME_DIR"
"$PY" --version
