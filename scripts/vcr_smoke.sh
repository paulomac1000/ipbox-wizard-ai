#!/bin/bash
# VCR Smoke Check - runs tests in playback mode without API calls
# Usage: ./scripts/vcr_smoke.sh [-v]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🧪 Running VCR smoketest (playback mode, no API calls)..."
echo ""

# Check if cassettes exist
if [ ! -d "tests/llm/vcr/cassettes" ]; then
    echo "❌ No cassettes directory found. Run with VCR_MODE=record first."
    exit 1
fi

# Count cassettes
CASSETTE_COUNT=$(find tests/llm/vcr/cassettes -name "*.yaml" | wc -l)
echo "📼 Found $CASSETTE_COUNT cassettes"

if [ "$CASSETTE_COUNT" -eq 0 ]; then
    echo "❌ No cassettes found. Run with VCR_MODE=record first."
    exit 1
fi

# Run tests in playback mode (no API calls)
VCR_MODE=playback python -m pytest \
    tests/llm/ \
    -v \
    --run-llm \
    --vcr-mode=playback \
    -m smoke \
    --tb=short \
    "$@"

echo ""
echo "✅ Smoke test passed (no API calls made)"