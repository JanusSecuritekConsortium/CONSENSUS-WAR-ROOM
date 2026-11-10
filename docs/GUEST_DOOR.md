# Guest door: another AI system asks the tribunal

The guest door lets another AI system (for example a friend's agent council) send a question to
the CONSENSUS tribunal and collect the verdict later. The verdict is advice only.

## What a guest gets, and what stays private

A guest question runs as a **guest deliberation**:

- No personal vault brief, no prior CONSENSUS decisions and no data packets (news feeds or any
  configured data source) reach the voters. The voters see only the guest's question.
- Local models only. Online voters (Claude, ChatGPT, Grok, DeepSeek) are not used for guests, so
  their questions never go out on the owner's subscriptions. `CONSENSUS_GUEST_ONLINE=1` allows them.
- Nothing is saved to the owner's decision history, session memory or decision traces, and ARBITER
  does not announce the verdict.
- The guest receives a summary: the verdict, its confidence and reason, and each voter's vote,
  confidence and reasoning (up to 600 characters). No raw model output, prompts or transcripts.
- A guest can read only its own tickets. While the owner's tribunal is busy, the guest is told to
  try later and learns nothing about the owner's question.
- One deliberation runs at a time. `CONSENSUS_GUEST_DAILY_LIMIT` (default 5) caps guest questions
  per 24 hours. A guest question never unloads the owner's Local AI models.

## For the owner: open the door

1. Make the password, once. It is saved in `.env` and shown once; give it to the other system's
   owner through a private channel:

   ```
   .venv\Scripts\python.exe -m integrations.guest.server --new-password
   ```

2. Open the door (or run `tools\launchers\start_guest_door.cmd`). It stays open while the window
   is open:

   ```
   .venv\Scripts\python.exe -m integrations.guest.server
   ```

By default the door listens on `127.0.0.1:8890`, which only this PC can reach.

### Letting another PC in, privately

Never forward the port on the router or expose the door to the internet. Use a private network
such as [Tailscale](https://tailscale.com):

1. Both owners install Tailscale and the owner shares this PC with the friend's Tailscale account
   (Tailscale admin console, "Share").
2. Put this PC's Tailscale address in `.env` (`tailscale ip -4` shows it):

   ```
   CONSENSUS_GUEST_HOST=100.x.y.z
   ```

3. Restart the door. Only devices on the shared Tailscale network can reach it, and they still
   need the password.

To shut the door, close its window. To lock the friend out for good, run `--new-password` again.

## For the guest system: the API

Every request carries the password: `Authorization: Bearer <password>`. A wrong password returns
401 after a one-second delay.

| Request | Answer |
|---|---|
| `GET /guest/v1/health` | `{"service", "version", "busy", "questions_left_today"}` |
| `POST /guest/v1/deliberations` with `{"question": "..."}` (up to 4000 characters) | 202 `{"ticket", "status": "queued"}`; 409 busy; 429 daily limit reached; 400 or 422 bad question; 503 the PC lacks memory for the models |
| `GET /guest/v1/deliberations/{ticket}` | `{"ticket", "status", "question", "result", "error", "advisory_only": true, ...}` |

`status` is `queued`, `running` (with `elapsed_minutes`), `finished` (with `result`) or `failed`
(with `error`). On local models a deliberation can take up to an hour: ask for the verdict every
few minutes, not every second.

Example with `curl`:

```
curl -H "Authorization: Bearer $PASSWORD" -H "Content-Type: application/json" \
     -d '{"question": "Should we move our backups to a second provider?"}' \
     http://100.x.y.z:8890/guest/v1/deliberations
curl -H "Authorization: Bearer $PASSWORD" http://100.x.y.z:8890/guest/v1/deliberations/<ticket>
```

A finished `result` looks like:

```json
{
  "session_id": "3f2a9c1d0b7e",
  "verdict": "CAUTION",
  "confidence": 0.71,
  "reason": "...",
  "votes": {
    "RATIONALIS": {"vote": "APPROVE", "confidence": 0.8, "reasoning": "..."},
    "AETERNUM": {"vote": "CAUTION", "confidence": 0.7, "reasoning": "..."},
    "BELLATOR": {"vote": "DENY", "confidence": 0.65, "reasoning": "..."}
  },
  "next_steps": ["..."],
  "review_triggers": ["..."]
}
```

The verdict is advisory: the guest system decides what to do with it.
