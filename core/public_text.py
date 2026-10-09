"""Filter tagged private reasoning from public presentation fields."""
from __future__ import annotations

import re


def public_text(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"<(think|analysis|reasoning)\b[^>]*>.*?</\1\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r"<(?:think|analysis|reasoning)\b[^>]*>.*$", "", text, flags=re.I | re.S)
    return text.strip()[:16000]
