#!/bin/bash
# Build Lambda Layer for Python 3.13 ARM64

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_ROOT/layer"
SRC_COMMON="$PROJECT_ROOT/src/common"

echo "🔧 Building Lambda Layer for Python 3.13 ARM64..."
echo "   Layer directory: $LAYER_DIR"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Clean up old packages
echo "📦 Cleaning old packages..."
rm -rf "$LAYER_DIR/python"
mkdir -p "$LAYER_DIR/python"

# Copy intro_common from src/common (single source of truth)
echo "📁 Syncing intro_common from src/common..."
cp -r "$SRC_COMMON" "$LAYER_DIR/python/intro_common"
# Update __init__.py to reflect it's now the deployed package
sed -i '' 's/Note: This package is deployed/Deployed/' "$LAYER_DIR/python/intro_common/__init__.py" 2>/dev/null || true

# Install dependencies using Docker
echo "📥 Installing dependencies..."
docker run --rm \
  --platform linux/arm64 \
  --entrypoint "" \
  -v "$LAYER_DIR:/layer" \
  -w /layer \
  public.ecr.aws/lambda/python:3.13 \
  pip install -t /layer/python -r requirements.txt --no-cache-dir

# Create ZIP
echo "📦 Creating layer ZIP..."
cd "$LAYER_DIR"
rm -f layer-python313-arm64.zip
zip -r layer-python313-arm64.zip python

echo ""
echo "✅ Layer built successfully!"
echo "   Output: $LAYER_DIR/layer-python313-arm64.zip"
echo "   Size: $(du -h layer-python313-arm64.zip | cut -f1)"
