#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.5.0)
Complete single-file architecture with integrated monolith logic,
EVA theme, decision history tracking, and enhanced TTS system.
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
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                          v3.6.0      ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

# === CONFIGURATION ===
VERSION = "3.6.0"
BUILD_DATE = "2025-05-19"
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
CONFIG_PATH = ARBITER_DIR / "config.json"

CONFIG = {
    "theme": "military",
    "current_view": "main",
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9
    }
}

MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "prompt": "You are RATIONALIS, logic engine of the Tribunal. Analyze the query logically and respond with APPROVE or DENY followed by your reasoning."
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "prompt": "You are AETERNUM, market historian and foresight node. Analyze patterns and respond with APPROVE or DENY followed by your reasoning."
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "prompt": "You are BELLATOR, tactical risk assessor and security analyst. Evaluate risks and respond with APPROVE or DENY followed by your reasoning."
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
decision_history = deque(maxlen=50)
notifications = deque(maxlen=10)
VOTES = {}

# === UTILITIES ===
def log(msg):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entries.append(f"[{t}] {msg}")
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / f"{datetime.datetime.now():%Y%m%d}.log", "a") as f:
            f.write(f"[{t}] {msg}\n")
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
            log(f"Failed to load config: {e}")

def save_config():
    try:
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except Exception as e:
        log(f"Failed to save config: {e}")

def initialize_tts_config():
    """Initialize TTS configuration on first run"""
    if "tts" not in CONFIG:
        CONFIG["tts"] = {
            "enabled": True,
            "engine": "pyttsx3",
            "voice_rate": 150,
            "voice_volume": 0.9
        }
        save_config()
        log("TTS configuration initialized")

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

# === DECISION HISTORY MANAGEMENT ===
def add_decision_to_history(query: str, verdict: str, reasoning: str = None, command_log: str = None):
    """Add a decision to the history with enhanced logging capabilities"""
    timestamp = datetime.datetime.now()
    
    # Create the decision record
    decision = {
        "query": query,
        "verdict": verdict,
        "timestamp": timestamp,
        "reasoning": reasoning or "No reasoning provided",
        "session_id": timestamp.strftime("%Y%m%d_%H%M%S"),
        "individual_votes": dict(VOTES) if VOTES else {},
        "command_origin": command_log
    }
    
    # Add to in-memory history
    decision_history.append(decision)
    
    # Enhanced logging with COMMAND: / RESPONSE: format
    log_entry = f"COMMAND: {query}"
    if command_log:
        log_entry = f"COMMAND: {command_log} -> {query}"
    
    log_entry += f"\nRESPONSE: {verdict}"
    if reasoning:
        log_entry += f"\nREASONING: {reasoning}"
    
    # Log individual monolith votes
    if VOTES:
        vote_summary = ", ".join([f"{name}: {vote}" for name, vote in VOTES.items()])
        log_entry += f"\nINDIVIDUAL_VOTES: {vote_summary}"
    
    log(log_entry)
    add_notification(f"Decision logged: {verdict}", "success")
    
    # Save to persistent storage
    try:
        decision_file = ARBITER_DIR / "decision_history.json"
        decisions = []
        
        # Load existing decisions if file exists
        if decision_file.exists():
            with open(decision_file, 'r') as f:
                decisions = json.load(f)
        
        # Add new decision (with JSON serializable timestamp)
        decision_copy = decision.copy()
        decision_copy["timestamp"] = timestamp.isoformat()
        decisions.append(decision_copy)
        
        # Keep only the last 100 decisions to prevent file bloat
        decisions = decisions[-100:]
        
        # Write back to file
        with open(decision_file, 'w') as f:
            json.dump(decisions, f, indent=2)
            
    except Exception as e:
        log(f"ERROR: Failed to save decision to persistent storage: {e}")

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

# === ARBITER VERDICT + TTS (v3.5.0) ===
def summarize_consensus(verdict: str):
    """Display final verdict with typing effect and TTS output"""
    typed_text = f"FINAL VERDICT: {verdict.upper()}"
    
    # Typing effect for console output
    for c in typed_text:
        print(c, end='', flush=True)
        time.sleep(0.04)
    print()
    
    # TTS Output using pyttsx3 (offline safe)
    if CONFIG.get("tts", {}).get("enabled"):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            
            # Configure voice settings
            voices = engine.getProperty('voices')
            if voices:
                # Try to find a female voice for GLaDOS-like effect
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
            
            # Adjust speech rate for dramatic effect
            engine.setProperty('rate', CONFIG["tts"].get("voice_rate", 150))
            engine.setProperty('volume', CONFIG["tts"].get("voice_volume", 0.9))
            
            # Generate TTS
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            
            log(f"[TTS] Announced verdict: {verdict}")
            
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3")
        except Exception as e:
            log(f"[TTS Error] {e}")

# === THEME CYCLING ===
def cycle_theme():
    themes = list(BOX_CHARS.keys())
    current = CONFIG.get("theme", "military")
    next_index = (themes.index(current) + 1) % len(themes)
    CONFIG["theme"] = themes[next_index]
    add_notification(f"Theme changed to {CONFIG['theme'].upper()}", "info")
    log(f"Theme changed to {CONFIG['theme']}")
    save_config()

# === UI UTILITIES ===
def safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0):
    """Safely add a string to the screen, avoiding errors at screen borders"""
    try:
        height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        
        max_len = width - x
        if max_len <= 0:
            return
        
        display_text = str(text)[:max_len]
        stdscr.addstr(y, x, display_text, attr)
    except curses.error:
        pass

def draw_box(stdscr, y: int, x: int, height: int, width: int, theme: str = "military"):
    """Draw a box using theme-appropriate characters"""
    chars = BOX_CHARS.get(theme, BOX_CHARS["military"])
    
    # Draw corners
    safe_addstr(stdscr, y, x, chars["tl"])
    safe_addstr(stdscr, y, x + width - 1, chars["tr"])
    safe_addstr(stdscr, y + height - 1, x, chars["bl"])
    safe_addstr(stdscr, y + height - 1, x + width - 1, chars["br"])
    
    # Draw horizontal lines
    for i in range(1, width - 1):
        safe_addstr(stdscr, y, x + i, chars["h"])
        safe_addstr(stdscr, y + height - 1, x + i, chars["h"])
    
    # Draw vertical lines
    for i in range(1, height - 1):
        safe_addstr(stdscr, y + i, x, chars["v"])
        safe_addstr(stdscr, y + i, x + width - 1, chars["v"])

# === UI RENDERING ===
def render_main_screen(stdscr, theme: str):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status
    status_y = 3
    safe_addstr(stdscr, status_y, 2, f"MODE: READY", curses.color_pair(2))
    safe_addstr(stdscr, status_y, width - 20, f"THEME: {CONFIG['theme'].upper()}", curses.color_pair(3))
    
    # Monolith status
    mono_y = 5
    safe_addstr(stdscr, mono_y, 2, "MONOLITH STATUS:", curses.A_BOLD)
    monoliths = ["RATIONALIS", "AETERNUM", "BELLATOR"]
    for i, name in enumerate(monoliths):
        safe_addstr(stdscr, mono_y + 1 + i, 4, f"{name}: READY", curses.color_pair(2))
    
    # Recent decisions
    if decision_history:
        recent_y = mono_y + len(monoliths) + 2
        safe_addstr(stdscr, recent_y, 2, "RECENT DECISIONS:", curses.A_BOLD)
        for i, decision in enumerate(list(decision_history)[-3:]):
            verdict_color = 2 if decision["verdict"] == "APPROVE" else 1 if decision["verdict"] == "DENY" else 3
            timestamp = decision["timestamp"].strftime("%H:%M")
            decision_text = f"[{timestamp}] {decision['verdict']}: {decision['query'][:40]}..."
            safe_addstr(stdscr, recent_y + 1 + i, 4, decision_text, curses.color_pair(verdict_color))
    
    # Notifications
    if notifications:
        notif_y = height - 6
        safe_addstr(stdscr, notif_y, 2, "NOTIFICATIONS:", curses.A_BOLD)
        for i, notif in enumerate(list(notifications)[-3:]):
            color = 2 if notif["level"] == "success" else 1 if notif["level"] == "error" else 3
            safe_addstr(stdscr, notif_y + 1 + i, 4, notif["message"], curses.color_pair(color))
    
    # Controls
    controls = "Q: Quit | S: Cycle Theme (MIL→TARS→EVA→WH40K→HELL) | V: Vote | 7: History | C: Console"
    safe_addstr(stdscr, height - 2, (width - len(controls)) // 2, controls, curses.color_pair(7))

def render_decision_history_screen(stdscr, theme: str):
    """Render the decision history screen (Key 7)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS DECISION HISTORY - TACTICAL REVIEW"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Draw border
    draw_box(stdscr, 3, 1, height - 6, width - 2, theme)
    
    # Column headers
    headers_y = 4
    safe_addstr(stdscr, headers_y, 3, "TIMESTAMP", curses.A_BOLD)
    safe_addstr(stdscr, headers_y, 15, "VERDICT", curses.A_BOLD)
    safe_addstr(stdscr, headers_y, 25, "QUERY", curses.A_BOLD)
    safe_addstr(stdscr, headers_y, width - 15, "VOTES", curses.A_BOLD)
    
    # Decision entries
    start_y = headers_y + 2
    max_entries = height - 8
    
    for i, decision in enumerate(list(decision_history)[-max_entries:]):
        if start_y + i >= height - 4:
            break
            
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
        
        # Individual votes
        votes_text = ""
        if decision.get("individual_votes"):
            vote_summary = []
            for name, vote in decision["individual_votes"].items():
                vote_short = "A" if "APPROVE" in vote.upper() else "D" if "DENY" in vote.upper() else "?"
                vote_summary.append(f"{name[0]}{vote_short}")
            votes_text = " ".join(vote_summary)
        
        safe_addstr(stdscr, y, width - 15, votes_text, curses.color_pair(4))
    
    # Footer stats
    total_decisions = len(decision_history)
    approve_count = sum(1 for d in decision_history if d["verdict"] == "APPROVE")
    deny_count = sum(1 for d in decision_history if d["verdict"] == "DENY")
    deadlock_count = sum(1 for d in decision_history if d["verdict"] == "DEADLOCK")
    
    stats_y = height - 3
    stats_text = f"Total: {total_decisions} | Approved: {approve_count} | Denied: {deny_count} | Deadlocks: {deadlock_count}"
    safe_addstr(stdscr, stats_y, (width - len(stats_text)) // 2, stats_text, curses.color_pair(7))
    
    # Controls
    controls = "M: Main View | Q: Quit"
    safe_addstr(stdscr, height - 1, (width - len(controls)) // 2, controls, curses.color_pair(3))

# === CONSOLE MODE ===
def run_console_mode():
    """Run console mode for direct voting"""
    print("\n" + "="*80)
    print("CONSENSUS SYSTEM - CONSOLE MODE")
    print("="*80)
    
    while True:
        query = input("\n>> ENTER QUERY FOR VOTE (or 'quit' to exit):\n> ")
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        log(f"COMMAND: console_vote -> {query}")
        add_notification(f"Starting console vote: {query}", "info")
        
        # Clear previous votes
        VOTES.clear()
        
        # Create monoliths and vote
        monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
        
        print("\nInitiating tribunal vote...")
        for m in monoliths:
            print(f"\n[{m.name}] Processing...")
            out = m.vote(query)
            print(f"[{m.name}] ➜ {out.strip()}")
        
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

# === ENHANCED DEMO VOTING PROCESS ===
def demo_voting_process():
    """Demo voting process with full consensus workflow"""
    query = f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?"
    add_notification(f"Starting vote: {query}", "info")
    log(f"COMMAND: demo_vote -> {query}")
    
    # Simulate voting
    monoliths = [Monolith("RATIONALIS"), Monolith("AETERNUM"), Monolith("BELLATOR")]
    VOTES.clear()
    
    for m in monoliths:
        # Simulate vote result
        result = random.choice([
            "APPROVE - Operation parameters are within acceptable range",
            "DENY - Risk assessment indicates unfavorable conditions", 
            "APPROVE - Historical patterns suggest positive outcome",
            "DENY - Current threat level exceeds operational thresholds",
            "APPROVE - Strategic analysis confirms mission viability"
        ])
        VOTES[m.name] = result
        add_notification(f"{m.name} voted", "info")
        log(f"[{m.name}] Vote: {result}")
        time.sleep(0.5)
    
    # Calculate consensus
    verdict = calculate_consensus(VOTES)
    
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

# === INPUT HANDLING ===
def handle_input(stdscr, key: int) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
        add_notification(f"Theme changed to {CONFIG['theme']}", "info")
    elif key in (ord('m'), ord('M')):
        CONFIG["current_view"] = "main"
    elif key == ord('7'):
        CONFIG["current_view"] = "history"
    elif key in (ord('v'), ord('V')):
        # Trigger voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    
    return True

# === MAIN LOOP ===
def run_ui_loop(stdscr):
    """Main UI loop"""
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
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                running = handle_input(stdscr, key)
            
            # Refresh screen periodically
            current_time = time.time()
            if current_time - last_refresh > 0.1:  # Refresh every 100ms
                current_view = CONFIG.get("current_view", "main")
                theme = CONFIG.get("theme", "military")
                
                if current_view == "history":
                    render_decision_history_screen(stdscr, theme)
                else:
                    render_main_screen(stdscr, theme)
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"Error in main loop: {e}")

# === ENTRY POINT ===
def main():
    """Main entry point"""
    try:
        load_config()
        initialize_tts_config()
        ARBITER_DIR.mkdir(parents=True, exist_ok=True)
        
        # Boot sequence
        boot()
        
        # Choose mode
        print("\nSelect mode:")
        print("1. GUI Mode (curses interface)")
        print("2. Console Mode (direct voting)")
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "2":
            run_console_mode()
        else:
            # Start UI
            curses.wrapper(run_ui_loop)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        log(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        log("CONSENSUS System shutdown")
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()