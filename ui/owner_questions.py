"""The desktop window's side of the owner rule: when the voters cannot agree, show their questions,
wait for the owner's answer, and give it to the rerun (an empty answer or SKIP ends the reruns).

The vote runs in a worker thread; the dialog lives on the window. GuiOwnerAsker blocks the worker
until the owner replies, the vote is cancelled, or the wait runs out.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

ANSWER_WAIT_SECONDS = 24 * 60 * 60  # same as a background vote: then the vote ends with its result
CHECK_SECONDS = 1.0

ShowQuestions = Callable[[list, Callable[[Optional[str]], None]], None]


def question_lines(questions: list) -> list[str]:
    """One readable line per question, prefixed with the voter who asks it."""
    lines: list[str] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        agent = str(item.get("agent") or "VOTER")
        vote = str(item.get("vote") or "")
        for ask in item.get("asks") or []:
            lines.append(f"{agent}{f' ({vote})' if vote else ''}: {ask}")
    return lines


class GuiOwnerAsker:
    """ask_owner for a vote started in the window."""

    def __init__(self, show: ShowQuestions, *, check: Callable[[], None] = lambda: None,
                 alert: Callable[[list], Any] = lambda questions: None,
                 wait_seconds: float = ANSWER_WAIT_SECONDS, clock: Callable[[], float] = time.monotonic,
                 dismiss: Callable[[], None] = lambda: None) -> None:
        self.show = show
        self.dismiss = dismiss  # closes the dialog when the vote stops waiting without a reply
        self.check = check  # raises when the owner cancels the vote
        self.alert = alert
        self.wait_seconds = wait_seconds
        self.clock = clock

    def __call__(self, questions: list) -> Optional[str]:
        replied = threading.Event()
        holder: dict[str, Optional[str]] = {"answer": None}

        def reply(answer: Optional[str]) -> None:
            holder["answer"] = " ".join(str(answer or "").split()) or None
            replied.set()

        self.show(questions, reply)
        self.alert(questions)
        deadline = self.clock() + self.wait_seconds
        try:
            while not replied.wait(CHECK_SECONDS):
                self.check()
                if self.clock() >= deadline:
                    return None
        finally:
            if not replied.is_set():
                self.dismiss()
        return holder["answer"]


def build_question_dialog(ft: Any, questions: list, reply: Callable[[Optional[str]], None],
                          close: Callable[[Any], None]) -> Any:
    """The window's dialog: the voters' questions, one answer box, Send and Skip."""
    answer = ft.TextField(label="YOUR ANSWER (it reaches every voter)", multiline=True, min_lines=3,
                          max_lines=8, autofocus=True)
    done = {"sent": False}

    def finish(text: Optional[str]) -> None:
        if done["sent"]:
            return
        done["sent"] = True
        close(dialog)
        reply(text)

    questions_view = ft.Column([ft.Text(line, selectable=True) for line in question_lines(questions)],
                               spacing=6, scroll=ft.ScrollMode.AUTO, height=220)
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("The voters need your answer"),
        content=ft.Column([
            ft.Text("They could not agree. Answer their questions and the vote reruns with your answer. "
                    "Skip ends the vote with its current result."),
            questions_view,
            answer,
        ], tight=True, width=640, spacing=10),
        actions=[
            ft.TextButton("SKIP", on_click=lambda _: finish(None)),
            ft.FilledButton("SEND ANSWER", on_click=lambda _: finish(answer.value)),
        ],
    )
    return dialog


def bring_window_forward(page: Any) -> bool:
    """Restore and raise the CONSENSUS window so the owner sees the questions. Never stops the vote."""
    window = getattr(page, "window", None)
    if window is None:
        return False
    try:
        if getattr(window, "minimized", False):
            window.minimized = False
        window.to_front()
        page.update()
    except Exception:
        return False
    return True
