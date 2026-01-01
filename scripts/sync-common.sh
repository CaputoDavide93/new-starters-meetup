#!/bin/bash
# Sync intro_common from src/common to layer (without rebuilding deps)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_ROOT/layer"
SRC_COMMON="$PROJECT_ROOT/src/common"

echo "📁 Syncing intro_common from src/common..."

# Remove old intro_common and copy fresh
rm -rf "$LAYER_DIR/python/intro_common"
cp -r "$SRC_COMMON" "$LAYER_DIR/python/intro_common"

echo "✅ Synced intro_common to layer/python/intro_common"
