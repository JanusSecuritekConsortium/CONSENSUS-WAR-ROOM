"""CONSENSUS lives on a portable SSD whose drive letter can change between PCs: defaults follow the running drive."""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import paths

# Modules whose default locations (vault, Aurelius store, briefings, Msty backups, Msty job workspace) are on the SSD.
PORTABLE_MODULES = [
    "core/knowledge/second_brain.py", "core/knowledge/ghostnotes.py", "integrations/msty/personal/store.py",
    "integrations/msty/personal/publication.py", "integrations/msty/personal/schedules.py",
    "integrations/msty/memory_packs.py", "integrations/attention/msty_jobs.py", "integrations/attention/config.py",
    "voice/riko_adapter.py",
]
DRIVE_LETTER_PATH = re.compile(r"""['"][A-Za-z]:[\\/]""")


class PortableDriveTest(unittest.TestCase):
    def test_the_drive_is_the_one_consensus_runs_from(self):
        with mock.patch.dict(os.environ, {"CONSENSUS_PORTABLE_DRIVE": ""}):
            self.assertEqual(paths.resolve_portable_drive(), Path(paths.SYSTEM_ROOT.anchor))

    def test_the_owner_can_name_another_drive(self):
        with mock.patch.dict(os.environ, {"CONSENSUS_PORTABLE_DRIVE": "E:\\"}):
            self.assertEqual(paths.resolve_portable_drive(), Path("E:\\"))

    def test_defaults_follow_the_drive(self):
        with mock.patch.object(paths, "PORTABLE_DRIVE", Path("E:\\")):
            self.assertEqual(paths.on_portable_drive("Obsidian", "Personal Attention"), Path("E:\\") / "Obsidian" / "Personal Attention")

    def test_no_module_names_a_drive_letter(self):
        for name in PORTABLE_MODULES:
            source = (ROOT / name).read_text(encoding="utf-8")
            self.assertEqual(DRIVE_LETTER_PATH.findall(source), [], name)

    def test_the_msty_job_prompt_runs_from_this_checkout(self):
        schedules = importlib.import_module("integrations.msty.personal.schedules")
        source = (ROOT / "integrations/msty/personal/schedules.py").read_text(encoding="utf-8")
        self.assertIn("SYSTEM_ROOT.as_posix() + '/.venv/Scripts/python.exe", source)
        self.assertTrue(hasattr(schedules, "SYSTEM_ROOT"))


if __name__ == "__main__":
    unittest.main()
