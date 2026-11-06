#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org/}"
export VITE_API_URL="${VITE_API_URL:-}"

echo "Using npm registry: $REGISTRY"
npm config set registry "$REGISTRY"
npm install --prefer-offline --no-audit --no-fund
npm run build
echo "Built -> $(pwd)/dist"
