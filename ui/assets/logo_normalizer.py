from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BOM = "\ufeff"


@dataclass(frozen=True)
class NormalizedLogo:
    text: str
    lines: tuple[str, ...]
    width: int
    height: int
    had_bom: bool = False


def normalize_logo_text(text: str, pad_lines: bool = False) -> NormalizedLogo:
    had_bom = text.startswith(BOM)
    if had_bom:
        text = text.lstrip(BOM)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.rstrip("\n")
    lines = tuple(line.rstrip() for line in text.split("\n") if line.rstrip() or text.strip())
    width = max((len(line) for line in lines), default=0)
    if pad_lines and width:
        lines = tuple(line.ljust(width) for line in lines)
    return NormalizedLogo(
        text="\n".join(lines),
        lines=lines,
        width=width,
        height=len(lines),
        had_bom=had_bom,
    )


def read_normalized_logo(path: Path, pad_lines: bool = False) -> NormalizedLogo:
    data = path.read_bytes()
    text = data.decode("utf-8")
    return normalize_logo_text(text, pad_lines=pad_lines)
