#!/bin/bash
set -e

# Test script for The Robot Overlord API
# Runs pytest with verbose output and coverage reporting

echo "Running tests with coverage..."

# Run pytest with coverage
uv run pytest \
    --verbose \
    --cov=src/therobotoverlord_api \
    --cov-report=html:htmlcov \
    --cov-report=term-missing \
    --cov-report=term \
    tests/

echo ""
echo "Coverage report generated in htmlcov/ directory"
echo "Open htmlcov/index.html in your browser to view the detailed coverage report"
