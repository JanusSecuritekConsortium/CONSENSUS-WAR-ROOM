"""Long pauses inside speech are shortened; gaps between words, and the speech itself, are left alone."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.audio_quality import tighten_pauses

RATE = 16_000


def tone(ms):
    return [round(12000 * math.sin(2 * math.pi * 220 * n / RATE)) for n in range(RATE * ms // 1000)]


def silence(ms):
    return [0] * (RATE * ms // 1000)


def write(path, parts):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(array("h", [sample for part in parts for sample in part]).tobytes())


def duration_ms(path):
    with wave.open(str(path), "rb") as source:
        return round(source.getnframes() * 1000 / source.getframerate())


class TightenPausesTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "speech.wav"

    def test_long_pauses_shrink_and_word_gaps_stay(self):
        # lead-in, word, word gap, word, comma pause, word, sentence pause, word, tail
        write(self.path, [silence(300), tone(400), silence(80), tone(400), silence(350), tone(400),
                          silence(900), tone(400), silence(300)])
        result = tighten_pauses(self.path)
        self.assertEqual(result["pauses_shortened"], 2)
        # comma 350 -> 120 + 0.4 * 230 = 212 ms; sentence 900 -> 432 ms; edges and the 80 ms gap untouched
        self.assertAlmostEqual(result["removed_ms"], (350 - 210) + (900 - 430), delta=20)
        self.assertAlmostEqual(duration_ms(self.path), 3530 - result["removed_ms"], delta=5)

    def test_pause_is_capped(self):
        write(self.path, [tone(300), silence(3000), tone(300)])
        tighten_pauses(self.path)
        self.assertLessEqual(duration_ms(self.path), 300 + 450 + 300 + 10)

    def test_nothing_to_do(self):
        write(self.path, [tone(300), silence(100), tone(300)])
        self.assertEqual(tighten_pauses(self.path), {"pauses_shortened": 0, "removed_ms": 0})
        write(self.path, [silence(500)])
        self.assertEqual(tighten_pauses(self.path)["pauses_shortened"], 0)


if __name__ == "__main__":
    unittest.main()
