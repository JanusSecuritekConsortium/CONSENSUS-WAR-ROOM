#!/usr/bin/env bash
# Run the tests the way GitHub CI sees them: on Linux, where Linux-only settings
# (for example voice/voice_config.linux.json) apply. Catches "passes on Windows,
# fails on CI" before a push.
#
# From Windows:  wsl -d Ubuntu -- bash tools/linux_tests.sh [pytest arguments]
# Example:       wsl -d Ubuntu -- bash tools/linux_tests.sh tests/test_spoken_briefing.py
#
# Packages live outside the repo in $CONSENSUS_LINUX_SITE (default G:\Tools\uv-linux\site),
# installed with the Linux uv:  uv pip install --no-cache --python /usr/bin/python3 --target <site> ...
# The window smoke tests are skipped, because CONSENSUS_GUI_TESTS is not set and there is no display.
set -euo pipefail
cd "$(dirname "$0")/.."
site="${CONSENSUS_LINUX_SITE:-/mnt/g/Tools/uv-linux/site}"
if [ ! -d "$site" ]; then
  echo "Linux test packages not found at $site; see the comment at the top of this script." >&2
  exit 2
fi
export PYTHONPATH="$site:$PWD${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
unset CONSENSUS_GUI_TESTS
exec python3 -m pytest -p no:cacheprovider \
  --ignore=tests/test_gui_launch_smoke.py --ignore=tests/test_gui_launch_smoke_readiness.py "$@"
