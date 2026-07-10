#!/usr/bin/env bash

# Run all lint checks and report every failure, rather than stopping at the
# first one. This keeps local runs consistent with CI and ensures shellcheck
# always runs even if ruff reports issues.

set -uo pipefail

overall_status=0

run_check() {
    local name=$1
    shift
    echo "Execute ${name}..."
    if "$@"; then
        echo "  ${name}: OK"
    else
        echo "  ${name}: FAILED"
        overall_status=1
    fi
}

run_check "python lint" scripts/lint-python.sh
run_check "type check" scripts/lint-types.sh
run_check "spell check" scripts/spellcheck.sh
run_check "shell check" scripts/lint-shell.sh

if [ "$overall_status" -ne 0 ]; then
    echo "Linting failed."
    exit 1
fi

echo "Linting complete!"
