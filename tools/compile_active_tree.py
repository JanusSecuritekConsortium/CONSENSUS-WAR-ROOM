from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.active_compile import compile_active_sources, print_compile_report


def main() -> int:
    result = compile_active_sources(ROOT)
    print_compile_report(result, ROOT)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
