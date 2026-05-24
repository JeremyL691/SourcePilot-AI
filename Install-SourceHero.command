#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
bash "$DIR/scripts/setup-macos.sh"
echo ""
read -n 1 -s -r -p "Press any key to close..."
echo ""
