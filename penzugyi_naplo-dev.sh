#!/usr/bin/env bash
set -e

PROJECT_DIR="$HOME/Projects/Penzügyi_Naplo_Dev"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
MAIN_FILE="$PROJECT_DIR/main.py"

cd "$PROJECT_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Hiba: nem található a virtuális környezet pythonja:"
    echo "  $PYTHON_BIN"
    exit 1
fi

if [ ! -f "$MAIN_FILE" ]; then
    echo "Hiba: nem található a main.py:"
    echo "  $MAIN_FILE"
    exit 1
fi

exec "$PYTHON_BIN" "$MAIN_FILE"
