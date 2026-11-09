# Online models for tribunal voters

Each tribunal voter (RATIONALIS, AETERNUM, BELLATOR) can use an online model instead of its
local Msty model. ARBITER stays deterministic, and AURELIUS is not affected.

Supported providers:

| Provider | Setting prefix | Key variable | Examples |
|---|---|---|---|
| Anthropic (Claude) | `anthropic:` | `ANTHROPIC_API_KEY` | `anthropic:claude-sonnet-5-5`, `anthropic:claude-opus-5-5` |
| OpenAI (GPT / Codex) | `openai:` | `OPENAI_API_KEY` | an OpenAI model ID from your API dashboard |
| DeepSeek | `deepseek:` | `DEEPSEEK_API_KEY` | `deepseek:deepseek-chat`, `deepseek:deepseek-reasoner` |

API access is billed separately from a Claude or ChatGPT subscription. You need an API key
from each provider's console.

## Setup

Add the settings to the gitignored `.env` file in the CONSENSUS folder (see `.env.example`):

```
CONSENSUS_ONLINE_MODEL_RATIONALIS=anthropic:claude-sonnet-5-5
CONSENSUS_ONLINE_MODEL_BELLATOR=deepseek:deepseek-chat
ANTHROPIC_API_KEY=<your key>
DEEPSEEK_API_KEY=<your key>
```

A voter without a setting, or whose provider has no key, stays local. The settings are read
on every call, so the next deliberation uses a change without restarting CONSENSUS. A value
set in the shell overrides the one in `.env`.

To check the setup:

```
.venv\Scripts\python.exe -m core.llm.online
.venv\Scripts\python.exe -m core.llm.online --ping
```

The first command lists each voter's state and never prints keys. `--ping` sends one tiny
request to each online voter's model.

## Behaviour

- **Fallback:** a failed online call (no network, rejected key, rate limit, an unfinished or
  unparseable answer) is logged as `online_model_fallback`, and the voter answers with its
  local model. The transcript records the online attempt and marks the turn as a model fallback.
- **Privacy:** an online voter's prompt leaves out the vault brief (`50 Agents/Shared
  Context.md`). The proposal, prior CONSENSUS decisions, public references and the BELLATOR and
  AETERNUM data packets are still sent. Set `CONSENSUS_ONLINE_SHARE_PERSONAL=1` to include the brief.
- **Cost limit:** `CONSENSUS_ONLINE_TOKEN_BUDGET` (default 250000) caps the input plus output
  tokens one deliberation may use online. Once it is reached, later calls use the local model.
  A full deliberation is 9 calls of roughly 4,000 to 8,000 input tokens each.
- **Switch off:** `CONSENSUS_ONLINE_MODELS=0` sends every voter back to its local model.
- **Keys** are sent only in the provider's request header and never appear in logs, errors,
  transcripts or the status command.
