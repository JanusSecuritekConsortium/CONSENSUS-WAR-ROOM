"""Local desktop alert for very important items. Shown on this PC only; nothing is sent anywhere."""
from __future__ import annotations

import os
import subprocess

# The text arrives through environment variables, so it is never parsed as PowerShell code.
SCRIPT = r'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$lines = $template.GetElementsByTagName('text')
$lines.Item(0).AppendChild($template.CreateTextNode($env:ATTENTION_TITLE)) | Out-Null
$lines.Item(1).AppendChild($template.CreateTextNode($env:ATTENTION_TEXT)) | Out-Null
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show(
    [Windows.UI.Notifications.ToastNotification]::new($template))
'''


def desktop(title: str, text: str) -> None:
    environment = dict(os.environ, ATTENTION_TITLE=title[:80], ATTENTION_TEXT=text[:400])
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', SCRIPT], env=environment,
                   check=True, capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
