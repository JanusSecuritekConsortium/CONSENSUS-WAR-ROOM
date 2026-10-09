# Linux migration readiness

Assessment date: 2026-09-07. These changes prepare the application for Linux;
they do not certify native desktop, CUDA, or voice-model operation on Linux.

Validation in the Windows workspace: 34 targeted portability, voice, boot,
and packaging tests passed; 490 active Python files compiled; both shell
launchers passed Bash syntax checks. Linux branches were tested with mocked
platform/process boundaries, not actual Linux audio or desktop execution.
The broader pytest run was interrupted before completion. Its observed
Windows-only executable-name assertion was updated and passed on rerun;
there is no full-suite pass claim.

## OS choice for the current PC

Detected locally: Intel Core i9-12900KF, NVIDIA RTX 4070 with 12 GB VRAM,
32 GB RAM. Motherboard, networking, peripherals, and target disk layout have
not been validated for Linux.

Stock SteamOS is not the recommended target for this NVIDIA PC. Valve's
[current hardware guidance](https://help.steampowered.com/en/faqs/view/65B4-2AA3-5F37-4227)
lists AMD graphics in its expanded PC support. Consider Bazzite KDE's NVIDIA
desktop image for a gaming-oriented experience, or Fedora KDE for easier
development/runtime customization. Use Bazzite's hardware image picker;
NVIDIA Steam Gaming Mode has beta caveats. See the
[Bazzite editions](https://docs.bazzite.gg/General/FAQ/) and
[Gaming Mode caveats](https://docs.bazzite.gg/General/Installation_Guide/Installing_Bazzite_for_HTPC_Setups/).

## Preserve local data first

Close running CONSENSUS processes before copying databases and history.
Back up the working tree including uncommitted changes and ignored runtime
data: `.env`, `_ARBITER`, `memory`, `reports`, voice models, external GLaDOS
project/checkpoints, and the RVC project. Git alone is not a backup of these.
Separately preserve Msty settings/exports, model storage, Obsidian and Kiwix
data outside this repository. Keep a verified backup and the Windows disk
until Linux has passed real usage tests.

Copy the project into a writable directory such as `~/Projects/CONSENSUS_SYSTEM`
on a Linux filesystem. Recreate environments: Windows `.venv`, `.exe` files,
CUDA libraries, and installed Windows applications cannot serve as Linux
runtimes. Do not overwrite a copied Windows environment with Linux packages;
retain it in the backup and omit it from the Linux working copy.

## First source installation

Use a Python version compatible with the pinned Flet 0.28.x dependencies;
Python 3.10 matches existing CI. Newer Python versions need validation.
Install Python/venv and Linux desktop libraries through the selected distro's
supported package workflow. On an immutable OS use a supported development
container or user runtime, rather than treating the OS root as a permanent
package workspace. A container also needs working display/audio and NVIDIA
access if it hosts those components; host Msty/Ollama endpoints must be reachable.

From the Linux repository directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pip install -e .
.venv/bin/python -m pytest
.venv/bin/python tools/compile_active_tree.py
.venv/bin/python consensus_war_room_genesis.py --no-boot --backend mock "Linux migration smoke test"
bash boot.sh --safe
bash boot.sh
```

`--safe` checks the configured provider and may fail until that provider is
installed and reachable. Reinstall Msty/Ollama for Linux, restore supported
model files, and check endpoint URLs and model aliases. Verify GPU discovery
with `nvidia-smi` and a real generation; do not infer acceleration from a
successful HTTP connection. Keep models unloaded while evaluating game performance.

MCP registration should use the absolute Linux path to `.venv/bin/python`,
with the absolute path to `integrations/mcp/consensus_mcp_server.py` as its
argument. A shell entry point is also available:
`bash integrations/mcp/run_consensus_mcp.sh`.

## Voice changes and remaining setup

On Linux, `voice/voice_config.linux.json` overlays the base configuration.
Its relative paths resolve from the project root. Windows retains the existing
configuration. Custom configuration files can have their own sibling
`<name>.linux.json` overlay.

Linux base speech uses `espeak-ng` (or `espeak`); WAV playback uses `paplay`
or `aplay`. Install these using the selected OS's supported workflow. Missing
tools and failed playback return explicit failures, not successful playback.
These tools are not installed by the Python requirements.

Microsoft SAPI voices do not transfer. The replacement base voice sounds
different, including when fed through RVC. Native GLaDOS and RVC models still
require their own Linux-compatible dependencies. The Linux configuration
expects a separately prepared `.venv-voice/bin/python`, the existing model
files, and the RVC source under `_ARBITER/tts_audio/`. Create that environment
and install each voice project's compatible PyTorch/dependencies before
claiming those voices work. FFmpeg is discovered through the Linux PATH.
No voice weights are downloaded and no voice environments are created by this patch.

## Packaging and validation limits

`python build_exe.py` now chooses the native executable name and omits Windows
version metadata on Linux. It must run on Linux to produce a Linux build;
no Linux binary has been produced or tested in this Windows session.

The existing theme screenshot automation depends on Win32 window capture.
`boot.sh --validate` reports this limitation after tests/compilation and returns
a nonzero result. Run the commands above and manually verify the desktop,
themes, folder opening, exports, history, MCP, and audible voice output.
Full Linux screenshot automation is not implemented.

## Star Citizen is a separate migration check

RSI [officially supports Windows only](https://support.robertsspaceindustries.com/hc/en-us/articles/360000758928-Game-and-Launcher-Requirements).
The community [LUG Helper](https://github.com/starcitizen-lug/lug-helper)
installs and maintains a Wine-based Linux environment. This is community
compatibility, not a native Linux release or a guarantee for future patches.

Follow the current [LUG Quick Start](https://wiki.starcitizen-lug.org/Quick-Start-Guide):
use its preflight checks, a Linux filesystem on an SSD with adequate free
space (currently about 150 GB minimum, plus room for updates), and the
recommended runner. Avoid putting the Wine prefix/game on NTFS. For immutable
systems the guide recommends the Helper AppImage. Consult current guidance
for memory limits, NVIDIA/Wayland issues, peripherals, and anti-cheat; do not
disable anti-cheat. The LUG [distribution recommendations](https://wiki.starcitizen-lug.org/Tips-and-Tricks)
include Fedora and Bazzite, with customization caveats for immutable systems.

Before removing Windows, test several actual multiplayer sessions, game
updates, audio/microphone, controls, suspend/resume, and any HOTAS/head tracking.
No Star Citizen installation, game launch, disk partitioning, or OS installation
has been performed as part of the code changes.
