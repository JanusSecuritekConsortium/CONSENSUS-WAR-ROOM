from __future__ import annotations

from typing import Optional, Protocol

from assistant.aurelius_runtime import AureliusResult, get_aurelius_runtime
from voice.speech_events import SpeechEvent, SpeechEventType


class CalendarAnnouncer(Protocol):
    def announce(self, event: SpeechEvent) -> AureliusResult:
        ...


def announce_calendar_event(
    action: str,
    title: str,
    start_time: str = "",
    announcer: Optional[CalendarAnnouncer] = None,
) -> AureliusResult:
    normalized = action.strip().lower()
    if normalized == "created":
        event_type = SpeechEventType.APPOINTMENT_CREATED
        text = f"{title}. Scheduled for {start_time}." if start_time else title
    elif normalized == "reminder":
        event_type = SpeechEventType.APPOINTMENT_REMINDER
        text = f"{title}. Begins at {start_time}." if start_time else title
    else:
        event_type = SpeechEventType.APPOINTMENT_SUMMARY
        text = title

    runtime = announcer or get_aurelius_runtime()
    return runtime.announce(
        SpeechEvent(
            event_type=event_type,
            text=text,
            priority=6,
            source="MSTY_CLAW_CALENDAR",
            metadata={"action": normalized, "title": title, "start_time": start_time},
        )
    )
