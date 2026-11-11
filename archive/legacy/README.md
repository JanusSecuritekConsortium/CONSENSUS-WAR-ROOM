# Legacy: the first CONSENSUS

The earliest pieces of CONSENSUS, kept for history. Nothing here runs or is imported by the
current system.

| Item | What it was |
| --- | --- |
| `AETERNUM/`, `BELLATOR/`, `RATIONALIS/` | The first three monoliths (spring 2025): one folder each with placeholder programs and a vote log. The logs hold the first recorded tribunal votes, from 13 May 2025. |
| `arbiter_config_2025.json` | The first tribunal settings file: the original monolith prompts, temperatures and voting rules. Retired because its BELLATOR (a cautious risk assessor) contradicts the current one. |
| `anima_bot.py` | The first Telegram assistant bot, the forerunner of AURELIUS. It read its keys from `.env`. |

The 2025 monoliths were replaced by the modular tribunal in `core/` and the models now run in
Msty. Their old voice-model downloads (Dia 1.6B, Kokoro 82M, XTTS v2) were removed in November
2026; they are public downloads. The RVC voice tool from that period still lives in
`archive/pre_modular_backups/Rationalis/TTS/` because the current voices use it.

Some files stay on the local PC only and are not published: Rationalis' memory file and
`write_memory.py` (personal context) and `RATIONALIS/agent/` (third-party data).
