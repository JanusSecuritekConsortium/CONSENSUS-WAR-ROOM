# AURELIUS agent execution

This clean-room implementation adds an optional execution layer to the existing
`assistant.aurelius_runtime.AureliusRuntime` and
`integrations.msty.aurelius.AureliusOperator`, with an opt-in route for the
legacy bot's interactive requests. AURELIUS orchestrates tools; the
existing tribunal still reasons and votes. No UI change, model replacement,
provider remapping, new daemon or live schedule installation is required.

## Architecture and implementation order

1. `assistant/agent/loop.py` provides bounded rounds, one tool call per round,
   cancellation, resumable approval waits, deadlines and structured outcomes.
   `context.py` pins system/operator input, bounds serialized characters and
   keeps complete recent assistant/tool exchanges. Source provenance and
   truncation travel with evidence. Every run starts fresh; durable knowledge
   belongs in the existing memory stores, not unlimited chat history.
2. `registry.py` ranks tool descriptions/domains against the request and recent
   evidence. Only the retrieved subset is sent to the executor; calls outside
   that subset fail closed. JSON Schema 2020-12 validates arguments before any
   callback. Unknown tools, invalid arguments and remote schema references
   cannot execute. `permissions.py` enforces host-owned impact classifications.
3. `adapters.py` connects actual memory, reports, tribunal, confined files and
   an optional host Telegram sender. `mcp.py` implements initialize/initialized,
   paginated discovery and tools/call through stdio or an injected JSON-RPC
   transport. Browser or external MNEMOSYNE servers can attach through this
   boundary. No general browser daemon exists in this source checkout; the
   existing Proton browser remains part of explicit personal actions.
4. `jobs.py` supplies a bounded SQLite-backed background queue with one owner,
   request-key deduplication, cancellation, approval waits and restart handling.
   The existing bot owns the 08:00/18:00 registration. Its factual report path
   can use the agent loop with a deterministic source executor; no generated
   news or additional Telegram delivery is introduced.
5. `executor.py` supplies the pluggable `Executor.step(messages, tools, timeout)`
   boundary and a Msty/OpenAI-compatible implementation. It uses the existing
   AURELIUS provider resolver. It never changes `RuntimeConfig` or monolith model
   assignments. A test/script executor can be injected without network calls.

## Install and configuration

Use the project virtual environment:

```powershell
python -m pip install -e ".[agent]"
# Or, when the project is already installed:
python -m pip install -r assistant/agent/requirements.txt
python -m assistant.agent --status
python -m assistant.agent --self-test
```

The optional dependency is `jsonschema>=4.18,<5`. Disabled legacy conversation,
voice and source reports do not require it. Missing dependencies degrade the
optional feature without breaking UI startup. Importing the package starts
no services, reads no private sources and does not discover models.
The existing development dependency group also includes the validator so CI
can run the new tests with its existing `.[dev]` installation command.

| Setting | Default | Meaning |
| --- | --- | --- |
| `AURELIUS_AGENT_ENABLED` | false | Opt into agent execution for AURELIUS requests |
| `AURELIUS_AGENT_MAX_ROUNDS` | 8 | Maximum executor rounds, including final response |
| `AURELIUS_AGENT_MAX_TOOLS` | 6 | Retrieved descriptors per round |
| `AURELIUS_AGENT_CONTEXT_CHARS` | 24000 | Serialized character budget; not a token guarantee |
| `AURELIUS_AGENT_RESULT_CHARS` | 6000 | Evidence and final-response bound |
| `AURELIUS_AGENT_DEADLINE_SECONDS` | 120 | Cooperative end-to-end deadline |
| `AURELIUS_AGENT_BACKGROUND_ENABLED` | false | Allow explicit host background manager creation |
| `AURELIUS_AGENT_SCHEDULED_ENABLED` | false | Route legacy factual report collection through bounded agent rounds |
| `AURELIUS_EXECUTOR_BACKEND` | msty | Existing verified backend; unsupported values rejected |
| `AURELIUS_EXECUTOR_MODEL` | empty | Dedicated executor model, otherwise existing `AURELIUS_MODEL` |

`AURELIUS_MSTY_BASE_URL`/`MSTY_BASE_URL`, `AURELIUS_PROVIDER` and `MSTY_API_KEY`
retain their existing meaning. Enabling the feature does not configure a new
endpoint or select a replacement model. Model tool-call support must be verified
on the configured backend. Malformed, multiple or missing tool calls degrade
the run; there is no silent mock, endpoint fallback or model remap.
The supplied tool executor requires a loopback endpoint, disables redirects and
ignores proxy environment variables so recalled local facts remain local.
Other deployments require an explicitly reviewed, injected executor adapter.

Executor responses are capped at 2048 generated tokens. The character context
budget includes local evidence and descriptors; choose a smaller budget for a
backend with a small token window. Oversized inputs/schemas fail closed.

Ajax is **disabled**. Configuration naming Ajax is rejected until weights,
license and backend compatibility have been verified and a reviewed executor
adapter is added. The public [Ajax page](https://data.pewdiepie.com/) was still
labelled “Coming soon” during implementation on 2026-10-03. No weights were
downloaded or tested.

## Permissions and approval

| Capability | Impact | Default behavior |
| --- | --- | --- |
| Decision memory search, native recall, archived briefing, factual reports | read | Automatic |
| Confined project text read | read | Explicit host attachment, bounded and redacted |
| New report/data file | write | Exact host approval; no overwrite |
| Native remembered fact / forget | high impact | Exact host approval; native user-confirmed semantics preserved |
| Submit to tribunal | high impact | Exact host approval; deliberation may persist a decision |
| Telegram send | high impact | Exact host approval; existing host recipient only |
| Unknown external MCP tool | high impact | Exact host approval regardless of server hints |
| Shell, destructive filesystem, arbitrary recipients | absent | No capability |

Only trusted host code can issue approval. There is no grant tool, approval
argument, MCP approval endpoint or automatic authorization from source text.
Grants bind run ID, tool name and canonical exact arguments, expire within five
minutes and are consumed once. High-impact tools always require them. A host
may explicitly allow named `write` tools through `AgentConfig.auto_write_tools`;
after any source/host evidence is consumed, those writes require approval too.
This setting cannot downgrade high-impact tools or user-confirmed memory writes.

```python
from integrations.msty.aurelius import AureliusOperator

operator = AureliusOperator()
result = operator.run_agent("Search remembered assessments of the topic")
# Display result.status, result.text and result.pending in the host.
# After a trusted operator authorizes the exact displayed pending action:
pending = result.pending
operator.agent_runtime.policy.approvals.grant(
    result.run_id, pending["name"], pending["arguments"]
)
result = operator.resume_agent(result.run_id)
```

The host must only grant after authorization; never infer it from model output.
Resume continues the paused run without replaying earlier tools. Pending runs
are process-local, bounded to 32 and expire at the execution deadline. They
cannot survive a restart. The MCP `aurelius_agent_run` endpoint returns the
pending proposal; it cannot approve it. `prepare_user_response` remains a string
API, while `run_agent` exposes full status for hosts needing approval UI.

Tool output is never promoted to system instructions. Prompt-injection policy
does not guarantee a model will ignore malicious text; the enforceable boundary
is argument validation, confined capabilities and exact host permission checks.

## Memory and MCP attachment

No separate MNEMOSYNE service was found in this checkout. `mnemosyne_search`
reads the real `core.memory.MemoryStore` decision file without relocating a
corrupt file. Native AURELIUS facts use existing Msty Memory Bank handlers.
Archived briefings stay in their existing local vault. Missing stores remain
unavailable; they do not become invented facts or an all-clear.

Explicit host example for an existing local MCP server:

```python
import sys
from assistant.agent.mcp import MCPConnection, StdioTransport
from assistant.agent.contracts import Impact

with StdioTransport([sys.executable, "integrations/mcp/consensus_mcp_server.py"],
                    cwd=project_root, timeout=15) as transport:
    connection = MCPConnection(transport)
    connection.register(agent.registry, "consensus", impacts={
        "aurelius_memory_recall": Impact.READ,
        "aurelius_briefing_memory": Impact.READ,
    })
    result = agent.run("Recall briefing memory")
```

The host supplies commands and risk mappings, never the model. Connections must
remain open through execution. A timeout closes the child and is never retried.
Server-requested sampling/elicitation is rejected; logs do not inherit stderr.
Annotations cannot turn an unknown write into a read. The implemented transport
follows [MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
and [tool results](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).
Streamable HTTP/SSE must be provided by a host adapter; it is not claimed as an
implemented transport. Network authentication stays with that adapter.

Filesystem roots and `telegram_sender` are optional host capabilities passed to
`build_agent`. They are not enabled by environment flags. Filesystem writes
create new `.md`, `.txt`, `.json` or `.csv` files in a dedicated output root;
relative traversal, hidden/runtime/credential paths and executable writes are
rejected. Source read content is bounded and common secret assignments redacted.
Redaction is not a license to attach a credential-containing directory.

## Background execution and existing schedules

```python
from pathlib import Path
from assistant.agent.jobs import BackgroundTasks

# AURELIUS_AGENT_BACKGROUND_ENABLED must also be enabled.
tasks = BackgroundTasks(agent, Path(project_root)/"_ARBITER/aurelius_agent/jobs.sqlite")
job_id = tasks.submit("operator-request-unique-key", "Recall previous assessments")
state = tasks.status(job_id)
# If waiting_approval, grant the exact run/action through the trusted host,
# then tasks.resume(job_id). Cancellation is cooperative: tasks.cancel(job_id).
tasks.close()  # Stops accepting work and waits for active callbacks to return.
```

An existing `AureliusOperator` can own this same manager with
`tasks = operator.agent_tasks()`; it uses the ignored runtime path above and
the operator's attached agent. Host schedule callbacks can submit work through
that API without creating another model session or scheduler.

No model tool can start jobs or install schedules. One manager owns a queue,
with two workers by default and at most 32 active tasks. Reusing a request key
with the same prompt returns the same job; reusing it with a different prompt
is rejected. Restart marks queued/running/waiting work `interrupted`, never
automatically resubmits a write or replays Telegram delivery. Records contain
private prompts/results and belong under the ignored runtime directory. They
are retained until the host deliberately manages retention.

Legacy bot registration still uses 08:00/18:00 and its existing local timezone
semantics. Existing Msty-owned personal briefings have independent configured
hours and delivery receipts; this change does not edit Msty's database, alter
those hours, start inbound Telegram polling or create a second delivery owner.
Attach additional background research explicitly from the current schedule
owner using stable request keys (for example label plus local date). Do not
start both owners for the same delivery.

Scheduled legacy reports use a deterministic executor that calls only the
existing factual source collector and returns its exact text. Failure or an
oversized report falls back to the existing collector. General background
tasks can use the pluggable model executor; scheduled communications still
belong to the current host, not model-generated actions.

## Failure behavior, audit and validation

Outcomes are `disabled`, `completed`, `waiting_approval`, `degraded`, `uncertain`
or `cancelled`. Background recovery also reports `interrupted`. Read failures
enter context as unavailable and make the final outcome degraded. Failed or
unverifiable writes stop the run as uncertain; duplicate writes are rejected
within a run. Cross-run retries require host review and downstream idempotency.

Cancellation/deadline checks run between executor and tool callbacks. They
cannot forcibly undo or stop an in-progress synchronous callback. Msty and MCP
have transport timeouts; attached tools must implement their own bounded I/O.
Never equate a timeout or cancellation with a rolled-back external action.

Audit events use `core.logging.log_event` with run/job ID, tool name, impact,
status, duration boundary and error type; no prompt, argument values, evidence,
model output, credentials or raw exception messages. Logging failure does not
break execution. Existing integrations retain their own audit behavior.

```powershell
python -m pytest tests/test_aurelius_agent.py tests/test_aurelius_runtime.py tests/test_aurelius_reports.py
python tests/test_aurelius_agent.py
python -m assistant.agent --self-test
python tools/run_tests.py --fast --provider --integration
```

The new offline contracts cover multiround context, exact approvals/resume,
injected source instructions, strict schemas, read/write failures, uncertain
outcomes, cancellation, retrieval limits, model isolation, confined files,
Telegram recipient scope, MCP handshake/errors/timeouts, queue ownership,
deduplication/restart and factual scheduled execution. They make no live model
calls or Telegram sends.

## Provenance and licensing boundary

The architectural ideas were inspired by the public
[Odysseus description](https://github.com/odysseus-dev/odysseus), which identifies
its license as AGPL-3.0-or-later. No Odysseus source was copied, vendored or linked
into CONSENSUS, and no new license claim is made for CONSENSUS. Any future
external Odysseus dependency requires separate review and an explicit service
or API boundary; this implementation does not depend on it.
## Actual Odysseus service

The optional local runtime described below is distinct from the real Odysseus
integration. See [AURELIUS_ODYSSEUS.md](AURELIUS_ODYSSEUS.md) for the separate
service/API boundary and its investigation-only AURELIUS route.
