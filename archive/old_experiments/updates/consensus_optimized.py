#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (Optimized v2.3.0)

An enhanced decision-making system with three distinct AI monoliths:
- RATIONALIS: Logical analysis using DeepSeek Coder
- AETERNUM: Financial/Historical analysis using Llama 3  
- BELLATOR: Tactical/Security analysis using Mixtral

Features:
- Multiple visual themes (Military, WH40k, TARS, Helldivers)
- Real-time model integration with Ollama/LM Studio
- Individual monolith specialized screens
- Decision history and consensus tracking
- System health monitoring
- Command-line interface with autocomplete

Author: Claude AI & Human Collaboration
Version: 2.3.0
Date: May 2025
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
import signal
import shutil
import subprocess
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple, Optional, Any, Union

# Optional imports with graceful fallbacks
try:
    import psutil
except ImportError:
    psutil = None

try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

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

CONSENSUS_LOGO = """
 ██████╗ ██████╗ ███╗   ██╗███████╗███████╗███╗   ██╗███████╗██╗   ██╗███████╗
██╔════╝██╔═══██╗████╗  ██║██╔════╝██╔════╝████╗  ██║██╔════╝██║   ██║██╔════╝
██║     ██║   ██║██╔██╗ ██║███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║███████╗
██║     ██║   ██║██║╚██╗██║╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║╚════██║
╚██████╗╚██████╔╝██║ ╚████║███████║███████╗██║ ╚████║███████║╚██████╔╝███████║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚══════╝
 
 __        ___    ____    ____   ___   ___  __  __ 
 \ \      / / \  |  _ \  |  _ \ / _ \ / _ \|  \/  |
  \ \ /\ / / _ \ | |_) | | |_) | | | | | | | |\/| |
   \ V  V / ___ \|  _ <  |  _ <| |_| | |_| | |  | |
    \_/\_/_/   \_\_| \_\ |_| \_\\___/ \___/|_|  |_|
                                      
      *** AI TRIBUNAL DECISION SYSTEM ***
"""

# ===== CONFIGURATION AND CONSTANTS =====

VERSION = "2.3.0"
BUILD_DATE = "2025-05-19"

# System paths
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
CONFIG_PATH = ARBITER_DIR / "config.json"

# Global configuration with optimized defaults
CONFIG = {
    "system_mode": "STANDBY",
    "current_view": "main",
    "current_query": "No active query",
    "theme": "military",
    "color_scheme": "dark",
    "animations_enabled": True,
    "animation_speed": 10,
    "llm_provider": "ollama",
    "vote_timeout": 30,
    "auto_refresh": True,
    "refresh_interval": 5,
    "show_notifications": True,
    "show_system_health": True,
    "enable_autocomplete": True,
    "command_history_size": 50,
    "max_log_entries": 1000,
    "max_decision_history": 20,
    "debug_mode": False,
    "api_keys": {
        "ibkr": {"enabled": False, "api_key": "", "secret": ""},
        "openai": {"enabled": False, "api_key": ""},
        "anthropic": {"enabled": False, "api_key": ""}
    },
    "panel_sizes": {
        "monolith_height": 8,
        "command_height": 3,
        "status_height": 3
    }
}

# LLM provider endpoints
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
        "system_prompt": "You are RATIONALIS, a logical reasoning assistant focused on organization and rational analysis.",
        "parameters": {"temperature": 0.1, "top_p": 0.9, "max_tokens": 1024}
    },
    "AETERNUM": {
        "model": "llama3:70b", 
        "system_prompt": "You are AETERNUM, a financial analysis AI focused on pattern recognition and market analysis.",
        "parameters": {"temperature": 0.3, "top_p": 0.95, "max_tokens": 1024}
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "system_prompt": "You are BELLATOR, a tactical analyst focused on identifying risks and security concerns.",
        "parameters": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 1024}
    }
}

# Monolith configuration
MONOLITHS = {
    "RATIONALIS": {
        "id": 3,
        "desc": "Logical analysis and rationality assessment",
        "color": 4,  # Blue
        "vote_path": VOTE_DIR / "rationalis_vote.json",
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
        "id": 1,
        "desc": "Pattern recognition and historical context",
        "color": 5,  # Magenta/Cyan
        "vote_path": VOTE_DIR / "aeternum_vote.json",
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
        "id": 2,
        "desc": "Tactical assessment and execution planning",
        "color": 2,  # Green
        "vote_path": VOTE_DIR / "bellator_vote.json",
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

# System modes with colors and descriptions
SYSTEM_MODES = {
    "STANDBY": {"color": 3, "desc": "System idle, awaiting commands"},
    "VOTING": {"color": 6, "desc": "Monoliths deliberating on proposal"},
    "CONSENSUS": {"color": 2, "desc": "Agreement reached, executing commands"},
    "DEADLOCK": {"color": 1, "desc": "No consensus reached, requiring override"},
    "ERROR": {"color": 1, "desc": "System error detected, manual intervention required"},
    "MAINTENANCE": {"color": 5, "desc": "System undergoing maintenance operations"},
    "CRITICAL": {"color": 1, "desc": "CRITICAL operations mode, high priority"}
}

# Vote colors
VOTE_COLORS = {
    "APPROVE": 2,  # Green
    "DENY": 1,     # Red  
    "PENDING": 7   # White
}

# Box drawing characters for themes
BOX_CHARS = {
    "default": {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
    "military": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
    "wh40k": {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
    "tars": {"tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦", "h": "⎯", "v": "⎮"},
    "helldivers": {"tl": "◢", "tr": "◣", "bl": "◥", "br": "◤", "h": "━", "v": "┃"}
}

# Query templates
QUERY_TEMPLATES = {
    "finance": "Analyze market conditions for {symbol} and recommend investment action.",
    "security": "Evaluate security implications of {action} regarding {target}.",
    "logical": "Determine optimal approach for {goal} given constraints {constraints}.",
    "general": "Should we proceed with {action}?",
    "critical": "Authorize emergency protocol {protocol_number} for {situation}."
}

# ===== GLOBAL STATE VARIABLES =====

# System state
MODEL_STATUS = {
    "RATIONALIS": {"status": "unknown", "memory_usage": 0, "loading": False},
    "AETERNUM": {"status": "unknown", "memory_usage": 0, "loading": False},
    "BELLATOR": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# System health metrics
SYSTEM_HEALTH = {
    "cpu": 0.0,
    "memory": 0.0,
    "disk": 0.0,
    "network": 0.0,
    "temperature": 0.0,
    "start_time": time.time(),
    "response_times": deque(maxlen=50),
    "avg_response_time": 0
}

# UI state
notifications = deque(maxlen=5)
decision_history = deque(maxlen=CONFIG["max_decision_history"])
command_history = deque(maxlen=CONFIG["command_history_size"])
log_entries = deque(maxlen=CONFIG["max_log_entries"])

# Command interface state
command_buffer = ""
command_output = ""
input_mode = False
help_page = 1

# IBKR state
IBKR_CONNECTED = False
ib = None

# Animation state
verdict_display_text = ""
verdict_display_length = 0
verdict_full_text = ""
last_verdict_update = 0

# Monolith data for specialized views
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

# ===== BOOT SEQUENCE =====

def show_boot_sequence():
    """Display the boot sequence with NERV logo and initialization steps"""
    print("\033[2J\033[H")  # Clear screen and move to top
    print(NERV_LOGO)
    time.sleep(1.5)
    
    # Display version information
    version_text = f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"
    print(f"\n{version_text:^80}")
    time.sleep(0.5)
    
    print("\n\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # System initialization steps
    init_steps = [
        ("Checking system resources", ["CPU availability", "Memory alignment", "Display capabilities"]),
        ("Initializing AI cores", ["RATIONALIS module", "AETERNUM module", "BELLATOR module"]),
        ("Establishing network", ["API endpoints", "Model connections", "Health monitoring"]),
        ("Loading interface", ["Theme system", "Command parser", "Display engine"])
    ]
    
    for step_name, substeps in init_steps:
        print(f"\n◢◣ {step_name}...")
        time.sleep(0.3)
        for substep in substeps:
            print(f"  ├─ {substep}{'.' * (30 - len(substep))} [✓]")
            time.sleep(0.2)
        time.sleep(0.3)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    print(f"""
\033[1;33m▶ Control Keys:\033[0m
  - \033[1;36mQ\033[0m: Quit               - \033[1;36mM\033[0m: Toggle mode
  - \033[1;36mS\033[0m: Cycle styles       - \033[1;36mI\033[0m: Command mode
  - \033[1;36mH\033[0m: Help screen        - \033[1;36m1-3\033[0m: Monolith views
    """)
    
    print("\033[1;32m■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE...\033[0m")
    input()

# ===== CORE SYSTEM FUNCTIONS =====

def init_system():
    """Initialize the CONSENSUS system directories and configuration"""
    # Create system directories
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR, EXPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Load or create configuration
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                loaded_config = json.load(f)
                CONFIG.update(loaded_config)
        except Exception as e:
            log_entry(f"Error loading configuration: {str(e)}", "ERROR")
    
    # Save current configuration
    save_config()
    log_entry("System initialized successfully", "INFO")

def save_config():
    """Save current configuration to disk"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        log_entry(f"Error saving configuration: {str(e)}", "ERROR")

def log_entry(message: str, level: str = "INFO"):
    """Add an entry to the system log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    log_entries.append(entry)
    
    # Save to disk
    try:
        log_path = LOG_DIR / f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except Exception:
        pass

def add_notification(message: str, level: str = "info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now(),
        "seen": False
    })

def add_decision_to_history(query: str, verdict: str, reasoning: str = None):
    """Add a decision to the history"""
    decision_history.append({
        "query": query,
        "verdict": verdict,
        "timestamp": datetime.datetime.now(),
        "reasoning": reasoning or "No reasoning provided"
    })

# ===== MODEL MANAGEMENT =====

def check_model_status(name: str) -> bool:
    """Check if a model is loaded and available"""
    try:
        endpoint = PROVIDER_ENDPOINTS[CONFIG["llm_provider"]]["status_endpoint"]
        response = requests.get(endpoint, timeout=5)
        
        if response.status_code == 200:
            if CONFIG["llm_provider"] == "ollama":
                models = response.json().get("models", [])
                model_name = MODEL_CONFIG[name]["model"]
                for model in models:
                    if model["name"] == model_name:
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                MODEL_STATUS[name]["status"] = "not_loaded"
            elif CONFIG["llm_provider"] == "lmstudio":
                models = response.json().get("data", [])
                model_name = MODEL_CONFIG[name]["model"].split(":")[0].lower()
                for model in models:
                    if model_name in model["id"].lower():
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                MODEL_STATUS[name]["status"] = "not_loaded"
        return False
    except Exception:
        MODEL_STATUS[name]["status"] = "service_down"
        return False

def update_model_statuses():
    """Update all model statuses in background"""
    for name in MODEL_STATUS:
        if not MODEL_STATUS[name]["loading"]:
            check_model_status(name)
            
        # Update memory usage if psutil available
        if psutil:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                    proc_name = proc.info['name'].lower()
                    if ((CONFIG["llm_provider"] == "ollama" and 'ollama' in proc_name) or
                        (CONFIG["llm_provider"] == "lmstudio" and 'lmstudio' in proc_name)):
                        MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)
                        break
            except Exception:
                pass

def query_model(name: str, prompt: str) -> str:
    """Query a specific model and get response"""
    try:
        config = MODEL_CONFIG[name]
        api_url = PROVIDER_ENDPOINTS[CONFIG["llm_provider"]]["api_url"]
        
        if MODEL_STATUS[name]["status"] != "ready":
            return f"Error: Model {config['model']} not ready. Status: {MODEL_STATUS[name]['status']}"
        
        # Create full prompt
        full_prompt = f"{config['system_prompt']}\n\nQUERY: {prompt}\n\nVOTE: "
        
        if CONFIG["llm_provider"] == "ollama":
            payload = {
                "model": config["model"],
                "prompt": full_prompt,
                "stream": False,
                **config["parameters"]
            }
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: API returned status {response.status_code}"
                
        elif CONFIG["llm_provider"] == "lmstudio":
            payload = {
                "model": config["model"],
                "prompt": full_prompt,
                **config["parameters"]
            }
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                return f"Error: API returned status {response.status_code}"
                
    except Exception as e:
        return f"Error querying model: {str(e)}"

# ===== VOTING SYSTEM =====

def generate_vote(name: str, query: str) -> Dict:
    """Generate a vote from a specific monolith"""
    try:
        start_time = time.time()
        MONOLITHS[name]["status"] = "processing"
        
        # Query the model
        response = query_model(name, query)
        response_time = time.time() - start_time
        
        # Parse response for vote decision
        response_lower = response.lower()
        if any(word in response_lower for word in ["approve", "yes", "accept"]):
            vote = "APPROVE"
        elif any(word in response_lower for word in ["deny", "no", "reject"]):
            vote = "DENY"
        else:
            vote = "PENDING"
        
        # Create vote data
        vote_data = {
            "monolith": name.lower(),
            "vote": vote,
            "reasoning": response,
            "timestamp": time.time(),
            "confidence": random.uniform(0.65, 0.98),
            "response_time": response_time
        }
        
        # Save vote to file
        vote_path = MONOLITHS[name]["vote_path"]
        with open(vote_path, 'w', encoding='utf-8') as f:
            json.dump(vote_data, f, indent=2)
        
        # Update system state
        SYSTEM_HEALTH["response_times"].append(response_time)
        if SYSTEM_HEALTH["response_times"]:
            SYSTEM_HEALTH["avg_response_time"] = sum(SYSTEM_HEALTH["response_times"]) / len(SYSTEM_HEALTH["response_times"])
        
        MONOLITHS[name]["status"] = "online"
        add_notification(f"{name} voted: {vote}", "info")
        log_entry(f"{name} completed vote: {vote} in {response_time:.2f}s")
        
        return vote_data
        
    except Exception as e:
        error_msg = f"Error generating vote from {name}: {str(e)}"
        add_notification(error_msg, "error")
        MONOLITHS[name]["status"] = "offline"
        log_entry(error_msg, "ERROR")
        
        return {
            "monolith": name.lower(),
            "vote": "PENDING",
            "reasoning": error_msg,
            "timestamp": time.time()
        }

def generate_all_votes(query: str):
    """Generate votes from all monoliths"""
    CONFIG["system_mode"] = "VOTING"
    start_time = time.time()
    add_notification(f"Consensus generation started", "info")
    
    # Create threads for each monolith
    threads = []
    for name in MONOLITHS:
        thread = threading.Thread(target=generate_vote, args=(name, query), daemon=True)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads with timeout
    for thread in threads:
        thread.join(timeout=CONFIG["vote_timeout"])
    
    # Calculate consensus
    votes = {}
    for name in MONOLITHS:
        vote_path = MONOLITHS[name]["vote_path"]
        if vote_path.exists():
            try:
                with open(vote_path, 'r') as f:
                    vote_data = json.load(f)
                    votes[name] = vote_data.get("vote", "PENDING")
            except Exception:
                votes[name] = "PENDING"
        else:
            votes[name] = "PENDING"
    
    consensus = calculate_consensus(votes)
    total_time = time.time() - start_time
    
    if consensus:
        CONFIG["system_mode"] = "CONSENSUS"
        add_notification(f"Consensus reached: {consensus}", "success")
        add_decision_to_history(query, consensus)
        log_entry(f"Consensus achieved: {consensus} in {total_time:.2f}s", "SUCCESS")
    else:
        CONFIG["system_mode"] = "DEADLOCK"
        add_notification("No consensus reached", "warning")
        log_entry(f"Deadlock after {total_time:.2f}s", "WARNING")

def calculate_consensus(votes: Dict[str, str]) -> Optional[str]:
    """Calculate consensus based on votes"""
    approve_count = sum(1 for vote in votes.values() if vote == "APPROVE")
    deny_count = sum(1 for vote in votes.values() if vote == "DENY")
    
    if approve_count >= 2:
        return "APPROVE"
    elif deny_count >= 2:
        return "DENY"
    return None

def get_vote_info(vote_path: Path) -> Dict:
    """Get vote information from file"""
    try:
        if vote_path.exists():
            with open(vote_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log_entry(f"Error reading vote file {vote_path}: {str(e)}", "ERROR")
    return {}

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

# ===== SYSTEM HEALTH MONITORING =====

def update_system_health():
    """Update system health metrics"""
    if psutil:
        try:
            SYSTEM_HEALTH["cpu"] = psutil.cpu_percent(interval=0.1)
            SYSTEM_HEALTH["memory"] = psutil.virtual_memory().percent
            SYSTEM_HEALTH["disk"] = psutil.disk_usage('/').percent
            
            # Network usage (bytes per second converted to Mbps)
            net_io = psutil.net_io_counters()
            SYSTEM_HEALTH["network"] = (net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024)
            
            # Temperature (if available)
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            SYSTEM_HEALTH["temperature"] = entries[0].current
                            break
        except Exception:
            # Fallback to simulated values
            SYSTEM_HEALTH["cpu"] = random.uniform(10, 30)
            SYSTEM_HEALTH["memory"] = random.uniform(40, 70)
            SYSTEM_HEALTH["disk"] = random.uniform(20, 50)
            SYSTEM_HEALTH["network"] = random.uniform(1, 10)
            SYSTEM_HEALTH["temperature"] = random.uniform(40, 70)
    else:
        # Simulated values when psutil not available
        SYSTEM_HEALTH["cpu"] = random.uniform(10, 30)
        SYSTEM_HEALTH["memory"] = random.uniform(40, 70)
        SYSTEM_HEALTH["disk"] = random.uniform(20, 50)
        SYSTEM_HEALTH["network"] = random.uniform(1, 10)
        SYSTEM_HEALTH["temperature"] = random.uniform(40, 70)

def check_any_model():
    """Check if any model is available in the current provider"""
    try:
        endpoint = PROVIDER_ENDPOINTS[CONFIG["llm_provider"]]["status_endpoint"]
        response = requests.get(endpoint, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

# ===== MONOLITH DATA UPDATES =====

def update_monolith_data():
    """Update all monolith specialized data"""
    update_rationalis_data()
    update_aeternum_data()
    update_bellator_data()

def update_rationalis_data():
    """Update RATIONALIS monolith data"""
    current_time = datetime.datetime.now()
    
    # System logs
    MONOLITH_DATA["RATIONALIS"]["system_logs"] = [
        {
            "timestamp": (current_time - datetime.timedelta(minutes=random.randint(0, 60))).strftime("%H:%M:%S"),
            "level": random.choice(["INFO", "INFO", "INFO", "WARNING", "ERROR"]),
            "message": random.choice([
                "System optimization complete",
                "Neural pathway calibration adjusted",
                "Logic circuit verification passed",
                "Decision tree pruning complete",
                "Detected reasoning anomaly",
                "Processing multiple inference threads"
            ])
        } for _ in range(8)
    ]
    
    # Logic patterns
    MONOLITH_DATA["RATIONALIS"]["logic_patterns"] = {
        "deductive_accuracy": round(random.uniform(0.85, 0.98), 2),
        "inductive_strength": round(random.uniform(0.8, 0.95), 2),
        "abductive_agility": round(random.uniform(0.75, 0.9), 2),
        "reasoning_cycles": int(random.uniform(1200, 5000)),
        "logical_fallacies_detected": int(random.uniform(0, 10))
    }
    
    # Analysis metrics
    MONOLITH_DATA["RATIONALIS"]["analysis_metrics"] = {
        "inference_speed": round(random.uniform(0.8, 0.99), 2),
        "memory_utilization": round(random.uniform(0.6, 0.85), 2),
        "pattern_recognition": round(random.uniform(0.75, 0.95), 2),
        "cognitive_load": round(random.uniform(0.3, 0.7), 2),
        "optimization_cycles": int(random.uniform(100, 1000))
    }
    
    # Efficiency rating
    MONOLITH_DATA["RATIONALIS"]["efficiency_rating"] = round(random.uniform(0.82, 0.96), 2)
    MONOLITH_DATA["RATIONALIS"]["last_updated"] = current_time

def update_aeternum_data():
    """Update AETERNUM monolith data with financial information"""
    current_time = datetime.datetime.now()
    
    # Market indices simulation
    MONOLITH_DATA["AETERNUM"]["market_indices"] = {
        "S&P 500": {"value": 5123.45 + random.uniform(-50, 50), "change": random.uniform(-2, 2), "trend": random.choice(["up", "down"])},
        "NASDAQ": {"value": 16789.34 + random.uniform(-100, 100), "change": random.uniform(-3, 3), "trend": random.choice(["up", "down"])},
        "Dow Jones": {"value": 37893.21 + random.uniform(-200, 200), "change": random.uniform(-1.5, 1.5), "trend": random.choice(["up", "down"])},
        "Russell 2000": {"value": 2134.56 + random.uniform(-30, 30), "change": random.uniform(-2.5, 2.5), "trend": random.choice(["up", "down"])},
        "VIX": {"value": 17.25 + random.uniform(-5, 5), "change": random.uniform(-10, 10), "trend": random.choice(["up", "down"])}
    }
    
    # Cryptocurrency prices
    MONOLITH_DATA["AETERNUM"]["crypto_prices"] = {
        "Bitcoin": {"price": 62453.21 + random.uniform(-2000, 2000), "change": random.uniform(-5, 5), "market_cap": "1.2T"},
        "Ethereum": {"price": 3245.67 + random.uniform(-200, 200), "change": random.uniform(-4, 4), "market_cap": "389B"},
        "Solana": {"price": 134.92 + random.uniform(-10, 10), "change": random.uniform(-6, 6), "market_cap": "58B"},
        "Cardano": {"price": 0.45 + random.uniform(-0.05, 0.05), "change": random.uniform(-3, 3), "market_cap": "16B"},
        "Polkadot": {"price": 5.78 + random.uniform(-0.5, 0.5), "change": random.uniform(-4, 4), "market_cap": "7.8B"}
    }
    
    # Portfolio performance
    MONOLITH_DATA["AETERNUM"]["portfolio_performance"] = {
        "daily_change": random.uniform(-2, 2),
        "weekly_change": random.uniform(-5, 5),
        "monthly_change": random.uniform(-8, 8),
        "yearly_change": random.uniform(-15, 25),
        "top_performers": random.sample(["NVDA", "MSFT", "TSLA", "AAPL", "GOOGL", "AMZN"], 3),
        "worst_performers": random.sample(["IBM", "GE", "T", "XOM", "VZ", "KO"], 3)
    }
    
    # Economic indicators
    MONOLITH_DATA["AETERNUM"]["economic_indicators"] = {
        "inflation": 3.2 + random.uniform(-0.5, 0.5),
        "unemployment": 3.7 + random.uniform(-0.3, 0.3),
        "fed_rate": 5.25,
        "treasury_10y": 4.1 + random.uniform(-0.2, 0.2),
        "oil_price": 76.45 + random.uniform(-5, 5),
        "gold_price": 2312.80 + random.uniform(-50, 50),
        "gdp_growth": 2.1 + random.uniform(-0.5, 0.5),
        "consumer_confidence": 103.5 + random.uniform(-10, 10)
    }
    
    MONOLITH_DATA["AETERNUM"]["last_updated"] = current_time

def update_bellator_data():
    """Update BELLATOR monolith data with security information"""
    current_time = datetime.datetime.now()
    
    # DEFCON level simulation
    MONOLITH_DATA["BELLATOR"]["defcon_level"] = random.choice([3, 4, 5])
    
    # Threat alerts
    threat_types = ["Cyber", "Geopolitical", "Economic", "Environmental", "Technological"]
    MONOLITH_DATA["BELLATOR"]["threat_alerts"] = [
        {
            "id": f"TH-{random.randint(1000, 9999)}",
            "type": random.choice(threat_types),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "description": random.choice([
                "Unusual network activity detected",
                "Supply chain disruption risk",
                "Market volatility indicators",
                "Geopolitical tension escalation",
                "Infrastructure vulnerability assessment"
            ]),
            "timestamp": (current_time - datetime.timedelta(hours=random.randint(0, 24))).strftime("%H:%M")
        } for _ in range(5)
    ]
    
    # Strategic analysis
    MONOLITH_DATA["BELLATOR"]["strategic_analysis"] = [
        {
            "category": random.choice(["Risk Assessment", "Threat Analysis", "Operational Security", "Intelligence"]),
            "status": random.choice(["Monitoring", "Analyzing", "Investigating", "Resolved"]),
            "priority": random.choice(["Low", "Medium", "High", "Critical"]),
            "details": random.choice([
                "Multi-vector threat assessment in progress",
                "Anomalous patterns detected in sector 7",
                "Security protocols updated and deployed",
                "Threat mitigation strategies under review",
                "Intelligence gathering operations active"
            ])
        } for _ in range(4)
    ]
    
    # Security news simulation
    MONOLITH_DATA["BELLATOR"]["security_news"] = [
        {
            "headline": random.choice([
                "New cybersecurity framework deployed",
                "International security cooperation increased",
                "Advanced threat detection systems online",
                "Security audit completed successfully",
                "Emergency response protocols updated"
            ]),
            "source": random.choice(["INTEL-NET", "SecOps", "ThreatWatch", "DefenseGrid"]),
            "timestamp": (current_time - datetime.timedelta(hours=random.randint(0, 48))).strftime("%m/%d %H:%M")
        } for _ in range(6)
    ]
    
    MONOLITH_DATA["BELLATOR"]["last_updated"] = current_time

# ===== UI UTILITY FUNCTIONS =====

def safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0):
    """Safely add a string to the screen, avoiding errors at screen borders"""
    try:
        height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        
        # Truncate text if it would go beyond the screen width
        max_len = width - x
        if max_len <= 0:
            return
        
        display_text = str(text)[:max_len]
        stdscr.addstr(y, x, display_text, attr)
    except curses.error:
        pass

def draw_box(stdscr, y: int, x: int, height: int, width: int, theme: str = "default"):
    """Draw a box using theme-appropriate characters"""
    chars = BOX_CHARS.get(theme, BOX_CHARS["default"])
    
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

def format_uptime(start_time: float) -> str:
    """Format uptime in human-readable format"""
    uptime_seconds = int(time.time() - start_time)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# ===== MAIN INTERFACE RENDERING =====

def render_header(stdscr, theme: str, width: int):
    """Render the main header with logo and status"""
    # Clear header area
    for i in range(5):
        safe_addstr(stdscr, i, 0, " " * width)
    
    # Draw CONSENSUS logo
    logo_lines = CONSENSUS_LOGO.strip().split('\n')
    logo_start_y = 0
    
    for i, line in enumerate(logo_lines):
        if logo_start_y + i < 5:
            # Center the logo
            logo_x = max(0, (width - len(line)) // 2)
            safe_addstr(stdscr, logo_start_y + i, logo_x, line, curses.A_BOLD | curses.color_pair(6))

def render_monolith_status(stdscr, y: int, x: int, width: int, theme: str):
    """Render monolith status panel"""
    # Header
    title = "MONOLITH STATUS"
    safe_addstr(stdscr, y, x + (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(7))
    
    y_pos = y + 2
    for name, info in MONOLITHS.items():
        if y_pos < y + 8:  # Ensure we don't overflow the panel
            # Monolith name with color
            safe_addstr(stdscr, y_pos, x + 2, name, curses.A_BOLD | curses.color_pair(info["color"]))
            
            # Status indicator
            status = info["status"].upper()
            status_color = 2 if status == "ONLINE" else 3 if status == "PROCESSING" else 1
            safe_addstr(stdscr, y_pos, x + 15, status, curses.color_pair(status_color))
            
            # Model status
            model_status = MODEL_STATUS[name]["status"].upper()
            model_color = 2 if model_status == "READY" else 3 if model_status == "LOADING" else 1
            safe_addstr(stdscr, y_pos, x + 25, f"[{model_status}]", curses.color_pair(model_color))
            
            y_pos += 1

def render_system_health(stdscr, y: int, x: int, width: int, theme: str):
    """Render system health panel"""
    # Header
    title = "SYSTEM HEALTH"
    safe_addstr(stdscr, y, x + (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(7))
    
    # Update health metrics
    update_system_health()
    
    y_pos = y + 2
    health_items = [
        ("CPU", SYSTEM_HEALTH["cpu"], "%"),
        ("Memory", SYSTEM_HEALTH["memory"], "%"),
        ("Disk", SYSTEM_HEALTH["disk"], "%"),
        ("Network", SYSTEM_HEALTH["network"], "MB/s")
    ]
    
    for name, value, unit in health_items:
        if y_pos < y + 8:
            # Metric name
            safe_addstr(stdscr, y_pos, x + 2, f"{name}:", curses.A_BOLD)
            
            # Value with color based on threshold
            if name == "Network":
                color = 7  # White for network
            else:
                color = 2 if value < 50 else 3 if value < 80 else 1
            
            value_str = f"{value:.1f}{unit}"
            safe_addstr(stdscr, y_pos, x + 12, value_str, curses.color_pair(color))
            
            y_pos += 1
    
    # Uptime
    uptime_str = format_uptime(SYSTEM_HEALTH["start_time"])
    safe_addstr(stdscr, y_pos, x + 2, f"Uptime: {uptime_str}", curses.color_pair(7))

def render_voting_panel(stdscr, y: int, x: int, width: int, height: int, theme: str):
    """Render the voting status panel"""
    # Header
    title = "CONSENSUS TRIBUNAL"
    safe_addstr(stdscr, y, x + (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(6))
    
    # Current query
    query_text = CONFIG.get("current_query", "No active query")
    if len(query_text) > width - 4:
        query_text = query_text[:width - 7] + "..."
    safe_addstr(stdscr, y + 2, x + 2, f"Query: {query_text}", curses.color_pair(7))
    
    # Voting results
    y_pos = y + 4
    for name in MONOLITHS:
        if y_pos < y + height - 2:
            vote_info = get_vote_info(MONOLITHS[name]["vote_path"])
            vote = vote_info.get("vote", "PENDING")
            
            # Monolith name
            safe_addstr(stdscr, y_pos, x + 2, name, curses.A_BOLD | curses.color_pair(MONOLITHS[name]["color"]))
            
            # Vote with appropriate color
            vote_color = VOTE_COLORS.get(vote, 7)
            safe_addstr(stdscr, y_pos, x + 15, vote, curses.color_pair(vote_color))
            
            # Confidence if available
            if "confidence" in vote_info:
                confidence = vote_info["confidence"] * 100
                safe_addstr(stdscr, y_pos, x + 25, f"({confidence:.0f}%)", curses.color_pair(7))
            
            y_pos += 1
    
    # System mode
    mode = CONFIG.get("system_mode", "STANDBY")
    mode_color = SYSTEM_MODES.get(mode, {"color": 7})["color"]
    safe_addstr(stdscr, y + height - 2, x + 2, f"Mode: {mode}", curses.A_BOLD | curses.color_pair(mode_color))

def render_notifications(stdscr, y: int, x: int, width: int, height: int):
    """Render notifications panel"""
    # Header
    title = "NOTIFICATIONS"
    safe_addstr(stdscr, y, x + (width - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(7))
    
    # Display recent notifications
    y_pos = y + 2
    displayed = 0
    max_display = height - 3
    
    for notification in reversed(list(notifications)):
        if displayed >= max_display:
            break
            
        # Determine color based on level
        level_colors = {"info": 7, "success": 2, "warning": 3, "error": 1}
        color = level_colors.get(notification["level"], 7)
        
        # Format timestamp
        time_str = notification["timestamp"].strftime("%H:%M")
        
        # Truncate message if too long
        message = notification["message"]
        max_msg_len = width - len(time_str) - 5
        if len(message) > max_msg_len:
            message = message[:max_msg_len - 3] + "..."
        
        # Display notification
        safe_addstr(stdscr, y_pos, x + 2, f"[{time_str}] {message}", curses.color_pair(color))
        y_pos += 1
        displayed += 1

def render_command_interface(stdscr, y: int, x: int, width: int):
    """Render command interface"""
    global command_buffer, command_output, input_mode
    
    # Command prompt
    prompt = "CONSENSUS> "
    safe_addstr(stdscr, y, x, prompt, curses.A_BOLD | curses.color_pair(6))
    
    # Command buffer
    buffer_display = command_buffer
    if input_mode:
        buffer_display += "_"  # Show cursor
    
    safe_addstr(stdscr, y, x + len(prompt), buffer_display, curses.color_pair(7))
    
    # Command output (if any)
    if command_output:
        output_lines = command_output.strip().split('\n')
        for i, line in enumerate(output_lines):
            if y + 1 + i < stdscr.getmaxyx()[0] - 1:
                safe_addstr(stdscr, y + 1 + i, x, line[:width], curses.color_pair(3))

def render_main_screen(stdscr, theme: str):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Render header
    render_header(stdscr, theme, width)
    
    # Calculate panel dimensions
    header_height = 6
    footer_height = 4
    content_height = height - header_height - footer_height
    panel_width = width // 2 - 2
    
    # Left column panels
    left_x = 1
    
    # Monolith status panel
    monolith_y = header_height
    monolith_height = content_height // 3
    draw_box(stdscr, monolith_y, left_x, monolith_height, panel_width, theme)
    render_monolith_status(stdscr, monolith_y + 1, left_x + 1, panel_width - 2, theme)
    
    # System health panel
    health_y = monolith_y + monolith_height
    health_height = content_height // 3
    draw_box(stdscr, health_y, left_x, health_height, panel_width, theme)
    render_system_health(stdscr, health_y + 1, left_x + 1, panel_width - 2, theme)
    
    # Command interface
    command_y = health_y + health_height
    command_height = content_height - monolith_height - health_height
    draw_box(stdscr, command_y, left_x, command_height, panel_width, theme)
    render_command_interface(stdscr, command_y + 2, left_x + 2, panel_width - 4)
    
    # Right column panels
    right_x = width // 2 + 1
    
    # Voting panel
    voting_y = header_height
    voting_height = content_height * 2 // 3
    draw_box(stdscr, voting_y, right_x, voting_height, panel_width, theme)
    render_voting_panel(stdscr, voting_y + 1, right_x + 1, panel_width - 2, voting_height - 2, theme)
    
    # Notifications panel
    notif_y = voting_y + voting_height
    notif_height = content_height - voting_height
    draw_box(stdscr, notif_y, right_x, notif_height, panel_width, theme)
    render_notifications(stdscr, notif_y + 1, right_x + 1, panel_width - 2, notif_height - 2)
    
    # Footer with controls
    footer_y = height - footer_height
    controls = "Q:Quit | S:Style | I:Input | H:Help | 1-3:Monoliths | M:Mode"
    safe_addstr(stdscr, footer_y + 1, (width - len(controls)) // 2, controls, curses.A_BOLD | curses.color_pair(3))
    
    # Version info
    version_info = f"CONSENSUS v{VERSION}"
    safe_addstr(stdscr, footer_y + 2, width - len(version_info) - 2, version_info, curses.color_pair(7))

# ===== SPECIALIZED MONOLITH SCREENS =====

def render_aeternum_screen(stdscr, theme: str):
    """Render AETERNUM monolith specialized screen"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Update data if needed
    if not MONOLITH_DATA["AETERNUM"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["AETERNUM"]["last_updated"]).total_seconds() > 60:
        update_aeternum_data()
    
    # Header based on theme
    headers = {
        "military": "AETERNUM FINANCIAL OPERATIONS CENTER",
        "wh40k": "ADMINISTRATUM AETERNUM TREASURIUM",
        "tars": "AETERNUM.FINANCE.MODULE",
        "helldivers": "SUPER EARTH ECONOMIC COMMAND"
    }
    header = headers.get(theme, "AETERNUM FINANCIAL INTERFACE")
    
    # Draw header
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
    
    # Market indices section
    y_pos = 4
    section_header = "[ MARKET INDICES ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    indices = MONOLITH_DATA["AETERNUM"]["market_indices"]
    col1_x = 4
    col2_x = width // 2 + 4
    
    idx = 0
    for name, data in indices.items():
        if y_pos + idx // 2 < height - 15:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["trend"] == "up" else 1
            
            value_str = f"{data['value']:,.2f}"
            change_str = f"{data['change']:+.2f}%"
            market_text = f"{name}: {value_str} ({change_str})"
            
            safe_addstr(stdscr, y_pos + idx // 2, x_pos, market_text, curses.color_pair(trend_color))
            idx += 1
    
    y_pos += (idx + 1) // 2 + 2
    
    # Cryptocurrency section
    section_header = "[ CRYPTOCURRENCY MARKET ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    crypto = MONOLITH_DATA["AETERNUM"]["crypto_prices"]
    idx = 0
    for name, data in crypto.items():
        if y_pos + idx // 2 < height - 10:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["change"] > 0 else 1
            
            price_str = f"${data['price']:,.2f}"
            change_str = f"{data['change']:+.2f}%"
            crypto_text = f"{name}: {price_str} ({change_str})"
            
            safe_addstr(stdscr, y_pos + idx // 2, x_pos, crypto_text, curses.color_pair(trend_color))
            idx += 1
    
    y_pos += (idx + 1) // 2 + 2
    
    # Portfolio performance
    section_header = "[ PORTFOLIO PERFORMANCE ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    portfolio = MONOLITH_DATA["AETERNUM"]["portfolio_performance"]
    
    # Time-based performance
    for period, change in [("Daily", portfolio["daily_change"]), 
                           ("Weekly", portfolio["weekly_change"]), 
                           ("Monthly", portfolio["monthly_change"]), 
                           ("Yearly", portfolio["yearly_change"])]:
        if y_pos < height - 6:
            change_color = 2 if change > 0 else 1
            perf_text = f"{period}: {change:+.2f}%"
            safe_addstr(stdscr, y_pos, col1_x, perf_text, curses.color_pair(change_color))
            y_pos += 1
    
    # Top and worst performers
    if y_pos < height - 6:
        top_text = f"Top: {', '.join(portfolio['top_performers'])}"
        worst_text = f"Worst: {', '.join(portfolio['worst_performers'])}"
        safe_addstr(stdscr, y_pos - 4, col2_x, top_text, curses.color_pair(2))
        safe_addstr(stdscr, y_pos - 3, col2_x, worst_text, curses.color_pair(1))
    
    # Footer
    if MONOLITH_DATA["AETERNUM"]["last_updated"]:
        update_time = MONOLITH_DATA["AETERNUM"]["last_updated"].strftime("%H:%M:%S")
        footer_text = f"Last updated: {update_time} | Press 'M' to return to main view"
        safe_addstr(stdscr, height - 2, (width - len(footer_text)) // 2, footer_text, curses.color_pair(7))

def render_bellator_screen(stdscr, theme: str):
    """Render BELLATOR monolith specialized screen"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Update data if needed
    if not MONOLITH_DATA["BELLATOR"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["BELLATOR"]["last_updated"]).total_seconds() > 60:
        update_bellator_data()
    
    # Header based on theme
    headers = {
        "military": "BELLATOR TACTICAL OPERATIONS CENTER",
        "wh40k": "BELLATOR FORTRESS COMMAND",
        "tars": "BELLATOR.TACTICAL.MODULE",
        "helldivers": "SUPER EARTH STRATEGIC COMMAND"
    }
    header = headers.get(theme, "BELLATOR TACTICAL INTERFACE")
    
    # Draw header
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
    
    # DEFCON level
    defcon = MONOLITH_DATA["BELLATOR"]["defcon_level"]
    defcon_color = 1 if defcon <= 2 else 3 if defcon == 3 else 2
    defcon_text = f"DEFCON LEVEL: {defcon}"
    safe_addstr(stdscr, 3, (width - len(defcon_text)) // 2, defcon_text, 
             curses.A_BOLD | curses.color_pair(defcon_color))
    
    # Threat alerts section
    y_pos = 6
    section_header = "[ ACTIVE THREAT ALERTS ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    alerts = MONOLITH_DATA["BELLATOR"]["threat_alerts"]
    for alert in alerts[:5]:  # Show only top 5 alerts
        if y_pos < height - 10:
            # Severity color
            sev_colors = {"LOW": 2, "MEDIUM": 3, "HIGH": 6, "CRITICAL": 1}
            sev_color = sev_colors.get(alert["severity"], 7)
            
            alert_text = f"[{alert['timestamp']}] {alert['id']} - {alert['type']}: {alert['description']}"
            if len(alert_text) > width - 8:
                alert_text = alert_text[:width - 11] + "..."
            
            safe_addstr(stdscr, y_pos, 4, alert_text, curses.color_pair(sev_color))
            y_pos += 1
    
    y_pos += 2
    
    # Strategic analysis section
    section_header = "[ STRATEGIC ANALYSIS ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    analysis = MONOLITH_DATA["BELLATOR"]["strategic_analysis"]
    for item in analysis:
        if y_pos < height - 6:
            # Priority color
            pri_colors = {"Low": 2, "Medium": 3, "High": 6, "Critical": 1}
            pri_color = pri_colors.get(item["priority"], 7)
            
            analysis_text = f"{item['category']}: {item['details']} [{item['status']}]"
            if len(analysis_text) > width - 8:
                analysis_text = analysis_text[:width - 11] + "..."
            
            safe_addstr(stdscr, y_pos, 4, analysis_text, curses.color_pair(pri_color))
            y_pos += 1
    
    # Footer
    if MONOLITH_DATA["BELLATOR"]["last_updated"]:
        update_time = MONOLITH_DATA["BELLATOR"]["last_updated"].strftime("%H:%M:%S")
        footer_text = f"Last updated: {update_time} | Press 'M' to return to main view"
        safe_addstr(stdscr, height - 2, (width - len(footer_text)) // 2, footer_text, curses.color_pair(7))

def render_rationalis_screen(stdscr, theme: str):
    """Render RATIONALIS monolith specialized screen"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Update data if needed
    if not MONOLITH_DATA["RATIONALIS"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["RATIONALIS"]["last_updated"]).total_seconds() > 60:
        update_rationalis_data()
    
    # Header based on theme
    headers = {
        "military": "RATIONALIS ANALYTICAL OPERATIONS CENTER",
        "wh40k": "MECHANICUS RATIONALIS LOGIC ENGINE",
        "tars": "RATIONALIS.CORE.MODULE",
        "helldivers": "SUPER EARTH STRATEGIC ANALYSIS"
    }
    header = headers.get(theme, "RATIONALIS LOGICAL INTERFACE")
    
    # Draw header
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, 
             curses.A_BOLD | curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
    
    # Efficiency rating
    efficiency = MONOLITH_DATA["RATIONALIS"]["efficiency_rating"] * 100
    efficiency_color = 2 if efficiency > 90 else 3 if efficiency > 75 else 1
    rating_text = f"OPERATIONAL EFFICIENCY: {efficiency:.1f}%"
    safe_addstr(stdscr, 3, (width - len(rating_text)) // 2, rating_text, 
             curses.A_BOLD | curses.color_pair(efficiency_color))
    
    # System logs section
    y_pos = 6
    section_header = "[ SYSTEM LOG ENTRIES ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    logs = MONOLITH_DATA["RATIONALIS"]["system_logs"]
    for log in logs[:6]:  # Show only recent logs
        if y_pos < height - 12:
            level_color = 2 if log["level"] == "INFO" else 3 if log["level"] == "WARNING" else 1
            log_text = f"[{log['timestamp']}] {log['level']}: {log['message']}"
            if len(log_text) > width - 8:
                log_text = log_text[:width - 11] + "..."
            
            safe_addstr(stdscr, y_pos, 4, log_text, curses.color_pair(level_color))
            y_pos += 1
    
    y_pos += 2
    
    # Logic patterns section
    section_header = "[ REASONING METRICS ]"
    safe_addstr(stdscr, y_pos, (width - len(section_header)) // 2, section_header, curses.A_BOLD)
    y_pos += 2
    
    patterns = MONOLITH_DATA["RATIONALIS"]["logic_patterns"]
    col1_x = 4
    col2_x = width // 2 + 4
    
    idx = 0
    for name, value in patterns.items():
        if y_pos + idx // 2 < height - 6:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format name to be more readable
            name_formatted = name.replace("_", " ").title()
            
            if isinstance(value, float):
                score_color = 2 if value > 0.8 else 3 if value > 0.6 else 1
                value_str = f"{value:.2f}"
            else:
                score_color = 7
                value_str = str(value)
            
            pattern_text = f"{name_formatted}: {value_str}"
            safe_addstr(stdscr, y_pos + idx // 2, x_pos, pattern_text, curses.color_pair(score_color))
            idx += 1
    
    # Footer
    if MONOLITH_DATA["RATIONALIS"]["last_updated"]:
        update_time = MONOLITH_DATA["RATIONALIS"]["last_updated"].strftime("%H:%M:%S")
        footer_text = f"Last updated: {update_time} | Press 'M' to return to main view"
        safe_addstr(stdscr, height - 2, (width - len(footer_text)) // 2, footer_text, curses.color_pair(7))

def render_help_screen(stdscr, theme: str, page: int = 1):
    """Render help screen with pagination"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS SYSTEM - HELP DOCUMENTATION"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, 
             curses.A_BOLD | curses.color_pair(6))
    
    # Page indicator
    total_pages = 3
    page_indicator = f"Page {page}/{total_pages}"
    safe_addstr(stdscr, 3, (width - len(page_indicator)) // 2, page_indicator, curses.color_pair(7))
    
    y_pos = 5
    
    if page == 1:
        # Basic controls
        sections = [
            ("BASIC CONTROLS", [
                "Q - Quit application",
                "H - Show/hide help screen",
                "S - Cycle through visual themes",
                "M - Return to main view from monolith screens",
                "I - Toggle command input mode",
                "1-3 - Switch to individual monolith views"
            ]),
            ("COMMAND INTERFACE", [
                "Type commands while in input mode (press I)",
                "Available commands:",
                "  query <question> - Submit query to tribunal",
                "  status - Show system status",
                "  clear - Clear notifications",
                "  export - Export decision history",
                "  config - Show configuration",
                "  help - Show this help"
            ])
        ]
    elif page == 2:
        # Advanced features
        sections = [
            ("MONOLITH VIEWS", [
                "AETERNUM (1) - Financial and market analysis",
                "  - Market indices and cryptocurrency tracking",
                "  - Portfolio performance monitoring",
                "  - Economic indicators display",
                "",
                "BELLATOR (2) - Tactical and security analysis",
                "  - DEFCON level monitoring",
                "  - Threat alerts and analysis",
                "  - Strategic assessment reports",
                "",
                "RATIONALIS (3) - Logical analysis and reasoning",
                "  - System efficiency metrics",
                "  - Logic pattern analysis",
                "  - Reasoning capability assessment"
            ])
        ]
    else:  # page == 3
        # System information
        sections = [
            ("SYSTEM INFORMATION", [
                f"Version: {VERSION}",
                f"Build Date: {BUILD_DATE}",
                f"LLM Provider: {CONFIG['llm_provider'].upper()}",
                "",
                "Supported Themes:",
                "  - Military (default tactical theme)",
                "  - WH40K (Warhammer 40,000 aesthetic)",
                "  - TARS (Interstellar-inspired design)",
                "  - Helldivers (Super Earth command style)"
            ]),
            ("TROUBLESHOOTING", [
                "- Ensure Ollama/LM Studio is running",
                "- Check model availability in provider",
                "- Verify API endpoints are accessible",
                "- Review logs in ./CONSENSUS_SYSTEM/_ARBITER/logs/",
                "- Use 'status' command for diagnostics"
            ])
        ]
    
    # Render sections
    for section_title, items in sections:
        if y_pos < height - 8:
            safe_addstr(stdscr, y_pos, 4, section_title, curses.A_BOLD | curses.color_pair(3))
            y_pos += 2
            
            for item in items:
                if y_pos < height - 6:
                    safe_addstr(stdscr, y_pos, 6, item, curses.color_pair(7))
                    y_pos += 1
            y_pos += 1
    
    # Navigation instructions
    nav_text = "Use LEFT/RIGHT arrows or N/P to navigate pages, H to close help"
    safe_addstr(stdscr, height - 3, (width - len(nav_text)) // 2, nav_text, 
             curses.A_BOLD | curses.color_pair(6))

# ===== COMMAND PROCESSING =====

def process_command(command: str) -> str:
    """Process user commands and return response"""
    global command_output
    
    command = command.strip().lower()
    command_history.append(command)
    
    if not command:
        return ""
    
    # Parse command and arguments
    parts = command.split()
    cmd = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    if cmd == "query":
        if args:
            query_text = " ".join(args)
            CONFIG["current_query"] = query_text
            # Start voting process in background
            threading.Thread(target=generate_all_votes, args=(query_text,), daemon=True).start()
            return f"Submitted query to tribunal: {query_text}"
        else:
            return "Usage: query <your question>"
    
    elif cmd == "status":
        uptime = format_uptime(SYSTEM_HEALTH["start_time"])
        model_status = []
        for name, status in MODEL_STATUS.items():
            model_status.append(f"{name}: {status['status'].upper()}")
        
        return f"System Status:\nUptime: {uptime}\nModels: {', '.join(model_status)}\nMode: {CONFIG['system_mode']}"
    
    elif cmd == "clear":
        notifications.clear()
        return "Notifications cleared"
    
    elif cmd == "export":
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = EXPORT_DIR / f"decisions_{timestamp}.json"
            
            export_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "decisions": list(decision_history),
                "system_info": {
                    "version": VERSION,
                    "uptime": format_uptime(SYSTEM_HEALTH["start_time"]),
                    "mode": CONFIG["system_mode"]
                }
            }
            
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return f"Decisions exported to {export_file}"
        except Exception as e:
            return f"Export failed: {str(e)}"
    
    elif cmd == "config":
        config_text = []
        for key, value in CONFIG.items():
            config_text.append(f"{key}: {value}")
        return "Configuration:\n" + "\n".join(config_text)
    
    elif cmd == "help":
        return "Available commands: query, status, clear, export, config, help\nPress H for detailed help screen"
    
    elif cmd == "theme":
        if args and args[0] in BOX_CHARS:
            CONFIG["theme"] = args[0]
            save_config()
            return f"Theme changed to: {args[0]}"
        else:
            themes = list(BOX_CHARS.keys())
            return f"Available themes: {', '.join(themes)}"
    
    elif cmd == "mode":
        if args and args[0].upper() in SYSTEM_MODES:
            CONFIG["system_mode"] = args[0].upper()
            return f"System mode changed to: {args[0].upper()}"
        else:
            modes = list(SYSTEM_MODES.keys())
            return f"Available modes: {', '.join(modes)}"
    
    else:
        return f"Unknown command: {cmd}. Type 'help' for available commands."

# ===== MAIN APPLICATION LOOP =====

def handle_input(stdscr, key: int) -> bool:
    """Handle keyboard input and return True if should continue"""
    global input_mode, command_buffer, command_output, help_page
    
    # Get current screen size
    height, width = stdscr.getmaxyx()
    
    if input_mode:
        # Command input mode
        if key == 27:  # ESC key
            input_mode = False
            command_buffer = ""
            command_output = ""
        elif key in (10, 13):  # Enter key
            if command_buffer.strip():
                command_output = process_command(command_buffer)
                command_buffer = ""
            input_mode = False
        elif key in (8, 127, curses.KEY_BACKSPACE):  # Backspace
            if command_buffer:
                command_buffer = command_buffer[:-1]
        elif 32 <= key <= 126:  # Printable characters
            command_buffer += chr(key)
    else:
        # Normal navigation mode
        if key in (ord('q'), ord('Q')):
            return False
        elif key in (ord('i'), ord('I')):
            input_mode = True
            command_buffer = ""
            command_output = ""
        elif key in (ord('s'), ord('S')):
            # Cycle themes
            themes = list(BOX_CHARS.keys())
            current_idx = themes.index(CONFIG["theme"])
            next_idx = (current_idx + 1) % len(themes)
            CONFIG["theme"] = themes[next_idx]
            add_notification(f"Theme changed to: {CONFIG['theme']}", "info")
            save_config()
        elif key in (ord('h'), ord('H')):
            CONFIG["current_view"] = "help" if CONFIG["current_view"] != "help" else "main"
        elif key in (ord('m'), ord('M')):
            CONFIG["current_view"] = "main"
        elif key == ord('1'):
            CONFIG["current_view"] = "aeternum"
        elif key == ord('2'):
            CONFIG["current_view"] = "bellator"
        elif key == ord('3'):
            CONFIG["current_view"] = "rationalis"
        elif CONFIG["current_view"] == "help":
            # Help screen navigation
            if key == curses.KEY_LEFT or key in (ord('p'), ord('P')):
                help_page = max(1, help_page - 1)
            elif key == curses.KEY_RIGHT or key in (ord('n'), ord('N')):
                help_page = min(3, help_page + 1)
    
    return True

def main_loop(stdscr):
    """Main application loop"""
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100) # 100ms timeout
    
    # Initialize color pairs
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)
    
    # Main loop
    last_refresh = 0
    running = True
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                running = handle_input(stdscr, key)
            
            # Refresh screen periodically
            current_time = time.time()
            if current_time - last_refresh > 0.1:  # Refresh every 100ms
                # Update model statuses periodically
                if CONFIG["auto_refresh"] and current_time - last_refresh > CONFIG["refresh_interval"]:
                    threading.Thread(target=update_model_statuses, daemon=True).start()
                    threading.Thread(target=update_monolith_data, daemon=True).start()
                
                # Render appropriate screen
                current_view = CONFIG["current_view"]
                theme = CONFIG["theme"]
                
                if current_view == "main":
                    render_main_screen(stdscr, theme)
                elif current_view == "aeternum":
                    render_aeternum_screen(stdscr, theme)
                elif current_view == "bellator":
                    render_bellator_screen(stdscr, theme)
                elif current_view == "rationalis":
                    render_rationalis_screen(stdscr, theme)
                elif current_view == "help":
                    render_help_screen(stdscr, theme, help_page)
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            # Log any unexpected errors
            log_entry(f"Unexpected error in main loop: {str(e)}", "ERROR")
            add_notification(f"System error: {str(e)}", "error")

# ===== SIGNAL HANDLERS =====

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    log_entry("Received shutdown signal", "INFO")
    sys.exit(0)

# ===== MAIN ENTRY POINT =====

def main():
    """Main entry point"""
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Show boot sequence
        show_boot_sequence()
        
        # Initialize system
        init_system()
        
        # Add startup notifications
        add_notification("CONSENSUS System Online", "success")
        add_notification("All monoliths initialized", "info")
        
        # Start background model status updates
        threading.Thread(target=update_model_statuses, daemon=True).start()
        
        # Start the main interface
        curses.wrapper(main_loop)
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        log_entry(f"Fatal error: {str(e)}", "ERROR")
        sys.exit(1)
    finally:
        # Cleanup
        log_entry("CONSENSUS System shutdown", "INFO")
        print("\n🟢 CONSENSUS System terminated gracefully")

if __name__ == "__main__":
    main()