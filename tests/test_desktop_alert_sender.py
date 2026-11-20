from __future__ import annotations

from core import notify
from ui.owner_questions import bring_window_forward


def test_alerts_are_sent_as_consensus_with_a_powershell_fallback(monkeypatch):
    monkeypatch.setenv("CONSENSUS_DESKTOP_ALERTS", "1")
    calls = []
    assert notify.desktop_alert("Title", "Text", launch=lambda command, **kwargs: calls.append(kwargs["env"]))
    env = calls[0]
    assert env["CONSENSUS_ALERT_APP"] == "JanusSecuritek.CONSENSUS"
    assert env["CONSENSUS_ALERT_FALLBACK_APP"].endswith(r"WindowsPowerShell\v1.0\powershell.exe")
    assert "DisplayName -Value 'CONSENSUS'" in notify._TOAST_SCRIPT
    assert "catch { $app = $env:CONSENSUS_ALERT_FALLBACK_APP }" in notify._TOAST_SCRIPT


def test_alerts_stay_off_when_switched_off(monkeypatch):
    monkeypatch.setenv("CONSENSUS_DESKTOP_ALERTS", "0")
    assert not notify.desktop_alert("Title", "Text", launch=lambda *a, **k: None)


class _Window:
    def __init__(self, fail=False):
        self.minimized = True
        self.raised = False
        self.fail = fail

    def to_front(self):
        if self.fail:
            raise RuntimeError("window gone")
        self.raised = True


class _Page:
    def __init__(self, window):
        self.window = window
        self.updates = 0

    def update(self):
        self.updates += 1


def test_the_window_is_restored_and_raised_for_questions():
    page = _Page(_Window())
    assert bring_window_forward(page)
    assert page.window.raised and not page.window.minimized and page.updates == 1


def test_a_window_that_cannot_be_raised_never_stops_the_vote():
    assert not bring_window_forward(_Page(_Window(fail=True)))
    assert not bring_window_forward(object())
