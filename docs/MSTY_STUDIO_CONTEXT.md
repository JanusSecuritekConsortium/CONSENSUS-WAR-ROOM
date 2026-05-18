# Msty Studio Local Context

Msty Studio is installed locally at:

```text
G:\Msty\MstyStudio
```

The Consensus runtime already supports Msty/Ollama-compatible backends through
`integrations/msty/` and the CLI flags documented in `README.md`.

## Observed Local Install Shape

Important paths:

- `G:\Msty\MstyStudio\MstyStudio.exe`
- `G:\Msty\MstyStudio\localai\msty-local-studio.exe`
- `G:\Msty\MstyStudio\localai\lib\ollama\cuda_v12\ggml-cuda.dll`
- `G:\Msty\MstyStudio\localai\lib\ollama\cuda_v13\cublas64_13.dll`
- `G:\Msty\MstyStudio\localai\lib\ollama\cuda_v13\cublasLt64_13.dll`
- `G:\Msty\MstyStudio\resources\app-update.yml`
- `G:\Msty\MstyStudio\resources\app.asar`

This is an installed application tree, not source code for this repository. Do
not commit the executable, DLLs, `.pak`, `.asar`, `node_modules`, or local runtime
binaries.

## Default Consensus Backend Endpoints

Consensus currently knows these local endpoints:

| Backend | Default endpoint | CLI flag |
| --- | --- | --- |
| Msty Claw bridge | `http://127.0.0.1:11964` | `--backend msty-claw` |
| Msty local LLaMA.cpp | `http://localhost:11454` | `--backend msty-llama-cpp` or `--backend msty-local` |
| Ollama direct | `http://127.0.0.1:11434` | `--backend ollama` |

Useful commands:

```powershell
python consensus_war_room_genesis.py --provider-diagnose --verbose
python consensus_war_room_genesis.py --provider-status --verbose
python consensus_war_room_genesis.py --list-models
python consensus_war_room_genesis.py --api
```

## Environment Variables

These can override local endpoint discovery:

```text
MSTY_BASE_URL=http://127.0.0.1:11964
MSTY_LLAMA_CPP_BASE_URL=http://localhost:11454
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

## Update Metadata Observed

`resources\app-update.yml` reports:

```yaml
provider: generic
url: https://next-assets.msty.studio/app/latest/win
updaterCacheDirName: mstystudio-updater
publisherName:
  - Ashok Gelal
```

## Integration Direction

Keep Msty Studio itself outside Git. Add source-controlled integration in this
repository through:

- backend endpoint probes
- model alias mapping
- local model inventory summaries
- Msty live-context API docs
- scripts that inspect the local install without copying binaries
