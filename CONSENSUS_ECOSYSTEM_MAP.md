# CONSENSUS ecosystem map

**Status: PROVISIONAL — implementation and live operation must be verified.**  
Recorded: 2026-10-26 (Europe/Madrid). Scope: the CONSENSUS umbrella.  
Inspected revision: `e851f59` (`main`, 2026-10-09) plus the uncommitted
working tree of 2026-10-26, consolidated on branch
`consolidate/2026-10-26-working-tree`. Re-inspect before relying on any
statement below for a later revision.

This is the root orientation map, not a release certification. It preserves the
user's visible naming and boundary decisions and reconciles them with the
inspected working-tree documentation. The referenced chat, **Preparar prompt
para Claude** (`6ad53364-2208-83ed-8183-40735e467f00`), returned placeholders for
its assistant replies, so the complete previously agreed diagram could not be
recovered. This reconstruction must not be described as its verbatim recovery.

## Names and boundaries

- **CONSENSUS**, in general conversation, means the entire ecosystem: the core
  application, supporting infrastructure, agents and related projects.
- **CONSENSUS core / War Room** means the tribunal application specifically.
  Its deliberating agents are RATIONALIS, AETERNUM and BELLATOR; ARBITER applies
  the decision rules. These roles are distinct from coding agents.
- **Msty is the base and an integral part of CONSENSUS.** The intended primary
  human-facing platform and local-model integration must remain visible in
  architecture decisions. The Flet desktop, CLI and API are additional core
  surfaces; their existence does not remove Msty's foundational role.
- **AURELIUS** is a distinct operator-assistant project/layer within the
  umbrella. Its source can live in this repository without making it a tribunal
  voter or a synonym for CONSENSUS core.
- Use **Persistent memory** as the plain-language umbrella label. Existing API
  identifiers such as `mnemosyne_search` are compatibility names, not evidence
  of an independent service. This document does not rename APIs or stored data.

### Msty: what "integral" means today

"Integral" is a statement of direction and priority. As implemented at the
inspected revision, Msty is the **default and preferred provider**, not a hard
runtime dependency:

- provider routing is Msty-first (`msty-local`, `msty-claw`, `msty-llama-cpp`);
- Ollama-compatible endpoints remain supported alternatives;
- without a reachable provider, health checks report `DEGRADED` and a
  controlled, clearly labelled mock fallback can run.

Changes must not remove or demote the Msty routes, and must not silently turn
fallback into the normal path. Making Msty a hard dependency (refusing to run
without it) would be a consequential change and requires an ADR.

## Provisional map

```text
CONSENSUS — ecosystem / umbrella
|
+-- Msty foundation (default provider and primary local-model integration)
|   +-- Msty Studio: primary platform / local-model workflows
|   +-- Msty Claw: bridge and tool orchestration, where configured
|   +-- CONSENSUS provider adapters and per-agent runtime sessions
|
+-- CONSENSUS core / War Room
|   +-- RATIONALIS + AETERNUM + BELLATOR: deliberation and votes
|   +-- ARBITER: deterministic decision rules and audit
|   +-- Flet desktop / CLI / local API / Msty integration surfaces
|   +-- CONSENSUS MCP: tribunal_deliberate and tribunal_verdict (ticketed, one run at a time)
|
+-- AURELIUS — distinct operator-assistant layer
|   +-- Operator interaction, optional voice and personal workflows
|   +-- Explicit delegation to the CONSENSUS tribunal
|   +-- Optional local agent runtime / separate Odysseus service route
|
+-- Shared knowledge and persistent memory (different stores and purposes)
|   +-- Obsidian second brain: curated knowledge and source provenance
|   +-- CONSENSUS decision/session memory: application records and recall
|   +-- AURELIUS Msty Memory Bank: selected shared facts/preferences
|   +-- Briefing archive and knowledge indexes: dated retrieval sources
|   +-- Personal attention state: replies owed, promises, waits, proposed meetings
|
+-- Related projects and external resources
    +-- TARS / earlier Flet prototype: archived under G:\Backup\Projects
    +-- Local models / Kiwix corpus / installed applications: outside Git
```

The tree groups runtime responsibilities; it does not assert that every route
is connected, running, deployed, or a separate process/repository. Code hosting
and conceptual project boundaries are different questions.

How the project is built is not part of the product. OpenAI Codex and Claude
act as task owners, implementers and reviewers under the
[collaboration protocol](AGENT_COLLABORATION.md), using shared Markdown, Git
history, handoffs and decision records.

## Memory authority (proposed)

The four stores serve different purposes, so none silently overrides another.
Until an ADR adopts or replaces this rule:

| Question | Authoritative store |
| --- | --- |
| What did the tribunal decide, when, and on what record? | CONSENSUS decision/session memory |
| What is known, from which source, with what provenance? | Obsidian second brain |
| What does the operator prefer, and which shared facts are confirmed? | AURELIUS Msty Memory Bank |
| What was reported on a given date? | Briefing archive (dated claims only, never current fact) |
| Who is waiting for the operator, and what did the operator promise? | Personal attention state (`system/state.sqlite3`; Markdown is generated from it) |

When two stores disagree, surface both with their sources and dates; do not
overwrite one from the other automatically. The operator resolves the conflict,
and the resolution is recorded in the store that owns that question.

## Evidence and verification state

Status levels, in order:

1. **Proposed** — named in a document only.
2. **Present** — source or configuration exists at the inspected revision.
3. **Tested** — automated tests covering it pass, with the command, environment
   and result recorded.
4. **Operational** — a dated live check on the operator's machine succeeded
   (real provider call, running service, delivered message), with the result
   recorded.

A component moves up only when the evidence for the next level is written into
this table or its owning document. Nothing here is Operational yet.

| Area | Status | Evidence inspected | Needed for next level |
| --- | --- | --- | --- |
| Msty foundation | Tested (adapters only) | User's explicit correction; [Msty integration](docs/MSTY_STUDIO_INTEGRATION.md); `integrations/msty/runtime.py`; provider routing tests pass | Live call through installed Msty with the active model recorded |
| Core / tribunal | Tested | [README](README.md), [module architecture](docs/ARCHITECTURE.md); `core/`, `monoliths/`, `ui/`; test suite (see below) | Real-provider deliberation and packaged executable self-test on Windows, recorded |
| AURELIUS | Tested (offline) | [Agent runtime](docs/AURELIUS_AGENT.md), [Odysseus route](docs/AURELIUS_ODYSSEUS.md); `assistant/agent/`, `integrations/odysseus/`; AURELIUS agent, runtime, memory, Odysseus and interaction tests pass | Running service with the enabled route, permissions, voice and delivery checks recorded |
| Persistent memory | Tested (application stores) | `core/memory/store.py`, `core/memory/session.py`, [AURELIUS shared memory](integrations/msty/AURELIUS_SHARED_MEMORY.md) | Live write and cross-client recall, with stored contents checked |
| Shared second brain | Tested (loader) | Repository `AGENTS.md`; vault startup notes; `core/knowledge/second_brain.py` (loads only `50 Agents/Shared Context.md`); second-brain tests pass | Each client's access to the real vault confirmed by an executed check |
| Surrounding workspace | Present | [Workspace ecosystem](docs/WORKSPACE_ECOSYSTEM.md), [folder guide](docs/FOLDER_GUIDE.md) | Per-path availability check; no active project is inferred from an archive |
| Personal attention | Tested (offline) | [Personal Attention Manager](integrations/attention/README.md); `integrations/attention/`; `tests/test_attention.py` passes; live read-only scan 2026-10-29 read 65 email conversations and classified them locally; 2026-10-31 Windows backup tasks ran every scan, the 08:05 brief and the morning briefing; Msty Go source jobs fail because of a Msty Go 1.1.0-beta.3 worker bug (see README); 2026-11-01 Telegram signed in and WhatsApp linked; both read live, chat classification not yet checked | Scheduled scans and briefs running in Msty Go, with a dated check of the brief; chat sources read live |
| Coding-agent coordination | Proposed | [Collaboration protocol](AGENT_COLLABORATION.md) | Adoption by both hosts and the first coordination record |

Test evidence, 2026-10-26: `python -m pytest` on the consolidation branch, run in
a Linux environment with Python 3.10 (not the operator's Windows install):
1,133 passed, 9 skipped, 1 failed. The failure is
`test_flet_desktop_runtime_present_in_current_environment`, which requires the
Windows `flet-desktop` runtime. The GUI desktop window, real providers and
the packaged executable were not exercised. Known isolation flaw: tests write
`_ARBITER/provider_model_cache.json`, so a second run in the same checkout can
fail `test_fallback_resolution_chain` until that file is removed.

## Open questions

- Where do `G:\Hermes` (an agent runtime) and the `G:\CONSENSUS SYSTEM` folder
  (distinct from the source root) belong: inside the umbrella, related, or
  outside it?
- Should Msty become a hard dependency (see above)? Requires an ADR either way.
- Adopt, amend or replace the proposed memory authority rule.

## Sources of truth and maintenance

The source-controlled project root is `G:\CONSENSUS_SYSTEM`, published at
<https://github.com/JanusSecuritekConsortium/CONSENSUS-WAR-ROOM>. The canonical
private second brain is `G:\Obsidian\CONSENSUS_SYSTEM`; read
`50 Agents/START HERE.md` and the small `50 Agents/Shared Context.md` before
loading task-relevant notes. Keep personal source contents out of this repository.
The inspected application loader reads only the small shared brief; a path in a
document does not provide every agent with full-vault retrieval.

This file owns umbrella terminology and conceptual boundaries.
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) owns detailed module descriptions;
[docs/WORKSPACE_ECOSYSTEM.md](docs/WORKSPACE_ECOSYSTEM.md) owns surrounding path
references. Link to these maintained sources instead of copying their inventories.

Before promoting a component's status, record the inspected revision or dirty
working-tree scope, dated evidence, exact verification command/result and
remaining limitations. Update the owning document and this map when boundaries
change. Keep new tendrils explicitly proposed until their scope is established;
record consequential changes in an ADR under the collaboration protocol.
