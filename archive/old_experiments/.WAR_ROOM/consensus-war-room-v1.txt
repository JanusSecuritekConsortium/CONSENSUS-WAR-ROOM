#!/usr/bin/env python3
"""
CONSENSUS War Room - Command and Control Interface

Enhanced implementation with NERV cyberpunk aesthetic and advanced features.
A tactical decision system with three monolithic nodes (Rationalis, Aeternum, Bellator) 
and consensus-based decision making capabilities.

Features:
- Multiple visual themes (Military, WH40k, TARS, Helldivers)
- Individual monolith detail screens with specialized data
- Real-time data visualization for each monolith's domain
- Decision history tracking and consensus calculation
- System health monitoring and performance metrics
- Command-line interface with auto-completion and command history
- Support for multiple LLM backends (Ollama, LM Studio)
"""

# Core imports
import curses
import time
import json
import os
import datetime
import threading
import random
import requests
import signal
import sys
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple, Optional, Any, Union
import shutil
import csv
import subprocess

# Optional imports with fallbacks
try:
    import psutil
except ImportError:
    psutil = None

try:
    from ib_insync import *
    ibi = True
except ImportError:
    ibi = None

# System configuration
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")  # Default, can be overridden
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
CONFIG_PATH = ARBITER_DIR / "config.json"

# NERV logo for boot sequence - simplified ASCII version
NERV_LOGO = """
                      _._.o8888888888888888P'.d88888888888888888K,8
    8888888888888888888888boo._:88b 8888888888888888888888888b.`Y8b
    88888888888888888888888888888b.`Yb. d8888888888888888888888888888888b`Yb.
    ___.8888888888888888888888888888888888b`Y8888888888888888888888888888
    CG88888P\"'`8888888888888888888888888MM88P\"'\"Y888K
    \"Y8P\"\"Y88888888888888888888888oo._\"\"\"\"88888b
    8 8888`Y8888888888888888888888oo.8\"Y8888b
    8 8888 ,88888888888888888888888o,8 \"Y8888b
    8 8888\"\"Y8`Y888888888888888888888b.8 \"Y8888
    8888 Y `Y88888888888888888888 \"Y88
    8888 .d `Y8888888888888888888b.d8b. \"8
    .d8888b..d88P `Y8888888888888888888`Y88888888888888b.
    \"Y888P\"\"Y8b. \"Y8888888888888888888888
    888 Y888`Y88888888888888888 d88P
    Y88b `Y8888888888888\"Y88K\" Y88b
    dPY8888888888P888 Y88b Y88dP
    `Y8888888b888 Y88b Y8P
    `Y8888888.d888b. Y88b. Y
    `Y88888`Y88K`Y8'
"""

# Box drawing characters for different themes
BOX_CHARS = {
    "default": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│", "title_l": "┤", "title_r": "├"
    },
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|", "title_l": "|", "title_r": "|"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║", "title_l": "╣", "title_r": "╠"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮", "title_l": "⎮", "title_r": "⎮"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃", "title_l": "┫", "title_r": "┣"
    }
}

# System modes
SYSTEM_MODES = {
    "STANDBY": {"color": 3, "desc": "System idle, awaiting commands"},
    "VOTING": {"color": 6, "desc": "Monoliths deliberating on proposal"},
    "CONSENSUS": {"color": 2, "desc": "Agreement reached, executing commands"},
    "DEADLOCK": {"color": 1, "desc": "No consensus reached, requiring override"},
    "ERROR": {"color": 1, "desc": "System error detected, manual intervention required"},
    "MAINTENANCE": {"color": 5, "desc": "System undergoing maintenance operations"},
    "CRITICAL": {"color": 1, "desc": "CRITICAL operations mode, high priority"}
}

# Define monoliths
MONOLITHS = {
    "RATIONALIS": {
        "id": 1,
        "desc": "Logical analysis and rationality assessment",
        "vote_path": VOTE_DIR / "rationalis_vote.json",
        "color": 4,  # Blue
        "thinking_phrases": [
            "Evaluating logical consistency...",
            "Analyzing decision tree branches...",
            "Calculating expected utility...",
            "Assessing probabilistic outcomes...",
            "Verifying axioms and premises..."
        ],
        "status": "offline"
    },
    "AETERNUM": {
        "id": 2,
        "desc": "Pattern recognition and historical context",
        "vote_path": VOTE_DIR / "aeternum_vote.json",
        "color": 5,  # Magenta/Cyan
        "thinking_phrases": [
            "Correlating historical patterns...",
            "Accessing pattern database...",
            "Calculating similarity indices...",
            "Projecting trend trajectories...",
            "Analyzing cyclical behaviors..."
        ],
        "status": "offline"
    },
    "BELLATOR": {
        "id": 3,
        "desc": "Tactical assessment and execution planning",
        "vote_path": VOTE_DIR / "bellator_vote.json",
        "color": 2,  # Green
        "thinking_phrases": [
            "Mapping strategic terrain...",
            "Evaluating tactical options...",
            "Projecting adversarial responses...",
            "Calculating risk-reward ratios...",
            "Simulating execution pathways..."
        ],
        "status": "offline"
    }
}

# LLM Provider settings - can be "ollama" or "lmstudio"
LLM_PROVIDER = "ollama"  # Default provider

# Provider endpoints
PROVIDER_ENDPOINTS = {
    "ollama": {
        "api_url": "http://localhost:11434/api/generate",
        "status_endpoint": "http://localhost:11434/api/tags"
    },
    "lmstudio": {
        "api_url": "http://localhost:1234/v1/completions",
        "status_endpoint": "http://localhost:1234/v1/models"
    }
}

# Model configuration for each monolith
MODEL_CONFIG = {
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "engine": LLM_PROVIDER,
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are RATIONALIS, a logical reasoning assistant focused on organization and rational analysis.",
        "parameters": {
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    },
    "AETERNUM": {
        "model": "llama3:70b",
        "engine": LLM_PROVIDER, 
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are AETERNUM, a financial analysis AI focused on Interactive Brokers operations, market analysis, and portfolio management.",
        "parameters": {
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "engine": LLM_PROVIDER,
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are BELLATOR, a tactical and strategic analyst focused on identifying geopolitical risks and security concerns.",
        "parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    }
}

# Vote colors - consistent across all monoliths
VOTE_COLORS = {
    "APPROVE": 4,  # Green
    "DENY": 6,     # Red
    "PENDING": 7   # White
}

# Status indicators
STATUS_INDICATORS = {
    "online": ("ONLINE", 4),      # Green
    "processing": ("PROCESSING", 5),  # Yellow
    "offline": ("OFFLINE", 6)     # Red
}

# Default configuration
DEFAULT_CONFIG = {
    "theme": "default",
    "animations_enabled": True,
    "animation_speed": 10,  # 1-20 scale
    "system_root": str(SYSTEM_ROOT),
    "debug_mode": False,
    "api_keys": {
        "ibkr": {"enabled": False, "api_key": "", "secret": ""},
        "openai": {"enabled": False, "api_key": ""},
        "anthropic": {"enabled": False, "api_key": ""}
    },
    "model_settings": {
        "rationalis": "claude-3-opus-20240229",
        "aeternum": "gpt-4-turbo",
        "bellator": "claude-3-sonnet-20240229"
    },
    "vote_timeout": 30,  # seconds
    "auto_refresh": True,
    "refresh_interval": 5,  # seconds
    "command_history_size": 50,
    "max_log_entries": 1000,
    "panel_sizes": {
        "monolith_height": 8,
        "command_height": 3,
        "status_height": 3
    }
}

# Light/Dark mode color schemes
COLOR_SCHEMES = {
    "dark": {
        "background": -1,  # Default terminal background
        "text": 7,         # White text
        "highlight": 2,    # Blue highlights
        "success": 4,      # Green for success
        "warning": 5,      # Yellow for warnings
        "error": 6,        # Red for errors
    },
    "light": {
        "background": 7,   # White background
        "text": 0,         # Black text
        "highlight": 2,    # Blue highlights
        "success": 4,      # Green for success
        "warning": 5,      # Yellow for warnings
        "error": 6,        # Red for errors
    }
}
current_color_scheme = "dark"

# Query templates
QUERY_TEMPLATES = {
    "finance": "Analyze market conditions for {symbol} and recommend investment action.",
    "security": "Evaluate security implications of {action} regarding {target}.",
    "logical": "Determine optimal approach for {goal} given constraints {constraints}.",
    "general": "Should we proceed with {action}?",
    "critical": "Authorize emergency protocol {protocol_number} for {situation}."
}

# Monolith-specific data structures - will be populated with live data
MONOLITH_DATA = {
    "BELLATOR": {
        "defcon_level": 4,
        "threat_alerts": [],
        "strategic_analysis": [],
        "security_news": [],
        "last_updated": None
    },
    "AETERNUM": {
        "market_indices": {},
        "crypto_prices": {},
        "portfolio_performance": {},
        "economic_indicators": {},
        "last_updated": None
    },
    "RATIONALIS": {
        "system_logs": [],
        "logic_patterns": {},
        "analysis_metrics": {},
        "efficiency_rating": 0.0,
        "last_updated": None
    },
    "ARBITER": {
        "agenda": [],
        "pending_decisions": [],
        "system_status": {},
        "balance_metrics": {},
        "last_updated": None
    }
}

# Global state
CONFIG = DEFAULT_CONFIG.copy()
CURRENT_VIEW = "main"  # main, rationalis, aeternum, bellator, logs, config, help
CURRENT_MODE = "STANDBY"
COMMAND_HISTORY = deque(maxlen=50)
LOG_ENTRIES = deque(maxlen=1000)
ANIMATION_RUNNING = {}
IBKR_CONNECTED = False
ib = None
VOTE_PROCESS = None

# For verdict typing animation
verdict_display_text = ""
verdict_display_length = 0
verdict_full_text = ""
last_verdict_update = 0

# Add a global dictionary to track model status and resources
MODEL_STATUS = {
    "RATIONALIS": {"status": "unknown", "memory_usage": 0, "loading": False},
    "AETERNUM": {"status": "unknown", "memory_usage": 0, "loading": False},
    "BELLATOR": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# System health metrics
SYSTEM_HEALTH = {
    "cpu": 0.0,      # Percentage
    "memory": 0.0,   # Percentage
    "disk": 0.0,     # Percentage
    "network": 0.0,  # Usage in Mbps
    "temperature": 0.0,  # Celsius
    "start_time": time.time(),
    "response_times": deque(maxlen=50),  # For plotting response time graph
    "avg_response_time": 0
}

# Decision history
decision_history = deque(maxlen=10)  # Store last 10 decisions

# Notification system
notifications = deque(maxlen=5)  # Last 5 notifications
notification_colors = {
    "info": 7,      # White
    "success": 4,   # Green
    "warning": 5,   # Yellow
    "error": 6      # Red
}

# Command line state
command_buffer = ""
command_history_index = 0
command_output = ""
input_mode = False
auto_complete_suggestions = []
auto_complete_index = 0

# UI style settings
STYLE = {
    "theme": "military",  # Options: "military", "wh40k", "tars", "helldivers"
    "show_status": True,
    "interactive": True,
    "animated_text": True,
    "show_notifications": True,
    "show_history": True,
    "show_system_health": True,
    "show_response_time_graph": True,
    "enable_autocomplete": True
}

# For help page navigation
help_page = 1

# Initialize system
def init_system():
    """Initialize the CONSENSUS system directories and configuration"""
    global CONFIG
    
    # Create system directories
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Load or create configuration
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                loaded_config = json.load(f)
                # Update with new values while preserving user settings
                for key, value in loaded_config.items():
                    if key in CONFIG:
                        if isinstance(value, dict) and isinstance(CONFIG[key], dict):
                            CONFIG[key].update(value)
                        else:
                            CONFIG[key] = value
        except Exception as e:
            log_entry(f"Error loading configuration: {str(e)}", "ERROR")
    
    # Save configuration
    save_config()

def save_config():
    """Save current configuration to disk"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        log_entry(f"Error saving configuration: {str(e)}", "ERROR")

def log_entry(message, level="INFO"):
    """Add an entry to the system log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    LOG_ENTRIES.append(entry)
    
    # Also save to disk
    try:
        log_path = LOG_DIR / f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except Exception as e:
        # Can't write to log file, but can't log that error either
        pass

def add_notification(message, level="info"):
    """Add a notification to the notification queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now(),
        "seen": False
    })

def add_decision_to_history(query, verdict, reasoning=None):
    """Add a decision to the history"""
    decision_history.append({
        "query": query,
        "verdict": verdict,
        "timestamp": datetime.datetime.now(),
        "reasoning": reasoning or "No reasoning provided"
    })

# UI Rendering Functions
def setup_colors():
    """Initialize color pairs"""
    curses.start_color()
    curses.use_default_colors()
    
    # Base colors
    curses.init_pair(1, curses.COLOR_RED, -1)      # Red (error, warning)
    curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green (success)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow (standby)
    curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue (info)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta (special)
    curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan (processing)
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # White (normal text)
    
    # Highlighted backgrounds
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Selected
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)     # Error bg
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_GREEN)  # Success bg
    curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Light mode text
    curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Dark mode highlight
    curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_RED)    # Alert background
    curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Success background
    curses.init_pair(15, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Command input

def render_boot_sequence(stdscr):
    """Render the boot sequence animation with NERV logo"""
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw NERV logo in red
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    for i, line in enumerate(NERV_LOGO.split('\n')):
        if i < height:
            safe_addstr(stdscr, i, max(0, (width - len(line)) // 2), line[:width])
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    
    # Display version information below the logo
    version_text = f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"
    safe_addstr(stdscr, len(NERV_LOGO.split('\n')) + 1, (width - len(version_text)) // 2, version_text, curses.color_pair(6) | curses.A_BOLD)
    
    stdscr.refresh()
    time.sleep(1.5)
    
    # Add boot text at the bottom
    boot_messages = [
        "INITIALIZING CONSENSUS WAR ROOM",
        "LOADING TACTICAL DECISION SYSTEM...",
        "CONFIGURING MONOLITHIC NODES...",
        "ESTABLISHING ARBITER COORDINATION LAYER...",
        "LOADING MODEL PARAMETERS...",
        "INITIALIZING NETWORK INTERFACES...",
        "SETTING UP SECURITY PROTOCOLS...",
        "LOADING USER INTERFACE...",
        "CONSENSUS SYSTEM READY"
    ]
    
    for i, message in enumerate(boot_messages):
        # Show the message at the bottom
        bottom_y = height - 5
        message_x = (width - len(message)) // 2
        
        # Clear previous message
        safe_addstr(stdscr, bottom_y, 0, " " * width)
        
        # Show new message
        stdscr.attron(curses.color_pair(7))
        safe_addstr(stdscr, bottom_y, message_x, message)
        stdscr.attroff(curses.color_pair(7))
        
        # Show progress bar
        progress_width = 20
        progress = "█" * (i + 1) + "░" * (len(boot_messages) - i - 1)
        progress_x = (width - progress_width) // 2
        
        safe_addstr(stdscr, bottom_y + 2, progress_x, progress)
        
        stdscr.refresh()
        time.sleep(0.5)
    
    time.sleep(1)

def draw_box(stdscr, y, x, height, width, title="", theme="default"):
    """Draw a themed box with title"""
    box_chars = BOX_CHARS.get(theme, BOX_CHARS["default"])
    
    # Draw corners
    safe_addstr(stdscr, y, x, box_chars["tl"])
    safe_addstr(stdscr, y, x + width - 1, box_chars["tr"])
    safe_addstr(stdscr, y + height - 1, x, box_chars["bl"])
    safe_addstr(stdscr, y + height - 1, x + width - 1, box_chars["br"])
    
    # Draw horizontal lines
    for i in range(1, width - 1):
        safe_addstr(stdscr, y, x + i, box_chars["h"])
        safe_addstr(stdscr, y + height - 1, x + i, box_chars["h"])
    
    # Draw vertical lines
    for i in range(1, height - 1):
        safe_addstr(stdscr, y + i, x, box_chars["v"])
        safe_addstr(stdscr, y + i, x + width - 1, box_chars["v"])
    
    # Draw title if provided
    if title:
        title_start = x + 2
        if title_start + len(title) + 4 < x + width:
            safe_addstr(stdscr, y, title_start, box_chars["title_r"])
            safe_addstr(stdscr, y, title_start + 1, " " + title + " ")
            safe_addstr(stdscr, y, title_start + len(title) + 3, box_chars["title_l"])

def render_monolith_panels(stdscr, theme, height, width):
    """Render monolith panels with theme-specific styling"""
    monolith_height = CONFIG["panel_sizes"]["monolith_height"]
    panel_y = 2  # Start after header
    
    # Calculate widths and positions
    panel_width = (width - 8) // 3  # Divide width into 3 panels with spacing
    
    for i, (name, info) in enumerate(MONOLITHS.items()):
        panel_x = 2 + i * (panel_width + 2)  # Add spacing between panels
        
        # Get vote information
        vote_info = get_vote_info(info['vote_path'])
        
        # Draw box
        stdscr.attron(curses.color_pair(info["color"]))
        draw_box(stdscr, panel_y, panel_x, monolith_height, panel_width, name, theme)
        stdscr.attroff(curses.color_pair(info["color"]))
        
        # Display monolith description
        safe_addstr(stdscr, panel_y + 1, panel_x + 2, info["desc"][:panel_width-4])
        
        # Display vote status
        if vote_info:
            # Display vote
            vote_str = f"VERDICT: {vote_info.get('vote', 'PENDING')}"
            stdscr.attron(curses.A_BOLD)
            safe_addstr(stdscr, panel_y + 3, panel_x + 2, vote_str)
            stdscr.attroff(curses.A_BOLD)
            
            # Display reasoning, truncated to fit
            reason = vote_info.get('reasoning', '')
            max_reason_length = (monolith_height - 5) * (panel_width - 4)
            
            if len(reason) > max_reason_length:
                reason = reason[:max_reason_length - 3] + "..."
                
            # Split reason into lines to fit panel width
            y_offset = 0
            for i in range(0, len(reason), panel_width - 4):
                if panel_y + 4 + y_offset < panel_y + monolith_height - 1:
                    safe_addstr(stdscr, panel_y + 4 + y_offset, panel_x + 2, reason[i:i+panel_width-4])
                    y_offset += 1
        else:
            if CURRENT_MODE == "VOTING":
                # Show thinking animation
                phrase = random.choice(info["thinking_phrases"])
                safe_addstr(stdscr, panel_y + 3, panel_x + 2, phrase)
            else:
                safe_addstr(stdscr, panel_y + 3, panel_x + 2, "AWAITING INPUT")
    
    return panel_y + monolith_height

def render_arbiter_panel(stdscr, theme, height, width, y_start):
    """Render the ARBITER coordination panel"""
    panel_height = 6
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after monolith panels
    
    # Draw box
    stdscr.attron(curses.color_pair(6))  # Cyan for ARBITER
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "ARBITER", theme)
    stdscr.attroff(curses.color_pair(6))
    
    # Display consensus status
    consensus_info = get_consensus_info()
    
    mode_color = SYSTEM_MODES[CURRENT_MODE]["color"]
    stdscr.attron(curses.color_pair(mode_color) | curses.A_BOLD)
    status_str = f"SYSTEM MODE: {CURRENT_MODE}"
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, status_str)
    stdscr.attroff(curses.color_pair(mode_color) | curses.A_BOLD)
    
    # Display description
    safe_addstr(stdscr, panel_y + 1, panel_x + len(status_str) + 4, f"- {SYSTEM_MODES[CURRENT_MODE]['desc']}")
    
    # Display vote summary
    if consensus_info:
        votes_str = "VOTES: "
        for name, vote in consensus_info.get("votes", {}).items():
            votes_str += f"{name}: {vote} | "
        
        safe_addstr(stdscr, panel_y + 3, panel_x + 2, votes_str)
        
        # Display consensus decision
        decision = consensus_info.get("decision", "PENDING")
        stdscr.attron(curses.A_BOLD)
        safe_addstr(stdscr, panel_y + 4, panel_x + 2, f"FINAL VERDICT: {decision}")
        stdscr.attroff(curses.A_BOLD)
    else:
        safe_addstr(stdscr, panel_y + 3, panel_x + 2, "NO ACTIVE PROPOSAL")
    
    return panel_y + panel_height

def render_command_panel(stdscr, theme, height, width, y_start):
    """Render the command input panel"""
    panel_height = CONFIG["panel_sizes"]["command_height"]
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after previous panel
    
    # Draw box
    stdscr.attron(curses.color_pair(7))
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "COMMAND", theme)
    stdscr.attroff(curses.color_pair(7))
    
    # Command prompt
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, "> ")
    
    # Leave space for user input
    
    return panel_y + panel_height

def render_status_panel(stdscr, theme, height, width, y_start):
    """Render the system status panel"""
    panel_height = CONFIG["panel_sizes"]["status_height"]
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after previous panel
    
    # Draw box
    stdscr.attron(curses.color_pair(3))
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "SYSTEM STATUS", theme)
    stdscr.attroff(curses.color_pair(3))
    
    # Display current time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# Display current time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, f"TIME: {current_time}")
    
    # Display version
    version_text = f"VERSION: {VERSION}"
    safe_addstr(stdscr, panel_y + 1, panel_width - len(version_text), version_text, curses.color_pair(6))
    
    # Display system resources
    resources_str = f"CPU: {SYSTEM_HEALTH['cpu']:.1f}% | MEM: {SYSTEM_HEALTH['memory']:.1f}% | DISK: {SYSTEM_HEALTH['disk']:.1f}% | NET: {SYSTEM_HEALTH['network']:.1f} Mbps"
    safe_addstr(stdscr, panel_y + 1, panel_x + len(current_time) + 8, resources_str)
    
    # Display key commands
    help_str = "NAV: [1-4] Monoliths | [5] Main | [7] Logs | [9] Config | [/] Command | [ESC] Exit"
    safe_addstr(stdscr, panel_y + 2, panel_x + 2, help_str[:panel_width-4])
    
    return panel_y + panel_height

def render_notifications(stdscr, height, width):
    """Render notification panel"""
    if not STYLE["show_notifications"] or not notifications:
        return
    
    # Position at top right
    panel_width = min(50, width // 2)
    panel_height = min(len(notifications) + 2, 7)
    panel_x = width - panel_width - 2
    panel_y = 2
    
    # Draw notification box
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "NOTIFICATIONS")
    
    # Display notifications
    for i, notification in enumerate(list(notifications)[-panel_height+2:]):
        if i >= panel_height - 2:
            break
            
        level = notification["level"]
        color = notification_colors.get(level, 7)
        
        # Format timestamp
        time_str = notification["timestamp"].strftime("%H:%M:%S")
        
        # Format notification with truncation if needed
        msg = notification["message"]
        if len(msg) > panel_width - 15:
            msg = msg[:panel_width-18] + "..."
            
        safe_addstr(stdscr, panel_y + i + 1, panel_x + 2, f"{time_str}", curses.color_pair(7))
        safe_addstr(stdscr, panel_y + i + 1, panel_x + 11, msg, curses.color_pair(color))

def render_log_view(stdscr, theme, height, width):
    """Render the log history view"""
    header_height = 2
    stdscr.attron(curses.A_BOLD)
    title = "CONSENSUS SYSTEM LOGS"
    safe_addstr(stdscr, 0, (width - len(title)) // 2, title)
    stdscr.attroff(curses.A_BOLD)
    
    # Draw main log box
    log_height = height - header_height - CONFIG["panel_sizes"]["status_height"] - 3
    log_width = width - 4
    log_x = 2
    log_y = header_height
    
    stdscr.attron(curses.color_pair(7))
    draw_box(stdscr, log_y, log_x, log_height, log_width, "LOG ENTRIES", theme)
    stdscr.attroff(curses.color_pair(7))
    
    # Display log entries, most recent first
    max_entries = log_height - 2
    entries_to_show = list(LOG_ENTRIES)[-max_entries:] if LOG_ENTRIES else []
    
    for i, entry in enumerate(entries_to_show):
        if i < max_entries:
            level = entry["level"]
            level_color = 7  # Default white
            
            if level == "ERROR":
                level_color = 1  # Red
            elif level == "WARNING":
                level_color = 3  # Yellow
            elif level == "SUCCESS":
                level_color = 2  # Green
            
            log_line = f"[{entry['timestamp']}] [{level}] {entry['message']}"
            
            # Truncate if necessary
            if len(log_line) > log_width - 4:
                log_line = log_line[:log_width - 7] + "..."
            
            stdscr.attron(curses.color_pair(level_color))
            safe_addstr(stdscr, log_y + i + 1, log_x + 2, log_line)
            stdscr.attroff(curses.color_pair(level_color))
    
    # Render status panel at bottom
    render_status_panel(stdscr, theme, height, width, log_y + log_height)

def render_bellator_screen(stdscr, theme, height, width):
    """Draw the Bellator monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, height-3):
        blank_line = " " * (width-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
    if not MONOLITH_DATA["BELLATOR"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["BELLATOR"]["last_updated"]).total_seconds() > 60:
        update_bellator_data()
    
    # Header based on theme
    if theme == "military":
        header = "BELLATOR TACTICAL OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "STRATEGOS BELLATOR COMMAND THRONE"
    elif theme == "tars":
        header = "BELLATOR.SECURITY.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH TACTICAL COMMAND"
    else:
        header = "BELLATOR TACTICAL INTERFACE"
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, width//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
    
    # Draw DEFCON level
    defcon = MONOLITH_DATA["BELLATOR"]["defcon_level"]
    defcon_color = 2 if defcon <= 2 else 3 if defcon == 3 else 1  # Green, Yellow, Red
    
    if theme == "military":
        defcon_text = f"DEFENSE CONDITION: DEFCON {defcon}"
    elif theme == "wh40k":
        defcon_text = f"IMPERIUM THREAT LEVEL: VERMILLION {defcon}"
    elif theme == "tars":
        defcon_text = f"SECURITY.CONDITION={defcon}"
    elif theme == "helldivers":
        defcon_text = f"LIBERTY THREAT INDEX: {defcon}"
    else:
        defcon_text = f"THREAT LEVEL: {defcon}"
        
    safe_addstr(stdscr, 3, width//2 - len(defcon_text)//2, defcon_text, 
             curses.A_BOLD | curses.color_pair(defcon_color))
    
    # Draw threat alerts section
    y_pos = 5
    if theme == "military":
        section_header = "[ ACTIVE THREAT ALERTS ]"
    elif theme == "wh40k":
        section_header = "[ ADEPTUS WARNINGS ]"
    elif theme == "tars":
        section_header = "[ THREAT.MONITOR ]"
    elif theme == "helldivers":
        section_header = "[ FREEDOM ALERTS ]"
    else:
        section_header = "[ THREAT ALERTS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, alert in enumerate(MONOLITH_DATA["BELLATOR"]["threat_alerts"]):
        if y_pos + idx < height-5:
            level_color = 2 if alert["level"] == "Low" else 3 if alert["level"] == "Moderate" or alert["level"] == "Elevated" else 1
            alert_text = f"{alert['region']}: {alert['level']} - {alert['description']}"
            safe_addstr(stdscr, y_pos + idx, 4, alert_text, curses.color_pair(level_color))
    
    y_pos += len(MONOLITH_DATA["BELLATOR"]["threat_alerts"]) + 1
    
    # Strategic analysis
    if theme == "military":
        section_header = "[ STRATEGIC ANALYSIS ]"
    elif theme == "wh40k":
        section_header = "[ TACTICAL COGITATION ]"
    elif theme == "tars":
        section_header = "[ ANALYSIS.MATRIX ]"
    elif theme == "helldivers":
        section_header = "[ SUPER EARTH INTELLIGENCE ]"
    else:
        section_header = "[ STRATEGIC ANALYSIS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, analysis in enumerate(MONOLITH_DATA["BELLATOR"]["strategic_analysis"]):
        if y_pos + idx < height-5:
            safe_addstr(stdscr, y_pos + idx, 4, f"- {analysis}")
    
    y_pos += len(MONOLITH_DATA["BELLATOR"]["strategic_analysis"]) + 1
    
    # News items
    if theme == "military":
        section_header = "[ INTELLIGENCE BRIEFING ]"
    elif theme == "wh40k":
        section_header = "[ ASTROPATHIC DISPATCHES ]"
    elif theme == "tars":
        section_header = "[ NEWS.FEED ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRACY BROADCASTS ]"
    else:
        section_header = "[ SECURITY NEWS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, news in enumerate(MONOLITH_DATA["BELLATOR"]["security_news"]):
        if y_pos + idx < height-5:
            news_text = f"{news['title']} - {news['source']} ({news['time']})"
            safe_addstr(stdscr, y_pos + idx, 4, news_text)
    
    # Footer
    if MONOLITH_DATA["BELLATOR"]["last_updated"]:
        update_time = MONOLITH_DATA["BELLATOR"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, height-4, width - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Draw model status
    if MODEL_STATUS["BELLATOR"]["status"] != "unknown":
        model_info = MODEL_CONFIG["BELLATOR"]["model"]
        model_status = MODEL_STATUS["BELLATOR"]["status"].upper()
        model_memory = MODEL_STATUS["BELLATOR"]["memory_usage"]
        
        model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEMORY: {model_memory:.0f}MB"
        status_color = 2 if model_status == "READY" else 3 if model_status == "LOADING" else 1
        safe_addstr(stdscr, height-5, 4, model_str, curses.color_pair(status_color))
    
    # Return to main view instruction
    footer = "Press '2' to return to main view"
    safe_addstr(stdscr, height-3, width//2 - len(footer)//2, footer, curses.A_BOLD)

def render_aeternum_screen(stdscr, theme, height, width):
    """Draw the Aeternum monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, height-3):
        blank_line = " " * (width-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
    if not MONOLITH_DATA["AETERNUM"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["AETERNUM"]["last_updated"]).total_seconds() > 60:
        update_aeternum_data()
    
    # Header based on theme
    if theme == "military":
        header = "AETERNUM FINANCIAL OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "ADMINISTRATUM AETERNUM"
    elif theme == "tars":
        header = "AETERNUM.FINANCE.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH ECONOMIC COMMAND"
    else:
        header = "AETERNUM FINANCIAL INTERFACE"
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, width//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
    
    # Draw market indices
    y_pos = 3
    if theme == "military":
        section_header = "[ MARKET INDICES ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIAL TREASURIUM ]"
    elif theme == "tars":
        section_header = "[ MARKET.MONITOR ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRATIC ECONOMIC INDICES ]"
    else:
        section_header = "[ MARKET INDICES ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indices = MONOLITH_DATA["AETERNUM"]["market_indices"]
    col1_x = 4
    col2_x = width // 2 + 4
    
    idx = 0
    for name, data in indices.items():
        if y_pos + idx//2 < height-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["trend"] == "up" else 1  # Green or Red
            value_str = f"{data['value']:,.2f}"
            change_str = f"{data['change']:+.2f}%"
            
            market_text = f"{name}: {value_str} ({change_str})"
            safe_addstr(stdscr, y_pos + idx//2, x_pos, market_text, curses.color_pair(trend_color))
            idx += 1
    
    y_pos += (idx + 1) // 2 + 1
    
    # Draw cryptocurrency prices
    if theme == "military":
        section_header = "[ CRYPTOCURRENCY MARKET ]"
    elif theme == "wh40k":
        section_header = "[ DIGITAL SCRIP EXCHANGE ]"
    elif theme == "tars":
        section_header = "[ CRYPTO.ASSETS ]"
    elif theme == "helldivers":
        section_header = "[ SUPER EARTH DIGITAL CURRENCY ]"
    else:
        section_header = "[ CRYPTO ASSETS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    crypto = MONOLITH_DATA["AETERNUM"]["crypto_prices"]
    idx = 0
    for name, data in crypto.items():
        if y_pos + idx//2 < height-10:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["change"] > 0 else 1  # Green or Red
            price_str = f"${data['price']:,.2f}"
            change_str = f"{data['change']:+.2f}%"
            
            crypto_text = f"{name}: {price_str} ({change_str}) Cap: {data['market_cap']}"
            safe_addstr(stdscr, y_pos + idx//2, x_pos, crypto_text, curses.color_pair(trend_color))
            idx += 1
    
    y_pos += (idx + 1) // 2 + 1
    
    # Portfolio performance
    if theme == "military":
        section_header = "[ PORTFOLIO PERFORMANCE ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIAL HOLDINGS ]"
    elif theme == "tars":
        section_header = "[ PORTFOLIO.STATUS ]"
    elif theme == "helldivers":
        section_header = "[ PATRIOTIC INVESTMENTS ]"
    else:
        section_header = "[ PORTFOLIO PERFORMANCE ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    portfolio = MONOLITH_DATA["AETERNUM"]["portfolio_performance"]
    
    # Time-based performance
    perf_y = y_pos
    for period, change in [("Daily", portfolio["daily_change"]), 
                           ("Weekly", portfolio["weekly_change"]), 
                           ("Monthly", portfolio["monthly_change"]), 
                           ("Yearly", portfolio["yearly_change"])]:
        if perf_y < height-10:
            change_color = 2 if change > 0 else 1  # Green or Red
            perf_text = f"{period}: {change:+.2f}%"
            safe_addstr(stdscr, perf_y, col1_x, perf_text, curses.color_pair(change_color))
            perf_y += 1
    
    # Top and worst performers
    if y_pos < height-10:
        top_text = f"Top: {', '.join(portfolio['top_performers'])}"
        worst_text = f"Worst: {', '.join(portfolio['worst_performers'])}"
        safe_addstr(stdscr, y_pos, col2_x, top_text, curses.color_pair(2))
        safe_addstr(stdscr, y_pos+1, col2_x, worst_text, curses.color_pair(1))
    
    y_pos += 4
    
    # Economic indicators
    if theme == "military":
        section_header = "[ ECONOMIC INDICATORS ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIUM ECONOMIC AUGURIES ]"
    elif theme == "tars":
        section_header = "[ ECONOMY.METRICS ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRATIC PROSPERITY INDICES ]"
    else:
        section_header = "[ ECONOMIC INDICATORS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indicators = MONOLITH_DATA["AETERNUM"]["economic_indicators"]
    idx = 0
    for name, value in indicators.items():
        if y_pos + idx//3 < height-5:
            column = idx % 3
            x_pos = col1_x + (column * (width // 3))
            
            # Format based on indicator
            if name == "inflation" or name == "unemployment" or name == "fed_rate" or name == "treasury_10y":
                value_str = f"{value:.2f}%"
            elif name == "oil_price":
                value_str = f"${value:.2f}/bbl"
            else:
                value_str = str(value)
            
            # Format name to be more readable
            name_formatted = name.replace("_", " ").title()
            
            indicator_text = f"{name_formatted}: {value_str}"
            safe_addstr(stdscr, y_pos + idx//3, x_pos, indicator_text)
            idx += 1
    
    # Footer
    if MONOLITH_DATA["AETERNUM"]["last_updated"]:
        update_time = MONOLITH_DATA["AETERNUM"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, height-4, width - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Draw model status
    if MODEL_STATUS["AETERNUM"]["status"] != "unknown":
        model_info = MODEL_CONFIG["AETERNUM"]["model"]
        model_status = MODEL_STATUS["AETERNUM"]["status"].upper()
        model_memory = MODEL_STATUS["AETERNUM"]["memory_usage"]
        
        model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEMORY: {model_memory:.0f}MB"
        status_color = 2 if model_status == "READY" else 3 if model_status == "LOADING" else 1
        safe_addstr(stdscr, height-5, 4, model_str, curses.color_pair(status_color))
    
    # Return to main view instruction
    footer = "Press '1' to return to main view"
    safe_addstr(stdscr, height-3, width//2 - len(footer)//2, footer, curses.A_BOLD)

def render_rationalis_screen(stdscr, theme, height, width):
    """Draw the Rationalis monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, height-3):
        blank_line = " " * (width-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
    if not MONOLITH_DATA["RATIONALIS"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["RATIONALIS"]["last_updated"]).total_seconds() > 60:
        update_rationalis_data()
    
    # Header based on theme
    if theme == "military":
        header = "RATIONALIS ANALYTICAL OPERATIONS CENTER"
    elif theme == "wh40k":
        header = "MECHANICUS RATIONALIS LOGIC ENGINE"
    elif theme == "tars":
        header = "RATIONALIS.CORE.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH STRATEGIC ANALYSIS"
    else:
        header = "RATIONALIS LOGICAL INTERFACE"
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, width//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
    
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
    else:
        rating_text = f"LOGICAL EFFICIENCY: {efficiency:.1f}%"
        
    safe_addstr(stdscr, 3, width//2 - len(rating_text)//2, rating_text, 
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
    else:
        section_header = "[ SYSTEM LOGS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    logs = MONOLITH_DATA["RATIONALIS"]["system_logs"]
    for idx, log in enumerate(logs):
        if y_pos + idx < height-12:
            level_color = 2 if log["level"] == "INFO" else 3 if log["level"] == "WARNING" else 1
            log_text = f"[{log['timestamp']}] {log['level']}: {log['message']}"
            safe_addstr(stdscr, y_pos + idx, 4, log_text, curses.color_pair(level_color))
    
    y_pos += len(logs) + 1
    
    # Logic patterns
    if theme == "military":
        section_header = "[ REASONING CAPABILITY METRICS ]"
    elif theme == "wh40k":
        section_header = "[ COGITATION PARAMETERS ]"
    elif theme == "tars":
        section_header = "[ LOGIC.PATTERNS ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRATIC THINKING METRICS ]"
    else:
        section_header = "[ REASONING METRICS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    patterns = MONOLITH_DATA["RATIONALIS"]["logic_patterns"]
    col1_x = 4
    col2_x = width // 2 + 4
    
    idx = 0
    for name, value in patterns.items():
        if y_pos + idx//2 < height-8 and name != "logical_fallacies_detected":
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
            if isinstance(value, float):
                score_color = 2 if value > 0.8 else 3 if value > 0.6 else 1
                value_str = f"{value:.2f}"
            else:
                score_color = 7
                value_str = str(value)
            
            # Format name to be more readable
            name_formatted = name.replace("_", " ").title()
            
            pattern_text = f"{name_formatted}: {value_str}"
            safe_addstr(stdscr, y_pos + idx//2, x_pos, pattern_text, curses.color_pair(score_color))
            idx += 1
    
    # Display fallacies separately
    if "logical_fallacies_detected" in patterns:
        fallacy_text = f"Logical Fallacies Detected: {patterns['logical_fallacies_detected']}"
        safe_addstr(stdscr, y_pos + (idx+1)//2, col1_x, fallacy_text, 
                 curses.color_pair(3 if patterns['logical_fallacies_detected'] < 10 else 1))
    
    y_pos += (idx + 3) // 2 + 1
    
    # Analysis metrics
    if theme == "military":
        section_header = "[ ANALYTICAL PERFORMANCE INDICATORS ]"
    elif theme == "wh40k":
        section_header = "[ RATIONALIS EFFICIENCY METRICS ]"
    elif theme == "tars":
        section_header = "[ ANALYSIS.METRICS ]"
    elif theme == "helldivers":
        section_header = "[ STRATAGEM EFFICIENCY RATINGS ]"
    else:
        section_header = "[ ANALYSIS METRICS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    metrics = MONOLITH_DATA["RATIONALIS"]["analysis_metrics"]
    idx = 0
    for name, value in metrics.items():
        if y_pos + idx//2 < height-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
            if isinstance(value, float):
                score_color = 2 if value > 0.8 else 3 if value > 0.6 else 1
                value_str = f"{value:.2f}"
            else:
                score_color = 7
                value_str = str(value)
            
            # Format name to be more readable
            name_formatted = name.replace("_", " ").title()
            
            metric_text = f"{name_formatted}: {value_str}"
            safe_addstr(stdscr, y_pos + idx//2, x_pos, metric_text, curses.color_pair(score_color))
            idx += 1
    
    # Footer
    if MONOLITH_DATA["RATIONALIS"]["last_updated"]:
        update_time = MONOLITH_DATA["RATIONALIS"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, height-4, width - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Draw model status
    if MODEL_STATUS["RATIONALIS"]["status"] != "unknown":
        model_info = MODEL_CONFIG["RATIONALIS"]["model"]
        model_status = MODEL_STATUS["RATIONALIS"]["status"].upper()
        model_memory = MODEL_STATUS["RATIONALIS"]["memory_usage"]
        
        model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEMORY: {model_memory:.0f}MB"
        status_color = 2 if model_status == "READY" else 3 if model_status == "LOADING" else 1
        safe_addstr(stdscr, height-5, 4, model_str, curses.color_pair(status_color))
    
    # Return to main view instruction
    footer = "Press '3' to return to main view"
    safe_addstr(stdscr, height-3, width//2 - len(footer)//2, footer, curses.A_BOLD)
def render_arbiter_screen(stdscr, theme, height, width):
    """Draw the Arbiter specialized screen"""
    # Create a full-screen view
    for i in range(1, height-3):
        blank_line = " " * (width-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
    if not MONOLITH_DATA["ARBITER"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["ARBITER"]["last_updated"]).total_seconds() > 60:
        update_arbiter_data()
    
    # Header based on theme
    if theme == "military":
        header = "ARBITER COMMAND & CONTROL CENTER"
    elif theme == "wh40k":
        header = "ADEPTUS ARBITER COMMAND THRONE"
    elif theme == "tars":
        header = "ARBITER.MASTER.MODULE"
    elif theme == "helldivers":
        header = "SUPER EARTH HIGH COMMAND"
    else:
        header = "ARBITER CONTROL INTERFACE"
        
    # Draw header with custom color (white bold)
    safe_addstr(stdscr, 1, width//2 - len(header)//2, header, curses.A_BOLD | curses.color_pair(7))
    
    # System status
    y_pos = 3
    status = MONOLITH_DATA["ARBITER"]["system_status"]
    status_text = ""
    
    if theme == "military":
        status_text = f"SYSTEM STATUS: {status['monoliths_online']}/3 MONOLITHS ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
    elif theme == "wh40k":
        status_text = f"MECHANICUS STATUS: {status['monoliths_online']}/3 ACTIVE | ASTROPATH: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
    elif theme == "tars":
        status_text = f"SYSTEM.STATUS: ACTIVE={status['monoliths_online']}/3 COMMS={status['communication_integrity']*100:.1f}% RATE={status['decision_throughput']:.1f}/h"
    elif theme == "helldivers":
        status_text = f"DEMOCRACY STATUS: {status['monoliths_online']}/3 ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | LIBERTY RATE: {status['decision_throughput']:.1f}/h"
    else:
        status_text = f"SYSTEM STATUS: {status['monoliths_online']}/3 ACTIVE | INTEGRITY: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
    
    status_color = 2 if status['monoliths_online'] == 3 else 3 if status['monoliths_online'] >= 2 else 1
    safe_addstr(stdscr, y_pos, width//2 - len(status_text)//2, status_text, curses.A_BOLD | curses.color_pair(status_color))
    
    # Agenda section
    y_pos = 5
    if theme == "military":
        section_header = "[ OPERATIONAL AGENDA ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIAL SCHEDULE ]"
    elif theme == "tars":
        section_header = "[ SCHEDULE.AGENDA ]"
    elif theme == "helldivers":
        section_header = "[ LIBERTY OPERATIONS SCHEDULE ]"
    else:
        section_header = "[ AGENDA ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    agenda = MONOLITH_DATA["ARBITER"]["agenda"]
    for idx, item in enumerate(agenda):
        if y_pos + idx < height-12:
            priority_color = 2 if item["priority"] == "Low" else 3 if item["priority"] == "Medium" else 1
            agenda_text = f"{item['time']} - {item['task']} (Priority: {item['priority']})"
            safe_addstr(stdscr, y_pos + idx, 4, agenda_text, curses.color_pair(priority_color))
    
    y_pos += len(agenda) + 1
    
    # Pending decisions
    if theme == "military":
        section_header = "[ PENDING CONSENSUS DECISIONS ]"
    elif theme == "wh40k":
        section_header = "[ AWAITING IMPERIAL DECREE ]"
    elif theme == "tars":
        section_header = "[ PENDING.DECISIONS ]"
    elif theme == "helldivers":
        section_header = "[ AWAITING DEMOCRATIC CONSENSUS ]"
    else:
        section_header = "[ PENDING DECISIONS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    decisions = MONOLITH_DATA["ARBITER"]["pending_decisions"]
    for idx, decision in enumerate(decisions):
        if y_pos + idx < height-8:
            decision_text = f"Query: \"{decision['query']}\" | Status: {decision['status']}"
            safe_addstr(stdscr, y_pos + idx, 4, decision_text)
    
    y_pos += len(decisions) + 1
    
    # Balance metrics
    if theme == "military":
        section_header = "[ MONOLITH BALANCE METRICS ]"
    elif theme == "wh40k":
        section_header = "[ IMPERIAL TRINITY HARMONY ]"
    elif theme == "tars":
        section_header = "[ BALANCE.METRICS ]"
    elif theme == "helldivers":
        section_header = "[ DEMOCRATIC BALANCE INDICATORS ]"
    else:
        section_header = "[ BALANCE METRICS ]"
        
    safe_addstr(stdscr, y_pos, width//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    balance = MONOLITH_DATA["ARBITER"]["balance_metrics"]
    
    # Draw a balance chart
    if y_pos + 4 < height-6:
        # Draw monolith influence
        rationalis_len = int(balance["rationalis_influence"] * 30)
        aeternum_len = int(balance["aeternum_influence"] * 30)
        bellator_len = int(balance["bellator_influence"] * 30)
        
        safe_addstr(stdscr, y_pos, 4, "Rationalis: ", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
        safe_addstr(stdscr, y_pos, 15, "[" + "#" * rationalis_len + " " * (30 - rationalis_len) + "]", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
        safe_addstr(stdscr, y_pos, 48, f"{balance['rationalis_influence']*100:.1f}%")
        
        safe_addstr(stdscr, y_pos+1, 4, "Aeternum:  ", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
        safe_addstr(stdscr, y_pos+1, 15, "[" + "#" * aeternum_len + " " * (30 - aeternum_len) + "]", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
        safe_addstr(stdscr, y_pos+1, 48, f"{balance['aeternum_influence']*100:.1f}%")
        
        safe_addstr(stdscr, y_pos+2, 4, "Bellator:  ", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
        safe_addstr(stdscr, y_pos+2, 15, "[" + "#" * bellator_len + " " * (30 - bellator_len) + "]", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
        safe_addstr(stdscr, y_pos+2, 48, f"{balance['bellator_influence']*100:.1f}%")
        
        # Consensus and conflict rates
        consensus_color = 2 if balance["consensus_rate"] > 0.7 else 3 if balance["consensus_rate"] > 0.5 else 1
        conflict_color = 2 if balance["conflict_rate"] < 0.3 else 3 if balance["conflict_rate"] < 0.5 else 1
        
        safe_addstr(stdscr, y_pos+4, 4, f"Consensus Rate: {balance['consensus_rate']*100:.1f}%", curses.color_pair(consensus_color))
        safe_addstr(stdscr, y_pos+4, 40, f"Conflict Rate: {balance['conflict_rate']*100:.1f}%", curses.color_pair(conflict_color))
    
    # Footer
    if MONOLITH_DATA["ARBITER"]["last_updated"]:
        update_time = MONOLITH_DATA["ARBITER"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, height-4, width - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '4' to return to main view"
    safe_addstr(stdscr, height-3, width//2 - len(footer)//2, footer, curses.A_BOLD)

def render_help_screen(stdscr, height, width, theme):
    """Draw a comprehensive help screen with all commands"""
    # Create a help overlay
    help_height = height - 6
    help_width = width - 6
    help_y = 3
    help_x = 3
    
    # Clear screen and draw help box
    for i in range(help_y, help_y + help_height):
        blank_line = " " * help_width
        safe_addstr(stdscr, i, help_x, blank_line)
    
    draw_box(stdscr, help_y, help_x, help_height, help_width, "HELP: KEYBOARD SHORTCUTS & COMMANDS", theme)
    
    # Show help content
    current_y = help_y + 2
    
    # Title
    if theme == "military":
        title = "CONSENSUS WAR ROOM - COMMAND REFERENCE"
    elif theme == "wh40k":
        title = "ADEPTUS MECHANICUS - COMMAND PROTOCOLS"
    elif theme == "tars":
        title = "CONSENSUS.OS - COMMAND.LIST"
    elif theme == "helldivers":
        title = "SUPER EARTH COMMAND MANUAL"
    else:
        title = "CONSENSUS SYSTEM - COMMAND REFERENCE"
    
    safe_addstr(stdscr, current_y, help_x + (help_width - len(title)) // 2, title, curses.A_BOLD)
    current_y += 2
    
    # Keyboard shortcuts section
    safe_addstr(stdscr, current_y, help_x + 2, "KEYBOARD SHORTCUTS:", curses.A_BOLD)
    current_y += 1
    
    shortcuts = [
        "Q - Quit the application",
        "M - Toggle system mode (NORMAL/CRITICAL)",
        "R - Refresh display",
        "S - Cycle through styles",
        "I - Enter command input mode",
        "H - Toggle help view",
        "C - Toggle configuration view",
        "D - Toggle decision history view",
        "TAB - Autocomplete commands (in input mode)",
        "ESC - Cancel command (in input mode)",
        "UP/DOWN - Navigate command history"
    ]
    
    for shortcut in shortcuts:
        safe_addstr(stdscr, current_y, help_x + 4, shortcut)
        current_y += 1
    
    current_y += 1
    
    # Command Categories
    command_categories = {
        "SYSTEM COMMANDS:": [
            "critical - Set system to CRITICAL mode",
            "normal - Set system to NORMAL mode",
            "status - Display model status information",
            "health - Toggle system health display",
            "notifications - Toggle notifications panel"
        ],
        "INTERFACE COMMANDS:": [
            "style <theme> - Set interface theme (military/wh40k/tars/helldivers)",
            "dark - Switch to dark mode color scheme",
            "light - Switch to light mode color scheme",
            "help - Show this help screen",
            "config - Show configuration panel",
            "history - Show decision history"
        ],
        "MODEL COMMANDS:": [
            "load <monolith> - Load model for specified monolith",
            "use ollama/lmstudio - Switch LLM provider",
            "vote <monolith> <query> - Generate vote from specific monolith"
        ],
        "OPERATION COMMANDS:": [
            "query <text> - Set active query",
            "consensus - Generate votes from all monoliths",
            "template <name> [params] - Apply query template",
            "export json/csv - Export decision history"
        ],
        "IBKR COMMANDS:": [
            "ibkr connect - Connect to Interactive Brokers",
            "ibkr status - Show IBKR account status",
            "ibkr stock <symbol> - Get stock information"
        ]
    }
    
    # Determine if we need pagination
    total_lines = sum(len(commands) + 2 for commands in command_categories.values())
    if current_y + total_lines > help_y + help_height - 3:
        # Use pagination
        page = 1
        max_page = 2
        
        # Page indicator
        page_text = f"Page {help_page}/{max_page} (Press SPACE for next page)"
        safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(page_text)) // 2, 
                   page_text, curses.A_BOLD)
        
        if help_page == 1:
            # Show first half of commands
            count = 0
            for category, commands in list(command_categories.items())[:3]:
                safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
                current_y += 1
                
                for cmd in commands:
                    safe_addstr(stdscr, current_y, help_x + 4, cmd)
                    current_y += 1
                    count += 1
                
                current_y += 1
        else:
            # Show second half of commands
            for category, commands in list(command_categories.items())[3:]:
                safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
                current_y += 1
                
                for cmd in commands:
                    safe_addstr(stdscr, current_y, help_x + 4, cmd)
                    current_y += 1
                
                current_y += 1
    else:
        # Show all commands without pagination
        for category, commands in command_categories.items():
            safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
            current_y += 1
            
            for cmd in commands:
                safe_addstr(stdscr, current_y, help_x + 4, cmd)
                current_y += 1
            
            current_y += 1
    
    # Footer
    footer = "Press 'H' or any key to return to main view"
    safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(footer)) // 2, 
               footer, curses.A_BOLD)

def render_config_view(stdscr, theme, height, width):
    """Render the configuration view"""
    header_height = 2
    stdscr.attron(curses.A_BOLD)
    title = "SYSTEM CONFIGURATION"
    safe_addstr(stdscr, 0, (width - len(title)) // 2, title)
    stdscr.attroff(curses.A_BOLD)
    
    # Draw main config box
    config_height = height - header_height - CONFIG["panel_sizes"]["status_height"] - 3
    config_width = width - 4
    config_x = 2
    config_y = header_height
    
    stdscr.attron(curses.color_pair(4))  # Blue for config
    draw_box(stdscr, config_y, config_x, config_height, config_width, "SETTINGS", theme)
    stdscr.attroff(curses.color_pair(4))
    
    # Display configuration options
    y_offset = 1
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"THEME: {CONFIG['theme']}")
    y_offset += 1
    
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"ANIMATIONS: {'ENABLED' if CONFIG['animations_enabled'] else 'DISABLED'}")
    y_offset += 1
    
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"ANIMATION SPEED: {CONFIG['animation_speed']}")
    y_offset += 1
    
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"DEBUG MODE: {'ENABLED' if CONFIG['debug_mode'] else 'DISABLED'}")
    y_offset += 2
    
    # Model settings
    stdscr.attron(curses.A_BOLD)
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, "MODEL SETTINGS:")
    stdscr.attroff(curses.A_BOLD)
    y_offset += 1
    
    for monolith, model in MODEL_CONFIG.items():
        status = MODEL_STATUS.get(monolith, {}).get("status", "unknown")
        status_color = 7  # Default white
        
        if status == "ready":
            status_color = 2  # Green
        elif status == "error":
            status_color = 1  # Red
        elif status == "loading":
            status_color = 6  # Cyan
        
        safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"{monolith}: {model['model']}")
        
        stdscr.attron(curses.color_pair(status_color))
        safe_addstr(stdscr, config_y + y_offset, config_x + 2 + len(f"{monolith}: {model['model']}") + 2, f"[{status.upper()}]")
        stdscr.attroff(curses.color_pair(status_color))
        
        y_offset += 1
    
    y_offset += 1
    
    # API settings
    stdscr.attron(curses.A_BOLD)
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, "API INTEGRATIONS:")
    stdscr.attroff(curses.A_BOLD)
    y_offset += 1
    
    for api, settings in CONFIG["api_keys"].items():
        status = "CONFIGURED" if settings.get("api_key") else "NOT CONFIGURED"
        enabled = "ENABLED" if settings.get("enabled") else "DISABLED"
        
        status_color = 2 if settings.get("api_key") and settings.get("enabled") else 3  # Green if configured and enabled, yellow otherwise
        
        safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"{api.upper()}: {status} - {enabled}")
        stdscr.attron(curses.color_pair(status_color))
        
        # Add connection status for IBKR
        if api == "ibkr" and settings.get("enabled"):
            ibkr_status = "CONNECTED" if IBKR_CONNECTED else "DISCONNECTED"
            status_color = 2 if IBKR_CONNECTED else 1
            
            stdscr.attron(curses.color_pair(status_color))
            safe_addstr(stdscr, config_y + y_offset, config_x + 2 + len(f"{api.upper()}: {status} - {enabled}") + 2, f"[{ibkr_status}]")
            stdscr.attroff(curses.color_pair(status_color))
        
        y_offset += 1
    
    # Provider settings
    y_offset += 1
    stdscr.attron(curses.A_BOLD)
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, "LLM PROVIDER:")
    stdscr.attroff(curses.A_BOLD)
    y_offset += 1
    
    provider_status = "READY" if check_any_model() else "UNAVAILABLE"
    provider_color = 2 if provider_status == "READY" else 1
    
    safe_addstr(stdscr, config_y + y_offset, config_x + 2, f"CURRENT PROVIDER: {LLM_PROVIDER.upper()}")
    stdscr.attron(curses.color_pair(provider_color))
    safe_addstr(stdscr, config_y + y_offset, config_x + 2 + len(f"CURRENT PROVIDER: {LLM_PROVIDER.upper()}") + 2, f"[{provider_status}]")
    stdscr.attroff(curses.color_pair(provider_color))
    
    # Render status panel at bottom
    render_status_panel(stdscr, theme, height, width, config_y + config_height)

def render_decision_history(stdscr, theme, height, width):
    """Render the decision history view"""
    header_height = 2
    stdscr.attron(curses.A_BOLD)
    title = "CONSENSUS DECISION HISTORY"
    safe_addstr(stdscr, 0, (width - len(title)) // 2, title)
    stdscr.attroff(curses.A_BOLD)
    
    # Draw main history box
    history_height = height - header_height - CONFIG["panel_sizes"]["status_height"] - 3
    history_width = width - 4
    history_x = 2
    history_y = header_height
    
    stdscr.attron(curses.color_pair(7))
    draw_box(stdscr, history_y, history_x, history_height, history_width, "DECISIONS", theme)
    stdscr.attroff(curses.color_pair(7))
    
    # Display decisions, most recent first
    if not decision_history:
        safe_addstr(stdscr, history_y + 2, history_x + 2, "No decisions recorded yet.")
    else:
        y_offset = 1
        for idx, decision in enumerate(reversed(decision_history)):
            if y_offset + 3 < history_height:
                # Format timestamp
                timestamp = decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                
                # Display verdict with color
                verdict = decision["verdict"]
                verdict_color = 2 if verdict == "APPROVE" else 1 if verdict == "DENY" else 7
                
                # Display decision header
                safe_addstr(stdscr, history_y + y_offset, history_x + 2, f"DECISION {len(decision_history) - idx}: {timestamp}")
                y_offset += 1
                
                # Display query
                query = decision["query"]
                if len(query) > history_width - 10:
                    query = query[:history_width - 13] + "..."
                safe_addstr(stdscr, history_y + y_offset, history_x + 4, f"Query: {query}")
                y_offset += 1
                
                # Display verdict
                safe_addstr(stdscr, history_y + y_offset, history_x + 4, f"Verdict: ", curses.A_BOLD)
                safe_addstr(stdscr, history_y + y_offset, history_x + 13, verdict, curses.color_pair(verdict_color) | curses.A_BOLD)
                y_offset += 1
                
                # Display reasoning summary if available
                if "reasoning" in decision and decision["reasoning"]:
                    reasoning = decision["reasoning"]
                    if len(reasoning) > history_width - 15:
                        reasoning = reasoning[:history_width - 18] + "..."
                    safe_addstr(stdscr, history_y + y_offset, history_x + 4, f"Reasoning: {reasoning}")
                    y_offset += 1
                
                # Add separator
                separator = "-" * (history_width - 4)
                safe_addstr(stdscr, history_y + y_offset, history_x + 2, separator)
                y_offset += 2
    
    # Render status panel at bottom
    render_status_panel(stdscr, theme, height, width, history_y + history_height)

def render_main_view(stdscr, height, width):
    """Render the main view with all panels"""
    # Set theme from config
    theme = STYLE["theme"] 
    
    # Clear screen
    stdscr.clear()
    
    # Render header with line across top
    header_line = "=" * width
    safe_addstr(stdscr, 0, 0, header_line)
    
    # System mode, title, and time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode_str = f"SYS-MODE: {CURRENT_MODE}"
    title_str = "# CONSENSUS WAR ROOM #"
    
    safe_addstr(stdscr, 1, 2, mode_str)
    safe_addstr(stdscr, 1, (width - len(title_str)) // 2, title_str)
    safe_addstr(stdscr, 1, width - len(current_time) - 2, current_time)
    
    # Second horizontal line
    safe_addstr(stdscr, 2, 0, header_line)
    
    # Draw monolith panels
    panel_end_y = render_monolith_panels(stdscr, theme, height, width)
    
    # Draw ARBITER coordination panel
    arbiter_end_y = render_arbiter_panel(stdscr, theme, height, width, panel_end_y)
    
    # Draw command input panel
    command_end_y = render_command_panel(stdscr, theme, height, width, arbiter_end_y)
    
    # Draw system status panel
    status_end_y = render_status_panel(stdscr, theme, height, width, command_end_y)
    
    # Draw notifications if enabled
    if STYLE["show_notifications"]:
        render_notifications(stdscr, height, width)
    
    # If in command input mode, display prompt
    if input_mode:
        # Calculate position (in command panel)
        input_y = command_end_y - 2
        input_x = 4  # Inside the command panel
        
        # Draw prompt and input
        safe_addstr(stdscr, input_y, input_x, "> ")
        safe_addstr(stdscr, input_y, input_x + 2, command_buffer)
        
        # Position cursor
        stdscr.move(input_y, input_x + 2 + len(command_buffer))
    
    # Display command output if available
    if command_output:
        output_y = command_end_y - 2
        if not input_mode:  # Only show if not in input mode
            safe_addstr(stdscr, output_y, 4, command_output, curses.color_pair(3))
# Core functionality
def get_vote_info(vote_path):
    """Get vote information from file"""
    try:
        if vote_path.exists():
            with open(vote_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        log_entry(f"Error reading vote file {vote_path}: {str(e)}", "ERROR")
    return None

def get_consensus_info():
    """Calculate consensus based on monolith votes"""
    consensus_path = ARBITER_DIR / "consensus.json"
    try:
        if consensus_path.exists():
            with open(consensus_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        log_entry(f"Error reading consensus file: {str(e)}", "ERROR")
    return None

def safe_addstr(stdscr, y, x, text, attr=0):
    """Safely add a string to the screen, avoiding errors at screen borders"""
    height, width = stdscr.getmaxyx()
    
    # Check if the position is valid
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    
    # Truncate the text if it would go beyond the screen width
    max_len = width - x
    if max_len <= 0:
        return
    
    # Truncate and display
    display_text = str(text)[:max_len]
    try:
        stdscr.addstr(y, x, display_text, attr)
    except curses.error:
        # Catch any curses errors (may happen at bottom-right corner)
        pass

def check_any_model():
    """Check if any model is available in the current provider"""
    try:
        endpoint = PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
        response = requests.get(endpoint, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def update_system_health():
    """Update system health metrics"""
    # Update CPU, memory, disk usage
    if psutil:
        SYSTEM_HEALTH["cpu"] = psutil.cpu_percent(interval=0.1)
        SYSTEM_HEALTH["memory"] = psutil.virtual_memory().percent
        SYSTEM_HEALTH["disk"] = psutil.disk_usage('/').percent
        
        # Network usage (simplified)
        net_io = psutil.net_io_counters()
        SYSTEM_HEALTH["network"] = net_io.bytes_sent + net_io.bytes_recv / 1024 / 1024  # Mbps
        
        # Temperature (if available)
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        SYSTEM_HEALTH["temperature"] = entries[0].current
                        break
    else:
        # Fallback to random values for demonstration
        SYSTEM_HEALTH["cpu"] = random.uniform(10, 90)
        SYSTEM_HEALTH["memory"] = random.uniform(20, 80)
SYSTEM_HEALTH["disk"] = random.uniform(30, 70)
        SYSTEM_HEALTH["network"] = random.uniform(1, 10)
        SYSTEM_HEALTH["temperature"] = random.uniform(40, 70)

def update_model_status():
    """Update status of all models"""
    for monolith, status in MODEL_STATUS.items():
        # Skip if currently loading
        if status["loading"]:
            continue
        
        try:
            endpoint = MODEL_CONFIG[monolith]["status_endpoint"]
            response = requests.get(endpoint, timeout=2)
            
            if response.status_code == 200:
                model_name = MODEL_CONFIG[monolith]["model"]
                
                # Check if model exists in provider
                if LLM_PROVIDER == "ollama":
                    models = response.json()["models"]
                    found = any(model["name"] == model_name.split(':')[0] for model in models)
                    status["status"] = "ready" if found else "not found"
                else:  # lmstudio
                    models = response.json()
                    found = model_name in models
                    status["status"] = "ready" if found else "not found"
                
                # Simulate memory usage for demo
                status["memory_usage"] = random.uniform(2000, 8000)
            else:
                status["status"] = "error"
        except Exception as e:
            status["status"] = "error"
            log_entry(f"Error updating model status for {monolith}: {str(e)}", "ERROR")

def update_bellator_data():
    """Update BELLATOR monolith data with realistic security information"""
    try:
        # Generate a realistic DEFCON level (usually 3-5)
        MONOLITH_DATA["BELLATOR"]["defcon_level"] = random.randint(3, 5)
        
        # Generate threat alerts
        MONOLITH_DATA["BELLATOR"]["threat_alerts"] = [
            {"region": "Middle East", "level": "Elevated", "description": "Increased tension in regional conflict zones"},
            {"region": "Cybersecurity", "level": "High", "description": "Multiple attacks targeting financial institutions"},
            {"region": "Pacific", "level": "Moderate", "description": "Naval exercises causing diplomatic tension"},
            {"region": "Economic", "level": "Low", "description": "Trade disruptions due to supply chain issues"}
        ]
        
        # Generate realistic security news
        MONOLITH_DATA["BELLATOR"]["security_news"] = [
            {"title": "New Defense Pact Signed", "source": "World Politics", "time": "3h ago"},
            {"title": "Cybersecurity Breach Detected", "source": "Tech Defense", "time": "8h ago"},
            {"title": "Strategic Resource Discovery", "source": "Resource Monitor", "time": "12h ago"},
            {"title": "International Summit Announced", "source": "Diplomatic Channel", "time": "4h ago"},
            {"title": "Military Exercise Completed", "source": "Defense News", "time": "2h ago"}
        ]
        
        # Strategic analysis
        MONOLITH_DATA["BELLATOR"]["strategic_analysis"] = [
            "Primary threats concentrated in cyber domain",
            "Resource contention increasing conflict risk",
            "Defensive posture recommended",
            "Economic leverage being used in geopolitical tensions",
            "Technological superiority remains a strategic advantage"
        ]
        
        MONOLITH_DATA["BELLATOR"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        log_entry(f"Error updating Bellator data: {str(e)}", "ERROR")
        return False

def update_aeternum_data():
    """Update AETERNUM monolith data with financial information"""
    try:
        # Market indices
        MONOLITH_DATA["AETERNUM"]["market_indices"] = {
            "S&P 500": {"value": 5123.45, "change": 0.75, "trend": "up"},
            "Dow Jones": {"value": 37893.21, "change": -0.12, "trend": "down"},
            "NASDAQ": {"value": 16789.34, "change": 1.42, "trend": "up"},
            "Russell 2000": {"value": 2134.56, "change": -0.31, "trend": "down"},
            "VIX": {"value": 17.25, "change": 2.1, "trend": "up"}
        }
        
        # Cryptocurrency prices
        MONOLITH_DATA["AETERNUM"]["crypto_prices"] = {
            "Bitcoin": {"price": 62453.21, "change": 2.3, "market_cap": "1.2T"},
            "Ethereum": {"price": 3245.67, "change": 1.5, "market_cap": "389B"},
            "Solana": {"price": 134.92, "change": 3.8, "market_cap": "58B"},
            "Cardano": {"price": 0.45, "change": -1.2, "market_cap": "16B"},
            "Polkadot": {"price": 5.78, "change": -0.5, "market_cap": "7.8B"}
        }
        
        # Portfolio performance
        MONOLITH_DATA["AETERNUM"]["portfolio_performance"] = {
            "daily_change": 0.42,
            "weekly_change": 1.87,
            "monthly_change": -0.53,
            "yearly_change": 12.76,
            "top_performers": ["NVDA", "MSFT", "TSLA"],
            "worst_performers": ["IBM", "GE", "T"]
        }
        
        # Economic indicators
        MONOLITH_DATA["AETERNUM"]["economic_indicators"] = {
            "inflation": 3.2,
            "unemployment": 3.7,
            "fed_rate": 5.25,
            "treasury_10y": 4.1,
            "oil_price": 76.45,
            "gold_price": 2312.80,
            "gdp_growth": 2.1,
            "consumer_confidence": 103.5
        }
        
        MONOLITH_DATA["AETERNUM"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        log_entry(f"Error updating Aeternum data: {str(e)}", "ERROR")
        return False

def update_rationalis_data():
    """Update RATIONALIS monolith data with system analysis"""
    try:
        # Generate system logs
        current_time = datetime.datetime.now()
        MONOLITH_DATA["RATIONALIS"]["system_logs"] = [
            {
                "timestamp": (current_time - datetime.timedelta(minutes=random.randint(0, 60))).strftime("%Y-%m-%d %H:%M:%S"),
                "level": random.choice(["INFO", "INFO", "INFO", "WARNING", "ERROR"]),
                "message": random.choice([
                    "System optimization complete",
                    "Query processing successfully",
                    "Neural pathway calibration adjusted",
                    "Resource allocation optimized",
                    "Multiple parallel inference threads running",
                    "Detected anomaly in reasoning pattern",
                    "Critical error in logic circuit",
                    "Decision tree pruning complete"
                ])
            } for _ in range(8)
        ]
        
        # Logic patterns
        MONOLITH_DATA["RATIONALIS"]["logic_patterns"] = {
            "deductive_accuracy": round(random.uniform(0.85, 0.98), 2),
            "inductive_strength": round(random.uniform(0.8, 0.95), 2),
            "abductive_agility": round(random.uniform(0.75, 0.9), 2),
            "reasoning_cycles": int(random.uniform(1200, 5000)),
            "logical_fallacies_detected": int(random.uniform(0, 10)),
            "concept_refinement": round(random.uniform(0.7, 0.95), 2)
        }
        
        # Analysis metrics
        MONOLITH_DATA["RATIONALIS"]["analysis_metrics"] = {
            "inference_speed": round(random.uniform(0.8, 0.99), 2),
            "memory_utilization": round(random.uniform(0.6, 0.85), 2),
            "latency_response": round(random.uniform(0.8, 0.95), 2),
            "pattern_recognition": round(random.uniform(0.75, 0.92), 2),
            "concept_relation": round(random.uniform(0.7, 0.9), 2)
        }
        
        # Efficiency rating
        MONOLITH_DATA["RATIONALIS"]["efficiency_rating"] = round(random.uniform(0.82, 0.96), 2)
        
        MONOLITH_DATA["RATIONALIS"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        log_entry(f"Error updating Rationalis data: {str(e)}", "ERROR")
        return False

def update_arbiter_data():
    """Update ARBITER data with coordination information"""
    try:
        current_time = datetime.datetime.now()
        
        # Agenda items
        MONOLITH_DATA["ARBITER"]["agenda"] = [
            {
                "time": (current_time + datetime.timedelta(minutes=random.randint(30, 480))).strftime("%H:%M"),
                "task": random.choice([
                    "System synchronization check",
                    "Neural pathway optimization",
                    "Vote on strategic deployment",
                    "Pattern recognition calibration",
                    "Threat assessment update",
                    "Model parameter tuning",
                    "Economic projection analysis",
                    "System diagnostics and patching"
                ]),
                "priority": random.choice(["High", "Medium", "Low", "Medium", "Medium"])
            } for _ in range(5)
        ]
        
        # Pending decisions
        MONOLITH_DATA["ARBITER"]["pending_decisions"] = [
            {
                "query": random.choice([
                    "Authorize access to restricted data center?",
                    "Allocate additional processing resources to RATIONALIS node?",
                    "Deploy enhanced security protocols in sector 7?",
                    "Initiate comprehensive system maintenance cycle?",
                    "Adjust risk assessment parameters for financial predictions?"
                ]),
                "status": random.choice(["Awaiting votes", "Processing", "Vote deadlock", "Final review"])
            } for _ in range(3)
        ]
        
        # System status
        MONOLITH_DATA["ARBITER"]["system_status"] = {
            "monoliths_online": random.randint(2, 3),
            "communication_integrity": round(random.uniform(0.92, 0.99), 2),
            "decision_throughput": round(random.uniform(20, 45), 1)
        }
        
        # Balance metrics
        total = 1.0
        rationalis = round(random.uniform(0.25, 0.45), 2)
        total -= rationalis
        aeternum = round(random.uniform(0.25, total), 2)
        bellator = round(total - aeternum, 2)
        
        MONOLITH_DATA["ARBITER"]["balance_metrics"] = {
            "rationalis_influence": rationalis,
            "aeternum_influence": aeternum, 
            "bellator_influence": bellator,
            "consensus_rate": round(random.uniform(0.65, 0.9), 2),
            "conflict_rate": round(random.uniform(0.1, 0.35), 2)
        }
        
        MONOLITH_DATA["ARBITER"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        log_entry(f"Error updating Arbiter data: {str(e)}", "ERROR")
        return False

def handle_monolith_query(monolith_name, query):
    """Send a direct query to a monolith and update MONOLITH_DATA with response"""
    global CURRENT_MODE
    
    # Change to voting mode
    old_mode = CURRENT_MODE
    CURRENT_MODE = "VOTING"
    
    log_entry(f"Sending direct query to {monolith_name}: {query}")
    config = MODEL_CONFIG.get(monolith_name.upper())
    if not config:
        log_entry(f"No config for {monolith_name}", "ERROR")
        CURRENT_MODE = old_mode
        return "Error: Monolith not found"

    # Set monolith status to processing
    MODEL_STATUS[monolith_name.upper()]["status"] = "processing"
    
    # Create a payload based on provider
    if config["engine"] == "ollama":
        payload = {
            "model": config["model"],
            "prompt": config["system_prompt"] + "\nQuery: " + query + "\nResponse:",
            "stream": False
        }
    else:  # lmstudio
        payload = {
            "model": config["model"],
            "prompt": config["system_prompt"] + "\nQuery: " + query + "\nResponse:",
            "temperature": config["parameters"]["temperature"],
            "max_tokens": config["parameters"]["max_tokens"]
        }

    try:
        # Make request to LLM
        start_time = time.time()
        response = requests.post(config["api_url"], json=payload, timeout=30)
        end_time = time.time()
        
        # Track response time
        response_time = end_time - start_time
        SYSTEM_HEALTH["response_times"].append(response_time)
        SYSTEM_HEALTH["avg_response_time"] = sum(SYSTEM_HEALTH["response_times"]) / len(SYSTEM_HEALTH["response_times"])
        
        if response.status_code == 200:
            result = response.json()
            
            # Parse response based on provider
            if config["engine"] == "ollama":
                answer = result.get("response", "").strip()
            else:  # lmstudio
                answer = result.get("choices", [{}])[0].get("text", "").strip()
            
            # Update monolith data with response
            if monolith_name.upper() == "BELLATOR":
                MONOLITH_DATA["BELLATOR"]["strategic_analysis"].insert(0, answer)
            elif monolith_name.upper() == "AETERNUM":
                # Store analysis as a custom entry
                if "analysis" not in MONOLITH_DATA["AETERNUM"]:
                    MONOLITH_DATA["AETERNUM"]["analysis"] = []
                MONOLITH_DATA["AETERNUM"]["analysis"].insert(0, answer)
            elif monolith_name.upper() == "RATIONALIS":
                # Simulate logical analysis
                MONOLITH_DATA["RATIONALIS"]["system_logs"].insert(0, {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "level": "INFO",
                    "message": f"Analysis complete: {answer[:50]}..."
                })
            
            # Create a vote file
            vote_info = {
                "monolith": monolith_name.lower(),
                "vote": random.choice(["APPROVE", "DENY"]),
                "reasoning": answer
            }
            
            vote_path = MONOLITHS[monolith_name.upper()]["vote_path"]
            with open(vote_path, 'w') as f:
                json.dump(vote_info, f)
            
            # Update monolith timestamp
            MONOLITH_DATA[monolith_name.upper()]["last_updated"] = datetime.datetime.now()
            
            # Reset status to ready
            MODEL_STATUS[monolith_name.upper()]["status"] = "ready"
            
            # Add to decision history
            add_decision_to_history(query, vote_info["vote"], vote_info["reasoning"])
            
            log_entry(f"Response from {monolith_name}: {answer[:100]}...")
            
            # Reset mode after delay
            time.sleep(1)  # Simulate processing time
            CURRENT_MODE = old_mode
            
            return f"Query processed successfully"
        else:
            log_entry(f"{monolith_name} responded with status {response.status_code}", "WARNING")
            MODEL_STATUS[monolith_name.upper()]["status"] = "error"
            CURRENT_MODE = old_mode
            return f"Error: HTTP {response.status_code}"
    except Exception as e:
        log_entry(f"Query to {monolith_name} failed: {e}", "ERROR")
        MODEL_STATUS[monolith_name.upper()]["status"] = "error"
        CURRENT_MODE = old_mode
        return f"Error: {str(e)}"

def process_command(command):
    """Process a command entered by the user"""
    global CURRENT_VIEW, CURRENT_MODE, command_output, STYLE, CONFIG, input_mode, LLM_PROVIDER
    
    cmd_parts = command.strip().lower().split()
    if not cmd_parts:
        return "Enter a command"
    
    cmd = cmd_parts[0]
    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
    
    # Monolith-specific commands
    if cmd in ["bellator", "rationalis", "aeternum"]:
        if args:
            query = " ".join(args)
            monolith = cmd.upper()
            threading.Thread(target=handle_monolith_query, args=(monolith, query), daemon=True).start()
            return f"Querying {monolith} with: {query}"
        else:
            if cmd.upper() == "BELLATOR":
                CURRENT_VIEW = "MONOLITH_BELLATOR"
            elif cmd.upper() == "RATIONALIS":
                CURRENT_VIEW = "MONOLITH_RATIONALIS"
            elif cmd.upper() == "AETERNUM":
                CURRENT_VIEW = "MONOLITH_AETERNUM"
            return f"Switching to {cmd.upper()} view"
    
    # System commands
    elif cmd == "help":
        CURRENT_VIEW = "help"
        return "Showing help screen"
    
    elif cmd == "config":
        CURRENT_VIEW = "config"
        return "Showing configuration screen"
    
    elif cmd == "history":
        CURRENT_VIEW = "history"
        return "Showing decision history"
    
    elif cmd == "main":
        CURRENT_VIEW = "main"
        return "Returning to main view"
    
    elif cmd == "logs":
        CURRENT_VIEW = "logs"
        return "Showing system logs"
    
    elif cmd == "status":
        update_model_status()
        return "Updated model status information"
    
    elif cmd == "refresh":
        update_system_health()
        update_model_status()
        return "Refreshed system data"
    
    elif cmd == "critical":
        CURRENT_MODE = "CRITICAL"
        log_entry("System mode changed to CRITICAL", "WARNING")
        return "System mode set to CRITICAL"
    
    elif cmd == "normal":
        CURRENT_MODE = "STANDBY"
        log_entry("System mode changed to STANDBY", "INFO")
        return "System mode set to STANDBY"
    
    # UI commands
    elif cmd == "style":
        if args and args[0] in BOX_CHARS:
            STYLE["theme"] = args[0]
            CONFIG["theme"] = args[0]
            save_config()
            return f"Theme set to {args[0]}"
        else:
            return f"Available themes: {', '.join(BOX_CHARS.keys())}"
    
    elif cmd == "dark":
        current_color_scheme = "dark"
        return "Switched to dark color scheme"
    
    elif cmd == "light":
        current_color_scheme = "light"
        return "Switched to light color scheme"
    
    elif cmd == "clear":
        LOG_ENTRIES.clear()
        return "Logs cleared"
    
    # LLM provider commands
    elif cmd == "use":
        if args and args[0] in ["ollama", "lmstudio"]:
            LLM_PROVIDER = args[0]
            for monolith in MODEL_CONFIG:
                MODEL_CONFIG[monolith]["api_url"] = PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"]
                MODEL_CONFIG[monolith]["status_endpoint"] = PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
            return f"Switched to {LLM_PROVIDER} provider"
        else:
            return "Usage: use <provider> (ollama/lmstudio)"
    
    # Query commands
    elif cmd == "query":
        if args:
            query = " ".join(args)
            # Create a thread for each monolith query
            CURRENT_MODE = "VOTING"
            for monolith in MONOLITHS:
                threading.Thread(target=handle_monolith_query, args=(monolith, query), daemon=True).start()
            return f"Querying all monoliths with: {query}"
        else:
            return "Usage: query <text>"
    
    elif cmd == "consensus":
        # Generate a consensus from existing votes
        votes = {}
        for name, info in MONOLITHS.items():
            vote_info = get_vote_info(info["vote_path"])
            if vote_info:
                votes[name] = vote_info.get("vote", "PENDING")
        
        # Decide based on majority
        approves = sum(1 for v in votes.values() if v == "APPROVE")
        denies = sum(1 for v in votes.values() if v == "DENY")
        
        if approves > denies:
            decision = "APPROVE"
        elif denies > approves:
            decision = "DENY"
        else:
            decision = "DEADLOCK"
        
        # Save consensus
        consensus_info = {
            "votes": votes,
            "decision": decision,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(ARBITER_DIR / "consensus.json", 'w') as f:
            json.dump(consensus_info, f)
        
        return f"Consensus generated: {decision}"
    
    # Default
    else:
        return f"Unknown command: {cmd}"

def handle_key_input(key, stdscr):
    """Handle keyboard input in main application"""
    global CURRENT_VIEW, input_mode, command_buffer, command_output, help_page, CURRENT_MODE
    
    # Toggle monolith views with 1-4 keys
    if key == ord('1'):
        if CURRENT_VIEW == "MONOLITH_AETERNUM":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "MONOLITH_AETERNUM"
            update_aeternum_data()
    elif key == ord('2'):
        if CURRENT_VIEW == "MONOLITH_BELLATOR":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "MONOLITH_BELLATOR"
            update_bellator_data()
    elif key == ord('3'):
        if CURRENT_VIEW == "MONOLITH_RATIONALIS":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "MONOLITH_RATIONALIS"
            update_rationalis_data()
    elif key == ord('4'):
        if CURRENT_VIEW == "MONOLITH_ARBITER":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "MONOLITH_ARBITER"
            update_arbiter_data()
    elif key == ord('5'):
        CURRENT_VIEW = "main"
    # Additional keys for logs (7) and config (9)
    elif key == ord('7'):
        CURRENT_VIEW = "logs"
    elif key == ord('9'):
        CURRENT_VIEW = "config"
    
    # View toggles
    elif key == ord('h') or key == ord('H'):
        if CURRENT_VIEW == "help":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "help"
    elif key == ord('c') or key == ord('C'):
        if CURRENT_VIEW == "config":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "config"
    elif key == ord('l') or key == ord('L'):
        if CURRENT_VIEW == "logs":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "logs"
    elif key == ord('d') or key == ord('D'):
        if CURRENT_VIEW == "history":
            CURRENT_VIEW = "main"
        else:
            CURRENT_VIEW = "history"
    
    # Toggle critical mode
    elif key == ord('m') or key == ord('M'):
        if CURRENT_MODE == "CRITICAL":
            CURRENT_MODE = "STANDBY"
            log_entry("System mode changed to STANDBY", "INFO")
        else:
            CURRENT_MODE = "CRITICAL"
            log_entry("System mode changed to CRITICAL", "WARNING")
    
    # Command mode
    elif key == ord('/'):
        input_mode = True
        command_buffer = ""
    
    # Escape exits command mode
    elif key == 27:  # ESC
        if input_mode:
            input_mode = False
            command_buffer = ""
        elif CURRENT_VIEW != "main":
            CURRENT_VIEW = "main"
    
    # Command entry handling
    elif input_mode:
        if key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            # Backspace
            command_buffer = command_buffer[:-1]
        elif key == 10 or key == 13:  # Enter
            # Process command
            if command_buffer:
                command_output = process_command(command_buffer)
                COMMAND_HISTORY.append(command_buffer)
                command_buffer = ""
                input_mode = False
        elif key == 9:  # Tab
            # Auto-complete (simple example)
            if command_buffer.startswith("s"):
                command_buffer = "status"
            elif command_buffer.startswith("h"):
                command_buffer = "help"
        elif 32 <= key <= 126:  # Printable ASCII
            command_buffer += chr(key)
    
    # Help pagination
    elif CURRENT_VIEW == "help":
        if key == ord(' '):  # Space
            help_page = 2 if help_page == 1 else 1
    
    # Other global keys
    elif key == ord('q') or key == ord('Q'):
        return False  # Exit
    elif key == ord('r') or key == ord('R'):
        update_system_health()
        update_model_status()
    elif key == ord('s') or key == ord('S'):
        # Cycle through styles
        themes = list(BOX_CHARS.keys())
        current_idx = themes.index(STYLE["theme"])
        STYLE["theme"] = themes[(current_idx + 1) % len(themes)]
        CONFIG["theme"] = STYLE["theme"]
        save_config()
    
    return True  # Continue running

def main(stdscr):
    """Main application function"""
    global CURRENT_VIEW, CURRENT_MODE, command_buffer
    
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    stdscr.timeout(100)  # Non-blocking input with 100ms refresh
    stdscr.keypad(True)  # Enable keypad mode
    
    # Setup colors
    setup_colors()
    
    # Initialize the system
    init_system()
    
    # Show boot sequence
    render_boot_sequence(stdscr)
    
    # Set initial view
    CURRENT_VIEW = "main"
    CURRENT_MODE = "STANDBY"
    
    # Initialize data
    update_system_health()
    update_bellator_data()
    update_aeternum_data()
    update_rationalis_data()
    update_arbiter_data()
    
    # Main loop
    running = True
    while running:
        # Get screen dimensions
        height, width = stdscr.getmaxyx()
        
        # Process any keyboard input
        try:
            key = stdscr.getch()
            if key != -1:  # -1 means no input available
                running = handle_key_input(key, stdscr)
        except curses.error:
            pass
        
        # Clear screen
        stdscr.clear()
        
        # Render current view
        if CURRENT_VIEW == "main":
            render_main_view(stdscr, height, width)
        elif CURRENT_VIEW == "MONOLITH_BELLATOR":
            render_bellator_screen(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "MONOLITH_AETERNUM":
            render_aeternum_screen(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "MONOLITH_RATIONALIS":
            render_rationalis_screen(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "MONOLITH_ARBITER":
            render_arbiter_screen(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "help":
            render_help_screen(stdscr, height, width, STYLE["theme"])
        elif CURRENT_VIEW == "config":
            render_config_view(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "logs":
            render_log_view(stdscr, STYLE["theme"], height, width)
        elif CURRENT_VIEW == "history":
            render_decision_history(stdscr, STYLE["theme"], height, width)
        
        # Periodically update system health (every ~5 seconds)
        if int(time.time()) % 5 == 0:
            update_system_health()
        
        # Every 30 seconds, update model status
        if int(time.time()) % 30 == 0:
            threading.Thread(target=update_model_status, daemon=True).start()
        
        # Refresh the screen
        stdscr.refresh()
        
        # Add a small delay to prevent CPU hogging
        time.sleep(0.05)

# Version information - update this whenever editing the script
VERSION = "1.0.3"
BUILD_DATE = "2025-05-14"

def show_version():
    """Display version information"""
    return f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"

if __name__ == "__main__":
    # Create directories if they don't exist
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Start the application
    try:
        # Wrap the main function to handle curses setup/teardown
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'TERM_PROGRAM' in os.environ and os.environ['TERM_PROGRAM'] == 'iTerm.app':
            # Special handling for iTerm on macOS
            print("If you're using iTerm2, try increasing the terminal window size.")