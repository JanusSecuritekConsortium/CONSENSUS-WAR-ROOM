# Telegram voice input

The local receiver accepts text, Telegram voice notes, audio attachments and audio
documents from the existing private Aurelius chat only. It downloads at most 20 MB,
transcribes at most ten minutes with local multilingual Whisper, removes the audio
file after processing, and forwards the text to the existing Msty Go Aurelius agent
through its authenticated local MCP `enqueue_prompt` tool. The same local model,
memory and action tools remain in use. Forwarded material is labelled as reference
data rather than authorization. Calls are not implemented.

## Spoken replies

A direct voice note gets its answer twice: the text reply first, as before, then the
same answer as a Telegram voice note in the local Aurelius voice (Windows voice plus
RVC conversion, Spanish or English to match the note), sent as a reply to the note.
Narration runs on a background thread, one at a time, so polling never waits for it;
on CPU it takes about a minute for a short answer. Typed text, forwarded audio, error
replies and answers over 1500 characters stay text-only. A failed narration is
recorded in the inbox row (`voice_reply_failed:…`) and never resent; the text reply
already arrived. Set `telegram_spoken_replies` to false in the local account store
to turn it off.

There is one Telegram polling owner. The native Msty Telegram connection must stay
disconnected, its auto-connect flag disabled, and the original agent's Telegram
binding removed while this receiver is enabled. The previous binding is saved in
the private `voice-relay-before.json`; the complete Msty backup path is recorded
there. Channel credentials and briefing destinations remain in the existing Msty
database; the briefing publisher still sends directly through that route.

`voice-relay.sqlite3` privately stores incoming messages, transcripts and delivery
states. Updates are persisted before their polling offset advances. Dispatch and
delivery ambiguity do not trigger automatic duplicates. Only completed assistant
replies are sent, bounded to one plain-text Telegram message. The receiver does not
execute actions itself. A timed-out action must be reconciled before resending.

Response correlation uses a receipt and a pre-dispatch database watermark. When
Msty's privacy filter redacts the receipt, its recorded redaction spans are applied
to the known outgoing prompt for comparison against new messages from this agent.
Only one exact matching turn is accepted; ambiguous matches are not delivered.
The privacy filter remains enabled. Tool-bearing intermediate replies are withheld.

## Run and reconnect

Agent/channel identifiers are private configuration, not source defaults. Set
`msty_bot_id` and `msty_channel_id` in the local account store, or use
`AURELIUS_MSTY_BOT_ID` and `AURELIUS_MSTY_CHANNEL_ID`. Existing installations
retain their identifiers locally. Never commit the populated store.

- `G:\Tools\Aurelius Voice Receiver.cmd` starts the receiver; a single-instance
  lock prevents competing copies. A Windows Startup shortcut runs it at sign-in.
- `python -m integrations.msty.personal.voice_relay status` reports health;
  `waiting_for_msty` means Telegram reception is alive. Read `msty_failure` and
  `msty_checked_at` for the last Msty Go check. For `unreachable`, check that the
  local Built-in Server is running. For `unauthorized`, refresh the saved token.
  After a sustained outage the relay sends one outage alert. If the server returns
  and rejects the saved token, the relay sends one follow-up with the token instructions.
- `python -m integrations.msty.personal.voice_setup` opens the local URL/token
  form. Tokens are stored with Windows DPAPI and are never placed in chat or source.
- Msty Go currently changes its local MCP bearer token after restart. Open
  Settings → Tools → Built-in Server, copy its current Auth into the local setup
  form, and save. The token exists only in Msty Go's memory, so it cannot be read
  automatically; instead, the first time the server rejects the saved token the relay
  opens this form on the PC, once per restart, with the saved URL already filled in.
  Set `open_token_form` to false in the local account store to turn that off.
  No receiver restart is necessary. If the relay cannot reach
  Msty Go before dispatch, it returns an offline reply. Requests with an uncertain
  dispatch outcome are never retried automatically.
- `python -m integrations.msty.personal.voice_relay stop` stops reception after its
  current work. It deliberately does not restart native polling automatically.

To return to native text-only routing, stop this receiver first, restore only the
saved original agent binding and channel auto-connect setting, and reload Msty Go.
Do not start both pollers. Never restore the full database over newer user data
merely to undo this integration.
