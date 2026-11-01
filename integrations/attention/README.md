# Personal Attention Manager

Tracks who is waiting for the user, what the user promised, what the user is
waiting on, and proposed meetings. It answers "what am I forgetting?" with one
short brief instead of another inbox. It reads, analyses, tracks and drafts.
It never sends messages and never changes a mailbox or calendar.

## Architecture

```text
Email accounts (existing read-only IMAP/Graph readers, integrations/msty/personal/connectors.py)
Configured ICS calendar (existing reader, availability only)
        │
        ▼
integrations/attention/scan.py ── only changed conversations ──► Msty Local AI (qwen3.5:9b, loopback only)
        │                                                        classify.py validates every answer
        ▼
<state folder>/system/state.sqlite3   ← single source of truth
        │  regenerated after every change
        ▼
<state folder>/attention, commitments, appointments, contacts, briefs   ← plain Markdown with YAML frontmatter
        │
        ├── Windows Task Scheduler (backup.py): scan every 30 min, brief at 08:05, Aurelius briefings
        ├── Msty Go scheduled jobs (msty_jobs.py): same jobs, currently failing (see below)
        ├── MCP tools: standalone server (mcp_server.py), compact subset on the CONSENSUS MCP connection
        └── CLI: python -m integrations.attention ...
```

The default state folder is `G:\Obsidian\Personal Attention`; set
`PERSONAL_ATTENTION_HOME` to move it. It works with any Markdown viewer;
Obsidian is not required. Copying the folder copies the complete state.
Credentials stay in the existing DPAPI store, never in this folder.

### Decisions

- **SQLite is authoritative; Markdown is generated.** Writes go through `store.py`,
  which validates state transitions and keeps closed items closed. A hand-edited
  file is copied to `system/conflicts/` before it is regenerated, never silently lost.
- **No new email monitor.** Email reuses the connectors and credentials behind the
  Aurelius briefings. Msty Go's own mail accounts have no watcher and no external
  read API, so they cannot feed this today.
- **Msty Go first, Windows as backup.** Msty Go scheduled jobs call MCP tools on the
  existing CONSENSUS MCP connection, a local stdio tool server; nothing here needs
  CONSENSUS.exe, the tribunal or Aurelius. Because those jobs currently fail (below),
  Windows Task Scheduler runs the same work through `backup.py`. The publisher's daily
  receipts keep one briefing per day whichever scheduler fires first.
- **Local inference only.** `config.loopback` rejects any non-local model endpoint.
  Only changed conversations are sent, at most the newest six messages each, with
  quoted history removed. Newsletters and no-reply senders never reach the model.
- **Attention, not archive.** Message bodies are not stored. Items keep a one-line
  summary, the next action, dates and a source reference.
- **Identities are not merged by name.** Each new address is its own contact; a
  matching name only creates a proposal that a person confirms (`contacts link`).

## Rhythm, drafts and contacts

- **One brief a day** (`brief_times`, default 08:00). Between briefs only very important
  items interrupt: urgent ones, or high-priority ones from a favourite contact. Each one
  raises a local desktop alert once (`notifier.py`); nothing is sent off this PC.
- **Old conversations stay quiet.** Up to `lookback_days` (60) are read, but replies and
  waits with no activity for `quiet_after_days` (30) never reach a brief or an alert.
  They remain queryable and are counted as "kept quietly".
- **Drafts in the owner's voice.** For each confident open reply, the scan prepares one
  draft from the conversation plus the owner's own recent sent messages (to that person
  first), copying language, greeting, sign-off and tone. The brief shows it as
  "Draft (not sent)". Sending always stays with the owner.
- **Google Contacts.** Save a Google CSV export (contacts.google.com, Export, Google CSV)
  as `<state folder>/system/google-contacts.csv`, or run `import-contacts PATH`. Names are
  taken from it, a Google contact's addresses join one person, and starred contacts become
  favourites, which rank one level higher. Addresses already tracked as different people
  are only proposed for linking, never merged.

## States and confidence

Conversations end as `NO_ACTION` or hold items. Items are `NEEDS_REPLY` (a question),
`WAITING_ON_ME` (a request), `WAITING_ON_OTHER`, `COMMITMENT_OPEN`,
`APPOINTMENT_PROPOSED`, `SNOOZED`, `COMPLETED`, `IGNORED` or `CANCELLED`. Commitments
show as open, overdue, done or cancelled. A reply by the user closes reply items and
may open a quiet waiting item; an answer from the other person closes that waiting
item and the conversation is evaluated again.

Confidence of at least 0.85 is tracked; 0.60 to 0.85 is listed under "to confirm"
at low priority; below 0.60 is kept only on the conversation for the next change.
Priority rules are in `priority.py`, and every item stores its reasons. Thresholds,
model, times and limits are in `<state folder>/system/settings.json`.

## Commands

```powershell
cd G:\CONSENSUS_SYSTEM
.\.venv\Scripts\python.exe -m integrations.attention status
.\.venv\Scripts\python.exe -m integrations.attention scan
.\.venv\Scripts\python.exe -m integrations.attention brief
.\.venv\Scripts\python.exe -m integrations.attention list --kind commitment
.\.venv\Scripts\python.exe -m integrations.attention done ITEM_ID
.\.venv\Scripts\python.exe -m integrations.attention snooze ITEM_ID tomorrow
.\.venv\Scripts\python.exe -m integrations.attention draft ITEM_ID
.\.venv\Scripts\python.exe -m integrations.attention pause      # scans become no-ops
.\.venv\Scripts\python.exe -m integrations.attention resume
```

### Windows backup schedule

Tasks in the Task Scheduler folder `\CONSENSUS\` run `pythonw -m integrations.attention.backup`
with `scan` (every 30 minutes), `brief` (08:05), `briefing morning` (07:05) and
`briefing evening` (17:35), only while the user is signed in. A briefing outside its
window is skipped, never sent late. Results go to `<state folder>/system/backup.log`.

### Msty Go jobs: known failure

Since Msty Go 1.1.0-beta.3 (installed 2026-10-28 18:33), every job that reads a
CONSENSUS MCP tool fails within milliseconds with "The live data source … is not
currently available. Reconnect it before this task can run." This is a Msty Go bug, not
the MCP server: the headless worker starts its scheduler with an empty list of
connected tools (`createSchedulerPump({availableMcpTools: []})` in `msty-go-worker.exe`
1.4.0), so the availability check rejects every MCP source before calling it.
Reconnecting the server or restarting Msty Go does not help; the server answers
`initialize` in under a second when started the way Msty Go starts it. Jobs without a
live source (plain reminders, agent prompts) are unaffected. Report it to Msty and
recheck after the next Msty Go update.

Schedule in Msty Go (close Msty Go completely first, then reopen it):

```powershell
.\.venv\Scripts\python.exe -m integrations.attention.msty_jobs            # dry run
.\.venv\Scripts\python.exe -m integrations.attention.msty_jobs --apply
.\.venv\Scripts\python.exe -m integrations.attention.msty_jobs --remove --apply
```

Other MCP hosts can run the full tool set with
`.\.venv\Scripts\python.exe -m integrations.attention serve-mcp`.

## Sources

| Source | State | Notes |
|---|---|---|
| Email | Working | Inbox and Sent of enabled accounts, last 60 days (`lookback_days`), 60 messages per folder |
| Calendar | Working for availability | ICS calendar; candidates are never added, accepted or declined |
| Telegram | Signed in 2026-11-01; read live | One-to-one chats with people, read through the user's own account (Telegram's user API). No groups, channels or bots; nothing sent or marked read. |
| WhatsApp | Linked 2026-11-01; history and live messages stored | One-to-one chats through a linked device (unofficial neonize/whatsmeow client; see the risk below). Text only, no groups, status or channels; nothing sent or marked read. |

Chats become one conversation per person, using the same lookback window, quiet period,
model and draft rules as email. Drafts copy how the owner writes on that channel.
`telegram_chats` or `whatsapp_chats` set to false in `settings.json` stops reading one.

### Telegram personal chats

1. At my.telegram.org → API development tools, create an app and note `api_id` and `api_hash`.
2. Run `.\.venv\Scripts\python.exe -m integrations.attention.telegram_user setup` from the
   repository folder, enter them with the phone number, press Send code, then type the code
   (and the cloud password, if one is set).

The api_id/api_hash and session are kept with Windows DPAPI in the private Aurelius folder.
`telegram_user forget` signs the reader out; it can also be ended in Telegram → Devices.

### WhatsApp personal chats

WhatsApp has no official way to read your own chats. A linked device through an unofficial
client is against WhatsApp's terms and can, rarely, get a number restricted; reading only is
the lowest-risk use. If WhatsApp logs the device out or restricts it, the listener stops and
does not reconnect until it is paired again.

1. Run `.\.venv-whatsapp\Scripts\python.exe -m integrations.attention.whatsapp pair` and scan the code
   in WhatsApp → Settings → Linked devices → Link a device. Keep the window open a few
   minutes while recent history arrives.
2. `whatsapp listen` keeps the local copy current. It must run while the PC is on (the `\CONSENSUS\WhatsApp listener`
   Windows sign-in task); a linked device only receives messages while it is connected, and
   messages sent while it was off arrive when it reconnects.

The device keys and the message copy (90 days, text only) live in the private Aurelius
folder under `whatsapp`. `whatsapp status` reports the link; `whatsapp forget` unlinks and
deletes the copy. The scan marks WhatsApp `stale` when the listener has not been heard from
for 30 minutes, and still uses the stored copy.

Extra packages: `pip install -r integrations/attention/requirements-chats.txt` in `.venv`.
WhatsApp rejects neonize 0.3.18 as outdated (error 405), and newer releases need Python 3.11
or newer, so pairing and the listener have their own environment. Create `.venv-whatsapp`
with Python 3.12 and install `requirements-whatsapp.txt` there. The scan only reads the
stored copy and stays in `.venv`.

## Tests

`python -m pytest tests/test_attention.py tests/test_attention_chats.py` runs offline with a fake source and
model in a temporary folder. It does not read mail, call Msty or open windows.
