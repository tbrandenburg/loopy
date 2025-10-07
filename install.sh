#!/bin/sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/install.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT_DIR/install.py" "$@"
else
    echo "Python is required to run this installer." >&2
    exit 1
fi
