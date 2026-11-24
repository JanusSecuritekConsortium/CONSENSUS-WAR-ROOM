from __future__ import annotations

import threading

import flet as ft
import pytest

from ui.owner_questions import GuiOwnerAsker, build_question_dialog, question_lines

QUESTIONS = [{"agent": "AETERNUM", "vote": "ABSTAIN", "asks": ["What is the budget?", "By when?"]},
             {"agent": "BELLATOR", "vote": "ABSTAIN", "asks": ["Who decides?"]}]


def test_question_lines_name_the_voter_for_each_question():
    assert question_lines(QUESTIONS) == ["AETERNUM (ABSTAIN): What is the budget?",
                                         "AETERNUM (ABSTAIN): By when?",
                                         "BELLATOR (ABSTAIN): Who decides?"]


def test_the_owner_answer_reaches_the_rerun_and_an_alert_is_shown():
    alerts = []

    def show(questions, reply):
        threading.Timer(0.05, reply, args=["  The budget is 500 euros,\n by March. "]).start()

    asker = GuiOwnerAsker(show, alert=alerts.append)
    assert asker(QUESTIONS) == "The budget is 500 euros, by March."
    assert alerts == [QUESTIONS]


def test_skip_ends_the_reruns():
    asker = GuiOwnerAsker(lambda questions, reply: reply(None))
    assert asker(QUESTIONS) is None


def test_no_answer_in_time_ends_the_reruns_and_closes_the_dialog():
    dismissed = []
    ticks = iter([0.0, 10.0])
    asker = GuiOwnerAsker(lambda questions, reply: None, wait_seconds=5, clock=lambda: next(ticks),
                          dismiss=lambda: dismissed.append(True))
    assert asker(QUESTIONS) is None
    assert dismissed == [True]


def test_cancelling_the_vote_while_it_waits_closes_the_dialog():
    class Cancelled(Exception):
        pass

    dismissed = []

    def check():
        raise Cancelled()

    asker = GuiOwnerAsker(lambda questions, reply: None, check=check, dismiss=lambda: dismissed.append(True))
    with pytest.raises(Cancelled):
        asker(QUESTIONS)
    assert dismissed == [True]


def test_the_dialog_sends_the_typed_answer_once():
    replies, closed = [], []
    dialog = build_question_dialog(ft, QUESTIONS, replies.append, closed.append)
    answer_box = dialog.content.controls[2]
    answer_box.value = "Yes, go ahead."
    skip, send = dialog.actions
    send.on_click(None)
    skip.on_click(None)
    assert replies == ["Yes, go ahead."]
    assert closed == [dialog]


def test_a_real_window_vote_reruns_and_asks_the_owner(monkeypatch):
    """Simulated votes stay at three rounds; a real one gets the reruns and the owner's questions."""
    from config.runtime import RuntimeConfig
    from ui import flet_app

    captured = {}

    def fake_cast_votes(self, *args, **kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop after the call")

    monkeypatch.setattr(flet_app.VotingOrchestrator, "cast_votes", fake_cast_votes)
    state = flet_app.create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    state.config = RuntimeConfig(theme="janus", backend="msty-local")
    asker = object()
    with pytest.raises(RuntimeError):
        flet_app.submit_proposal_live_for_gui(state, "Buy a second backup drive?", skip_animations=True,
                                              ask_owner=asker)
    assert captured["ask_owner"] is asker
    assert captured["extra_rounds"] == 3
    assert captured["consensus_check"] is not None


def test_an_empty_answer_is_refused_with_an_explanation():
    replies, closed = [], []
    dialog = build_question_dialog(ft, [{"agent": "BELLATOR", "vote": "ABSTAIN", "asks": ["Budget?"]}],
                                   replies.append, closed.append)
    answer_box = dialog.content.controls[2]
    skip, send = dialog.actions
    answer_box.value = "   "
    send.on_click(None)
    assert replies == [] and closed == [] and "SKIP" in answer_box.error_text
    assert answer_box.max_length == 4000
    answer_box.value = "Budget is 2,000 euros."
    send.on_click(None)
    assert replies == ["Budget is 2,000 euros."]
