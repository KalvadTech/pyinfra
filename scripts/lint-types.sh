#!/usr/bin/env bash

set -euo pipefail

echo "Execute mypy..."
uv run mypy

echo "Execute arguments type check..."
uv run python scripts/lint_arguments_sync.py
