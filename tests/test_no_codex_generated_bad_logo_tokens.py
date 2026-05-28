from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import compact_logo_text
from ui.themes.catalog import THEMES


BAD_TOKENS = {
    "eva": ("NERV GEOMETRIC MAGI MARK", "CASPER", "BALTHASAR", "MELCHIOR"),
    "helldivers": ("O O", "LIBERTY WINGS", "MANAGED DEMOCRACY ONLINE", "invented cartoon skull"),
}


def test_user_supplied_headers_do_not_contain_previous_generated_tokens() -> None:
    for theme_key, tokens in BAD_TOKENS.items():
        text = compact_logo_text(THEMES[theme_key])
        for token in tokens:
            assert token not in text


if __name__ == "__main__":
    test_user_supplied_headers_do_not_contain_previous_generated_tokens()
    print("test_no_codex_generated_bad_logo_tokens PASS")
