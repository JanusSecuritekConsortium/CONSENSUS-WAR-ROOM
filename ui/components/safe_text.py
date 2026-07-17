from __future__ import annotations

from textwrap import wrap


def safe_ellipsis(value: object, max_chars: int = 80) -> str:
    text = str(value or "")
    if max_chars <= 3 or len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def safe_wrap(value: object, *, width: int = 72, max_lines: int = 2) -> list[str]:
    text = str(value or "")
    if not text:
        return [""]
    if width <= 0:
        return [safe_ellipsis(text, 1)]
    lines: list[str] = []
    for raw_line in text.splitlines() or [text]:
        lines.extend(wrap(raw_line, width=width, break_long_words=False, break_on_hyphens=False) or [""])
    if len(lines) <= max_lines:
        return lines
    kept = lines[: max(1, max_lines)]
    kept[-1] = safe_ellipsis(kept[-1], width)
    return kept


def safe_text(value: object, *, max_chars: int = 80) -> str:
    return safe_ellipsis(value, max_chars=max_chars)


__all__ = ["safe_ellipsis", "safe_text", "safe_wrap"]
