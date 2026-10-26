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
_SPANISH_SMALL = ('cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
                  'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete',
                  'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidós', 'veintitrés',
                  'veinticuatro', 'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve')


def _spanish_clock_number(value):
    if value < 30:
        return _SPANISH_SMALL[value]
    tens, units = divmod(value, 10)
    word = ('', '', '', 'treinta', 'cuarenta', 'cincuenta')[tens]
    return word+(' y '+_SPANISH_SMALL[units] if units else '')


def _spanish_time(match):
    hour, minute = int(match[1]), int(match[2])
    if hour > 24 or minute > 59:
        return match.group(0)
    return _spanish_clock_number(hour)+(' en punto' if minute == 0 else
                                      ' horas y '+_spanish_clock_number(minute)+' minutos')
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


def prepare_speech_text(text: str, lang: str = 'en') -> str:
    """Turn visual formatting into pauses, preserving the words and numeric meaning."""
    text = unicodedata.normalize("NFKC", html.unescape(str(text))).strip()
    text = re.sub(r"\[([^\]\n]+)\]\(https?://[^\s)]+\)", r"\1", text)
    text = re.sub(r"(?m)^\s*(?:[-*_]\s*){3,}$", "", text)
    text = re.sub(r"(?m)^\s*```[^\n]*$", "", text)
    text = re.sub(r"(?m)^\s*(?:#{1,6}\s+|>\s*|[-+*•‣–—]\s+|\d+[.)]\s+)", "", text)
    text = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"(?<!\w)(\*|_)(?=\S)([^\n]+?)(?<=\S)\1(?!\w)", r"\2", text)
    text = text.replace("`", "")
    text = text.replace('→', ' a ' if lang == 'es' else ' to ')
    text = text.replace('↔', ' se solapa con ' if lang == 'es' else ' overlaps with ')

    # A dash in a numeric/time range has meaning; a prose dash is just a pause.
    value = r"-?\d+(?::\d{2}|\.\d+)?%?"
    text = re.sub(rf"(?<![\w./:-])({value})\s*[-–]\s*({value})(?!\w|[./:-]\d)", r"\1 a \2" if lang == 'es' else r"\1 to \2", text)
    text = re.sub(r"(?<=\d)\s*−\s*(?=\d)", " menos " if lang == 'es' else " minus ", text)
    text = re.sub(r"(?<!\w)[-−](?=\d)", "menos " if lang == 'es' else "minus ", text)
    text = re.sub(r"\s+[—–-]\s+|[—–]|[·•|]", ", ", text)
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)
    text = re.sub(r"\b(\d+)/(\d+)\b", r"\1 entre \2" if lang == 'es' else r"\1 over \2", text)
    text = re.sub(r"(?<=\w)/(?=\w)", " ", text)
    text = re.sub(r"[()\[\]{}]", ", ", text)
    text = re.sub(r"[,;:]\s*[,;:]+", ",", text)
    text = re.sub(r"[,;:]\s*([.!?])", r"\1", text)

    lines = [line.strip(" ,") for line in text.splitlines() if line.strip(" ,")]
    for index, line in enumerate(lines[:-1]):
        if line[-1] not in ".!?;:,":
            lines[index] += "."
    text = " ".join(lines)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"[ \t]+", " ", text).strip(" ,")


def normalize_for_speech(text: str, lang: str = 'en') -> str:
    """Normalize UI and operator text into stable, TTS-friendly English."""
    normalized = prepare_speech_text(text, lang=lang)
    if lang == 'es':
        # Spell the 24-hour clock to prevent a voice changing 14:00 into an
        # ambiguous "two". Other numbers use the selected Spanish voice.
        return re.sub(r'\b(\d{1,2}):(\d{2})\b', _spanish_time, normalized).replace('&', ' y ')
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


def split_speech_text(text: str, max_chars: int = 360, lang: str = 'en') -> List[str]:
    """Split normalized speech at sentence boundaries without dropping content."""
    normalized = normalize_for_speech(text, lang=lang)
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


__all__ = ["normalize_for_speech", "number_to_words", "prepare_speech_text", "split_speech_text"]
