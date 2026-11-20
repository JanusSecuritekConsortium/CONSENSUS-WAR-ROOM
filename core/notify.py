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

APP_ID = "JanusSecuritek.CONSENSUS"
_POWERSHELL_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"

# Names the sender "CONSENSUS" (a per-user entry under HKCU, no admin rights) and falls back to
# PowerShell's own app id if that entry cannot be written.
_TOAST_SCRIPT = r"""
$app = $env:CONSENSUS_ALERT_APP
try {
    $key = "HKCU:\Software\Classes\AppUserModelId\$app"
    New-Item -Path $key -Force -ErrorAction Stop | Out-Null
    New-ItemProperty -Path $key -Name DisplayName -Value 'CONSENSUS' -PropertyType String -Force -ErrorAction Stop | Out-Null
    if ($env:CONSENSUS_ALERT_ICON) {
        New-ItemProperty -Path $key -Name IconUri -Value $env:CONSENSUS_ALERT_ICON -PropertyType String -Force -ErrorAction Stop | Out-Null
    }
} catch { $app = $env:CONSENSUS_ALERT_FALLBACK_APP }
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$lines = $template.GetElementsByTagName('text')
$lines.Item(0).AppendChild($template.CreateTextNode($env:CONSENSUS_ALERT_TITLE)) | Out-Null
$lines.Item(1).AppendChild($template.CreateTextNode($env:CONSENSUS_ALERT_TEXT)) | Out-Null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($template))
"""


def _icon_path() -> str:
    try:
        from ui.assets.app_icon import resolve_app_icon_path

        icon = resolve_app_icon_path(prefer_ico=False)
    except Exception:
        return ""
    return str(icon) if icon else ""


def alerts_enabled() -> bool:
    return os.getenv("CONSENSUS_DESKTOP_ALERTS", "1").strip().lower() not in {"0", "false", "no", "off"}


def desktop_alert(title: str, text: str, *, launch: Optional[Callable[..., object]] = None) -> bool:
    """Show a Windows notification without waiting for it. Returns False when it was not shown."""
    if not alerts_enabled() or (launch is None and sys.platform != "win32"):
        return False
    env = {**os.environ, "CONSENSUS_ALERT_TITLE": title[:120], "CONSENSUS_ALERT_TEXT": text[:400],
           "CONSENSUS_ALERT_APP": APP_ID, "CONSENSUS_ALERT_FALLBACK_APP": _POWERSHELL_APP_ID,
           "CONSENSUS_ALERT_ICON": _icon_path()}
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
