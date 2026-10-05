# Telegram voice input

The local receiver accepts text, Telegram voice notes, audio attachments and audio
documents from the existing private Aurelius chat only. It downloads at most 20 MB,
transcribes at most ten minutes with local multilingual Whisper, removes the audio
file after processing, and forwards the text to the existing Msty Go Aurelius agent
through its authenticated local MCP `enqueue_prompt` tool. The same local model,
memory and action tools remain in use. Forwarded material is labelled as reference
data rather than authorization. Calls and spoken replies are not implemented.

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

- `G:\Tools\Aurelius Voice Receiver.cmd` starts the receiver; a single-instance
  lock prevents competing copies. A Windows Startup shortcut runs it at sign-in.
- `python -m integrations.msty.personal.voice_relay status` reports health;
  `waiting_for_msty` means reception is alive but the agent endpoint is unavailable.
- `python -m integrations.msty.personal.voice_setup` opens the local URL/token
  form. Tokens are stored with Windows DPAPI and are never placed in chat or source.
- Msty Go currently changes its local MCP bearer token after restart. Open
  Settings → Tools → Built-in Server, copy its current Auth into the local setup
  form, and save. No receiver restart is necessary. An unavailable endpoint leaves
  prepared requests waiting; it does not authorize replaying uncertain actions.
- `python -m integrations.msty.personal.voice_relay stop` stops reception after its
  current work. It deliberately does not restart native polling automatically.

To return to native text-only routing, stop this receiver first, restore only the
saved original agent binding and channel auto-connect setting, and reload Msty Go.
Do not start both pollers. Never restore the full database over newer user data
merely to undo this integration.
