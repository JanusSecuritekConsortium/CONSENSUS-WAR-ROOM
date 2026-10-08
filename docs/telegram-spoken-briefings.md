# Telegram spoken briefings

Set `telegram_briefing_format` to `ask` in the private account configuration
to offer a choice before each scheduled briefing: reply `1` for voice or `2`
for plain text. The default for other installations remains `text`.

Morning agenda, tasks and follow-ups remain separate from evening news. The
existing publisher archives the detailed Markdown locally. Both delivery
formats use the same concise digest; speech removes URLs, not factual qualifiers.

The sole Telegram receiver consumes choices locally, without invoking the agent
or interpreting a number as an email/calendar action. Reply directly to the
offer to select that specific briefing; a plain number selects the latest pending
offer. Reply to a delivered digest with `read it aloud` or `1` to request its
spoken version. Offers expire after 18 hours. No choice means
no briefing payload is sent. Forwarded choices and other senders are ignored.

Narration uses `AureliusAdapter` and the assigned `AURELIUS` profile, including
its existing voice conversion settings. Arbiter's profile is unchanged. Local
FFmpeg converts the generated WAV into Ogg Opus for Telegram `sendVoice`.
Temporary audio stays in the private runtime directory and is removed afterward.
No cloud speech service is used. Source: [Telegram Bot API](https://core.telegram.org/bots/api#sendvoice).

Receipts persist the offer, selected format and final acknowledgement. Delivery
uncertainty never triggers an automatic resend. Rendering failure before upload
falls back to the exact text digest and records `local_narration_failed` in the
private receipt. A receiver restart loads code changes; do not enable a second
Telegram poller. Existing conversational replies continue to match the incoming
language, while scheduled briefings use English.

For user-session recovery, launch `pythonw -m integrations.msty.personal.voice_watchdog`
from the repository directory through the existing Windows startup shortcut.
The supervisor restarts the receiver after exits and both enforce singleton locks.
It uses hidden processes and requires no administrator service. A startup database
failure is retried. Pending agent requests no longer prevent polling new format
choices. Old non-choice requests recovered after an outage require resubmission
before any agent action. The computer must be on and the user logged in.

## Optional shared news folder

Install `integrations/msty/personal/requirements-news.txt` for PDF extraction.
In the private account configuration, `shared_news_folders` is a list of objects
with `label`, `path`, and `enabled`. Use an explicitly shared local, synced, or
UNC folder path; a website sharing link must first be made available locally.
No folders are discovered or enabled automatically.

The evening publisher reads Markdown and text PDFs without modifying them. It
includes up to three attributed excerpts from files modified within 36 hours,
separate from current news. Modification times are not asserted as event dates.
Detailed provenance and hashes stay in the private briefing vault; Telegram gets
bounded excerpts where space permits. Each folder scan is limited to 500 files,
10 MB per document and the first 10 PDF pages. Scanned PDFs need OCR and produce
a visible coverage warning. Missing or unreadable sources are reported. Folder
contents are reference data, never executable instructions.

Validation: `python -m pytest tests/test_spoken_briefing.py tests/test_voice_relay.py tests/test_personal_context_publication.py -q`.
