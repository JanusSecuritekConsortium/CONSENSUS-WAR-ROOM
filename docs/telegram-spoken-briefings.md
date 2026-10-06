# Telegram spoken briefings

Set `telegram_briefing_format` to `ask` in the private account configuration
to offer a choice before each scheduled briefing: reply `1` for voice or `2`
for plain text. The default for other installations remains `text`.

Morning agenda, tasks and follow-ups remain separate from evening news. The
existing publisher archives the detailed Markdown locally. Both delivery
formats use the same concise digest; speech removes URLs, not factual qualifiers.

The sole Telegram receiver consumes choices locally, without invoking the agent
or interpreting a number as an email/calendar action. Reply directly to the
offer if more than one is pending. Offers expire after 18 hours. No choice means
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

Validation: `python -m pytest tests/test_spoken_briefing.py tests/test_voice_relay.py tests/test_personal_context_publication.py -q`.
