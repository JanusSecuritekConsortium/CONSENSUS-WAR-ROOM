# Reproducing CONSENSUS on another PC

This guide takes a fresh copy of this repository to a real tribunal vote on local models. Every step was
checked on 2026-11-19 by cloning the public repository into an empty folder and following it.

The repository holds the complete program. What it leaves out on purpose:

- **Model files.** These are large public downloads; step 4 lists them.
- **Voice models.** These are optional; without them the system voice is used.
- **Accounts and personal context.** Telegram, mail, calendar, online-model keys and the Obsidian vault are optional.

CONSENSUS is free for noncommercial use under the [PolyForm Noncommercial License 1.0.0](../LICENSE.md).

## What you need

| Item | Tested with | Notes |
| --- | --- | --- |
| Operating system | Windows 11 | Linux runs the tests and the command line; see [LINUX_MIGRATION.md](LINUX_MIGRATION.md). |
| Python | 3.10.9 | 3.10 or newer. CI uses 3.10. |
| Git | any recent | Used only to clone the repository. |
| Msty Studio | 2.9.12 | Serves the models through its built-in llama.cpp server. |
| llama.cpp (inside Msty) | build 12110 | Msty installs and updates it. |
| Graphics card | NVIDIA RTX 4070, 12 GB, driver 621 | Any card works if memory allows. CPU-only is possible but very slow. |
| RAM | 32 GB | See "Memory" below. |
| Disk | about 55 GB | Program about 120 MB with its Python packages; the four models about 49 GB. |

### Memory

A vote loads one voter model at a time and unloads the others first. Each voter model needs its file
size plus about 3 GB, split between the graphics card and RAM.

| Voter | Model file size | Needs about |
| --- | --- | --- |
| RATIONALIS | 15.4 GB | 18.5 GB |
| AETERNUM | 15.8 GB | 19 GB |
| BELLATOR | 13.3 GB | 16.5 GB |

With a 12 GB card, the rest comes from RAM, so keep about 10 GB of RAM free during a vote. Close games,
large browser sessions and other AI apps first. When memory is short, the tribunal waits up to 10 minutes,
then stops with a clear message instead of answering from swap, where one answer can take 20 minutes.

### Storage speed

Each voter's model is read from disk every time it loads, and a vote loads a model at least once per
voter per round. Keep the model files on a fast drive: an internal NVMe SSD, or a USB SSD plugged
straight into a USB 3.2 port on the motherboard. On the tested PC, a USB SSD connected through a hub read
only about 40 MB/s, so loading one 15 GB model took about 7 minutes and a vote took hours. At 1,000 MB/s
the same load takes about 15 seconds.

To measure your drive, time a copy of one model file to another drive, or run
`.\.venv\Scripts\python.exe -m integrations.mcp.voter_check` and look at "first answer in N s" (most of that is load time).

## 1. Get the code and install it

Install [Python 3.10 or newer](https://www.python.org/downloads/) (tick "Add python.exe to PATH") and
[Git](https://git-scm.com/downloads). Then, in PowerShell:

```powershell
git clone https://github.com/JanusSecuritekConsortium/CONSENSUS-WAR-ROOM.git
cd CONSENSUS-WAR-ROOM
.\setup.bat
```

Without Git, use **Code → Download ZIP** on the GitHub page, unzip it, and double-click `setup.bat`.

`setup.bat` does steps 1 and 2 for you, and can safely be run again:

- creates the `.venv` folder and installs the program and its Python packages;
- runs a test vote with simulated voters and the health check;
- checks whether Msty's model server is reachable and lists which voter models it already has.

The folder can live on any drive; nothing in the code expects a fixed path.

<details>
<summary>The same steps by hand</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
python consensus_war_room_genesis.py --no-boot --backend mock "Should we proceed?"
python consensus_war_room_genesis.py --health
```

</details>

## 2. What the first check shows

The test vote prints a verdict marked `SIMULATION ONLY`. This is expected: simulated voters give canned
answers and only prove the program runs. The health check should pass everything except `voice_files`,
which stays DEGRADED until you add voice models. That is optional.

## 3. Install Msty Studio

1. Download Msty Studio from its official site (msty.studio) and install it.
2. Open it once, so its local model server starts. CONSENSUS talks to two Msty addresses:

| Service | Address | Used for |
| --- | --- | --- |
| Msty llama.cpp server | `http://localhost:11454` | The voters' models. This is the one that matters. |
| Msty Local Service | `http://127.0.0.1:11964` | Status and older integrations. |

These are Msty's defaults and are already set in `_ARBITER/genesis_config.json` and `.env.example`.

## 4. Download the models

In Msty Studio, open the model hub, search Hugging Face for each repository below and download the exact
file named. The tribunal finds each model by this name.

| Role | Maker | Hugging Face repository | File | Size |
| --- | --- | --- | --- | --- |
| RATIONALIS (Logic) | Alibaba | [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) | `Qwen3.8-27B-UD-Q4_K_M.gguf` | 15.4 GB |
| AETERNUM (Finance) | Google | [unsloth/gemma-4-26B-A4B-it-GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF) | `gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` | 15.8 GB |
| BELLATOR (Growth) | Mistral AI | [unsloth/Mistral-Small-3.2-24B-Instruct-2506-GGUF](https://huggingface.co/unsloth/Mistral-Small-3.2-24B-Instruct-2506-GGUF) | `Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf` | 13.3 GB |
| ARBITER and base model | Nous Research | [NousResearch/Hermes-3-Llama-3.1-8B-GGUF](https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B-GGUF) | `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` | 4.6 GB |

Direct download links, if you prefer to download the files yourself and add them to Msty as local models
(keep the `repository/file` name Msty shows, or update `_ARBITER/genesis_config.json` to match):

- https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/main/Qwen3.8-27B-UD-Q4_K_M.gguf
- https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF/resolve/main/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf
- https://huggingface.co/unsloth/Mistral-Small-3.2-24B-Instruct-2506-GGUF/resolve/main/Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf
- https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B-GGUF/resolve/main/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf

Run `setup.bat` again afterwards: its last section should list all four models as `ready`.

Each voter comes from a different maker, on purpose: different training gives different reasoning. The
ARBITER does not vote by opinion. It applies fixed rules, so its model matters little.

To use other models, change `agent_model_overrides` and `node_overrides` in
`_ARBITER/genesis_config.json`. Keep the three voters from three different makers. A voter falls back only
to another model from its own maker that is already on the server, never to a model of 40B or larger.

### Msty model settings

These are Msty's defaults on the tested PC. Check them if votes fail.

| Setting | Value | Why |
| --- | --- | --- |
| Context size | 8192 tokens | CONSENSUS trims each prompt to fit 8,192 tokens (`core/prompting/fit.py`). |
| Parallel requests | 1 | One answer at a time; the voters take turns. |
| Unload after idle | 600 seconds | Frees memory after a vote. |
| Thinking / reasoning | No change needed | CONSENSUS asks for no thinking in every voter request. |

## 5. Check that each voter's model loads

```powershell
.\.venv\Scripts\python.exe -m integrations.mcp.voter_check
```

This loads each voter's model in turn, asks it for one word, and reports whether it loaded and how fast it
answered. Nothing is saved. If a model fails to load, the message comes from the model server itself. A
llama.cpp update can refuse older conversions; download a current file.

## 6. Run a real vote

Command line:

```powershell
.\.venv\Scripts\python.exe consensus_war_room_genesis.py --no-boot "Should we buy a second backup drive this month?"
```

Desktop window:

```powershell
.\boot.bat
```

A real vote runs three rounds with each of the three voters: nine model answers. If the voters are unsure,
they abstain and the vote reruns up to three more times. On the tested PC one answer takes about 1 to 3
minutes once the model is loaded, so a vote takes roughly 15 to 60 minutes. The result says which model
gave each answer. A real vote never falls back to the mock voters.

## Optional pieces

None of these is needed for a vote. Each has its own guide.

| Piece | What it adds | Guide |
| --- | --- | --- |
| Online voters | Run a voter on Claude, ChatGPT, Grok or a paid API instead of a local model | [ONLINE_MODELS.md](ONLINE_MODELS.md) |
| Voices | ARBITER and AURELIUS speak through RVC voice models | `python -m voice.voice_check` lists what is missing |
| Guest door | Another AI system asks the tribunal for advice | [GUEST_DOOR.md](GUEST_DOOR.md) |
| Phone page | Submit and answer votes from a phone | [PHONE_ACCESS.md](PHONE_ACCESS.md) |
| Second brain | Local Obsidian notes as background context | `CONSENSUS_SECOND_BRAIN` in `.env` |
| Telegram, mail, calendar | AURELIUS assistant features | [AURELIUS_AGENT.md](AURELIUS_AGENT.md) |

Copy `.env.example` to `.env` and fill in only what you use. Never commit `.env`.

## Running the tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Tests that open the desktop window are skipped unless `CONSENSUS_GUI_TESTS=1` is set. On Linux,
`bash tools/linux_tests.sh` runs the same tests.

## When something goes wrong

| What you see | Likely cause | What to do |
| --- | --- | --- |
| "Low memory" before a vote, or "Not enough free memory" during it | The voter's model plus 3 GB does not fit in free RAM and graphics memory | Close other programs and run the vote again |
| Answers take 20 minutes each | The model is running partly from swap | The same; also unload other models in Msty |
| "The msty-llama-cpp model server is not answering" | Msty's server is down | Open Msty Studio; a voter waits up to 10 minutes for it |
| "Prompt too long for the model's context window" | Context size below 8192 | Set the model's context to 8192 in Msty |
| A voter's model will not load | File too old for Msty's llama.cpp | Download a current GGUF |
| Verdict says `SIMULATION ONLY` | The backend is `mock` | Use `--backend msty-local` or the default config |
