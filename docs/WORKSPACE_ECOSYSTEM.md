# G Drive Workspace Ecosystem

This project is part of a larger local workspace rooted at `G:\`. The Git
repository remains at `G:\CONSENSUS_SYSTEM` so the public repository does not
accidentally absorb private notes, model binaries, installed applications,
Kiwix archives, caches, or local runtime state.

## Important Local Paths

| Area | Path | Role | Git policy |
| --- | --- | --- | --- |
| Active project | `G:\CONSENSUS_SYSTEM` | Source-controlled Consensus War Room implementation | Tracked |
| Msty Studio | `G:\Msty\MstyStudio` | Installed Msty Studio app and bundled local runtime | Document only |
| AI models | `G:\AI_MODELS` | Local model storage for Hugging Face, GGUF, Ollama, Clawd, and related runtimes | Inventory only |
| TARS archive | `G:\Backup\Projects\TARS` | Preserved robot/control code and large STEP model | Source snippets only if intentionally imported |
| Flet prototype archive | `G:\Backup\Projects\Flet-Prototype` | Earlier Flet-based Consensus UI prototype | Local reference only; not tracked |
| Kiwix/Msty knowledge stack | `G:\Kiwix\Kowledge Stack Msty` | Local knowledge corpus and exported project/context vaults | Index only |
| Obsidian vault | `G:\Obsidian\CONSENSUS_SYSTEM` | Local Obsidian notes for Consensus | Index only unless specific notes are approved |

## Why Git Is Not Rooted At `G:\`

Putting `.git` at `G:\` would make the whole drive the working tree. That would
expose:

- multi-GB model weights and CUDA/runtime binaries
- installed Electron app files and bundled `node_modules`
- personal Obsidian/Kiwix/drive-export content
- logs, caches, generated audio/video, and runtime state
- sensitive local configuration and credentials

The safer pattern is to keep this repository focused and add curated references,
adapters, and import scripts for the surrounding local ecosystem.

## Model Inventory

Known model families and runtime folders observed under `G:\AI_MODELS`:

- `huggingface\DeepSeek`
- `huggingface\Mistral`
- `huggingface\YI-34B`
- `unsloth\Mistral-Small-3.2-24B-Instruct-2506-GGUF` (BELLATOR's current model)
- `mradermacher\Mixtral-8x7B-Instruct-v0.1-i1-GGUF` (BELLATOR's previous model; too big for 32 GB of RAM)
- `TheBloke\Mixtral-8x7B-Instruct-v0.1-GGUF` (older files; current llama.cpp cannot load them)
- `TheBloke\Yi-34B-Chat-GGUF`
- `TheBloke\deepseek-coder-33B-instruct-GGUF`
- `lmstudio-community\Meta-Llama-3.1-8B-Instruct-GGUF`
- `lmstudio-community\DeepSeek-R1-Distill-Qwen-7B-GGUF`
- `lmstudio-community\Mistral-7B-Instruct-v0.3-GGUF`
- `lmstudio-community\Llama-3.3-70B-Instruct-GGUF`
- `lmstudio-community\gemma-3-12b-it-GGUF`
- `Lucy-in-the-Sky\UI-TARS-1.5-7B-Q4_K_M-GGUF`
- `NousResearch\Hermes-3-Llama-3.1-8B-GGUF`
- `Ollama\models`, `Ollama\manifests`, and `Ollama\blobs`
- `MaziyarPanahi\solar-pro-preview-instruct-GGUF`
- `reedmayhew\claude-3.7-sonnet-reasoning-gemma3-12B`
- `Clawd`

Do not commit the model files themselves. If the project needs model awareness,
add model aliases, endpoint configuration, or generated inventory summaries.

## Knowledge Stack Notes

The Kiwix/Msty stack includes project and personal context exports. Treat it as
a source of local reference material, not as repository content. The project can
consume selected summaries or paths after a deliberate review.

Relevant folders observed:

- `G:\Kiwix\Kowledge Stack Msty\PsiCorpus_v1\CONSENSUS_SYSTEM`
- `G:\Kiwix\Kowledge Stack Msty\PsiCorpus_v1_Obsidian\CONSENSUS_SYSTEM`
- `G:\Kiwix\Kowledge Stack Msty\PsiCorpus_Full_Archive\CONSENSUS_SYSTEM`
- `G:\Kiwix\Kowledge Stack Msty\PsiCorpus_Full_Archive\TARS_Control`

## TARS Notes

`G:\Backup\Projects\TARS` contains the control scripts and large mechanical model formerly stored at `G:\.TARS` (moved 2026-10-09):

- `download_model.py`
- `servo_abstractor.py`
- `servo_controller.py`
- `tars_runner.py`
- `tars_3_v9_tvCxpHViUu.step` (large binary/CAD asset, do not commit)

The active repository already has related TARS/servo files under `_ARBITER/`.
Future imports should compare source files first and avoid bringing the STEP
asset into Git.
