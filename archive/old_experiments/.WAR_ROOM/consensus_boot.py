import os
import sys
import time
import random
import datetime
from pathlib import Path
import json

# ==============================================================================
# MODULE 1: System Paths & Config Manager
# ==============================================================================

class SystemPaths:
    def __init__(self):
        self.root = Path("J:/CONSENSUS_SYSTEM")
        self.arbiter = self.root / "_ARBITER"
        self.votes = self.arbiter / "tmp_votes"
        self.logs = self.arbiter / "logs"
        self.exports = self.root / "exports"
        self.config = self.arbiter / "config.json"

        for path in [self.root, self.arbiter, self.votes, self.logs, self.exports]:
            path.mkdir(parents=True, exist_ok=True)

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.defaults = {
            "system_mode": "STANDBY",
            "current_view": "main",
            "theme": "military",
            "llm_provider": "ollama",
            "vote_timeout": 30,
            "auto_refresh": True,
            "refresh_interval": 5,
            "animations_enabled": True,
            "max_history": 20
        }
        self.config = self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return {**self.defaults, **json.load(f)}
            except Exception:
                pass
        return self.defaults.copy()

    def save(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def __getitem__(self, key):
        return self.config.get(key, self.defaults.get(key))

    def __setitem__(self, key, value):
        self.config[key] = value

# ==============================================================================
# MODULE 2: Boot Screen
# ==============================================================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter(text, delay=0.014):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def boot_sequence():
    mode = "ALERT" if random.random() < 0.025 else "NORMAL"
    while True:
        clear()

        if mode == "ALERT":
            print("\033[5;91m[!!] SYSTEM ALERT - BOOT FAILURE DETECTED [!!]\033[0m\n")
            time.sleep(0.4)
            alert_lines = [
                "\033[97m[SYS] POST FAILURE - Entanglement Buffers Disrupted\033[0m .................. \033[91;5m[FAIL]\033[0m",
                "\033[97m[CRITICAL] Bellator Response Loop Frozen\033[0m .............................. \033[91;5m[FAIL]\033[0m",
                "\033[97m[SYS] Memory Core Misalignment\033[0m ........................................ \033[93;5m[WARN]\033[0m",
                "\033[97m[SEC] Audit Trail Tampered – Investigating Source\033[0m ..................... \033[91;5m[ALERT]\033[0m",
                "\033[97m[AI] RATIONALIS OFFLINE – Logical Core Not Responding\033[0m .................. \033[91;5m[FAIL]\033[0m",
                "\033[97m[SYS] Emergency Subroutine Triggered – Auto-Restart in 3 seconds...\033[0m"
            ]
            for line in alert_lines:
                typewriter(line, delay=random.uniform(0.005, 0.02))
                time.sleep(random.uniform(0.2, 0.4))
            time.sleep(3)
            mode = "NORMAL"
            continue

        # NORMAL MODE
        nerv_logo = r"""
                                __ _._.,._.__
                          .o8888888888888888P'
                        .d88888888888888888K
          ,8            888888888888888888888boo._
         :88b           888888888888888888888888888b.
          `Y8b          88888888888888888888888888888b.
            `Yb.       d8888888888888888888888888888888b
              `Yb.___.88888888888888888888888888888888888b
                `Y888888888888888888888888888888CG88888P"'
                  `88888888888888888888888888888MM88P"'
 Y888K     Y8P Y888888888888888888888888oo._
   88888b    8    8888`Y88888888888888888888888oo.
   8"Y8888b  8    8888  ,8888888888888888888888888o,
   8  "Y8888b8    8888 Y8`Y8888888888888888888888b.
   8    "Y8888    8888   Y  `Y8888888888888888888888
   8      "Y88    8888     .d `Y88888888888888888888b
 .d8b.      "8  .d8888b..d88P   `Y88888888888888888888
                                  `Y88888888888888888b.
                   "Y888P Y8b. "Y888888888888888888888
                     888    888   Y888`Y888888888888888
                     888   d88P    Y88b `Y8888888888888
                     888"Y88K"      Y88b dPY8888888888P
                     888  Y88b       Y88dP  `Y88888888b
                     888   Y88b       Y8P     `Y8888888
                   .d888b.  Y88b.      Y        `Y88888
                                                  `Y88K
                                                    `Y8
                                                      '
        """
        print("\033[91m" + nerv_logo + "\033[0m")
        time.sleep(0.6)

        print("NERV SYSTEM BIOS {bios_ver}  (C) ARASAKA CORPORATION")
        print("Author: Erhardt Von Grupten Mundt")
        print("─────────────────────────────────────────────────────────────────────────────")
        time.sleep(0.5)

        fake_serial = f"0x{random.randint(10**12, 10**13-1):x}".upper()
        bios_ver = f"v5.7.1"
        year = datetime.datetime.now().year
        build_date = datetime.datetime.now().strftime('%Y-%m-%d')

        pad = 70
        boot_lines = [
            f"{bios_ver} - WAR ROOM Command Console",
            f"Copyright (C) 1995-{year} ARASAKA CORPORATION / Serial {fake_serial}",
            f"Build: {build_date}",
            "",
            "[SYS] POST:    Quantum Core Check".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] CPU:     Consensus Neural Thread v9.12 [Q-Lattice 11.8THz]".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] RAM:     65536MB ECC HBM".ljust(pad) + "\033[92mOK\033[0m",
            f"[SYS] GPU:     NERV ARX-7 Coprocessor [{random.randint(7000,9000)} GFLOPS]".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] TPM:     Secure enclave handshake".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] Boot Bus: NVMe Hyperlane x16 (1.6TB/s)".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] Display: HoloTerminal WQHD RGB OLED".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] Entanglement Buffers: Synced".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] Memory Integrity: Verified [Triple Parity]".ljust(pad) + "\033[92mOK\033[0m",
            "[SYS] Network: Port 7851 link established".ljust(pad) + "\033[92mOK\033[0m",
            "",
            "[BOOT] Initializing Monoliths:",
            " > RATIONALIS [DeepSeek Coder]".ljust(pad) + "\033[92mOK\033[0m",
            " > AETERNUM [LLaMA 3 Temporal]".ljust(pad) + "\033[92mOK\033[0m",
            " > BELLATOR [Mixtral Tactical]".ljust(pad) + "\033[92mOK\033[0m",
            "",
            "[AI] Inference Engines Calibrated".ljust(pad) + "\033[92mOK\033[0m",
            "[AI] TTS Interface (GLaDOS Personality Matrix)".ljust(pad) + "\033[92mOK\033[0m",
            "[AI] Contextual Memory Expansion".ljust(pad) + "\033[92mOK\033[0m",
            "",
            "[SEC] Firewall Status: Hardened [No intrusion detected]".ljust(pad) + "\033[92mOK\033[0m",
            "[SEC] Audit Trail: ACTIVE [Immutable]",
            "",
            "[SYS] All systems nominal. Welcome back, Commander.",
            "",
            "[94m>>> Press [ENTER] to initiate WAR ROOM <<<[0m"
        ]

        if random.random() < 0.10:
            warn_line = "[SYS] TPM: Firmware revision mismatch".ljust(pad) + "\033[93mWARN\033[0m"
            boot_lines.insert(8, warn_line)

        for line in boot_lines:
            typewriter(line, delay=random.uniform(0.004, 0.019))
            time.sleep(random.uniform(0.09, 0.18))
        input()
        break

if __name__ == "__main__":
    boot_sequence()

# ==============================================================================
# MODULE 3: Theme Definitions
# ==============================================================================

# Theme Definitions with Box Characters
THEME_DEFINITIONS = {
    "military": {
        "name": "Military HQ",
        "box_chars": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
        "colors": {"primary": 2, "secondary": 3, "accent": 6, "warning": 1},
        "labels": {
            "monolith_bellator": "TACTICAL OPERATIONS CENTER",
            "monolith_aeternum": "TEMPORAL INTELLIGENCE DIVISION",
            "monolith_rationalis": "LOGICAL ANALYSIS MATRIX",
            "history": "DECISION ARCHIVE",
            "analytics": "INTELLIGENCE ANALYTICS",
            "system_status": "COMMAND READINESS",
            "vote_status": "TRIBUNAL DELIBERATION",
            "vote_approve": "AUTHORIZATION GRANTED",
            "vote_deny": "AUTHORIZATION DENIED",
            "vote_deadlock": "COMMAND DEADLOCK"
        }
    },
    "tars": {
        "name": "TARS Interface",
        "box_chars": {"tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦", "h": "⎯", "v": "⎮"},
        "colors": {"primary": 4, "secondary": 6, "accent": 7, "warning": 3},
        "labels": {
            "monolith_bellator": "STRATEGIC.ASSESSMENT.MODULE",
            "monolith_aeternum": "TEMPORAL.ANALYSIS.MODULE",
            "monolith_rationalis": "LOGICAL.INFERENCE.MODULE",
            "history": "DECISION.MEMORY.ARCHIVE",
            "analytics": "DATA.CORRELATION.MATRIX",
            "system_status": "SYSTEM.DIAGNOSTIC",
            "vote_status": "PROCESSING.QUERY",
            "vote_approve": "OUTCOME.POSITIVE",
            "vote_deny": "OUTCOME.NEGATIVE",
            "vote_deadlock": "OUTCOME.INCONCLUSIVE"
        }
    },
    "eva": {
        "name": "Evangelion MAGI",
        "box_chars": {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "v": "▌"},
        "colors": {"primary": 5, "secondary": 1, "accent": 3, "warning": 6},
        "labels": {
            "monolith_bellator": "MAGI MELCHIOR-1 - STRATEGIC UNIT",
            "monolith_aeternum": "MAGI BALTHASAR-2 - ANALYTICAL CORE",
            "monolith_rationalis": "MAGI CASPER-3 - CORE LOGIC NODE",
            "history": "CENTRAL DOGMA ARCHIVES",
            "analytics": "PATTERN RECOGNITION SYSTEM",
            "system_status": "MAGI SYNCHRONIZATION",
            "vote_status": "CONSENSUS CALCULATION",
            "vote_approve": "PATTERN BLUE CONFIRMED",
            "vote_deny": "PATTERN RED DETECTED",
            "vote_deadlock": "PATTERN ORANGE - INDETERMINATE"
        }
    },
    "wh40k": {
        "name": "Imperial Gothic",
        "box_chars": {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
        "colors": {"primary": 6, "secondary": 3, "accent": 2, "warning": 1},
        "labels": {
            "monolith_bellator": "MUNITORUM TACTICUS",
            "monolith_aeternum": "ADMINISTRATUM HISTORICUS",
            "monolith_rationalis": "ADEPTUS MECHANICUS LOGIS",
            "history": "IMPERIAL ARCHIVE SANCTORUM",
            "analytics": "COGITATOR AUGURY",
            "system_status": "MACHINE SPIRIT PURITY",
            "vote_status": "COUNCIL OF TERRA DELIBERATION",
            "vote_approve": "IMPERIAL SANCTION GRANTED",
            "vote_deny": "IMPERIAL SANCTION DENIED",
            "vote_deadlock": "COUNCIL DISCORD - INQUISITORIAL REVIEW"
        }
    },
    "helldivers": {
        "name": "Super Earth Command",
        "box_chars": {"tl": "◢", "tr": "◣", "bl": "◥", "br": "◤", "h": "━", "v": "┃"},
        "colors": {"primary": 2, "secondary": 4, "accent": 6, "warning": 1},
        "labels": {
            "monolith_bellator": "LIBERTY DEFENSE MATRIX",
            "monolith_aeternum": "FREEDOM FORECASTING SYSTEM",
            "monolith_rationalis": "DEMOCRACY ASSESSMENT ENGINE",
            "history": "PATRIOTIC OPERATIONS RECORD",
            "analytics": "MANAGED DEMOCRACY INSIGHTS",
            "system_status": "SUPER EARTH READINESS",
            "vote_status": "DEMOCRATIC DELIBERATION",
            "vote_approve": "LIBERTY ASSURED",
            "vote_deny": "FREEDOM ENDANGERED",
            "vote_deadlock": "DEMOCRACY COMPROMISED"
        }
    }
}

# ==============================================================================
# MODULE 4: Monolith Configuration
# ==============================================================================

MONOLITHS = {
    "RATIONALIS": {
        "name": "RATIONALIS",
        "model": "deepseek-coder:33b",
        "specialization": "Logic engine",
        "color": 4,
        "magi": "CASPER-3",
        "symbol": "R",
        "log_path": "./Rationalis/rationalis.log",
        "vote_path": "./_ARBITER/tmp_votes/rationalis_vote.json",
        "analysis_prefix": {
            "military": "LOGICAL ANALYSIS:",
            "wh40k": "++ LOGICAL COGITATION ++",
            "tars": "LOGIC.SYS:",
            "helldivers": "STRATEGIC CALCULATION:",
            "eva": "CASPER ANALYTICAL MODE:"
        },
        "status": "offline"
    },
    "AETERNUM": {
        "name": "AETERNUM",
        "model": "llama3:70b",
        "specialization": "Temporal analyst",
        "color": 5,
        "magi": "BALTHASAR-2",
        "symbol": "A",
        "log_path": "./Aeternum/aeternum.log",
        "vote_path": "./_ARBITER/tmp_votes/aeternum_vote.json",
        "analysis_prefix": {
            "military": "FINANCIAL ASSESSMENT:",
            "wh40k": "++ FISCAL DIVINATION ++",
            "tars": "FINANCE.SYS:",
            "helldivers": "ECONOMIC INTELLIGENCE:",
            "eva": "BALTHASAR PROJECTION NODE:"
        },
        "status": "offline"
    },
    "BELLATOR": {
        "name": "BELLATOR",
        "model": "mixtral:8x7b",
        "specialization": "Tactical strategist",
        "color": 1,
        "magi": "MELCHIOR-1",
        "symbol": "B",
        "log_path": "./Bellator/bellator.log",
        "vote_path": "./_ARBITER/tmp_votes/bellator_vote.json",
        "analysis_prefix": {
            "military": "SECURITY ANALYSIS:",
            "wh40k": "++ TACTICAL ASSESSMENT ++",
            "tars": "SECURITY.SYS:",
            "helldivers": "COMBAT DIRECTIVE:",
            "eva": "MELCHIOR DEFENSE PROTOCOL:"
        },
        "status": "offline"
    }
}

# ==============================================================================
# MODULE 5: Vote Colors and Status Indicators
# ==============================================================================

VOTE_COLORS = {
    "APPROVE": 4,
    "DENY": 6,
    "CONDITIONAL": 5,
    "ABSTAIN": 3,
    "PENDING": 7,
    "ERROR": 6
}

STATUS_INDICATORS = {
    "online": ("ONLINE", 4),
    "processing": ("PROCESSING", 5),
    "offline": ("OFFLINE", 6),
    "ready": ("READY", 4),
    "loading": ("LOADING", 5),
    "error": ("ERROR", 6),
    "service_down": ("UNAVAILABLE", 6),
    "not_loaded": ("NOT LOADED", 5)
}

# ==============================================================================
# MODULE 6: Memory & Runtime State (SystemState)
# ==============================================================================

import datetime
from dataclasses import dataclass, field
from collections import deque
from typing import List, Dict, Optional

@dataclass
class Notification:
    message: str
    level: str = "info"
    timestamp: float = field(default_factory=time.time)
    seen: bool = False

@dataclass
class Decision:
    query: str
    verdict: str
    confidence: float
    timestamp: str
    reasoning: str

@dataclass
class MonolithMemory:
    last_updated: Optional[datetime.datetime] = None
    system_logs: List[Dict[str, str]] = field(default_factory=list)
    efficiency_rating: float = 1.0
    defcon_level: int = 5
    threat_alerts: List[Dict[str, str]] = field(default_factory=list)
    market_indices: Dict[str, Dict[str, float]] = field(default_factory=dict)
    crypto_prices: Dict[str, Dict[str, float]] = field(default_factory=dict)

class SystemState:
    def __init__(self):
        self.mode = "READY"
        self.theme = "military"
        self.current_view = "main"
        self.current_query = "No active query"

        self.notifications: deque = deque(maxlen=6)
        self.decision_history: deque = deque(maxlen=100)
        self.command_history: deque = deque(maxlen=50)
        self.log_entries: deque = deque(maxlen=1000)

        self.model_status: Dict[str, Dict[str, any]] = {
            "RATIONALIS": {"status": "offline", "loading": False},
            "AETERNUM": {"status": "offline", "loading": False},
            "BELLATOR": {"status": "offline", "loading": False}
        }

        self.monolith_memory: Dict[str, MonolithMemory] = {
            "RATIONALIS": MonolithMemory(),
            "AETERNUM": MonolithMemory(),
            "BELLATOR": MonolithMemory()
        }

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().isoformat()
        self.log_entries.append({"timestamp": timestamp, "level": level, "message": message})

    def notify(self, message: str, level: str = "info"):
        self.notifications.append(Notification(message, level))

    def record_decision(self, query: str, verdict: str, confidence: float, reasoning: str):
        self.decision_history.append(Decision(
            query=query,
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.datetime.now().isoformat()
        ))

    def add_command(self, cmd: str):
        self.command_history.append(cmd)

    def set_model_status(self, name: str, status: str, loading: bool = False):
        if name in self.model_status:
            self.model_status[name]["status"] = status
            self.model_status[name]["loading"] = loading

    def get_monolith_memory(self, name: str) -> MonolithMemory:
        return self.monolith_memory.get(name.upper(), MonolithMemory())

# ==============================================================================
# MODULE 7: LLM Interface
# ==============================================================================

import requests

class LLMInterface:
    def __init__(self, provider: str = "ollama"):
        self.provider = provider.lower()
        self.timeout = 25
        self.endpoints = {
            "ollama": {
                "api": "http://localhost:11434/api/generate",
                "status": "http://localhost:11434/api/tags"
            },
            "lmstudio": {
                "api": "http://localhost:1234/v1/completions",
                "status": "http://localhost:1234/v1/models"
            }
        }

    def check_model(self, monolith_name: str, model_name: str) -> bool:
        try:
            url = self.endpoints[self.provider]["status"]
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                SYSTEM.set_model_status(monolith_name, "service_down")
                return False

            models = response.json().get("models" if self.provider == "ollama" else "data", [])
            match = any(model_name.lower() in m.get("name" if self.provider == "ollama" else "id", "").lower()
                        for m in models)
            SYSTEM.set_model_status(monolith_name, "ready" if match else "not_loaded")
            return match
        except Exception:
            SYSTEM.set_model_status(monolith_name, "service_down")
            return False

    def query(self, monolith, query: str) -> Optional[Dict[str, str]]:
        if SYSTEM.model_status[monolith["name"]]["status"] != "ready":
            if not self.check_model(monolith["name"], monolith["model"]):
                return None

        prompt = self._build_prompt(monolith, query)
        payload = {
            "model": monolith["model"],
            "prompt": prompt,
            "temperature": 0.3,
            "max_tokens": 1024,
            "stream": False
        }

        url = self.endpoints[self.provider]["api"]
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            result = response.json()
            raw = result.get("response", "") if self.provider == "ollama" else result.get("choices", [{}])[0].get("text", "")
            return self._parse_response(raw)
        except Exception as e:
            SYSTEM.log(f"{monolith['name']} query error: {e}", "ERROR") # type: ignore
            return None

    def _build_prompt(self, monolith, query: str) -> str:
        return f"""{monolith["analysis_prefix"][SYSTEM.theme]}

QUERY: {query}

Respond in this format:
VOTE: [APPROVE / DENY / ABSTAIN]
REASONING: [short but clear]
CONFIDENCE: [0.0 to 1.0]
"""

    def _parse_response(self, text: str) -> Dict[str, str]:
        lines = text.strip().splitlines()
        vote, reasoning, confidence = "ABSTAIN", "Unclear", 0.5

        for line in lines:
            upper = line.upper()
            if "VOTE:" in upper:
                if "APPROVE" in upper: vote = "APPROVE"
                elif "DENY" in upper: vote = "DENY"
                elif "ABSTAIN" in upper: vote = "ABSTAIN"
                elif "CONDITIONAL" in upper: vote = "CONDITIONAL"
                elif "ERROR" in upper: vote = "ERROR"
            elif "REASONING:" in upper:
                reasoning = line.partition(":")[2].strip()
            elif "CONFIDENCE:" in upper:
                try:
                    confidence = float(line.partition(":")[2].strip())
                except ValueError:
                    confidence = 0.5

        return {
            "vote": vote,
            "reasoning": reasoning,
            "confidence": f"{confidence:.2f}"
        }

# ==============================================================================
# MODULE 9: Basic UI Utilities
# ==============================================================================

import curses

def safe_addstr(window, y: int, x: int, text: str, attr: Optional[int] = 0):
    max_y, max_x = window.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x:
        trimmed = text[: max_x - x - 1]
        try:
            window.addstr(y, x, trimmed, attr)
        except Exception:
            pass

# ==============================================================================
# MODULE 10: Launcher + CLI Entry Point
# ==============================================================================

def main():
    PATHS = SystemPaths()
    boot_sequence()

    config = ConfigManager(PATHS.config)
    SYSTEM.theme = config["theme"]
    SYSTEM.log("CONSENSUS War Room Booted", "STARTUP")

    watch_proposal_file()  # Auto-voting trigger

    try:
        curses.wrapper(render_ui)
    except Exception as e:
        SYSTEM.log(f"UI crashed: {e}", "CRITICAL")
        print(f"UI error: {e}")

if __name__ == "__main__":
    main()


# ==============================================================================
# MODULE 11: Proposal Engine (Auto-Voting)
# ==============================================================================

class ProposalEngine:
    def __init__(self, consensus_engine: ConsensusEngine):
        self.engine = consensus_engine

    def submit(self, query: str):
        SYSTEM.log(f"Proposal submitted: {query}", "STARTUP")
        SYSTEM.mode = "VOTING"
        SYSTEM.notify("Processing new query...", level="info")
        verdict = self.engine.run_consensus(query)
        SYSTEM.notify(f"Consensus verdict: {verdict}", level="success" if verdict == "APPROVE" else "warning")


# ==============================================================================
# MODULE 12: Proposal Watcher
# ==============================================================================

import json
import hashlib
import threading

PROPOSAL_PATH = Path("J:/CONSENSUS_SYSTEM/_ARBITER/proposal.json")
_last_proposal_hash = None

def hash_string(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def watch_proposal_file(interval=5):
    def monitor():
        global _last_proposal_hash
        SYSTEM.log("Proposal watcher active.", "INFO")

        while True:
            try:
                if PROPOSAL_PATH.exists():
                    content = PROPOSAL_PATH.read_text().strip()
                    if not content:
                        time.sleep(interval)
                        continue

                    data = json.loads(content)
                    proposal = data.get("query", "").strip()
                    if not proposal:
                        time.sleep(interval)
                        continue

                    proposal_hash = hash_string(proposal)
                    if proposal_hash != _last_proposal_hash:
                        _last_proposal_hash = proposal_hash
                        SYSTEM.log(f"New proposal detected: {proposal}", "INFO")
                        ProposalEngine(ConsensusEngine(LLMInterface())).submit(proposal)
                        PROPOSAL_PATH.unlink()

            except Exception as e:
                SYSTEM.log(f"Proposal watcher error: {e}", "ERROR")

            time.sleep(interval)

    t = threading.Thread(target=monitor, daemon=True)
    t.start()

# ==============================================================================
# MODULE 13: Diagnostics Bar
# ==============================================================================

import psutil

def get_system_diagnostics():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    uptime = time.time() - psutil.boot_time()
    return {
        "CPU": f"{cpu:.1f}%",
        "MEM": f"{mem:.1f}%",
        "DISK": f"{disk:.1f}%",
        "UPTIME": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "LLM": SYSTEM.model_status["RATIONALIS"]["status"].upper(),
        "TTS": "READY",  # Placeholder
        "API": "ONLINE"
    }

def draw_diagnostics_bar(stdscr, theme: str):
    h, w = stdscr.getmaxyx()
    stats = get_system_diagnostics()
    line = f"MODE: {SYSTEM.mode:<8} | THEME: {theme.upper():<10} | " + " | ".join(
        f"{k}: {v}" for k, v in stats.items()
    )
    safe_addstr(stdscr, h - 1, 1, line[:w-2], curses.A_REVERSE)

# ==============================================================================
# MODULE 14: TTS Subsystem
# ==============================================================================

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class TTSManager:
    def __init__(self, voice: str = "default"):
        if pyttsx3 is None:
            SYSTEM.log("TTS not available: pyttsx3 not installed", "WARNING")
            self.engine = None
            return

        self.engine = pyttsx3.init()
        if voice != "default":
            for v in self.engine.getProperty("voices"):
                if voice.lower() in v.name.lower():
                    self.engine.setProperty("voice", v.id)
                    break

    def speak(self, message: str):
        if self.engine:
            SYSTEM.log(f"TTS: {message}", "INFO")
            self.engine.say(message)
            self.engine.runAndWait()
        else:
            SYSTEM.log("TTS engine not initialized", "ERROR")

if SYSTEM.mode != "CRITICAL":
    TTSManager("glados").speak(f"Consensus reached. Verdict: {final}")


# ==============================================================================
# MODULE 15: Web Interface
# ==============================================================================

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

WEB_PORT = 7851
WEB_ROOT = "web"
PROPOSAL_FILE = Path("J:/CONSENSUS_SYSTEM/_ARBITER/proposal.json")

app = FastAPI()
app.mount("/static", StaticFiles(directory=f"{WEB_ROOT}/static"), name="static")
templates = Jinja2Templates(directory=f"{WEB_ROOT}/templates")

@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit")
def submit_proposal(request: Request, proposal: str = Form(...)):
    if proposal.strip():
        data = {"query": proposal.strip()}
        PROPOSAL_FILE.write_text(json.dumps(data, indent=2))
    return RedirectResponse("/", status_code=303)

# ==============================================================================
# MODULE N: [Descriptive Title]
# ==============================================================================


# ==============================================================================
# MODULE N: [Descriptive Title]
# ==============================================================================


# ==============================================================================
# MODULE N: [Descriptive Title]
# ==============================================================================

