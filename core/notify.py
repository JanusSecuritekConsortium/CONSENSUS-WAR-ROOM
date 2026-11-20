"""Desktop alerts for the owner: a Windows notification that needs no extra packages.

Used when a vote is waiting for the owner's answers. Alerts stay on this PC; nothing is sent
anywhere else. Turn them off with CONSENSUS_DESKTOP_ALERTS=0 (the tests do).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable, Optional

from core.logging import log_error, log_event

# PowerShell's own app id, so Windows shows the notification without registering an app.
_TOAST_SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$lines = $template.GetElementsByTagName('text')
$lines.Item(0).AppendChild($template.CreateTextNode($env:CONSENSUS_ALERT_TITLE)) | Out-Null
$lines.Item(1).AppendChild($template.CreateTextNode($env:CONSENSUS_ALERT_TEXT)) | Out-Null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($template))
"""


def alerts_enabled() -> bool:
    return os.getenv("CONSENSUS_DESKTOP_ALERTS", "1").strip().lower() not in {"0", "false", "no", "off"}


def desktop_alert(title: str, text: str, *, launch: Optional[Callable[..., object]] = None) -> bool:
    """Show a Windows notification without waiting for it. Returns False when it was not shown."""
    if not alerts_enabled() or (launch is None and sys.platform != "win32"):
        return False
    env = {**os.environ, "CONSENSUS_ALERT_TITLE": title[:120], "CONSENSUS_ALERT_TEXT": text[:400]}
    command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _TOAST_SCRIPT]
    try:
        (launch or subprocess.Popen)(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as exc:  # an alert must never stop a vote
        log_error("desktop_alert_failed", exc, {"title": title})
        return False
    log_event("desktop_alert_shown", {"title": title})
    return True


def questions_alert(questions: list) -> bool:
    """Tell the owner that a vote is paused for their answers."""
    count = sum(len(item.get("asks") or []) for item in questions if isinstance(item, dict)) or len(questions)
    voters = ", ".join(str(item.get("agent")) for item in questions if isinstance(item, dict) and item.get("agent"))
    return desktop_alert("CONSENSUS needs your answer",
                         f"The voters could not agree. {voters or 'They'} asked {count} question(s); "
                         "the vote waits for your answer.")
