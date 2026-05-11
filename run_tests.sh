#!/usr/bin/env bash
# run_tests.sh — Kanban E2E test runner
#
# Usage:
#   ./run_tests.sh                   # full suite, 3 parallel workers (default)
#   ./run_tests.sh -n 1              # sequential (easier to read logs)
#   ./run_tests.sh -k test_name      # run one test by name
#   ./run_tests.sh -f tests/test_kanban_filters.py   # run one file
#   ./run_tests.sh --fresh           # delete cached auth state and re-login
#   ./run_tests.sh --help
#
# Environment overrides (defaults target 185574-crm-bundle.creatio.com / clio):
#   KANBAN_BASE_URL=https://my-env.creatio.com
#   KANBAN_USER=admin
#   KANBAN_PASSWORD=secret
#   ./run_tests.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTH_FILE="/tmp/kanban_auth.json"
AUTH_LOCK="/tmp/kanban_auth.lock"

# ── defaults ──────────────────────────────────────────────────────────────────
WORKERS=3
EXTRA_ARGS=()
FRESH=0
SHOW_HELP=0

# ── arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fresh)
            FRESH=1
            shift
            ;;
        --help|-h)
            SHOW_HELP=1
            shift
            ;;
        -n)
            WORKERS="$2"
            shift 2
            ;;
        -k)
            EXTRA_ARGS+=("-k" "$2")
            shift 2
            ;;
        -f|--file)
            EXTRA_ARGS+=("$2")
            shift 2
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ $SHOW_HELP -eq 1 ]]; then
    cat <<'EOF'
run_tests.sh — Kanban E2E test runner

Usage:
  ./run_tests.sh                   # full suite, 3 parallel workers (~3.5 min)
  ./run_tests.sh -n 1              # sequential (easier to read logs)
  ./run_tests.sh -k test_name      # run one test by name
  ./run_tests.sh -f tests/test_kanban_filters.py  # run one file
  ./run_tests.sh --fresh           # delete cached auth state and re-login
  ./run_tests.sh --help

Environment overrides (defaults: 185574-crm-bundle.creatio.com / clio):
  KANBAN_BASE_URL=https://my-env.creatio.com KANBAN_USER=admin KANBAN_PASSWORD=secret ./run_tests.sh
EOF
    exit 0
fi

# ── fresh auth ────────────────────────────────────────────────────────────────
if [[ $FRESH -eq 1 ]]; then
    echo ">>> Clearing cached auth state"
    rm -f "$AUTH_FILE" "$AUTH_LOCK"
fi

# ── dependency check ──────────────────────────────────────────────────────────
if ! python3 -c "import playwright" 2>/dev/null; then
    echo ">>> Installing test dependencies"
    pip install -r "$SCRIPT_DIR/tests/requirements.txt" -q
    playwright install chromium
fi

# ── run ───────────────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"

if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
    # Full suite — default target
    EXTRA_ARGS=("tests/")
fi

echo ">>> Running: pytest ${EXTRA_ARGS[*]} -n $WORKERS"
echo ""

pytest "${EXTRA_ARGS[@]}" \
    -n "$WORKERS" \
    -v \
    --tb=short \
    -p no:warnings
