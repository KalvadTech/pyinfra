#!/usr/bin/env bash

set -euo pipefail

echo "Execute ruff check..."
uv run ruff check --diff --unsafe-fixes

echo "Execute ruff format..."
uv run ruff format --diff
