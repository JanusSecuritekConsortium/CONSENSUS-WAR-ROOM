#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (Optimized)

An enhanced decision-making system with three distinct AI monoliths:
- RATIONALIS: Logical analysis using DeepSeek Coder
- AETERNUM: Financial/Historical analysis using LLaMA 3
- BELLATOR: Tactical/Security analysis using Mixtral

Features:
- Multiple visual themes (Military, WH40k, TARS, Helldivers)
- Real-time model integration with Ollama/LM Studio
- Individual monolith specialized screens
- Decision history and consensus tracking
- System health monitoring
- Command-line interface with autocomplete

Author: Erhardt Von Grupten Mundt
Version: 4.2.0
Build: 2025-05-20
Date: May 2025
"""

# ==============================================================================
# MODULE 1: System Constants & Config
# ============================================================================== 
import os
import sys
import json
import time
import curses
import random
import datetime
import threading
import requests
import csv
import signal
import shutil
import subprocess
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple, Optional, Any, Union

# Optional dependencies
try:
    import psutil
except ImportError:
    psutil = None

try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

# Paths and File Constants
BASE_PATH = Path("J:/CONSENSUS_SYSTEM")
VOTES_PATH = BASE_PATH / "votes"
LOG_PATH = BASE_PATH / "logs"
MEMORY_PATH = BASE_PATH / "memory.json"
PROPOSAL_FILE = BASE_PATH / "proposal.json"
CONFIG_FILE = BASE_PATH / "config.json"

# Monolith configuration
MONOLITHS = {
    "Rationalis": {
        "name": "Rationalis",
        "model": "deepseek-coder:33b",
        "specialization": "Logic engine",
        "color": curses.COLOR_CYAN
    },
    "Aeternum": {
        "name": "Aeternum",
        "model": "llama3:70b",
        "specialization": "Temporal analyst",
        "color": curses.COLOR_MAGENTA
    },
    "Bellator": {
        "name": "Bellator",
        "model": "mixtral:8x7b",
        "specialization": "Tactical strategist",
        "color": curses.COLOR_RED
    }
}

# Theme configuration
THEMES = [
    "Military HQ",
    "TARS Interface",
    "Evangelion MAGI",
    "Imperial Gothic",
    "Super Earth Command"
]

# API Configuration Flags
API_FLAGS = {
    "YahooFinance": True,
    "AlphaVantage": True,
    "CoinGecko": True,
    "NewsAPI": True,
    "GDELT": True,
    "IBKR": IB_AVAILABLE,
    "TTS": True,
    "Tortoise": True
}

# Metadata
VERSION = "4.1.0"
BUILD_DATE = "2025-05-20"
SESSION_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")


# ==============================================================================
# MODULE 2: Boot Sequence & Initialization
# ==============================================================================

# ===== SYSTEM LOGOS AND GRAPHICS =====
NERV_LOGO = r"""
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

from colorama import init, Fore, Style
init(autoreset=True)

def type_out(text, delay=0.02):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def boot_system():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.RED + NERV_LOGO)

    BIOS_BOOT_STEPS = [
        "ARASAKA BIOS v3.7.0 - WAR ROOM Interface",
        "Copyright (C) 1995-2025 NEURODYNE SYSTEMS",
        "",
        "Detecting CPU... Consensus Neural Thread v9.12 .............. OK",
        "Detecting Memory... 65536MB ................................ OK",
        "[SYS] Syncing quantum entanglement buffers...",
        "Initializing Monolith Interfaces:",
        " > RATIONALIS [DeepSeek Coder] ............................ OK",
        " > AETERNUM [LLaMA 3 Temporal] ........................... OK",
        " > BELLATOR [Mixtral Tactical] ........................... OK",
        "Verifying Inference Engines ............................... OK",
        "Loading TTS Subsystem... GLaDOS Interface Ready ........... OK",
        "Establishing Shadow Context ............................... OK",
        "All systems functional.",
        "",
        ">>> Press [ENTER] to initiate WAR ROOM <<<"
    ]

    for line in BIOS_BOOT_STEPS:
        color = Fore.GREEN if line.strip().endswith("OK") else Fore.WHITE
        type_out(color + line, delay=random.uniform(0.005, 0.02))
        time.sleep(random.uniform(0.15, 0.4))

    # Boot sequence logic authored by Erhardt Von Grupten Mundt


# ==============================================================================
# MODULE 3: Logging System
# ==============================================================================
from enum import Enum

class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    SYSTEM = "SYSTEM"

def log_event(level: str, component: str, message: str):
    """
    Log an event with structured formatting and console output.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "component": component,
        "message": message,
        "session": SESSION_ID
    }
    formatted = f"[{entry['timestamp']}] [{entry['level']}] [{entry['component']}] {entry['message']}"

    if entry['level'] == "ERROR":
        print(Fore.RED + formatted)
    elif entry['level'] == "WARN":
        print(Fore.YELLOW + formatted)
    elif entry['level'] == "DEBUG":
        print(Fore.MAGENTA + formatted)
    else:
        print(Fore.CYAN + formatted)

    if 'log_entries' in globals():
        log_entries.append(entry)

def log_header(title: str):
    bar = "=" * 70
    print(Fore.WHITE + Style.BRIGHT + f"
{bar}
{title.center(70)}
{bar}")


# ==============================================================================
# MODULE 4: Configuration Management
# ==============================================================================

def load_config(path: Path = CONFIG_FILE) -> Dict[str, Any]:
    """Load configuration from file or return empty dict if not found."""
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log_event("INFO", "CONFIG", f"Loaded config from {path.name}")
                return config
        except Exception as e:
            log_event("ERROR", "CONFIG", f"Failed to load config: {e}")
    else:
        log_event("WARN", "CONFIG", "No config file found, using defaults.")
    return {}

def save_config(config: Dict[str, Any], path: Path = CONFIG_FILE):
    """Save configuration to file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        log_event("INFO", "CONFIG", f"Configuration saved to {path.name}")
    except Exception as e:
        log_event("ERROR", "CONFIG", f"Failed to save config: {e}")

def backup_config(source: Path = CONFIG_FILE, backup_dir: Path = LOG_PATH):
    """Create a timestamped backup of the config file."""
    if source.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"config_backup_{timestamp}.json"
        try:
            shutil.copy(source, backup_path)
            log_event("INFO", "CONFIG", f"Backup saved to {backup_path.name}")
        except Exception as e:
            log_event("ERROR", "CONFIG", f"Backup failed: {e}")
    else:
        log_event("WARN", "CONFIG", "No config file to back up.")


# ==============================================================================
# MODULE 5: Health Monitoring
# ==============================================================================

def get_system_health() -> Dict[str, Any]:
    """Collect real-time system metrics using psutil."""
    if not psutil:
        log_event("WARN", "HEALTH", "psutil not available, skipping metrics.")
        return {}

    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        net = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        metrics = {
            "cpu": cpu,
            "memory": mem,
            "disk": disk,
            "network_traffic": net,
            "timestamp": datetime.datetime.now().isoformat()
        }
        return metrics
    except Exception as e:
        log_event("ERROR", "HEALTH", f"Failed to collect metrics: {e}")
        return {}

def monitor_health():
    """Log system health periodically and update SYSTEM_HEALTH."""
    metrics = get_system_health()
    if metrics:
        log_event("INFO", "HEALTH", f"CPU {metrics['cpu']}% | MEM {metrics['memory']}% | DISK {metrics['disk']}%")
        for key in ['cpu', 'memory', 'disk', 'network_traffic']:
            SYSTEM_HEALTH[key] = metrics[key]
        SYSTEM_HEALTH["last_check"] = metrics["timestamp"]


# ==============================================================================
# MODULE 6: Enhanced Monolith System
# ==============================================================================

def execute_monolith(monolith: str) -> Tuple[str, float]:
    """Simulate execution of a monolith model with a decision and confidence."""
    if monolith not in MONOLITHS:
        log_event("WARN", "MONOLITH", f"Unknown monolith: {monolith}")
        return ("PENDING", 0.0)

    data = MONOLITHS[monolith]
    model_name = data.get("model", "unknown")
    role = data.get("specialization", "general")

    log_event("INFO", monolith, f"Executing model {model_name} ({role})")
    time.sleep(random.uniform(0.2, 0.5))

    decision = random.choice(["APPROVE", "DENY", "PENDING"])
    confidence = round(random.uniform(0.6, 0.99), 2)
    log_event("INFO", monolith, f"Decision: {decision} | Confidence: {confidence}")
    return decision, confidence


# ==============================================================================
# MODULE 7: Consensus Engine
# ==============================================================================

def calculate_consensus(votes: Dict[str, Tuple[str, float]]) -> str:
    """Determine consensus outcome using confidence-weighted logic."""
    tally = {"APPROVE": 0.0, "DENY": 0.0, "PENDING": 0.0}

    for monolith, (decision, confidence) in votes.items():
        if decision in tally:
            tally[decision] += confidence

    log_event("DEBUG", "CONSENSUS", f"Weighted vote tally: {tally}")

    outcome = max(tally.items(), key=lambda item: item[1])[0]

    if outcome == "PENDING":
        return "DEADLOCK"
    elif abs(tally["APPROVE"] - tally["DENY"]) < 0.05:
        log_event("WARN", "CONSENSUS", "Close result, applying tie-breaker")
        return "REJECTED"  # default fallback
    else:
        return "APPROVED" if outcome == "APPROVE" else "REJECTED"


# ==============================================================================
# MODULE 8: Voting Orchestrator
# ==============================================================================

def orchestrate_votes(monoliths: List[str]) -> str:
    """Execute all monoliths in parallel and determine the consensus."""
    results = {}
    threads = []
    log_event("DEBUG", "VOTING", f"Starting vote execution for {len(monoliths)} monoliths")

    def worker(name):
        try:
            results[name] = execute_monolith(name)
        except Exception as e:
            log_event("ERROR", name, f"Execution failed: {e}")
            results[name] = ("PENDING", 0.0)

    for m in monoliths:
        t = threading.Thread(target=worker, args=(m,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    consensus_result = calculate_consensus(results)
    log_event("SYSTEM", "VOTING", f"Final verdict: {consensus_result}")
    return consensus_result


# ==============================================================================
# MODULE 9: User Interface System
# ==============================================================================

def safe_addstr(window, y: int, x: int, text: str, attr: Optional[int] = 0):
    """Safely add a string to the curses window without overflow."""
    max_y, max_x = window.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x:
        trimmed = text[: max_x - x - 1]
        try:
            window.addstr(y, x, trimmed, attr)
        except Exception:
            pass

def render_rationalis_screen(stdscr, theme: str, height: int, width: int):
    """Draw the Rationalis monolith specialized screen."""
    for i in range(1, height - 3):
        blank_line = " " * (width - 2)
        safe_addstr(stdscr, i, 1, blank_line)

    if not MONOLITH_DATA["RATIONALIS"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["RATIONALIS"]["last_updated"]).total_seconds() > 60:
        update_rationalis_data()

    if theme == "military":
        header = "RATIONALIS ANALYTICAL OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "MECHANICUS RATIONALIS LOGIC ENGINE"
    elif theme == "tars":
        header = "RATIONALIS.CORE.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH STRATEGIC ANALYSIS"
    elif theme == "eva":
        header = "MAGI CASPER-3 - CORE LOGIC NODE"
    else:
        header = "RATIONALIS LOGICAL INTERFACE"

    safe_addstr(stdscr, 1, width // 2 - len(header) // 2, header,
                curses.A_BOLD | curses.color_pair(MONOLITHS["Rationalis"]["color"]))

    # Draw efficiency rating
    efficiency = MONOLITH_DATA["RATIONALIS"]["efficiency_rating"] * 100
    efficiency_color = 2 if efficiency > 90 else 3 if efficiency > 75 else 1

    if theme == "military":
        rating_text = f"SYSTEM EFFICIENCY: {efficiency:.1f}%"
    elif theme == "wh40k":
        rating_text = f"MACHINE SPIRIT POTENCY: {efficiency:.1f}%"
    elif theme == "tars":
        rating_text = f"EFFICIENCY.RATING={efficiency:.1f}%"
    elif theme == "helldivers":
        rating_text = f"LIBERTY EFFICIENCY: {efficiency:.1f}%"
    elif theme == "eva":
        rating_text = f"CASPER LOGIC STABILITY: {efficiency:.1f}%"
    else:
        rating_text = f"LOGICAL EFFICIENCY: {efficiency:.1f}%"

    safe_addstr(stdscr, 3, width // 2 - len(rating_text) // 2, rating_text,
                curses.A_BOLD | curses.color_pair(efficiency_color))

    # System logs
    y_pos = 5
    if theme == "military":
        section_header = "[ SYSTEM LOG ENTRIES ]"
    elif theme == "wh40k":
        section_header = "[ NOOSPHERE TRANSMISSIONS ]"
    elif theme == "tars":
        section_header = "[ SYSTEM.LOGS ]"
    elif theme == "helldivers":
        section_header = "[ MISSION INTELLIGENCE ]"
    elif theme == "eva":
        section_header = "[ ACCESS LOG - NODE CASPER-3 ]"
    else:
        section_header = "[ SYSTEM LOGS ]"

    safe_addstr(stdscr, y_pos, width // 2 - len(section_header) // 2, section_header, curses.A_BOLD)
    y_pos += 1

    logs = MONOLITH_DATA["RATIONALIS"]["system_logs"]
    for idx, log in enumerate(logs):
        if y_pos + idx < height - 12:
            level_color = 2 if log["level"] == "INFO" else 3 if log["level"] == "WARNING" else 1
            log_text = f"[{log['timestamp']}] {log['level']}: {log['message']}"
            safe_addstr(stdscr, y_pos + idx, 2, log_text, curses.color_pair(level_color))

def render_aeternum_screen(stdscr, theme, height, width):
    for i in range(1, height - 3):
        blank_line = " " * (width - 2)
        safe_addstr(stdscr, i, 1, blank_line)

    if not MONOLITH_DATA["AETERNUM"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["AETERNUM"]["last_updated"]).total_seconds() > 60:
        update_aeternum_data()

    if theme == "military":
        header = "AETERNUM FINANCIAL OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "ADMINISTRATUM AETERNUM"
    elif theme == "tars":
        header = "AETERNUM.FINANCE.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH ECONOMIC COMMAND"
    elif theme == "eva":
        header = "MAGI BALTHASAR-2 - ANALYTICAL CORE"
    else:
        header = "AETERNUM FINANCIAL INTERFACE"

    safe_addstr(stdscr, 1, width // 2 - len(header) // 2, header,
                curses.A_BOLD | curses.color_pair(MONOLITHS["Aeternum"]["color"]))

    y_pos = 3
    if theme == "military":
        section_header = "[ MARKET INDICES ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIAL TREASURIUM ]"
    elif theme == "tars":
        section_header = "[ MARKET.MONITOR ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRATIC ECONOMIC INDICES ]"
    elif theme == "eva":
        section_header = "[ FINANCIAL TRACE - NODE BALTHASAR-2 ]"
    else:
        section_header = "[ MARKET INDICES ]"

    safe_addstr(stdscr, y_pos, width // 2 - len(section_header) // 2, section_header, curses.A_BOLD)
    y_pos += 1

    indices = MONOLITH_DATA["AETERNUM"]["market_indices"]
    col1_x = 4
    col2_x = width // 2 + 4

    idx = 0
    for name, data in indices.items():
        if y_pos + idx // 2 < height - 5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["trend"] == "up" else 1
            value_str = f"{data['value']:,.2f}"
            change_str = f"{data['change']:+.2f}%"
            market_text = f"{name}: {value_str} ({change_str})"
            safe_addstr(stdscr, y_pos + idx // 2, x_pos, market_text, curses.color_pair(trend_color))
            idx += 1

    y_pos += (idx + 1) // 2 + 1

def render_bellator_screen(stdscr, theme: str, height: int, width: int):
    for i in range(1, height - 3):
        blank_line = " " * (width - 2)
        safe_addstr(stdscr, i, 1, blank_line)

    if not MONOLITH_DATA["BELLATOR"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["BELLATOR"]["last_updated"]).total_seconds() > 60:
        update_bellator_data()

    if theme == "military":
        header = "BELLATOR COMBAT OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "MUNITORUM BELLATOR COMMAND"
    elif theme == "tars":
        header = "BELLATOR.STRATEGY.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH STRATEGIC DEFENSE"
    elif theme == "eva":
        header = "MAGI MELCHIOR-1 - STRATEGIC UNIT"
    else:
        header = "BELLATOR STRATEGIC INTERFACE"

    safe_addstr(stdscr, 1, width // 2 - len(header) // 2, header,
                curses.A_BOLD | curses.color_pair(MONOLITHS["Bellator"]["color"]))

    # Efficiency metric
    efficiency = MONOLITH_DATA["BELLATOR"]["defcon_level"]
    efficiency_color = 2 if efficiency <= 2 else 3 if efficiency <= 4 else 1

    if theme == "military":
        rating_text = f"DEFCON LEVEL: {efficiency}"
    elif theme == "wh40k":
        rating_text = f"CONFLICT PURITY INDEX: {6-efficiency}/5"
    elif theme == "tars":
        rating_text = f"DEFCON.LEVEL={efficiency}"
    elif theme == "helldivers":
        rating_text = f"THREAT READINESS LEVEL: {efficiency}"
    elif theme == "eva":
        rating_text = f"MELCHIOR CONFLICT READINESS: {efficiency}/5"
    else:
        rating_text = f"TACTICAL READINESS: {efficiency}"

    safe_addstr(stdscr, 3, width // 2 - len(rating_text) // 2, rating_text,
                curses.A_BOLD | curses.color_pair(efficiency_color))

    # Threat alerts log
    y_pos = 5
    if theme == "military":
        section_header = "[ TACTICAL INTELLIGENCE REPORTS ]"
    elif theme == "wh40k":
        section_header = "[ ASTROPATHIC ALERTS ]"
    elif theme == "tars":
        section_header = "[ ALERT.LOG ]"
    elif theme == "helldivers":
        section_header = "[ ENEMY MOVEMENT REPORTS ]"
    elif theme == "eva":
        section_header = "[ TACTICAL READOUT - NODE MELCHIOR-1 ]"
    else:
        section_header = "[ THREAT REPORTS ]"

    safe_addstr(stdscr, y_pos, width // 2 - len(section_header) // 2, section_header, curses.A_BOLD)
    y_pos += 1

    alerts = MONOLITH_DATA["BELLATOR"]["threat_alerts"]
    for idx, alert in enumerate(alerts):
        if y_pos + idx < height - 12:
            color = 1 if alert["priority"] == "HIGH" else 3
            log_text = f"[{alert['timestamp']}] {alert['type']}: {alert['description']}"
            safe_addstr(stdscr, y_pos + idx, 2, log_text, curses.color_pair(color))


# ==============================================================================
# MODULE 10: Console Mode
# ==============================================================================

import readline  # Optional, for command autocomplete/history

command_history = deque(maxlen=CONFIG["command_history_size"])

# Command registry: command name → function
COMMANDS = {}

def command(name):
    """Decorator to register a console command."""
    def decorator(func):
        COMMANDS[name] = func
        return func
    return decorator

@command("vote")
def cmd_vote(args):
    result = orchestrate_votes(list(MONOLITHS.keys()))
    print(f"Vote result: {result}")

@command("status")
def cmd_status(args):
    cpu = SYSTEM_HEALTH.get("cpu", "N/A")
    mem = SYSTEM_HEALTH.get("memory", "N/A")
    print(f"System health: CPU {cpu}%, MEM {mem}%")

@command("export")
def cmd_export(args):
    if not args:
        print("Specify format: json, csv, txt, logs, all")
        return
    fmt = args[0].lower()
    if fmt == "json":
        export_decision_history_json()
    elif fmt == "csv":
        export_decision_history_csv()
    elif fmt == "txt":
        export_decision_history_txt()
    elif fmt == "logs":
        export_system_logs_txt()
    elif fmt == "all":
        export_all()
    else:
        print(f"Unknown export format: {fmt}")

@command("reload")
def cmd_reload(args):
    print("Reloading configurations... (not implemented)")

@command("help")
def cmd_help(args):
    print("Available commands:")
    for cmd_name in sorted(COMMANDS.keys()):
        print(f"  - {cmd_name}")

def setup_readline():
    try:
        readline.parse_and_bind('tab: complete')
        readline.set_completer(lambda text, state: [c for c in COMMANDS.keys() if c.startswith(text)][state])
    except Exception:
        pass

def console_loop():
    setup_readline()
    print("Entering console mode. Type 'help' for commands.")
    while True:
        try:
            command_line = input("> ").strip()
            if not command_line:
                continue
            if command_line.lower() in ("exit", "quit"):
                print("Exiting console.")
                break

            parts = command_line.split()
            cmd_name, *args = parts
            cmd_name = cmd_name.lower()

            command_history.append(command_line)

            if cmd_name in COMMANDS:
                COMMANDS[cmd_name](args)
            else:
                print(f"Unknown command: {cmd_name}. Type 'help' for a list of commands.")
        except KeyboardInterrupt:
            print("\nExiting console.")
            break
        except Exception as e:
            print(f"Error: {e}")


# ==============================================================================
# MODULE 11: Export & I/O Operations
# ==============================================================================

def get_timestamped_path(basename: str, ext: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return BASE_PATH / f"{basename}_{timestamp}.{ext}"

def export_decision_history_json(path: Path = None):
    if path is None:
        path = get_timestamped_path("decision_history", "json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(decision_history), f, indent=2)
        log_event("INFO", "EXPORT", f"Decision history exported to {path}")
    except Exception as e:
        log_event("ERROR", "EXPORT", f"Failed to export decision history: {e}")

def export_decision_history_csv(path: Path = None):
    if path is None:
        path = get_timestamped_path("decision_history", "csv")
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "monolith", "decision", "confidence"])
            for entry in decision_history:
                writer.writerow([
                    entry.get("timestamp", ""),
                    entry.get("monolith", ""),
                    entry.get("decision", ""),
                    entry.get("confidence", "")
                ])
        log_event("INFO", "EXPORT", f"Decision history exported to {path}")
    except Exception as e:
        log_event("ERROR", "EXPORT", f"Failed to export decision history CSV: {e}")

def export_decision_history_txt(path: Path = None):
    if path is None:
        path = get_timestamped_path("decision_history", "txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            for entry in decision_history:
                f.write(f"{entry}\\n")
        log_event("INFO", "EXPORT", f"Decision history exported to {path}")
    except Exception as e:
        log_event("ERROR", "EXPORT", f"Failed to export decision history TXT: {e}")

def export_system_logs_txt(path: Path = None):
    if path is None:
        path = get_timestamped_path("system_logs", "txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            for log in log_entries:
                f.write(f\"{log}\\n\")
        log_event("INFO", "EXPORT", f"System logs exported to {path}")
    except Exception as e:
        log_event("ERROR", "EXPORT", f"Failed to export system logs TXT: {e}")

def export_all():
    export_decision_history_json()
    export_decision_history_csv()
    export_decision_history_txt()
    export_system_logs_txt()
    log_event("INFO", "EXPORT", "All export formats completed.")


# ==============================================================================
# MODULE 12: Demo & Testing Functions
# ==============================================================================

def run_vote_demo(iterations: int = 10):
    print(f"Running vote demo for {iterations} iterations...")
    results_summary = {"APPROVED": 0, "REJECTED": 0, "DEADLOCK": 0}

    for i in range(iterations):
        votes = {}
        for monolith in MONOLITHS:
            decision = random.choice(["APPROVE", "DENY", "PENDING"])
            confidence = round(random.uniform(0.6, 0.99), 2)
            votes[monolith] = (decision, confidence)
        result = calculate_consensus(votes)
        results_summary[result] += 1
        print(f"Iteration {i+1}: Votes={votes}, Result={result}")

    print("Demo complete. Summary:")
    for outcome, count in results_summary.items():
        print(f"{outcome}: {count}")

def run_stress_test(duration_seconds: int = 30):
    print(f"Starting stress test for {duration_seconds} seconds...")
    start_time = time.time()
    count = 0
    while time.time() - start_time < duration_seconds:
        orchestrate_votes(list(MONOLITHS.keys()))
        count += 1
    print(f"Stress test complete: {count} iterations run.")


# ==============================================================================
# MODULE 13: Main Application Loop
# ==============================================================================

def main_loop(stdscr):
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)

    current_view = "main"
    query_text = ""
    last_refresh = 0
    refresh_interval = CONFIG.get("refresh_interval", 5)

    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        # Handle input
        try:
            ch = stdscr.getch()
        except KeyboardInterrupt:
            break

        if ch != -1:
            if ch in (ord('q'), 27):  # q or ESC to quit
                break
            elif ch == ord('1'):
                current_view = "rationalis"
            elif ch == ord('2'):
                current_view = "aeternum"
            elif ch == ord('3'):
                current_view = "bellator"
            elif ch == ord('7'):
                current_view = "history"
            elif ch == ord('s'):
                # Cycle theme (implement theme cycling elsewhere)
                cycle_theme()
            elif ch == ord('c'):
                # Open console mode (implement console launcher)
                launch_console_mode()

        # Draw the current view
        if current_view == "main":
            render_main_screen(stdscr, CONFIG["theme"], height, width)
        elif current_view == "rationalis":
            render_rationalis_screen(stdscr, CONFIG["theme"], height, width)
        elif current_view == "aeternum":
            render_aeternum_screen(stdscr, CONFIG["theme"], height, width)
        elif current_view == "bellator":
            render_bellator_screen(stdscr, CONFIG["theme"], height, width)
        elif current_view == "history":
            render_history_screen(stdscr, height, width)

        stdscr.refresh()

        # Refresh at intervals
        now = time.time()
        if now - last_refresh > refresh_interval:
            refresh_data()
            last_refresh = now

        time.sleep(0.05)  # Slight delay to reduce CPU usage

def refresh_data():
    # Trigger data updates for all monoliths or system info
    update_rationalis_data()
    update_aeternum_data()
    update_bellator_data()
    monitor_health()

def cycle_theme():
    current_index = THEMES.index(CONFIG["theme"]) if CONFIG["theme"] in THEMES else 0
    CONFIG["theme"] = THEMES[(current_index + 1) % len(THEMES)]
    log_event("INFO", "UI", f"Theme changed to {CONFIG['theme']}")

def launch_console_mode():
    curses.endwin()
    console_loop()
    # After console exit, reinitialize curses
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()


# ==============================================================================
# MODULE 14: Main Entry Point
# ==============================================================================

import argparse
import signal
import sys

def signal_handler(sig, frame):
    print("\nInterrupt received, exiting gracefully...")
    curses.endwin()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    # Load config
    config = load_config()
    CONFIG.update(config)

    # Run boot animation
    boot_system()

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="CONSENSUS War Room Launcher")
    parser.add_argument("--console", action="store_true", help="Run in console mode")
    args = parser.parse_args()

    if args.console:
        print("Starting in console mode...")
        console_loop()
    else:
        print("Starting in GUI mode...")
        curses.wrapper(main_loop)

if __name__ == "__main__":
    main()
