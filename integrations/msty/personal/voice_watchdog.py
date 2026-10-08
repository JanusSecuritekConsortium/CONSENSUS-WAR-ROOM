"""User-session receiver supervisor, with no visible console or admin task."""
from pathlib import Path
import subprocess
import sys
import time

from . import store
from .voice_relay import single_instance


def run():
    with single_instance('voice-watchdog.lock'):
        while store.load().get('telegram_voice_relay_enabled'):
            subprocess.run([sys.executable, '-m', 'integrations.msty.personal.voice_relay', 'run'],
                           cwd=Path(__file__).resolve().parents[3],
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(10)


if __name__ == '__main__':
    run()
