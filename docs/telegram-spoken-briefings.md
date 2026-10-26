# Telegram spoken briefings

Set `telegram_briefing_format` to `ask` in the private account configuration
to offer a choice before each scheduled briefing: reply `1` for voice or `2`
for plain text. The default for other installations remains `text`.

Morning agenda, tasks and follow-ups remain separate from evening news. The
existing publisher archives the detailed Markdown locally. Both delivery
formats use the same concise digest; speech removes URLs, not factual qualifiers.

## Reading instructions

Read as a calm narrator, using punctuation for pauses and intonation. Do not
announce "hyphen", "dash", "slash", "asterisk", "bullet", "open parenthesis"
or other formatting names unless the text explicitly discusses that symbol.
Read the words inside emphasis, quotes, brackets and parentheses naturally.
Use a short pause for a prose dash or middle dot and a sentence pause between
headings and list items. Keep compound words fluent. Read numeric and time
ranges as "to" and negative values as "minus"; never discard their meaning.
Preserve names, source attribution, facts, uncertainty and warnings.

The local speech engine accepts text rather than a model instruction prompt, so
these rules are applied before synthesis by `prepare_speech_text`. Briefing
`narration` also removes URLs and expands the publisher's day/month timestamps:
`BBC World · 09/10 17:32: Headline` becomes
`BBC World, the ninth of October at seventeen thirty two: Headline`.
Visual Markdown and separators do not become spoken formatting words. The
written digest remains the source of truth for exact links and timestamps.

## Routine agenda reminders

Private account configuration can set `agenda_reminder_excluded_titles` to a
list of exact event titles. Matching ignores case and repeated whitespace.
Only these named events are omitted from the concise agenda reminder used for
text and voice; other recurring events continue to appear. Filtering happens
before the message length limit, leaving room for other appointments.

Calendar sources and the full local agenda retain all events. A retained
appointment overlapping an excluded event still produces a conflict warning,
with the excluded title described as a "routine calendar block". Direct requests
to show the full calendar continue to include its complete schedule. A fresh
scheduled publisher process reads the configuration for each briefing.

## Locations on request

Agenda reminders and general agenda replies omit locations by default. Private
configuration can explicitly opt in with `agenda_include_locations_by_default`;
the source calendar and detailed local archive always retain recorded locations.
Ask `Where is my meeting today?`, `Where is Project review tomorrow?`, or
`Show my schedule today with locations` to request them. A singular location
question with multiple matching appointments asks which one, and an event without
a recorded location is reported as unavailable rather than guessed.

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

## Direct agenda questions

The receiver handles simple English schedule/agenda/calendar requests for today or tomorrow, optionally morning (00:00–12:00), afternoon (12:00–18:00) or evening (18:00–24:00), through fresh calendar reads without Msty. Responses include event titles, times, overlaps and source limitations. Ambiguous or unsupported requests remain on the agent route. If the agent connection fails before dispatch, the user receives an explicit failure response; no action is claimed or silently queued indefinitely.

## Calendar changes and conversation controls

Briefings include a bounded change section comparing upcoming appointments with
the most recent successfully delivered structured calendar snapshot. Preparing
an archive, offering a format, and uncertain delivery do not advance that baseline.
The first delivered snapshot establishes it; earlier text-only archives cannot
be reliably reconstructed into events. One-off events use source and UID;
recurrences also use the original recurrence ID, so a moved instance remains
identifiable. Changes include additions, time/duration changes, renamed events,
explicit cancellations, and removals qualified as cancellation unconfirmed.
Calendar limits, changed sources, unavailable feeds, ambiguous IDs and dates
outside comparable windows do not establish cancellations. Named routine
exclusions also apply to change highlights. Locations stay on request.

Typed messages and locally transcribed voice notes use the same local command
router. Examples: `What is next?`, `What changed?`, `Where is my next meeting?`,
`¿Qué sigue?`, `¿Qué ha cambiado?`, `¿Dónde es mi reunión hoy?`, and
`Muestra mi agenda mañana`. Next-event queries search the retrieved seven-day
window. General schedule queries retain overlap checks and support all-day events.
These local commands work while the model connection is unavailable.

Direct replies, errors and control buttons match English or Spanish. Explicit
language requests override detection; voice language detection supplies a hint.
Short ambiguous choices reuse the previous conversation language. Source names,
event titles and email subjects stay unchanged. Scheduled briefings and news
retain the English default. Agent conversation prompts carry the detected language;
arbitrary conversation still requires the existing model connection.

Use `Follow-ups` / `Seguimientos` to select a specific saved task or email
candidate from the latest briefing. Select `Handled` / `Hecho` to stop its
reminders, or `Tomorrow` / `Mañana` to restore it in the next day's briefing
(Europe/Madrid date, including daylight-saving changes). You can also reply to
the numbered selector with `handled 1` / `hecho 1` or `tomorrow 1` / `mañana 1`.
`I've handled this` and `Recuérdamelo mañana` work when replying to a message
bound to one item; otherwise a selector asks which item. A number without a
reply context cannot dismiss an item. These private overlays affect concise
reminders; source tasks, email and calendar records stay intact. A new incoming
email is a distinct item even when its subject matches a dismissed email.

Telegram offers include Read aloud/Text buttons. Delivered text and direct
replies include Read aloud, What's next?, Where? and Follow-ups controls;
voice messages include navigation controls. Buttons expire after 18 hours and
are bound to the configured private owner and acknowledged message. Callback
data contains only random opaque tokens; payloads remain in a private SQLite
store. The single receiver polls both messages and callback queries, acknowledges
button presses, and retains durable deduplication and uncertain-send protection.
Protocol reference: [Telegram inline keyboards](https://core.telegram.org/bots/api#inlinekeyboardmarkup).

Spanish narration selects an installed Spanish system voice before the existing
Aurelius conversion and spells the 24-hour clock in Spanish. If that voice or
conversion is unavailable before upload, the exact Spanish text is delivered.
No additional cloud speech provider is configured.
