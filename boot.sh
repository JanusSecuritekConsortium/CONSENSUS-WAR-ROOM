#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    printf '%s\n' 'Missing Linux virtual environment. See docs/LINUX_MIGRATION.md.' >&2
    exit 1
fi
cd -- "$ROOT"
exec "$PYTHON" "$ROOT/tools/boot.py" "$@"
