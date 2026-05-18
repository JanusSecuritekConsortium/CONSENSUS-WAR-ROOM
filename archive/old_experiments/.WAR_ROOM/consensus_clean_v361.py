#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.6.1)
Complete single-file implementation with all features.
"""

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
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional

# === SYSTEM ASCII ART ===
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

CONSENSUS_LOGO = """
╔════════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                          v3.6.1      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# === CONFIGURATION ===
VERSION = "3.6.1"
BUILD_DATE = "2025-05-19"
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
CONFIG_PATH = ARBITER_DIR / "config.json"

CONFIG = {
    "theme": "military",
    "current_view": "main",
    "system_mode": "READY",
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9
    },
    "health_monitoring": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3
    }
}

MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "prompt": "You are RATIONALIS, logic engine of the Tribunal. Analyze the query logically and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "prompt": "You are AETERNUM, market historian and foresight node. Analyze patterns and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "prompt": "You are BELLATOR, tactical risk assessor and security analyst. Evaluate risks and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    }
}

# Box drawing characters for themes
BOX_CHARS = {
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮"
    },
    "eva": {
        "tl": "▛", "tr": "▜", "bl": "▙", "br": "▟",
        "h": "▀", "v": "▌"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃"
    }
}

# === STATE ===
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
VOTES = {}
SYSTEM_HEALTH = {
    "cpu": 0.0,
    "memory": 0.0,
    "uptime": time.time(),
    "tts_status": "unknown",
    "api_status": "unknown",
    "last_health_check": 0
}

# === UTILITIES ===
def log(msg, level="INFO"):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{t}] [{level}] {msg}"
    log_entries.append(formatted_msg)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{datetime.datetime.now():%Y%m%d}.log", "a") as f:
            f.write(f"{formatted_msg}\n")
    except: 
        pass

def add_notification(message: str, level: str = "info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now()
    })

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                CONFIG.update(json.load(f))
        except Exception as e:
            log(f"Failed to load config: {e}", "ERROR")

def save_config():
    try:
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        log(f"Failed to save config: {e}", "ERROR")

def post_to_model(monolith, query):
    cfg = MODEL_CONFIG[monolith]
    provider = CONFIG["llm_provider"]
    prompt = f"{cfg['prompt']}\n\nQUERY: {query}\n\nVOTE:"
    api = {
        "ollama": "http://localhost:11434/api/generate",
        "lmstudio": "http://localhost:1234/v1/completions"
    }[provider]

    payload = {"model": cfg["model"], "prompt": prompt, "stream": False, "temperature": 0.5, "max_tokens": 512}
    try:
        r = requests.post(api, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("response") or data.get("choices", [{}])[0].get("text", "")
        return f"Error: {r.status_code}"
    except Exception as e:
        return f"Exception: {e}"

def calculate_consensus(votes: Dict[str, str]) -> Optional[str]:
    """Calculate consensus based on votes"""
    approve_count = sum(1 for vote in votes.values() if "APPROVE" in vote.upper())
    deny_count = sum(1 for vote in votes.values() if "DENY" in vote.upper())
    
    if approve_count >= 2:
        return "APPROVE"
    elif deny_count >= 2:
        return "DENY"
    return "DEADLOCK"

# === MONOLITH LOGIC ===
class Monolith:
    def __init__(self, name):
        self.name = name
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        VOTE_DIR.mkdir(parents=True, exist_ok=True)

    def vote(self, query):
        log(f"[{self.name}] Voting on: {query}")
        result = post_to_model(self.name, query).strip()
        VOTES[self.name] = result
        self.write_vote(result)
        return result

    def write_vote(self, result):
        data = {"monolith": self.name, "vote": result, "timestamp": datetime.datetime.now().isoformat()}
        with open(self.vote_file, "w") as f:
            json.dump(data, f, indent=2)

# === BOOT SEQUENCE ===
def boot():
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.0)
    print(CONSENSUS_LOGO)
    time.sleep(0.5)
    print(f"Booting CONSENSUS SYSTEM v{VERSION} — Build {BUILD_DATE}\n")
    steps = ["Loading memory cores", "Validating vote ports", "Activating monoliths"]
    for s in steps:
        print(f"[✓] {s}")
        time.sleep(0.4)
    print("\n▛ SYSTEM READY ▟ — PRESS ENTER TO CONTINUE")
    input()

# === ARBITER VERDICT + TTS ===
def summarize_consensus(verdict: str):
    typed_text = f"FINAL VERDICT: {verdict.upper()}"
    for c in typed_text:
        print(c, end='', flush=True)
        time.sleep(0.04)
    print()
    
    if CONFIG.get("tts", {}).get("enabled"):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            engine.setProperty('rate', CONFIG["tts"].get("voice_rate", 150))
            engine.setProperty('volume', CONFIG["tts"].get("voice_volume", 0.9))
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            log(f"[TTS] Announced verdict: {verdict}")
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3", "WARNING")
        except Exception as e:
            log(f"[TTS Error] {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. Console Mode (Direct voting)")
        print("2. Exit")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Console mode - simplified for testing
            while True:
                query = input("\n>> ENTER QUERY FOR VOTE (or 'quit' to exit):\n> ")
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                    
                log(f"COMMAND: console_vote -> {query}")
                VOTES.clear()
                
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                verdict = calculate_consensus(VOTES)
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                print(f"\nVotes saved to {VOTE_DIR}")
        
        else:
            print("Exiting CONSENSUS System...")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()
        y = start_y + i
        
        # Timestamp
        timestamp = decision["timestamp"].strftime("%m/%d %H:%M")
        safe_addstr(stdscr, y, 3, timestamp, curses.color_pair(7))
        
        # Verdict with color
        verdict = decision["verdict"]
        verdict_color = 2 if verdict == "APPROVE" else 1 if verdict == "DENY" else 3
        safe_addstr(stdscr, y, 15, verdict, curses.A_BOLD | curses.color_pair(verdict_color))
        
        # Query (truncated)
        query = decision["query"][:35] + "..." if len(decision["query"]) > 35 else decision["query"]
        safe_addstr(stdscr, y, 25, query, curses.color_pair(7))
        
        # Individual votes summary
        votes_text = ""
        if decision.get("individual_votes"):
            vote_summary = []
            for name, vote in decision["individual_votes"].items():
                vote_short = "A" if "APPROVE" in vote.upper() else "D" if "DENY" in vote.upper() else "?"
                vote_summary.append(f"{name[0]}{vote_short}")
            votes_text = " ".join(vote_summary)
        safe_addstr(stdscr, y, width - 20, votes_text, curses.color_pair(4))
        
        # Session ID (last 6 chars)
        session_id = decision.get("session_id", "")[-6:] if decision.get("session_id") else "N/A"
        safe_addstr(stdscr, y, width - 8, session_id, curses.color_pair(5))
    
    # Footer stats
    total_decisions = len(decision_history)
    approve_count = sum(1 for d in decision_history if d["verdict"] == "APPROVE")
    deny_count = sum(1 for d in decision_history if d["verdict"] == "DENY")
    deadlock_count = sum(1 for d in decision_history if d["verdict"] == "DEADLOCK")
    
    stats_y = height - 4
    stats_text = f"Total: {total_decisions} | Approved: {approve_count} | Denied: {deny_count} | Deadlocks: {deadlock_count}"
    safe_addstr(stdscr, stats_y, (width - len(stats_text)) // 2, stats_text, curses.color_pair(7))
    
    # Controls
    controls = "M: Main View | Q: Quit | D: Forensic View"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_config_diagnostics_screen(stdscr, theme: str):
    """Render configuration diagnostics screen (Key 9)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS CONFIGURATION DIAGNOSTICS"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Draw border
    draw_box(stdscr, 3, 1, height - 7, width - 2, theme)
    
    y_pos = 5
    
    # System Information
    safe_addstr(stdscr, y_pos, 3, "SYSTEM INFORMATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    sys_info = [
        ("Version", VERSION),
        ("Build Date", BUILD_DATE),
        ("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("System Root", str(SYSTEM_ROOT)),
        ("Config Path", str(CONFIG_PATH)),
        ("Current Theme", CONFIG.get("theme", "unknown")),
        ("Current View", CONFIG.get("current_view", "unknown"))
    ]
    
    for label, value in sys_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 25, str(value), curses.color_pair(2))
        y_pos += 1
    
    y_pos += 1
    
    # LLM Configuration
    safe_addstr(stdscr, y_pos, 3, "LLM CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    safe_addstr(stdscr, y_pos, 5, f"Provider: {CONFIG.get('llm_provider', 'unknown')}", curses.color_pair(2))
    y_pos += 1
    safe_addstr(stdscr, y_pos, 5, f"Vote Timeout: {CONFIG.get('vote_timeout', 'unknown')}s", curses.color_pair(2))
    y_pos += 1
    
    # Model Status
    for name, config in MODEL_CONFIG.items():
        model_name = config.get("model", "unknown")
        status = config.get("status", "unknown")
        status_color = 2 if status == "ready" else 3 if status == "not_loaded" else 1
        
        safe_addstr(stdscr, y_pos, 5, f"{name}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 18, model_name, curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 45, f"[{status.upper()}]", curses.color_pair(status_color))
        y_pos += 1
    
    y_pos += 1
    
    # TTS Configuration
    safe_addstr(stdscr, y_pos, 3, "TTS CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    tts_config = CONFIG.get("tts", {})
    tts_info = [
        ("Enabled", tts_config.get("enabled", "unknown")),
        ("Engine", tts_config.get("engine", "unknown")),
        ("Voice Rate", tts_config.get("voice_rate", "unknown")),
        ("Voice Volume", tts_config.get("voice_volume", "unknown")),
        ("Status", SYSTEM_HEALTH.get("tts_status", "unknown"))
    ]
    
    for label, value in tts_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        color = 2 if str(value).lower() in ["true", "operational"] else 1 if str(value).lower() in ["false", "unavailable"] else 7
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    y_pos += 1
    
    # Health Monitoring
    safe_addstr(stdscr, y_pos, 3, "HEALTH MONITORING:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    health_info = [
        ("CPU Usage", f"{SYSTEM_HEALTH.get('cpu', 0):.1f}%"),
        ("Memory Usage", f"{SYSTEM_HEALTH.get('memory', 0):.1f}%"),
        ("API Status", SYSTEM_HEALTH.get("api_status", "unknown")),
        ("Last Health Check", datetime.datetime.fromtimestamp(SYSTEM_HEALTH.get("last_health_check", 0)).strftime("%H:%M:%S"))
    ]
    
    for label, value in health_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        
        # Color based on value
        if "%" in str(value):
            numeric_value = float(value.replace("%", ""))
            color = 2 if numeric_value < 70 else 3 if numeric_value < 90 else 1
        elif str(value).lower() == "operational":
            color = 2
        elif str(value).lower() in ["error", "unreachable", "unavailable"]:
            color = 1
        else:
            color = 7
            
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    # Controls
    controls = "M: Main View | Q: Quit | R: Refresh Diagnostics"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_decision_forensics_screen(stdscr, theme: str, selected_index: int = 0):
    """Render decision forensics screen (Key D)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS DECISION FORENSIC INSPECTOR"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions available", curses.color_pair(3))
        controls = "M: Main View | Q: Quit"
        safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
        render_status_bar(stdscr, theme)
        return
    
    # Get selected decision
    decisions_list = list(decision_history)
    selected_index = max(0, min(selected_index, len(decisions_list) - 1))
    decision = decisions_list[selected_index]
    
    # Decision list (left panel)
    list_width = width // 3
    draw_box(stdscr, 3, 1, height - 7, list_width, theme)
    safe_addstr(stdscr, 3, 3, "DECISION LIST", curses.A_BOLD)
    
    # Show decisions with selection
    list_start_y = 5
    max_list_items = height - 10
    
    for i, dec in enumerate(decisions_list[-max_list_items:]):
        y = list_start_y + i
        if y >= height - 5:
            break
            
        # Highlight selected item
        attr = curses.A_REVERSE if i == selected_index else 0
        
        timestamp = dec["timestamp"].strftime("%m/%d %H:%M")
        verdict = dec["verdict"][:3]
        verdict_color = 2 if dec["verdict"] == "APPROVE" else 1 if dec["verdict"] == "DENY" else 3
        
        safe_addstr(stdscr, y, 3, f"{timestamp} {verdict}", curses.color_pair(verdict_color) | attr)
    
    # Decision details (right panel)
    details_x = list_width + 2
    details_width = width - list_width - 3
    draw_box(stdscr, 3, details_x, height - 7, details_width, theme)
    safe_addstr(stdscr, 3, details_x + 2, "DECISION DETAILS", curses.A_BOLD)
    
    # Display decision details
    detail_y = 5
    
    # Basic info
    safe_addstr(stdscr, detail_y, details_x + 2, "QUERY:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    # Word wrap query
    query = decision["query"]
    max_width = details_width - 6
    query_lines = [query[i:i+max_width] for i in range(0, len(query), max_width)]
    for line in query_lines[:3]:  # Max 3 lines
        safe_addstr(stdscr, detail_y, details_x + 4, line, curses.color_pair(7))
        detail_y += 1
    
    detail_y += 1
    
    # Verdict and timestamp
    safe_addstr(stdscr, detail_y, details_x + 2, "VERDICT:", curses.A_BOLD | curses.color_pair(3))
    verdict_color = 2 if decision["verdict"] == "APPROVE" else 1 if decision["verdict"] == "DENY" else 3
    safe_addstr(stdscr, detail_y, details_x + 12, decision["verdict"], curses.A_BOLD | curses.color_pair(verdict_color))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "TIMESTAMP:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 14, decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), curses.color_pair(7))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "SESSION ID:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 15, decision.get("session_id", "N/A"), curses.color_pair(7))
    detail_y += 2
    
    # Individual votes
    safe_addstr(stdscr, detail_y, details_x + 2, "INDIVIDUAL VOTES:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    if decision.get("individual_votes"):
        for name, vote in decision["individual_votes"].items():
            safe_addstr(stdscr, detail_y, details_x + 2, f"{name}:", curses.A_BOLD | curses.color_pair(4))
            
            # Truncate long votes
            vote_display = vote[:max_width-15] + "..." if len(vote) > max_width-15 else vote
            safe_addstr(stdscr, detail_y, details_x + 15, vote_display, curses.color_pair(7))
            detail_y += 1
    else:
        safe_addstr(stdscr, detail_y, details_x + 4, "No individual votes recorded", curses.color_pair(3))
        detail_y += 1
    
    detail_y += 1
    
    # System state
    if decision.get("system_state"):
        safe_addstr(stdscr, detail_y, details_x + 2, "SYSTEM STATE:", curses.A_BOLD | curses.color_pair(3))
        detail_y += 1
        
        state = decision["system_state"]
        safe_addstr(stdscr, detail_y, details_x + 4, f"Theme: {state.get('theme', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Mode: {state.get('mode', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Version: {state.get('version', 'N/A')}", curses.color_pair(7))
        detail_y += 1
    
    # Navigation info
    nav_info = f"Decision {selected_index + 1} of {len(decisions_list)}"
    safe_addstr(stdscr, height - 5, (width - len(nav_info)) // 2, nav_info, curses.color_pair(5))
    
    # Controls
    controls = "↑↓: Navigate | M: Main View | 7: History | Q: Quit"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

# === EXPORT FUNCTIONALITY ===
def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"decisions_{timestamp}.json"
        export_data = {
            "export_info": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "total_decisions": len(decision_history)
            },
            "decisions": [
                {
                    **decision,
                    "timestamp": decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"decisions_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Query", "Verdict", "Session_ID", "Individual_Votes", "Reasoning"])
            
            for decision in decision_history:
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                votes_str = "; ".join([f"{k}: {v}" for k, v in decision.get("individual_votes", {}).items()])
                writer.writerow([
                    timestamp,
                    decision["query"],
                    decision["verdict"],
                    decision.get("session_id", ""),
                    votes_str,
                    decision.get("reasoning", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"decisions_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Version: {VERSION}\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, decision in enumerate(decision_history, 1):
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                f.write(f"DECISION #{i}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Verdict: {decision['verdict']}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                if decision.get("individual_votes"):
                    f.write("Individual Votes:\n")
                    for name, vote in decision["individual_votes"].items():
                        f.write(f"  {name}: {vote}\n")
                
                if decision.get("reasoning"):
                    f.write(f"Reasoning: {decision['reasoning']}\n")
                
                f.write("-" * 80 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    return str(filename)

# === CONSOLE MODE ===
def run_console_mode():
    """Run console mode for direct voting and commands"""
    print("\n" + "="*80)
    print("CONSENSUS SYSTEM - CONSOLE MODE")
    print("="*80)
    print("Commands: vote <query> | export <format> | reload <monolith> | status | quit")
    
    while True:
        try:
            command_input = input("\n>> ").strip()
            
            if not command_input:
                continue
                
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ['quit', 'exit', 'q']:
                break
            
            elif command == "vote":
                if not args:
                    print("Usage: vote <your question>")
                    continue
                    
                query = args
                log(f"COMMAND: console_vote -> {query}")
                add_notification(f"Console vote: {query}", "info")
                
                # Clear previous votes
                VOTES.clear()
                
                # Create monoliths and vote
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                # Calculate consensus
                verdict = calculate_consensus(VOTES)
                
                # Generate reasoning summary
                reasoning_parts = []
                for name, vote in VOTES.items():
                    reasoning_parts.append(f"{name}: {vote}")
                reasoning = "; ".join(reasoning_parts)
                
                # Display verdict
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                
                # Log decision
                add_decision_to_history(query, verdict, reasoning, "console_vote")
                
                print(f"\nVotes saved to {VOTE_DIR}")
                print("Full trace available in logs.")
            
            elif command == "export":
                if not args or args.lower() not in ["json", "csv", "txt"]:
                    print("Usage: export <json|csv|txt>")
                    continue
                
                try:
                    filename = export_decisions(args.lower())
                    print(f"Decisions exported to: {filename}")
                    log(f"Exported decisions to {filename}")
                except Exception as e:
                    print(f"Export failed: {e}")
                    log(f"Export failed: {e}", "ERROR")
            
            elif command == "reload":
                if not args or args.upper() not in MODEL_CONFIG:
                    print("Usage: reload <RATIONALIS|AETERNUM|BELLATOR>")
                    continue
                
                monolith_name = args.upper()
                monolith = Monolith(monolith_name)
                status = monolith.reload_model()
                print(f"{monolith_name} model status: {status}")
            
            elif command == "status":
                print("\nSYSTEM STATUS:")
                print(f"Version: {VERSION}")
                print(f"Uptime: {time.time() - SYSTEM_HEALTH['uptime']:.1f}s")
                print(f"Total Decisions: {len(decision_history)}")
                print(f"API Status: {SYSTEM_HEALTH.get('api_status', 'unknown')}")
                print(f"TTS Status: {SYSTEM_HEALTH.get('tts_status', 'unknown')}")
                
                print("\nMONOLITH STATUS:")
                for name, config in MODEL_CONFIG.items():
                    status = config.get("status", "unknown")
                    print(f"  {name}: {status}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: vote, export, reload, status, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", "ERROR")

# === ENHANCED DEMO VOTING PROCESS ===
def demo_voting_process():
    """Demo voting process with full consensus workflow"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    add_notification(f"Starting demo vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    # Update system mode
    CONFIG["system_mode"] = "VOTING"
    
    # Simulate voting
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        # Simulate vote result with more varied responses
        responses = [
            "APPROVE - Operational parameters fall within acceptable risk thresholds",
            "DENY - Current threat assessment indicates elevated risk levels",
            "APPROVE - Historical analysis supports favorable outcome probability",
            "DENY - Resource allocation conflicts with existing priorities",
            "APPROVE - Strategic objectives align with proposed course of action",
            "DENY - Insufficient intelligence for confident risk assessment"
        ]
        result = random.choice(responses)
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    # Calculate consensus
    verdict = calculate_consensus(VOTES)
    
    # Update system mode based on result
    if verdict == "APPROVE":
        CONFIG["system_mode"] = "AUTHORIZED"
    elif verdict == "DENY":
        CONFIG["system_mode"] = "DENIED"
    else:
        CONFIG["system_mode"] = "DEADLOCK"
    
    # Generate reasoning summary
    reasoning_parts = []
    for name, vote in VOTES.items():
        reasoning_parts.append(f"{name}: {vote}")
    reasoning = "; ".join(reasoning_parts)
    
    # Log decision to history
    add_decision_to_history(query, verdict, reasoning, "demo_vote")
    
    # Display final verdict with TTS
    summarize_consensus(verdict)
    
    add_notification(f"Consensus reached: {verdict}", "success")
    log(f"RESPONSE: {verdict}")
    
    # Reset system mode after a delay
    def reset_mode():
        time.sleep(5)
        CONFIG["system_mode"] = "READY"
    
    threading.Thread(target=reset_mode, daemon=True).start()

# === INPUT HANDLING ===
def handle_input(stdscr, key: int, current_state: dict) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
        add_notification(f"Theme changed to {CONFIG['theme'].upper()}", "info")
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('7'):
        CONFIG["current_view"] = "history"
    elif key == ord('9'):
        CONFIG["current_view"] = "config"
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
    elif key in (ord('d'), ord('D')):
        CONFIG["current_view"] = "forensics"
        current_state["forensics_index"] = 0
    elif key in (ord('v'), ord('V')):
        # Trigger voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('r'), ord('R')) and CONFIG["current_view"] == "config":
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        add_notification("Diagnostics refreshed", "info")
    elif CONFIG["current_view"] == "forensics":
        # Handle forensics navigation
        if key == curses.KEY_UP:
            current_state["forensics_index"] = max(0, current_state.get("forensics_index", 0) - 1)
        elif key == curses.KEY_DOWN:
            max_index = len(decision_history) - 1
            current_state["forensics_index"] = min(max_index, current_state.get("forensics_index", 0) + 1)
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    """Main UI loop with enhanced state management"""
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    # Initialize color pairs
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)      # Red
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # White
    
    # State for UI navigation
    ui_state = {
        "forensics_index": 0,
        "last_health_update": 0
    }
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    # Special handling for console mode
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    # Re-initialize color pairs
                    if curses.has_colors():#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.6.1)
Complete single-file implementation with all features.
"""

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
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional

# === SYSTEM ASCII ART ===
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

CONSENSUS_LOGO = """
╔════════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                          v3.6.1      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# === CONFIGURATION ===
VERSION = "3.6.1"
BUILD_DATE = "2025-05-19"
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
CONFIG_PATH = ARBITER_DIR / "config.json"

CONFIG = {
    "theme": "military",
    "current_view": "main",
    "system_mode": "READY",
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9
    },
    "health_monitoring": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3
    }
}

MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "prompt": "You are RATIONALIS, logic engine of the Tribunal. Analyze the query logically and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "prompt": "You are AETERNUM, market historian and foresight node. Analyze patterns and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "prompt": "You are BELLATOR, tactical risk assessor and security analyst. Evaluate risks and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    }
}

# Box drawing characters for themes
BOX_CHARS = {
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮"
    },
    "eva": {
        "tl": "▛", "tr": "▜", "bl": "▙", "br": "▟",
        "h": "▀", "v": "▌"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃"
    }
}

# === STATE ===
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
VOTES = {}
SYSTEM_HEALTH = {
    "cpu": 0.0,
    "memory": 0.0,
    "uptime": time.time(),
    "tts_status": "unknown",
    "api_status": "unknown",
    "last_health_check": 0
}

# === UTILITIES ===
def log(msg, level="INFO"):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{t}] [{level}] {msg}"
    log_entries.append(formatted_msg)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{datetime.datetime.now():%Y%m%d}.log", "a") as f:
            f.write(f"{formatted_msg}\n")
    except: 
        pass

def add_notification(message: str, level: str = "info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now()
    })

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                CONFIG.update(json.load(f))
        except Exception as e:
            log(f"Failed to load config: {e}", "ERROR")

def save_config():
    try:
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        log(f"Failed to save config: {e}", "ERROR")

def post_to_model(monolith, query):
    cfg = MODEL_CONFIG[monolith]
    provider = CONFIG["llm_provider"]
    prompt = f"{cfg['prompt']}\n\nQUERY: {query}\n\nVOTE:"
    api = {
        "ollama": "http://localhost:11434/api/generate",
        "lmstudio": "http://localhost:1234/v1/completions"
    }[provider]

    payload = {"model": cfg["model"], "prompt": prompt, "stream": False, "temperature": 0.5, "max_tokens": 512}
    try:
        r = requests.post(api, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("response") or data.get("choices", [{}])[0].get("text", "")
        return f"Error: {r.status_code}"
    except Exception as e:
        return f"Exception: {e}"

def calculate_consensus(votes: Dict[str, str]) -> Optional[str]:
    """Calculate consensus based on votes"""
    approve_count = sum(1 for vote in votes.values() if "APPROVE" in vote.upper())
    deny_count = sum(1 for vote in votes.values() if "DENY" in vote.upper())
    
    if approve_count >= 2:
        return "APPROVE"
    elif deny_count >= 2:
        return "DENY"
    return "DEADLOCK"

# === MONOLITH LOGIC ===
class Monolith:
    def __init__(self, name):
        self.name = name
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        VOTE_DIR.mkdir(parents=True, exist_ok=True)

    def vote(self, query):
        log(f"[{self.name}] Voting on: {query}")
        result = post_to_model(self.name, query).strip()
        VOTES[self.name] = result
        self.write_vote(result)
        return result

    def write_vote(self, result):
        data = {"monolith": self.name, "vote": result, "timestamp": datetime.datetime.now().isoformat()}
        with open(self.vote_file, "w") as f:
            json.dump(data, f, indent=2)

# === BOOT SEQUENCE ===
def boot():
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.0)
    print(CONSENSUS_LOGO)
    time.sleep(0.5)
    print(f"Booting CONSENSUS SYSTEM v{VERSION} — Build {BUILD_DATE}\n")
    steps = ["Loading memory cores", "Validating vote ports", "Activating monoliths"]
    for s in steps:
        print(f"[✓] {s}")
        time.sleep(0.4)
    print("\n▛ SYSTEM READY ▟ — PRESS ENTER TO CONTINUE")
    input()

# === ARBITER VERDICT + TTS ===
def summarize_consensus(verdict: str):
    typed_text = f"FINAL VERDICT: {verdict.upper()}"
    for c in typed_text:
        print(c, end='', flush=True)
        time.sleep(0.04)
    print()
    
    if CONFIG.get("tts", {}).get("enabled"):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            engine.setProperty('rate', CONFIG["tts"].get("voice_rate", 150))
            engine.setProperty('volume', CONFIG["tts"].get("voice_volume", 0.9))
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            log(f"[TTS] Announced verdict: {verdict}")
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3", "WARNING")
        except Exception as e:
            log(f"[TTS Error] {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. Console Mode (Direct voting)")
        print("2. Exit")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Console mode - simplified for testing
            while True:
                query = input("\n>> ENTER QUERY FOR VOTE (or 'quit' to exit):\n> ")
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                    
                log(f"COMMAND: console_vote -> {query}")
                VOTES.clear()
                
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                verdict = calculate_consensus(VOTES)
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                print(f"\nVotes saved to {VOTE_DIR}")
        
        else:
            print("Exiting CONSENSUS System...")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()
        y = start_y + i
        
        # Timestamp
        timestamp = decision["timestamp"].strftime("%m/%d %H:%M")
        safe_addstr(stdscr, y, 3, timestamp, curses.color_pair(7))
        
        # Verdict with color
        verdict = decision["verdict"]
        verdict_color = 2 if verdict == "APPROVE" else 1 if verdict == "DENY" else 3
        safe_addstr(stdscr, y, 15, verdict, curses.A_BOLD | curses.color_pair(verdict_color))
        
        # Query (truncated)
        query = decision["query"][:35] + "..." if len(decision["query"]) > 35 else decision["query"]
        safe_addstr(stdscr, y, 25, query, curses.color_pair(7))
        
        # Individual votes summary
        votes_text = ""
        if decision.get("individual_votes"):
            vote_summary = []
            for name, vote in decision["individual_votes"].items():
                vote_short = "A" if "APPROVE" in vote.upper() else "D" if "DENY" in vote.upper() else "?"
                vote_summary.append(f"{name[0]}{vote_short}")
            votes_text = " ".join(vote_summary)
        safe_addstr(stdscr, y, width - 20, votes_text, curses.color_pair(4))
        
        # Session ID (last 6 chars)
        session_id = decision.get("session_id", "")[-6:] if decision.get("session_id") else "N/A"
        safe_addstr(stdscr, y, width - 8, session_id, curses.color_pair(5))
    
    # Footer stats
    total_decisions = len(decision_history)
    approve_count = sum(1 for d in decision_history if d["verdict"] == "APPROVE")
    deny_count = sum(1 for d in decision_history if d["verdict"] == "DENY")
    deadlock_count = sum(1 for d in decision_history if d["verdict"] == "DEADLOCK")
    
    stats_y = height - 4
    stats_text = f"Total: {total_decisions} | Approved: {approve_count} | Denied: {deny_count} | Deadlocks: {deadlock_count}"
    safe_addstr(stdscr, stats_y, (width - len(stats_text)) // 2, stats_text, curses.color_pair(7))
    
    # Controls
    controls = "M: Main View | Q: Quit | D: Forensic View"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_config_diagnostics_screen(stdscr, theme: str):
    """Render configuration diagnostics screen (Key 9)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS CONFIGURATION DIAGNOSTICS"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Draw border
    draw_box(stdscr, 3, 1, height - 7, width - 2, theme)
    
    y_pos = 5
    
    # System Information
    safe_addstr(stdscr, y_pos, 3, "SYSTEM INFORMATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    sys_info = [
        ("Version", VERSION),
        ("Build Date", BUILD_DATE),
        ("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("System Root", str(SYSTEM_ROOT)),
        ("Config Path", str(CONFIG_PATH)),
        ("Current Theme", CONFIG.get("theme", "unknown")),
        ("Current View", CONFIG.get("current_view", "unknown"))
    ]
    
    for label, value in sys_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 25, str(value), curses.color_pair(2))
        y_pos += 1
    
    y_pos += 1
    
    # LLM Configuration
    safe_addstr(stdscr, y_pos, 3, "LLM CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    safe_addstr(stdscr, y_pos, 5, f"Provider: {CONFIG.get('llm_provider', 'unknown')}", curses.color_pair(2))
    y_pos += 1
    safe_addstr(stdscr, y_pos, 5, f"Vote Timeout: {CONFIG.get('vote_timeout', 'unknown')}s", curses.color_pair(2))
    y_pos += 1
    
    # Model Status
    for name, config in MODEL_CONFIG.items():
        model_name = config.get("model", "unknown")
        status = config.get("status", "unknown")
        status_color = 2 if status == "ready" else 3 if status == "not_loaded" else 1
        
        safe_addstr(stdscr, y_pos, 5, f"{name}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 18, model_name, curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 45, f"[{status.upper()}]", curses.color_pair(status_color))
        y_pos += 1
    
    y_pos += 1
    
    # TTS Configuration
    safe_addstr(stdscr, y_pos, 3, "TTS CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    tts_config = CONFIG.get("tts", {})
    tts_info = [
        ("Enabled", tts_config.get("enabled", "unknown")),
        ("Engine", tts_config.get("engine", "unknown")),
        ("Voice Rate", tts_config.get("voice_rate", "unknown")),
        ("Voice Volume", tts_config.get("voice_volume", "unknown")),
        ("Status", SYSTEM_HEALTH.get("tts_status", "unknown"))
    ]
    
    for label, value in tts_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        color = 2 if str(value).lower() in ["true", "operational"] else 1 if str(value).lower() in ["false", "unavailable"] else 7
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    y_pos += 1
    
    # Health Monitoring
    safe_addstr(stdscr, y_pos, 3, "HEALTH MONITORING:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    health_info = [
        ("CPU Usage", f"{SYSTEM_HEALTH.get('cpu', 0):.1f}%"),
        ("Memory Usage", f"{SYSTEM_HEALTH.get('memory', 0):.1f}%"),
        ("API Status", SYSTEM_HEALTH.get("api_status", "unknown")),
        ("Last Health Check", datetime.datetime.fromtimestamp(SYSTEM_HEALTH.get("last_health_check", 0)).strftime("%H:%M:%S"))
    ]
    
    for label, value in health_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        
        # Color based on value
        if "%" in str(value):
            numeric_value = float(value.replace("%", ""))
            color = 2 if numeric_value < 70 else 3 if numeric_value < 90 else 1
        elif str(value).lower() == "operational":
            color = 2
        elif str(value).lower() in ["error", "unreachable", "unavailable"]:
            color = 1
        else:
            color = 7
            
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    # Controls
    controls = "M: Main View | Q: Quit | R: Refresh Diagnostics"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_decision_forensics_screen(stdscr, theme: str, selected_index: int = 0):
    """Render decision forensics screen (Key D)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS DECISION FORENSIC INSPECTOR"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions available", curses.color_pair(3))
        controls = "M: Main View | Q: Quit"
        safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
        render_status_bar(stdscr, theme)
        return
    
    # Get selected decision
    decisions_list = list(decision_history)
    selected_index = max(0, min(selected_index, len(decisions_list) - 1))
    decision = decisions_list[selected_index]
    
    # Decision list (left panel)
    list_width = width // 3
    draw_box(stdscr, 3, 1, height - 7, list_width, theme)
    safe_addstr(stdscr, 3, 3, "DECISION LIST", curses.A_BOLD)
    
    # Show decisions with selection
    list_start_y = 5
    max_list_items = height - 10
    
    for i, dec in enumerate(decisions_list[-max_list_items:]):
        y = list_start_y + i
        if y >= height - 5:
            break
            
        # Highlight selected item
        attr = curses.A_REVERSE if i == selected_index else 0
        
        timestamp = dec["timestamp"].strftime("%m/%d %H:%M")
        verdict = dec["verdict"][:3]
        verdict_color = 2 if dec["verdict"] == "APPROVE" else 1 if dec["verdict"] == "DENY" else 3
        
        safe_addstr(stdscr, y, 3, f"{timestamp} {verdict}", curses.color_pair(verdict_color) | attr)
    
    # Decision details (right panel)
    details_x = list_width + 2
    details_width = width - list_width - 3
    draw_box(stdscr, 3, details_x, height - 7, details_width, theme)
    safe_addstr(stdscr, 3, details_x + 2, "DECISION DETAILS", curses.A_BOLD)
    
    # Display decision details
    detail_y = 5
    
    # Basic info
    safe_addstr(stdscr, detail_y, details_x + 2, "QUERY:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    # Word wrap query
    query = decision["query"]
    max_width = details_width - 6
    query_lines = [query[i:i+max_width] for i in range(0, len(query), max_width)]
    for line in query_lines[:3]:  # Max 3 lines
        safe_addstr(stdscr, detail_y, details_x + 4, line, curses.color_pair(7))
        detail_y += 1
    
    detail_y += 1
    
    # Verdict and timestamp
    safe_addstr(stdscr, detail_y, details_x + 2, "VERDICT:", curses.A_BOLD | curses.color_pair(3))
    verdict_color = 2 if decision["verdict"] == "APPROVE" else 1 if decision["verdict"] == "DENY" else 3
    safe_addstr(stdscr, detail_y, details_x + 12, decision["verdict"], curses.A_BOLD | curses.color_pair(verdict_color))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "TIMESTAMP:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 14, decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), curses.color_pair(7))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "SESSION ID:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 15, decision.get("session_id", "N/A"), curses.color_pair(7))
    detail_y += 2
    
    # Individual votes
    safe_addstr(stdscr, detail_y, details_x + 2, "INDIVIDUAL VOTES:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    if decision.get("individual_votes"):
        for name, vote in decision["individual_votes"].items():
            safe_addstr(stdscr, detail_y, details_x + 2, f"{name}:", curses.A_BOLD | curses.color_pair(4))
            
            # Truncate long votes
            vote_display = vote[:max_width-15] + "..." if len(vote) > max_width-15 else vote
            safe_addstr(stdscr, detail_y, details_x + 15, vote_display, curses.color_pair(7))
            detail_y += 1
    else:
        safe_addstr(stdscr, detail_y, details_x + 4, "No individual votes recorded", curses.color_pair(3))
        detail_y += 1
    
    detail_y += 1
    
    # System state
    if decision.get("system_state"):
        safe_addstr(stdscr, detail_y, details_x + 2, "SYSTEM STATE:", curses.A_BOLD | curses.color_pair(3))
        detail_y += 1
        
        state = decision["system_state"]
        safe_addstr(stdscr, detail_y, details_x + 4, f"Theme: {state.get('theme', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Mode: {state.get('mode', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Version: {state.get('version', 'N/A')}", curses.color_pair(7))
        detail_y += 1
    
    # Navigation info
    nav_info = f"Decision {selected_index + 1} of {len(decisions_list)}"
    safe_addstr(stdscr, height - 5, (width - len(nav_info)) // 2, nav_info, curses.color_pair(5))
    
    # Controls
    controls = "↑↓: Navigate | M: Main View | 7: History | Q: Quit"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

# === EXPORT FUNCTIONALITY ===
def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"decisions_{timestamp}.json"
        export_data = {
            "export_info": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "total_decisions": len(decision_history)
            },
            "decisions": [
                {
                    **decision,
                    "timestamp": decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"decisions_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Query", "Verdict", "Session_ID", "Individual_Votes", "Reasoning"])
            
            for decision in decision_history:
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                votes_str = "; ".join([f"{k}: {v}" for k, v in decision.get("individual_votes", {}).items()])
                writer.writerow([
                    timestamp,
                    decision["query"],
                    decision["verdict"],
                    decision.get("session_id", ""),
                    votes_str,
                    decision.get("reasoning", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"decisions_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Version: {VERSION}\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, decision in enumerate(decision_history, 1):
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                f.write(f"DECISION #{i}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Verdict: {decision['verdict']}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                if decision.get("individual_votes"):
                    f.write("Individual Votes:\n")
                    for name, vote in decision["individual_votes"].items():
                        f.write(f"  {name}: {vote}\n")
                
                if decision.get("reasoning"):
                    f.write(f"Reasoning: {decision['reasoning']}\n")
                
                f.write("-" * 80 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    return str(filename)

# === CONSOLE MODE ===
def run_console_mode():
    """Run console mode for direct voting and commands"""
    print("\n" + "="*80)
    print("CONSENSUS SYSTEM - CONSOLE MODE")
    print("="*80)
    print("Commands: vote <query> | export <format> | reload <monolith> | status | quit")
    
    while True:
        try:
            command_input = input("\n>> ").strip()
            
            if not command_input:
                continue
                
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ['quit', 'exit', 'q']:
                break
            
            elif command == "vote":
                if not args:
                    print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                
                add_decision_to_history(query, verdict, reasoning, "console_vote")
                print(f"\nVotes saved to {VOTE_DIR}")
            
            elif command == "status":
                print("\nSYSTEM STATUS:")
                print(f"Version: {VERSION}")
                print(f"Uptime: {time.time() - SYSTEM_HEALTH['uptime']:.1f}s")
                print(f"Total Decisions: {len(decision_history)}")
                print(f"API Status: {SYSTEM_HEALTH.get('api_status', 'unknown')}")
                print(f"TTS Status: {SYSTEM_HEALTH.get('tts_status', 'unknown')}")
                
                print("\nMONOLITH STATUS:")
                for name, config in MODEL_CONFIG.items():
                    status = config.get("status", "unknown")
                    print(f"  {name}: {status}")
            
            elif command == "reload":
                if not args or args.upper() not in MODEL_CONFIG:
                    print("Usage: reload <RATIONALIS|AETERNUM|BELLATOR>")
                    continue
                
                monolith_name = args.upper()
                monolith = Monolith(monolith_name)
                status = monolith.reload_model()
                print(f"{monolith_name} model status: {status}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: vote, status, reload, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

# === DEMO VOTING ===
def demo_voting_process():
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    add_notification(f"Starting demo vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    CONFIG["system_mode"] = "VOTING"
    
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        responses = [
            "APPROVE - Operational parameters fall within acceptable risk thresholds",
            "DENY - Current threat assessment indicates elevated risk levels",
            "APPROVE - Historical analysis supports favorable outcome probability",
            "DENY - Resource allocation conflicts with existing priorities",
            "APPROVE - Strategic objectives align with proposed course of action",
            "DENY - Insufficient intelligence for confident risk assessment"
        ]
        result = random.choice(responses)
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    verdict = calculate_consensus(VOTES)
    
    if verdict == "APPROVE":
        CONFIG["system_mode"] = "AUTHORIZED"
    elif verdict == "DENY":
        CONFIG["system_mode"] = "DENIED"
    else:
        CONFIG["system_mode"] = "DEADLOCK"
    
    reasoning_parts = []
    for name, vote in VOTES.items():
        reasoning_parts.append(f"{name}: {vote}")
    reasoning = "; ".join(reasoning_parts)
    
    add_decision_to_history(query, verdict, reasoning, "demo_vote")
    summarize_consensus(verdict)
    add_notification(f"Consensus reached: {verdict}", "success")
    log(f"RESPONSE: {verdict}")
    
    def reset_mode():
        time.sleep(5)
        CONFIG["system_mode"] = "READY"
    
    threading.Thread(target=reset_mode, daemon=True).start()

# === INPUT HANDLING ===
def handle_input(stdscr, key: int, current_state: dict) -> bool:
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('9'):
        CONFIG["current_view"] = "config"
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
    elif key in (ord('v'), ord('V')):
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        return False  # Exit to console mode
    elif key in (ord('r'), ord('R')) and CONFIG["current_view"] == "config":
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        add_notification("Diagnostics refreshed", "info")
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)      # Red
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # White
    
    ui_state = {
        "last_health_update": 0
    }
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    if curses.has_colors():
                        curses.init_pair(1, curses.COLOR_RED, -1)
                        curses.init_pair(2, curses.COLOR_GREEN, -1)
                        curses.init_pair(3, curses.COLOR_YELLOW, -1)
                        curses.init_pair(4, curses.COLOR_BLUE, -1)
                        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
                        curses.init_pair(6, curses.COLOR_CYAN, -1)
                        curses.init_pair(7, curses.COLOR_WHITE, -1)
                else:
                    running = handle_input(stdscr, key, ui_state)
            
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                
                if current_time - ui_state["last_health_update"] > 5:
                    update_system_health()
                    ui_state["last_health_update"] = current_time
                
                current_view = CONFIG.get("current_view", "main")
                theme = CONFIG.get("theme", "military")
                
                if current_view == "config":
                    render_config_screen(stdscr, theme)
                else:
                    render_main_screen(stdscr, theme)
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"Error in main loop: {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        log(f"CONSENSUS System v{VERSION} starting up", "STARTUP")
        
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. GUI Mode (Full interface with diagnostics)")
        print("2. Console Mode (Direct command-line operation)")
        print("3. Exit")
        
        while True:
            choice = input("\nEnter choice (1, 2, or 3): ").strip()
            
            if choice == "1":
                log("Starting GUI mode", "MODE")
                add_notification("GUI mode initialized", "info")
                curses.wrapper(run_ui_loop)
                break
            elif choice == "2":
                log("Starting console mode", "MODE")
                run_console_mode()
                break
            elif choice == "3":
                log("User requested exit", "MODE")
                print("Exiting CONSENSUS System...")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
    except Exception as e:
        error_msg = f"Fatal error: {e}"
        print(error_msg)
        log(error_msg, "FATAL")
        sys.exit(1)
    finally:
        uptime = time.time() - SYSTEM_HEALTH["uptime"]
        log(f"CONSENSUS System shutting down after {uptime:.1f}s uptime", "SHUTDOWN")
        print("\n🟢 CONSENSUS System terminated gracefully")
        print(f"📊 Session summary: {len(decision_history)} decisions processed")
        if decision_history:
            last_decision = decision_history[-1]
            print(f"🕒 Last decision: {last_decision['timestamp'].strftime('%H:%M:%S')} - {last_decision['verdict']}")

if __name__ == "__main__":
    main()("Usage: vote <your question>")
                    continue
                    
                query = args
                log(f"COMMAND: console_vote -> {query}")
                add_notification(f"Console vote: {query}", "info")
                
                # Clear previous votes
                VOTES.clear()
                
                # Create monoliths and vote
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                # Calculate consensus
                verdict = calculate_consensus(VOTES)
                
                # Generate reasoning summary
                reasoning_parts = []
                for name, vote in VOTES.items():
                    reasoning_parts.append(f"{name}: {vote}")
                reasoning = "; ".join(reasoning_parts)
                
                # Display verdict
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                
                # Log decision
                add_decision_to_history(query, verdict, reasoning, "console_vote")
                
                print(f"\nVotes saved to {VOTE_DIR}")
                print("Full trace available in logs.")
            
            elif command == "export":
                if not args or args.lower() not in ["json", "csv", "txt"]:
                    print("Usage: export <json|csv|txt>")
                    continue
                
                try:
                    filename = export_decisions(args.lower())
                    print(f"Decisions exported to: {filename}")
                    log(f"Exported decisions to {filename}")
                except Exception as e:
                    print(f"Export failed: {e}")
                    log(f"Export failed: {e}", "ERROR")
            
            elif command == "reload":
                if not args or args.upper() not in MODEL_CONFIG:
                    print("Usage: reload <RATIONALIS|AETERNUM|BELLATOR>")
                    continue
                
                monolith_name = args.upper()
                monolith = Monolith(monolith_name)
                status = monolith.reload_model()
                print(f"{monolith_name} model status: {status}")
            
            elif command == "status":
                print("\nSYSTEM STATUS:")
                print(f"Version: {VERSION}")
                print(f"Uptime: {time.time() - SYSTEM_HEALTH['uptime']:.1f}s")
                print(f"Total Decisions: {len(decision_history)}")
                print(f"API Status: {SYSTEM_HEALTH.get('api_status', 'unknown')}")
                print(f"TTS Status: {SYSTEM_HEALTH.get('tts_status', 'unknown')}")
                
                print("\nMONOLITH STATUS:")
                for name, config in MODEL_CONFIG.items():
                    status = config.get("status", "unknown")
                    print(f"  {name}: {status}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: vote, export, reload, status, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", "ERROR")

# === ENHANCED DEMO VOTING PROCESS ===
def demo_voting_process():
    """Demo voting process with full consensus workflow"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    add_notification(f"Starting demo vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    # Update system mode
    CONFIG["system_mode"] = "VOTING"
    
    # Simulate voting
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        # Simulate vote result with more varied responses
        responses = [
            "APPROVE - Operational parameters fall within acceptable risk thresholds",
            "DENY - Current threat assessment indicates elevated risk levels",
            "APPROVE - Historical analysis supports favorable outcome probability",
            "DENY - Resource allocation conflicts with existing priorities",
            "APPROVE - Strategic objectives align with proposed course of action",
            "DENY - Insufficient intelligence for confident risk assessment"
        ]
        result = random.choice(responses)
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    # Calculate consensus
    verdict = calculate_consensus(VOTES)
    
    # Update system mode based on result
    if verdict == "APPROVE":
        CONFIG["system_mode"] = "AUTHORIZED"
    elif verdict == "DENY":
        CONFIG["system_mode"] = "DENIED"
    else:
        CONFIG["system_mode"] = "DEADLOCK"
    
    # Generate reasoning summary
    reasoning_parts = []
    for name, vote in VOTES.items():
        reasoning_parts.append(f"{name}: {vote}")
    reasoning = "; ".join(reasoning_parts)
    
    # Log decision to history
    add_decision_to_history(query, verdict, reasoning, "demo_vote")
    
    # Display final verdict with TTS
    summarize_consensus(verdict)
    
    add_notification(f"Consensus reached: {verdict}", "success")
    log(f"RESPONSE: {verdict}")
    
    # Reset system mode after a delay
    def reset_mode():
        time.sleep(5)
        CONFIG["system_mode"] = "READY"
    
    threading.Thread(target=reset_mode, daemon=True).start()

# === INPUT HANDLING ===
def handle_input(stdscr, key: int, current_state: dict) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
        add_notification(f"Theme changed to {CONFIG['theme'].upper()}", "info")
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('7'):
        CONFIG["current_view"] = "history"
    elif key == ord('9'):
        CONFIG["current_view"] = "config"
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
    elif key in (ord('d'), ord('D')):
        CONFIG["current_view"] = "forensics"
        current_state["forensics_index"] = 0
    elif key in (ord('v'), ord('V')):
        # Trigger voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('r'), ord('R')) and CONFIG["current_view"] == "config":
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        add_notification("Diagnostics refreshed", "info")
    elif CONFIG["current_view"] == "forensics":
        # Handle forensics navigation
        if key == curses.KEY_UP:
            current_state["forensics_index"] = max(0, current_state.get("forensics_index", 0) - 1)
        elif key == curses.KEY_DOWN:
            max_index = len(decision_history) - 1
            current_state["forensics_index"] = min(max_index, current_state.get("forensics_index", 0) + 1)
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    """Main UI loop with enhanced state management"""
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    # Initialize color pairs
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)      # Red
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # White
    
    # State for UI navigation
    ui_state = {
        "forensics_index": 0,
        "last_health_update": 0
    }
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    # Special handling for console mode
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    # Re-initialize color pairs
                    if curses.has_colors():#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.6.1)
Complete single-file implementation with all features.
"""

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
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional

# === SYSTEM ASCII ART ===
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

CONSENSUS_LOGO = """
╔════════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                          v3.6.1      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# === CONFIGURATION ===
VERSION = "3.6.1"
BUILD_DATE = "2025-05-19"
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
CONFIG_PATH = ARBITER_DIR / "config.json"

CONFIG = {
    "theme": "military",
    "current_view": "main",
    "system_mode": "READY",
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9
    },
    "health_monitoring": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3
    }
}

MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "prompt": "You are RATIONALIS, logic engine of the Tribunal. Analyze the query logically and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "prompt": "You are AETERNUM, market historian and foresight node. Analyze patterns and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "prompt": "You are BELLATOR, tactical risk assessor and security analyst. Evaluate risks and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    }
}

# Box drawing characters for themes
BOX_CHARS = {
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮"
    },
    "eva": {
        "tl": "▛", "tr": "▜", "bl": "▙", "br": "▟",
        "h": "▀", "v": "▌"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃"
    }
}

# === STATE ===
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
VOTES = {}
SYSTEM_HEALTH = {
    "cpu": 0.0,
    "memory": 0.0,
    "uptime": time.time(),
    "tts_status": "unknown",
    "api_status": "unknown",
    "last_health_check": 0
}

# === UTILITIES ===
def log(msg, level="INFO"):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{t}] [{level}] {msg}"
    log_entries.append(formatted_msg)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{datetime.datetime.now():%Y%m%d}.log", "a") as f:
            f.write(f"{formatted_msg}\n")
    except: 
        pass

def add_notification(message: str, level: str = "info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now()
    })

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                CONFIG.update(json.load(f))
        except Exception as e:
            log(f"Failed to load config: {e}", "ERROR")

def save_config():
    try:
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        log(f"Failed to save config: {e}", "ERROR")

def post_to_model(monolith, query):
    cfg = MODEL_CONFIG[monolith]
    provider = CONFIG["llm_provider"]
    prompt = f"{cfg['prompt']}\n\nQUERY: {query}\n\nVOTE:"
    api = {
        "ollama": "http://localhost:11434/api/generate",
        "lmstudio": "http://localhost:1234/v1/completions"
    }[provider]

    payload = {"model": cfg["model"], "prompt": prompt, "stream": False, "temperature": 0.5, "max_tokens": 512}
    try:
        r = requests.post(api, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("response") or data.get("choices", [{}])[0].get("text", "")
        return f"Error: {r.status_code}"
    except Exception as e:
        return f"Exception: {e}"

def calculate_consensus(votes: Dict[str, str]) -> Optional[str]:
    """Calculate consensus based on votes"""
    approve_count = sum(1 for vote in votes.values() if "APPROVE" in vote.upper())
    deny_count = sum(1 for vote in votes.values() if "DENY" in vote.upper())
    
    if approve_count >= 2:
        return "APPROVE"
    elif deny_count >= 2:
        return "DENY"
    return "DEADLOCK"

# === MONOLITH LOGIC ===
class Monolith:
    def __init__(self, name):
        self.name = name
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        VOTE_DIR.mkdir(parents=True, exist_ok=True)

    def vote(self, query):
        log(f"[{self.name}] Voting on: {query}")
        result = post_to_model(self.name, query).strip()
        VOTES[self.name] = result
        self.write_vote(result)
        return result

    def write_vote(self, result):
        data = {"monolith": self.name, "vote": result, "timestamp": datetime.datetime.now().isoformat()}
        with open(self.vote_file, "w") as f:
            json.dump(data, f, indent=2)

# === BOOT SEQUENCE ===
def boot():
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.0)
    print(CONSENSUS_LOGO)
    time.sleep(0.5)
    print(f"Booting CONSENSUS SYSTEM v{VERSION} — Build {BUILD_DATE}\n")
    steps = ["Loading memory cores", "Validating vote ports", "Activating monoliths"]
    for s in steps:
        print(f"[✓] {s}")
        time.sleep(0.4)
    print("\n▛ SYSTEM READY ▟ — PRESS ENTER TO CONTINUE")
    input()

# === ARBITER VERDICT + TTS ===
def summarize_consensus(verdict: str):
    typed_text = f"FINAL VERDICT: {verdict.upper()}"
    for c in typed_text:
        print(c, end='', flush=True)
        time.sleep(0.04)
    print()
    
    if CONFIG.get("tts", {}).get("enabled"):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            engine.setProperty('rate', CONFIG["tts"].get("voice_rate", 150))
            engine.setProperty('volume', CONFIG["tts"].get("voice_volume", 0.9))
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            log(f"[TTS] Announced verdict: {verdict}")
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3", "WARNING")
        except Exception as e:
            log(f"[TTS Error] {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. Console Mode (Direct voting)")
        print("2. Exit")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Console mode - simplified for testing
            while True:
                query = input("\n>> ENTER QUERY FOR VOTE (or 'quit' to exit):\n> ")
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                    
                log(f"COMMAND: console_vote -> {query}")
                VOTES.clear()
                
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                verdict = calculate_consensus(VOTES)
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                print(f"\nVotes saved to {VOTE_DIR}")
        
        else:
            print("Exiting CONSENSUS System...")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()
        y = start_y + i
        
        # Timestamp
        timestamp = decision["timestamp"].strftime("%m/%d %H:%M")
        safe_addstr(stdscr, y, 3, timestamp, curses.color_pair(7))
        
        # Verdict with color
        verdict = decision["verdict"]
        verdict_color = 2 if verdict == "APPROVE" else 1 if verdict == "DENY" else 3
        safe_addstr(stdscr, y, 15, verdict, curses.A_BOLD | curses.color_pair(verdict_color))
        
        # Query (truncated)
        query = decision["query"][:35] + "..." if len(decision["query"]) > 35 else decision["query"]
        safe_addstr(stdscr, y, 25, query, curses.color_pair(7))
        
        # Individual votes summary
        votes_text = ""
        if decision.get("individual_votes"):
            vote_summary = []
            for name, vote in decision["individual_votes"].items():
                vote_short = "A" if "APPROVE" in vote.upper() else "D" if "DENY" in vote.upper() else "?"
                vote_summary.append(f"{name[0]}{vote_short}")
            votes_text = " ".join(vote_summary)
        safe_addstr(stdscr, y, width - 20, votes_text, curses.color_pair(4))
        
        # Session ID (last 6 chars)
        session_id = decision.get("session_id", "")[-6:] if decision.get("session_id") else "N/A"
        safe_addstr(stdscr, y, width - 8, session_id, curses.color_pair(5))
    
    # Footer stats
    total_decisions = len(decision_history)
    approve_count = sum(1 for d in decision_history if d["verdict"] == "APPROVE")
    deny_count = sum(1 for d in decision_history if d["verdict"] == "DENY")
    deadlock_count = sum(1 for d in decision_history if d["verdict"] == "DEADLOCK")
    
    stats_y = height - 4
    stats_text = f"Total: {total_decisions} | Approved: {approve_count} | Denied: {deny_count} | Deadlocks: {deadlock_count}"
    safe_addstr(stdscr, stats_y, (width - len(stats_text)) // 2, stats_text, curses.color_pair(7))
    
    # Controls
    controls = "M: Main View | Q: Quit | D: Forensic View"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_config_diagnostics_screen(stdscr, theme: str):
    """Render configuration diagnostics screen (Key 9)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS CONFIGURATION DIAGNOSTICS"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Draw border
    draw_box(stdscr, 3, 1, height - 7, width - 2, theme)
    
    y_pos = 5
    
    # System Information
    safe_addstr(stdscr, y_pos, 3, "SYSTEM INFORMATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    sys_info = [
        ("Version", VERSION),
        ("Build Date", BUILD_DATE),
        ("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("System Root", str(SYSTEM_ROOT)),
        ("Config Path", str(CONFIG_PATH)),
        ("Current Theme", CONFIG.get("theme", "unknown")),
        ("Current View", CONFIG.get("current_view", "unknown"))
    ]
    
    for label, value in sys_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 25, str(value), curses.color_pair(2))
        y_pos += 1
    
    y_pos += 1
    
    # LLM Configuration
    safe_addstr(stdscr, y_pos, 3, "LLM CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    safe_addstr(stdscr, y_pos, 5, f"Provider: {CONFIG.get('llm_provider', 'unknown')}", curses.color_pair(2))
    y_pos += 1
    safe_addstr(stdscr, y_pos, 5, f"Vote Timeout: {CONFIG.get('vote_timeout', 'unknown')}s", curses.color_pair(2))
    y_pos += 1
    
    # Model Status
    for name, config in MODEL_CONFIG.items():
        model_name = config.get("model", "unknown")
        status = config.get("status", "unknown")
        status_color = 2 if status == "ready" else 3 if status == "not_loaded" else 1
        
        safe_addstr(stdscr, y_pos, 5, f"{name}:", curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 18, model_name, curses.color_pair(7))
        safe_addstr(stdscr, y_pos, 45, f"[{status.upper()}]", curses.color_pair(status_color))
        y_pos += 1
    
    y_pos += 1
    
    # TTS Configuration
    safe_addstr(stdscr, y_pos, 3, "TTS CONFIGURATION:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    tts_config = CONFIG.get("tts", {})
    tts_info = [
        ("Enabled", tts_config.get("enabled", "unknown")),
        ("Engine", tts_config.get("engine", "unknown")),
        ("Voice Rate", tts_config.get("voice_rate", "unknown")),
        ("Voice Volume", tts_config.get("voice_volume", "unknown")),
        ("Status", SYSTEM_HEALTH.get("tts_status", "unknown"))
    ]
    
    for label, value in tts_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        color = 2 if str(value).lower() in ["true", "operational"] else 1 if str(value).lower() in ["false", "unavailable"] else 7
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    y_pos += 1
    
    # Health Monitoring
    safe_addstr(stdscr, y_pos, 3, "HEALTH MONITORING:", curses.A_BOLD | curses.color_pair(3))
    y_pos += 1
    
    health_info = [
        ("CPU Usage", f"{SYSTEM_HEALTH.get('cpu', 0):.1f}%"),
        ("Memory Usage", f"{SYSTEM_HEALTH.get('memory', 0):.1f}%"),
        ("API Status", SYSTEM_HEALTH.get("api_status", "unknown")),
        ("Last Health Check", datetime.datetime.fromtimestamp(SYSTEM_HEALTH.get("last_health_check", 0)).strftime("%H:%M:%S"))
    ]
    
    for label, value in health_info:
        safe_addstr(stdscr, y_pos, 5, f"{label}:", curses.color_pair(7))
        
        # Color based on value
        if "%" in str(value):
            numeric_value = float(value.replace("%", ""))
            color = 2 if numeric_value < 70 else 3 if numeric_value < 90 else 1
        elif str(value).lower() == "operational":
            color = 2
        elif str(value).lower() in ["error", "unreachable", "unavailable"]:
            color = 1
        else:
            color = 7
            
        safe_addstr(stdscr, y_pos, 20, str(value), curses.color_pair(color))
        y_pos += 1
    
    # Controls
    controls = "M: Main View | Q: Quit | R: Refresh Diagnostics"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

def render_decision_forensics_screen(stdscr, theme: str, selected_index: int = 0):
    """Render decision forensics screen (Key D)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS DECISION FORENSIC INSPECTOR"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions available", curses.color_pair(3))
        controls = "M: Main View | Q: Quit"
        safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
        render_status_bar(stdscr, theme)
        return
    
    # Get selected decision
    decisions_list = list(decision_history)
    selected_index = max(0, min(selected_index, len(decisions_list) - 1))
    decision = decisions_list[selected_index]
    
    # Decision list (left panel)
    list_width = width // 3
    draw_box(stdscr, 3, 1, height - 7, list_width, theme)
    safe_addstr(stdscr, 3, 3, "DECISION LIST", curses.A_BOLD)
    
    # Show decisions with selection
    list_start_y = 5
    max_list_items = height - 10
    
    for i, dec in enumerate(decisions_list[-max_list_items:]):
        y = list_start_y + i
        if y >= height - 5:
            break
            
        # Highlight selected item
        attr = curses.A_REVERSE if i == selected_index else 0
        
        timestamp = dec["timestamp"].strftime("%m/%d %H:%M")
        verdict = dec["verdict"][:3]
        verdict_color = 2 if dec["verdict"] == "APPROVE" else 1 if dec["verdict"] == "DENY" else 3
        
        safe_addstr(stdscr, y, 3, f"{timestamp} {verdict}", curses.color_pair(verdict_color) | attr)
    
    # Decision details (right panel)
    details_x = list_width + 2
    details_width = width - list_width - 3
    draw_box(stdscr, 3, details_x, height - 7, details_width, theme)
    safe_addstr(stdscr, 3, details_x + 2, "DECISION DETAILS", curses.A_BOLD)
    
    # Display decision details
    detail_y = 5
    
    # Basic info
    safe_addstr(stdscr, detail_y, details_x + 2, "QUERY:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    # Word wrap query
    query = decision["query"]
    max_width = details_width - 6
    query_lines = [query[i:i+max_width] for i in range(0, len(query), max_width)]
    for line in query_lines[:3]:  # Max 3 lines
        safe_addstr(stdscr, detail_y, details_x + 4, line, curses.color_pair(7))
        detail_y += 1
    
    detail_y += 1
    
    # Verdict and timestamp
    safe_addstr(stdscr, detail_y, details_x + 2, "VERDICT:", curses.A_BOLD | curses.color_pair(3))
    verdict_color = 2 if decision["verdict"] == "APPROVE" else 1 if decision["verdict"] == "DENY" else 3
    safe_addstr(stdscr, detail_y, details_x + 12, decision["verdict"], curses.A_BOLD | curses.color_pair(verdict_color))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "TIMESTAMP:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 14, decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), curses.color_pair(7))
    detail_y += 1
    
    safe_addstr(stdscr, detail_y, details_x + 2, "SESSION ID:", curses.A_BOLD | curses.color_pair(3))
    safe_addstr(stdscr, detail_y, details_x + 15, decision.get("session_id", "N/A"), curses.color_pair(7))
    detail_y += 2
    
    # Individual votes
    safe_addstr(stdscr, detail_y, details_x + 2, "INDIVIDUAL VOTES:", curses.A_BOLD | curses.color_pair(3))
    detail_y += 1
    
    if decision.get("individual_votes"):
        for name, vote in decision["individual_votes"].items():
            safe_addstr(stdscr, detail_y, details_x + 2, f"{name}:", curses.A_BOLD | curses.color_pair(4))
            
            # Truncate long votes
            vote_display = vote[:max_width-15] + "..." if len(vote) > max_width-15 else vote
            safe_addstr(stdscr, detail_y, details_x + 15, vote_display, curses.color_pair(7))
            detail_y += 1
    else:
        safe_addstr(stdscr, detail_y, details_x + 4, "No individual votes recorded", curses.color_pair(3))
        detail_y += 1
    
    detail_y += 1
    
    # System state
    if decision.get("system_state"):
        safe_addstr(stdscr, detail_y, details_x + 2, "SYSTEM STATE:", curses.A_BOLD | curses.color_pair(3))
        detail_y += 1
        
        state = decision["system_state"]
        safe_addstr(stdscr, detail_y, details_x + 4, f"Theme: {state.get('theme', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Mode: {state.get('mode', 'N/A')}", curses.color_pair(7))
        detail_y += 1
        safe_addstr(stdscr, detail_y, details_x + 4, f"Version: {state.get('version', 'N/A')}", curses.color_pair(7))
        detail_y += 1
    
    # Navigation info
    nav_info = f"Decision {selected_index + 1} of {len(decisions_list)}"
    safe_addstr(stdscr, height - 5, (width - len(nav_info)) // 2, nav_info, curses.color_pair(5))
    
    # Controls
    controls = "↑↓: Navigate | M: Main View | 7: History | Q: Quit"
    safe_addstr(stdscr, height - 3, (width - len(controls)) // 2, controls, curses.color_pair(3))
    
    # Render status bar
    render_status_bar(stdscr, theme)

# === EXPORT FUNCTIONALITY ===
def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"decisions_{timestamp}.json"
        export_data = {
            "export_info": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "total_decisions": len(decision_history)
            },
            "decisions": [
                {
                    **decision,
                    "timestamp": decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"decisions_{timestamp}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Query", "Verdict", "Session_ID", "Individual_Votes", "Reasoning"])
            
            for decision in decision_history:
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                votes_str = "; ".join([f"{k}: {v}" for k, v in decision.get("individual_votes", {}).items()])
                writer.writerow([
                    timestamp,
                    decision["query"],
                    decision["verdict"],
                    decision.get("session_id", ""),
                    votes_str,
                    decision.get("reasoning", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"decisions_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Version: {VERSION}\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, decision in enumerate(decision_history, 1):
                timestamp = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                f.write(f"DECISION #{i}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Verdict: {decision['verdict']}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                if decision.get("individual_votes"):
                    f.write("Individual Votes:\n")
                    for name, vote in decision["individual_votes"].items():
                        f.write(f"  {name}: {vote}\n")
                
                if decision.get("reasoning"):
                    f.write(f"Reasoning: {decision['reasoning']}\n")
                
                f.write("-" * 80 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    return str(filename)

# === CONSOLE MODE ===
def run_console_mode():
    """Run console mode for direct voting and commands"""
    print("\n" + "="*80)
    print("CONSENSUS SYSTEM - CONSOLE MODE")
    print("="*80)
    print("Commands: vote <query> | export <format> | reload <monolith> | status | quit")
    
    while True:
        try:
            command_input = input("\n>> ").strip()
            
            if not command_input:
                continue
                
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ['quit', 'exit', 'q']:
                break
            
            elif command == "vote":
                if not args:
                    print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                
                add_decision_to_history(query, verdict, reasoning, "console_vote")
                print(f"\nVotes saved to {VOTE_DIR}")
            
            elif command == "status":
                print("\nSYSTEM STATUS:")
                print(f"Version: {VERSION}")
                print(f"Uptime: {time.time() - SYSTEM_HEALTH['uptime']:.1f}s")
                print(f"Total Decisions: {len(decision_history)}")
                print(f"API Status: {SYSTEM_HEALTH.get('api_status', 'unknown')}")
                print(f"TTS Status: {SYSTEM_HEALTH.get('tts_status', 'unknown')}")
                
                print("\nMONOLITH STATUS:")
                for name, config in MODEL_CONFIG.items():
                    status = config.get("status", "unknown")
                    print(f"  {name}: {status}")
            
            elif command == "reload":
                if not args or args.upper() not in MODEL_CONFIG:
                    print("Usage: reload <RATIONALIS|AETERNUM|BELLATOR>")
                    continue
                
                monolith_name = args.upper()
                monolith = Monolith(monolith_name)
                status = monolith.reload_model()
                print(f"{monolith_name} model status: {status}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: vote, status, reload, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

# === DEMO VOTING ===
def demo_voting_process():
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    add_notification(f"Starting demo vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    CONFIG["system_mode"] = "VOTING"
    
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        responses = [
            "APPROVE - Operational parameters fall within acceptable risk thresholds",
            "DENY - Current threat assessment indicates elevated risk levels",
            "APPROVE - Historical analysis supports favorable outcome probability",
            "DENY - Resource allocation conflicts with existing priorities",
            "APPROVE - Strategic objectives align with proposed course of action",
            "DENY - Insufficient intelligence for confident risk assessment"
        ]
        result = random.choice(responses)
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    verdict = calculate_consensus(VOTES)
    
    if verdict == "APPROVE":
        CONFIG["system_mode"] = "AUTHORIZED"
    elif verdict == "DENY":
        CONFIG["system_mode"] = "DENIED"
    else:
        CONFIG["system_mode"] = "DEADLOCK"
    
    reasoning_parts = []
    for name, vote in VOTES.items():
        reasoning_parts.append(f"{name}: {vote}")
    reasoning = "; ".join(reasoning_parts)
    
    add_decision_to_history(query, verdict, reasoning, "demo_vote")
    summarize_consensus(verdict)
    add_notification(f"Consensus reached: {verdict}", "success")
    log(f"RESPONSE: {verdict}")
    
    def reset_mode():
        time.sleep(5)
        CONFIG["system_mode"] = "READY"
    
    threading.Thread(target=reset_mode, daemon=True).start()

# === INPUT HANDLING ===
def handle_input(stdscr, key: int, current_state: dict) -> bool:
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('9'):
        CONFIG["current_view"] = "config"
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
    elif key in (ord('v'), ord('V')):
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        return False  # Exit to console mode
    elif key in (ord('r'), ord('R')) and CONFIG["current_view"] == "config":
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        add_notification("Diagnostics refreshed", "info")
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)      # Red
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # White
    
    ui_state = {
        "last_health_update": 0
    }
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    if curses.has_colors():
                        curses.init_pair(1, curses.COLOR_RED, -1)
                        curses.init_pair(2, curses.COLOR_GREEN, -1)
                        curses.init_pair(3, curses.COLOR_YELLOW, -1)
                        curses.init_pair(4, curses.COLOR_BLUE, -1)
                        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
                        curses.init_pair(6, curses.COLOR_CYAN, -1)
                        curses.init_pair(7, curses.COLOR_WHITE, -1)
                else:
                    running = handle_input(stdscr, key, ui_state)
            
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                
                if current_time - ui_state["last_health_update"] > 5:
                    update_system_health()
                    ui_state["last_health_update"] = current_time
                
                current_view = CONFIG.get("current_view", "main")
                theme = CONFIG.get("theme", "military")
                
                if current_view == "config":
                    render_config_screen(stdscr, theme)
                else:
                    render_main_screen(stdscr, theme)
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"Error in main loop: {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        log(f"CONSENSUS System v{VERSION} starting up", "STARTUP")
        
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. GUI Mode (Full interface with diagnostics)")
        print("2. Console Mode (Direct command-line operation)")
        print("3. Exit")
        
        while True:
            choice = input("\nEnter choice (1, 2, or 3): ").strip()
            
            if choice == "1":
                log("Starting GUI mode", "MODE")
                add_notification("GUI mode initialized", "info")
                curses.wrapper(run_ui_loop)
                break
            elif choice == "2":
                log("Starting console mode", "MODE")
                run_console_mode()
                break
            elif choice == "3":
                log("User requested exit", "MODE")
                print("Exiting CONSENSUS System...")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
    except Exception as e:
        error_msg = f"Fatal error: {e}"
        print(error_msg)
        log(error_msg, "FATAL")
        sys.exit(1)
    finally:
        uptime = time.time() - SYSTEM_HEALTH["uptime"]
        log(f"CONSENSUS System shutting down after {uptime:.1f}s uptime", "SHUTDOWN")
        print("\n🟢 CONSENSUS System terminated gracefully")
        print(f"📊 Session summary: {len(decision_history)} decisions processed")
        if decision_history:
            last_decision = decision_history[-1]
            print(f"🕒 Last decision: {last_decision['timestamp'].strftime('%H:%M:%S')} - {last_decision['verdict']}")

if __name__ == "__main__":
    main()("Usage: vote <your question>")
                    continue
                    
                query = args
                log(f"COMMAND: console_vote -> {query}")
                add_notification(f"Console vote: {query}", "info")
                
                # Clear previous votes
                VOTES.clear()
                
                # Create monoliths and vote
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                # Calculate consensus
                verdict = calculate_consensus(VOTES)
                
                # Generate reasoning summary
                reasoning_parts = []
                for name, vote in VOTES.items():
                    reasoning_parts.append(f"{name}: {vote}")
                reasoning = "; ".join(reasoning_parts)
                
                # Display verdict
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                
                # Log decision
                add_decision_to_history(query, verdict, reasoning, "console_vote")
                
                print(f"\nVotes saved to {VOTE_DIR}")
                print("Full trace available in logs.")
            
            elif command == "export":
                if not args or args.lower() not in ["json", "csv", "txt"]:
                    print("Usage: export <json|csv|txt>")
                    continue
                
                try:
                    filename = export_decisions(args.lower())
                    print(f"Decisions exported to: {filename}")
                    log(f"Exported decisions to {filename}")
                except Exception as e:
                    print(f"Export failed: {e}")
                    log(f"Export failed: {e}", "ERROR")
            
            elif command == "reload":
                if not args or args.upper() not in MODEL_CONFIG:
                    print("Usage: reload <RATIONALIS|AETERNUM|BELLATOR>")
                    continue
                
                monolith_name = args.upper()
                monolith = Monolith(monolith_name)
                status = monolith.reload_model()
                print(f"{monolith_name} model status: {status}")
            
            elif command == "status":
                print("\nSYSTEM STATUS:")
                print(f"Version: {VERSION}")
                print(f"Uptime: {time.time() - SYSTEM_HEALTH['uptime']:.1f}s")
                print(f"Total Decisions: {len(decision_history)}")
                print(f"API Status: {SYSTEM_HEALTH.get('api_status', 'unknown')}")
                print(f"TTS Status: {SYSTEM_HEALTH.get('tts_status', 'unknown')}")
                
                print("\nMONOLITH STATUS:")
                for name, config in MODEL_CONFIG.items():
                    status = config.get("status", "unknown")
                    print(f"  {name}: {status}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: vote, export, reload, status, quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", "ERROR")

# === ENHANCED DEMO VOTING PROCESS ===
def demo_voting_process():
    """Demo voting process with full consensus workflow"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    add_notification(f"Starting demo vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    # Update system mode
    CONFIG["system_mode"] = "VOTING"
    
    # Simulate voting
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        # Simulate vote result with more varied responses
        responses = [
            "APPROVE - Operational parameters fall within acceptable risk thresholds",
            "DENY - Current threat assessment indicates elevated risk levels",
            "APPROVE - Historical analysis supports favorable outcome probability",
            "DENY - Resource allocation conflicts with existing priorities",
            "APPROVE - Strategic objectives align with proposed course of action",
            "DENY - Insufficient intelligence for confident risk assessment"
        ]
        result = random.choice(responses)
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    # Calculate consensus
    verdict = calculate_consensus(VOTES)
    
    # Update system mode based on result
    if verdict == "APPROVE":
        CONFIG["system_mode"] = "AUTHORIZED"
    elif verdict == "DENY":
        CONFIG["system_mode"] = "DENIED"
    else:
        CONFIG["system_mode"] = "DEADLOCK"
    
    # Generate reasoning summary
    reasoning_parts = []
    for name, vote in VOTES.items():
        reasoning_parts.append(f"{name}: {vote}")
    reasoning = "; ".join(reasoning_parts)
    
    # Log decision to history
    add_decision_to_history(query, verdict, reasoning, "demo_vote")
    
    # Display final verdict with TTS
    summarize_consensus(verdict)
    
    add_notification(f"Consensus reached: {verdict}", "success")
    log(f"RESPONSE: {verdict}")
    
    # Reset system mode after a delay
    def reset_mode():
        time.sleep(5)
        CONFIG["system_mode"] = "READY"
    
    threading.Thread(target=reset_mode, daemon=True).start()

# === INPUT HANDLING ===
def handle_input(stdscr, key: int, current_state: dict) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
        add_notification(f"Theme changed to {CONFIG['theme'].upper()}", "info")
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('7'):
        CONFIG["current_view"] = "history"
    elif key == ord('9'):
        CONFIG["current_view"] = "config"
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
    elif key in (ord('d'), ord('D')):
        CONFIG["current_view"] = "forensics"
        current_state["forensics_index"] = 0
    elif key in (ord('v'), ord('V')):
        # Trigger voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('r'), ord('R')) and CONFIG["current_view"] == "config":
        # Refresh diagnostics
        update_system_health()
        for name in MODEL_CONFIG:
            check_model_status(name)
        add_notification("Diagnostics refreshed", "info")
    elif CONFIG["current_view"] == "forensics":
        # Handle forensics navigation
        if key == curses.KEY_UP:
            current_state["forensics_index"] = max(0, current_state.get("forensics_index", 0) - 1)
        elif key == curses.KEY_DOWN:
            max_index = len(decision_history) - 1
            current_state["forensics_index"] = min(max_index, current_state.get("forensics_index", 0) + 1)
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    """Main UI loop with enhanced state management"""
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    # Initialize color pairs
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)      # Red
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow
        curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta
        curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan
        curses.init_pair(7, curses.COLOR_WHITE, -1)    # White
    
    # State for UI navigation
    ui_state = {
        "forensics_index": 0,
        "last_health_update": 0
    }
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    # Special handling for console mode
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    # Re-initialize color pairs
                    if curses.has_colors():#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.6.1)
Complete single-file implementation with all features.
"""

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
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional

# === SYSTEM ASCII ART ===
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

CONSENSUS_LOGO = """
╔════════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                          v3.6.1      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# === CONFIGURATION ===
VERSION = "3.6.1"
BUILD_DATE = "2025-05-19"
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
CONFIG_PATH = ARBITER_DIR / "config.json"

CONFIG = {
    "theme": "military",
    "current_view": "main",
    "system_mode": "READY",
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9
    },
    "health_monitoring": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3
    }
}

MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "prompt": "You are RATIONALIS, logic engine of the Tribunal. Analyze the query logically and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "prompt": "You are AETERNUM, market historian and foresight node. Analyze patterns and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "prompt": "You are BELLATOR, tactical risk assessor and security analyst. Evaluate risks and respond with APPROVE or DENY followed by your reasoning.",
        "status": "unknown",
        "last_check": None
    }
}

# Box drawing characters for themes
BOX_CHARS = {
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮"
    },
    "eva": {
        "tl": "▛", "tr": "▜", "bl": "▙", "br": "▟",
        "h": "▀", "v": "▌"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃"
    }
}

# === STATE ===
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
VOTES = {}
SYSTEM_HEALTH = {
    "cpu": 0.0,
    "memory": 0.0,
    "uptime": time.time(),
    "tts_status": "unknown",
    "api_status": "unknown",
    "last_health_check": 0
}

# === UTILITIES ===
def log(msg, level="INFO"):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{t}] [{level}] {msg}"
    log_entries.append(formatted_msg)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{datetime.datetime.now():%Y%m%d}.log", "a") as f:
            f.write(f"{formatted_msg}\n")
    except: 
        pass

def add_notification(message: str, level: str = "info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now()
    })

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                CONFIG.update(json.load(f))
        except Exception as e:
            log(f"Failed to load config: {e}", "ERROR")

def save_config():
    try:
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        log(f"Failed to save config: {e}", "ERROR")

def post_to_model(monolith, query):
    cfg = MODEL_CONFIG[monolith]
    provider = CONFIG["llm_provider"]
    prompt = f"{cfg['prompt']}\n\nQUERY: {query}\n\nVOTE:"
    api = {
        "ollama": "http://localhost:11434/api/generate",
        "lmstudio": "http://localhost:1234/v1/completions"
    }[provider]

    payload = {"model": cfg["model"], "prompt": prompt, "stream": False, "temperature": 0.5, "max_tokens": 512}
    try:
        r = requests.post(api, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data.get("response") or data.get("choices", [{}])[0].get("text", "")
        return f"Error: {r.status_code}"
    except Exception as e:
        return f"Exception: {e}"

def calculate_consensus(votes: Dict[str, str]) -> Optional[str]:
    """Calculate consensus based on votes"""
    approve_count = sum(1 for vote in votes.values() if "APPROVE" in vote.upper())
    deny_count = sum(1 for vote in votes.values() if "DENY" in vote.upper())
    
    if approve_count >= 2:
        return "APPROVE"
    elif deny_count >= 2:
        return "DENY"
    return "DEADLOCK"

# === MONOLITH LOGIC ===
class Monolith:
    def __init__(self, name):
        self.name = name
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        VOTE_DIR.mkdir(parents=True, exist_ok=True)

    def vote(self, query):
        log(f"[{self.name}] Voting on: {query}")
        result = post_to_model(self.name, query).strip()
        VOTES[self.name] = result
        self.write_vote(result)
        return result

    def write_vote(self, result):
        data = {"monolith": self.name, "vote": result, "timestamp": datetime.datetime.now().isoformat()}
        with open(self.vote_file, "w") as f:
            json.dump(data, f, indent=2)

# === BOOT SEQUENCE ===
def boot():
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.0)
    print(CONSENSUS_LOGO)
    time.sleep(0.5)
    print(f"Booting CONSENSUS SYSTEM v{VERSION} — Build {BUILD_DATE}\n")
    steps = ["Loading memory cores", "Validating vote ports", "Activating monoliths"]
    for s in steps:
        print(f"[✓] {s}")
        time.sleep(0.4)
    print("\n▛ SYSTEM READY ▟ — PRESS ENTER TO CONTINUE")
    input()

# === ARBITER VERDICT + TTS ===
def summarize_consensus(verdict: str):
    typed_text = f"FINAL VERDICT: {verdict.upper()}"
    for c in typed_text:
        print(c, end='', flush=True)
        time.sleep(0.04)
    print()
    
    if CONFIG.get("tts", {}).get("enabled"):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            engine.setProperty('rate', CONFIG["tts"].get("voice_rate", 150))
            engine.setProperty('volume', CONFIG["tts"].get("voice_volume", 0.9))
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            log(f"[TTS] Announced verdict: {verdict}")
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3", "WARNING")
        except Exception as e:
            log(f"[TTS Error] {e}", "ERROR")

# === MAIN ENTRY POINT ===
def main():
    try:
        load_config()
        boot()
        
        print("\n" + "="*60)
        print("CONSENSUS SYSTEM - MODE SELECTION")
        print("="*60)
        print("1. Console Mode (Direct voting)")
        print("2. Exit")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Console mode - simplified for testing
            while True:
                query = input("\n>> ENTER QUERY FOR VOTE (or 'quit' to exit):\n> ")
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                    
                log(f"COMMAND: console_vote -> {query}")
                VOTES.clear()
                
                monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
                
                print(f"\nInitiating tribunal vote for: {query}")
                for m in monoliths:
                    print(f"\n[{m.name}] Processing...")
                    result = m.vote(query)
                    print(f"[{m.name}] ➜ {result.strip()}")
                
                verdict = calculate_consensus(VOTES)
                print("\n" + "="*60)
                summarize_consensus(verdict)
                print("="*60)
                print(f"\nVotes saved to {VOTE_DIR}")
        
        else:
            print("Exiting CONSENSUS System...")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()