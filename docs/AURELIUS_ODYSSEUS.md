# Real Odysseus as an AURELIUS complement

`integrations.odysseus` connects AURELIUS to the **actual, separately installed
Odysseus service**, using its public `/api/chat_stream` agent endpoint. It does
not import, vendor or reimplement the Odysseus agent loop. The earlier
`assistant.agent` runtime remains a separate optional local implementation.

The inspected local installation is `G:\Odysseus`, serving
`http://127.0.0.1:7000`; installed checkout
`934d23c0be29c9721385f34565c0ae2cbd60da04`. This is an operational observation,
not a dependency on a particular drive. Base URL and credential path are
configurable. No automatic upstream update or model download occurs.

The local service now has a separately tracked inspection extension. Its source
and AGPL obligations remain with Odysseus; no service implementation is copied
into CONSENSUS. See `G:\Odysseus\AURELIUS_EXTENSION.md` and the prepared
`Odysseus-AURELIUS-tool-fix.patch`. Review that local patch when updating Odysseus.

## Responsibilities and permissions

Odysseus investigates and proposes next steps as AURELIUS. CONSENSUS keeps
tribunal deliberation, voting and reasoning models. AURELIUS keeps its voice,
Telegram delivery and existing briefing owners. The integration does not register
any cron job, scheduler or autonomous delivery task. Both the legacy 08:00/18:00
workflow and the independently configured Msty briefing workflow remain unchanged.

Every request sets `mode=agent`, `plan_mode=true`, `allow_bash=false`,
`use_research=false`, `use_rag=false`; web tools require a host configuration
opt-in. These are actual server-side controls, not merely prompt instructions.
`execution_mode=plan` retains the legacy checklist behavior. The tested local
configuration uses `execution_mode=readonly`, adding `investigation_mode=true`
while keeping the plan-mode write/approval guards. The service's separate
inspection directive permits actual lookups rather than asking for a checklist.
Only model/server/catalog inspection tools and explicitly enabled web tools are
allowed. It cannot send messages, write, schedule, change settings, serve models
or delegate to another model. Existing denials and guide-only requests win.
Model fallbacks are disabled in this mode, retaining the selected local executor.
Automatic Odysseus memory/skills/integration-description injection, teacher calls,
and post-response extractors/webhooks are skipped for inspection requests.
Each inspection uses the current operator request and explicit evidence, excluding
stale prior dialogue from model context while retaining the saved transcript.
Original message metadata is assessed by the authority guard before filtering.
CONSENSUS still supplies selected evidence explicitly, and the existing
untrusted-context approval guard remains active. Explicit inventory requests
require an offered native read tool on the first round, preventing an unsupported
verbal claim from substituting for inspection.
The delegated bearer token additionally
blocks privileged filesystem, shell, MCP, settings, memory-management and email
tools. Chat/session messages are still persisted by Odysseus. This integration
cannot approve tool actions or elevate the token. If Odysseus asks a question or
requires approval, inspect the dedicated AURELIUS session in its own UI.

Readonly mode first checks authenticated `/api/aurelius/capabilities` for protocol
version 1, inspection support and disabled model fallbacks. A missing/incompatible
extension prevents an agent request and returns `readonly_service_upgrade_required`.
This avoids silently treating an ignored request flag as successful tool execution.
Cogito's native function-call support was verified against the local backend;
the service now recognizes its name. An explicit endpoint tool opt-out is preserved.
The verified local executor is currently `qwen3:latest`, which completed a fresh
native inventory lookup through the actual CONSENSUS MCP entry point on
4 October 2026. Cogito's full agent inspection remained unreliable despite its
successful standalone transport probe.

The optional stdio MCP server exposes **only** `mnemosyne_search`,
`aurelius_memory_recall` and `aurelius_briefing_memory`. It contains no general
file reader, arbitrary SQL, write, send, shell, or recursive agent entry point.
Its decision search reads the actual CONSENSUS decision store; it does not
pretend a separate MNEMOSYNE service exists. Native memory reads use the existing
AURELIUS shared pack, and briefing recall uses the existing historical archive.
Missing sources degrade individually. Credentials and runtime data are ignored.

Delegated tokens cannot execute privileged MCP tools in the inspected Odysseus
version. For this route, CONSENSUS retrieves relevant read-only facts itself
and supplies bounded, labelled, untrusted evidence to Odysseus. It only selects
memory, decisions or briefing sources when the request mentions them. A signed-in
Odysseus admin may separately register the narrow MCP service for native UI agent
sessions; registration is not performed automatically and does not make MCP
available to a restricted token.

## Configure and verify

The existing CONSENSUS MCP server exposes `aurelius_odysseus_status` and
`aurelius_odysseus_task` for its host clients, including Msty. Task delegation
accepts only an operator prompt, requires the configured real-service route, and
cannot change permissions, models or endpoints. These tools are excluded from
the read-only evidence bridge and the local agent registry to prevent recursion.
Already running stdio clients need to reconnect to discover the new tools.
The existing scheduler process need not be restarted for that reconnect.

1. Sign in to Odysseus. Open **Settings → Integrations → Add → Codex Agent →
   Create token**. Name it `Codex Agent AURELIUS`. Token creation grants `chat`;
   additional scopes are optional and do not override the execution policy. Save the token locally, without quotes, at
   `_ARBITER/aurelius_odysseus_token.txt`. Do not commit it or paste it into chat.
2. Run `python -m integrations.odysseus models` from CONSENSUS with its Python
   environment. This lists existing registered model and endpoint identifiers.
3. Run `python -m integrations.odysseus setup --endpoint-id EXISTING_ID --model
   EXISTING_MODEL`. This validates the model through the service, creates a
   dedicated AURELIUS session and exclusively creates the ignored configuration
   `_ARBITER/aurelius_odysseus/settings.json`. Existing configuration is not
   overwritten. Setup is a one-time host operation, not an agent tool.
   For compatibility with running builds that still require `endpoint_url`,
   session creation sends both the endpoint identifier and its catalog URL.
   The URL must be a registered loopback chat-completion route, with no embedded
   credentials or query parameters; arbitrary user-supplied endpoints are refused.
   After applying and testing the isolated service extension, set saved
   `execution_mode` to `readonly` or use `AURELIUS_ODYSSEUS_EXECUTION_MODE=readonly`.
   This accepts only `plan` or `readonly`; there is no unrestricted execution mode.
4. Run `python -m integrations.odysseus status`, then
   `python -m integrations.odysseus ask "Identify your role and execution engine"`.
   A completed result identifies `engine=odysseus-service` and its session/model.
   This live check requires credentials and a reachable registered model. For a
   real tool check, ask "Which local models are available?" and require a successful
   `list_models` entry in `executed_tools`/`tool_results`. A `tool_start` event alone
   records an attempt. A `tool_output` with exit code 0 records completion; native
   inventory tools without an exit code require the inspection extension's explicit
   `success=true` and a preceding dispatch event. Failed results cannot complete. Missing tool completion produces `tool_execution_unconfirmed`.

Local setup enables Odysseus for AURELIUS interactive operator, voice/UI and
Telegram entry points on their next construction/restart. An explicit
`AURELIUS_ODYSSEUS_ENABLED=false` environment value overrides local settings.
The example environment defaults to disabled. A configured Odysseus route takes
precedence over the optional local agent; failures produce an explicit degraded
result, rather than silently switching engines. Explicit tribunal routing bypasses
Odysseus. No existing running process is restarted automatically.

All HTTP requests stay on loopback, do not use proxy environment settings, do
not follow redirects, and do not retry uncertain executions. Streams, prompts,
evidence and responses have fixed limits. Missing credentials/configuration,
unavailable models, rejected authentication, malformed/truncated streams,
timeouts and remote budget failures do not report success. Logs retain run
identifier, status and counts, never prompts, source contents or credentials.
Overlapping runs for the same integration session are rejected across processes
using an OS file lock. A disconnected or timed-out request may still be visible
as an interrupted/background stream in Odysseus; inspect that session before
retrying. No execution is replayed automatically.
Local-model warm-up can take longer than 15 seconds; the HTTP read timeout uses
the configured 180-second default (maximum 300). Elapsed-time checks run between
stream chunks, and an idle read remains bounded by that same configured timeout.
The local executor configuration can use 300 seconds to allow a lookup followed
by its answer on this PC. Closing the browser tab does not stop the service;
it must remain running independently. No auto-start or startup task is registered.

To register the optional MCP boundary, use the existing CONSENSUS Python as
`command` and the absolute `integrations/odysseus/mcp_server.py` path as the sole
argument. It implements newline-delimited JSON-RPC initialize, ping, tools/list
and tools/call. Read-only enforcement comes from the closed dispatch table.

Ajax is deliberately rejected until its actual weights, license and backend
compatibility have been verified. Existing CONSENSUS reasoning models are never
changed. The AGPL Odysseus installation stays separately distributed; this
CONSENSUS-owned client contains no upstream implementation code.

Offline checks: `python -m pytest tests/test_aurelius_odysseus.py
tests/test_aurelius_agent.py tests/test_aurelius_runtime.py
tests/test_consensus_mcp_server.py`. They do not contact models or send messages.
