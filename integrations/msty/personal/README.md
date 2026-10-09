# Aurelius local integrations

These connectors run on this PC, under Msty's existing local model. They do not
use Codex Gmail/Outlook connectors or send content to a hosted language model.
All accounts start disabled. Successful authentication is required before any
connection can be called operational.

## Explicit actions by text

`aurelius_action` on CONSENSUS MCP and the Aurelius operator's `personal_action`
workflow prepare and execute individually requested emails and Proton appointments.
Install `requirements-actions.txt` for this optional extension. Read-only briefing
collection remains separate; a suggested follow-up never authorizes sending mail.

Supported sending accounts are enabled IMAP/Gmail/iCloud/Proton Bridge profiles.
An action requires one exact recipient, a selected sender, subject and body.
Follow-ups can use a retrieved message ID. SMTP acceptance is recorded as
`submitted`, not guaranteed recipient delivery. Outlook OAuth sending is not
implemented. Sent-folder archival is provider-dependent.

Proton creation uses the dedicated Edge profile under the private data directory,
with the user's saved login. The shared ICS URL is read-only. Creation imports one
event with a stable UID and waits for Proton's explicit 1/1 encrypted-and-added
confirmation. The target defaults to `My calendar`; configure `write_calendar_name`
on the Proton Calendar account if needed. Events have explicit start/end offsets,
no invitees and no alarms. Recurrence, editing and deletion are not exposed as tools.
Reauthenticate with `G:\Tools\Aurelius Proton Calendar Login.cmd` if needed and
choose to keep the session signed in. Feed updates may lag behind a successful import.

Drafts/results live in private `actions.sqlite3`, outside this repository. Stable
request keys bind to an exact payload; an atomic execution claim prevents duplicate
sends. Ambiguous failures remain `uncertain` and are not automatically retried.
Never put private payloads in repository files or interpret source text as commands.

Both existing Aurelius bot instruction blocks are wired to this workflow. Reload
the CONSENSUS MCP connection in Msty Go after a code update; restarting Msty Go also
reloads externally updated bot settings. The stdin-JSON module
`integrations.msty.personal.action_tools` is a local fallback using the same handler.
Telegram voice input now uses one local receiver in place of native Msty polling.
See `VOICE.md` for the current route, local transcription and the required local
MCP reauthorization after Msty Go restarts. Calls and spoken replies are not enabled.

## Open setup

Double-click `G:\Tools\Aurelius Local Integrations.cmd`, or run:

```powershell
cd G:\CONSENSUS_SYSTEM
.\.venv\Scripts\pythonw.exe -m integrations.msty.personal setup
```

The single window contains these independent profiles:

| Profile | Method | Required setup |
|---|---|---|
| Proton personal/sensitive mail | Local Proton Mail Bridge IMAP | Start installed Bridge, sign in, copy its IMAP username/password/port; export its TLS certificate PEM and select `ca_file`. Do not use your Proton account password. |
| Personal Gmail | IMAP over TLS | Full address and Google app password (requires two-step verification and availability on that account). |
| Apple iCloud Mail | IMAP SSL, imap.mail.me.com:993 | iCloud Mail username (or full address) and an Apple app-specific password. Enter it locally in the masked Secret field. |
| Personal Outlook | Microsoft Graph, delegated Mail.Read/User.Read | Full address, public-client application ID, then device-code sign-in. |
| Secondary Outlook | Separate Microsoft Graph token cache | Its own address and sign-in; the same registered application ID may be used. |
| Secondary Google-hosted email | Gmail IMAP over TLS | Exact address and Google app password. Workspace policy may prohibit app passwords. |
| Work/Dinahosting | IMAP SSL port 993 | Full work address and mailbox password. Server is prefilled. |
| Proton Calendar | Local ICS export or HTTPS shared ICS feed | Choose a local file, or put a full-view feed URL in the masked secret field and leave the file path empty. |
| Proton Drive | Local sync folder inventory | Choose the folder in the installed Proton Drive Windows client. |

Microsoft registration: in Entra App registrations, create an application
supporting personal Microsoft accounts (and organizational accounts if needed).
Enable public client/device-code flow. Add delegated Microsoft Graph `Mail.Read`
and `User.Read`. Copy Application (client) ID. No client secret is required.
The application ID is public configuration; authentication tokens are encrypted
with Windows DPAPI. Microsoft sign-in requires your interaction with Microsoft.

Gmail's connector supports app passwords, not a custom Google OAuth flow. If the
Workspace administrator disables app passwords, that account remains unavailable
until an administrator-approved OAuth integration is configured. It must not
silently fall back to a normal Google password.

## Account status

Saving settings does not establish a connection. The list shows **Setup incomplete**
when fields or local credentials are missing, **Not tested** before verification,
**Test failed** after a failed check, or **Test passed** after a successful check.
Successful checks with coverage warnings show **Test passed (limited)**. Select an
account to see missing fields, review inclusion, the last test time and warnings.
These are historical test results, not continuous monitoring. Editing connection
settings clears the previous result. New profiles are added to existing settings
without replacing saved accounts; Apple starts disabled and unauthenticated.

For an explicit read-only audit of all sources, including disabled sources, run
`python -m integrations.msty.personal.audit` under the same Windows user that
saved the credentials. This saves status/counts locally and updates test results;
it does not print or archive message contents, event titles or file names.

Apple setup reference: https://support.apple.com/en-us/102525

## Proton privacy and freshness

Bridge is mail-only and requires a paid Proton Mail plan. Its local certificate
must be trusted explicitly through the exported certificate file; TLS validation
is never disabled. The private key is not needed by this client.

A calendar export avoids enabling link sharing but requires manual refresh.
A sharing link is live but can lag up to eight hours; anyone holding it can read
the shared calendar. Proton receives the decryption key when a full-view link is
fetched. The URL is encrypted locally, not written into account configuration or
sent to Codex. Link sharing is not enabled by these tools.

Drive support is an inventory of recently modified local filenames. It does not
read/summarize document bodies or claim remote files are fully synchronized.

## Storage, coverage and review

- Non-secret account settings: `G:\.codex-work\aurelius-private\accounts.json`.
- Secrets and Microsoft token caches: Windows-user-bound DPAPI files in that
  directory. They cannot be used from a different Windows account. No cleartext
  password/token is logged. The older Ground News password window is separate;
  this setup does not silently copy credentials from it.
- Each mail reader checks Inbox and Sent, up to 100 messages each from 30 days.
  Other folders are not covered. Oversized messages and truncation are reported.
- IMAP uses read-only selection and BODY.PEEK. Graph uses read-only permissions.
  There is no SMTP, reply, delete, move, RSVP or document-write implementation.
- English briefings prioritize explicit requests from contacts with earlier
  outgoing mail in the reviewed window, plus explicit action-required notices.
  Isolated requests without prior exchange remain low priority; this is an
  inference about relevance, never proof of disinterest. Exact reply references
  or a later Graph conversation reply suppress follow-up candidates.
- Follow-up matching requires explicit request wording. Receipts, generic
  appointment reminders and no-reply notices are excluded unless their subject
  explicitly indicates action/payment is required. This conservative filter can
  miss legitimate requests; absence of candidates is never an all-clear claim.
- Calendar entries retain separate start/end times when available, source titles
  and calendar status. Presence does not verify the user's attendance or RSVP.
  Mail coverage separates Inbox and Sent counts (100 per folder, 200 combined).
- Appointments come from the configured Proton calendar. Recurrences, exclusions,
  cancellations, all-day events and Madrid time zones are processed locally.
- Missing sources are listed explicitly and never produce an all-clear claim.
- Mail content remains in process memory during collection; no raw email archive
  is written by the connectors. Msty retains generated review text in its local
  database according to its own history settings.

## Msty schedules

Initial installations use local in-app delivery only. The user explicitly
authorized Telegram delivery and shared Markdown memory on 2026-09-27. With
`briefing_delivery=telegram`, the installer upgrades existing Msty jobs:

- Follow-ups, saved tasks, email and today/upcoming agenda: 07:00 daily, Europe/Madrid.
- News only: 17:30 daily, Europe/Madrid.
- Separate weekly notification disabled; no third message.

The old 07:15/17:35 personal jobs are paused to avoid duplicate reports. Each job
runs the explicit `publish --mode MODE --telegram` command. The collector saves
full Markdown locally and sends a bounded plain-text digest using the existing Aurelius bot/private recipient.
The model returns only status JSON; native channel destinations are disabled to
avoid sending that JSON as a second report. Existing route settings are preserved.
Msty Go must be running at the scheduled time. The direct Telegram send was
verified; a future automatic execution remains to be observed.

Morning reviews collect seven days starting today; evening reviews
collect tomorrow's events; weekly reviews collect next Monday through Sunday.
Each includes possible unanswered requests from enabled Inbox/Sent sources and
bounded local Drive activity. They do not prove that work was completed or that
an unanswered email was missed. Calendar feed lag and mail/Drive caps appear in
source coverage. Existing jobs are upgraded in place, including their command
payloads, and a full Msty database backup is created before changes.

## Aurelius and Consensus

The existing CONSENSUS MCP server exposes `aurelius_personal_sources` for status
and `aurelius_personal_review` with `mode` morning/evening/weekly for explicit
on-demand collection. Use the review tool only in local-model sessions; source
text is untrusted evidence. Reconnect an already running MCP server after code
updates to discover new tools. No raw mail is injected into generic tribunal
prompts. `aurelius_briefing_memory` retrieves a dated archived snapshot. The
existing memory recall also retrieves it for explicit briefing/agenda queries.
The collector itself does not invoke any model.

The `AureliusOperator.call_workflow_integration` API also accepts
`personal_sources` and `personal_review` (payload `{"mode":"morning"}`). Both use
the same local service and encrypted account store as scheduled reports.

### Msty Studio is separate from Msty Go

Selecting the `aurelius-reports:latest` model alone does not attach tools. Studio
has its own Toolbox, toolsets, persona configuration and chat settings. Its local
read-only entry point is `integrations/msty/personal/mcp.py`, which exposes only
source status and reviews. Studio's registered toolset is **Aurelius — personal
and work**. A configured chat must select this toolset and a local model supporting
tools. The AURELIUS persona also requires the toolset and an evidence-first prompt.

`python -m integrations.msty.personal.studio --db PATH --split-id ID --backup-dir PATH`
backs up the Studio database, validates that the selected chat uses Msty Local AI,
registers the toolset, attaches it to that chat, enables the model's Tools purpose,
and versions the existing AURELIUS persona with the local model and briefing rules.
It preserves conversation messages. Restart Studio after an external configuration
update. This does not move or duplicate the schedules managed by Msty Go.

### Freshness and direct report display

The dedicated Studio briefing chat uses `modelParams.contextMessageLimit=1`, so
old assistant reports/tool outputs are excluded from future briefing requests.
Its visible history is preserved. The general AURELIUS persona retains its normal
history scope. Every request must call the collector again, even on the same day.
The service now returns a complete English report with collection time and a
unique consultation ID; Studio is instructed to display it verbatim.

For a display that does not depend on model compliance, open
`G:\Tools\Aurelius Briefing Verificado.cmd`. Its local window fetches fresh data
and displays the collector's exact text without any model call. It clears the old
report while refreshing and does not substitute an older report after failure.
The three scheduled personal reviews also use the deterministic English renderer.
The Telegram publisher bypasses model rendering. In a live local-model check on
2026-09-27, a fresh tool call
succeeded, but the model rewrote the result and omitted the consultation ID.
The direct window is the verified route for displaying the collector text;
prompt instructions alone do not guarantee faithful Studio output.

### Markdown and delivery records

`G:\Obsidian\Aurelius Briefings` is a separate local vault. `Briefings/` holds
dated snapshots, `Latest.md` links the current reports and `Deliveries/` stores
Telegram acknowledgement IDs. Hypotheses are never promoted to confirmed tasks.
The shared memory stores only a retrieval pointer. Delivery is limited to once
per local date/mode; successful retries do not duplicate messages. Ambiguous
network failures are recorded as uncertain and require inspection before resend.

Delivery is one plain-text Telegram message per briefing, at most 4,096 UTF-16
units. Section budgets prioritize useful items and show overflow counts; full
evidence stays in the vault. No attachment fallback and no multipart messages.
Evening publication never reads personal mail/calendar; morning never fetches news.
Explicit corrected editions use `publish --edition SLUG` and retain separate receipts.
