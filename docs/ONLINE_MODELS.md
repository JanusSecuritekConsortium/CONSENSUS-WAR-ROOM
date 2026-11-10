# Online models for tribunal voters

Each tribunal voter (RATIONALIS, AETERNUM, BELLATOR) can use an online model instead of its
local Msty model. ARBITER stays deterministic, and AURELIUS is not affected. Giving each voter
a model from a different company gives the tribunal different reasoning styles.

## Providers

**Subscriptions (no API bill).** CONSENSUS runs the company's own command-line tool in its
single-answer mode. The tool must be installed and signed in with your subscription. Each
deliberation makes 3 calls per voter, which count toward your plan's usage limits.

| Setting | Tool | Signed in with | Sign in once with |
|---|---|---|---|
| `claude-cli:sonnet` (or `opus`, `haiku`) | Claude Code (`claude`) | Claude Pro/Max | `claude` then `/login` |
| `codex-cli:default` (or a model name) | Codex CLI (`codex`) | ChatGPT Plus/Pro | `codex login` |
| `grok-cli:default` | Grok CLI (`grok`) | SuperGrok / X Premium | `grok login` |

The tools run in an empty folder (`.local\voter-cli`) with their own tools, web search and
plugins switched off. Any API key for the same company is removed from their environment so
that the subscription is used.

**Paid APIs.** You need a key from the provider's console. A deliberation is 9 calls of
roughly 4,000 to 8,000 input tokens each.

| Setting | Key variable | Rough cost per deliberation |
|---|---|---|
| `anthropic:claude-sonnet-5-5` | `ANTHROPIC_API_KEY` | $0.10 to $0.50 |
| `openai:<model id>` | `OPENAI_API_KEY` | $0.10 to $0.50 |
| `deepseek:deepseek-chat` (or `deepseek-reasoner`) | `DEEPSEEK_API_KEY` | about $0.01 to $0.02 |
| `xai:<grok model id>` | `XAI_API_KEY` | depends on the model |

## Setup

The easiest way is the Online voters screen in the War Room (Ctrl+O): pick a model for
each voter and the backup, and press TEST. It writes the same settings described below.
Keys are not entered there; they stay in `.env`.

By hand, add the settings to the gitignored `.env` file in the CONSENSUS folder (see `.env.example`):

```
CONSENSUS_ONLINE_MODEL_RATIONALIS=claude-cli:sonnet
CONSENSUS_ONLINE_MODEL_AETERNUM=codex-cli:default
CONSENSUS_ONLINE_MODEL_BELLATOR=deepseek:deepseek-chat
DEEPSEEK_API_KEY=<your key>
```

A voter without a setting, whose provider has no key, or whose tool is not installed stays
local. The settings are read on every call, so the next deliberation uses a change without
restarting CONSENSUS. A value set in the shell overrides the one in `.env`.

To check the setup:

```
.venv\Scripts\python.exe -m core.llm.online
.venv\Scripts\python.exe -m core.llm.online --ping
```

The first command lists each voter's state and never prints keys. `--ping` sends one tiny
request to each online voter's model.

## Shared backup model

`CONSENSUS_ONLINE_FALLBACK` names one more model, for example `deepseek:deepseek-chat`. When
an online voter's own model fails or reaches a usage limit, the voter asks the backup before
falling back to its local model. Voters without an online model never use the backup.

## Behaviour

- **Fallback:** a failed online call (no network, not signed in, rejected key, usage limit,
  an unfinished or unparseable answer) is logged as `online_model_fallback`. The voter then
  tries the shared backup model, if one is set, and otherwise answers with its local model.
  The transcript records every attempt.
- **Privacy.** When any voter can go online, every voter leaves out the vault brief
  (`50 Agents/Shared Context.md`) so private facts cannot pass between voters in later rounds.
  A deliberation that uses the brief locally stays local if a route becomes available mid-run.
  The proposal, prior CONSENSUS decisions, public references and the BELLATOR and AETERNUM
  data packets are still sent online. Set `CONSENSUS_ONLINE_SHARE_PERSONAL=1` to share the brief.
- **Token budget.** `CONSENSUS_ONLINE_TOKEN_BUDGET` (default 250000) uses reported usage where
  available, including usage reported by the Codex CLI. Codex and Grok subscription calls
  reserve a conservative estimate before starting, based on the prompt's UTF-8 size and the
  requested output allowance. The estimate is used when usage is unavailable. Later calls
  fall back to local models when the budget is exhausted.
- **Switch off:** `CONSENSUS_ONLINE_MODELS=0` sends every voter back to its local model.
- **Keys** are sent only in the provider's request header and never appear in logs, errors,
  transcripts or the status command.
