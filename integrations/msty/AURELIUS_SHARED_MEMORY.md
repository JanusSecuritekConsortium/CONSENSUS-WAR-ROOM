# Aurelius shared memory

Telegram and mobile Aurelius share the native Msty Go Memory Bank pack
`aurelius-shared-persistent-memory`. The same pack is attached to both agents
and their existing conversations. Existing working briefs remain untouched.

The CONSENSUS MCP tools provide fresh recall, verified single-fact saves and
explicit single-fact forgetting. The helper `aurelius_memory.py` implements
these operations; it is not a background service and does not poll Telegram.

Ask Aurelius to remember a concise, non-secret fact or preference. It should
call `aurelius_memory_remember` and confirm only after `saved: true`. Before
answering memory questions it should call `aurelius_memory_recall` rather than
depend on its current transcript. Saved data survives chat and app restarts.

Writes are transactional and append native revisions, preserving unrelated
facts and packs. Native search indexes are updated with each save. Concurrent
writes on different keys do not overwrite one another. A correction replaces
the active value for its key but keeps revision history.

Forgetting removes a fact from active recall, not from historical revisions
or backups. Do not use this store for credentials or promise permanent erasure.
Shared facts are not shared complete transcripts, and do not automatically
combine active task state. Permission controls and existing report schedules
remain independent and unchanged.

Validation: remember a harmless unique detail on Telegram, then ask for it in
a fresh mobile chat without including the answer. Repeat in the other direction.
The model must actually use the memory tools; a prose acknowledgment alone is
not proof of a save. If an operation needs approval or fails, the fact has not
been successfully saved and Aurelius must report that honestly.
