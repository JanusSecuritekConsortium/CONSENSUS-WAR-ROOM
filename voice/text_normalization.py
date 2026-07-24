from __future__ import annotations

import html
import re
import unicodedata
from typing import List


_ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_SPOKEN_NAMES = {
    "A.U.R.E.L.I.U.S.": "Aurelius",
    "A.U.R.E.L.I.U.S": "Aurelius",
    "GLaDOS": "Glados",
    "CONSENSUS_SYSTEM": "Consensus System",
}
_SPOKEN_ACRONYMS = {
    "API": "A P I",
    "CPU": "C P U",
    "GPU": "G P U",
    "GUI": "G U I",
    "RVC": "R V C",
    "TTS": "T T S",
    "WAV": "wave",
}


def number_to_words(value: int) -> str:
    """Return a compact English reading for an integer used in operator text."""
    if value < 0:
        return f"minus {number_to_words(-value)}"
    if value < 20:
        return _ONES[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return _TENS[tens] if not ones else f"{_TENS[tens]} {_ONES[ones]}"
    if value < 1_000:
        hundreds, remainder = divmod(value, 100)
        prefix = f"{_ONES[hundreds]} hundred"
        return prefix if not remainder else f"{prefix} {number_to_words(remainder)}"
    if value < 1_000_000:
        thousands, remainder = divmod(value, 1_000)
        prefix = f"{number_to_words(thousands)} thousand"
        return prefix if not remainder else f"{prefix} {number_to_words(remainder)}"
    return " ".join(_ONES[int(digit)] for digit in str(value))


def normalize_for_speech(text: str) -> str:
    """Normalize UI and operator text into stable, TTS-friendly English."""
    normalized = unicodedata.normalize("NFKC", html.unescape(str(text))).strip()
    if not normalized:
        return ""

    normalized = normalized.translate(
        str.maketrans(
            {
                "\u2018": "'",
                "\u2019": "'",
                "\u201c": '"',
                "\u201d": '"',
                "\u2013": "-",
                "\u2014": " - ",
                "&": " and ",
            }
        )
    )
    for source, replacement in _SPOKEN_NAMES.items():
        normalized = normalized.replace(source, replacement)

    normalized = re.sub(r"(?<=\w)_(?=\w)", " ", normalized)
    normalized = re.sub(r"(?<=\w)/(?=\w)", " slash ", normalized)
    normalized = re.sub(r"\b([A-Za-z])-(\d+)\b", r"\1 \2", normalized)
    normalized = re.sub(r"\b(\d{1,2}):(\d{2})\b", _replace_time, normalized)
    normalized = re.sub(r"\$([0-9]+(?:\.[0-9]{1,2})?)", _replace_dollars, normalized)
    normalized = re.sub(r"\b([0-9]+(?:\.[0-9]+)?)\s*%", _replace_percent, normalized)
    normalized = re.sub(r"\b(\d+)\.(\d+)\b", _replace_decimal, normalized)
    normalized = re.sub(r"\b\d{1,6}\b", lambda match: number_to_words(int(match.group(0))), normalized)

    for source, replacement in _SPOKEN_ACRONYMS.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", replacement, normalized)

    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\s*\n\s*", " ", normalized)
    return normalized.strip()


def split_speech_text(text: str, max_chars: int = 360) -> List[str]:
    """Split normalized speech at sentence boundaries without dropping content."""
    normalized = normalize_for_speech(text)
    if not normalized:
        return []
    if max_chars < 80:
        raise ValueError("max_chars must be at least 80")

    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_clause(sentence, max_chars))
            continue
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _replace_time(match: re.Match[str]) -> str:
    hour = int(match.group(1))
    minute = int(match.group(2))
    if minute == 0:
        return f"{number_to_words(hour)} o'clock"
    minute_text = f"oh {number_to_words(minute)}" if minute < 10 else number_to_words(minute)
    return f"{number_to_words(hour)} {minute_text}"


def _replace_dollars(match: re.Match[str]) -> str:
    raw = match.group(1)
    whole, dot, fraction = raw.partition(".")
    dollars = int(whole)
    result = f"{number_to_words(dollars)} {'dollar' if dollars == 1 else 'dollars'}"
    if dot and int(fraction):
        cents = int(fraction.ljust(2, "0")[:2])
        result += f" and {number_to_words(cents)} {'cent' if cents == 1 else 'cents'}"
    return result


def _replace_percent(match: re.Match[str]) -> str:
    return f"{_spoken_decimal(match.group(1))} percent"


def _replace_decimal(match: re.Match[str]) -> str:
    return _spoken_decimal(match.group(0))


def _spoken_decimal(raw: str) -> str:
    whole, dot, fraction = raw.partition(".")
    if not dot:
        return number_to_words(int(whole))
    digits = " ".join(_ONES[int(digit)] for digit in fraction)
    return f"{number_to_words(int(whole))} point {digits}"


def _split_long_clause(text: str, max_chars: int) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks


__all__ = ["normalize_for_speech", "number_to_words", "split_speech_text"]
