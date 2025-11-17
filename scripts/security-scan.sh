#!/bin/bash

# Security Scanning Script for Dexter
# Usage: ./scripts/security-scan.sh

set -e

echo "🔒 Running Security Scans for Dexter Financial Research Agent"
echo "=========================================================="

# Ensure we're in project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run from project root."
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  Warning: No .venv found, using system Python"
fi

# Install security tools if needed
echo "🛠️  Ensuring security tools are available..."
pip install bandit safety 2>/dev/null || true

# Create reports directory
mkdir -p docs/security-reports
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

echo ""
echo "1️⃣  Running Bandit Python Security Analysis..."
echo "-----------------------------------------------"

# Run Bandit scan
if command -v bandit &> /dev/null; then
    bandit -r src/dexter/ -f json -o "docs/security-reports/bandit-report-$TIMESTAMP.json" || {
        BANDIT_EXIT_CODE=$?
        echo "⚠️  Bandit found issues (exit code: $BANDIT_EXIT_CODE)"
    }

    # Also show console output
    echo ""
    echo "📊 Bandit Summary:"
    bandit -r src/dexter/ --quiet || true
else
    echo "❌ Bandit not available, skipping..."
fi

echo ""
echo "2️⃣  Running Safety Dependency Vulnerability Scan..."
echo "----------------------------------------------------"

# Create requirements.txt from pyproject.toml for safety scan
echo "📄 Generating requirements.txt from pyproject.toml..."
python -c "
import tomllib
from pathlib import Path

try:
    with open('pyproject.toml', 'rb') as f:
        pyproject = tomllib.load(f)

    deps = pyproject.get('project', {}).get('dependencies', [])
    print('\\n'.join(deps))
except Exception as e:
    print(f'Error reading pyproject.toml: {e}')
    exit(1)
" > requirements-temp.txt

# Run Safety scan
if command -v safety &> /dev/null; then
    # Try to run safety with local config to avoid permission issues
    export SAFETY_CACHE_DIR=/tmp/safety-cache
    mkdir -p $SAFETY_CACHE_DIR

    safety check --json --output "docs/security-reports/safety-report-$TIMESTAMP.json" \
        --file requirements-temp.txt || {
        SAFETY_EXIT_CODE=$?
        echo "⚠️  Safety found issues (exit code: $SAFETY_EXIT_CODE)"
    }

    # Also show console output
    echo ""
    echo "📊 Safety Summary:"
    safety check --file requirements-temp.txt || true
else
    echo "❌ Safety not available, skipping..."
fi

# Clean up temp file
rm -f requirements-temp.txt

echo ""
echo "3️⃣  Security Scan Results Summary"
echo "================================="

# Count Bandit issues
if [ -f "docs/security-reports/bandit-report-$TIMESTAMP.json" ]; then
    BANDIT_ISSUES=$(python -c "
import json
try:
    with open('docs/security-reports/bandit-report-$TIMESTAMP.json') as f:
        data = json.load(f)
    print(len(data.get('results', [])))
except:
    print('N/A')
" 2>/dev/null || echo "N/A")
    echo "🔍 Bandit Issues Found: $BANDIT_ISSUES"
else
    echo "🔍 Bandit Issues Found: Scan failed"
fi

# Count Safety issues
if [ -f "docs/security-reports/safety-report-$TIMESTAMP.json" ]; then
    SAFETY_ISSUES=$(python -c "
import json
try:
    with open('docs/security-reports/safety-report-$TIMESTAMP.json') as f:
        data = json.load(f)
    print(len(data.get('vulnerabilities', [])))
except:
    print('N/A')
" 2>/dev/null || echo "N/A")
    echo "🔍 Safety Issues Found: $SAFETY_ISSUES"
else
    echo "🔍 Safety Issues Found: Scan failed"
fi

echo ""
echo "📁 Reports saved to docs/security-reports/"
echo "✨ Security scanning complete!"
echo ""
echo "📋 Next Steps:"
echo "   - Review detailed reports in docs/security-reports/"
echo "   - Fix any critical/high severity vulnerabilities found"
echo "   - Update dependencies as needed"