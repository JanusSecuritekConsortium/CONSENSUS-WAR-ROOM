

# ================================================================================
#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (Optimized)

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
Version: 2.2.0
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

VERSION = "2.2.0"
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
    "max_decision_history": 20
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
    CONFIG["current_view"] = "VOTING"
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
        CONFIG["current_view"] = "CONSENSUS"
        add_notification(f"Consensus reached: {consensus}", "success")
        add_decision_to_history(query, consensus)
        log_entry(f"Consensus achieved: {consensus} in {total_time:.2f}s", "SUCCESS")
    else:
        CONFIG["current_view"] = "DEADLOCK"
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
        except Exception:
            # Fallback to simulated values
            SYSTEM_HEALTH["cpu"] = random.uniform(10, 30)
            SYSTEM_HEALTH["memory"] = random.uniform(40, 70)
            SYSTEM_HEALTH["disk"] = random.uniform(20, 50)
            SYSTEM_HEALTH["network"] = random.uniform(1, 10)
    else:
        # Simulated values when psutil not available
        SYSTEM_HEALTH["cpu"] = random.uniform(10, 30)
        SYSTEM_HEALTH["memory"] = random.uniform(40, 70)
        SYSTEM_HEALTH["disk"] = random.uniform(20, 50)
        SYSTEM_HEALTH["network"] = random.uniform(1, 10)

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

import textwrap
# ===== FILE: consensus_war_room.py =====
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
        pass
    elif theme == "wh40k":
        pass
    elif theme == "tars":
        pass
    elif theme == "helldivers":
        pass
    else:
        pass
        
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
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
                pass
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
    # Removed corrupted safe_addstr line
            
    for name, data in indices.items():
        if y_pos + idx//2 < height - 5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["trend"] == "up" else 1
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
    "AETERNUM": {
        "id": 1,
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
        "id": 2,
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
    },
    "RATIONALIS": {
        "id": 3,
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
    },
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
            f.write(f"[{timestamp}] [{level}] {message}\\n")
    except Exception as e:
        pass
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
        bottom_y = height - 5
        message_x = (width - len(message)) // 2
        safe_addstr(stdscr, bottom_y, 0, " " * width)
        stdscr.attron(curses.color_pair(7))
        safe_addstr(stdscr, bottom_y, message_x, message)
        stdscr.attroff(curses.color_pair(7))
        progress_width = 20
        progress = "█" * (i + 1) + "░" * (len(boot_messages) - i - 1)
        progress_x = (width - progress_width) // 2
        safe_addstr(stdscr, bottom_y + 2, progress_x, progress)
        stdscr.refresh()
        time.sleep(0.5)

time.sleep(1)
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw NERV logo in red
    logo_lines = NERV_LOGO.split('\n')
    for i, line in enumerate(logo_lines):
        if i < height and line.strip():  # Skip empty lines
            # Use color pair 1 (red) for the logo
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(stdscr, i, max(0, (width - len(line)) // 2), line)
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    
    # Display version information below the logo
    version_text = f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"
    safe_addstr(stdscr, len(logo_lines), (width - len(version_text)) // 2, version_text, curses.color_pair(6) | curses.A_BOLD)
    
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
            pass
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
                pass
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
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
                pass
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
    footer = "Press '2' to return to main view"
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
        pass
    elif theme == "wh40k":
        pass
    elif theme == "tars":
        pass
    elif theme == "helldivers":
        pass
    else:
        pass
        
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
        pass
        rationalis_len = int(balance["rationalis_influence"] * 30)
        aeternum_len = int(balance["aeternum_influence"] * 30)
        bellator_len = int(balance["bellator_influence"] * 30)
        
        safe_addstr(stdscr, y_pos, 4, "Rationalis: ", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
        safe_addstr(stdscr, y_pos, 15, "[" + "#" * rationalis_len + " " * (30 - rationalis_len) + "]", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+1, 4, "Aeternum:  ", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
        safe_addstr(stdscr, y_pos+1, 15, "[" + "#" * aeternum_len + " " * (30 - aeternum_len) + "]", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+2, 4, "Bellator:  ", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
        safe_addstr(stdscr, y_pos+2, 15, "[" + "#" * bellator_len + " " * (30 - bellator_len) + "]", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
    # Removed corrupted f-string call
        
        # Consensus and conflict rates
        consensus_color = 2 if balance["consensus_rate"] > 0.7 else 3 if balance["consensus_rate"] > 0.5 else 1
        conflict_color = 2 if balance["conflict_rate"] < 0.3 else 3 if balance["conflict_rate"] < 0.5 else 1
        
    # Removed corrupted f-string call
    # Removed corrupted f-string call
    
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
        pass
        page = 1
        max_page = 2
        
        # Page indicator
        page_text = f"Page {help_page}/{max_page} (Press SPACE for next page)"
        safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(page_text)) // 2, 
                   page_text, curses.A_BOLD)
        
        if help_page == 1:
            pass
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
            pass
            for category, commands in list(command_categories.items())[3:]:
                safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
                current_y += 1
                
                for cmd in commands:
                    safe_addstr(stdscr, current_y, help_x + 4, cmd)
                    current_y += 1
                
                current_y += 1
    else:
        pass
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
                pass
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
        pass
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
        pass
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
        pass
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
        pass
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
        pass
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
        pass
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
        pass
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
                pass
                if "analysis" not in MONOLITH_DATA["AETERNUM"]:
                    MONOLITH_DATA["AETERNUM"]["analysis"] = []
                MONOLITH_DATA["AETERNUM"]["analysis"].insert(0, answer)
            elif monolith_name.upper() == "RATIONALIS":
                pass
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
    global CURRENT_VIEW, CURRENT_MODE, command_output, STYLE, CONFIG, active_monolith
    
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
            CURRENT_VIEW = f"MONOLITH_{monolith}"
            threading.Thread(target=handle_monolith_query, args=(monolith, query), daemon=True).start()
            return f"Querying {monolith} with: {query}"
        else:
            return f"Usage: {cmd} <query>"
    
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
        pass
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
    global CURRENT_VIEW, input_mode, command_buffer, command_output, help_page
    
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
            pass
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
        pass
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
        pass
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Start the application
    try:
        pass
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'TERM_PROGRAM' in os.environ and os.environ['TERM_PROGRAM'] == 'iTerm.app':
        pass
            print("If you're using iTerm2, try increasing the terminal window size.")

# ===== FILE: CONSENSUS_WAR_ROOM3.py =====
        elif key == ord('1'):
        if view_mode == "MONOLITH_BELLATOR":
        view_mode = "MAIN"
        add_notification("Returned to main view", "info")
        else:
        view_mode = "MONOLITH_BELLATOR"
        add_notification("Accessing Bellator tactical systems", "info")
        elif key == ord('2'):
        if view_mode == "MONOLITH_AETERNUM":
        view_mode = "MAIN"
        add_notification("Returned to main view", "info")
        else:
        view_mode = "MONOLITH_AETERNUM"
        add_notification("Accessing Aeternum financial systems", "info")
        elif key == ord('3'):
        if view_mode == "MONOLITH_RATIONALIS":
        view_mode = "MAIN"
        add_notification("Returned to main view", "info")
        else:
        view_mode = "MONOLITH_RATIONALIS"
        add_notification("Accessing Rationalis analytical systems", "info")
        elif key == ord('4'):
        if view_mode == "MONOLITH_ARBITER":
        view_mode = "MAIN"
        add_notification("Returned to main view", "info")
        else:
        view_mode = "MONOLITH_ARBITER"
        add_notification("Accessing Arbiter control systems", "info")# Drawing functions for monolith screens

def draw_bellator_screen(stdscr, h, w, theme):
    """Draw the Bellator monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Bellator"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Bellator"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(3))  # Bellator color (MAGENTA)
    
    # Draw DEFCON level
    defcon = MONOLITH_DATA["Bellator"]["defcon_level"]
    defcon_color = 6 if defcon <= 2 else 5 if defcon == 3 else 4  # Red, Yellow, Green
    
if theme == "military":
        defcon_text = f"DEFENSE CONDITION: DEFCON {defcon}"
        elif theme == "wh40k":
        defcon_text = f"IMPERIUM THREAT LEVEL: VERMILLION {defcon}"
        elif theme == "tars":
        defcon_text = f"SECURITY.CONDITION={defcon}"
        elif theme == "helldivers":
        defcon_text = f"LIBERTY THREAT INDEX: {defcon}"
        
    safe_addstr(stdscr, 3, w//2 - len(defcon_text)//2, defcon_text, 
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, alert in enumerate(MONOLITH_DATA["Bellator"]["threat_alerts"]):
        if y_pos + idx < h-5:
            level_color = 4 if alert["level"] == "Low" else 5 if alert["level"] == "Moderate" or alert["level"] == "Elevated" else 6
            alert_text = f"{alert['region']}: {alert['level']} - {alert['description']}"
            safe_addstr(stdscr, y_pos + idx, 4, alert_text, curses.color_pair(level_color))
    
    y_pos += len(MONOLITH_DATA["Bellator"]["threat_alerts"]) + 1
    
    # Strategic analysis
if theme == "military":
        section_header = "[ STRATEGIC ANALYSIS ]"
        elif theme == "wh40k":
        section_header = "[ TACTICAL COGITATION ]"
        elif theme == "tars":
        section_header = "[ ANALYSIS.MATRIX ]"
        elif theme == "helldivers":
        section_header = "[ SUPER EARTH INTELLIGENCE ]"
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, analysis in enumerate(MONOLITH_DATA["Bellator"]["strategic_analysis"]):
        if y_pos + idx < h-5:
            safe_addstr(stdscr, y_pos + idx, 4, f"- {analysis}")
    
    y_pos += len(MONOLITH_DATA["Bellator"]["strategic_analysis"]) + 1
    
    # News items
if theme == "military":
        section_header = "[ INTELLIGENCE BRIEFING ]"
        elif theme == "wh40k":
        section_header = "[ ASTROPATHIC DISPATCHES ]"
        elif theme == "tars":
        section_header = "[ NEWS.FEED ]"
        elif theme == "helldivers":
        section_header = "[ DEMOCRACY BROADCASTS ]"
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, news in enumerate(MONOLITH_DATA["Bellator"]["security_news"]):
        if y_pos + idx < h-5:
            news_text = f"{news['title']} - {news['source']} ({news['time']})"
            safe_addstr(stdscr, y_pos + idx, 4, news_text)
    
    # Footer
        if MONOLITH_DATA["Bellator"]["last_updated"]:
        update_time = MONOLITH_DATA["Bellator"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '1' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_aeternum_screen(stdscr, h, w, theme):
    """Draw the Aeternum monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Aeternum"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Aeternum"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(1))  # Aeternum color (CYAN)
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indices = MONOLITH_DATA["Aeternum"]["market_indices"]
    col1_x = 4
    col2_x = w // 2 + 4
    
    idx = 0
    for name, data in indices.items():
        if y_pos + idx//2 < h-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["trend"] == "up" else 6  # Green or Red
            value_str = f"{data['value']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    crypto = MONOLITH_DATA["Aeternum"]["crypto_prices"]
    idx = 0
    for name, data in crypto.items():
        if y_pos + idx//2 < h-10:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["change"] > 0 else 6  # Green or Red
            price_str = f"${data['price']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    portfolio = MONOLITH_DATA["Aeternum"]["portfolio_performance"]
    
    # Time-based performance
    perf_y = y_pos
    for period, change in [("Daily", portfolio["daily_change"]), 
                           ("Weekly", portfolio["weekly_change"]), 
                           ("Monthly", portfolio["monthly_change"]), 
                           ("Yearly", portfolio["yearly_change"])]:
        if perf_y < h-10:
            change_color = 4 if change > 0 else 6  # Green or Red
    # Removed corrupted f-string call
            safe_addstr(stdscr, perf_y, col1_x, perf_text, curses.color_pair(change_color))
            perf_y += 1
    
    # Top and worst performers
        if y_pos < h-10:
        top_text = f"Top: {', '.join(portfolio['top_performers'])}"
        worst_text = f"Worst: {', '.join(portfolio['worst_performers'])}"
        safe_addstr(stdscr, y_pos, col2_x, top_text, curses.color_pair(4))
        safe_addstr(stdscr, y_pos+1, col2_x, worst_text, curses.color_pair(6))
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indicators = MONOLITH_DATA["Aeternum"]["economic_indicators"]
    idx = 0
    for name, value in indicators.items():
        if y_pos + idx//3 < h-5:
            column = idx % 3
            x_pos = col1_x + (column * (w // 3))
            
            # Format based on indicator
        if name == "inflation" or name == "unemployment" or name == "fed_rate" or name == "treasury_10y":
        pass
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
        if MONOLITH_DATA["Aeternum"]["last_updated"]:
        update_time = MONOLITH_DATA["Aeternum"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '2' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_rationalis_screen(stdscr, h, w, theme):
    """Draw the Rationalis monolith specialized screen"""
    # Create a full-screen view
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Rationalis"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Rationalis"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(2))  # Rationalis color (BLUE)
    
    # Draw efficiency rating
    efficiency = MONOLITH_DATA["Rationalis"]["efficiency_rating"] * 100
    efficiency_color = 4 if efficiency > 90 else 5 if efficiency > 75 else 6
    
if theme == "military":
        pass
        elif theme == "wh40k":
        pass
        elif theme == "tars":
        pass
        elif theme == "helldivers":
        pass
    safe_addstr(stdscr, 3, w//2 - len(rating_text)//2, rating_text, 
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    logs = MONOLITH_DATA["Rationalis"]["system_logs"]
    for idx, log in enumerate(logs):
        if y_pos + idx < h-12:
            level_color = 4 if log["level"] == "INFO" else 5 if log["level"] == "WARNING" else 6
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    patterns = MONOLITH_DATA["Rationalis"]["logic_patterns"]
    col1_x = 4
    col2_x = w // 2 + 4
    
    idx = 0
    for name, value in patterns.items():
        if y_pos + idx//2 < h-8 and name != "logical_fallacies_detected":
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
        if isinstance(value, float):
                score_color = 4 if value > 0.8 else 5 if value > 0.6 else 6
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
                 curses.color_pair(5 if patterns['logical_fallacies_detected'] < 10 else 6))
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    metrics = MONOLITH_DATA["Rationalis"]["analysis_metrics"]
    idx = 0
    for name, value in metrics.items():
        if y_pos + idx//2 < h-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
        if isinstance(value, float):
                score_color = 4 if value > 0.8 else 5 if value > 0.6 else 6
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
        if MONOLITH_DATA["Rationalis"]["last_updated"]:
        update_time = MONOLITH_DATA["Rationalis"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '3' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_arbiter_screen(stdscr, h, w, theme):
    """Draw the Arbiter specialized screen"""
    # Create a full-screen view
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Arbiter"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Arbiter"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with custom color (white bold)
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, curses.A_BOLD | curses.color_pair(7))
    
    # System status
    y_pos = 3
    status = MONOLITH_DATA["Arbiter"]["system_status"]
    status_text = ""
    
if theme == "military":
        status_text = f"SYSTEM STATUS: {status['monoliths_online']}/3 MONOLITHS ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
        elif theme == "wh40k":
        status_text = f"MECHANICUS STATUS: {status['monoliths_online']}/3 ACTIVE | ASTROPATH: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
        elif theme == "tars":
        status_text = f"SYSTEM.STATUS: ACTIVE={status['monoliths_online']}/3 COMMS={status['communication_integrity']*100:.1f}% RATE={status['decision_throughput']:.1f}/h"
        elif theme == "helldivers":
        status_text = f"DEMOCRACY STATUS: {status['monoliths_online']}/3 ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | LIBERTY RATE: {status['decision_throughput']:.1f}/h"
    
    safe_addstr(stdscr, y_pos, w//2 - len(status_text)//2, status_text, curses.A_BOLD)
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    agenda = MONOLITH_DATA["Arbiter"]["agenda"]
    for idx, item in enumerate(agenda):
        if y_pos + idx < h-12:
            priority_color = 4 if item["priority"] == "Low" else 5 if item["priority"] == "Medium" else 6
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    decisions = MONOLITH_DATA["Arbiter"]["pending_decisions"]
    for idx, decision in enumerate(decisions):
        if y_pos + idx < h-8:
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    balance = MONOLITH_DATA["Arbiter"]["balance_metrics"]
    
    # Draw a balance chart
        if y_pos + 4 < h-6:
        pass
        rationalis_len = int(balance["rationalis_influence"] * 30)
        aeternum_len = int(balance["aeternum_influence"] * 30)
        bellator_len = int(balance["bellator_influence"] * 30)
        
        safe_addstr(stdscr, y_pos, 4, "Rationalis: ", curses.color_pair(2))
        safe_addstr(stdscr, y_pos, 15, "[" + "#" * rationalis_len + " " * (30 - rationalis_len) + "]", curses.color_pair(2))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+1, 4, "Aeternum:  ", curses.color_pair(1))
        safe_addstr(stdscr, y_pos+1, 15, "[" + "#" * aeternum_len + " " * (30 - aeternum_len) + "]", curses.color_pair(1))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+2, 4, "Bellator:  ", curses.color_pair(3))
        safe_addstr(stdscr, y_pos+2, 15, "[" + "#" * bellator_len + " " * (30 - bellator_len) + "]", curses.color_pair(3))
    # Removed corrupted f-string call
        
        # Consensus and conflict rates
        consensus_color = 4 if balance["consensus_rate"] > 0.7 else 5 if balance["consensus_rate"] > 0.5 else 6
        conflict_color = 4 if balance["conflict_rate"] < 0.3 else 5 if balance["conflict_rate"] < 0.5 else 6
        
    # Removed corrupted f-string call
    # Removed corrupted f-string call
    
    # Footer
        if MONOLITH_DATA["Arbiter"]["last_updated"]:
        update_time = MONOLITH_DATA["Arbiter"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '4' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)# Add functions for getting monolith-specific data

def update_bellator_data():
    """Update Bellator's security and military data"""
    try:
        pass
        
        # Simulated DEFCON level (would come from official sources if available)
        MONOLITH_DATA["Bellator"]["defcon_level"] = random.randint(3, 5)
        
        # Simulated threat alerts (would come from news APIs)
        MONOLITH_DATA["Bellator"]["threat_alerts"] = [
            {"region": "Middle East", "level": "Elevated", "description": "Increased tension in regional conflict zones"},
            {"region": "Cybersecurity", "level": "High", "description": "Multiple attacks targeting financial institutions"},
            {"region": "Pacific", "level": "Moderate", "description": "Naval exercises causing diplomatic tension"}
        ]
        
        # Simulated news (would come from NewsAPI)
        MONOLITH_DATA["Bellator"]["security_news"] = [
            {"title": "New Defense Pact Signed Between Major Powers", "source": "World Politics", "time": "3h ago"},
            {"title": "Cybersecurity Breach Affects Military Contractors", "source": "Tech Defense", "time": "8h ago"},
            {"title": "Strategic Resource Discovered in Disputed Territory", "source": "Resource Monitor", "time": "12h ago"}
        ]
        
        # Strategic analysis (would be generated by the Bellator monolith)
        MONOLITH_DATA["Bellator"]["strategic_analysis"] = [
            "Primary threats concentrated in cyber domain with 64% increase in state-sponsored attacks",
            "Resource contention increasing risk of conflict in 3 key regions",
            "Defensive posture recommended with emphasis on intelligence gathering"
        ]
        
        MONOLITH_DATA["Bellator"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Bellator data: {e}")
        return False

def update_aeternum_data():
    """Update Aeternum's financial and market data"""
    try:
        pass
        
        # Market indices (would come from Yahoo Finance or similar)
        MONOLITH_DATA["Aeternum"]["market_indices"] = {
            "S&P 500": {"value": 5123.45, "change": 0.75, "trend": "up"},
            "Dow Jones": {"value": 37893.21, "change": -0.12, "trend": "down"},
            "NASDAQ": {"value": 16789.34, "change": 1.42, "trend": "up"},
            "FTSE 100": {"value": 7825.68, "change": 0.31, "trend": "up"}
        }
        
        # Cryptocurrency prices (would come from CoinGecko or Binance)
        MONOLITH_DATA["Aeternum"]["crypto_prices"] = {
            "Bitcoin": {"price": 62453.21, "change": 2.3, "market_cap": "1.2T"},
            "Ethereum": {"price": 3245.67, "change": 1.5, "market_cap": "389B"},
            "Solana": {"price": 165.32, "change": 5.4, "market_cap": "76B"},
            "Cardano": {"price": 0.59, "change": -1.2, "market_cap": "21B"}
        }
        
        # Portfolio performance (simulated, would come from broker API)
        MONOLITH_DATA["Aeternum"]["portfolio_performance"] = {
            "daily_change": 0.86,
            "weekly_change": 2.34,
            "monthly_change": -1.45,
            "yearly_change": 12.67,
            "top_performers": ["NVDA", "MSFT", "AMZN"],
            "worst_performers": ["IBM", "INTC", "T"]
        }
        
        # Economic indicators (would come from financial APIs)
        MONOLITH_DATA["Aeternum"]["economic_indicators"] = {
            "inflation": 2.4,
            "unemployment": 3.7,
            "fed_rate": 3.75,
            "treasury_10y": 3.45,
            "oil_price": 74.32
        }
        
        MONOLITH_DATA["Aeternum"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Aeternum data: {e}")
        return False

def update_rationalis_data():
    """Update Rationalis's logic and analysis data"""
    try:
        pass
        MONOLITH_DATA["Rationalis"]["system_logs"] = [
            {"timestamp": "15:42:23", "level": "INFO", "message": "Analysis framework optimized, +12% efficiency"},
            {"timestamp": "14:37:01", "level": "WARNING", "message": "Recursive pattern detected in query syntax"},
            {"timestamp": "12:15:49", "level": "INFO", "message": "Knowledge base updated with 537 new entries"}
        ]
        
        # Logic patterns (simulated ML metrics)
        MONOLITH_DATA["Rationalis"]["logic_patterns"] = {
            "inductive_reasoning": 0.87,
            "deductive_reasoning": 0.93,
            "abductive_reasoning": 0.76,
            "analogical_reasoning": 0.82,
            "logical_fallacies_detected": 7
        }
        
        # Analysis metrics
        MONOLITH_DATA["Rationalis"]["analysis_metrics"] = {
            "query_complexity_avg": 7.8,
            "inference_depth_avg": 12.3,
            "contextual_awareness": 0.85,
            "bias_detection": 0.91,
            "factual_accuracy": 0.94
        }
        
        # Efficiency rating (simulated)
        MONOLITH_DATA["Rationalis"]["efficiency_rating"] = random.uniform(0.88, 0.97)
        
        MONOLITH_DATA["Rationalis"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Rationalis data: {e}")
        return False

def update_arbiter_data():
    """Update Arbiter's management and coordination data"""
    try:
        pass
        MONOLITH_DATA["Arbiter"]["agenda"] = [
            {"time": "10:00", "task": "Security protocol review", "priority": "High"},
            {"time": "13:30", "task": "Financial market analysis", "priority": "Medium"},
            {"time": "15:45", "task": "Strategic planning session", "priority": "High"},
            {"time": "17:00", "task": "System optimization", "priority": "Low"}
        ]
        
        # Pending decisions (based on actual CONSENSUS data)
        MONOLITH_DATA["Arbiter"]["pending_decisions"] = [
            {"query": "Authorize fund reallocation to defensive assets?", "status": "Under review"},
            {"query": "Increase security monitoring in sector 7?", "status": "Awaiting consensus"},
            {"query": "Deploy new analytical model v4.3?", "status": "Data collection"}
        ]
        
        # System status
        MONOLITH_DATA["Arbiter"]["system_status"] = {
            "monoliths_online": 3,
            "communication_integrity": 0.99,
            "decision_throughput": 8.4,
            "balance_index": 0.87
        }
        
        # Balance metrics (measuring how well the monoliths are working together)
        MONOLITH_DATA["Arbiter"]["balance_metrics"] = {
            "rationalis_influence": 0.33,
            "aeternum_influence": 0.35,
            "bellator_influence": 0.32,
            "consensus_rate": 0.76,
            "conflict_rate": 0.21
        }
        
        MONOLITH_DATA["Arbiter"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Arbiter data: {e}")
        return False# External API configuration - placeholders for now
API_CONFIG = {
    "finance": {
        "yahoo_finance": {
            "enabled": False,
            "api_key": "YOUR_API_KEY",  # Would be replaced with actual key
            "url": "https://yfapi.net"
        },
        "alpha_vantage": {
            "enabled": False,
            "api_key": "YOUR_API_KEY", 
            "url": "https://www.alphavantage.co/query"
        },
        "coingecko": {
            "enabled": False,
            "url": "https://api.coingecko.com/api/v3"  # No API key needed for basic access
        }
    },
    "security": {
        "newsapi": {
            "enabled": False,
            "api_key": "YOUR_API_KEY",
            "url": "https://newsapi.org/v2"
        },
        "gdelt": {
            "enabled": False,
            "url": "https://api.gdeltproject.org/api/v2"  # No API key needed
        }
    }
}            # Process input for help page navigation
        if view_mode == "HELP" and not input_mode:
        if key == ord(' '):  # Space key for pagination
                    help_page = 2 if help_page == 1 else 1  # Toggle between pages
        else:
        pass
        view_mode = "MAIN"def draw_help_screen(stdscr, h, w, theme):
    """Draw a comprehensive help screen with all commands"""
    # Create a help overlay
    help_height = h - 6
    help_width = w - 6
    help_y = 3
    help_x = 3
    
    # Clear screen and draw help box
    for i in range(help_y, help_y + help_height):
        blank_line = " " * help_width
        safe_addstr(stdscr, i, help_x, blank_line)
    
    draw_box(stdscr, help_y, help_x, help_width, help_height, "HELP: KEYBOARD SHORTCUTS & COMMANDS")
    
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
        pass
        page = 1
        max_page = 2
        
        # Page indicator
        page_text = f"Page {page}/{max_page} (Press SPACE for next page)"
        safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(page_text)) // 2, 
                   page_text, curses.A_BOLD)
        
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
        pass
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
               footer, curses.A_BOLD)def add_notification(message, level="info"):
    """Add a notification to the notification queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now(),
        "seen": False
    })

def update_system_health():
    """Update system health metrics"""
        if psutil:
        try:
            system_health["cpu_usage"] = psutil.cpu_percent()
            system_health["memory_usage"] = psutil.virtual_memory().percent
        except Exception as e:
        pass
            system_health["cpu_usage"] = 0
            system_health["memory_usage"] = 0
        else:
        pass
        system_health["cpu_usage"] = 0
        system_health["memory_usage"] = 0
    
    # Calculate average response time
        if system_health["response_times"]:
        system_health["avg_response_time"] = sum(system_health["response_times"]) / len(system_health["response_times"])

def record_response_time(start_time):
    """Record response time for a query"""
    response_time = time.time() - start_time
    system_health["response_times"].append(response_time)
    
    # Update average
        if len(system_health["response_times"]) > 0:
        system_health["avg_response_time"] = sum(system_health["response_times"]) / len(system_health["response_times"])
    
    return response_time

def export_history(format_type="json"):
    """Export decision history to a file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
        if format_type.lower() == "json":
        filename = f"consensus_history_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(list(decision_history), f, indent=2, default=str)
        elif format_type.lower() == "csv":
        filename = f"consensus_history_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Query", "Verdict", "Reasoning"])
            for decision in decision_history:
                writer.writerow([
                    decision["timestamp"],
                    decision["query"],
                    decision["verdict"],
                    decision["reasoning"]
                ])
        else:
        return f"Unsupported format: {format_type}"
    
    return f"History exported to {filename}"

def get_command_suggestions(partial_command):
    """Get command suggestions based on partial input"""
    commands = [
        "query", "critical", "normal", "style", "load", "use ollama", "use lmstudio",
        "status", "vote", "consensus", "ibkr connect", "ibkr status", "ibkr stock",
        "help", "history", "export json", "export csv", "template", "config", 
        "notifications", "health", "dark", "light", "quit", "reload"
    ]
    
        if not partial_command:
        return []
    
    # Filter commands that start with the partial command
    return [cmd for cmd in commands if cmd.startswith(partial_command.lower())]

def apply_template(template_name, params=None):
    """Apply a query template with parameters"""
        if template_name not in QUERY_TEMPLATES:
        return f"Unknown template: {template_name}"
    
    template = QUERY_TEMPLATES[template_name]
    
        if not params:
        pass
        return template
    
    try:
        pass
        param_dict = {}
        param_pairs = params.split(',')
        for pair in param_pairs:
        if '=' in pair:
                key, value = pair.split('=', 1)
                param_dict[key.strip()] = value.strip()
        
        return template.format(**param_dict)
    except Exception as e:
        return f"Error applying template: {str(e)}"

def draw_response_time_graph(stdscr, y, x, width, height):
    """Draw a simple response time graph"""
        if not system_health["response_times"]:
        safe_addstr(stdscr, y + height // 2, x + width // 2 - 10, "No data available")
        return
    
    # Draw axes
    for i in range(height):
        safe_addstr(stdscr, y + i, x, "|")
    
    for i in range(width):
        safe_addstr(stdscr, y + height - 1, x + i, "_")
    
    # Calculate scale
    max_time = max(system_health["response_times"])
    scale = (height - 2) / max_time if max_time > 0 else 1
    
    # Draw data points
    data_points = list(system_health["response_times"])[-width:]
    for i, point in enumerate(data_points):
        if i < width:
            point_height = min(int(point * scale), height - 2)
            safe_addstr(stdscr, y + (height - 2) - point_height, x + i + 1, "*", curses.color_pair(5))
    
    # Draw average line
    avg_height = min(int(system_health["avg_response_time"] * scale), height - 2)
    for i in range(min(width, len(data_points))):
        safe_addstr(stdscr, y + (height - 2) - avg_height, x + i + 1, "-", curses.color_pair(4))
    
    # Draw scale
    safe_addstr(stdscr, y, x - 5, f"{max_time:.1f}s")
    safe_addstr(stdscr, y + height - 2, x - 5, "0s")
"""
CONSENSUS War Room - Command and Control Interface

This enhanced interface provides monitoring and control for the CONSENSUS system
with three monolithic AI agents (Rationalis, Aeternum, and Bellator),
each using a different local LLM.

FEATURES:
- Multiple visual themes (Military, WH40k, TARS, Helldivers)
- Decision history tracking and visualization
- System health monitoring and performance graphs
- Command auto-completion and templates
- Notification system with multiple priority levels
- Export capabilities for decisions and logs
- Configuration management for monoliths
- Dark/light mode color schemes
"""

from contextlib import contextmanager

try:
    import ib_insync as ibi
except ImportError:
    ibi = None

# Global variables for command processing
current_query = "No active query"
system_mode = "NORMAL"
        view_mode = "MAIN"  # Options: MAIN, HELP, CONFIG, HISTORY, MONOLITH_BELLATOR, MONOLITH_AETERNUM, MONOLITH_RATIONALIS, MONOLITH_ARBITER

# Monolith-specific data 
MONOLITH_DATA = {
    "Bellator": {
        "defcon_level": 4,
        "threat_alerts": [],
        "strategic_analysis": [],
        "security_news": [],
        "last_updated": None
    },
    "Aeternum": {
        "market_indices": {},
        "crypto_prices": {},
        "portfolio_performance": {},
        "economic_indicators": {},
        "last_updated": None
    },
    "Rationalis": {
        "system_logs": [],
        "logic_patterns": {},
        "analysis_metrics": {},
        "efficiency_rating": 0.0,
        "last_updated": None
    },
    "Arbiter": {
        "agenda": [],
        "pending_decisions": [],
        "system_status": {},
        "balance_metrics": {},
        "last_updated": None
    }
}

# System health metrics
system_health = {
    "cpu_usage": 0,
    "memory_usage": 0,
    "start_time": time.time(),
    "response_times": deque(maxlen=50),  # For plotting response time graph
    "avg_response_time": 0
}

# Command history and autocomplete
command_history = []
command_history_index = 0
command_output = ""  # Store feedback from command execution
command_suggestions = []  # Autocomplete suggestions
current_suggestion_index = 0

# Styling options
STYLE = {
    "theme": "military",  # Options: "military", "wh40k", "tars", "helldivers"
    "show_status": True,
    "interactive": True,
    "animated_text": True,  # Always enabled
    "show_notifications": True,
    "show_history": True,
    "show_system_health": True,
    "show_response_time_graph": True,
    "enable_autocomplete": True
}

# LLM Provider settings - can be "ollama" or "lmstudio"
LLM_PROVIDER = "ollama"  # Change to "lmstudio" to use LM Studio

# Model configuration for each monolith
MODEL_CONFIG = {
    "Rationalis": {
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
    "Aeternum": {
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
    "Bellator": {
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

# Add a global dictionary to track model status and resources
MODEL_STATUS = {
    "Rationalis": {"status": "unknown", "memory_usage": 0, "loading": False},
    "Aeternum": {"status": "unknown", "memory_usage": 0, "loading": False},
    "Bellator": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# Configuration for monoliths - reordered with specific colors
MONOLITHS = {
    "Aeternum": {  # First
        "symbol": "A",
        "color_pair": 1,  # CYAN (curses.COLOR_CYAN)
        "log_path": "./Aeternum/aeternum.log",
        "vote_path": "./_ARBITER/tmp_votes/aeternum_vote.json",
        "analysis_prefix": {
            "military": "FINANCIAL ASSESSMENT:",
            "wh40k": "++ FISCAL DIVINATION ++",
            "tars": "FINANCE.SYS:",
            "helldivers": "ECONOMIC INTELLIGENCE:"
        },
        "status": "offline"
    },
    "Bellator": {  # Second
        "symbol": "B",
        "color_pair": 3,  # MAGENTA (curses.COLOR_MAGENTA)
        "log_path": "./Bellator/bellator.log",
        "vote_path": "./_ARBITER/tmp_votes/bellator_vote.json",
        "analysis_prefix": {
            "military": "SECURITY ANALYSIS:",
            "wh40k": "++ TACTICAL ASSESSMENT ++",
            "tars": "SECURITY.SYS:",
            "helldivers": "COMBAT DIRECTIVE:"
        },
        "status": "offline"
    },
    "Rationalis": {  # Last
        "symbol": "R",
        "color_pair": 2,  # BLUE (curses.COLOR_BLUE)
        "log_path": "./Rationalis/rationalis.log",
        "vote_path": "./_ARBITER/tmp_votes/rationalis_vote.json",
        "analysis_prefix": {
            "military": "LOGICAL ANALYSIS:",
            "wh40k": "++ LOGICAL COGITATION ++",
            "tars": "LOGIC.SYS:",
            "helldivers": "STRATEGIC CALCULATION:"
        },
        "status": "offline"
    }
}

# System modes
SYSTEM_MODES = {
    "NORMAL": {
        "symbol": {"military": "#", "wh40k": "I", "tars": "■", "helldivers": "★"}, 
        "color_pair": 7
    },
    "CRITICAL": {
        "symbol": {"military": "!", "wh40k": "X", "tars": "▲", "helldivers": "⚠"}, 
        "color_pair": 5
    }
}

# Command history
command_history = []
command_history_index = 0
command_output = ""  # Store feedback from command execution

# IBKR connection state
IBKR_CONNECTED = False
ib = None

# Box drawing characters for different styles
BOX_CHARS = {
    "military": {
        "top_left": "+",
        "top_right": "+",
        "bottom_left": "+",
        "bottom_right": "+",
        "horizontal": "=",
        "vertical": "|"
    },
    "wh40k": {
        "top_left": "/",
        "top_right": "\\",
        "bottom_left": "\\",
        "bottom_right": "/",
        "horizontal": "-",
        "vertical": "|"
    },
    "tars": {
        "top_left": "+",
        "top_right": "+",
        "bottom_left": "+",
        "bottom_right": "+",
        "horizontal": "-",
        "vertical": "|"
    },
    "helldivers": {
        "top_left": "[",
        "top_right": "]",
        "bottom_left": "[",
        "bottom_right": "]",
        "horizontal": "=",
        "vertical": "|"
    }
}

# No ASCII art

def check_model_status(name):
    """Check if a model is loaded and available in the LLM provider"""
    try:
        config = MODEL_CONFIG[name]
        engine = config["engine"]
        
        if engine == "ollama":
            response = requests.get(config["status_endpoint"])
        if response.status_code == 200:
                models = response.json().get("models", [])
                model_name = config["model"]
                
                # Check if model is in the list of available models
                for model in models:
        if model["name"] == model_name:
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                        
                # Model not found, but service is running
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
                
        elif engine == "lmstudio":
            response = requests.get(config["status_endpoint"])
        if response.status_code == 200:
        pass
                models = response.json().get("data", [])
                model_name = config["model"].split(":")[0].lower()
                
                for model in models:
        if model_name in model["id"].lower():
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                        
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
    except:
        pass
        MODEL_STATUS[name]["status"] = "service_down"
        return False

def start_model_loading(name):
    """Start loading a model in a background thread"""
        if MODEL_STATUS[name]["loading"]:
        return  # Already loading
        
    MODEL_STATUS[name]["loading"] = True
    MODEL_STATUS[name]["status"] = "loading"
    
    def load_model():
        try:
            config = MODEL_CONFIG[name]
            model = config["model"]
            engine = config["engine"]
            
        if engine == "ollama":
        pass
                response = requests.post(
                    config["api_url"],
                    json={
                        "model": model,
                        "prompt": "hello",  # Simple prompt to load model
                        "stream": False
                    }
                )
                
        if response.status_code == 200:
                    MODEL_STATUS[name]["status"] = "ready"
        else:
                    MODEL_STATUS[name]["status"] = "error"
                    
        elif engine == "lmstudio":
        pass
                response = requests.post(
                    config["api_url"],
                    json={
                        "model": model,
                        "prompt": "hello",
                        "max_tokens": 5
                    }
                )
                
        if response.status_code == 200:
                    MODEL_STATUS[name]["status"] = "ready"
        else:
                    MODEL_STATUS[name]["status"] = "error"
        except:
            MODEL_STATUS[name]["status"] = "error"
        finally:
            MODEL_STATUS[name]["loading"] = False
    
    threading.Thread(target=load_model, daemon=True).start()

def update_model_statuses():
    """Update all model statuses in a background thread"""
    while True:
        try:
        pass
            for name in MODEL_STATUS:
        if not MODEL_STATUS[name]["loading"]:
                    check_model_status(name)
                
                # Update memory usage if possible
        if psutil:
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        if MODEL_CONFIG[name]["engine"] == "ollama" and 'ollama' in proc.info['name'].lower():
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)  # MB
                                break
        elif MODEL_CONFIG[name]["engine"] == "lmstudio" and 'lmstudio' in proc.info['name'].lower():
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)  # MB
                                break
                    except:
        pass
                    
            time.sleep(5)  # Check every 5 seconds
        except:
            time.sleep(10)  # Longer delay on error

def query_model(name, prompt):
    """Query a specific model and get a response"""
    try:
        config = MODEL_CONFIG[name]
        engine = config["engine"]
        
        # Check if model is ready
        if MODEL_STATUS[name]["status"] != "ready":
            return f"Error: Model {config['model']} is not ready. Status: {MODEL_STATUS[name]['status']}"
        
        # Create the full prompt with system prompt
        full_prompt = f"{config['system_prompt']}\n\nQUERY: {prompt}\n\nVOTE: "
        
        if engine == "ollama":
        pass
            response = requests.post(
                config["api_url"],
                json={
                    "model": config["model"],
                    "prompt": full_prompt,
                    "temperature": config["parameters"]["temperature"],
                    "top_p": config["parameters"]["top_p"],
                    "max_tokens": config["parameters"]["max_tokens"],
                    "stream": False
                }
            )
            
        if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
        else:
                return f"Error: API returned status {response.status_code}"
                
        elif engine == "lmstudio":
        pass
            response = requests.post(
                config["api_url"],
                json={
                    "model": config["model"],
                    "prompt": full_prompt,
                    "temperature": config["parameters"]["temperature"],
                    "top_p": config["parameters"]["top_p"],
                    "max_tokens": config["parameters"]["max_tokens"]
                }
            )
            
        if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
        else:
                return f"Error: API returned status {response.status_code}"
                
    except Exception as e:
        return f"Error querying model: {str(e)}"

def generate_vote(name, query):
    """Generate a vote from a specific monolith"""
    try:
        pass
        start_time = time.time()
        
        # Query the model
        response = query_model(name, query)
        
        # Parse the response to get vote decision
        response_lower = response.lower()
        
        if "approve" in response_lower or "yes" in response_lower or "accept" in response_lower:
            vote = "APPROVE"
        elif "deny" in response_lower or "no" in response_lower or "reject" in response_lower:
            vote = "DENY"
        else:
            vote = "PENDING"  # Unclear response
        
        # Create vote data
        confidence = random.uniform(0.65, 0.98)  # Simulated confidence value
        vote_data = {
            "monolith": name.lower(),
            "vote": vote,
            "reasoning": response,
            "timestamp": time.time(),
            "confidence": confidence,
            "response_time": time.time() - start_time
        }
        
        # Save vote to file
        vote_path = f"./_ARBITER/tmp_votes/{name.lower()}_vote.json"
        os.makedirs(os.path.dirname(vote_path), exist_ok=True)
        
        with open(vote_path, 'w', encoding='utf-8') as f:
            json.dump(vote_data, f, indent=2)
        
        # Record response time for metrics
        record_response_time(start_time)
        
        # Add to decision history if this is a final vote
        if vote != "PENDING":
            add_decision_to_history(query, vote, response)
            
        add_notification(f"{name} voted: {vote}", "info")
        return vote_data
    except Exception as e:
        error_msg = f"Error generating vote: {str(e)}"
        add_notification(error_msg, "error")
        return {
            "monolith": name.lower(),
            "vote": "PENDING",
            "reasoning": error_msg,
            "timestamp": time.time()
        }

def generate_all_votes(query):
    """Generate votes from all monoliths for the current query"""
    start_time = time.time()
        add_notification(f"Consensus generation started for: {query}", "info")
    
    threads = []
    for name in MODEL_STATUS:
        t = threading.Thread(target=generate_vote, args=(name, query), daemon=True)
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete (with timeout)
    for t in threads:
        t.join(timeout=30)  # Timeout after 30 seconds
    
    # Record overall response time
    response_time = time.time() - start_time
    record_response_time(response_time)
    
    # Check if we have a consensus
    votes = {}
    for name in MODEL_STATUS:
        vote_path = f"./_ARBITER/tmp_votes/{name.lower()}_vote.json"
        if os.path.exists(vote_path):
            try:
                with open(vote_path, 'r') as f:
                    vote_data = json.load(f)
                    votes[name] = vote_data.get("vote", "PENDING")
            except:
                votes[name] = "PENDING"
    
    consensus = calculate_consensus(votes)
        if consensus:
        add_notification(f"Consensus reached: {consensus}", "success")
        add_decision_to_history(query, consensus)
        else:
        add_notification("No consensus reached", "warning")

def connect_to_ibkr():
    """Connect to Interactive Brokers API"""
    global IBKR_CONNECTED, ib
    
        if ibi is None:
        return "Error: ib_insync package not installed. Install with 'pip install ib_insync'"
        
    try:
        ib = ibi.IB()
        ib.connect('127.0.0.1', 7497, clientId=1)  # TWS connection
        IBKR_CONNECTED = ib.isConnected()
        
        if IBKR_CONNECTED:
            return "Connected to Interactive Brokers"
        else:
            return "Failed to connect to Interactive Brokers"
    except Exception as e:
        return f"IBKR connection error: {str(e)}"

def update_statuses():
    """Background thread to update monolith statuses"""
    while True:
        try:
        pass
            for name, info in MONOLITHS.items():
                # Check if vote file exists and when it was last modified
        if os.path.exists(info['vote_path']):
                    last_modified = os.path.getmtime(info['vote_path'])
        if time.time() - last_modified > 300:  # No activity for 5 minutes
                        MONOLITHS[name]['status'] = "offline"
        else:
        pass
                        try:
                            with open(info['vote_path'], 'r') as f:
                                vote_data = json.load(f)
        if vote_data.get('vote', 'PENDING') == 'PENDING':
                                    MONOLITHS[name]['status'] = "processing"
        else:
                                    MONOLITHS[name]['status'] = "online"
                        except:
                            MONOLITHS[name]['status'] = "processing"
        else:
                    MONOLITHS[name]['status'] = "offline"
                
                # Simulate occasional processing state for demo purposes
        if random.random() < 0.05:  # 5% chance
                    MONOLITHS[name]['status'] = "processing"
            
            time.sleep(5)
        except:
            time.sleep(10)  # Longer sleep on error

def process_command(command):
    """Process a command and return output message"""
    global current_query, system_mode, IBKR_CONNECTED, ib, LLM_PROVIDER, view_mode, current_color_scheme
    
    cmd = command.lower().strip()
    
    # Command: query
        if cmd.startswith("query "):
        new_query = command[6:].strip()
        if new_query:
            current_query = new_query
        add_notification(f"Query set: {current_query}", "info")
            return f"Query set to: {current_query}"
        else:
        add_notification("Query cannot be empty", "error")
            return "Error: Query cannot be empty"
    
    # Command: mode changes
        elif cmd == "critical":
        system_mode = "CRITICAL"
        add_notification("System mode set to CRITICAL", "warning")
        return "System mode set to CRITICAL"
        elif cmd == "normal":
        system_mode = "NORMAL"
        add_notification("System mode set to NORMAL", "info")
        return "System mode set to NORMAL"
    
    # Command: style changes
        elif cmd.startswith("style "):
        style_arg = cmd[6:].strip().lower()
        if style_arg in ["military", "wh40k", "tars", "helldivers"]:
            STYLE["theme"] = style_arg
        add_notification(f"Style set to {style_arg}", "info")
            return f"Interface style set to: {style_arg}"
        else:
        add_notification(f"Unknown style: {style_arg}", "error")
            return f"Unknown style: {style_arg}. Available styles: military, wh40k, tars, helldivers"
    
    # View mode commands
        elif cmd == "help":
        if view_mode == "HELP":
        view_mode = "MAIN"
            return "Returned to main view"
        else:
        view_mode = "HELP"
            return "Showing help view. Press 'H' to return to main view."
            
        elif cmd == "config":
        if view_mode == "CONFIG":
        view_mode = "MAIN"
            return "Returned to main view"
        else:
        view_mode = "CONFIG"
            return "Showing configuration view. Press 'C' to return to main view."
            
        elif cmd == "history":
        if view_mode == "HISTORY":
        view_mode = "MAIN"
            return "Returned to main view"
        else:
        view_mode = "HISTORY"
            return "Showing decision history. Press 'D' to return to main view."
    
    # Add model management commands
        elif cmd.startswith("load "):
        model_name = cmd[5:].strip().title()
        if model_name in MODEL_STATUS:
            start_model_loading(model_name)
        add_notification(f"Loading model for {model_name}", "info")
            return f"Loading model for {model_name}..."
        else:
        add_notification(f"Unknown monolith: {model_name}", "error")
            return f"Unknown monolith: {model_name}"
    
    # Switch LLM provider
        elif cmd == "use ollama":
        LLM_PROVIDER = "ollama"
        for name in MODEL_CONFIG:
            MODEL_CONFIG[name]["engine"] = "ollama"
            MODEL_CONFIG[name]["api_url"] = PROVIDER_ENDPOINTS["ollama"]["api_url"]
            MODEL_CONFIG[name]["status_endpoint"] = PROVIDER_ENDPOINTS["ollama"]["status_endpoint"]
        add_notification("Switched to Ollama LLM provider", "info")
        return "Switched to Ollama LLM provider"
        
        elif cmd == "use lmstudio":
        LLM_PROVIDER = "lmstudio"
        for name in MODEL_CONFIG:
            MODEL_CONFIG[name]["engine"] = "lmstudio"
            MODEL_CONFIG[name]["api_url"] = PROVIDER_ENDPOINTS["lmstudio"]["api_url"]
            MODEL_CONFIG[name]["status_endpoint"] = PROVIDER_ENDPOINTS["lmstudio"]["status_endpoint"]
        add_notification("Switched to LM Studio LLM provider", "info")
        return "Switched to LM Studio LLM provider"
    
        elif cmd == "status":
        status_lines = []
        for name, status in MODEL_STATUS.items():
            status_lines.append(f"{name}: {status['status'].upper()} ({status['memory_usage']:.0f} MB)")
        return "\n".join(status_lines)
    
        elif cmd.startswith("vote "):
        parts = cmd[5:].strip().split(" ", 1)
        if len(parts) != 2:
        add_notification("Invalid vote command format", "error")
            return "Usage: vote <monolith> <query>"
            
        monolith_name = parts[0].title()
        vote_query = parts[1]
        
        if monolith_name in MODEL_STATUS:
            threading.Thread(target=generate_vote, args=(monolith_name, vote_query), daemon=True).start()
        add_notification(f"Generating vote from {monolith_name}", "info")
            return f"Generating vote from {monolith_name} for: {vote_query}"
        else:
        add_notification(f"Unknown monolith: {monolith_name}", "error")
            return f"Unknown monolith: {monolith_name}"
            
        elif cmd == "consensus":
        start_time = time.time()
        threading.Thread(target=generate_all_votes, args=(current_query,), daemon=True).start()
        response_time = record_response_time(start_time)
        add_notification(f"Generating consensus (response time: {response_time:.2f}s)", "info")
        return f"Generating consensus for query: {current_query}"
    
    # IBKR integration commands
        elif cmd == "ibkr connect":
        result = connect_to_ibkr()
        if "Connected" in result:
        add_notification("Connected to Interactive Brokers", "success")
        else:
        add_notification("Failed to connect to IBKR", "error")
        return result
        
        elif cmd == "ibkr status":
        if IBKR_CONNECTED and ib:
            try:
                account = ib.accountSummary()
        if account:
                    account_info = [(row.tag, row.value) for row in account if row.tag in ['NetLiquidation', 'AvailableFunds']]
                    return f"IBKR Connected - Account: {', '.join([f'{tag}: {val}' for tag, val in account_info])}"
        else:
                    return "IBKR Connected - No account information available"
            except:
                return "IBKR Connected - Error retrieving account information"
        else:
            return "IBKR Not Connected - Use 'ibkr connect' to connect"
            
        elif cmd.startswith("ibkr stock "):
        if not IBKR_CONNECTED or not ib:
        add_notification("IBKR Not Connected", "error")
            return "IBKR Not Connected - Use 'ibkr connect' first"
            
        symbol = cmd[11:].strip().upper()
        try:
            contract = ibi.Stock(symbol, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Request market data
            ib.reqMktData(contract)
            time.sleep(1)  # Wait for data
            
            ticker = ib.ticker(contract)
            return (f"Stock: {symbol} | Price: {ticker.last} | Bid: {ticker.bid} | Ask: {ticker.ask} | "
                    f"High: {ticker.high} | Low: {ticker.low} | Volume: {ticker.volume}")
        except Exception as e:
        add_notification(f"Error querying stock {symbol}", "error")
            return f"Error querying stock {symbol}: {str(e)}"
    
    # New commands for enhanced features
        elif cmd.startswith("template "):
        pass
        parts = cmd[9:].strip().split(" ", 1)
        template_name = parts[0].lower()
        params = parts[1] if len(parts) > 1 else None
        
        result = apply_template(template_name, params)
        if result.startswith("Unknown") or result.startswith("Error"):
        add_notification(result, "error")
        else:
            current_query = result
        add_notification(f"Applied template: {template_name}", "success")
        
        return result
    
        elif cmd.startswith("export "):
        format_type = cmd[7:].strip().lower()
        if format_type in ["json", "csv"]:
            result = export_history(format_type)
        add_notification(f"Exported history as {format_type}", "success")
            return result
        else:
        add_notification(f"Unsupported export format: {format_type}", "error")
            return f"Unsupported export format: {format_type}. Use 'export json' or 'export csv'."
    
        elif cmd == "notifications":
        if STYLE["show_notifications"]:
            STYLE["show_notifications"] = False
            return "Notifications hidden"
        else:
            STYLE["show_notifications"] = True
            return "Notifications shown"
    
        elif cmd == "health":
        if STYLE["show_system_health"]:
            STYLE["show_system_health"] = False
            return "System health display hidden"
        else:
            STYLE["show_system_health"] = True
            return "System health display shown"
    
        elif cmd == "dark":
        current_color_scheme = "dark"
        add_notification("Switched to dark mode", "info")
        return "Switched to dark color scheme"
    
        elif cmd == "light":
        current_color_scheme = "light"
        add_notification("Switched to light mode", "info")
        return "Switched to light color scheme"
    
        elif cmd == "reload":
        pass
        add_notification("System reloaded", "success")
        return "CONSENSUS War Room reloaded"
        
    # Command: detailed help
        elif cmd == "help":
        view_mode = "HELP"
        return ("Available commands:\n"
                "query <text> - Set active query\n"
                "critical/normal - Set system mode\n"
                "style <theme> - Change interface style\n"
                "load <monolith> - Load model for a monolith\n"
                "use ollama/lmstudio - Switch LLM provider\n"
                "status - Show model status\n"
                "vote <monolith> <query> - Generate vote from a monolith\n"
                "consensus - Generate votes from all monoliths\n"
                "ibkr connect - Connect to Interactive Brokers\n"
                "ibkr status - Show IBKR account status\n"
                "ibkr stock <symbol> - Get stock information\n"
                "template <name> [params] - Apply query template\n"
                "export json/csv - Export decision history\n"
                "notifications - Toggle notifications\n"
                "health - Toggle system health display\n"
                "dark/light - Switch color scheme\n"
                "help/config/history - Switch views")
    
    # Unknown command
        else:
        add_notification(f"Unknown command: {command}", "error")
        return f"Unknown command: {command}. Type 'help' for available commands."

def main(stdscr):
    global current_query, system_mode, command_output
    global verdict_display_text, verdict_display_length, verdict_full_text, last_verdict_update
    
    # Setup
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.use_default_colors()
    
    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # Aeternum
    curses.init_pair(2, curses.COLOR_BLUE, -1)     # Rationalis
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)  # Bellator
    curses.init_pair(4, curses.COLOR_GREEN, -1)    # APPROVE/Online
    curses.init_pair(5, curses.COLOR_YELLOW, -1)   # WARNING/CRITICAL/Processing
    curses.init_pair(6, curses.COLOR_RED, -1)      # DENY/Offline
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # Normal text
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)    # Alert background
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Success background
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Command input
    curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_WHITE) # Light mode text
    curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLACK) # Dark mode highlight
    
    stdscr.timeout(500)  # Refresh rate in ms
    
    # Local UI state
    last_update = datetime.datetime.now()
    input_mode = False
    command_buffer = ""
    animated_text_position = 0
    
    # Always ensure text animation is enabled
    STYLE["animated_text"] = True
    
    # Start background threads
        if STYLE["show_status"]:
        threading.Thread(target=update_statuses, daemon=True).start()
    
    # Start the model status monitoring thread
    threading.Thread(target=update_model_statuses, daemon=True).start()
    
    # Check if models are available at startup
    for name in MODEL_STATUS:
        if not check_model_status(name):
            command_output = f"Model {MODEL_CONFIG[name]['model']} not ready. Use 'load {name}' to load."
    
    while True:
        try:
            h, w = stdscr.getmaxyx()
            stdscr.clear()
            
            # Check if terminal is big enough
        if h < 25 or w < 80:
                safe_addstr(stdscr, 0, 0, "Terminal too small. Resize to at least 80x25.")
                stdscr.refresh()
                time.sleep(1)
                continue
            
            # Get current style
            theme = STYLE["theme"]
            box_style = BOX_CHARS[theme]
            
            # Draw decorative border at top
            border_char = box_style["horizontal"]
            mode_info = SYSTEM_MODES[system_mode]
            border = border_char * (w-2)
            safe_addstr(stdscr, 0, 1, border, curses.A_BOLD)
            
            # Draw header based on style
if theme == "military":
                header = f" {mode_info['symbol'][theme]} CONSENSUS WAR ROOM {mode_info['symbol'][theme]} "
                mode_display = f"SYS-MODE: {system_mode}"
        elif theme == "wh40k":
                header = f" MECHANICUS CONSENSII {mode_info['symbol'][theme]} COMMAND THRONE "
                mode_display = f"IMPERIUM STATUS: {system_mode}"
        elif theme == "tars":
                header = f" CONSENSUS.CORE.{system_mode} {mode_info['symbol'][theme]} "
                mode_display = f"SYS.MODE={system_mode}"
        elif theme == "helldivers":
                header = f" ★ SUPER EARTH COMMAND CENTER {mode_info['symbol'][theme]} "
                mode_display = f"DEMOCRACY STATUS: {system_mode}"
                
        if system_mode == "CRITICAL":
if theme == "military":
                    header = "/// CRITICAL ALERT ACTIVE ///"
        elif theme == "wh40k":
                    header = "!!! EXTERMINATUS PROTOCOL ACTIVE !!!"
        elif theme == "tars":
                    header = "*** CRITICAL.OVERRIDE.ACTIVE ***"
        elif theme == "helldivers":
                    header = "!!! LIBERTY EMERGENCY PROTOCOL ACTIVE !!!"
            
            safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
                     curses.A_BOLD | curses.color_pair(mode_info["color_pair"]))
            
            # Draw timestamp and mode indicator
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            safe_addstr(stdscr, 1, 2, mode_display, 
                     curses.color_pair(mode_info["color_pair"]))
            safe_addstr(stdscr, 1, w - len(timestamp) - 2, timestamp)
            
            # Draw second border
            safe_addstr(stdscr, 2, 1, border, curses.A_BOLD)
            
            # Draw current query with style-specific header
            query_display = current_query[:w-12] if len(current_query) > w-12 else current_query
            
if theme == "military":
                query_header = "[ ACTIVE QUERY ]"
        elif theme == "wh40k":
                query_header = "[ IMPERIAL INQUIRY ]"
        elif theme == "tars":
                query_header = "[ QUERY.ACTIVE ]"
        elif theme == "helldivers":
                query_header = "[ MISSION DIRECTIVE ]"
                
            safe_addstr(stdscr, 3, w//2 - len(query_header)//2, query_header, curses.A_BOLD)
            
            # Animate text if long enough
        if len(query_display) > w-40:
                animated_text_position = (animated_text_position + 1) % (len(query_display) - (w-40))
                display_text = query_display[animated_text_position:animated_text_position + (w-40)]
                safe_addstr(stdscr, 4, w//2 - len(display_text)//2, display_text)
        else:
                safe_addstr(stdscr, 4, w//2 - len(query_display)//2, query_display)
            
            # Divider after query
            safe_addstr(stdscr, 5, 1, border, curses.A_BOLD)
            
                # Remove drawing ASCII art code
                # (previously here)
            
            # Draw monolith panels
            monolith_votes = {}
            
            panel_y = 7
            for name, info in MONOLITHS.items():
                # Check if we have room to draw this panel
        if panel_y + 10 >= h:
                    break
                
                # Get vote information
                vote_info = get_vote_info(info['vote_path'])
                vote_str = vote_info.get('vote', 'PENDING')
                monolith_votes[name] = vote_str
                
                # Select vote color
                vote_color = VOTE_COLORS.get(vote_str, VOTE_COLORS["PENDING"])
                
                # Draw monolith box - using full width now that ASCII art is removed
                box_width = min(w - 4, 76)  # Full width
                
                # Style-specific box drawing
if theme == "military":
        pass
                    box_top = f"+{'=' * (box_width-2)}+"
                    safe_addstr(stdscr, panel_y, 2, box_top)
                    
                    # Side borders
                    for i in range(1, 8):
        if panel_y+i < h:
                            safe_addstr(stdscr, panel_y+i, 2, "|")
                            safe_addstr(stdscr, panel_y+i, 2+box_width-1, "|")
                            
                    # Bottom border
                    box_bottom = f"+{'=' * (box_width-2)}+"
                    safe_addstr(stdscr, panel_y+8, 2, box_bottom)
                    
                    # Middle divider
                    divider = f"|{'=' * (box_width-2)}|"
                    safe_addstr(stdscr, panel_y+2, 2, divider)
                    
        elif theme == "wh40k":
        pass
                    box_top = f"/{'-' * (box_width-2)}\\"
                    safe_addstr(stdscr, panel_y, 2, box_top)
                    
                    # Side borders
                    for i in range(1, 8):
        if panel_y+i < h:
                            safe_addstr(stdscr, panel_y+i, 2, "|")
                            safe_addstr(stdscr, panel_y+i, 2+box_width-1, "|")
                            
                    # Bottom border
                    box_bottom = f"\\{'-' * (box_width-2)}/"
                    safe_addstr(stdscr, panel_y+8, 2, box_bottom)
                    
                    # Middle divider
                    divider = f"|{'-' * (box_width-2)}|"
                    safe_addstr(stdscr, panel_y+2, 2, divider)
                    
        elif theme == "helldivers":
        pass
                    box_top = f"[{'=' * (box_width-2)}]"
                    safe_addstr(stdscr, panel_y, 2, box_top)
                    
                    # Side borders
                    for i in range(1, 8):
        if panel_y+i < h:
                            safe_addstr(stdscr, panel_y+i, 2, "|")
                            safe_addstr(stdscr, panel_y+i, 2+box_width-1, "|")
                            
                    # Bottom border
                    box_bottom = f"[{'=' * (box_width-2)}]"
                    safe_addstr(stdscr, panel_y+8, 2, box_bottom)
                    
                    # Middle divider
                    divider = f"|{'=' * (box_width-2)}|"
                    safe_addstr(stdscr, panel_y+2, 2, divider)
                    
        else:  # TARS
                    # Top border
                    box_top = f"+{'-' * (box_width-2)}+"
                    safe_addstr(stdscr, panel_y, 2, box_top)
                    
                    # Side borders
                    for i in range(1, 8):
        if panel_y+i < h:
                            safe_addstr(stdscr, panel_y+i, 2, "|")
                            safe_addstr(stdscr, panel_y+i, 2+box_width-1, "|")
                            
                    # Bottom border
                    box_bottom = f"+{'-' * (box_width-2)}+"
                    safe_addstr(stdscr, panel_y+8, 2, box_bottom)
                    
                    # Middle divider
                    divider = f"|{'-' * (box_width-2)}|"
                    safe_addstr(stdscr, panel_y+2, 2, divider)
                
                # Draw monolith header based on style
if theme == "military":
                    header = f" [{info['symbol']}] {name.upper()} MONOLITH "
        elif theme == "wh40k":
                    header = f" [{info['symbol']}] LEXMECHANIC {name.upper()} "
        elif theme == "tars":
                    header = f" {name.upper()}.NODE "
        elif theme == "helldivers":
                    header = f" [{info['symbol']}] {name.upper()} STRATAGEM "
                    
                safe_addstr(stdscr, panel_y+1, 4, header, 
                         curses.A_BOLD | curses.color_pair(info['color_pair']))
                
                # Display status indicators if enabled
        if STYLE["show_status"]:
                    status = info["status"]
                    status_text, status_color = STATUS_INDICATORS[status]
                    
if theme == "military":
                        status_display = f"STATUS: {status_text}"
        elif theme == "wh40k":
                        status_display = f"MACHINE SPIRIT: {status_text}"  # Proper spacing
        elif theme == "tars":
                        status_display = f"STATUS={status_text}"
        elif theme == "helldivers":
                        status_display = f"LIBERTY STATUS: {status_text}"
                        
                    # Ensure status text fits within available space
                    max_status_pos = min(w - len(status_display) - 4, box_width - 30)
                    safe_addstr(stdscr, panel_y+1, max_status_pos, 
                             status_display, curses.color_pair(status_color))
                
                # Display vote with style-specific formatting
                # Calculate space to ensure it fits
if theme == "military":
                    vote_display = f"[ {vote_str} ]"
        elif theme == "wh40k":
                    vote_display = f"<<< {vote_str} >>>"  # Fixed spacing
        elif theme == "tars":
                    vote_display = f"[{vote_str}]"
        elif theme == "helldivers":
                    vote_display = f"{vote_str}"  # Removed stars
                
                # Calculate position to ensure vote display fits within box
                vote_pos = box_width - len(vote_display) - 2
                safe_addstr(stdscr, panel_y+1, 2 + vote_pos, vote_display, 
                         curses.color_pair(vote_color) | curses.A_BOLD)
                
                # Display reasoning with monolith-specific formatting
                reasoning = vote_info.get('reasoning', 'AWAITING ANALYSIS...')
                
                # Format reasoning based on monolith personality and style
                prefix = info['analysis_prefix'][theme]
                
                # Draw prefix with monolith color
                safe_addstr(stdscr, panel_y+3, 4, prefix, 
                         curses.color_pair(info['color_pair']) | curses.A_BOLD)
                
                # Wrap and display reasoning
                reasoning_lines = wrap_text(reasoning, box_width - 6)
        if reasoning_lines:
                    safe_addstr(stdscr, panel_y+3, 4 + len(prefix) + 1, reasoning_lines[0])
                
                # Display additional reasoning lines
                for i, line in enumerate(reasoning_lines[1:3], 1):
        if panel_y+3+i < h:
                        safe_addstr(stdscr, panel_y+3+i, 4, line)
                
                # Add model status display to each monolith panel
        if panel_y+6 < h:
                    model_info = MODEL_CONFIG[name]["model"]
                    model_status = MODEL_STATUS[name]["status"].upper()
                    model_memory = MODEL_STATUS[name]["memory_usage"]
                    
if theme == "military":
                        model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEM: {model_memory:.0f}MB"
        elif theme == "wh40k":
                        model_str = f"COGITATOR: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        elif theme == "helldivers":
                        model_str = f"STRATAGEM: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        else:
                        model_str = f"MODEL={model_info} STATUS={model_status} MEM={model_memory:.0f}MB"
                        
                    # Color based on status
                    status_color = curses.color_pair(4)  # Default green
        if model_status in ["ERROR", "SERVICE_DOWN"]:
                        status_color = curses.color_pair(6)  # Red
        elif model_status in ["LOADING", "NOT_LOADED", "UNKNOWN"]:
                        status_color = curses.color_pair(5)  # Yellow
                        
                    safe_addstr(stdscr, panel_y+6, 4, model_str, status_color)
                
                # Draw confidence meter if available - style based on theme
        if 'confidence' in vote_info and panel_y+7 < h:
                    conf_val = vote_info['confidence']
                    
if theme == "military":
        pass
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'#' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "wh40k":
        pass
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'+' * filled}{'-' * (meter_len - filled)}]"
        elif theme == "tars":
        pass
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'=' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "helldivers":
        pass
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'★' * filled}{' ' * (meter_len - filled)}]"
                    
                    safe_addstr(stdscr, panel_y+7, 4, conf_str)
                    safe_addstr(stdscr, panel_y+7, 4 + len(conf_str) + 2, meter, 
                             curses.color_pair(vote_color))
                
                panel_y += 10
            
            # Calculate and display consensus
            consensus = calculate_consensus(monolith_votes)
            
            # Draw consensus box if there's room
        if panel_y + 4 < h:
                consensus_y = panel_y
                
                # Style-specific box and header
if theme == "military":
                    consensus_box_top = f"+{'=' * (min(w-6, 74))}+"
                    consensus_box_bottom = f"+{'=' * (min(w-6, 74))}+"
        elif theme == "wh40k":
                    consensus_box_top = f"+{'=' * (min(w-6, 74))}+"
                    consensus_box_bottom = f"+{'=' * (min(w-6, 74))}+"
        elif theme == "tars":
                    consensus_box_top = f"+{'=' * (min(w-6, 74))}+"
                    consensus_box_bottom = f"+{'=' * (min(w-6, 74))}+"
        elif theme == "helldivers":
                    consensus_box_top = f"[{'=' * (min(w-6, 74))}]"
                    consensus_box_bottom = f"[{'=' * (min(w-6, 74))}]"
                
                safe_addstr(stdscr, consensus_y, 2, consensus_box_top, curses.A_BOLD)
                
        if consensus:
        pass
if theme == "military":
                        verdict_str = f"CONSENSUS VERDICT: {consensus}"
        elif theme == "wh40k":
                        verdict_str = f"IMPERIAL DECREE: {consensus}"
        elif theme == "tars":
                        verdict_str = f"CONSENSUS.VERDICT={consensus}"
        elif theme == "helldivers":
                        verdict_str = f"DEMOCRATIC DECISION: {consensus}"
                        
                    # Set up for typing animation if verdict changed
        if verdict_full_text != verdict_str:
                        verdict_full_text = verdict_str
                        verdict_display_length = 0
                        verdict_display_text = ""
                    
                    # Update the displayed text with typing animation
                    current_time = time.time()
        if current_time - last_verdict_update > 0.05:  # Update every 50ms
        if verdict_display_length < len(verdict_full_text):
                            verdict_display_length += 1
                            verdict_display_text = verdict_full_text[:verdict_display_length]
                            last_verdict_update = current_time
                    
                    verdict_color = VOTE_COLORS[consensus]
                    
                    # Center the verdict text - but only display the current animation frame
                    safe_addstr(stdscr, consensus_y+1, w//2 - len(verdict_full_text)//2, 
                             verdict_display_text, curses.color_pair(verdict_color) | curses.A_BOLD)
                    
                    # Style-specific warning/confirmation for critical mode
        if system_mode == "CRITICAL" and consensus == "APPROVE" and consensus_y+2 < h:
if theme == "military":
                            warn_str = "!!! WARNING: CRITICAL ACTION REQUIRES VERIFICATION !!!"
        elif theme == "wh40k":
                            warn_str = "!!! BY THE EMPEROR'S WILL: VERIFICATION REQUIRED !!!"
        elif theme == "tars":
                            warn_str = "!!! CRITICAL.OVERRIDE.VERIFICATION.REQUIRED !!!"
        elif theme == "helldivers":
                            warn_str = "!!! FOR DEMOCRACY: VERIFICATION REQUIRED !!!"
                            
                        safe_addstr(stdscr, consensus_y+2, w//2 - len(warn_str)//2, warn_str, 
                                 curses.color_pair(8) | curses.A_BOLD)
        elif consensus == "APPROVE" and consensus_y+2 < h:
if theme == "military":
                            confirm_str = ">>> ACTION AUTHORIZED <<<"
        elif theme == "wh40k":
                            confirm_str = ">>> THE EMPEROR APPROVES <<<"
        elif theme == "tars":
                            confirm_str = ">>> EXECUTION.AUTHORIZED <<<"
        elif theme == "helldivers":
                            confirm_str = ">>> LIBERTY DELIVERED <<<"
                            
                        safe_addstr(stdscr, consensus_y+2, w//2 - len(confirm_str)//2, confirm_str, 
                                 curses.color_pair(9) | curses.A_BOLD)
        else:
        pass
if theme == "military":
                        wait_str = "AWAITING CONSENSUS..."
        elif theme == "wh40k":
                        wait_str = "THE COUNCIL DELIBERATES..."
        elif theme == "tars":
                        wait_str = "CONSENSUS.PENDING..."
        elif theme == "helldivers":
                        wait_str = "DEMOCRACY IN PROGRESS..."
                        
                    # Reset verdict animation state if no consensus
                    verdict_full_text = ""
                    verdict_display_text = ""
                    verdict_display_length = 0
                    
                    safe_addstr(stdscr, consensus_y+1, w//2 - len(wait_str)//2, wait_str, 
                             curses.A_BOLD)
                
        if consensus_y+3 < h:
                    safe_addstr(stdscr, consensus_y+3, 2, consensus_box_bottom, curses.A_BOLD)
            
            # Command input area and history display
            cmd_y = h - 6
        if cmd_y > 0 and STYLE["interactive"]:
        pass
                history_width = w - 4
                
if theme == "military":
                    cmd_box_top = f"+{'=' * (history_width)}+"
                    cmd_box_bottom = f"+{'=' * (history_width)}+"
        elif theme == "wh40k":
                    cmd_box_top = f"<{'=' * (history_width)}>"
                    cmd_box_bottom = f"<{'=' * (history_width)}>"
        elif theme == "helldivers":
                    cmd_box_top = f"[{'=' * (history_width)}]"
                    cmd_box_bottom = f"[{'=' * (history_width)}]"
        else:
                    cmd_box_top = f"+{'-' * (history_width)}+"
                    cmd_box_bottom = f"+{'-' * (history_width)}+"
                
                safe_addstr(stdscr, cmd_y, 2, cmd_box_top)
                
                # Command history display
                history_count = min(2, len(command_history))
                for i in range(history_count):
                    idx = len(command_history) - history_count + i
        if 0 <= idx < len(command_history):
                        cmd = command_history[idx]
        if len(cmd) > history_width - 5:
                            cmd = cmd[:history_width-8] + "..."
                        safe_addstr(stdscr, cmd_y + 1 + i, 4, f"> {cmd}")
                
                # Display command output if there's any
        if command_output:
                    output_y = cmd_y + 1 + history_count
        if output_y < h-3:
        pass
                        output_lines = command_output.split('\n')
                        for i, line in enumerate(output_lines):
        if output_y + i < h-3:
        if len(line) > history_width - 5:
                                    line = line[:history_width-8] + "..."
                                safe_addstr(stdscr, output_y + i, 4, line, curses.color_pair(5))
                
                safe_addstr(stdscr, cmd_y + 3, 2, cmd_box_bottom)
            
            # Command help/input prompt at bottom of screen
            help_y = h - 2
            
        if input_mode:
        pass
if theme == "military":
                    prompt = "ENTER COMMAND: "
        elif theme == "wh40k":
                    prompt = "ISSUE DECREE: "
        elif theme == "tars":
                    prompt = "CMD> "
        elif theme == "helldivers":
                    prompt = "DECLARE FREEDOM: "
                
                safe_addstr(stdscr, help_y, 2, prompt, curses.A_BOLD)
                
                # Display command buffer with cursor
                safe_addstr(stdscr, help_y, 2 + len(prompt), command_buffer)
                curses.curs_set(1)  # Show cursor
                stdscr.move(help_y, 2 + len(prompt) + len(command_buffer))
        else:
        pass
if theme == "military":
                    help_text = "[ Q:QUIT | M:MODE | R:REFRESH | S:STYLE | I:INPUT ]"
        elif theme == "wh40k":
                    help_text = "[ Q:RETREAT | M:MODE | R:REFRESH | S:STYLE | I:COMMAND ]"
        elif theme == "tars":
                    help_text = "[ Q:EXIT | M:MODE | R:REFRESH | S:STYLE | I:CMD ]"
        elif theme == "helldivers":
                    help_text = "[ Q:EXTRACT | M:MODE | R:REFRESH | S:STYLE | I:ORDERS ]"
                
                # Draw help in a styled box
                help_box_top = f"*{'*' * (w-2)}*"
                safe_addstr(stdscr, help_y-1, 0, help_box_top)
                # Center the command help
                safe_addstr(stdscr, help_y, w//2 - len(help_text)//2, help_text, curses.A_BOLD)
                
                # Display current style at the right side with yellow color
                style_display = f"STYLE: {theme.upper()}"
                safe_addstr(stdscr, help_y, w - len(style_display) - 2, style_display, curses.color_pair(5))
                
                safe_addstr(stdscr, help_y+1, 0, help_box_top)
            
            # Process input
            key = stdscr.getch()
            
        if input_mode:
        pass
        if key == curses.KEY_ENTER or key == 10 or key == 13:  # Enter
                    # Process command
        if command_buffer:
                        command_history.append(command_buffer)
                        command_output = process_command(command_buffer)
                        command_buffer = ""
                    input_mode = False
                    curses.curs_set(0)
        elif key == 27:  # Escape
                    command_buffer = ""
                    input_mode = False
                    curses.curs_set(0)
        elif key == curses.KEY_BACKSPACE or key == 8 or key == 127:  # Backspace
                    command_buffer = command_buffer[:-1]
        elif key == curses.KEY_UP:  # Up arrow - command history
        if command_history:
                        command_history_index = max(0, command_history_index - 1)
        if command_history_index < len(command_history):
                            command_buffer = command_history[command_history_index]
        elif key == curses.KEY_DOWN:  # Down arrow - command history
        if command_history:
                        command_history_index = min(len(command_history), command_history_index + 1)
        if command_history_index < len(command_history):
                            command_buffer = command_history[command_history_index]
        else:
                            command_buffer = ""
        elif 32 <= key <= 126:  # Printable ASCII
                    command_buffer += chr(key)
        else:
        pass
        if key == ord('q') or key == ord('Q'):
                    break
        elif key == ord('m') or key == ord('M'):
                    system_mode = "CRITICAL" if system_mode == "NORMAL" else "NORMAL"
                    command_output = f"System mode changed to: {system_mode}"
        elif key == ord('r') or key == ord('R'):
                    last_update = datetime.datetime.now()
                    command_output = "Display refreshed"
        elif key == ord('s') or key == ord('S'):
        pass
        if STYLE["theme"] == "military":
                        STYLE["theme"] = "wh40k"
        elif STYLE["theme"] == "wh40k":
                        STYLE["theme"] = "tars"
        elif STYLE["theme"] == "tars":
                        STYLE["theme"] = "helldivers"
        else:
                        STYLE["theme"] = "military"
                    command_output = f"Style changed to: {STYLE['theme']}"
        elif key == ord('i') or key == ord('I'):
                    input_mode = True
                    command_history_index = len(command_history)
                    
            stdscr.refresh()
            
        except Exception as e:
            try:
                stdscr.clear()
                safe_addstr(stdscr, 0, 0, f"ERROR: {str(e)}")
                stdscr.refresh()
                time.sleep(2)
            except:
        pass

def safe_addstr(stdscr, y, x, text, attr=0):
    """Safely add a string to the screen, checking boundaries"""
    height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
        return
        
    # Truncate text if it would go off screen
    max_len = width - x
        if max_len <= 0:
        return
    
        if len(text) > max_len:
        text = text[:max_len]
        
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass
        pass

def get_vote_info(path):
    """Get vote information from the vote JSON file"""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                vote_data = json.load(f)
                return vote_data
    except Exception as e:
        pass
    return {}

def wrap_text(text, width):
    """Wrap text to fit within width"""
        if not text:
        return []
        
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + len(current_line) > width:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word)
    
        if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def calculate_consensus(votes):
    """Calculate consensus based on votes"""
    approve_votes = sum(1 for vote in votes.values() if vote == "APPROVE")
    deny_votes = sum(1 for vote in votes.values() if vote == "DENY")
    
        if approve_votes >= 2:
        return "APPROVE"
        elif deny_votes >= 2:
        return "DENY"
    
    # No consensus yet
    return None

if __name__ == "__main__":
        pass
    print("\033[2J\033[H")  # Clear screen
    print("""
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
                                      
    ENHANCED COMMAND & CONTROL INTERFACE v2.0
    """)
    
    print("\n\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Simulate steampunk-style loading with gear animations
    print("\n◢◣ Checking system resources...")
    time.sleep(0.5)
    print("  ├─ CPU availability.............. [✓]")
    time.sleep(0.3)
    print("  ├─ Memory alignment.............. [✓]")
    time.sleep(0.3)
    print("  └─ Display capabilities.......... [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Initializing quantum calculators...")
    time.sleep(0.5)
    print("  ├─ Rationalis core............... [✓]")
    time.sleep(0.3)
    print("  ├─ Aeternum module............... [✓]")
    time.sleep(0.3)
    print("  └─ Bellator engine............... [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Establishing directory architecture...")
    os.makedirs("./_ARBITER/tmp_votes", exist_ok=True)
    print("  ├─ ARBITER connections........... [✓]")
    time.sleep(0.2)
    os.makedirs("./Rationalis", exist_ok=True)
    print("  ├─ Rationalis linkage............ [✓]")
    time.sleep(0.2)
    os.makedirs("./Aeternum", exist_ok=True)
    print("  ├─ Aeternum pathways............. [✓]")
    time.sleep(0.2)
    os.makedirs("./Bellator", exist_ok=True)
    print("  ├─ Bellator conduits............. [✓]")
    time.sleep(0.2)
    os.makedirs("./logs", exist_ok=True)
    print("  ├─ Logbook creation.............. [✓]")
    time.sleep(0.2)
    os.makedirs("./exports", exist_ok=True)
    print("  └─ Export valves................. [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Calibrating system protocols...")
    time.sleep(0.5)
    print("  ├─ Interface mechanisms.......... [✓]")
    time.sleep(0.3)
    print("  ├─ Security valves............... [✓]")
    time.sleep(0.3)
    print("  └─ Command relays................ [✓]")
    time.sleep(0.5)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    print("""
\033[1;33m▶ Control Keys:\033[0m
  - \033[1;36mQ\033[0m: Quit               - \033[1;36mM\033[0m: Toggle mode (NORMAL/CRITICAL)
  - \033[1;36mS\033[0m: Cycle styles       - \033[1;36mI\033[0m: Enter command mode
  - \033[1;36mH\033[0m: Help screen        - \033[1;36mC\033[0m: Configuration
  - \033[1;36mD\033[0m: Decision history
    """)
    
    print("\033[1;32m■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE...\033[0m")
    input()
    
    # Create a keyboard interrupt handler
    def signal_handler(sig, frame):
        print("\n\033[1;31mShutting down CONSENSUS War Room...\033[0m")
        print("Goodbye.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the War Room
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[1;31mShutting down CONSENSUS War Room...\033[0m")
    finally:
        print("Goodbye.")

# ===== FILE: consensus_war_room1.py =====
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
        pass
        elif theme == "wh40k":
        pass
        elif theme == "tars":
        pass
        elif theme == "helldivers":
        pass
        else:
        pass
        
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

def render_aeternum_screen(stdscr, theme, height, width):
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
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
        pass
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
    # Removed corrupted safe_addstr line
            
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
"""
CONSENSUS War Room - Command and Control Interface

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

def render_boot_sequence(stdscr):
    """Render the boot sequence animation with NERV logo"""
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw NERV logo in red
    logo_lines = NERV_LOGO.split('\n')
    for i, line in enumerate(logo_lines):
        if i < height and line.strip():  # Skip empty lines
            # Use color pair 1 (red) for the logo
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(stdscr, i, max(0, (width - len(line)) // 2), line)
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    
    # Display version information below the logo
    version_text = f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"
    safe_addstr(stdscr, len(logo_lines), (width - len(version_text)) // 2, version_text, curses.color_pair(6) | curses.A_BOLD)
    
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
        pass
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
        pass
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
            
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
    # Removed corrupted f-string call
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
        pass
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
    footer = "Press '2' to return to main view"
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
        pass
        elif theme == "wh40k":
        pass
        elif theme == "tars":
        pass
        elif theme == "helldivers":
        pass
        else:
        pass
        
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
        pass
        rationalis_len = int(balance["rationalis_influence"] * 30)
        aeternum_len = int(balance["aeternum_influence"] * 30)
        bellator_len = int(balance["bellator_influence"] * 30)
        
        safe_addstr(stdscr, y_pos, 4, "Rationalis: ", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
        safe_addstr(stdscr, y_pos, 15, "[" + "#" * rationalis_len + " " * (30 - rationalis_len) + "]", curses.color_pair(MONOLITHS["RATIONALIS"]["color"]))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+1, 4, "Aeternum:  ", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
        safe_addstr(stdscr, y_pos+1, 15, "[" + "#" * aeternum_len + " " * (30 - aeternum_len) + "]", curses.color_pair(MONOLITHS["AETERNUM"]["color"]))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+2, 4, "Bellator:  ", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
        safe_addstr(stdscr, y_pos+2, 15, "[" + "#" * bellator_len + " " * (30 - bellator_len) + "]", curses.color_pair(MONOLITHS["BELLATOR"]["color"]))
    # Removed corrupted f-string call
        
        # Consensus and conflict rates
        consensus_color = 2 if balance["consensus_rate"] > 0.7 else 3 if balance["consensus_rate"] > 0.5 else 1
        conflict_color = 2 if balance["conflict_rate"] < 0.3 else 3 if balance["conflict_rate"] < 0.5 else 1
        
    # Removed corrupted f-string call
    # Removed corrupted f-string call
    
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
        pass
        page = 1
        max_page = 2
        
        # Page indicator
        page_text = f"Page {help_page}/{max_page} (Press SPACE for next page)"
        safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(page_text)) // 2, 
                   page_text, curses.A_BOLD)
        
        if help_page == 1:
        pass
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
        pass
            for category, commands in list(command_categories.items())[3:]:
                safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
                current_y += 1
                
                for cmd in commands:
                    safe_addstr(stdscr, current_y, help_x + 4, cmd)
                    current_y += 1
                
                current_y += 1
        else:
        pass
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
        pass
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
        pass
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
        pass
        pass

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
        pass
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
        pass
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
        pass
        if "analysis" not in MONOLITH_DATA["AETERNUM"]:
                    MONOLITH_DATA["AETERNUM"]["analysis"] = []
                MONOLITH_DATA["AETERNUM"]["analysis"].insert(0, answer)
        elif monolith_name.upper() == "RATIONALIS":
        pass
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
    global CURRENT_VIEW, CURRENT_MODE, command_output, STYLE, CONFIG, active_monolith
    
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
            CURRENT_VIEW = f"MONOLITH_{monolith}"
            threading.Thread(target=handle_monolith_query, args=(monolith, query), daemon=True).start()
            return f"Querying {monolith} with: {query}"
        else:
            return f"Usage: {cmd} <query>"
    
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
        pass
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
    global CURRENT_VIEW, input_mode, command_buffer, command_output, help_page
    
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
        pass
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
        pass
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

# ===== FILE: consensus-system.py =====
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    metrics = MONOLITH_DATA["Rationalis"]["analysis_metrics"]
    idx = 0
    for name, value in metrics.items():
        if y_pos + idx//2 < h-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
        if isinstance(value, float):
                score_color = 4 if value > 0.8 else 5 if value > 0.6 else 6
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
        if MONOLITH_DATA["Rationalis"]["last_updated"]:
        update_time = MONOLITH_DATA["Rationalis"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '1' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_arbiter_screen(stdscr, h, w, theme):
    """Draw the Arbiter specialized screen"""
    # Clear the screen
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Arbiter"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Arbiter"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with custom color (white bold)
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, curses.A_BOLD | curses.color_pair(7))
    
    # System status
    y_pos = 3
    status = MONOLITH_DATA["Arbiter"]["system_status"]
    status_text = ""
    
if theme == "military":
        status_text = f"SYSTEM STATUS: {status['monoliths_online']}/3 MONOLITHS ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
        elif theme == "wh40k":
        status_text = f"MECHANICUS STATUS: {status['monoliths_online']}/3 ACTIVE | ASTROPATH: {status['communication_integrity']*100:.1f}% | THROUGHPUT: {status['decision_throughput']:.1f}/h"
        elif theme == "tars":
        status_text = f"SYSTEM.STATUS: ACTIVE={status['monoliths_online']}/3 COMMS={status['communication_integrity']*100:.1f}% RATE={status['decision_throughput']:.1f}/h"
        elif theme == "helldivers":
        status_text = f"DEMOCRACY STATUS: {status['monoliths_online']}/3 ACTIVE | COMMS: {status['communication_integrity']*100:.1f}% | LIBERTY RATE: {status['decision_throughput']:.1f}/h"
    
    safe_addstr(stdscr, y_pos, w//2 - len(status_text)//2, status_text, curses.A_BOLD)
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    agenda = MONOLITH_DATA["Arbiter"]["agenda"]
    for idx, item in enumerate(agenda):
        if y_pos + idx < h-12:
            priority_color = 4 if item["priority"] == "Low" else 5 if item["priority"] == "Medium" else 6
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    decisions = MONOLITH_DATA["Arbiter"]["pending_decisions"]
    for idx, decision in enumerate(decisions):
        if y_pos + idx < h-8:
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    balance = MONOLITH_DATA["Arbiter"]["balance_metrics"]
    
    # Draw a balance chart
        if y_pos + 4 < h-6:
        pass
        rationalis_len = int(balance["rationalis_influence"] * 30)
        aeternum_len = int(balance["aeternum_influence"] * 30)
        bellator_len = int(balance["bellator_influence"] * 30)
        
        safe_addstr(stdscr, y_pos, 4, "Rationalis: ", curses.color_pair(2))
        safe_addstr(stdscr, y_pos, 15, "[" + "#" * rationalis_len + " " * (30 - rationalis_len) + "]", curses.color_pair(2))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+1, 4, "Aeternum:  ", curses.color_pair(1))
        safe_addstr(stdscr, y_pos+1, 15, "[" + "#" * aeternum_len + " " * (30 - aeternum_len) + "]", curses.color_pair(1))
    # Removed corrupted f-string call
        
        safe_addstr(stdscr, y_pos+2, 4, "Bellator:  ", curses.color_pair(3))
        safe_addstr(stdscr, y_pos+2, 15, "[" + "#" * bellator_len + " " * (30 - bellator_len) + "]", curses.color_pair(3))
    # Removed corrupted f-string call
        
        # Consensus and conflict rates
        consensus_color = 4 if balance["consensus_rate"] > 0.7 else 5 if balance["consensus_rate"] > 0.5 else 6
        conflict_color = 4 if balance["conflict_rate"] < 0.3 else 5 if balance["conflict_rate"] < 0.5 else 6
        
    # Removed corrupted f-string call
    # Removed corrupted f-string call
    
    # Footer
        if MONOLITH_DATA["Arbiter"]["last_updated"]:
        update_time = MONOLITH_DATA["Arbiter"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '4' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

# Add functions for updating monolith-specific data

def update_bellator_data():
    """Update Bellator's security and military data"""
    try:
        pass
        
        # DEFCON level (would come from official sources if available)
        MONOLITH_DATA["Bellator"]["defcon_level"] = random.randint(3, 5)
        
        # Threat alerts (would come from news APIs)
        MONOLITH_DATA["Bellator"]["threat_alerts"] = [
            {"region": "Middle East", "level": "Elevated", "description": "Increased tension in regional conflict zones"},
            {"region": "Cybersecurity", "level": "High", "description": "Multiple attacks targeting financial institutions"},
            {"region": "Pacific", "level": "Moderate", "description": "Naval exercises causing diplomatic tension"}
        ]
        
        # News (would come from NewsAPI)
        MONOLITH_DATA["Bellator"]["security_news"] = [
            {"title": "New Defense Pact Signed Between Major Powers", "source": "World Politics", "time": "3h ago"},
            {"title": "Cybersecurity Breach Affects Military Contractors", "source": "Tech Defense", "time": "8h ago"},
            {"title": "Strategic Resource Discovered in Disputed Territory", "source": "Resource Monitor", "time": "12h ago"}
        ]
        
        # Strategic analysis (would be generated by the Bellator monolith)
        MONOLITH_DATA["Bellator"]["strategic_analysis"] = [
            "Primary threats concentrated in cyber domain with 64% increase in state-sponsored attacks",
            "Resource contention increasing risk of conflict in 3 key regions",
            "Defensive posture recommended with emphasis on intelligence gathering"
        ]
        
        MONOLITH_DATA["Bellator"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Bellator data: {e}")
        return False

def update_rationalis_data():
    """Update Rationalis's logic and analysis data"""
    try:
        pass
        
        # System logs
        MONOLITH_DATA["Rationalis"]["system_logs"] = [
            {"timestamp": "15:42:23", "level": "INFO", "message": "Analysis framework optimized, +12% efficiency"},
            {"timestamp": "14:37:01", "level": "WARNING", "message": "Recursive pattern detected in query syntax"},
            {"timestamp": "12:15:49", "level": "INFO", "message": "Knowledge base updated with 537 new entries"}
        ]
        
        # Logic patterns (simulated ML metrics)
        MONOLITH_DATA["Rationalis"]["logic_patterns"] = {
            "inductive_reasoning": 0.87,
            "deductive_reasoning": 0.93,
            "abductive_reasoning": 0.76,
            "analogical_reasoning": 0.82,
            "logical_fallacies_detected": 7
        }
        
        # Analysis metrics
        MONOLITH_DATA["Rationalis"]["analysis_metrics"] = {
            "query_complexity_avg": 7.8,
            "inference_depth_avg": 12.3,
            "contextual_awareness": 0.85,
            "bias_detection": 0.91,
            "factual_accuracy": 0.94
        }
        
        # Efficiency rating
        MONOLITH_DATA["Rationalis"]["efficiency_rating"] = random.uniform(0.88, 0.97)
        
        MONOLITH_DATA["Rationalis"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Rationalis data: {e}")
        return False

def update_arbiter_data():
    """Update Arbiter's management and coordination data"""
    try:
        pass
        
        # Agenda items
        MONOLITH_DATA["Arbiter"]["agenda"] = [
            {"time": "10:00", "task": "Security protocol review", "priority": "High"},
            {"time": "13:30", "task": "Financial market analysis", "priority": "Medium"},
            {"time": "15:45", "task": "Strategic planning session", "priority": "High"},
            {"time": "17:00", "task": "System optimization", "priority": "Low"}
        ]
        
        # Pending decisions (based on CONSENSUS data)
        MONOLITH_DATA["Arbiter"]["pending_decisions"] = [
            {"query": "Authorize fund reallocation to defensive assets?", "status": "Under review"},
            {"query": "Increase security monitoring in sector 7?", "status": "Awaiting consensus"},
            {"query": "Deploy new analytical model v4.3?", "status": "Data collection"}
        ]
        
        # System status
        MONOLITH_DATA["Arbiter"]["system_status"] = {
            "monoliths_online": 3,
            "communication_integrity": 0.99,
            "decision_throughput": 8.4,
            "balance_index": 0.87
        }
        
        # Balance metrics (measuring how well the monoliths are working together)
        MONOLITH_DATA["Arbiter"]["balance_metrics"] = {
            "rationalis_influence": 0.33,
            "aeternum_influence": 0.35,
            "bellator_influence": 0.32,
            "consensus_rate": 0.76,
            "conflict_rate": 0.21
        }
        
        MONOLITH_DATA["Arbiter"]["last_updated"] = datetime.datetime.now()
        return True
    except Exception as e:
        print(f"Error updating Arbiter data: {e}")
        return False

def draw_main_interface(stdscr):
    """Draw the main interface with all monolith panels"""
    h, w = stdscr.getmaxyx()
    theme = CONFIG["theme"]
    system_mode = CONFIG["system_mode"]
    
    # Draw decorative border at top
    border_char = BOX_CHARS[theme]["horizontal"]
    mode_info = SYSTEM_MODES[system_mode]
    border = border_char * (w-2)
    safe_addstr(stdscr, 0, 1, border, curses.A_BOLD)
    
    # Draw header based on style
if theme == "military":
        header = f" {mode_info['symbol'][theme]} CONSENSUS WAR ROOM {mode_info['symbol'][theme]} "
        mode_display = f"SYS-MODE: {system_mode}"
        elif theme == "wh40k":
        header = f" MECHANICUS CONSENSII {mode_info['symbol'][theme]} COMMAND THRONE "
        mode_display = f"IMPERIUM STATUS: {system_mode}"
        elif theme == "tars":
        header = f" CONSENSUS.CORE.{system_mode} {mode_info['symbol'][theme]} "
        mode_display = f"SYS.MODE={system_mode}"
        elif theme == "helldivers":
        header = f" ★ SUPER EARTH COMMAND CENTER {mode_info['symbol'][theme]} "
        mode_display = f"DEMOCRACY STATUS: {system_mode}"
        
        if system_mode == "CRITICAL":
if theme == "military":
            header = "/// CRITICAL ALERT ACTIVE ///"
        elif theme == "wh40k":
            header = "!!! EXTERMINATUS PROTOCOL ACTIVE !!!"
        elif theme == "tars":
            header = "*** CRITICAL.OVERRIDE.ACTIVE ***"
        elif theme == "helldivers":
            header = "!!! LIBERTY EMERGENCY PROTOCOL ACTIVE !!!"
    
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(mode_info["color_pair"]))
    
    # Draw timestamp and mode indicator
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_addstr(stdscr, 1, 2, mode_display, 
             curses.color_pair(mode_info["color_pair"]))
    safe_addstr(stdscr, 1, w - len(timestamp) - 2, timestamp)
    
    # Draw second border
    safe_addstr(stdscr, 2, 1, border, curses.A_BOLD)
    
    # Draw current query with style-specific header
    query_display = CONFIG["current_query"]
        if len(query_display) > w-12:
        query_display = query_display[:w-15] + "..."
    
if theme == "military":
        query_header = "[ ACTIVE QUERY ]"
        elif theme == "wh40k":
        query_header = "[ IMPERIAL INQUIRY ]"
        elif theme == "tars":
        query_header = "[ QUERY.ACTIVE ]"
        elif theme == "helldivers":
        query_header = "[ MISSION DIRECTIVE ]"
        
    safe_addstr(stdscr, 3, w//2 - len(query_header)//2, query_header, curses.A_BOLD)
    safe_addstr(stdscr, 4, w//2 - len(query_display)//2, query_display)
    
    # Divider after query
    safe_addstr(stdscr, 5, 1, border, curses.A_BOLD)
    
    # Draw monolith panels
    panel_y = 7
    for name, info in MONOLITHS.items():
        # Check if we have room to draw this panel
        if panel_y + 9 >= h:
            break
        
        next_y = draw_monolith_panel(stdscr, name, info, panel_y, w, h)
        panel_y = next_y + 1
    
    # Draw consensus box if there's room
        if panel_y + 4 < h - 6:
        draw_consensus_panel(stdscr, panel_y, w, h)
        panel_y += 5
    
    # Draw notifications if enabled and there's room
        if CONFIG["show_notifications"] and notifications and panel_y + 5 < h - 6:
        draw_notifications(stdscr, panel_y, 2, w - 4, 5)
        panel_y += 6
    
    # Draw system health if enabled and there's room
        if CONFIG["show_health"] and panel_y + 5 < h - 2:
        draw_system_health(stdscr, panel_y, 2, w - 4, 5)

def draw_command_area(stdscr, h, w, input_mode, command_buffer):
    """Draw the command input area at the bottom of the screen"""
    help_y = h - 2
    theme = CONFIG["theme"]
    
        if input_mode:
        pass
if theme == "military":
            prompt = "ENTER COMMAND: "
        elif theme == "wh40k":
            prompt = "ISSUE DECREE: "
        elif theme == "tars":
            prompt = "CMD> "
        elif theme == "helldivers":
            prompt = "DECLARE FREEDOM: "
        
        safe_addstr(stdscr, help_y, 2, prompt, curses.A_BOLD)
        
        # Display command buffer with cursor
        safe_addstr(stdscr, help_y, 2 + len(prompt), command_buffer)
        curses.curs_set(1)  # Show cursor
        stdscr.move(help_y, 2 + len(prompt) + len(command_buffer))
        else:
        pass
if theme == "military":
            help_text = "[ Q:QUIT | M:MODE | R:REFRESH | S:STYLE | I:INPUT | 1-4:MONOLITHS | H/C/D:VIEWS ]"
        elif theme == "wh40k":
            help_text = "[ Q:RETREAT | M:MODE | R:REFRESH | S:STYLE | I:COMMAND | 1-4:COGITATORS | H/C/D:VIEWS ]"
        elif theme == "tars":
            help_text = "[ Q:EXIT | M:MODE | R:REFRESH | S:STYLE | I:CMD | 1-4:NODES | H/C/D:VIEWS ]"
        elif theme == "helldivers":
            help_text = "[ Q:EXTRACT | M:MODE | R:REFRESH | S:STYLE | I:ORDERS | 1-4:STRATAGEMS | H/C/D:VIEWS ]"
        
        # Draw help in a styled box
        help_box_top = f"*{'*' * (w-2)}*"
        safe_addstr(stdscr, help_y-1, 0, help_box_top)
        # Center the command help
        safe_addstr(stdscr, help_y, w//2 - len(help_text)//2, help_text, curses.A_BOLD)
        
        # Display current style at the right side with yellow color
        style_display = f"STYLE: {theme.upper()}"
        safe_addstr(stdscr, help_y, w - len(style_display) - 2, style_display, curses.color_pair(5))
        
        safe_addstr(stdscr, help_y+1, 0, help_box_top)

def main(stdscr):
    """Main function that runs the CONSENSUS War Room interface"""
    # Setup
    curses.curs_set(0)  # Hide cursor initially
    curses.start_color()
    curses.use_default_colors()
    
    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # Aeternum
    curses.init_pair(2, curses.COLOR_BLUE, -1)     # Rationalis
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)  # Bellator
    curses.init_pair(4, curses.COLOR_GREEN, -1)    # APPROVE/Online
    curses.init_pair(5, curses.COLOR_YELLOW, -1)   # WARNING/CRITICAL/Processing
    curses.init_pair(6, curses.COLOR_RED, -1)      # DENY/Offline
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # Normal text
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)    # Alert background
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Success background
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Command input
    curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_WHITE) # Light mode text
    curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLACK) # Dark mode highlight
    
    stdscr.timeout(100)  # Refresh rate in ms
    
    # Local UI state
    input_mode = False
    command_buffer = ""
    animated_text_position = 0
    
    # Start background threads
    threading.Thread(target=update_model_statuses, daemon=True).start()
    
    # Simulate initial data for monoliths
    update_bellator_data()
    update_aeternum_data()
    update_rationalis_data()
    update_arbiter_data()
    
    # Simulate initial system status
    for name in MONOLITHS:
        MONOLITHS[name]["status"] = random.choice(["online", "processing", "offline"])
    
    # Add initial notifications
        add_notification("CONSENSUS System initialized", "info")
        add_notification("All monoliths ready for operation", "success")
    
    while True:
        try:
            h, w = stdscr.getmaxyx()
            stdscr.clear()
            
            # Check if terminal is big enough
        if h < 25 or w < 80:
                safe_addstr(stdscr, 0, 0, "Terminal too small. Resize to at least 80x25.")
                stdscr.refresh()
                time.sleep(1)
                continue
            
            # Handle different view modes
        if CONFIG["view_mode"] == "HELP":
                draw_help_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "CONFIG":
                draw_config_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "HISTORY":
                draw_history_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "MONOLITH_BELLATOR":
                draw_bellator_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "MONOLITH_AETERNUM":
                draw_aeternum_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "MONOLITH_RATIONALIS":
                draw_rationalis_screen(stdscr, h, w, CONFIG["theme"])
        elif CONFIG["view_mode"] == "MONOLITH_ARBITER":
                draw_arbiter_screen(stdscr, h, w, CONFIG["theme"])
        else:
        pass
                draw_main_interface(stdscr)
            
            # Always draw command area at the bottom
            draw_command_area(stdscr, h, w, input_mode, command_buffer)
            
            # Process input
            key = stdscr.getch()
            
        if input_mode:
        pass
        if key == curses.KEY_ENTER or key == 10 or key == 13:  # Enter
                    # Process command
        if command_buffer:
                        command_history.append(command_buffer)
                        global command_output
                        command_output = process_command(command_buffer)
                        command_buffer = ""
                    input_mode = False
                    curses.curs_set(0)
        elif key == 27:  # Escape
                    command_buffer = ""
                    input_mode = False
                    curses.curs_set(0)
        elif key == curses.KEY_BACKSPACE or key == 8 or key == 127:  # Backspace
                    command_buffer = command_buffer[:-1]
        elif key == curses.KEY_UP:  # Up arrow - command history
        if command_history:
                        global command_history_index
                        command_history_index = max(0, command_history_index - 1)
        if command_history_index < len(command_history):
                            command_buffer = command_history[command_history_index]
        elif key == curses.KEY_DOWN:  # Down arrow - command history
        if command_history:
                        command_history_index = min(len(command_history), command_history_index + 1)
        if command_history_index < len(command_history):
                            command_buffer = command_history[command_history_index]
        else:
                            command_buffer = ""
        elif key == 9:  # Tab - autocomplete
        if CONFIG["enable_autocomplete"]:
                        suggestions = get_command_suggestions(command_buffer)
        if suggestions and len(suggestions) == 1:
                            command_buffer = suggestions[0]
        elif 32 <= key <= 126:  # Printable ASCII
                    command_buffer += chr(key)
        else:
        pass
        if key == ord('q') or key == ord('Q'):
                    break
        elif key == ord('m') or key == ord('M'):
                    CONFIG["system_mode"] = "CRITICAL" if CONFIG["system_mode"] == "NORMAL" else "NORMAL"
                    command_output = f"System mode changed to: {CONFIG['system_mode']}"
        elif key == ord('r') or key == ord('R'):
                    command_output = "Display refreshed"
        elif key == ord('s') or key == ord('S'):
        pass
                    themes = ["military", "wh40k", "tars", "helldivers"]
                    current_idx = themes.index(CONFIG["theme"])
                    next_idx = (current_idx + 1) % len(themes)
                    CONFIG["theme"] = themes[next_idx]
                    command_output = f"Style changed to: {CONFIG['theme']}"
        elif key == ord('i') or key == ord('I'):
                    input_mode = True
                    command_history_index = len(command_history)
        elif key == ord('h') or key == ord('H'):
                    CONFIG["view_mode"] = "HELP" if CONFIG["view_mode"] != "HELP" else "MAIN"
        elif key == ord('c') or key == ord('C'):
                    CONFIG["view_mode"] = "CONFIG" if CONFIG["view_mode"] != "CONFIG" else "MAIN"
        elif key == ord('d') or key == ord('D'):
                    CONFIG["view_mode"] = "HISTORY" if CONFIG["view_mode"] != "HISTORY" else "MAIN"
        elif key == ord('1'):
                    CONFIG["view_mode"] = "MONOLITH_RATIONALIS" if CONFIG["view_mode"] != "MONOLITH_RATIONALIS" else "MAIN"
        elif key == ord('2'):
                    CONFIG["view_mode"] = "MONOLITH_AETERNUM" if CONFIG["view_mode"] != "MONOLITH_AETERNUM" else "MAIN"
        elif key == ord('3'):
                    CONFIG["view_mode"] = "MONOLITH_BELLATOR" if CONFIG["view_mode"] != "MONOLITH_BELLATOR" else "MAIN"
        elif key == ord('4'):
                    CONFIG["view_mode"] = "MONOLITH_ARBITER" if CONFIG["view_mode"] != "MONOLITH_ARBITER" else "MAIN"
        elif key == ord(' ') and CONFIG["view_mode"] == "HELP":
        pass
                    global help_page
                    help_page = 2 if help_page == 1 else 1
            
            stdscr.refresh()
            
        except Exception as e:
            try:
                stdscr.clear()
                safe_addstr(stdscr, 0, 0, f"ERROR: {str(e)}")
                stdscr.refresh()
                time.sleep(2)
            except:
        pass

def boot_sequence():
    """Display a fancy boot sequence animation"""
    print("\033[2J\033[H")  # Clear screen
    print(CONSENSUS_LOGO)
    time.sleep(1)
    
    print("\n\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # System boot animation
    print("\n◢◣ Checking system resources...")
    time.sleep(0.5)
    print("  ├─ CPU availability.............. [✓]")
    time.sleep(0.3)
    print("  ├─ Memory alignment.............. [✓]")
    time.sleep(0.3)
    print("  └─ Display capabilities.......... [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Initializing quantum calculators...")
    time.sleep(0.5)
    print("  ├─ Rationalis core............... [✓]")
    time.sleep(0.3)
    print("  ├─ Aeternum module............... [✓]")
    time.sleep(0.3)
    print("  └─ Bellator engine............... [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Establishing directory architecture...")
    setup_directories()
    print("  ├─ ARBITER connections........... [✓]")
    time.sleep(0.2)
    print("  ├─ Rationalis linkage............ [✓]")
    time.sleep(0.2)
    print("  ├─ Aeternum pathways............. [✓]")
    time.sleep(0.2)
    print("  ├─ Bellator conduits............. [✓]")
    time.sleep(0.2)
    print("  ├─ Logbook creation.............. [✓]")
    time.sleep(0.2)
    print("  └─ Export valves................. [✓]")
    time.sleep(0.5)
    
    print("\n◢◣ Calibrating system protocols...")
    time.sleep(0.5)
    print("  ├─ Interface mechanisms.......... [✓]")
    time.sleep(0.3)
    print("  ├─ Security valves............... [✓]")
    time.sleep(0.3)
    print("  └─ Command relays................ [✓]")
    time.sleep(0.5)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    print("""
\033[1;33m▶ Control Keys:\033[0m
  - \033[1;36mQ\033[0m: Quit               - \033[1;36mM\033[0m: Toggle mode (NORMAL/CRITICAL)
  - \033[1;36mS\033[0m: Cycle styles       - \033[1;36mI\033[0m: Enter command mode
  - \033[1;36mH\033[0m: Help screen        - \033[1;36mC\033[0m: Configuration
  - \033[1;36mD\033[0m: Decision history   - \033[1;36m1-4\033[0m: Monolith views
    """)
    
    print("\033[1;32m■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE...\033[0m")
    input()

if __name__ == "__main__":
        pass
    boot_sequence()
    
    # Create a keyboard interrupt handler
    def signal_handler(sig, frame):
        print("\n\033[1;31mShutting down CONSENSUS System...\033[0m")
        print("Goodbye.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the War Room
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n\033[1;31mShutting down CONSENSUS System...\033[0m")
    finally:
        print("Goodbye.")
def safe_addstr(stdscr, y, x, text, attr=0):
    """Safely add a string to the screen, checking boundaries"""
    height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
        return
        
    # Truncate text if it would go off screen
    max_len = width - x
        if max_len <= 0:
        return
    
        if len(text) > max_len:
        text = text[:max_len]
        
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass
        pass

def draw_box(stdscr, y, x, width, height, title=None, box_style=None):
    """Draw a styled box with optional title"""
        if box_style is None:
        box_style = BOX_CHARS[CONFIG["theme"]]
    
    # Draw corners
    safe_addstr(stdscr, y, x, box_style["top_left"])
    safe_addstr(stdscr, y, x + width - 1, box_style["top_right"])
    safe_addstr(stdscr, y + height - 1, x, box_style["bottom_left"])
    safe_addstr(stdscr, y + height - 1, x + width - 1, box_style["bottom_right"])
    
    # Draw horizontal edges
    h_bar = box_style["horizontal"] * (width - 2)
    safe_addstr(stdscr, y, x + 1, h_bar)
    safe_addstr(stdscr, y + height - 1, x + 1, h_bar)
    
    # Draw vertical edges
    for i in range(1, height - 1):
        safe_addstr(stdscr, y + i, x, box_style["vertical"])
        safe_addstr(stdscr, y + i, x + width - 1, box_style["vertical"])
    
    # Add title if provided
        if title:
        title_x = x + (width - len(title)) // 2
        safe_addstr(stdscr, y, title_x, f" {title} ", curses.A_BOLD)

def draw_notifications(stdscr, y, x, width, height):
    """Draw the notifications panel"""
        if not CONFIG["show_notifications"] or not notifications:
        return
    
    # Draw notification box
    draw_box(stdscr, y, x, width, height, "NOTIFICATIONS")
    
    # Display notifications with timestamp and level-based coloring
    max_display = min(len(notifications), height - 2)
    for i in range(max_display):
        notification = notifications[i]
        level = notification["level"]
        color = notification_colors.get(level, 7)  # Default white
        
        timestamp = notification["timestamp"].strftime("%H:%M:%S")
        if level == "error":
            prefix = "[ERROR]"
        elif level == "warning":
            prefix = "[WARN]"
        elif level == "success":
            prefix = "[OK]"
        else:
            prefix = "[INFO]"
            
        # Format and display notification
        notification_text = f"{timestamp} {prefix} {notification['message']}"
        if len(notification_text) > width - 4:
            notification_text = notification_text[:width - 7] + "..."
            
        safe_addstr(stdscr, y + i + 1, x + 2, notification_text, curses.color_pair(color))

def draw_system_health(stdscr, y, x, width, height):
    """Draw system health metrics panel"""
        if not CONFIG["show_health"]:
        return
        
    # Draw health box
    draw_box(stdscr, y, x, width, height, "SYSTEM HEALTH")
    
    # Update health metrics
    update_system_health()
    
    # Format uptime
    uptime_seconds = time.time() - system_health["start_time"]
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    # Display metrics
    safe_addstr(stdscr, y + 1, x + 2, f"CPU: {system_health['cpu_usage']}%")
    safe_addstr(stdscr, y + 2, x + 2, f"Memory: {system_health['memory_usage']}%")
    safe_addstr(stdscr, y + 3, x + 2, f"Uptime: {uptime_str}")
    
    # Display avg response time if available
        if system_health["response_times"]:
        avg_time = system_health["avg_response_time"]
        safe_addstr(stdscr, y + 4, x + 2, f"Avg Response: {avg_time:.2f}s")

def draw_monolith_panel(stdscr, name, info, panel_y, width, height):
    """Draw a panel for a specific monolith"""
    # Get box style based on current theme
    box_style = BOX_CHARS[CONFIG["theme"]]
    theme = CONFIG["theme"]
    
    # Get vote information
    vote_info = get_vote_info(info['vote_path'])
    vote_str = vote_info.get('vote', 'PENDING')
    
    # Select vote color
    vote_color = VOTE_COLORS.get(vote_str, VOTE_COLORS["PENDING"])
    
    # Calculate box width
    box_width = min(width - 4, 76)
    
    # Draw styled box
    draw_box(stdscr, panel_y, 2, box_width, 8)
    
    # Style-specific divider
    divider = f"{box_style['vertical']}{box_style['horizontal'] * (box_width-2)}{box_style['vertical']}"
    safe_addstr(stdscr, panel_y+2, 2, divider)
    
    # Draw monolith header based on style
if theme == "military":
        header = f" [{info['symbol']}] {name.upper()} MONOLITH "
        elif theme == "wh40k":
        header = f" [{info['symbol']}] LEXMECHANIC {name.upper()} "
        elif theme == "tars":
        header = f" {name.upper()}.NODE "
        elif theme == "helldivers":
        header = f" [{info['symbol']}] {name.upper()} STRATAGEM "
        
    safe_addstr(stdscr, panel_y+1, 4, header, 
             curses.A_BOLD | curses.color_pair(info['color_pair']))
    
    # Display status indicators
    status = info["status"]
    status_text, status_color = STATUS_INDICATORS[status]
    
if theme == "military":
        status_display = f"STATUS: {status_text}"
        elif theme == "wh40k":
        status_display = f"MACHINE SPIRIT: {status_text}"
        elif theme == "tars":
        status_display = f"STATUS={status_text}"
        elif theme == "helldivers":
        status_display = f"LIBERTY STATUS: {status_text}"
        
    # Ensure status text fits within available space
    max_status_pos = min(width - len(status_display) - 4, box_width - 30)
    safe_addstr(stdscr, panel_y+1, max_status_pos, 
             status_display, curses.color_pair(status_color))
    
    # Display vote with style-specific formatting
if theme == "military":
        vote_display = f"[ {vote_str} ]"
        elif theme == "wh40k":
        vote_display = f"<<< {vote_str} >>>"
        elif theme == "tars":
        vote_display = f"[{vote_str}]"
        elif theme == "helldivers":
        vote_display = f"{vote_str}"
    
    # Calculate position to ensure vote display fits within box
    vote_pos = box_width - len(vote_display) - 2
    safe_addstr(stdscr, panel_y+1, 2 + vote_pos, vote_display, 
             curses.color_pair(vote_color) | curses.A_BOLD)
    
    # Display reasoning with monolith-specific formatting
    reasoning = vote_info.get('reasoning', 'AWAITING ANALYSIS...')
    
    # Format reasoning based on monolith personality and style
    prefix = info['analysis_prefix'][theme]
    
    # Draw prefix with monolith color
    safe_addstr(stdscr, panel_y+3, 4, prefix, 
             curses.color_pair(info['color_pair']) | curses.A_BOLD)
    
    # Wrap and display reasoning
    reasoning_lines = wrap_text(reasoning, box_width - 6)
        if reasoning_lines:
        safe_addstr(stdscr, panel_y+3, 4 + len(prefix) + 1, reasoning_lines[0])
    
    # Display additional reasoning lines
    for i, line in enumerate(reasoning_lines[1:3], 1):
        if panel_y+3+i < height:
            safe_addstr(stdscr, panel_y+3+i, 4, line)
    
    # Add model status display to each monolith panel
        if panel_y+6 < height:
        model_info = MODEL_CONFIG[name]["model"]
        model_status = MODEL_STATUS[name]["status"].upper()
        model_memory = MODEL_STATUS[name]["memory_usage"]
        
if theme == "military":
            model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEM: {model_memory:.0f}MB"
        elif theme == "wh40k":
            model_str = f"COGITATOR: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        elif theme == "helldivers":
            model_str = f"STRATAGEM: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        else:
            model_str = f"MODEL={model_info} STATUS={model_status} MEM={model_memory:.0f}MB"
            
        # Color based on status
        status_color = curses.color_pair(4)  # Default green
        if model_status in ["ERROR", "SERVICE_DOWN"]:
            status_color = curses.color_pair(6)  # Red
        elif model_status in ["LOADING", "NOT_LOADED", "UNKNOWN"]:
            status_color = curses.color_pair(5)  # Yellow
            
        safe_addstr(stdscr, panel_y+6, 4, model_str, status_color)
    
    # Draw confidence meter if available
        if 'confidence' in vote_info and panel_y+7 < height:
        conf_val = vote_info['confidence'] * 100
        
if theme == "military":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'#' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "wh40k":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'+' * filled}{'-' * (meter_len - filled)}]"
        elif theme == "tars":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'=' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "helldivers":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'★' * filled}{' ' * (meter_len - filled)}]"
        
        safe_addstr(stdscr, panel_y+7, 4, conf_str)
        safe_addstr(stdscr, panel_y+7, 4 + len(conf_str) + 2, meter, 
                 curses.color_pair(vote_color))
    
    return panel_y + 10  # Return next panel position

def draw_consensus_panel(stdscr, y, width, height):
    """Draw the consensus result panel"""
    # Get all votes
    votes = {}
    for name, info in MONOLITHS.items():
        vote_path = info["vote_path"]
        if os.path.exists(vote_path):
            try:
                with open(vote_path, 'r') as f:
                    vote_data = json.load(f)
                    votes[name] = vote_data.get("vote", "PENDING")
            except:
                votes[name] = "PENDING"
    
    # Calculate consensus
    consensus = calculate_consensus(votes)
    
    # Style-specific box
    theme = CONFIG["theme"]
if theme == "military":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "wh40k":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "tars":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "helldivers":
        consensus_box_top = f"[{'=' * (min(width-6, 74))}]"
        consensus_box_bottom = f"[{'=' * (min(width-6, 74))}]"
    
    safe_addstr(stdscr, y, 2, consensus_box_top, curses.A_BOLD)
    
        if consensus:
        pass
if theme == "military":
            verdict_str = f"CONSENSUS VERDICT: {consensus}"
        elif theme == "wh40k":
            verdict_str = f"IMPERIAL DECREE: {consensus}"
        elif theme == "tars":
            verdict_str = f"CONSENSUS.VERDICT={consensus}"
        elif theme == "helldivers":
            verdict_str = f"DEMOCRATIC DECISION: {consensus}"
            
        # Set up for typing animation if verdict changed
        global verdict_animation
        if verdict_animation["full_text"] != verdict_str:
            verdict_animation["full_text"] = verdict_str
            verdict_animation["display_length"] = 0
            verdict_animation["display_text"] = ""
        
        # Update the displayed text with typing animation
        current_time = time.time()
        if current_time - verdict_animation["last_update"] > 0.05:  # Update every 50ms
        if verdict_animation["display_length"] < len(verdict_animation["full_text"]):
                verdict_animation["display_length"] += 1
                verdict_animation["display_text"] = verdict_animation["full_text"][:verdict_animation["display_length"]]
                verdict_animation["last_update"] = current_time
        
        verdict_color = VOTE_COLORS[consensus]
        
        # Center the verdict text - but only display the current animation frame
        safe_addstr(stdscr, y+1, width//2 - len(verdict_animation["full_text"])//2, 
                 verdict_animation["display_text"], curses.color_pair(verdict_color) | curses.A_BOLD)
        
        # Style-specific warning/confirmation for critical mode
        if CONFIG["system_mode"] == "CRITICAL" and consensus == "APPROVE" and y+2 < height:
if theme == "military":
                warn_str = "!!! WARNING: CRITICAL ACTION REQUIRES VERIFICATION !!!"
        elif theme == "wh40k":
                warn_str = "!!! BY THE EMPEROR'S WILL: VERIFICATION REQUIRED !!!"
        elif theme == "tars":
                warn_str = "!!! CRITICAL.OVERRIDE.VERIFICATION.REQUIRED !!!"
        elif theme == "helldivers":
                warn_str = "!!! FOR DEMOCRACY: VERIFICATION REQUIRED !!!"
                
            safe_addstr(stdscr, y+2, width//2 - len(warn_str)//2, warn_str, 
                     curses.color_pair(8) | curses.A_BOLD)
        elif consensus == "APPROVE" and y+2 < height:
if theme == "military":
                confirm_str = ">>> ACTION AUTHORIZED <<<"
        elif theme == "wh40k":
                confirm_str = ">>> THE EMPEROR APPROVES <<<"
        elif theme == "tars":
                confirm_str = ">>> EXECUTION.AUTHORIZED <<<"
        elif theme == "helldivers":
                confirm_str = ">>> LIBERTY DELIVERED <<<"
                
            safe_addstr(stdscr, y+2, width//2 - len(confirm_str)//2, confirm_str, 
                     curses.color_pair(9) | curses.A_BOLD)
        else:
        pass
if theme == "military":
            wait_str = "AWAITING CONSENSUS..."
        elif theme == "wh40k":
            wait_str = "THE COUNCIL DELIBERATES..."
        elif theme == "tars":
            wait_str = "CONSENSUS.PENDING..."
        elif theme == "helldivers":
            wait_str = "DEMOCRACY IN PROGRESS..."
            
        # Reset verdict animation state if no consensus
        verdict_animation["full_text"] = ""
        verdict_animation["display_text"] = ""
        verdict_animation["display_length"] = 0
        
        safe_addstr(stdscr, y+1, width//2 - len(wait_str)//2, wait_str, 
                 curses.A_BOLD)
    
    safe_addstr(stdscr, y+3, 2, consensus_box_bottom, curses.A_BOLD)
    
    return y + 4  # Return next panel position

def draw_help_screen(stdscr, height, width, theme):
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
    
    draw_box(stdscr, help_y, help_x, help_width, help_height, "HELP: KEYBOARD SHORTCUTS & COMMANDS")
    
    # Get current help page
    global help_page
    
    # Show help content
    current_y = help_y + 2
    
    # Title
if theme == "military":
        title = "CONSENSUS SYSTEM - COMMAND REFERENCE"
        elif theme == "wh40k":
        title = "ADEPTUS MECHANICUS - COMMAND PROTOCOLS"
        elif theme == "tars":
        title = "CONSENSUS.OS - COMMAND.LIST"
        elif theme == "helldivers":
        title = "SUPER EARTH COMMAND MANUAL"
    
    safe_addstr(stdscr, current_y, help_x + (help_width - len(title)) // 2, title, curses.A_BOLD)
    current_y += 2
    
        if help_page == 1:
        pass
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
            "1 - Toggle Rationalis monolith view",
            "2 - Toggle Aeternum monolith view",
            "3 - Toggle Bellator monolith view",
            "4 - Toggle Arbiter monolith view",
            "TAB - Autocomplete commands (in input mode)",
            "ESC - Cancel command (in input mode)",
            "UP/DOWN - Navigate command history"
        ]
        
        for shortcut in shortcuts:
            safe_addstr(stdscr, current_y, help_x + 4, shortcut)
            current_y += 1
        
        current_y += 1
        
        # Command Categories - Page 1
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
                "history - Show decision history",
                "reload - Simulate system reload"
            ]
        }
        else:
        pass
        command_categories = {
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
            "MONOLITH ACCESS:": [
                "1/rationalis - Access Rationalis monolith view",
                "2/aeternum - Access Aeternum monolith view",
                "3/bellator - Access Bellator monolith view",
                "4/arbiter - Access Arbiter system view"
            ],
        }
    
    # Display command categories
    for category, commands in command_categories.items():
        safe_addstr(stdscr, current_y, help_x + 2, category, curses.A_BOLD)
        current_y += 1
        
        for cmd in commands:
            safe_addstr(stdscr, current_y, help_x + 4, cmd)
            current_y += 1
        
        current_y += 1
    
    # Page indicator
    page_text = f"Page {help_page}/2 (Press SPACE for next page)"
    safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(page_text)) // 2, 
               page_text, curses.A_BOLD)
    
    # Footer
    footer = "Press 'H' or any key to return to main view"
    safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(footer)) // 2, 
               footer, curses.A_BOLD)

def draw_history_screen(stdscr, h, w, theme):
    """Draw the decision history screen"""
    # Create a history overlay
    history_height = h - 6
    history_width = w - 6
    history_y = 3
    history_x = 3
    
    # Clear screen and draw history box
    for i in range(history_y, history_y + history_height):
        blank_line = " " * history_width
        safe_addstr(stdscr, i, history_x, blank_line)
    
    draw_box(stdscr, history_y, history_x, history_width, history_height, "DECISION HISTORY")
    
    # Title
if theme == "military":
        title = "CONSENSUS DECISION LOG"
        elif theme == "wh40k":
        title = "IMPERIAL DECREE REGISTRY"
        elif theme == "tars":
        title = "DECISION.HISTORY.LOG"
        elif theme == "helldivers":
        title = "DEMOCRATIC DECISIONS ARCHIVE"
    
    safe_addstr(stdscr, history_y + 2, history_x + (history_width - len(title)) // 2, title, curses.A_BOLD)
    
    # Display decision history
    current_y = history_y + 4
    
        if not decision_history:
        message = "No decisions recorded yet."
        safe_addstr(stdscr, current_y, history_x + (history_width - len(message)) // 2, message)
        else:
        pass
        headers = ["TIMESTAMP", "QUERY", "VERDICT"]
        header_widths = [20, history_width - 32, 10]
        header_x = [history_x + 2]
        for i in range(1, len(headers)):
            header_x.append(header_x[i-1] + header_widths[i-1] + 2)
        
        for i, header in enumerate(headers):
            safe_addstr(stdscr, current_y, header_x[i], header, curses.A_BOLD)
            
        # Separator
        safe_addstr(stdscr, current_y + 1, history_x + 2, "-" * (history_width - 4))
        current_y += 2
        
        # Entries (most recent first)
        for i, decision in enumerate(reversed(list(decision_history))):
        if current_y + i >= history_y + history_height - 2:
                break
                
            # Format timestamp
            timestamp = decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            safe_addstr(stdscr, current_y + i, header_x[0], timestamp)
            
            # Format query (truncate if needed)
            query = decision["query"]
        if len(query) > header_widths[1] - 3:
                query = query[:header_widths[1] - 6] + "..."
            safe_addstr(stdscr, current_y + i, header_x[1], query)
            
            # Format verdict with color
            verdict = decision["verdict"]
            verdict_color = VOTE_COLORS.get(verdict, 7)
            safe_addstr(stdscr, current_y + i, header_x[2], verdict, curses.color_pair(verdict_color) | curses.A_BOLD)
    
    # Footer
    footer = "Press 'D' to return to main view"
    safe_addstr(stdscr, history_y + history_height - 2, history_x + (history_width - len(footer)) // 2, 
               footer, curses.A_BOLD)

def draw_config_screen(stdscr, h, w, theme):
    """Draw the configuration screen"""
    # Create a config overlay
    config_height = h - 6
    config_width = w - 6
    config_y = 3
    config_x = 3
    
    # Clear screen and draw config box
    for i in range(config_y, config_y + config_height):
        blank_line = " " * config_width
        safe_addstr(stdscr, i, config_x, blank_line)
    
    draw_box(stdscr, config_y, config_x, config_width, config_height, "SYSTEM CONFIGURATION")
    
    # Title
if theme == "military":
        title = "CONSENSUS SYSTEM CONFIGURATION"
        elif theme == "wh40k":
        title = "MECHANICUS COGITATION PARAMETERS"
        elif theme == "tars":
        title = "SYSTEM.CONFIGURATION"
        elif theme == "helldivers":
        title = "SUPER EARTH COMMAND SETTINGS"
    
    safe_addstr(stdscr, config_y + 2, config_x + (config_width - len(title)) // 2, title, curses.A_BOLD)
    
    # Display configuration sections
    current_y = config_y + 4
    
    # System Settings
    safe_addstr(stdscr, current_y, config_x + 4, "SYSTEM SETTINGS:", curses.A_BOLD)
    current_y += 2
    
    safe_addstr(stdscr, current_y, config_x + 6, f"System Mode: {CONFIG['system_mode']}", 
               curses.color_pair(5 if CONFIG['system_mode'] == 'CRITICAL' else 7))
    current_y += 1
    
    safe_addstr(stdscr, current_y, config_x + 6, f"UI Theme: {CONFIG['theme'].upper()}")
    current_y += 1
    
    safe_addstr(stdscr, current_y, config_x + 6, f"Color Scheme: {CONFIG['color_scheme'].upper()}")
    current_y += 2
    
    # LLM Provider Settings
    safe_addstr(stdscr, current_y, config_x + 4, "LLM PROVIDER SETTINGS:", curses.A_BOLD)
    current_y += 2
    
    safe_addstr(stdscr, current_y, config_x + 6, f"Provider: {CONFIG['provider'].upper()}")
    current_y += 1
    
    api_url = PROVIDER_ENDPOINTS[CONFIG['provider']]['api_url']
    safe_addstr(stdscr, current_y, config_x + 6, f"API URL: {api_url}")
    current_y += 2
    
    # Monolith Model Settings
    safe_addstr(stdscr, current_y, config_x + 4, "MONOLITH MODEL SETTINGS:", curses.A_BOLD)
    current_y += 2
    
    for name, config in MODEL_CONFIG.items():
        model_status = MODEL_STATUS[name]["status"].upper()
        status_color = 4 if model_status == "READY" else 5 if model_status == "LOADING" else 6
        
        safe_addstr(stdscr, current_y, config_x + 6, f"{name}: {config['model']}")
        safe_addstr(stdscr, current_y, config_x + 40, f"Status: {model_status}", 
                   curses.color_pair(status_color))
        current_y += 1
    
    current_y += 1
    
    # Display Features
    safe_addstr(stdscr, current_y, config_x + 4, "DISPLAY FEATURES:", curses.A_BOLD)
    current_y += 2
    
    features = [
        ("Show Status", CONFIG["show_status"]),
        ("Show Notifications", CONFIG["show_notifications"]),
        ("Show Health", CONFIG["show_health"]),
        ("Enable Autocomplete", CONFIG["enable_autocomplete"]),
        ("Animated Text", CONFIG["animated_text"])
    ]
    
    for i, (feature, enabled) in enumerate(features):
        status = "ENABLED" if enabled else "DISABLED"
        color = 4 if enabled else 6
        safe_addstr(stdscr, current_y + i, config_x + 6, f"{feature}: {status}", 
                   curses.color_pair(color))
    
    # Footer with commands
    footer = "Use commands to change settings (e.g., 'style military', 'dark', 'use ollama')"
    safe_addstr(stdscr, config_y + config_height - 2, config_x + (config_width - len(footer)) // 2, 
               footer, curses.A_BOLD)

def draw_bellator_screen(stdscr, h, w, theme):
    """Draw the Bellator monolith specialized screen"""
    # Clear the screen
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Bellator"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Bellator"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(3))  # Bellator color (MAGENTA)
    
    # Draw DEFCON level
    defcon = MONOLITH_DATA["Bellator"]["defcon_level"]
    defcon_color = 6 if defcon <= 2 else 5 if defcon == 3 else 4  # Red, Yellow, Green
    
if theme == "military":
        defcon_text = f"DEFENSE CONDITION: DEFCON {defcon}"
        elif theme == "wh40k":
        defcon_text = f"IMPERIUM THREAT LEVEL: VERMILLION {defcon}"
        elif theme == "tars":
        defcon_text = f"SECURITY.CONDITION={defcon}"
        elif theme == "helldivers":
        defcon_text = f"LIBERTY THREAT INDEX: {defcon}"
        
    safe_addstr(stdscr, 3, w//2 - len(defcon_text)//2, defcon_text, 
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, alert in enumerate(MONOLITH_DATA["Bellator"]["threat_alerts"]):
        if y_pos + idx < h-5:
            level_color = 4 if alert["level"] == "Low" else 5 if alert["level"] == "Moderate" or alert["level"] == "Elevated" else 6
            alert_text = f"{alert['region']}: {alert['level']} - {alert['description']}"
            safe_addstr(stdscr, y_pos + idx, 4, alert_text, curses.color_pair(level_color))
    
    y_pos += len(MONOLITH_DATA["Bellator"]["threat_alerts"]) + 1
    
    # Strategic analysis
if theme == "military":
        section_header = "[ STRATEGIC ANALYSIS ]"
        elif theme == "wh40k":
        section_header = "[ TACTICAL COGITATION ]"
        elif theme == "tars":
        section_header = "[ ANALYSIS.MATRIX ]"
        elif theme == "helldivers":
        section_header = "[ SUPER EARTH INTELLIGENCE ]"
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, analysis in enumerate(MONOLITH_DATA["Bellator"]["strategic_analysis"]):
        if y_pos + idx < h-5:
            safe_addstr(stdscr, y_pos + idx, 4, f"- {analysis}")
    
    y_pos += len(MONOLITH_DATA["Bellator"]["strategic_analysis"]) + 1
    
    # News items
if theme == "military":
        section_header = "[ INTELLIGENCE BRIEFING ]"
        elif theme == "wh40k":
        section_header = "[ ASTROPATHIC DISPATCHES ]"
        elif theme == "tars":
        section_header = "[ NEWS.FEED ]"
        elif theme == "helldivers":
        section_header = "[ DEMOCRACY BROADCASTS ]"
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    for idx, news in enumerate(MONOLITH_DATA["Bellator"]["security_news"]):
        if y_pos + idx < h-5:
            news_text = f"{news['title']} - {news['source']} ({news['time']})"
            safe_addstr(stdscr, y_pos + idx, 4, news_text)
    
    # Footer
        if MONOLITH_DATA["Bellator"]["last_updated"]:
        update_time = MONOLITH_DATA["Bellator"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '3' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_aeternum_screen(stdscr, h, w, theme):
    """Draw the Aeternum monolith specialized screen"""
    # Clear the screen
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Aeternum"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Aeternum"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(1))  # Aeternum color (CYAN)
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indices = MONOLITH_DATA["Aeternum"]["market_indices"]
    col1_x = 4
    col2_x = w // 2 + 4
    
    idx = 0
    for name, data in indices.items():
        if y_pos + idx//2 < h-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["trend"] == "up" else 6  # Green or Red
            value_str = f"{data['value']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    crypto = MONOLITH_DATA["Aeternum"]["crypto_prices"]
    idx = 0
    for name, data in crypto.items():
        if y_pos + idx//2 < h-10:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["change"] > 0 else 6  # Green or Red
            price_str = f"${data['price']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    portfolio = MONOLITH_DATA["Aeternum"]["portfolio_performance"]
    
    # Time-based performance
    perf_y = y_pos
    for period, change in [("Daily", portfolio["daily_change"]), 
                          ("Weekly", portfolio["weekly_change"]), 
                          ("Monthly", portfolio["monthly_change"]), 
                          ("Yearly", portfolio["yearly_change"])]:
        if perf_y < h-10:
            change_color = 4 if change > 0 else 6  # Green or Red
    # Removed corrupted f-string call
            safe_addstr(stdscr, perf_y, col1_x, perf_text, curses.color_pair(change_color))
            perf_y += 1
    
    # Top and worst performers
        if y_pos < h-10:
        top_text = f"Top: {', '.join(portfolio['top_performers'])}"
        worst_text = f"Worst: {', '.join(portfolio['worst_performers'])}"
        safe_addstr(stdscr, y_pos, col2_x, top_text, curses.color_pair(4))
        safe_addstr(stdscr, y_pos+1, col2_x, worst_text, curses.color_pair(6))
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indicators = MONOLITH_DATA["Aeternum"]["economic_indicators"]
    idx = 0
    for name, value in indicators.items():
        if y_pos + idx//3 < h-5:
            column = idx % 3
            x_pos = col1_x + (column * (w // 3))
            
            # Format based on indicator
        if name == "inflation" or name == "unemployment" or name == "fed_rate" or name == "treasury_10y":
        pass
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
        if MONOLITH_DATA["Aeternum"]["last_updated"]:
        update_time = MONOLITH_DATA["Aeternum"]["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
        update_text = f"Last updated: {update_time}"
        safe_addstr(stdscr, h-4, w - len(update_text) - 4, update_text, curses.color_pair(7))
    
    # Return to main view instruction
    footer = "Press '2' to return to main view"
    safe_addstr(stdscr, h-3, w//2 - len(footer)//2, footer, curses.A_BOLD)

def draw_rationalis_screen(stdscr, h, w, theme):
    """Draw the Rationalis monolith specialized screen"""
    # Clear the screen
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Rationalis"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Rationalis"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(2))  # Rationalis color (BLUE)
    
    # Draw efficiency rating
    efficiency = MONOLITH_DATA["Rationalis"]["efficiency_rating"] * 100
    efficiency_color = 4 if efficiency > 90 else 5 if efficiency > 75 else 6
    
if theme == "military":
        pass
        elif theme == "wh40k":
        pass
        elif theme == "tars":
        pass
        elif theme == "helldivers":
        pass
    safe_addstr(stdscr, 3, w//2 - len(rating_text)//2, rating_text, 
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    logs = MONOLITH_DATA["Rationalis"]["system_logs"]
    for idx, log in enumerate(logs):
        if y_pos + idx < h-12:
            level_color = 4 if log["level"] == "INFO" else 5 if log["level"] == "WARNING" else 6
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    patterns = MONOLITH_DATA["Rationalis"]["logic_patterns"]
    col1_x = 4
    col2_x = w // 2 + 4
    
    idx = 0
    for name, value in patterns.items():
        if y_pos + idx//2 < h-8 and name != "logical_fallacies_detected":
            x_pos = col1_x if idx % 2 == 0 else col2_x
            
            # Format score with color based on value
        if isinstance(value, float):
                score_color = 4 if value > 0.8 else 5 if value > 0.6 else 6
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
                 curses.color_pair(5 if patterns['logical_fallacies_detected'] < 10 else 6))
    
"""
CONSENSUS System - AI Tribunal Decision Engine

A decision-making system with three distinct monolithic AI agents:
- RATIONALIS: Logical analysis and protocol compliance
- AETERNUM: Historical pattern recognition and risk assessment
- BELLATOR: Strategic and tactical analysis

Each agent operates independently and votes on queries, with results coordinated
by the central ARBITER module.

Author: Claude AI
Date: May 2025
"""

# Try to import optional dependencies with graceful fallbacks
try:
    import psutil
except ImportError:
    psutil = None

# ASCII Art for system initialization
CONSENSUS_LOGO = """
 ██████╗ ██████╗ ███╗   ██╗███████╗███████╗███╗   ██╗███████╗██╗   ██╗███████╗
██╔════╝██╔═══██╗████╗  ██║██╔════╝██╔════╝████╗  ██║██╔════╝██║   ██║██╔════╝
██║     ██║   ██║██╔██╗ ██║███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║███████╗
██║     ██║   ██║██║╚██╗██║╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║╚════██║
╚██████╗╚██████╔╝██║ ╚████║███████║███████╗██║ ╚████║███████║╚██████╔╝███████║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚══════╝
 
  ▄████▄   ▒█████   ███▄    █   ██████ ▓█████  ███▄    █   ██████  █    ██   ██████ 
 ▒██▀ ▀█  ▒██▒  ██▒ ██ ▀█   █ ▒██    ▒ ▓█   ▀  ██ ▀█   █ ▒██    ▒  ██  ▓██▒▒██    ▒ 
 ▒▓█    ▄ ▒██░  ██▒▓██  ▀█ ██▒░ ▓██▄   ▒███   ▓██  ▀█ ██▒░ ▓██▄   ▓██  ▒██░░ ▓██▄   
 ▒▓▓▄ ▄██▒▒██   ██░▓██▒  ▐▌██▒  ▒   ██▒▒▓█  ▄ ▓██▒  ▐▌██▒  ▒   ██▒▓▓█  ░██░  ▒   ██▒
 ▒ ▓███▀ ░░ ████▓▒░▒██░   ▓██░▒██████▒▒░▒████▒▒██░   ▓██░▒██████▒▒▒▒█████▓ ▒██████▒▒
 ░ ░▒ ▒  ░░ ▒░▒░▒░ ░ ▒░   ▒ ▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░░ ▒░   ▒ ▒ ▒ ▒▓▒ ▒ ░░▒▓▒ ▒ ▒ ▒ ▒▓▒ ▒ ░
   ░  ▒     ░ ▒ ▒░ ░ ░░   ░ ▒░░ ░▒  ░ ░ ░ ░  ░░ ░░   ░ ▒░░ ░▒  ░ ░░░▒░ ░ ░ ░ ░▒  ░ ░
 ░        ░ ░ ░ ▒     ░   ░ ░ ░  ░  ░     ░      ░   ░ ░ ░  ░  ░   ░░░ ░ ░ ░  ░  ░  
 ░ ░          ░ ░           ░       ░     ░  ░         ░       ░     ░           ░  
 ░                                                                                   
 
      AI TRIBUNAL DECISION SYSTEM v1.0
"""

# Global configuration
CONFIG = {
    "system_mode": "NORMAL",  # NORMAL or CRITICAL
    "view_mode": "MAIN",      # MAIN, HELP, CONFIG, HISTORY, MONOLITH_*
    "current_query": "No active query",
    "theme": "military",      # military, wh40k, tars, helldivers
    "provider": "ollama",     # ollama or lmstudio
    "color_scheme": "dark",   # dark or light
    "show_status": True,
    "show_notifications": True,
    "show_history": True,
    "show_health": True,
    "enable_autocomplete": True,
    "animated_text": True
}

# System paths configuration
PATHS = {
    "root": "CONSENSUS_SYSTEM",
    "votes_dir": "_ARBITER/tmp_votes",
    "logs_dir": "_ARBITER/logs",
    "exports_dir": "exports"
}

# Model configuration for monoliths
MODEL_CONFIG = {
    "Rationalis": {
        "model": "deepseek-coder:33b",
        "system_prompt": "You are RATIONALIS, a logical reasoning assistant focused on organization and rational analysis.",
        "parameters": {
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024
        }
    },
    "Aeternum": {
        "model": "llama3:70b",
        "system_prompt": "You are AETERNUM, a financial and historical analysis AI focused on pattern recognition, continuity, and safety.",
        "parameters": {
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024
        }
    },
    "Bellator": {
        "model": "mixtral:8x7b",
        "system_prompt": "You are BELLATOR, a tactical and strategic analyst focused on identifying risks and security concerns.",
        "parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024
        }
    }
}

# Monolith configuration
MONOLITHS = {
    "Rationalis": {
        "symbol": "R",
        "color_pair": 2,  # BLUE (curses.COLOR_BLUE)
        "log_path": "./Rationalis/rationalis.log",
        "vote_path": "./_ARBITER/tmp_votes/rationalis_vote.json",
        "analysis_prefix": {
            "military": "LOGICAL ANALYSIS:",
            "wh40k": "++ LOGICAL COGITATION ++",
            "tars": "LOGIC.SYS:",
            "helldivers": "STRATEGIC CALCULATION:"
        },
        "status": "offline"
    },
    "Aeternum": {
        "symbol": "A",
        "color_pair": 1,  # CYAN (curses.COLOR_CYAN)
        "log_path": "./Aeternum/aeternum.log",
        "vote_path": "./_ARBITER/tmp_votes/aeternum_vote.json",
        "analysis_prefix": {
            "military": "FINANCIAL ASSESSMENT:",
            "wh40k": "++ FISCAL DIVINATION ++",
            "tars": "FINANCE.SYS:",
            "helldivers": "ECONOMIC INTELLIGENCE:"
        },
        "status": "offline"
    },
    "Bellator": {
        "symbol": "B",
        "color_pair": 3,  # MAGENTA (curses.COLOR_MAGENTA)
        "log_path": "./Bellator/bellator.log",
        "vote_path": "./_ARBITER/tmp_votes/bellator_vote.json",
        "analysis_prefix": {
            "military": "SECURITY ANALYSIS:",
            "wh40k": "++ TACTICAL ASSESSMENT ++",
            "tars": "SECURITY.SYS:",
            "helldivers": "COMBAT DIRECTIVE:"
        },
        "status": "offline"
    }
}

# System modes
SYSTEM_MODES = {
    "NORMAL": {
        "symbol": {"military": "#", "wh40k": "I", "tars": "■", "helldivers": "★"}, 
        "color_pair": 7  # WHITE
    },
    "CRITICAL": {
        "symbol": {"military": "!", "wh40k": "X", "tars": "▲", "helldivers": "⚠"}, 
        "color_pair": 5  # YELLOW
    }
}

# Vote colors
VOTE_COLORS = {
    "APPROVE": 4,  # Green
    "DENY": 6,     # Red
    "PENDING": 7   # White
}

# Box drawing characters for different themes
BOX_CHARS = {
    "military": {
        "top_left": "+",
        "top_right": "+",
        "bottom_left": "+",
        "bottom_right": "+",
        "horizontal": "=",
        "vertical": "|"
    },
    "wh40k": {
        "top_left": "/",
        "top_right": "\\",
        "bottom_left": "\\",
        "bottom_right": "/",
        "horizontal": "-",
        "vertical": "|"
    },
    "tars": {
        "top_left": "+",
        "top_right": "+",
        "bottom_left": "+",
        "bottom_right": "+",
        "horizontal": "-",
        "vertical": "|"
    },
    "helldivers": {
        "top_left": "[",
        "top_right": "]",
        "bottom_left": "[",
        "bottom_right": "]",
        "horizontal": "=",
        "vertical": "|"
    }
}

# System state
MODEL_STATUS = {
    "Rationalis": {"status": "unknown", "memory_usage": 0, "loading": False},
    "Aeternum": {"status": "unknown", "memory_usage": 0, "loading": False},
    "Bellator": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# Metrics and history tracking
system_health = {
    "cpu_usage": 0,
    "memory_usage": 0,
    "start_time": time.time(),
    "response_times": deque(maxlen=50),
    "avg_response_time": 0
}

# Store notifications with timestamp and level
notifications = deque(maxlen=10)
notification_colors = {
    "info": 7,      # White
    "success": 4,   # Green
    "warning": 5,   # Yellow
    "error": 6      # Red
}

# Command history and output
command_history = []
command_history_index = 0
command_output = ""
command_suggestions = []
current_suggestion_index = 0

# Decision history
decision_history = deque(maxlen=20)

# For verdict typing animation
verdict_animation = {
    "full_text": "",
    "display_text": "",
    "display_length": 0,
    "last_update": 0
}

# Monolith-specific data for specialized views
MONOLITH_DATA = {
    "Bellator": {
        "defcon_level": 4,
        "threat_alerts": [],
        "strategic_analysis": [],
        "security_news": [],
        "last_updated": None
    },
    "Aeternum": {
        "market_indices": {},
        "crypto_prices": {},
        "portfolio_performance": {},
        "economic_indicators": {},
        "last_updated": None
    },
    "Rationalis": {
        "system_logs": [],
        "logic_patterns": {},
        "analysis_metrics": {},
        "efficiency_rating": 0.0,
        "last_updated": None
    },
    "Arbiter": {
        "agenda": [],
        "pending_decisions": [],
        "system_status": {},
        "balance_metrics": {},
        "last_updated": None
    }
}

# Initialize help page settings
help_page = 1

def setup_directories():
    """Create required directory structure"""
    # Create base directory if it doesn't exist
    os.makedirs(PATHS["root"], exist_ok=True)
    
    # Create subdirectories for each monolith
    for monolith in MONOLITHS:
        os.makedirs(f"{PATHS['root']}/{monolith}", exist_ok=True)
    
    # Create Arbiter directories
    os.makedirs(f"{PATHS['root']}/{PATHS['votes_dir']}", exist_ok=True)
    os.makedirs(f"{PATHS['root']}/{PATHS['logs_dir']}", exist_ok=True)
    
    # Create exports directory
    os.makedirs(f"{PATHS['root']}/{PATHS['exports_dir']}", exist_ok=True)

def add_notification(message, level="info"):
    """Add a notification to the queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now(),
        "seen": False
    })

def update_system_health():
    """Update system health metrics"""
        if psutil:
        try:
            system_health["cpu_usage"] = psutil.cpu_percent()
            system_health["memory_usage"] = psutil.virtual_memory().percent
        except Exception:
            system_health["cpu_usage"] = 0
            system_health["memory_usage"] = 0
        else:
        system_health["cpu_usage"] = random.randint(10, 50)  # Simulated values
        system_health["memory_usage"] = random.randint(20, 60)
    
    # Calculate average response time
        if system_health["response_times"]:
        system_health["avg_response_time"] = sum(system_health["response_times"]) / len(system_health["response_times"])

def record_response_time(start_time):
    """Record response time for a query"""
    response_time = time.time() - start_time
    system_health["response_times"].append(response_time)
    
    # Update average
    update_system_health()
    
    return response_time

def check_model_status(name):
    """Check if a model is loaded and available in the LLM provider"""
    try:
        endpoint = PROVIDER_ENDPOINTS[CONFIG["provider"]]["status_endpoint"]
        
        response = requests.get(endpoint)
        if response.status_code == 200:
        if CONFIG["provider"] == "ollama":
                models = response.json().get("models", [])
                model_name = MODEL_CONFIG[name]["model"]
                
                for model in models:
        if model["name"] == model_name:
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
                
        elif CONFIG["provider"] == "lmstudio":
                models = response.json().get("data", [])
                model_name = MODEL_CONFIG[name]["model"].split(":")[0].lower()
                
                for model in models:
        if model_name in model["id"].lower():
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
    except:
        pass
        MODEL_STATUS[name]["status"] = "service_down"
        return False

def start_model_loading(name):
    """Start loading a model in a background thread"""
        if MODEL_STATUS[name]["loading"]:
        return
        
    MODEL_STATUS[name]["loading"] = True
    MODEL_STATUS[name]["status"] = "loading"
    
    def load_model():
        try:
            model = MODEL_CONFIG[name]["model"]
            api_url = PROVIDER_ENDPOINTS[CONFIG["provider"]]["api_url"]
            
        if CONFIG["provider"] == "ollama":
        pass
                response = requests.post(
                    api_url,
                    json={
                        "model": model,
                        "prompt": "hello",  # Simple prompt to load model
                        "stream": False
                    }
                )
                
        if response.status_code == 200:
                    MODEL_STATUS[name]["status"] = "ready"
        else:
                    MODEL_STATUS[name]["status"] = "error"
                    
        elif CONFIG["provider"] == "lmstudio":
        pass
                response = requests.post(
                    api_url,
                    json={
                        "model": model,
                        "prompt": "hello",
                        "max_tokens": 5
                    }
                )
                
        if response.status_code == 200:
                    MODEL_STATUS[name]["status"] = "ready"
        else:
                    MODEL_STATUS[name]["status"] = "error"
        except:
            MODEL_STATUS[name]["status"] = "error"
        finally:
            MODEL_STATUS[name]["loading"] = False
    
    threading.Thread(target=load_model, daemon=True).start()

def update_model_statuses():
    """Update all model statuses in a background thread"""
    while True:
        try:
        pass
            for name in MODEL_STATUS:
        if not MODEL_STATUS[name]["loading"]:
                    check_model_status(name)
                
                # Update memory usage if possible
        if psutil:
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        if (CONFIG["provider"] == "ollama" and 
                                'ollama' in proc.info['name'].lower()):
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)
                                break
        elif (CONFIG["provider"] == "lmstudio" and 
                                  'lmstudio' in proc.info['name'].lower()):
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)
                                break
                    except:
        pass
                    
            time.sleep(5)  # Check every 5 seconds
        except:
            time.sleep(10)  # Longer delay on error

def query_model(name, prompt):
    """Query a specific model and get a response"""
    try:
        config = MODEL_CONFIG[name]
        api_url = PROVIDER_ENDPOINTS[CONFIG["provider"]]["api_url"]
        
        # Check if model is ready
        if MODEL_STATUS[name]["status"] != "ready":
            return f"Error: Model {config['model']} is not ready. Status: {MODEL_STATUS[name]['status']}"
        
        # Create the full prompt with system prompt
        full_prompt = f"{config['system_prompt']}\n\nQUERY: {prompt}\n\nVOTE: "
        
        if CONFIG["provider"] == "ollama":
        pass
            response = requests.post(
                api_url,
                json={
                    "model": config["model"],
                    "prompt": full_prompt,
                    "temperature": config["parameters"]["temperature"],
                    "top_p": config["parameters"]["top_p"],
                    "max_tokens": config["parameters"]["max_tokens"],
                    "stream": False
                }
            )
            
        if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
        else:
                return f"Error: API returned status {response.status_code}"
                
        elif CONFIG["provider"] == "lmstudio":
        pass
            response = requests.post(
                api_url,
                json={
                    "model": config["model"],
                    "prompt": full_prompt,
                    "temperature": config["parameters"]["temperature"],
                    "top_p": config["parameters"]["top_p"],
                    "max_tokens": config["parameters"]["max_tokens"]
                }
            )
            
        if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
        else:
                return f"Error: API returned status {response.status_code}"
                
    except Exception as e:
        return f"Error querying model: {str(e)}"

def generate_vote(name, query):
    """Generate a vote from a specific monolith"""
    try:
        pass
        start_time = time.time()
        
        # Update monolith status
        MONOLITHS[name]["status"] = "processing"
        
        # Query the model
        response = query_model(name, query)
        
        # Parse the response to get vote decision
        response_lower = response.lower()
        
        if "approve" in response_lower or "yes" in response_lower or "accept" in response_lower:
            vote = "APPROVE"
        elif "deny" in response_lower or "no" in response_lower or "reject" in response_lower:
            vote = "DENY"
        else:
            vote = "PENDING"  # Unclear response
        
        # Create vote data
        confidence = random.uniform(0.65, 0.98)  # Simulated confidence value
        vote_data = {
            "monolith": name.lower(),
            "vote": vote,
            "reasoning": response,
            "timestamp": time.time(),
            "confidence": confidence,
            "response_time": time.time() - start_time
        }
        
        # Save vote to file
        vote_path = MONOLITHS[name]["vote_path"]
        os.makedirs(os.path.dirname(vote_path), exist_ok=True)
        
        with open(vote_path, 'w', encoding='utf-8') as f:
            json.dump(vote_data, f, indent=2)
        
        # Record response time for metrics
        record_response_time(start_time)
        
        # Update monolith status
        MONOLITHS[name]["status"] = "online"
        
        # Add notification
        add_notification(f"{name} voted: {vote}", "info")
        
        return vote_data
    except Exception as e:
        error_msg = f"Error generating vote from {name}: {str(e)}"
        add_notification(error_msg, "error")
        MONOLITHS[name]["status"] = "offline"
        
        return {
            "monolith": name.lower(),
            "vote": "PENDING",
            "reasoning": error_msg,
            "timestamp": time.time()
        }

def generate_all_votes(query):
    """Generate votes from all monoliths for the current query"""
    start_time = time.time()
        add_notification(f"Consensus generation started for: {query}", "info")
    
    threads = []
    for name in MONOLITHS:
        t = threading.Thread(target=generate_vote, args=(name, query), daemon=True)
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete (with timeout)
    for t in threads:
        t.join(timeout=30)  # Timeout after 30 seconds
    
    # Record overall response time
    response_time = time.time() - start_time
    record_response_time(response_time)
    
    # Check votes and determine consensus
    votes = {}
    for name in MONOLITHS:
        vote_path = MONOLITHS[name]["vote_path"]
        if os.path.exists(vote_path):
            try:
                with open(vote_path, 'r') as f:
                    vote_data = json.load(f)
                    votes[name] = vote_data.get("vote", "PENDING")
            except:
                votes[name] = "PENDING"
    
    consensus = calculate_consensus(votes)
        if consensus:
        add_notification(f"Consensus reached: {consensus}", "success")
        add_decision_to_history(query, consensus)
        else:
        add_notification("No consensus reached", "warning")

def export_history(format_type="json"):
    """Export decision history to a file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    exports_dir = f"{PATHS['root']}/{PATHS['exports_dir']}"
    os.makedirs(exports_dir, exist_ok=True)
    
        if format_type.lower() == "json":
        filename = f"{exports_dir}/consensus_history_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(list(decision_history), f, indent=2, default=str)
        elif format_type.lower() == "csv":
        filename = f"{exports_dir}/consensus_history_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Query", "Verdict", "Reasoning"])
            for decision in decision_history:
                writer.writerow([
                    decision["timestamp"],
                    decision["query"],
                    decision["verdict"],
                    decision["reasoning"]
                ])
        else:
        return f"Unsupported format: {format_type}"
    
    return f"History exported to {filename}"

def get_command_suggestions(partial_command):
    """Get command suggestions based on partial input"""
    commands = [
        "query", "critical", "normal", "style", "load", "use ollama", "use lmstudio",
        "status", "vote", "consensus", "help", "history", "export json", "export csv", 
        "template", "config", "notifications", "health", "dark", "light", "quit", "reload"
    ]
    
        if not partial_command:
        return []
    
    # Filter commands that start with the partial command
    return [cmd for cmd in commands if cmd.startswith(partial_command.lower())]

def get_vote_info(path):
    """Get vote information from the vote JSON file"""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                vote_data = json.load(f)
                return vote_data
    except Exception:
        pass
    return {}

def process_command(command):
    """Process a command and return output message"""
    cmd = command.lower().strip()
    
    # Command: query
        if cmd.startswith("query "):
        new_query = command[6:].strip()
        if new_query:
            CONFIG["current_query"] = new_query
        add_notification(f"Query set: {new_query}", "info")
            return f"Query set to: {new_query}"
        else:
        add_notification("Query cannot be empty", "error")
            return "Error: Query cannot be empty"
    
    # Command: mode changes
        elif cmd == "critical":
        CONFIG["system_mode"] = "CRITICAL"
        add_notification("System mode set to CRITICAL", "warning")
        return "System mode set to CRITICAL"
        elif cmd == "normal":
        CONFIG["system_mode"] = "NORMAL"
        add_notification("System mode set to NORMAL", "info")
        return "System mode set to NORMAL"
    
    # Command: style changes
        elif cmd.startswith("style "):
        style_arg = cmd[6:].strip().lower()
        if style_arg in ["military", "wh40k", "tars", "helldivers"]:
            CONFIG["theme"] = style_arg
        add_notification(f"Style set to {style_arg}", "info")
            return f"Interface style set to: {style_arg}"
        else:
        add_notification(f"Unknown style: {style_arg}", "error")
            return f"Unknown style: {style_arg}. Available styles: military, wh40k, tars, helldivers"
    
    # View mode commands
        elif cmd == "help":
        if CONFIG["view_mode"] == "HELP":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "HELP"
            return "Showing help view. Press 'H' to return to main view."
            
        elif cmd == "config":
        if CONFIG["view_mode"] == "CONFIG":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "CONFIG"
            return "Showing configuration view. Press 'C' to return to main view."
            
        elif cmd == "history":
        if CONFIG["view_mode"] == "HISTORY":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "HISTORY"
            return "Showing decision history. Press 'D' to return to main view."
    
    # LLM Provider commands
        elif cmd.startswith("load "):
        model_name = cmd[5:].strip().title()
        if model_name in MODEL_STATUS:
            start_model_loading(model_name)
        add_notification(f"Loading model for {model_name}", "info")
            return f"Loading model for {model_name}..."
        else:
        add_notification(f"Unknown monolith: {model_name}", "error")
            return f"Unknown monolith: {model_name}"
    
    # Switch LLM provider
        elif cmd == "use ollama":
        CONFIG["provider"] = "ollama"
        add_notification("Switched to Ollama LLM provider", "info")
        return "Switched to Ollama LLM provider"
        
        elif cmd == "use lmstudio":
        CONFIG["provider"] = "lmstudio"
        add_notification("Switched to LM Studio LLM provider", "info")
        return "Switched to LM Studio LLM provider"
    
        elif cmd == "status":
        status_lines = []
        for name, status in MODEL_STATUS.items():
            status_lines.append(f"{name}: {status['status'].upper()} ({status['memory_usage']:.0f} MB)")
        return "\n".join(status_lines)
    
        elif cmd.startswith("vote "):
        parts = cmd[5:].strip().split(" ", 1)
        if len(parts) != 2:
        add_notification("Invalid vote command format", "error")
            return "Usage: vote <monolith> <query>"
            
        monolith_name = parts[0].title()
        vote_query = parts[1]
        
        if monolith_name in MODEL_STATUS:
            threading.Thread(target=generate_vote, args=(monolith_name, vote_query), daemon=True).start()
        add_notification(f"Generating vote from {monolith_name}", "info")
            return f"Generating vote from {monolith_name} for: {vote_query}"
        else:
        add_notification(f"Unknown monolith: {monolith_name}", "error")
            return f"Unknown monolith: {monolith_name}"
            
        elif cmd == "consensus":
        threading.Thread(target=generate_all_votes, args=(CONFIG["current_query"],), daemon=True).start()
        add_notification(f"Generating consensus for: {CONFIG['current_query']}", "info")
        return f"Generating consensus for query: {CONFIG['current_query']}"
    
    # Template commands
        elif cmd.startswith("template "):
        parts = cmd[9:].strip().split(" ", 1)
        template_name = parts[0].lower()
        params = parts[1] if len(parts) > 1 else None
        
        result = apply_template(template_name, params)
        if result.startswith("Unknown") or result.startswith("Error"):
        add_notification(result, "error")
        else:
            CONFIG["current_query"] = result
        add_notification(f"Applied template: {template_name}", "success")
        
        return result
    
    # Export commands
        elif cmd.startswith("export "):
        format_type = cmd[7:].strip().lower()
        if format_type in ["json", "csv"]:
            result = export_history(format_type)
        add_notification(f"Exported history as {format_type}", "success")
            return result
        else:
        add_notification(f"Unsupported export format: {format_type}", "error")
            return f"Unsupported export format: {format_type}. Use 'export json' or 'export csv'."
    
    # Toggle features
        elif cmd == "notifications":
        CONFIG["show_notifications"] = not CONFIG["show_notifications"]
        state = "shown" if CONFIG["show_notifications"] else "hidden"
        return f"Notifications {state}"
    
        elif cmd == "health":
        CONFIG["show_health"] = not CONFIG["show_health"]
        state = "shown" if CONFIG["show_health"] else "hidden"
        return f"System health display {state}"
    
    # Color schemes
        elif cmd == "dark":
        CONFIG["color_scheme"] = "dark"
        add_notification("Switched to dark mode", "info")
        return "Switched to dark color scheme"
    
        elif cmd == "light":
        CONFIG["color_scheme"] = "light"
        add_notification("Switched to light mode", "info")
        return "Switched to light color scheme"
    
    # Monolith views
        elif cmd in ["monolith 1", "1", "rationalis"]:
        CONFIG["view_mode"] = "MONOLITH_RATIONALIS" if CONFIG["view_mode"] != "MONOLITH_RATIONALIS" else "MAIN"
        return f"Switched to {'Rationalis view' if CONFIG['view_mode'] == 'MONOLITH_RATIONALIS' else 'main view'}"
        
        elif cmd in ["monolith 2", "2", "aeternum"]:
        CONFIG["view_mode"] = "MONOLITH_AETERNUM" if CONFIG["view_mode"] != "MONOLITH_AETERNUM" else "MAIN"
        return f"Switched to {'Aeternum view' if CONFIG['view_mode'] == 'MONOLITH_AETERNUM' else 'main view'}"
        
        elif cmd in ["monolith 3", "3", "bellator"]:
        CONFIG["view_mode"] = "MONOLITH_BELLATOR" if CONFIG["view_mode"] != "MONOLITH_BELLATOR" else "MAIN"
        return f"Switched to {'Bellator view' if CONFIG['view_mode'] == 'MONOLITH_BELLATOR' else 'main view'}"
        
        elif cmd in ["monolith 4", "4", "arbiter"]:
        CONFIG["view_mode"] = "MONOLITH_ARBITER" if CONFIG["view_mode"] != "MONOLITH_ARBITER" else "MAIN"
        return f"Switched to {'Arbiter view' if CONFIG['view_mode'] == 'MONOLITH_ARBITER' else 'main view'}"
    
        elif cmd == "reload":
        pass
        add_notification("System reloaded", "success")
        return "CONSENSUS System reloaded"
        
    # Unknown command
        else:
        add_notification(f"Unknown command: {command}", "error")
        return f"Unknown command: {command}. Type 'help' for available commands."

# ===== FILE: consensus-system2.py =====
"""
CONSENSUS War Room - AI Tribunal Decision Engine

A decision-making system that simulates parallel AI reasoning using three distinct monolithic agents:
- RATIONALIS: Logical analysis and protocol compliance using DeepSeek Coder
- AETERNUM: Historical pattern recognition and risk assessment using Llama 3
- BELLATOR: Strategic and tactical analysis using Mixtral

# ASCII Art for system initialization
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
                                      
   *** AI TRIBUNAL DECISION SYSTEM v2.0 ***
"""

# NERV-inspired logo (simplified version that works in terminal)
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

# Monolith configuration with specific colors
MONOLITHS = {
    "Rationalis": {
        "symbol": "R",
        "color_pair": 2,  # BLUE (curses.COLOR_BLUE)
        "log_path": "./Rationalis/rationalis.log",
        "vote_path": "./_ARBITER/tmp_votes/rationalis_vote.json",
        "analysis_prefix": {
            "military": "LOGICAL ANALYSIS:",
            "wh40k": "++ LOGICAL COGITATION ++",
            "tars": "LOGIC.SYS:",
            "helldivers": "STRATEGIC CALCULATION:"
        },
        "status": "offline"
    },
    "Aeternum": {
        "symbol": "A",
        "color_pair": 1,  # CYAN (curses.COLOR_CYAN)
        "log_path": "./Aeternum/aeternum.log",
        "vote_path": "./_ARBITER/tmp_votes/aeternum_vote.json",
        "analysis_prefix": {
            "military": "FINANCIAL ASSESSMENT:",
            "wh40k": "++ FISCAL DIVINATION ++",
            "tars": "FINANCE.SYS:",
            "helldivers": "ECONOMIC INTELLIGENCE:"
        },
        "status": "offline"
    },
    "Bellator": {
        "symbol": "B",
        "color_pair": 3,  # MAGENTA (curses.COLOR_MAGENTA)
        "log_path": "./Bellator/bellator.log",
        "vote_path": "./_ARBITER/tmp_votes/bellator_vote.json",
        "analysis_prefix": {
            "military": "SECURITY ANALYSIS:",
            "wh40k": "++ TACTICAL ASSESSMENT ++",
            "tars": "SECURITY.SYS:",
            "helldivers": "COMBAT DIRECTIVE:"
        },
        "status": "offline"
    }
}

def draw_box(stdscr, y, x, width, height, title=None):
    """Draw a styled box with optional title"""
    theme = CONFIG["theme"]
    box_style = BOX_CHARS[theme]
    
    # Draw corners
    safe_addstr(stdscr, y, x, box_style["top_left"])
    safe_addstr(stdscr, y, x + width - 1, box_style["top_right"])
    safe_addstr(stdscr, y + height - 1, x, box_style["bottom_left"])
    safe_addstr(stdscr, y + height - 1, x + width - 1, box_style["bottom_right"])
    
    # Draw horizontal edges
    h_bar = box_style["horizontal"] * (width - 2)
    safe_addstr(stdscr, y, x + 1, h_bar)
    safe_addstr(stdscr, y + height - 1, x + 1, h_bar)
    
    # Draw vertical edges
    for i in range(1, height - 1):
        safe_addstr(stdscr, y + i, x, box_style["vertical"])
        safe_addstr(stdscr, y + i, x + width - 1, box_style["vertical"])
    
    # Add title if provided
        if title:
        title_x = x + (width - len(title)) // 2
        safe_addstr(stdscr, y, title_x, f" {title} ", curses.A_BOLD)

def process_command(command):
    """Process a command and return output message"""
    global command_output
    
    cmd = command.lower().strip()
    
    # Command: query
        if cmd.startswith("query "):
        new_query = command[6:].strip()
        if new_query:
            CONFIG["current_query"] = new_query
        add_notification(f"Query set: {new_query}", "info")
            return f"Query set to: {new_query}"
        else:
        add_notification("Query cannot be empty", "error")
            return "Error: Query cannot be empty"
    
    # Command: mode changes
        elif cmd == "critical":
        CONFIG["system_mode"] = "CRITICAL"
        add_notification("System mode set to CRITICAL", "warning")
        return "System mode set to CRITICAL"
        elif cmd == "normal":
        CONFIG["system_mode"] = "NORMAL"
        add_notification("System mode set to NORMAL", "info")
        return "System mode set to NORMAL"
    
    # Command: style changes
        elif cmd.startswith("style "):
        style_arg = cmd[6:].strip().lower()
        if style_arg in ["military", "wh40k", "tars", "helldivers"]:
            CONFIG["theme"] = style_arg
        add_notification(f"Style set to {style_arg}", "info")
            return f"Interface style set to: {style_arg}"
        else:
        add_notification(f"Unknown style: {style_arg}", "error")
            return f"Unknown style: {style_arg}. Available styles: military, wh40k, tars, helldivers"
    
    # View mode commands
        elif cmd == "help":
        if CONFIG["view_mode"] == "HELP":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "HELP"
            return "Showing help view. Press 'H' to return to main view."
            
        elif cmd == "config":
        if CONFIG["view_mode"] == "CONFIG":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "CONFIG"
            return "Showing configuration view. Press 'C' to return to main view."
            
        elif cmd == "history":
        if CONFIG["view_mode"] == "HISTORY":
            CONFIG["view_mode"] = "MAIN"
            return "Returned to main view"
        else:
            CONFIG["view_mode"] = "HISTORY"
            return "Showing decision history. Press 'D' to return to main view."
    
    # LLM Provider commands
        elif cmd.startswith("load "):
        model_name = cmd[5:].strip().title()
        if model_name in MODEL_STATUS:
            start_model_loading(model_name)
        add_notification(f"Loading model for {model_name}", "info")
            return f"Loading model for {model_name}..."
        else:
        add_notification(f"Unknown monolith: {model_name}", "error")
            return f"Unknown monolith: {model_name}"
    
    # Switch LLM provider
        elif cmd == "use ollama":
        CONFIG["provider"] = "ollama"
        add_notification("Switched to Ollama LLM provider", "info")
        return "Switched to Ollama LLM provider"
        
        elif cmd == "use lmstudio":
        CONFIG["provider"] = "lmstudio"
        add_notification("Switched to LM Studio LLM provider", "info")
        return "Switched to LM Studio LLM provider"
    
        elif cmd == "status":
        status_lines = []
        for name, status in MODEL_STATUS.items():
            status_lines.append(f"{name}: {status['status'].upper()} ({status['memory_usage']:.0f} MB)")
        return "\n".join(status_lines)
    
        elif cmd.startswith("vote "):
        parts = cmd[5:].strip().split(" ", 1)
        if len(parts) != 2:
        add_notification("Invalid vote command format", "error")
            return "Usage: vote <monolith> <query>"
            
        monolith_name = parts[0].title()
        vote_query = parts[1]
        
        if monolith_name in MODEL_STATUS:
            threading.Thread(target=generate_vote, args=(monolith_name, vote_query), daemon=True).start()
        add_notification(f"Generating vote from {monolith_name}", "info")
            return f"Generating vote from {monolith_name} for: {vote_query}"
        else:
        add_notification(f"Unknown monolith: {monolith_name}", "error")
            return f"Unknown monolith: {monolith_name}"
            
        elif cmd == "consensus":
        threading.Thread(target=generate_all_votes, args=(CONFIG["current_query"],), daemon=True).start()
        add_notification(f"Generating consensus for: {CONFIG['current_query']}", "info")
        return f"Generating consensus for query: {CONFIG['current_query']}"
    
    # Template commands
        elif cmd.startswith("template "):
        parts = cmd[9:].strip().split(" ", 1)
        template_name = parts[0].lower()
        params = parts[1] if len(parts) > 1 else None
        
        result = apply_template(template_name, params)
        if result.startswith("Unknown") or result.startswith("Error"):
        add_notification(result, "error")
        else:
            CONFIG["current_query"] = result
        add_notification(f"Applied template: {template_name}", "success")
        
        return result
    
    # Export commands
        elif cmd.startswith("export "):
        format_type = cmd[7:].strip().lower()
        if format_type in ["json", "csv"]:
            result = export_history(format_type)
        add_notification(f"Exported history as {format_type}", "success")
            return result
        else:
        add_notification(f"Unsupported export format: {format_type}", "error")
            return f"Unsupported export format: {format_type}. Use 'export json' or 'export csv'."
    
    # Toggle features
        elif cmd == "notifications":
        CONFIG["show_notifications"] = not CONFIG["show_notifications"]
        state = "shown" if CONFIG["show_notifications"] else "hidden"
        return f"Notifications {state}"
    
        elif cmd == "health":
        CONFIG["show_health"] = not CONFIG["show_health"]
        state = "shown" if CONFIG["show_health"] else "hidden"
        return f"System health display {state}"
    
    # Color schemes
        elif cmd == "dark":
        CONFIG["color_scheme"] = "dark"
        add_notification("Switched to dark mode", "info")
        return "Switched to dark color scheme"
    
        elif cmd == "light":
        CONFIG["color_scheme"] = "light"
        add_notification("Switched to light mode", "info")
        return "Switched to light color scheme"
    
    # Monolith views
        elif cmd in ["monolith 1", "1", "rationalis"]:
        CONFIG["view_mode"] = "MONOLITH_RATIONALIS" if CONFIG["view_mode"] != "MONOLITH_RATIONALIS" else "MAIN"
        return f"Switched to {'Rationalis view' if CONFIG['view_mode'] == 'MONOLITH_RATIONALIS' else 'main view'}"
        
        elif cmd in ["monolith 2", "2", "aeternum"]:
        CONFIG["view_mode"] = "MONOLITH_AETERNUM" if CONFIG["view_mode"] != "MONOLITH_AETERNUM" else "MAIN"
        return f"Switched to {'Aeternum view' if CONFIG['view_mode'] == 'MONOLITH_AETERNUM' else 'main view'}"
        
        elif cmd in ["monolith 3", "3", "bellator"]:
        CONFIG["view_mode"] = "MONOLITH_BELLATOR" if CONFIG["view_mode"] != "MONOLITH_BELLATOR" else "MAIN"
        return f"Switched to {'Bellator view' if CONFIG['view_mode'] == 'MONOLITH_BELLATOR' else 'main view'}"
        
        elif cmd in ["monolith 4", "4", "arbiter"]:
        CONFIG["view_mode"] = "MONOLITH_ARBITER" if CONFIG["view_mode"] != "MONOLITH_ARBITER" else "MAIN"
        return f"Switched to {'Arbiter view' if CONFIG['view_mode'] == 'MONOLITH_ARBITER' else 'main view'}"
    
        elif cmd == "reload":
        pass
        add_notification("System reloaded", "success")
        return "CONSENSUS System reloaded"
        
    # Unknown command
        else:
        add_notification(f"Unknown command: {command}", "error")
        return f"Unknown command: {command}. Type 'help' for available commands."

def draw_monolith_panel(stdscr, name, info, panel_y, width, height):
    """Draw a panel for a specific monolith"""
    # Calculate box width
    box_width = min(width - 4, 76)
    
    # Draw styled box
    draw_box(stdscr, panel_y, 2, box_width, 8)
    
    # Style-specific divider
    theme = CONFIG["theme"]
    box_style = BOX_CHARS[theme]
    divider = f"{box_style['vertical']}{box_style['horizontal'] * (box_width-2)}{box_style['vertical']}"
    safe_addstr(stdscr, panel_y+2, 2, divider)
    
    # Get vote information
    vote_info = get_vote_info(info['vote_path'])
    vote_str = vote_info.get('vote', 'PENDING')
    
    # Select vote color
    vote_color = VOTE_COLORS.get(vote_str, VOTE_COLORS["PENDING"])
    
    # Draw monolith header based on style
if theme == "military":
        header = f" [{info['symbol']}] {name.upper()} MONOLITH "
        elif theme == "wh40k":
        header = f" [{info['symbol']}] LEXMECHANIC {name.upper()} "
        elif theme == "tars":
        header = f" {name.upper()}.NODE "
        elif theme == "helldivers":
        header = f" [{info['symbol']}] {name.upper()} STRATAGEM "
        
    safe_addstr(stdscr, panel_y+1, 4, header, 
             curses.A_BOLD | curses.color_pair(info['color_pair']))
    
    # Display status indicators
    status = info["status"]
    status_text, status_color = STATUS_INDICATORS[status]
    
if theme == "military":
        status_display = f"STATUS: {status_text}"
        elif theme == "wh40k":
        status_display = f"MACHINE SPIRIT: {status_text}"
        elif theme == "tars":
        status_display = f"STATUS={status_text}"
        elif theme == "helldivers":
        status_display = f"LIBERTY STATUS: {status_text}"
        
    # Ensure status text fits within available space
    max_status_pos = min(width - len(status_display) - 4, box_width - 30)
    safe_addstr(stdscr, panel_y+1, max_status_pos, 
             status_display, curses.color_pair(status_color))
    
    # Display vote with style-specific formatting
if theme == "military":
        vote_display = f"[ {vote_str} ]"
        elif theme == "wh40k":
        vote_display = f"<<< {vote_str} >>>"
        elif theme == "tars":
        vote_display = f"[{vote_str}]"
        elif theme == "helldivers":
        vote_display = f"{vote_str}"
    
    # Calculate position to ensure vote display fits within box
    vote_pos = box_width - len(vote_display) - 2
    safe_addstr(stdscr, panel_y+1, 2 + vote_pos, vote_display, 
             curses.color_pair(vote_color) | curses.A_BOLD)
    
    # Display reasoning with monolith-specific formatting
    reasoning = vote_info.get('reasoning', 'AWAITING ANALYSIS...')
    
    # Format reasoning based on monolith personality and style
    prefix = info['analysis_prefix'][theme]
    
    # Draw prefix with monolith color
    safe_addstr(stdscr, panel_y+3, 4, prefix, 
             curses.color_pair(info['color_pair']) | curses.A_BOLD)
    
    # Wrap and display reasoning
    reasoning_lines = wrap_text(reasoning, box_width - 6)
        if reasoning_lines:
        safe_addstr(stdscr, panel_y+3, 4 + len(prefix) + 1, reasoning_lines[0])
    
    # Display additional reasoning lines
    for i, line in enumerate(reasoning_lines[1:3], 1):
        if panel_y+3+i < height:
            safe_addstr(stdscr, panel_y+3+i, 4, line)
    
    # Add model status display to each monolith panel
        if panel_y+6 < height:
        model_info = MODEL_CONFIG[name]["model"]
        model_status = MODEL_STATUS[name]["status"].upper()
        model_memory = MODEL_STATUS[name]["memory_usage"]
        
if theme == "military":
            model_str = f"MODEL: {model_info} | STATUS: {model_status} | MEM: {model_memory:.0f}MB"
        elif theme == "wh40k":
            model_str = f"COGITATOR: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        elif theme == "helldivers":
            model_str = f"STRATAGEM: {model_info} | READINESS: {model_status} | POWER: {model_memory:.0f}MB"
        else:
            model_str = f"MODEL={model_info} STATUS={model_status} MEM={model_memory:.0f}MB"
            
        # Color based on status
        status_color = curses.color_pair(4)  # Default green
        if model_status in ["ERROR", "SERVICE_DOWN"]:
            status_color = curses.color_pair(6)  # Red
        elif model_status in ["LOADING", "NOT_LOADED", "UNKNOWN"]:
            status_color = curses.color_pair(5)  # Yellow
            
        safe_addstr(stdscr, panel_y+6, 4, model_str, status_color)
    
    # Draw confidence meter if available
        if 'confidence' in vote_info and panel_y+7 < height:
        conf_val = vote_info['confidence'] * 100
        
if theme == "military":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'#' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "wh40k":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'+' * filled}{'-' * (meter_len - filled)}]"
        elif theme == "tars":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'=' * filled}{' ' * (meter_len - filled)}]"
        elif theme == "helldivers":
        pass
            meter_len = 20
            filled = int((conf_val/100) * meter_len)
            meter = f"[{'★' * filled}{' ' * (meter_len - filled)}]"
        
        safe_addstr(stdscr, panel_y+7, 4, conf_str)
        safe_addstr(stdscr, panel_y+7, 4 + len(conf_str) + 2, meter, 
                 curses.color_pair(vote_color))
    
    return panel_y + 10  # Return next panel position

def draw_consensus_panel(stdscr, y, width, height):
    """Draw the consensus result panel"""
    # Get all votes
    votes = {}
    for name, info in MONOLITHS.items():
        vote_path = info["vote_path"]
        if os.path.exists(vote_path):
            try:
                with open(vote_path, 'r') as f:
                    vote_data = json.load(f)
                    votes[name] = vote_data.get("vote", "PENDING")
            except:
                votes[name] = "PENDING"
    
    # Calculate consensus
    consensus = calculate_consensus(votes)
    
    # Style-specific box
    theme = CONFIG["theme"]
if theme == "military":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "wh40k":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "tars":
        consensus_box_top = f"+{'=' * (min(width-6, 74))}+"
        consensus_box_bottom = f"+{'=' * (min(width-6, 74))}+"
        elif theme == "helldivers":
        consensus_box_top = f"[{'=' * (min(width-6, 74))}]"
        consensus_box_bottom = f"[{'=' * (min(width-6, 74))}]"
    
    safe_addstr(stdscr, y, 2, consensus_box_top, curses.A_BOLD)
    
        if consensus:
        pass
if theme == "military":
            verdict_str = f"CONSENSUS VERDICT: {consensus}"
        elif theme == "wh40k":
            verdict_str = f"IMPERIAL DECREE: {consensus}"
        elif theme == "tars":
            verdict_str = f"CONSENSUS.VERDICT={consensus}"
        elif theme == "helldivers":
            verdict_str = f"DEMOCRATIC DECISION: {consensus}"
            
        # Set up for typing animation if verdict changed
        if verdict_animation["full_text"] != verdict_str:
            verdict_animation["full_text"] = verdict_str
            verdict_animation["display_length"] = 0
            verdict_animation["display_text"] = ""
        
        # Update the displayed text with typing animation
        current_time = time.time()
        if current_time - verdict_animation["last_update"] > 0.05:  # Update every 50ms
        if verdict_animation["display_length"] < len(verdict_animation["full_text"]):
                verdict_animation["display_length"] += 1
                verdict_animation["display_text"] = verdict_animation["full_text"][:verdict_animation["display_length"]]
                verdict_animation["last_update"] = current_time
        
        verdict_color = VOTE_COLORS[consensus]
        
        # Center the verdict text - but only display the current animation frame
        safe_addstr(stdscr, y+1, width//2 - len(verdict_animation["full_text"])//2, 
                 verdict_animation["display_text"], curses.color_pair(verdict_color) | curses.A_BOLD)
        
        # Style-specific warning/confirmation for critical mode
        if CONFIG["system_mode"] == "CRITICAL" and consensus == "APPROVE" and y+2 < height:
if theme == "military":
                warn_str = "!!! WARNING: CRITICAL ACTION REQUIRES VERIFICATION !!!"
        elif theme == "wh40k":
                warn_str = "!!! BY THE EMPEROR'S WILL: VERIFICATION REQUIRED !!!"
        elif theme == "tars":
                warn_str = "!!! CRITICAL.OVERRIDE.VERIFICATION.REQUIRED !!!"
        elif theme == "helldivers":
                warn_str = "!!! FOR DEMOCRACY: VERIFICATION REQUIRED !!!"
                
            safe_addstr(stdscr, y+2, width//2 - len(warn_str)//2, warn_str, 
                     curses.color_pair(8) | curses.A_BOLD)
        elif consensus == "APPROVE" and y+2 < height:
if theme == "military":
                confirm_str = ">>> ACTION AUTHORIZED <<<"
        elif theme == "wh40k":
                confirm_str = ">>> THE EMPEROR APPROVES <<<"
        elif theme == "tars":
                confirm_str = ">>> EXECUTION.AUTHORIZED <<<"
        elif theme == "helldivers":
                confirm_str = ">>> LIBERTY DELIVERED <<<"
                
            safe_addstr(stdscr, y+2, width//2 - len(confirm_str)//2, confirm_str, 
                     curses.color_pair(9) | curses.A_BOLD)
        else:
        pass
if theme == "military":
            wait_str = "AWAITING CONSENSUS..."
        elif theme == "wh40k":
            wait_str = "THE COUNCIL DELIBERATES..."
        elif theme == "tars":
            wait_str = "CONSENSUS.PENDING..."
        elif theme == "helldivers":
            wait_str = "DEMOCRACY IN PROGRESS..."
            
        # Reset verdict animation state if no consensus
        verdict_animation["full_text"] = ""
        verdict_animation["display_text"] = ""
        verdict_animation["display_length"] = 0
        
        safe_addstr(stdscr, y+1, width//2 - len(wait_str)//2, wait_str, 
                 curses.A_BOLD)
    
    safe_addstr(stdscr, y+3, 2, consensus_box_bottom, curses.A_BOLD)
    
    return y + 4  # Return next panel position

def draw_aeternum_screen(stdscr, h, w, theme):
    """Draw the Aeternum monolith specialized screen"""
    # Clear the screen
    for i in range(1, h-3):
        blank_line = " " * (w-2)
        safe_addstr(stdscr, i, 1, blank_line)
    
    # Update data if needed
        if not MONOLITH_DATA["Aeternum"]["last_updated"] or \
       (datetime.datetime.now() - MONOLITH_DATA["Aeternum"]["last_updated"]).total_seconds() > 60:
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
        
    # Draw header with monolith color
    safe_addstr(stdscr, 1, w//2 - len(header)//2, header, 
             curses.A_BOLD | curses.color_pair(1))  # Aeternum color (CYAN)
    
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    indices = MONOLITH_DATA["Aeternum"]["market_indices"]
    col1_x = 4
    col2_x = w // 2 + 4
    
    idx = 0
    for name, data in indices.items():
        if y_pos + idx//2 < h-5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["trend"] == "up" else 6  # Green or Red
            value_str = f"{data['value']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    crypto = MONOLITH_DATA["Aeternum"]["crypto_prices"]
    idx = 0
    for name, data in crypto.items():
        if y_pos + idx//2 < h-10:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 4 if data["change"] > 0 else 6  # Green or Red
            price_str = f"${data['price']:,.2f}"
    # Removed corrupted f-string call
            
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
        
    safe_addstr(stdscr, y_pos, w//2 - len(section_header)//2, section_header, curses.A_BOLD)
    y_pos += 1
    
    portfolio = MONOLITH_DATA["Aeternum"]["portfolio_performance"]
    
    # Time-based performance
    perf_y = y_pos
    for period, change in [("Daily", portfolio["daily_change"]), 
                          ("Weekly", portfolio["weekly_change"]), 
                          ("Monthly", portfolio["monthly_change"]), 
                          ("Yearly", portfolio["yearly_change"])]:
        if perf_y < h-10:
            change_color = 4 if change > 0 else 6  # Green or Red
    # Removed corrupted f-string call
            safe_addstr(stdscr, perf_y, col1_x, perf_text, curses.color_pair(change_color))
            perf_y += 1
    
    # Top and worst performers
        if y_pos < h-10:
        top_text = f"Top: {', '.join(portfolio['top_performers'])}"
        worst_text = f"Worst: {', '.join(portfolio['worst_performers'])}"
        safe_addstr(stdscr, y_pos, col2_x, top_text, curses.color_pair(4))
        safe_addstr(stdscr, y_pos+1, col2_x, worst_text, curses.color_pair(6))
    
    y_pos += 4
    
    # Economic indicators
if theme == "military":
        section_header = "[ ECONOMIC INDICATORS

# ================================================================================
            # Make API call
            response = self._call_api(full_prompt)
            response_time = time.time() - start_time
            
            # Parse response
            parsed_vote, confidence = self._parse_response(response)
            
            # Create vote data
            vote_data = VoteData(
                monolith=self.name,
                query=query,
                vote=parsed_vote,
                reasoning=response,
                confidence=confidence,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
            
            # Save vote
            self._save_vote(vote_data)
            
            # Update metrics
            self.total_votes += 1
            self.response_times.append(response_time)
            
            log(f"[{self.name}] Vote cast: {parsed_vote.value} (confidence: {confidence:.2f}, time: {response_time:.2f}s)", 
                LogLevel.INFO, "VOTE", session_id)
            
            return vote_data
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Vote failed: {str(e)}"
            
            log(f"[{self.name}] {error_msg}", LogLevel.ERROR, "VOTE", session_id)
            self.error_count += 1
            
            # Return error vote
            return VoteData(
                monolith=self.name,
                query=query,
                vote=VoteResult.ERROR,
                reasoning=error_msg,
                confidence=0.0,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
    
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM provider"""
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/api/generate",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        elif provider == "lmstudio":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/v1/completions",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _parse_response(self, response: str) -> Tuple[VoteResult, float]:
        """Parse LLM response to extract vote and confidence"""
        response_upper = response.upper()
        
        # Extract vote
        if "APPROVE" in response_upper:
            vote = VoteResult.APPROVE
        elif "DENY" in response_upper:
            vote = VoteResult.DENY
        elif "ABSTAIN" in response_upper:
            vote = VoteResult.ABSTAIN
        else:
            vote = VoteResult.ERROR
        
        # Calculate confidence based on response characteristics
        confidence = min(0.95, max(0.1, 
            0.7 + 0.2 * (len(response) / 500) + 
            0.1 * (response.count(".") / max(1, len(response.split())))
        ))
        
        return vote, confidence
    
    def _save_vote(self, vote_data: VoteData):
        """Save vote to file"""
        try:
            with open(self.vote_file, 'w', encoding='utf-8') as f:
                # Convert dataclass to dict for JSON serialization
                vote_dict = asdict(vote_data)
                vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                vote_dict["vote"] = vote_data.vote.value
                json.dump(vote_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"[{self.name}] Failed to save vote: {e}", LogLevel.ERROR, "VOTE")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this monolith"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return {
            "status": self.status,
            "total_votes": self.total_votes,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_votes),
            "avg_response_time": avg_response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "specialty": self.config["specialty"],
            "model": self.config["model"]
        }

# ==============================================================================
# PHASE 7: CONSENSUS ENGINE
# ==============================================================================

class ConsensusEngine:
    """Enhanced consensus calculation and analysis engine"""
    
    @staticmethod
    def calculate_consensus(votes: Dict[str, VoteData]) -> Tuple[VoteResult, float, str]:
        """Calculate consensus with confidence and reasoning"""
        vote_counts = defaultdict(int)
        total_confidence = 0.0
        total_votes = 0
        reasoning_parts = []
        
        for monolith, vote_data in votes.items():
            if vote_data.vote != VoteResult.ERROR:
                vote_counts[vote_data.vote] += 1
                total_confidence += vote_data.confidence
                total_votes += 1
                
                # Collect reasoning snippets
                reasoning_snippet = vote_data.reasoning[:100] + "..." if len(vote_data.reasoning) > 100 else vote_data.reasoning
                reasoning_parts.append(f"{monolith}: {vote_data.vote.value} - {reasoning_snippet}")
        
        # Determine consensus
        if total_votes == 0:
            return VoteResult.ERROR, 0.0, "No valid votes received"
        
        approve_count = vote_counts[VoteResult.APPROVE]
        deny_count = vote_counts[VoteResult.DENY]
        abstain_count = vote_counts[VoteResult.ABSTAIN]
        
        # Consensus logic
        if approve_count >= 2:
            consensus = VoteResult.APPROVE
        elif deny_count >= 2:
            consensus = VoteResult.DENY
        elif approve_count == deny_count == 1 and abstain_count == 1:
            # Tie-breaker: abstain
            consensus = VoteResult.ABSTAIN
        else:
            consensus = VoteResult.ERROR  # Represents deadlock
        
        # Calculate consensus confidence
        consensus_confidence = total_confidence / total_votes
        
        # Adjust confidence based on unanimity
        if vote_counts[consensus] == total_votes:
            consensus_confidence *= 1.2  # Boost for unanimity
        elif vote_counts[consensus] == 2 and total_votes == 3:
            consensus_confidence *= 1.0  # Standard majority
        else:
            consensus_confidence *= 0.8  # Reduce for weak consensus
        
        consensus_confidence = min(0.99, consensus_confidence)
        
        # Create reasoning summary
        reasoning = f"Consensus: {consensus.value} ({vote_counts[consensus]}/{total_votes} votes). " + "; ".join(reasoning_parts)
        
        return consensus, consensus_confidence, reasoning

# ==============================================================================
# PHASE 8: VOTING ORCHESTRATOR
# ==============================================================================

class VotingOrchestrator:
    """Orchestrates the voting process between monoliths"""
    
    def __init__(self):
        self.monoliths = {
            name: EnhancedMonolith(name) for name in CONFIG["monoliths"]
        }
        self.consensus_engine = ConsensusEngine()
        self.active_session = None
    
    def initiate_vote(self, query: str, context: Dict[str, Any] = None) -> Tuple[VoteResult, float, str, Dict[str, VoteData]]:
        """Initiate voting process with enhanced session management"""
        session_id = self._generate_session_id(query)
        self.active_session = session_id
        
        log(f"Initiating vote for session {session_id}: {query[:100]}...", LogLevel.INFO, "VOTE", session_id)
        
        # Update system mode
        CONFIG["system"]["system_mode"] = SystemMode.VOTING.value
        add_notification("AI Tribunal deliberation commenced", NotificationLevel.INFO)
        
        try:
            # Collect votes from all monoliths
            votes = self._collect_votes(query, session_id)
            
            # Analyze and calculate consensus
            CONFIG["system"]["system_mode"] = SystemMode.ANALYZING.value
            consensus, confidence, reasoning = self.consensus_engine.calculate_consensus(votes)
            
            # Update system mode based on result
            if consensus == VoteResult.APPROVE:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION GRANTED", NotificationLevel.SUCCESS)
            elif consensus == VoteResult.DENY:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION DENIED", NotificationLevel.WARNING)
            elif consensus == VoteResult.ABSTAIN:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("TRIBUNAL ABSTAINS", NotificationLevel.INFO)
            else:
                CONFIG["system"]["system_mode"] = SystemMode.DEADLOCK.value
                add_notification("DEADLOCK - Manual intervention required", NotificationLevel.ERROR)
            
            # Record decision
            self._record_decision(query, consensus, votes, confidence, reasoning, session_id)
            
            # Announce verdict
            self._announce_verdict(consensus, confidence)
            
            # Schedule system reset
            threading.Timer(10.0, self._reset_mode).start()
            
            log(f"Vote complete - Consensus: {consensus.value}, Confidence: {confidence:.2f}", 
                LogLevel.INFO, "VOTE", session_id)
            
            return consensus, confidence, reasoning, votes
            
        except concurrent.futures.TimeoutError:
            log(f"Vote timed out after {CONFIG['llm']['vote_timeout']}s", LogLevel.ERROR, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification("Vote timeout - System error", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, "Vote timed out", {}
            
        except Exception as e:
            log(f"Vote orchestration failed: {e}", LogLevel.ERROR, "VOTE", session_id)
            log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification(f"Vote failed: {str(e)}", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, f"Vote failed: {str(e)}", {}
    
    def _generate_session_id(self, query: str) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
        return f"{timestamp}_{query_hash}"
    
    def _collect_votes(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Collect votes from all monoliths"""
        votes = {}
        
        # Sequential vote collection for clarity
        for name, monolith in self.monoliths.items():
            try:
                vote_data = monolith.cast_vote(query, session_id)
                votes[name] = vote_data
                active_votes[name] = vote_data
                add_notification(f"{name} deliberation complete", NotificationLevel.INFO)
            except Exception as e:
                log(f"Vote collection failed for {name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        
        return votes
    
    def _record_decision(self, query: str, consensus: VoteResult, votes: Dict[str, VoteData], 
                        confidence: float, reasoning: str, session_id: str):
        """Record decision with comprehensive metadata"""
        decision_id = hashlib.md5(f"{query}{session_id}{time.time()}".encode()).hexdigest()[:12]
        
        # Capture system state
        system_state = {
            "theme": CONFIG["system"]["theme"],
            "version": VERSION,
            "build_hash": BUILD_HASH,
            "mode": CONFIG["system"]["system_mode"],
            "uptime": get_system_uptime()
        }
        
        # Create decision record
        decision = DecisionRecord(
            id=decision_id,
            query=query,
            verdict=consensus,
            individual_votes=votes,
            confidence=confidence,
            timestamp=datetime.datetime.now(),
            session_id=session_id,
            reasoning=reasoning,
            system_state=system_state,
            audit_trail=[f"Decision recorded for session {session_id}"]
        )
        
        # Add to history
        with decision_lock:
            decision_history.append(decision)
        
        # Save to persistent storage
        self._save_decision_history()
        
        log(f"Decision recorded: {consensus.value} for query '{query[:50]}...'", LogLevel.INFO, "DECISION", session_id)
    
    def _announce_verdict(self, consensus: VoteResult, confidence: float):
        """Announce verdict with TTS"""
        if not CONFIG["tts"]["enabled"] or not CONFIG["tts"]["announce_decisions"]:
            return
        
        try:
            import pyttsx3
            
            # Initialize TTS engine
            engine = pyttsx3.init()
            
            # Configure voice properties
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    if any(keyword in voice_name for keyword in ['zira', 'hazel', 'female']):
                        engine.setProperty('voice', voice.id)
                        break
            
            # Set speech parameters
            engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
            engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
            # Create announcement
            if consensus == VoteResult.APPROVE:
                announcement = f"Consensus achieved. Authorization granted with {confidence:.0%} confidence."
            elif consensus == VoteResult.DENY:
                announcement = f"Consensus achieved. Authorization denied with {confidence:.0%} confidence."
            elif consensus == VoteResult.ABSTAIN:
                announcement = f"Tribunal abstains from decision with {confidence:.0%} confidence."
            else:
                announcement = "Tribunal deadlocked. Manual intervention required."
            
            # Speak
            engine.say(announcement)
            engine.runAndWait()
            engine.stop()
            
            log(f"TTS announcement completed: {consensus.value}", LogLevel.INFO, "TTS")
            
        except ImportError:
            log("TTS failed: pyttsx3 not installed", LogLevel.WARNING, "TTS")
            system_health.tts_status = "unavailable"
        except Exception as e:
            log(f"TTS error: {e}", LogLevel.ERROR, "TTS")
            system_health.tts_status = "error"
    
    def _reset_mode(self):
        """Reset system mode after decision process"""
        CONFIG["system"]["system_mode"] = SystemMode.READY.value
        self.active_session = None
        active_votes.clear()
        log("System mode reset to READY", LogLevel.INFO, "VOTE")
    
    def _save_decision_history(self):
        """Save decision history to persistent storage"""
        try:
            # Prepare data for JSON serialization
            decisions_data = []
            for decision in decision_history:
                decision_dict = asdict(decision)
                decision_dict["timestamp"] = decision.timestamp.isoformat()
                decision_dict["verdict"] = decision.verdict.value
                
                # Convert individual votes
                votes_dict = {}
                for monolith, vote_data in decision.individual_votes.items():
                    vote_dict = asdict(vote_data)
                    vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                    vote_dict["vote"] = vote_data.vote.value
                    votes_dict[monolith] = vote_dict
                decision_dict["individual_votes"] = votes_dict
                
                decisions_data.append(decision_dict)
            
            with open(DECISION_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(decisions_data, f, indent=2, ensure_ascii=False)
            
            log("Decision history saved to persistent storage", LogLevel.INFO, "DECISION")
            
        except Exception as e:
            log(f"Failed to save decision history: {e}", LogLevel.ERROR, "DECISION")
    
    def check_all_models(self):
        """Check status of all monolith models"""
        results = {}
        
        for name, monolith in self.monoliths.items():
            status = monolith.check_model_status()
            results[name] = {
                "status": status,
                "performance": monolith.get_performance_metrics()
            }
            log(f"[{name}] Model check: {status}", LogLevel.INFO, "MONOLITH")
        
        return results

def load_decision_history():
    """Load decision history from persistent storage"""
    try:
        if DECISION_HISTORY_PATH.exists():
            with open(DECISION_HISTORY_PATH, 'r', encoding='utf-8') as f:
                stored_decisions = json.load(f)
            
            # Convert back to datetime objects and add to memory
            for stored_decision in stored_decisions[-CONFIG["system"]["max_decisions"]:]:
                stored_decision["timestamp"] = datetime.datetime.fromisoformat(stored_decision["timestamp"])
                decision_history.append(stored_decision)
            
            log(f"Loaded {len(decision_history)} decisions from history", LogLevel.INFO, "DECISION")
        
    except Exception as e:
        log(f"Failed to load decision history: {e}", LogLevel.ERROR, "DECISION")

# ==============================================================================
# PHASE 4: INTERFACE ACTIVATION
# ==============================================================================

def activate_interfaces():
    """PHASE 4: Activate user interfaces"""
    print("  → Preparing GUI interface...")
    # GUI interface preparation (curses initialization happens later)
    
    print("  → Setting up console interface...")
    # Console interface setup
    
    print("  → Configuring TTS system...")
    # TTS system check
    if CONFIG["tts"]["enabled"]:
        try:
            import pyttsx3
            print("    TTS engine available")
        except ImportError:
            print("    TTS engine not available (install pyttsx3)")
    
    print("  → Finalizing theme system...")
    # Theme system ready
    current_theme = THEME_DEFINITIONS[CONFIG["system"]["theme"]]
    print(f"    Active theme: {current_theme['name']}")
    
    print("  ✅ Interfaces activated successfully!\n")

# ==============================================================================
# PHASE 9: USER INTERFACE SYSTEM
# ==============================================================================

def safe_addstr(stdscr, y: int, x: int, text: str, attr: int = 0):
    """Safely add string to screen with boundary checking"""
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

def draw_themed_box(stdscr, y: int, x: int, height: int, width: int, theme: str = None):
    """Draw box using current theme characters"""
    if theme is None:
        theme = CONFIG["system"]["theme"]
    
    chars = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["box_chars"]
    
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

def cycle_theme():
    """Cycle to next theme in sequence"""
    themes = list(THEME_DEFINITIONS.keys())
    current_theme = CONFIG["system"]["theme"]
    current_index = themes.index(current_theme) if current_theme in themes else 0
    next_index = (current_index + 1) % len(themes)
    
    CONFIG["system"]["theme"] = themes[next_index]
    theme_info = THEME_DEFINITIONS[CONFIG["system"]["theme"]]
    
    add_notification(f"Theme: {theme_info['name']}", NotificationLevel.INFO)
    log(f"Theme changed to {CONFIG['system']['theme']}", LogLevel.INFO, "UI")
    save_system_config()

def render_main_screen(stdscr, theme: str = None):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL COMMAND CENTER"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status overview
    status_y = 3
    safe_addstr(stdscr, status_y, 2, "SYSTEM STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    mode = CONFIG["system"]["system_mode"]
    safe_addstr(stdscr, status_y + 1, 4, f"Operational Mode: {mode}", curses.color_pair(2))
    safe_addstr(stdscr, status_y + 1, 30, f"API Status: {system_health.network_status.upper()}", curses.color_pair(2))
    
    # Control instructions
    controls_y = height - 3
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

# ==============================================================================
# PHASE 5: OPERATION MODE SELECTION
# ==============================================================================

def select_operation_mode():
    """PHASE 5: Operation mode selection"""
    print("🎯 CONSENSUS SYSTEM READY FOR OPERATION")
    print("\n" + "="*80)
    print("SELECT OPERATIONAL MODE:")
    print("="*80)
    print("1. 🖥️  GUI Mode      - Full interface with real-time monitoring")
    print("2. 💻 Console Mode   - Direct command-line operation")  
    print("3. 🎮 Demo Mode      - Automated demonstration")
    print("4. 🚪 Exit System    - Terminate CONSENSUS")
    print("="*80)
    
    while True:
        choice = input("\n🎯 Select mode (1-4): ").strip()
        
        if choice == "1":
            log("Starting GUI mode", LogLevel.INFO, "MODE")
            print("\n🖥️  Launching GUI interface...")
            try:
                curses.wrapper(run_ui_loop)
            except Exception as e:
                log(f"GUI mode error: {e}", LogLevel.ERROR, "MODE")
                print(f"❌ GUI mode failed: {e}")
            break
        elif choice == "2":
            log("Starting console mode", LogLevel.INFO, "MODE")
            print("\n💻 Entering console mode...")
            run_console_mode()
            break
        elif choice == "3":
            log("Starting demo mode", LogLevel.INFO, "MODE")
            print("\n🎮 Running demonstration...")
            demo_voting_process()
            print("\n✅ Demo complete!")
            break
        elif choice == "4":
            log("User requested exit", LogLevel.INFO, "MODE")
            print("\n🚪 Terminating CONSENSUS System...")
            break
        else:
            print("❌ Invalid selection. Please choose 1-4.")

# ==============================================================================
# PHASE 10: CONSOLE MODE
# ==============================================================================

def run_console_mode():
    """Enhanced console mode with comprehensive commands"""
    print("\n" + "=" * 80)
    print("CONSENSUS SYSTEM - CONSOLE COMMAND INTERFACE")
    print("=" * 80)
    print("Available commands:")
    print("  vote <query>    - Submit query to tribunal for voting")
    print("  status          - Display system status")
    print("  help            - Show this help")
    print("  quit            - Exit console mode")
    print("=" * 80)
    
    orchestrator = VotingOrchestrator()
    
    while True:
        try:
            # Get command input
            command_input = input(f"\n[{CONFIG['system']['system_mode']}] CONSENSUS> ").strip()
            
            if not command_input:
                continue
            
            # Parse command and arguments
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            # Process commands
            if command in ["quit", "exit", "q"]:
                break
            
            elif command == "vote":
                handle_console_vote(orchestrator, args)
            
            elif command == "status":
                display_console_status(orchestrator)
            
            elif command == "help":
                display_console_help()
            
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", LogLevel.ERROR, "CONSOLE")

def handle_console_vote(orchestrator: VotingOrchestrator, query: str):
    """Handle voting command in console mode"""
    if not query:
        print("Usage: vote <your question>")
        return
    
    print(f"\n🗳️  Initiating tribunal vote on: {query}")
    print("-" * 60)
    
    # Execute vote
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"⚖️  FINAL TRIBUNAL VERDICT: {consensus.value}")
    print(f"📊 Confidence: {confidence:.0%}")
    print(f"{'='*60}")
    
    # Display individual votes
    print("\n📋 Individual Monolith Votes:")
    for name, vote_data in votes.items():
        print(f"  {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})")
    
    print(f"\n💡 Reasoning: {reasoning[:200]}...")

def display_console_status(orchestrator: VotingOrchestrator):
    """Display system status in console mode"""
    print("\n📊 SYSTEM STATUS:")
    print(f"  Version: {VERSION}")
    print(f"  Uptime: {get_system_uptime()}")
    print(f"  Total Decisions: {len(decision_history)}")
    print(f"  System Mode: {CONFIG['system']['system_mode']}")
    print(f"  API Status: {system_health.network_status}")
    
    print("\n🤖 MONOLITH STATUS:")
    model_results = orchestrator.check_all_models()
    for name, result in model_results.items():
        status = result["status"]
        print(f"  {name}: {status.upper()}")

def display_console_help():
    """Display console help"""
    print("\n📖 CONSENSUS CONSOLE HELP:")
    print("  vote <query>    - Submit query to AI tribunal for consensus decision")
    print("  status          - Show system operational status and monolith health")
    print("  help            - Show this help message")
    print("  quit            - Exit console mode")

# ==============================================================================
# PHASE 11: DEMO & TESTING FUNCTIONS
# ==============================================================================

def demo_voting_process():
    """Demo voting process with sample queries"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    log(f"Demo vote initiated: {query}", LogLevel.INFO, "DEMO")
    
    print(f"\n🎮 DEMO MODE - Running automated tribunal vote...")
    print(f"📝 Sample Query: {query}")
    print("-" * 60)
    
    # Create orchestrator and execute vote
    orchestrator = VotingOrchestrator()
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"🎯 DEMO RESULTS")
    print(f"  Query: {query}")
    print(f"  Consensus: {consensus.value}")
    print(f"  Confidence: {confidence:.0%}")
    print(f"{'='*60}")
    
    # Log results
    log(f"Demo vote complete: {consensus.value} (confidence: {confidence:.2f})", LogLevel.INFO, "DEMO")

# ==============================================================================
# PHASE 12: MAIN APPLICATION LOOP  
# ==============================================================================

def handle_input(stdscr, key: int) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
    elif key in (ord('m'), ord('M')):
        CONFIG["system"]["current_view"] = "main"
    elif key in (ord('v'), ord('V')):
        # Trigger demo voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('h'), ord('H')):
        # Show help (placeholder)
        add_notification("Help system coming soon", NotificationLevel.INFO)
    
    return True

def run_ui_loop(stdscr):
    """Main UI loop"""
    # Initialize curses
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    # Initialize color pairs
    if curses.has_colors():
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    # Special handling for console mode transition
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    # Re-initialize curses after console mode
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    if curses.has_colors():
                        for i in range(1, 8):
                            curses.init_pair(i, i, -1)
                else:
                    running = handle_input(stdscr, key)
            
            # Refresh screen periodically
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                
                # Render current screen
                theme = CONFIG["system"]["theme"]
                render_main_screen(stdscr, theme)
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"UI loop error: {e}", LogLevel.ERROR, "UI")
            add_notification(f"UI error: {str(e)}", NotificationLevel.ERROR)

# ==============================================================================
# FINAL: RUN THE SYSTEM
# ==============================================================================

if __name__ == "__main__":
    main()                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_name = self.config["model"]
                    
                    for model in models:
                        if model["name"] == model_name:
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            elif provider == "lmstudio":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/v1/models",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    model_name = self.config["model"].split(":")[0].lower()
                    
                    for model in models:
                        if model_name in model["id"].lower():
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            else:
                self.status = "unknown_provider"
                return "unknown_provider"
                
        except Exception as e:
            log(f"[{self.name}] Status check failed: {e}", LogLevel.ERROR, "MONOLITH")
            self.status = "unreachable"
            self.error_count += 1
            return "unreachable"
    
    def cast_vote(self, query: str, session_id: str) -> VoteData:
        """Cast a vote with enhanced error handling and metrics"""
        start_time = time.time()
        
        try:
            log(f"[{self.name}] Casting vote for session {session_id}", LogLevel.INFO, "VOTE", session_id)
            
            # Check model status first
            if self.status != "ready":
                status = self.check_model_status()
                if status != "ready":
                    raise Exception(f"Model not ready: {status}")
            
            # Prepare prompt
            full_prompt = f"{self.config['prompt']}\n\nQUERY: {query}\n\nVOTE:"
            
            # Make API call
            response = self._call_api(full_prompt)
            response_time = time.time() - start_time
            
            # Parse response
            parsed_vote, confidence = self._parse_response(response)
            
            # Create vote data
            vote_data = VoteData(
                monolith=self.name,
                query=query,
                vote=parsed_vote,
                reasoning=response,
                confidence=confidence,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
            
            # Save vote
            self._save_vote(vote_data)
            
            # Update metrics
            self.total_votes += 1
            self.response_times.append(response_time)
            
            log(f"[{self.name}] Vote cast: {parsed_vote.value} (confidence: {confidence:.2f}, time: {response_time:.2f}s)", 
                LogLevel.INFO, "VOTE", session_id)
            
            return vote_data
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Vote failed: {str(e)}"
            
            log(f"[{self.name}] {error_msg}", LogLevel.ERROR, "VOTE", session_id)
            self.error_count += 1
            
            # Return error vote
            return VoteData(
                monolith=self.name,
                query=query,
                vote=VoteResult.ERROR,
                reasoning=error_msg,
                confidence=0.0,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
    
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM provider"""
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/api/generate",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        elif provider == "lmstudio":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/v1/completions",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _parse_response(self, response: str) -> Tuple[VoteResult, float]:
        """Parse LLM response to extract vote and confidence"""
        response_upper = response.upper()
        
        # Extract vote
        if "APPROVE" in response_upper:
            vote = VoteResult.APPROVE
        elif "DENY" in response_upper:
            vote = VoteResult.DENY
        elif "ABSTAIN" in response_upper:
            vote = VoteResult.ABSTAIN
        else:
            vote = VoteResult.ERROR
        
        # Calculate confidence based on response characteristics
        confidence = min(0.95, max(0.1, 
            0.7 + 0.2 * (len(response) / 500) + 
            0.1 * (response.count(".") / max(1, len(response.split())))
        ))
        
        return vote, confidence
    
    def _save_vote(self, vote_data: VoteData):
        """Save vote to file"""
        try:
            with open(self.vote_file, 'w', encoding='utf-8') as f:
                # Convert dataclass to dict for JSON serialization
                vote_dict = asdict(vote_data)
                vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                vote_dict["vote"] = vote_data.vote.value
                json.dump(vote_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"[{self.name}] Failed to save vote: {e}", LogLevel.ERROR, "VOTE")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this monolith"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return {
            "status": self.status,
            "total_votes": self.total_votes,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_votes),
            "avg_response_time": avg_response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "specialty": self.config["specialty"],
            "model": self.config["model"]
        }

# ==============================================================================
# MODULE 6: CONSENSUS ENGINE
# ==============================================================================

# ==============================================================================
# MODULE 7: VOTING ORCHESTRATOR
# ==============================================================================

# ==============================================================================
# MODULE 8: USER INTERFACE SYSTEM
# ==============================================================================

# ==============================================================================
# MODULE 9: CONSOLE MODE
# ==============================================================================

# ==============================================================================
# MODULE 10: DEMO & TESTING FUNCTIONS
# ==============================================================================

# ==============================================================================
# MODULE 11: MAIN APPLICATION LOOP  
# ==============================================================================

if __name__ == "__main__":
    main()                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/api/generate",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        elif provider == "lmstudio":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/v1/completions",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _parse_response(self, response: str) -> Tuple[VoteResult, float]:
        """Parse LLM response to extract vote and confidence"""
        response_upper = response.upper()
        
        # Extract vote
        if "APPROVE" in response_upper:
            vote = VoteResult.APPROVE
        elif "DENY" in response_upper:
            vote = VoteResult.DENY
        elif "ABSTAIN" in response_upper:
            vote = VoteResult.ABSTAIN
        else:
            vote = VoteResult.ERROR
        
        # Calculate confidence based on response characteristics
        confidence = min(0.95, max(0.1, 
            0.7 + 0.2 * (len(response) / 500) + 
            0.1 * (response.count(".") / max(1, len(response.split())))
        ))
        
        return vote, confidence
    
    def _save_vote(self, vote_data: VoteData):
        """Save vote to file"""
        try:
            with open(self.vote_file, 'w', encoding='utf-8') as f:
                # Convert dataclass to dict for JSON serialization
                vote_dict = asdict(vote_data)
                vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                vote_dict["vote"] = vote_data.vote.value
                json.dump(vote_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"[{self.name}] Failed to save vote: {e}", LogLevel.ERROR, "VOTE")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this monolith"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return {
            "status": self.status,
            "total_votes": self.total_votes,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_votes),
            "avg_response_time": avg_response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "specialty": self.config["specialty"],
            "model": self.config["model"]
        }

# ==============================================================================
# MODULE 7: CONSENSUS ENGINE
# ==============================================================================

class ConsensusEngine:
    """Enhanced consensus calculation and analysis engine"""
    
    @staticmethod
    def calculate_consensus(votes: Dict[str, VoteData]) -> Tuple[VoteResult, float, str]:
        """Calculate consensus with confidence and reasoning"""
        vote_counts = defaultdict(int)
        total_confidence = 0.0
        total_votes = 0
        reasoning_parts = []
        
        for monolith, vote_data in votes.items():
            if vote_data.vote != VoteResult.ERROR:
                vote_counts[vote_data.vote] += 1
                total_confidence += vote_data.confidence
                total_votes += 1
                
                # Collect reasoning snippets
                reasoning_snippet = vote_data.reasoning[:100] + "..." if len(vote_data.reasoning) > 100 else vote_data.reasoning
                reasoning_parts.append(f"{monolith}: {vote_data.vote.value} - {reasoning_snippet}")
        
        # Determine consensus
        if total_votes == 0:
            return VoteResult.ERROR, 0.0, "No valid votes received"
        
        approve_count = vote_counts[VoteResult.APPROVE]
        deny_count = vote_counts[VoteResult.DENY]
        abstain_count = vote_counts[VoteResult.ABSTAIN]
        
        # Consensus logic
        if approve_count >= 2:
            consensus = VoteResult.APPROVE
        elif deny_count >= 2:
            consensus = VoteResult.DENY
        elif approve_count == deny_count == 1 and abstain_count == 1:
            # Tie-breaker: abstain
            consensus = VoteResult.ABSTAIN
        else:
            consensus = VoteResult.ERROR  # Represents deadlock
        
        # Calculate consensus confidence
        consensus_confidence = total_confidence / total_votes
        
        # Adjust confidence based on unanimity
        if vote_counts[consensus] == total_votes:
            consensus_confidence *= 1.2  # Boost for unanimity
        elif vote_counts[consensus] == 2 and total_votes == 3:
            consensus_confidence *= 1.0  # Standard majority
        else:
            consensus_confidence *= 0.8  # Reduce for weak consensus
        
        consensus_confidence = min(0.99, consensus_confidence)
        
        # Create reasoning summary
        reasoning = f"Consensus: {consensus.value} ({vote_counts[consensus]}/{total_votes} votes). " + "; ".join(reasoning_parts)
        
        return consensus, consensus_confidence, reasoning
    
    @staticmethod
    def analyze_voting_patterns(decisions: List[DecisionRecord]) -> Dict[str, Any]:
        """Analyze historical voting patterns"""
        if not decisions:
            return {}
        
        # Overall statistics
        total_decisions = len(decisions)
        verdict_counts = defaultdict(int)
        monolith_agreement = defaultdict(list)
        
        for decision in decisions:
            verdict_counts[decision.verdict] += 1
            
            # Track monolith agreement
            votes = [vote.vote for vote in decision.individual_votes.values() if vote.vote != VoteResult.ERROR]
            if len(votes) >= 2:
                # Check pairwise agreement
                for i, vote1 in enumerate(votes):
                    for vote2 in votes[i+1:]:
                        if vote1 == vote2:
                            monolith_agreement[vote1].append(1)
                        else:
                            monolith_agreement[vote1].append(0)
        
        # Calculate metrics
        approval_rate = verdict_counts[VoteResult.APPROVE] / total_decisions
        denial_rate = verdict_counts[VoteResult.DENY] / total_decisions
        deadlock_rate = verdict_counts[VoteResult.ERROR] / total_decisions
        
        # Average confidence
        avg_confidence = sum(d.confidence for d in decisions) / total_decisions
        
        # Response times
        all_response_times = []
        for decision in decisions:
            for vote in decision.individual_votes.values():
                all_response_times.append(vote.response_time)
        
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0.0
        
        return {
            "total_decisions": total_decisions,
            "approval_rate": approval_rate,
            "denial_rate": denial_rate,
            "deadlock_rate": deadlock_rate,
            "average_confidence": avg_confidence,
            "average_response_time": avg_response_time,
            "verdict_distribution": dict(verdict_counts),
            "recent_trend": ConsensusEngine._calculate_trend(decisions[-10:]) if len(decisions) >= 10 else "insufficient_data"
        }
    
    @staticmethod
    def _calculate_trend(recent_decisions: List[DecisionRecord]) -> str:
        """Calculate recent decision trend"""
        if len(recent_decisions) < 5:
            return "insufficient_data"
        
        approve_count = sum(1 for d in recent_decisions if d.verdict == VoteResult.APPROVE)
        deny_count = sum(1 for d in recent_decisions if d.verdict == VoteResult.DENY)
        
        approve_rate = approve_count / len(recent_decisions)
        
        if approve_rate > 0.7:
            return "approval_trending"
        elif approve_rate < 0.3:
            return "denial_trending"
        else:
            return "balanced"

# ==============================================================================
# MODULE 8: VOTING ORCHESTRATOR
# ==============================================================================

class VotingOrchestrator:
    """Orchestrates the voting process between monoliths"""
    
    def __init__(self):
        self.monoliths = {
            name: EnhancedMonolith(name) for name in CONFIG["monoliths"]
        }
        self.consensus_engine = ConsensusEngine()
        self.active_session = None
    
    def initiate_vote(self, query: str, context: Dict[str, Any] = None) -> Tuple[VoteResult, float, str, Dict[str, VoteData]]:
        """Initiate voting process with enhanced session management"""
        session_id = self._generate_session_id(query)
        self.active_session = session_id
        
        log(f"Initiating vote for session {session_id}: {query[:100]}...", LogLevel.INFO, "VOTE", session_id)
        
        # Update system mode
        CONFIG["system"]["system_mode"] = SystemMode.VOTING.value
        add_notification("AI Tribunal deliberation commenced", NotificationLevel.INFO)
        
        try:
            # Collect votes from all monoliths
            votes = self._collect_votes(query, session_id)
            
            # Analyze and calculate consensus
            CONFIG["system"]["system_mode"] = SystemMode.ANALYZING.value
            consensus, confidence, reasoning = self.consensus_engine.calculate_consensus(votes)
            
            # Update system mode based on result
            if consensus == VoteResult.APPROVE:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION GRANTED", NotificationLevel.SUCCESS)
            elif consensus == VoteResult.DENY:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION DENIED", NotificationLevel.WARNING)
            elif consensus == VoteResult.ABSTAIN:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("TRIBUNAL ABSTAINS", NotificationLevel.INFO)
            else:
                CONFIG["system"]["system_mode"] = SystemMode.DEADLOCK.value
                add_notification("DEADLOCK - Manual intervention required", NotificationLevel.ERROR)
            
            # Record decision
            self._record_decision(query, consensus, votes, confidence, reasoning, session_id)
            
            # Announce verdict
            self._announce_verdict(consensus, confidence)
            
            # Schedule system reset
            threading.Timer(10.0, self._reset_mode).start()
            
            log(f"Vote complete - Consensus: {consensus.value}, Confidence: {confidence:.2f}", 
                LogLevel.INFO, "VOTE", session_id)
            
            return consensus, confidence, reasoning, votes
            
        except concurrent.futures.TimeoutError:
            log(f"Vote timed out after {CONFIG['llm']['vote_timeout']}s", LogLevel.ERROR, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification("Vote timeout - System error", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, "Vote timed out", {}
            
        except Exception as e:
            log(f"Vote orchestration failed: {e}", LogLevel.ERROR, "VOTE", session_id)
            log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification(f"Vote failed: {str(e)}", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, f"Vote failed: {str(e)}", {}
    
    def _generate_session_id(self, query: str) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
        return f"{timestamp}_{query_hash}"
    
    def _collect_votes(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Collect votes from all monoliths"""
        votes = {}
        
        if CONFIG["llm"].get("enable_parallel_processing", True):
            # Parallel vote collection
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.monoliths)) as executor:
                future_to_monolith = {
                    executor.submit(monolith.cast_vote, query, session_id): name 
                    for name, monolith in self.monoliths.items()
                }
                
                for future in concurrent.futures.as_completed(future_to_monolith, timeout=CONFIG["llm"]["vote_timeout"]):
                    monolith_name = future_to_monolith[future]
                    try:
                        vote_data = future.result()
                        votes[monolith_name] = vote_data
                        
                        # Update active votes for UI
                        active_votes[monolith_name] = vote_data
                        
                        add_notification(f"{monolith_name} deliberation complete", NotificationLevel.INFO)
                        
                    except Exception as e:
                        log(f"Vote collection failed for {monolith_name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        else:
            # Sequential vote collection
            for name, monolith in self.monoliths.items():
                try:
                    vote_data = monolith.cast_vote(query, session_id)
                    votes[name] = vote_data
                    active_votes[name] = vote_data
                    add_notification(f"{name} deliberation complete", NotificationLevel.INFO)
                except Exception as e:
                    log(f"Sequential vote collection failed for {name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        
        return votes
    
    def _record_decision(self, query: str, consensus: VoteResult, votes: Dict[str, VoteData], 
                        confidence: float, reasoning: str, session_id: str):
        """Record decision with comprehensive metadata"""
        decision_id = hashlib.md5(f"{query}{session_id}{time.time()}".encode()).hexdigest()[:12]
        
        # Capture system state
        system_state = {
            "theme": CONFIG["system"]["theme"],
            "version": VERSION,
            "build_hash": BUILD_HASH,
            "mode": CONFIG["system"]["system_mode"],
            "uptime": get_system_uptime(),
            "health_score": self._calculate_health_score()
        }
        
        # Create decision record
        decision = DecisionRecord(
            id=decision_id,
            query=query,
            verdict=consensus,
            individual_votes=votes,
            confidence=confidence,
            timestamp=datetime.datetime.now(),
            session_id=session_id,
            reasoning=reasoning,
            system_state=system_state,
            audit_trail=[f"Decision recorded for session {session_id}"]
        )
        
        # Add to history
        with decision_lock:
            decision_history.append(decision)
        
        # Save to persistent storage
        self._save_decision_history()
        
        log(f"Decision recorded: {consensus.value} for query '{query[:50]}...'", LogLevel.INFO, "DECISION", session_id)
    
    def _announce_verdict(self, consensus: VoteResult, confidence: float):
        """Announce verdict with TTS"""
        if not CONFIG["tts"]["enabled"] or not CONFIG["tts"]["announce_decisions"]:
            return
        
        try:
            import pyttsx3
            
            # Initialize TTS engine
            engine = pyttsx3.init()
            
            # Configure voice properties
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    if any(keyword in voice_name for keyword in ['zira', 'hazel', 'female']):
                        engine.setProperty('voice', voice.id)
                        break
            
            # Set speech parameters
            engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
            engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
            # Create announcement
            if consensus == VoteResult.APPROVE:
                announcement = f"Consensus achieved. Authorization granted with {confidence:.0%} confidence."
            elif consensus == VoteResult.DENY:
                announcement = f"Consensus achieved. Authorization denied with {confidence:.0%} confidence."
            elif consensus == VoteResult.ABSTAIN:
                announcement = f"Tribunal abstains from decision with {confidence:.0%} confidence."
            else:
                announcement = "Tribunal deadlocked. Manual intervention required."
            
            # Speak
            engine.say(announcement)
            engine.runAndWait()
            engine.stop()
            
            log(f"TTS announcement completed: {consensus.value}", LogLevel.INFO, "TTS")
            
        except ImportError:
            log("TTS failed: pyttsx3 not installed", LogLevel.WARNING, "TTS")
            system_health.tts_status = "unavailable"
        except Exception as e:
            log(f"TTS error: {e}", LogLevel.ERROR, "TTS")
            system_health.tts_status = "error"
    
    def _reset_mode(self):
        """Reset system mode after decision process"""
        CONFIG["system"]["system_mode"] = SystemMode.READY.value
        self.active_session = None
        active_votes.clear()
        log("System mode reset to READY", LogLevel.INFO, "VOTE")
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score"""
        # Simple health score calculation
        score = 0.85  # Base score
        
        # Adjust based on system health
        if system_health.network_status == "operational":
            score += 0.1
        elif system_health.network_status == "degraded":
            score -= 0.05
        else:
            score -= 0.2
        
        if system_health.tts_status == "operational":
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _save_decision_history(self):
        """Save decision history to persistent storage"""
        try:
            # Prepare data for JSON serialization
            decisions_data = []
            for decision in decision_history:
                decision_dict = asdict(decision)
                decision_dict["timestamp"] = decision.timestamp.isoformat()
                decision_dict["verdict"] = decision.verdict.value
                
                # Convert individual votes
                votes_dict = {}
                for monolith, vote_data in decision.individual_votes.items():
                    vote_dict = asdict(vote_data)
                    vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                    vote_dict["vote"] = vote_data.vote.value
                    votes_dict[monolith] = vote_dict
                decision_dict["individual_votes"] = votes_dict
                
                decisions_data.append(decision_dict)
            
            with open(DECISION_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(decisions_data, f, indent=2, ensure_ascii=False)
            
            log("Decision history saved to persistent storage", LogLevel.INFO, "DECISION")
            
        except Exception as e:
            log(f"Failed to save decision history: {e}", LogLevel.ERROR, "DECISION")
    
    def check_all_models(self):
        """Check status of all monolith models"""
        results = {}
        
        for name, monolith in self.monoliths.items():
            status = monolith.check_model_status()
            results[name] = {
                "status": status,
                "performance": monolith.get_performance_metrics()
            }
            log(f"[{name}] Model check: {status}", LogLevel.INFO, "MONOLITH")
        
        return results

# ==============================================================================
# MODULE 9: USER INTERFACE SYSTEM
# ==============================================================================

def render_main_screen(stdscr, theme: str = None):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL COMMAND CENTER"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status overview
    status_y = 3
    safe_addstr(stdscr, status_y, 2, "SYSTEM STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    mode = CONFIG["system"]["system_mode"]
    safe_addstr(stdscr, status_y + 1, 4, f"Operational Mode: {mode}", curses.color_pair(2))
    safe_addstr(stdscr, status_y + 1, 30, f"Health Score: 85%", curses.color_pair(2))  # Placeholder
    safe_addstr(stdscr, status_y + 1, 50, f"API Status: {system_health.network_status.upper()}", curses.color_pair(2))
    
    # Monolith status section
    mono_y = status_y + 3
    safe_addstr(stdscr, mono_y, 2, "MONOLITH STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    # Display recent decisions
    if decision_history:
        decisions_y = mono_y + 6
        safe_addstr(stdscr, decisions_y, 2, "RECENT DECISIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_decisions = list(decision_history)[-5:]  # Show last 5
        for i, decision in enumerate(recent_decisions):
            y_pos = decisions_y + 1 + i
            
            # Timestamp
            timestamp = decision["timestamp"].strftime("%H:%M") if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"][:5]
            safe_addstr(stdscr, y_pos, 4, f"[{timestamp}]", curses.color_pair(7))
            
            # Consensus with color
            consensus = decision["verdict"]
            if consensus == "APPROVE":
                consensus_color = 2
            elif consensus == "DENY":
                consensus_color = 1
            else:
                consensus_color = 3
            
            safe_addstr(stdscr, y_pos, 12, consensus, curses.A_BOLD | curses.color_pair(consensus_color))
            
            # Query preview
            query_preview = decision["query"][:40] + "..." if len(decision["query"]) > 40 else decision["query"]
            safe_addstr(stdscr, y_pos, 22, query_preview, curses.color_pair(7))
    
    # Notifications section
    cleanup_expired_notifications()
    if notifications:
        notif_y = height - 8
        safe_addstr(stdscr, notif_y, 2, "NOTIFICATIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_notifications = list(notifications)[-4:]  # Show last 4
        for i, notif in enumerate(recent_notifications):
            y_pos = notif_y + 1 + i
            
            # Color based on level
            color_map = {"success": 2, "error": 1, "warning": 3, "info": 7}
            color = color_map.get(notif["level"], 7)
            
            # Format notification
            timestamp = notif["timestamp"].strftime("%H:%M")
            notif_text = f"[{timestamp}] {notif['message']}"
            safe_addstr(stdscr, y_pos, 4, notif_text, curses.color_pair(color))
    
    # Control instructions
    controls_y = height - 3
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

# ==============================================================================
# MODULE 10: CONSOLE MODE
# ==============================================================================

def run_console_mode():
    """Enhanced console mode with comprehensive commands"""
    print(f"\nInitiating tribunal vote on: {query}")
    print("-" * 60)
    
    # Execute vote
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"FINAL TRIBUNAL VERDICT: {consensus.value}")
    print(f"Confidence: {confidence:.0%}")
    print(f"{'='*60}")
    
    # Display individual votes
    print("\nIndividual Monolith Votes:")
    for name, vote_data in votes.items():
        print(f"  {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})")
    
    print(f"\nReasoning: {reasoning}")

def display_console_status(orchestrator: VotingOrchestrator):
    """Display system status in console mode"""
    print("\nSYSTEM STATUS:")
    print(f"  Version: {VERSION}")
    print(f"  Uptime: {get_system_uptime()}")
    print(f"  Total Decisions: {len(decision_history)}")
    print(f"  System Mode: {CONFIG['system']['system_mode']}")
    print(f"  API Status: {system_health.network_status}")
    print(f"  TTS Status: {system_health.tts_status}")
    
    print("\nMONOLITH STATUS:")
    model_results = orchestrator.check_all_models()
    for name, result in model_results.items():
        status = result["status"]
        performance = result["performance"]
        print(f"  {name}: {status.upper()} (votes: {performance['total_votes']}, errors: {performance['error_count']})")

def display_health_metrics():
    """Display detailed health metrics"""
    print("\nSYSTEM HEALTH METRICS:")
    print(f"  CPU Usage: {system_health.cpu_usage:.1f}%")
    print(f"  Memory Usage: {system_health.memory_usage:.1f}%")
    print(f"  Disk Usage: {system_health.disk_usage:.1f}%")
    print(f"  API Response Time: {system_health.api_response_time:.2f}s")
    print(f"  Network Status: {system_health.network_status}")
    print(f"  TTS Status: {system_health.tts_status}")
    print(f"  Error Count: {system_health.error_count}")
    print(f"  Last Health Check: {system_health.last_check.strftime('%H:%M:%S')}")

def display_decision_history(args: str):
    """Display decision history"""
    try:
        count = int(args) if args else 10
        count = min(count, len(decision_history))
    except ValueError:
        count = 10
    
    print(f"\nLAST {count} DECISIONS:")
    print("-" * 80)
    
    recent_decisions = list(decision_history)[-count:]
    for i, decision in enumerate(recent_decisions, 1):
        timestamp = decision["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.datetime.fromisoformat(timestamp)
        
        print(f"{i}. [{timestamp.strftime('%m/%d %H:%M')}] {decision['verdict']} - {decision['query'][:50]}...")
        if decision.get("individual_votes"):
            votes_summary = ", ".join([f"{name}: {vote['vote']}" for name, vote in decision["individual_votes"].items()])
            print(f"   Votes: {votes_summary}")
        print()

def handle_console_export(args: str):
    """Handle export command"""
    if not args or args.lower() not in ["json", "csv", "txt"]:
        print("Usage: export <json|csv|txt>")
        return
    
    try:
        filename = export_decisions(args.lower())
        print(f"Decisions exported to: {filename}")
    except Exception as e:
        print(f"Export failed: {e}")
        log(f"Export failed: {e}", LogLevel.ERROR, "CONSOLE")

def display_configuration():
    """Display current configuration"""
    print("\nSYSTEM CONFIGURATION:")
    print(f"  Theme: {CONFIG['system']['theme']}")
    print(f"  LLM Provider: {CONFIG['llm']['provider']}")
    print(f"  Base URL: {CONFIG['llm']['base_url']}")
    print(f"  Vote Timeout: {CONFIG['llm']['vote_timeout']}s")
    print(f"  TTS Enabled: {CONFIG['tts']['enabled']}")
    print(f"  Health Monitoring: {CONFIG['health']['enabled']}")
    
    print("\nMONOLITH MODELS:")
    for name, config in CONFIG["monoliths"].items():
        print(f"  {name}: {config['model']} (specialty: {config['specialty']})")

def handle_theme_change(args: str):
    """Handle theme change command"""
    themes = list(THEME_DEFINITIONS.keys())
    
    if not args:
        print("Available themes:")
        for i, theme in enumerate(themes):
            print(f"  {i}: {theme} - {THEME_DEFINITIONS[theme]['name']}")
        return
    
    try:
        theme_index = int(args)
        if 0 <= theme_index < len(themes):
            CONFIG["system"]["theme"] = themes[theme_index]
            save_system_config()
            print(f"Theme changed to: {themes[theme_index]}")
        else:
            print(f"Invalid theme index. Choose 0-{len(themes)-1}")
    except ValueError:
        print("Invalid theme index. Use 'theme' without args to see available themes.")

def display_console_help():
    """Display console help"""
    print("\nCONSENSUS CONSOLE HELP:")
    print("  vote <query>    - Submit query to AI tribunal for consensus decision")
    print("  status          - Show system operational status and monolith health")
    print("  health          - Display detailed system health metrics")
    print("  history [N]     - Show last N decisions (default: 10)")
    print("  export <format> - Export decision history (json, csv, txt)")
    print("  config          - Display current system configuration")
    print("  theme [N]       - Change UI theme (use without args to list themes)")
    print("  help            - Show this help message")
    print("  quit            - Exit console mode")

# ==============================================================================
# MODULE 11: EXPORT & I/O OPERATIONS
# ==============================================================================

def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.json"
        export_data = {
            "export_metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "total_decisions": len(decision_history),
                "export_format": "json"
            },
            "decisions": [
                {
                    **decision,
                    "timestamp": decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Timestamp", "Decision_ID", "Query", "Consensus", "Confidence",
                "Session_ID", "System_Mode", "Theme", "Version"
            ])
            
            # Write data
            for decision in decision_history:
                timestamp_str = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                
                writer.writerow([
                    timestamp_str,
                    decision.get("id", ""),
                    decision["query"],
                    decision["verdict"],
                    f"{decision.get('confidence', 0.0):.2f}",
                    decision.get("session_id", ""),
                    decision.get("system_state", {}).get("mode", ""),
                    decision.get("system_state", {}).get("theme", ""),
                    decision.get("system_state", {}).get("version", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"System Version: {VERSION}\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 60 + "\n\n")
            
            # Individual decisions
            for i, decision in enumerate(decision_history, 1):
                timestamp_str = decision["timestamp"].isoformat() if isinstance(decision["timestamp"], datetime.datetime) else decision["timestamp"]
                
                f.write(f"DECISION #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"ID: {decision.get('id', 'N/A')}\n")
                f.write(f"Timestamp: {timestamp_str}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Consensus: {decision['verdict']}\n")
                f.write(f"Confidence: {decision.get('confidence', 0.0):.0%}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                # Individual votes
                if decision.get("individual_votes"):
                    f.write("\nIndividual Monolith Votes:\n")
                    for monolith, vote_data in decision["individual_votes"].items():
                        f.write(f"  {monolith}: {vote_data.get('vote', 'N/A')}\n")
                
                # System state
                if decision.get("system_state"):
                    state = decision["system_state"]
                    f.write(f"\nSystem State: Mode={state.get('mode', 'N/A')}, Theme={state.get('theme', 'N/A')}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    log(f"Decisions exported to {filename} ({format_type.upper()} format)", LogLevel.INFO, "EXPORT")
    return str(filename)

# ==============================================================================
# MODULE 12: DEMO & TESTING FUNCTIONS
# ==============================================================================

def demo_voting_process():
    """Demo voting process with sample queries"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?"
    ]
    
    query = random.choice(queries)
    log(f"Demo vote initiated: {query}", LogLevel.INFO, "DEMO")
    
    # Create orchestrator and execute vote
    orchestrator = VotingOrchestrator()
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Log results
    log(f"Demo vote complete: {consensus.value} (confidence: {confidence:.2f})", LogLevel.INFO, "DEMO")
    
    # Display results in console if available
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print(f"\nDemo Vote Results:")
        print(f"Query: {query}")
        print(f"Consensus: {consensus.value}")
        print(f"Confidence: {confidence:.0%}")

# ==============================================================================
# MODULE 13: MAIN APPLICATION LOOP
# ==============================================================================

# ==============================================================================
# MODULE 14: MAIN ENTRY POINT
# ==============================================================================

def main():
    """Main entry point with enhanced error handling"""
    try:
        # Show boot sequence
        show_boot_sequence()
        
        # Initialize system
        initialize_system()
        
        # Add startup notifications
        add_notification("All monoliths initialized", NotificationLevel.INFO)
        add_notification("System ready for operation", NotificationLevel.SUCCESS)
        
        # Mode selection
        print("\n" + "="*80)
        print("CONSENSUS SYSTEM - OPERATIONAL MODE SELECTION")
        print("="*80)
        print("1. GUI Mode (Full interface with real-time monitoring)")
        print("2. Console Mode (Direct command-line operation)")
        print("3. Demo Mode (Automated demonstration)")
        print("4. Exit System")
        
        while True:
            choice = input("\nSelect operational mode (1-4): ").strip()
            
            if choice == "1":
                log("Starting GUI mode", LogLevel.INFO, "MODE")
                try:
                    curses.wrapper(run_ui_loop)
                except Exception as e:
                    log(f"GUI mode error: {e}", LogLevel.ERROR, "MODE")
                    print(f"GUI mode failed: {e}")
                break
            elif choice == "2":
                log("Starting console mode", LogLevel.INFO, "MODE")
                run_console_mode()
                break
            elif choice == "3":
                log("Starting demo mode", LogLevel.INFO, "MODE")
                demo_voting_process()
                break
            elif choice == "4":
                log("User requested exit", LogLevel.INFO, "MODE")
                print("Terminating CONSENSUS System...")
                break
            else:
                print("Invalid selection. Please choose 1-4.")
        
    except KeyboardInterrupt:
        print("\n\nSystem interrupted by user.")
        log("System interrupted by user", LogLevel.WARNING, "MAIN")
    except Exception as e:
        error_msg = f"Fatal system error: {e}"
        print(f"\n{error_msg}")
        log(error_msg, LogLevel.CRITICAL, "MAIN")
        log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "MAIN")
        sys.exit(1)
    finally:
        # Cleanup and shutdown
        uptime = get_system_uptime()
        log(f"CONSENSUS System shutting down after {uptime} uptime", LogLevel.SHUTDOWN, "MAIN")
        
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        SYSTEM SHUTDOWN COMPLETE                            ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print(f"🟢 CONSENSUS System terminated gracefully")
        print(f"📊 Session summary: {len(decision_history)} decisions processed")
        print(f"⏱️  Total uptime: {uptime}")
        
        if decision_history:
            last_decision = decision_history[-1]
            last_time = last_decision["timestamp"]
            if isinstance(last_time, str):
                last_time = datetime.datetime.fromisoformat(last_time)
            print(f"🕒 Last decision: {last_time.strftime('%H:%M:%S')} - {last_decision['verdict']}")

if __name__ == "__main__":
    main()("\n" + "=" * 80)
    print("CONSENSUS SYSTEM - CONSOLE COMMAND INTERFACE")
    print("=" * 80)
    print("Available commands:")
    print("  vote <query>          - Submit query to tribunal for voting")
    print("  status                - Display system status")
    print("  health                - Show detailed health metrics")
    print("  history [N]           - Show last N decisions (default: 10)")
    print("  export <json|csv|txt> - Export decision history")
    print("  config                - Display configuration")
    print("  theme <name>          - Change UI theme")
    print("  help                  - Show this help")
    print("  quit                  - Exit console mode")
    print("=" * 80)
    
    orchestrator = VotingOrchestrator()
    
    while True:
        try:
            # Get command input
            command_input = input(f"\n[{CONFIG['system']['system_mode']}] CONSENSUS> ").strip()
            
            if not command_input:
                continue
            
            # Parse command and arguments
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            # Process commands
            if command in ["quit", "exit", "q"]:
                break
            
            elif command == "vote":
                handle_console_vote(orchestrator, args)
            
            elif command == "status":
                display_console_status(orchestrator)
            
            elif command == "health":
                display_health_metrics()
            
            elif command == "history":
                display_decision_history(args)
            
            elif command == "export":
                handle_console_export(args)
            
            elif command == "config":
                display_configuration()
            
            elif command == "theme":
                handle_theme_change(args)
            
            elif command == "help":
                display_console_help()
            
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", LogLevel.ERROR, "CONSOLE")

def handle_console_vote(orchestrator: VotingOrchestrator, query: str):
    """Handle voting command in console mode"""
    if not query:
        print("Usage: vote <your question>")
        return
    
    print#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.8.0)
Modular implementation with organized structure for easy extension.

Author: AI Assistant & Human Collaboration
Version: 3.8.0
Date: May 2025
"""

import hashlib
import traceback
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures

# ==============================================================================
# MODULE 1: SYSTEM CONSTANTS & CONFIGURATION
# ==============================================================================

# === VERSION INFORMATION ===
VERSION = "3.8.0"
BUILD_DATE = "2025-05-19"
BUILD_HASH = hashlib.md5(f"{VERSION}{BUILD_DATE}".encode()).hexdigest()[:8]

# === SYSTEM PATHS ===
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
BACKUP_DIR = ARBITER_DIR / "backups"
CONFIG_PATH = ARBITER_DIR / "config.json"
DECISION_HISTORY_PATH = ARBITER_DIR / "decision_history.json"

# === ENUMS ===
class SystemMode(Enum):
    READY = "READY"
    VOTING = "VOTING"
    ANALYZING = "ANALYZING"
    CONSENSUS = "CONSENSUS"
    DEADLOCK = "DEADLOCK"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"
    CRITICAL = "CRITICAL"

class VoteResult(Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    ERROR = "ERROR"

class NotificationLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"

# === DATA STRUCTURES ===
@dataclass
class VoteData:
    monolith: str
    query: str
    vote: VoteResult
    reasoning: str
    confidence: float
    response_time: float
    timestamp: datetime.datetime
    session_id: str

@dataclass
class DecisionRecord:
    id: str
    query: str
    verdict: VoteResult
    individual_votes: Dict[str, VoteData]
    confidence: float
    timestamp: datetime.datetime
    session_id: str
    reasoning: str
    system_state: Dict[str, Any]
    audit_trail: List[str]

@dataclass
class SystemHealthMetrics:
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    api_response_time: float
    tts_status: str
    network_status: str
    uptime: float
    error_count: int
    last_check: datetime.datetime

# === ASCII ART ===
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

CONSENSUS_LOGO = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                       v{VERSION}      ║
║                         Build: {BUILD_HASH}                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# === THEME DEFINITIONS ===
THEME_DEFINITIONS = {
    "military": {
        "name": "Military HQ",
        "box_chars": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
        "colors": {"primary": 2, "secondary": 3, "accent": 6, "warning": 1}
    },
    "tars": {
        "name": "TARS Interface",
        "box_chars": {"tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦", "h": "⎯", "v": "⎮"},
        "colors": {"primary": 4, "secondary": 6, "accent": 7, "warning": 3}
    },
    "eva": {
        "name": "Evangelion MAGI",
        "box_chars": {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "v": "▌"},
        "colors": {"primary": 5, "secondary": 1, "accent": 3, "warning": 6}
    },
    "wh40k": {
        "name": "Imperial Gothic",
        "box_chars": {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
        "colors": {"primary": 6, "secondary": 3, "accent": 2, "warning": 1}
    },
    "helldivers": {
        "name": "Super Earth Command",
        "box_chars": {"tl": "◢", "tr": "◣", "bl": "◥", "br": "◤", "h": "━", "v": "┃"},
        "colors": {"primary": 2, "secondary": 4, "accent": 6, "warning": 1}
    }
}

# === SYSTEM CONFIGURATION ===
DEFAULT_CONFIG = {
    "system": {
        "theme": "military",
        "current_view": "main",
        "system_mode": SystemMode.READY.value,
        "debug_mode": False,
        "max_log_entries": 1000,
        "max_decisions": 100
    },
    "llm": {
        "provider": "ollama",
        "api_timeout": 30,
        "vote_timeout": 45,
        "max_retries": 3,
        "base_url": "http://localhost:11434"
    },
    "monoliths": {
        "RATIONALIS": {
            "model": "deepseek-coder:33b",
            "prompt": "You are RATIONALIS, the logic engine of the CONSENSUS Tribunal. Analyze the query with pure logical reasoning. Respond with APPROVE or DENY followed by your detailed logical analysis.",
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024,
            "specialty": "logical_analysis"
        },
        "AETERNUM": {
            "model": "llama3:70b",
            "prompt": "You are AETERNUM, the temporal analyst and market sage of the CONSENSUS Tribunal. Analyze patterns, historical precedents, and market implications. Respond with APPROVE or DENY followed by your temporal analysis.",
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024,
            "specialty": "pattern_analysis"
        },
        "BELLATOR": {
            "model": "mixtral:8x7b",
            "prompt": "You are BELLATOR, the tactical strategist and risk assessor of the CONSENSUS Tribunal. Evaluate security implications, tactical risks, and strategic outcomes. Respond with APPROVE or DENY followed by your tactical assessment.",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "specialty": "risk_assessment"
        }
    },
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9,
        "announce_decisions": True
    },
    "health": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3,
        "alert_thresholds": {
            "cpu": 90.0,
            "memory": 85.0,
            "response_time": 10.0
        }
    },
    "ui": {
        "refresh_rate": 10,
        "animation_speed": 50,
        "show_debug": False,
        "color_scheme": "default"
    },
    "export": {
        "auto_backup": True,
        "backup_interval": 3600,
        "formats": ["json", "csv", "txt"]
    }
}

# === GLOBAL STATE ===
CONFIG = DEFAULT_CONFIG.copy()
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
active_votes = {}
startup_time = time.time()

system_health = SystemHealthMetrics(
    cpu_usage=0.0, memory_usage=0.0, disk_usage=0.0,
    api_response_time=0.0, tts_status="unknown", network_status="unknown",
    uptime=0.0, error_count=0, last_check=datetime.datetime.now()
)

# Threading locks
health_lock = threading.Lock()
decision_lock = threading.Lock()
log_lock = threading.Lock()

# ==============================================================================
# MODULE 2: BOOT SEQUENCE & INITIALIZATION
# ==============================================================================

def show_boot_sequence():
    """Display the enhanced boot sequence with NERV logo and initialization"""
    # Clear screen and display NERV logo
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.5)
    
    # Display CONSENSUS header
    print(CONSENSUS_LOGO)
    time.sleep(0.8)
    
    # System initialization display
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Initialization steps with progress
    init_steps = [
        ("Checking system resources", [
            "CPU availability", "Memory alignment", "Storage capacity", "Display capabilities"
        ]),
        ("Initializing AI cores", [
            "RATIONALIS logic engine", "AETERNUM temporal analyst", "BELLATOR tactical assessor"
        ]),
        ("Establishing network", [
            "API endpoints", "Model connections", "Health monitoring", "TTS integration"
        ]),
        ("Loading interface", [
            "Theme system", "Command parser", "Display engine", "Control bindings"
        ]),
        ("Finalizing startup", [
            "Configuration validation", "Log system", "Decision tracking", "Ready state"
        ])
    ]
    
    for step_name, substeps in init_steps:
        print(f"\n◢◣ {step_name}...")
        time.sleep(0.4)
        for substep in substeps:
            print(f"  ├─ {substep}{'.' * (35 - len(substep))} [✓]")
            time.sleep(0.3)
        time.sleep(0.2)
    
    # Boot completion
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Display control information
    print(f"""
\033[1;33m▶ Control Keys:\033[0m
  - \033[1;36mQ\033[0m: Quit system         - \033[1;36mM\033[0m: Main view
  - \033[1;36mS\033[0m: Cycle themes        - \033[1;36mV\033[0m: Vote demo
  - \033[1;36mC\033[0m: Console mode        - \033[1;36m9\033[0m: Diagnostics
  - \033[1;36mH\033[0m: Help system         - \033[1;36m7\033[0m: Decision history

\033[1;32m■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE...\033[0m""")
    
    input()

def initialize_system():
    """Initialize the CONSENSUS system directories and configuration"""
    try:
        # Create system directories
        for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR, EXPORT_DIR, BACKUP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        load_system_config()
        
        # Initialize logging
        log("CONSENSUS System initialization started", LogLevel.STARTUP)
        log(f"Version: {VERSION}, Build: {BUILD_HASH}", LogLevel.STARTUP)
        
        # Load decision history
        load_decision_history()
        
        # Initialize health monitoring
        if CONFIG["health"]["enabled"]:
            threading.Thread(target=health_monitor_daemon, daemon=True).start()
            log("Health monitoring daemon started", LogLevel.INFO)
        
        log("System initialization completed successfully", LogLevel.STARTUP)
        add_notification("CONSENSUS System Online", NotificationLevel.SUCCESS)
        
    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        log(error_msg, LogLevel.CRITICAL)
        print(f"FATAL ERROR: {error_msg}")
        sys.exit(1)

# ==============================================================================
# MODULE 3: LOGGING SYSTEM
# ==============================================================================

def log(message: str, level: LogLevel = LogLevel.INFO, component: str = "SYSTEM", session_id: str = None):
    """Enhanced logging with component tracking and structured format"""
    timestamp = datetime.datetime.now()
    
    # Create log entry
    entry = {
        "timestamp": timestamp,
        "level": level.value,
        "component": component,
        "message": message,
        "session_id": session_id,
        "thread": threading.current_thread().name
    }
    
    # Add to memory
    with log_lock:
        log_entries.append(entry)
    
    # Format for file output
    session_part = f" [{session_id}]" if session_id else ""
    formatted_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [{level.value:8}] [{component:12}]{session_part} {message}"
    
    # Write to daily log file
    try:
        log_file = LOG_DIR / f"{timestamp.strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{formatted_entry}\n")
    except Exception as e:
        print(f"Failed to write log: {e}")

def add_notification(message: str, level: NotificationLevel = NotificationLevel.INFO, context: Dict[str, Any] = None):
    """Add notification with enhanced metadata"""
    notification = {
        "id": hashlib.md5(f"{message}{time.time()}".encode()).hexdigest()[:8],
        "message": message,
        "level": level.value,
        "timestamp": datetime.datetime.now(),
        "context": context or {},
        "seen": False,
        "persistent": level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
    }
    
    notifications.append(notification)
    log(f"Notification: {message}", LogLevel.INFO if level == NotificationLevel.INFO else LogLevel.WARNING)

def cleanup_expired_notifications():
    """Remove old non-critical notifications"""
    current_time = datetime.datetime.now()
    cutoff_time = current_time - datetime.timedelta(minutes=5)
    
    global notifications
    notifications = deque([
        n for n in notifications 
        if n["persistent"] or n["timestamp"] > cutoff_time
    ], maxlen=15)

# ==============================================================================
# MODULE 4: CONFIGURATION MANAGEMENT
# ==============================================================================

def load_system_config():
    """Load system configuration with validation and migration"""
    global CONFIG
    
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # Merge with defaults (preserving new defaults)
            CONFIG = merge_configs(DEFAULT_CONFIG, loaded_config)
            log("Configuration loaded successfully", LogLevel.INFO, "CONFIG")
        else:
            CONFIG = DEFAULT_CONFIG.copy()
            save_system_config()
            log("Default configuration created", LogLevel.INFO, "CONFIG")
            
    except Exception as e:
        log(f"Failed to load configuration: {e}", LogLevel.ERROR, "CONFIG")
        CONFIG = DEFAULT_CONFIG.copy()

def merge_configs(default: dict, loaded: dict) -> dict:
    """Recursively merge configuration dictionaries"""
    result = default.copy()
    
    for key, value in loaded.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result

def save_system_config():
    """Save current configuration to file"""
    try:
        # Create backup of existing config
        if CONFIG_PATH.exists():
            backup_path = BACKUP_DIR / f"config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import shutil
            shutil.copy2(CONFIG_PATH, backup_path)
        
        # Save current config
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=2, default=str)
        
        log("Configuration saved successfully", LogLevel.INFO, "CONFIG")
        
    except Exception as e:
        log(f"Failed to save configuration: {e}", LogLevel.ERROR, "CONFIG")

# ==============================================================================
# MODULE 5: HEALTH MONITORING
# ==============================================================================

def update_system_health():
    """Comprehensive system health check"""
    global system_health
    
    try:
        import psutil
        
        with health_lock:
            # CPU and Memory
            system_health.cpu_usage = psutil.cpu_percent(interval=0.1)
            system_health.memory_usage = psutil.virtual_memory().percent
            system_health.disk_usage = psutil.disk_usage('/').percent
            
            # Network connectivity test
            try:
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                if response.status_code == 200:
                    system_health.network_status = "operational"
                    system_health.api_response_time = response.elapsed.total_seconds()
                else:
                    system_health.network_status = "degraded"
            except Exception:
                system_health.network_status = "unavailable"
                system_health.api_response_time = 999.0
            
            # TTS status
            if CONFIG["tts"]["enabled"]:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    system_health.tts_status = "operational"
                    engine.stop()
                    del engine
                except Exception:
                    system_health.tts_status = "unavailable"
            else:
                system_health.tts_status = "disabled"
            
            # Update timestamp and uptime
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except ImportError:
        log("psutil not available - using simulated health metrics", LogLevel.WARNING, "HEALTH")
        # Simulated values when psutil not available
        with health_lock:
            system_health.cpu_usage = random.uniform(10, 40)
            system_health.memory_usage = random.uniform(30, 70)
            system_health.disk_usage = random.uniform(20, 80)
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except Exception as e:
        log(f"Health check failed: {e}", LogLevel.ERROR, "HEALTH")
        system_health.error_count += 1

def health_monitor_daemon():
    """Background health monitoring daemon"""
    while True:
        try:
            update_system_health()
            
            # Check thresholds and alert if necessary
            if CONFIG["health"]["enabled"]:
                thresholds = CONFIG["health"]["alert_thresholds"]
                
                if system_health.cpu_usage > thresholds["cpu"]:
                    add_notification(f"High CPU usage: {system_health.cpu_usage:.1f}%", NotificationLevel.WARNING)
                
                if system_health.memory_usage > thresholds["memory"]:
                    add_notification(f"High memory usage: {system_health.memory_usage:.1f}%", NotificationLevel.WARNING)
                
                if system_health.api_response_time > thresholds["response_time"]:
                    add_notification(f"Slow API response: {system_health.api_response_time:.2f}s", NotificationLevel.WARNING)
            
            time.sleep(CONFIG["health"]["check_interval"])
            
        except Exception as e:
            log(f"Health monitor daemon error: {e}", LogLevel.ERROR, "HEALTH")
            time.sleep(30)  # Back off on error

def get_system_uptime() -> str:
    """Get formatted system uptime"""
    uptime_seconds = int(time.time() - startup_time)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {uptime_seconds % 60}s"

# ==============================================================================
# MODULE 6: MONOLITH SYSTEM
# ==============================================================================

class EnhancedMonolith:
    """Enhanced monolith with specialized analysis capabilities"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = CONFIG["monoliths"][name]
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        self.status = "unknown"
        self.last_check = None
        self.error_count = 0
        self.total_votes = 0
        self.response_times = deque(maxlen=50)
        
    def check_model_status(self) -> str:
        """Check if the model is available and loaded"""
        try:
            provider = CONFIG["llm"]["provider"]
            
            if provider == "ollama":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_name = self.config["model"]
                    
                    for model in models:
                        if model["name"] == model_name:
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            elif provider == "lmstudio":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/v1/models",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    model_name = self.config["model"].split(":")[0].lower()
                    
                    for model in models:
                        if model_name in model["id"].lower():
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            else:
                self.status = "unknown_provider"
                return "unknown_provider"
                
        except Exception as e:
            log(f"[{self.name}] Status check failed: {e}", LogLevel.ERROR, "MONOLITH")
            self.status = "unreachable"
            self.error_count += 1
            return "unreachable"
    
    def cast_vote(self, query: str, session_id: str) -> VoteData:
        """Cast a vote with enhanced error handling and metrics"""
        start_time = time.time()
        
        try:
            log(f"[{self.name}] Casting vote for session {session_id}", LogLevel.INFO, "VOTE", session_id)
            
            # Check model status first
            if self.status != "ready":
                status = self.check_model_status()
                if status != "ready":
                    raise Exception(f"Model not ready: {status}")
            
            # Prepare prompt
            full_prompt = f"{self.config['prompt']}\n\nQUERY: {query}\n\nVOTE:"
            
            # Make API call
            response = self._call_api(full_prompt)
            response_time = time.time() - start_time
            
            # Parse response
            parsed_vote, confidence = self._parse_response(response)
            
            # Create vote data
            vote_data = VoteData(
                monolith=self.name,
                query=query,
                vote=parsed_vote,
                reasoning=response,
                confidence=confidence,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
            
            # Save vote
            self._save_vote(vote_data)
            
            # Update metrics
            self.total_votes += 1
            self.response_times.append(response_time)
            
            log(f"[{self.name}] Vote cast: {parsed_vote.value} (confidence: {confidence:.2f}, time: {response_time:.2f}s)", 
                LogLevel.INFO, "VOTE", session_id)
            
            return vote_data
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Vote failed: {str(e)}"
            
            log(f"[{self.name}] {error_msg}", LogLevel.ERROR, "VOTE", session_id)
            self.error_count += 1
            
            # Return error vote
            return VoteData(
                monolith=self.name,
                query=query,
                vote=VoteResult.ERROR,
                reasoning=error_msg,
                confidence=0.0,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
    
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM provider"""
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "top_p": self.config["

# ================================================================================
#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.8.0)
Modular implementation with organized structure for easy extension.

def update_system_health():
    """Comprehensive system health check"""
    global system_health
    
    try:
        import psutil
        
        with health_lock:
            # CPU and Memory
            system_health.cpu_usage = psutil.cpu_percent(interval=0.1)
            system_health.memory_usage = psutil.virtual_memory().percent
            system_health.disk_usage = psutil.disk_usage('/').percent
            
            # Network connectivity test
            try:
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _parse_response(self, response: str) -> Tuple[VoteResult, float]:
        """Parse LLM response to extract vote and confidence"""
        response_upper = response.upper()
        
        # Extract vote
        if "APPROVE" in response_upper:
            vote = VoteResult.APPROVE
        elif "DENY" in response_upper:
            vote = VoteResult.DENY
        elif "ABSTAIN" in response_upper:
            vote = VoteResult.ABSTAIN
        else:
            vote = VoteResult.ERROR
        
        # Calculate confidence based on response characteristics
        confidence = min(0.95, max(0.1, 
            0.7 + 0.2 * (len(response) / 500) + 
            0.1 * (response.count(".") / max(1, len(response.split())))
        ))
        
        return vote, confidence
    
    def _save_vote(self, vote_data: VoteData):
        """Save vote to file"""
        try:
            with open(self.vote_file, 'w', encoding='utf-8') as f:
                # Convert dataclass to dict for JSON serialization
                vote_dict = asdict(vote_data)
                vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                vote_dict["vote"] = vote_data.vote.value
                json.dump(vote_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"[{self.name}] Failed to save vote: {e}", LogLevel.ERROR, "VOTE")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this monolith"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return {
            "status": self.status,
            "total_votes": self.total_votes,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_votes),
            "avg_response_time": avg_response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "specialty": self.config["specialty"],
            "model": self.config["model"]
        }

class VotingOrchestrator:
    """Orchestrates the voting process between monoliths"""
    
    def __init__(self):
        self.monoliths = {
            name: EnhancedMonolith(name) for name in CONFIG["monoliths"]
        }
        self.consensus_engine = ConsensusEngine()
        self.active_session = None
    
    def initiate_vote(self, query: str, context: Dict[str, Any] = None) -> Tuple[VoteResult, float, str, Dict[str, VoteData]]:
        """Initiate voting process with enhanced session management"""
        session_id = self._generate_session_id(query)
        self.active_session = session_id
        
        log(f"Initiating vote for session {session_id}: {query[:100]}...", LogLevel.INFO, "VOTE", session_id)
        
        # Update system mode
        CONFIG["system"]["system_mode"] = SystemMode.VOTING.value
        add_notification("AI Tribunal deliberation commenced", NotificationLevel.INFO)
        
        try:
            # Collect votes from all monoliths
            votes = self._collect_votes(query, session_id)
            
            # Analyze and calculate consensus
            CONFIG["system"]["system_mode"] = SystemMode.ANALYZING.value
            consensus, confidence, reasoning = self.consensus_engine.calculate_consensus(votes)
            
            # Update system mode based on result
            if consensus == VoteResult.APPROVE:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION GRANTED", NotificationLevel.SUCCESS)
            elif consensus == VoteResult.DENY:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION DENIED", NotificationLevel.WARNING)
            elif consensus == VoteResult.ABSTAIN:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("TRIBUNAL ABSTAINS", NotificationLevel.INFO)
            else:
                CONFIG["system"]["system_mode"] = SystemMode.DEADLOCK.value
                add_notification("DEADLOCK - Manual intervention required", NotificationLevel.ERROR)
            
            # Record decision
            self._record_decision(query, consensus, votes, confidence, reasoning, session_id)
            
            # Announce verdict with enhanced TTS
            self._announce_verdict(consensus, confidence)
            
            # Schedule system reset
            threading.Timer(10.0, self._reset_mode).start()
            
            log(f"Vote complete - Consensus: {consensus.value}, Confidence: {confidence:.2f}", 
                LogLevel.INFO, "VOTE", session_id)
            
            return consensus, confidence, reasoning, votes
            
        except concurrent.futures.TimeoutError:
            log(f"Vote timed out after {CONFIG['llm']['vote_timeout']}s", LogLevel.ERROR, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification("Vote timeout - System error", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, "Vote timed out", {}
            
        except Exception as e:
            log(f"Vote orchestration failed: {e}", LogLevel.ERROR, "VOTE", session_id)
            log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification(f"Vote failed: {str(e)}", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, f"Vote failed: {str(e)}", {}
    
    def _generate_session_id(self, query: str) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
        return f"{timestamp}_{query_hash}"
    
    def _collect_votes(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Collect votes from all monoliths with parallel processing"""
        votes = {}
        
        if CONFIG["llm"].get("enable_parallel_processing", True):
            # Parallel vote collection
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.monoliths)) as executor:
                future_to_monolith = {
                    executor.submit(monolith.cast_vote, query, session_id): name 
                    for name, monolith in self.monoliths.items()
                }
                
                for future in concurrent.futures.as_completed(future_to_monolith, timeout=CONFIG["llm"]["vote_timeout"]):
                    monolith_name = future_to_monolith[future]
                    try:
                        vote_data = future.result()
                        votes[monolith_name] = vote_data
                        
                        # Update active votes for UI
                        active_votes[monolith_name] = vote_data
                        
                        add_notification(f"{monolith_name} deliberation complete", NotificationLevel.INFO)
                        
                    except Exception as e:
                        log(f"Vote collection failed for {monolith_name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        else:
            # Sequential vote collection
            for name, monolith in self.monoliths.items():
                try:
                    vote_data = monolith.cast_vote(query, session_id)
                    votes[name] = vote_data
                    active_votes[name] = vote_data
                    add_notification(f"{name} deliberation complete", NotificationLevel.INFO)
                except Exception as e:
                    log(f"Sequential vote collection failed for {name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        
        return votes
    
    def _record_decision(self, query: str, consensus: VoteResult, votes: Dict[str, VoteData], 
                        confidence: float, reasoning: str, session_id: str):
        """Record decision with comprehensive metadata"""
        decision_id = hashlib.md5(f"{query}{session_id}{time.time()}".encode()).hexdigest()[:12]
        
        # Capture system state
        system_state = {
            "theme": CONFIG["system"]["theme"],
            "version": VERSION,
            "build_hash": BUILD_HASH,
            "mode": CONFIG["system"]["system_mode"],
            "uptime": get_system_uptime(),
            "health_score": self._calculate_health_score()
        }
        
        # Create decision record
        decision = DecisionRecord(
            id=decision_id,
            query=query,
            verdict=consensus,
            individual_votes=votes,
            confidence=confidence,
            timestamp=datetime.datetime.now(),
            session_id=session_id,
            reasoning=reasoning,
            system_state=system_state,
            audit_trail=[f"Decision recorded for session {session_id}"]
        )
        
        # Add to history
        with decision_lock:
            decision_history.append(decision)
        
        # Save to persistent storage
        self._save_decision_history()
        
        log(f"Decision recorded: {consensus.value} for query '{query[:50]}...'", LogLevel.INFO, "DECISION", session_id)
    
    def _announce_verdict(self, consensus: VoteResult, confidence: float):
        """Announce verdict with enhanced TTS and typing effect"""
        if not CONFIG["tts"]["enabled"] or not CONFIG["tts"]["announce_decisions"]:
            return
        
        try:
            import pyttsx3
            
            # Initialize TTS engine with enhanced configuration
            engine = pyttsx3.init()
            
            # Configure voice properties
            voices = engine.getProperty('voices')
            if voices:
                # Prefer female voice for GLaDOS-like effect
                for voice in voices:
                    voice_name = voice.name.lower()
                    if any(keyword in voice_name for keyword in ['zira', 'hazel', 'female']):
                        engine.setProperty('voice', voice.id)
                        break
            
            # Set speech parameters based on decision type
            base_rate = CONFIG["tts"]["voice_rate"]
            if consensus == VoteResult.ERROR:
                engine.setProperty('rate', int(base_rate * 0.7))  # Slower for errors
            else:
                engine.setProperty('rate', base_rate)
            
            engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
            # Create enhanced announcement with typing effect
            if consensus == VoteResult.APPROVE:
                announcement = f"Consensus achieved. Authorization granted with {confidence:.0%} confidence."
                intro = "The tribunal has reached its decision..."
            elif consensus == VoteResult.DENY:
                announcement = f"Consensus achieved. Authorization denied with {confidence:.0%} confidence."
                intro = "The tribunal has reached its decision..."
            elif consensus == VoteResult.ABSTAIN:
                announcement = f"Tribunal abstains from decision with {confidence:.0%} confidence."
                intro = "The tribunal finds itself... conflicted..."
            else:
                announcement = "Tribunal deadlocked. Manual intervention required."
                intro = "The tribunal cannot reach consensus..."
            
            # Typing effect for console output
            print("\n" + "=" * 60)
            print("TRIBUNAL VERDICT ANNOUNCEMENT")
            print("=" * 60)
            
            def type_text(text, delay=0.03):
                """Print text with typing effect"""
                for char in text:
                    print(char, end='', flush=True)
                    time.sleep(delay)
                print()
            
            type_text(intro, 0.05)
            time.sleep(1.0)
            type_text(announcement, 0.02)
            print("=" * 60)
            
            # Speak the announcement
            engine.say(intro)
            engine.runAndWait()
            time.sleep(0.5)
            engine.say(announcement)
            engine.runAndWait()
            engine.stop()
            
            log(f"Enhanced TTS announcement completed: {consensus.value}", LogLevel.INFO, "TTS")
            
        except ImportError:
            log("TTS failed: pyttsx3 not installed. Install with: pip install pyttsx3", LogLevel.WARNING, "TTS")
            system_health.tts_status = "unavailable"
        except Exception as e:
            log(f"Enhanced TTS error: {e}", LogLevel.ERROR, "TTS")
            system_health.tts_status = "error"
    
    def _reset_mode(self):
        """Reset system mode after decision process"""
        CONFIG["system"]["system_mode"] = SystemMode.READY.value
        self.active_session = None
        active_votes.clear()
        log("System mode reset to READY", LogLevel.INFO, "VOTE")
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score"""
        score = 0.85  # Base score
        
        # Adjust based on system health
        if system_health.network_status == "operational":
            score += 0.1
        elif system_health.network_status == "degraded":
            score -= 0.05
        else:
            score -= 0.2
        
        if system_health.tts_status == "operational":
            score += 0.05
        
        # Factor in error rate
        if system_health.error_count == 0:
            score += 0.02
        elif system_health.error_count > 5:
            score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _save_decision_history(self):
        """Save decision history to persistent storage"""
        try:
            # Prepare data for JSON serialization
            decisions_data = []
            for decision in decision_history:
                decision_dict = asdict(decision)
                decision_dict["timestamp"] = decision.timestamp.isoformat()
                decision_dict["verdict"] = decision.verdict.value
                
                # Convert individual votes
                votes_dict = {}
                for monolith, vote_data in decision.individual_votes.items():
                    vote_dict = asdict(vote_data)
                    vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                    vote_dict["vote"] = vote_data.vote.value
                    votes_dict[monolith] = vote_dict
                decision_dict["individual_votes"] = votes_dict
                
                decisions_data.append(decision_dict)
            
            # Add metadata
            export_data = {
                "metadata": {
                    "version": VERSION,
                    "build_hash": BUILD_HASH,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "total_decisions": len(decisions_data)
                },
                "decisions": decisions_data
            }
            
            with open(DECISION_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            log("Decision history saved to persistent storage", LogLevel.INFO, "DECISION")
            
        except Exception as e:
            log(f"Failed to save decision history: {e}", LogLevel.ERROR, "DECISION")
    
    def check_all_models(self):
        """Check status of all monolith models"""
        results = {}
        
        for name, monolith in self.monoliths.items():
            status = monolith.check_model_status()
            results[name] = {
                "status": status,
                "performance": monolith.get_performance_metrics()
            }
            log(f"[{name}] Model check: {status}", LogLevel.INFO, "MONOLITH")
        
        return results

def load_decision_history():
    """Load decision history from persistent storage"""
    try:
        if DECISION_HISTORY_PATH.exists():
            with open(DECISION_HISTORY_PATH, 'r', encoding='utf-8') as f:
                stored_data = json.load(f)
            
            # Handle both old and new format
            if "decisions" in stored_data:
                decisions_data = stored_data["decisions"]
            else:
                decisions_data = stored_data  # Old format
            
            # Convert back to datetime objects and add to memory
            for stored_decision in decisions_data[-CONFIG["system"]["max_decisions"]:]:
                stored_decision["timestamp"] = datetime.datetime.fromisoformat(stored_decision["timestamp"])
                decision_history.append(stored_decision)
            
            log(f"Loaded {len(decision_history)} decisions from history", LogLevel.INFO, "DECISION")
        
    except Exception as e:
        log(f"Failed to load decision history: {e}", LogLevel.ERROR, "DECISION")

def render_main_screen(stdscr, theme: str = None):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header with enhanced styling
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL COMMAND CENTER"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status overview
    status_y = 3
    safe_addstr(stdscr, status_y, 2, "SYSTEM STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    mode = CONFIG["system"]["system_mode"]
    mode_color = 2 if mode == "READY" else 3
    safe_addstr(stdscr, status_y + 1, 4, f"Operational Mode: {mode}", curses.color_pair(mode_color))
    
    health_score = f"{system_health.cpu_usage:.0f}% CPU"
    safe_addstr(stdscr, status_y + 1, 30, f"Health: {health_score}", curses.color_pair(2))
    
    api_color = 2 if system_health.network_status == "operational" else 1
    safe_addstr(stdscr, status_y + 1, 50, f"API: {system_health.network_status.upper()}", curses.color_pair(api_color))
    
    # Monolith status section
    mono_y = status_y + 3
    safe_addstr(stdscr, mono_y, 2, "MONOLITH STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    orchestrator = VotingOrchestrator()
    model_results = orchestrator.check_all_models()
    for i, (name, result) in enumerate(model_results.items()):
        status = result["status"]
        status_color = 2 if status == "ready" else 1
        safe_addstr(stdscr, mono_y + 1 + i, 4, f"{name}: {status.upper()}", curses.color_pair(status_color))
    
    # Display recent decisions (Key 7 functionality)
    if decision_history:
        decisions_y = mono_y + 6
        safe_addstr(stdscr, decisions_y, 2, "RECENT DECISIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_decisions = list(decision_history)[-5:]  # Show last 5
        for i, decision in enumerate(recent_decisions):
            y_pos = decisions_y + 1 + i
            
            # Timestamp
            timestamp = decision["timestamp"].strftime("%H:%M") if hasattr(decision["timestamp"], 'strftime') else str(decision["timestamp"])[:5]
            safe_addstr(stdscr, y_pos, 4, f"[{timestamp}]", curses.color_pair(7))
            
            # Consensus with color
            consensus = decision["verdict"]
            if consensus == "APPROVE":
                consensus_color = 2
            elif consensus == "DENY":
                consensus_color = 1
            else:
                consensus_color = 3
            
            safe_addstr(stdscr, y_pos, 12, consensus, curses.A_BOLD | curses.color_pair(consensus_color))
            
            # Query preview
            query_preview = decision["query"][:40] + "..." if len(decision["query"]) > 40 else decision["query"]
            safe_addstr(stdscr, y_pos, 22, query_preview, curses.color_pair(7))
    
    # Notifications section with cleanup
    cleanup_expired_notifications()
    if notifications:
        notif_y = height - 8
        safe_addstr(stdscr, notif_y, 2, "NOTIFICATIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_notifications = list(notifications)[-4:]  # Show last 4
        for i, notif in enumerate(recent_notifications):
            y_pos = notif_y + 1 + i
            
            # Color based on level
            color_map = {"success": 2, "error": 1, "warning": 3, "info": 7}
            color = color_map.get(notif["level"], 7)
            
            # Format notification
            timestamp = notif["timestamp"].strftime("%H:%M")
            notif_text = f"[{timestamp}] {notif['message']}"
            safe_addstr(stdscr, y_pos, 4, notif_text, curses.color_pair(color))
    
    # Control instructions
    controls_y = height - 3
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | 7:History | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

def render_decision_history(stdscr):
    """Render decision history view (Key 7 functionality)"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS DECISION HISTORY"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions recorded", curses.color_pair(3))
    else:
        # Table headers
        headers_y = 3
        safe_addstr(stdscr, headers_y, 2, "TIME", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 10, "VERDICT", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 20, "CONF", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 28, "QUERY", curses.A_BOLD | curses.color_pair(3))
        
        # Draw separator
        safe_addstr(stdscr, headers_y + 1, 2, "-" * (width - 4), curses.color_pair(7))
        
        # Display decisions
        start_y = headers_y + 2
        max_display = min(height - start_y - 3, len(decision_history))
        
        for i, decision in enumerate(list(decision_history)[-max_display:]):
            y_pos = start_y + i
            
            # Time
            timestamp = decision["timestamp"].strftime("%H:%M") if hasattr(decision["timestamp"], 'strftime') else str(decision["timestamp"])[:5]
            safe_addstr(stdscr, y_pos, 2, timestamp, curses.color_pair(7))
            
            # Verdict with color
            verdict = decision["verdict"]
            if verdict == "APPROVE":
                verdict_color = 2
            elif verdict == "DENY":  
                verdict_color = 1
            else:
                verdict_color = 3
            safe_addstr(stdscr, y_pos, 10, verdict, curses.color_pair(verdict_color))
            
            # Confidence
            confidence = f"{decision.get('confidence', 0.0):.0%}"
            safe_addstr(stdscr, y_pos, 20, confidence, curses.color_pair(7))
            
            # Query (truncated)
            query = decision["query"][:45] + "..." if len(decision["query"]) > 45 else decision["query"]
            safe_addstr(stdscr, y_pos, 28, query, curses.color_pair(7))
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press any key to return to main view", curses.color_pair(3))

def run_console_mode():
    """Enhanced console mode with comprehensive commands"""
    print("\n" + "=" * 80)
    print("CONSENSUS SYSTEM - CONSOLE COMMAND INTERFACE")
    print("=" * 80)
    print("Available commands:")
    print("  vote <query>          - Submit query to tribunal for voting")
    print("  status                - Display system status")
    print("  health                - Show detailed health metrics")
    print("  history [N]           - Show last N decisions (default: 10)")
    print("  export <json|csv|txt> - Export decision history")
    print("  config                - Display configuration")
    print("  theme <name>          - Change UI theme")
    print("  help                  - Show this help")
    print("  quit                  - Exit console mode")
    print("=" * 80)
    
    orchestrator = VotingOrchestrator()
    
    while True:
        try:
            # Get command input
            command_input = input(f"\n[{CONFIG['system']['system_mode']}] CONSENSUS> ").strip()
            
            if not command_input:
                continue
            
            # Parse command and arguments
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            # Process commands
            if command in ["quit", "exit", "q"]:
                break
            
            elif command == "vote":
                handle_console_vote(orchestrator, args)
            
            elif command == "status":
                display_console_status(orchestrator)
            
            elif command == "health":
                display_health_metrics()
            
            elif command == "history":
                display_decision_history(args)
            
            elif command == "export":
                handle_console_export(args)
            
            elif command == "config":
                display_configuration()
            
            elif command == "theme":
                handle_theme_change(args)
            
            elif command == "help":
                display_console_help()
            
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", LogLevel.ERROR, "CONSOLE")

def handle_console_vote(orchestrator: VotingOrchestrator, query: str):
    """Handle voting command in console mode with enhanced display"""
    if not query:
        print("Usage: vote <your question>")
        return
    
    print(f"\n🗳️  Initiating tribunal vote on: {query}")
    print("-" * 60)
    
    # Execute vote with enhanced display
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Display results with enhanced formatting
    print(f"\n{'='*60}")
    print(f"⚖️  FINAL TRIBUNAL VERDICT: {consensus.value}")
    print(f"📊 Confidence: {confidence:.0%}")
    print(f"{'='*60}")
    
    # Display individual votes
    print("\n📋 Individual Monolith Votes:")
    for name, vote_data in votes.items():
        status_icon = "✓" if vote_data.vote != VoteResult.ERROR else "✗"
        print(f"  {status_icon} {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})")
    
    print(f"\n💡 Reasoning: {reasoning[:200]}...")
    
    # Show enhanced summary with TTS announcement
    if CONFIG["tts"]["enabled"]:
        print("\n🔊 Audio announcement in progress...")

def display_console_status(orchestrator: VotingOrchestrator):
    """Display system status in console mode"""
    print("\n📊 SYSTEM STATUS:")
    print(f"  Version: {VERSION} (Build: {BUILD_HASH})")
    print(f"  Uptime: {get_system_uptime()}")
    print(f"  Total Decisions: {len(decision_history)}")
    print(f"  System Mode: {CONFIG['system']['system_mode']}")
    print(f"  API Status: {system_health.network_status}")
    print(f"  TTS Status: {system_health.tts_status}")
    
    print("\n🤖 MONOLITH STATUS:")
    model_results = orchestrator.check_all_models()
    for name, result in model_results.items():
        status = result["status"]
        performance = result["performance"]
        status_icon = "🟢" if status == "ready" else "🔴"
        print(f"  {status_icon} {name}: {status.upper()}")
        print(f"     Model: {performance['model']}")
        print(f"     Votes: {performance['total_votes']}, Errors: {performance['error_count']}")
        print(f"     Avg Response: {performance['avg_response_time']:.2f}s")

def display_health_metrics():
    """Display detailed health metrics"""
    print("\n🏥 SYSTEM HEALTH METRICS:")
    print(f"  CPU Usage: {system_health.cpu_usage:.1f}%")
    print(f"  Memory Usage: {system_health.memory_usage:.1f}%")
    print(f"  Disk Usage: {system_health.disk_usage:.1f}%")
    print(f"  API Response Time: {system_health.api_response_time:.2f}s")
    print(f"  Network Status: {system_health.network_status}")
    print(f"  TTS Status: {system_health.tts_status}")
    print(f"  Error Count: {system_health.error_count}")
    print(f"  Last Health Check: {system_health.last_check.strftime('%H:%M:%S')}")

def display_decision_history(args: str):
    """Display decision history with enhanced formatting"""
    try:
        count = int(args) if args else 10
        count = min(count, len(decision_history))
    except ValueError:
        count = 10
    
    print(f"\n📜 LAST {count} DECISIONS:")
    print("-" * 80)
    
    if not decision_history:
        print("  No decisions recorded yet.")
        return
    
    recent_decisions = list(decision_history)[-count:]
    for i, decision in enumerate(recent_decisions, 1):
        timestamp = decision["timestamp"]
        if hasattr(timestamp, 'strftime'):
            time_str = timestamp.strftime('%m/%d %H:%M')
        else:
            time_str = str(timestamp)[:16]
        
        verdict_icon = {"APPROVE": "✅", "DENY": "❌", "ABSTAIN": "⚪", "ERROR": "⚠️"}.get(decision["verdict"], "❓")
        
        print(f"{i:2d}. [{time_str}] {verdict_icon} {decision['verdict']} - {decision['query'][:50]}...")
        
        if decision.get("individual_votes"):
            votes_summary = ", ".join([f"{name}: {vote.get('vote', 'N/A')}" for name, vote in decision["individual_votes"].items()])
            print(f"     Votes: {votes_summary}")
        print()

def handle_console_export(args: str):
    """Handle export command"""
    if not args or args.lower() not in ["json", "csv", "txt"]:
        print("Usage: export <json|csv|txt>")
        return
    
    try:
        filename = export_decisions(args.lower())
        print(f"✅ Decisions exported to: {filename}")
    except Exception as e:
        print(f"❌ Export failed: {e}")
        log(f"Export failed: {e}", LogLevel.ERROR, "CONSOLE")

def display_configuration():
    """Display current configuration"""
    print("\n⚙️  SYSTEM CONFIGURATION:")
    print(f"  Theme: {CONFIG['system']['theme']} ({THEME_DEFINITIONS[CONFIG['system']['theme']]['name']})")
    print(f"  LLM Provider: {CONFIG['llm']['provider']}")
    print(f"  Base URL: {CONFIG['llm']['base_url']}")
    print(f"  Vote Timeout: {CONFIG['llm']['vote_timeout']}s")
    print(f"  TTS Enabled: {CONFIG['tts']['enabled']}")
    print(f"  Health Monitoring: {CONFIG['health']['enabled']}")
    
    print("\n🧠 MONOLITH MODELS:")
    for name, config in CONFIG["monoliths"].items():
        print(f"  {name}:")
        print(f"    Model: {config['model']}")
        print(f"    Specialty: {config['specialty']}")
        print(f"    Temperature: {config['temperature']}")

def handle_theme_change(args: str):
    """Handle theme change command"""
    themes = list(THEME_DEFINITIONS.keys())
    
    if not args:
        print("\n🎨 Available themes:")
        for i, theme in enumerate(themes):
            current = " (current)" if theme == CONFIG['system']['theme'] else ""
            print(f"  {i}: {theme} - {THEME_DEFINITIONS[theme]['name']}{current}")
        return
    
    try:
        if args.isdigit():
            theme_index = int(args)
            if 0 <= theme_index < len(themes):
                CONFIG["system"]["theme"] = themes[theme_index]
                save_system_config()
                print(f"✅ Theme changed to: {themes[theme_index]} ({THEME_DEFINITIONS[themes[theme_index]]['name']})")
            else:
                print(f"❌ Invalid theme index. Choose 0-{len(themes)-1}")
        else:
            # Try to find theme by name
            theme_name = args.lower()
            if theme_name in themes:
                CONFIG["system"]["theme"] = theme_name
                save_system_config()
                print(f"✅ Theme changed to: {theme_name} ({THEME_DEFINITIONS[theme_name]['name']})")
            else:
                print(f"❌ Unknown theme: {args}")
    except ValueError:
        print("❌ Invalid theme selection. Use 'theme' without args to see available themes.")

def display_console_help():
    """Display enhanced console help"""
    print("\n📖 CONSENSUS CONSOLE HELP:")
    print("┌─ VOTING COMMANDS ────────────────────────────────────────────────────────┐")
    print("│ vote <query>    - Submit query to AI tribunal for consensus decision     │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ SYSTEM COMMANDS ────────────────────────────────────────────────────────┐")
    print("│ status          - Show system operational status and monolith health     │")
    print("│ health          - Display detailed system health metrics                 │")
    print("│ config          - Display current system configuration                   │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ DATA COMMANDS ──────────────────────────────────────────────────────────┐")
    print("│ history [N]     - Show last N decisions (default: 10)                   │")
    print("│ export <format> - Export decision history (json, csv, txt)               │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ UI COMMANDS ────────────────────────────────────────────────────────────┐")
    print("│ theme [N|name]  - Change UI theme (use without args to list themes)      │")
    print("│ help            - Show this help message                                 │")
    print("│ quit            - Exit console mode                                      │")
    print("└───────────────────────────────────────────────────────────────────────────┘")

def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.json"
        export_data = {
            "export_metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "build_hash": BUILD_HASH,
                "total_decisions": len(decision_history),
                "export_format": "json"
            },
            "decisions": [
                {
                    **{k: v for k, v in decision.items() if k != "timestamp"},
                    "timestamp": decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Timestamp", "Decision_ID", "Query", "Consensus", "Confidence",
                "Session_ID", "System_Mode", "Theme", "Version"
            ])
            
            # Write data
            for decision in decision_history:
                timestamp_str = decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                
                writer.writerow([
                    timestamp_str,
                    decision.get("id", ""),
                    decision["query"],
                    decision["verdict"],
                    f"{decision.get('confidence', 0.0):.2f}",
                    decision.get("session_id", ""),
                    decision.get("system_state", {}).get("mode", ""),
                    decision.get("system_state", {}).get("theme", ""),
                    decision.get("system_state", {}).get("version", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"System Version: {VERSION} (Build: {BUILD_HASH})\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 60 + "\n\n")
            
            # Individual decisions
            for i, decision in enumerate(decision_history, 1):
                timestamp_str = decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                
                f.write(f"DECISION #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"ID: {decision.get('id', 'N/A')}\n")
                f.write(f"Timestamp: {timestamp_str}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Consensus: {decision['verdict']}\n")
                f.write(f"Confidence: {decision.get('confidence', 0.0):.0%}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                # Individual votes
                if decision.get("individual_votes"):
                    f.write("\nIndividual Monolith Votes:\n")
                    for monolith, vote_data in decision["individual_votes"].items():
                        vote_val = vote_data.get('vote', 'N/A') if isinstance(vote_data, dict) else str(vote_data)
                        f.write(f"  {monolith}: {vote_val}\n")
                
                # System state
                if decision.get("system_state"):
                    state = decision["system_state"]
                    f.write(f"\nSystem State: Mode={state.get('mode', 'N/A')}, Theme={state.get('theme', 'N/A')}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    log(f"Decisions exported to {filename} ({format_type.upper()} format)", LogLevel.INFO, "EXPORT")
    return str(filename)

def demo_voting_process():
    """Enhanced demo voting process with sample queries"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?",
        "Grant clearance for classified data access request?",
        "Execute contingency plan for system failover scenario?",
        "Authorize resource allocation for mission-critical objectives?"
    ]
    
    query = random.choice(queries)
    log(f"Demo vote initiated: {query}", LogLevel.INFO, "DEMO")
    
    # Create orchestrator and execute vote
    orchestrator = VotingOrchestrator()
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Log results
    log(f"Demo vote complete: {consensus.value} (confidence: {confidence:.2f})", LogLevel.INFO, "DEMO")
    
    # Display results in console if available
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print(f"\n🎮 DEMO VOTE RESULTS:")
        print(f"Query: {query}")
        print(f"Consensus: {consensus.value}")
        print(f"Confidence: {confidence:.0%}")
        print("-" * 50)

def summarize_consensus(consensus: VoteResult, votes: Dict[str, VoteData], reasoning: str):
    """Enhanced consensus summary with typing effect and detailed analysis"""
    print("\n" + "=" * 80)
    print("TRIBUNAL CONSENSUS ANALYSIS")
    print("=" * 80)
    
    # Typing effect for dramatic presentation
    def type_text(text, delay=0.02):
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()
    
    # Main verdict
    print("\nFINAL VERDICT:")
    verdict_text = f"The AI Tribunal has reached consensus: {consensus.value}"
    type_text(verdict_text, 0.03)
    
    # Individual analysis
    print("\nMONOLITH ANALYSIS:")
    for name, vote_data in votes.items():
        if vote_data.vote != VoteResult.ERROR:
            vote_icon = {"APPROVE": "✓", "DENY": "✗", "ABSTAIN": "○"}.get(vote_data.vote.value, "?")
            analysis = f"  {vote_icon} {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})"
            type_text(analysis, 0.01)
            
            # Show specialty reasoning
            specialty = CONFIG["monoliths"][name]["specialty"].replace("_", " ").title()
            type_text(f"    Specialty: {specialty}", 0.01)
            
            # Brief reasoning excerpt
            brief_reasoning = vote_data.reasoning[:80] + "..." if len(vote_data.reasoning) > 80 else vote_data.reasoning
            type_text(f"    Reasoning: {brief_reasoning}", 0.005)
    
    # Consensus strength analysis
    print("\nCONSENSUS ANALYSIS:")
    approve_count = sum(1 for v in votes.values() if v.vote == VoteResult.APPROVE)
    deny_count = sum(1 for v in votes.values() if v.vote == VoteResult.DENY)
    abstain_count = sum(1 for v in votes.values() if v.vote == VoteResult.ABSTAIN)
    
    strength = "Strong" if max(approve_count, deny_count, abstain_count) == 3 else "Majority"
    type_text(f"  Consensus Strength: {strength}", 0.02)
    type_text(f"  Vote Distribution: {approve_count} Approve, {deny_count} Deny, {abstain_count} Abstain", 0.02)
    
    # Response time analysis
    avg_response = sum(v.response_time for v in votes.values()) / len(votes)
    type_text(f"  Average Response Time: {avg_response:.2f}s", 0.02)
    
    print("=" * 80)

def handle_input(stdscr, key: int) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
    elif key in (ord('m'), ord('M')):
        CONFIG["system"]["current_view"] = "main"
    elif key in (ord('v'), ord('V')):
        # Trigger demo voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('7')):
        # Toggle decision history view (Key 7 functionality)
        if CONFIG["system"]["current_view"] == "history":
            CONFIG["system"]["current_view"] = "main"
        else:
            CONFIG["system"]["current_view"] = "history"
    elif key in (ord('h'), ord('H')):
        # Show help (placeholder)
        add_notification("Help system: Press 7 for history, S for themes, V for demo vote", NotificationLevel.INFO)
    
    return True

def run_ui_loop(stdscr):
    """Enhanced main UI loop with multiple views"""
    # Initialize curses
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    # Initialize color pairs
    if curses.has_colors():
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
    
    running = True
    last_refresh = 0
    
    while running:
        try:
            # Handle input
            key = stdscr.getch()
            if key != -1:
                if key == ord('c') or key == ord('C'):
                    # Special handling for console mode transition
                    stdscr.clear()
                    stdscr.addstr(0, 0, "Entering console mode...")
                    stdscr.refresh()
                    curses.endwin()
                    run_console_mode()
                    # Re-initialize curses after console mode
                    stdscr = curses.initscr()
                    curses.start_color()
                    curses.use_default_colors()
                    curses.noecho()
                    curses.cbreak()
                    stdscr.keypad(True)
                    stdscr.nodelay(1)
                    stdscr.timeout(100)
                    if curses.has_colors():
                        for i in range(1, 8):
                            curses.init_pair(i, i, -1)
                else:
                    running = handle_input(stdscr, key)
            
            # Refresh screen periodically
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                # Render current view
                current_view = CONFIG["system"]["current_view"]
                if current_view == "history":
                    render_decision_history(stdscr)
                else:
                    render_main_screen(stdscr, CONFIG["system"]["theme"])
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"UI loop error: {e}", LogLevel.ERROR, "UI")
            add_notification(f"UI error: {str(e)}", NotificationLevel.ERROR)

def main():
    """Main entry point with enhanced error handling and startup sequence"""
    try:
        # Show enhanced boot sequence
        show_boot_sequence()
        
        # Initialize system
        initialize_system()
        
        # Add startup notifications
        add_notification("All monoliths initialized", NotificationLevel.INFO)
        add_notification("System ready for operation", NotificationLevel.SUCCESS)
        
        # Mode selection with enhanced interface
        print("\n" + "="*80)
        print("CONSENSUS SYSTEM - OPERATIONAL MODE SELECTION")
        print("="*80)
        print("1. 🖥️  GUI Mode      - Full interface with real-time monitoring")
        print("2. 💻 Console Mode   - Direct command-line operation")
        print("3. 🎮 Demo Mode      - Automated demonstration")
        print("4. 🚪 Exit System    - Terminate CONSENSUS")
        print("="*80)
        
        while True:
            choice = input("\n🎯 Select operational mode (1-4): ").strip()
            
            if choice == "1":
                log("Starting GUI mode", LogLevel.INFO, "MODE")
                try:
                    print("\n🖥️  Launching GUI interface...")
                    curses.wrapper(run_ui_loop)
                except Exception as e:
                    log(f"GUI mode error: {e}", LogLevel.ERROR, "MODE")
                    print(f"❌ GUI mode failed: {e}")
                    print("💡 Try console mode instead...")
                break
            elif choice == "2":
                log("Starting console mode", LogLevel.INFO, "MODE")
                print("\n💻 Entering console mode...")
                run_console_mode()
                break
            elif choice == "3":
                log("Starting demo mode", LogLevel.INFO, "MODE")
                print("\n🎮 Running demonstration...")
                demo_voting_process()
                print("\n✅ Demo complete!")
                break
            elif choice == "4":
                log("User requested exit", LogLevel.INFO, "MODE")
                print("\n🚪 Terminating CONSENSUS System...")
                break
            else:
                print("❌ Invalid selection. Please choose 1-4.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  System interrupted by user.")
        log("System interrupted by user", LogLevel.WARNING, "MAIN")
    except Exception as e:
        error_msg = f"Fatal system error: {e}"
        print(f"\n❌ {error_msg}")
        log(error_msg, LogLevel.CRITICAL, "MAIN")
        log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "MAIN")
        sys.exit(1)
    finally:
        # Cleanup and enhanced shutdown
        uptime = get_system_uptime()
        log(f"CONSENSUS System shutting down after {uptime} uptime", LogLevel.SHUTDOWN, "MAIN")
        
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        SYSTEM SHUTDOWN COMPLETE                            ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print(f"🟢 CONSENSUS System terminated gracefully")
        print(f"📊 Session summary: {len(decision_history)} decisions processed")
        print(f"⏱️  Total uptime: {uptime}")
        
        if decision_history:
            last_decision = decision_history[-1]
            last_time = last_decision["timestamp"]
            if hasattr(last_time, 'strftime'):
                time_str = last_time.strftime('%H:%M:%S')
            else:
                time_str = str(last_time)
            print(f"🕒 Last decision: {time_str} - {last_decision['verdict']}")
        
        print(f"\n🔒 All systems secured. Have a great day, Commander.")

if __name__ == "__main__":
    main()
                    system_health.network_status = "operational"
                    system_health.api_response_time = response.elapsed.total_seconds()
                else:
                    system_health.network_status = "degraded"
            except Exception:
                system_health.network_status = "unavailable"
                system_health.api_response_time = 999.0
            
            # TTS status
            if CONFIG["tts"]["enabled"]:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    system_health.tts_status = "operational"
                    engine.stop()
                    del engine
                except Exception:
                    system_health.tts_status = "unavailable"
            else:
                system_health.tts_status = "disabled"
            
            # Update timestamp and uptime
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except ImportError:
        log("psutil not available - using simulated health metrics", LogLevel.WARNING, "HEALTH")
        # Simulated values when psutil not available
        with health_lock:
            system_health.cpu_usage = random.uniform(10, 40)
            system_health.memory_usage = random.uniform(30, 70)
            system_health.disk_usage = random.uniform(20, 80)
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except Exception as e:
        log(f"Health check failed: {e}", LogLevel.ERROR, "HEALTH")
        system_health.error_count += 1

class EnhancedMonolith:
    """Enhanced monolith with specialized analysis capabilities"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = CONFIG["monoliths"][name]
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        self.status = "unknown"
        self.last_check = None
        self.error_count = 0
        self.total_votes = 0
        self.response_times = deque(maxlen=50)
        
    def check_model_status(self) -> str:
        """Check if the model is available and loaded"""
        try:
            provider = CONFIG["llm"]["provider"]
            
            if provider == "ollama":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_name = self.config["model"]
                    
                    for model in models:
                        if model["name"] == model_name:
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            elif provider == "lmstudio":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/v1/models",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    model_name = self.config["model"].split(":")[0].lower()
                    
                    for model in models:
                        if model_name in model["id"].lower():
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            else:
                self.status = "unknown_provider"
                return "unknown_provider"
                
        except Exception as e:
            log(f"[{self.name}] Status check failed: {e}", LogLevel.ERROR, "MONOLITH")
            self.status = "unreachable"
            self.error_count += 1
            return "unreachable"
    
    def cast_vote(self, query: str, session_id: str) -> VoteData:
        """Cast a vote with enhanced error handling and metrics"""
        start_time = time.time()
        
        try:
            log(f"[{self.name}] Casting vote for session {session_id}", LogLevel.INFO, "VOTE", session_id)
            
            # Check model status first
            if self.status != "ready":
                status = self.check_model_status()
                if status != "ready":
                    raise Exception(f"Model not ready: {status}")
            
            # Prepare prompt
            full_prompt = f"{self.config['prompt']}\n\nQUERY: {query}\n\nVOTE:"
            
            # Make API call
            response = self._call_api(full_prompt)
            response_time = time.time() - start_time
            
            # Parse response
            parsed_vote, confidence = self._parse_response(response)
            
            # Create vote data
            vote_data = VoteData(
                monolith=self.name,
                query=query,
                vote=parsed_vote,
                reasoning=response,
                confidence=confidence,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
            
            # Save vote
            self._save_vote(vote_data)
            
            # Update metrics
            self.total_votes += 1
            self.response_times.append(response_time)
            
            log(f"[{self.name}] Vote cast: {parsed_vote.value} (confidence: {confidence:.2f}, time: {response_time:.2f}s)", 
                LogLevel.INFO, "VOTE", session_id)
            
            return vote_data
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Vote failed: {str(e)}"
            
            log(f"[{self.name}] {error_msg}", LogLevel.ERROR, "VOTE", session_id)
            self.error_count += 1
            
            # Return error vote
            return VoteData(
                monolith=self.name,
                query=query,
                vote=VoteResult.ERROR,
                reasoning=error_msg,
                confidence=0.0,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
    
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM provider"""
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/api/generate",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        elif provider == "lmstudio":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/v1/completions",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:

# ================================================================================
#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v3.7.0)
Complete refactored implementation with clean modular architecture.

Features:
- Three specialized AI monoliths (RATIONALIS, AETERNUM, BELLATOR)
- Enhanced voting consensus algorithm with probabilistic scoring
- Multiple UI themes with tactical aesthetics
- Comprehensive decision logging and analytics
- Text-to-speech verdict announcements
- Dual-mode operation (GUI/Console)

Author: AI Assistant & Human Collaboration
Version: 3.7.0
Date: May 2025
"""

import statistics
from collections import deque, defaultdict, Counter

# ================================================================================
# MODULE 1: System Constants & Configuration
# ================================================================================

# Version Information
VERSION = "3.7.0"
BUILD_DATE = "2025-05-19"
BUILD_HASH = hashlib.md5(f"{VERSION}{BUILD_DATE}".encode()).hexdigest()[:8]

# System Paths
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
BACKUP_DIR = ARBITER_DIR / "backups"
CONFIG_PATH = ARBITER_DIR / "config.json"
DECISION_HISTORY_PATH = ARBITER_DIR / "decision_history.json"

# Enums
class SystemMode(Enum):
    READY = "READY"
    VOTING = "VOTING"
    ANALYZING = "ANALYZING"
    CONSENSUS = "CONSENSUS"
    DEADLOCK = "DEADLOCK"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"
    CRITICAL = "CRITICAL"

class VoteResult(Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    CONDITIONAL = "CONDITIONAL"
    ESCALATE = "ESCALATE"
    ERROR = "ERROR"

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"
    VOTE = "VOTE"
    CONSENSUS = "CONSENSUS"
    DECISION = "DECISION"
    ANALYTICS = "ANALYTICS"

# Data Structures
@dataclass
class VoteData:
    monolith: str
    query: str
    vote: VoteResult
    reasoning: str
    confidence: float
    response_time: float
    timestamp: datetime.datetime
    session_id: str

# ASCII Art & Themes
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

THEME_DEFINITIONS = {
    "military": {
        "name": "Military HQ",
        "box_chars": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
        "colors": {"primary": 2, "secondary": 3, "accent": 6, "warning": 1}
    },
    "tars": {
        "name": "TARS Interface",
        "box_chars": {"tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦", "h": "⎯", "v": "⎮"},
        "colors": {"primary": 4, "secondary": 6, "accent": 7, "warning": 3}
    },
    "eva": {
        "name": "Evangelion MAGI",
        "box_chars": {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "v": "▌"},
        "colors": {"primary": 5, "secondary": 1, "accent": 3, "warning": 6}
    },
    "wh40k": {
        "name": "Imperial Gothic",
        "box_chars": {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
        "colors": {"primary": 6, "secondary": 3, "accent": 2, "warning": 1}
    },
    "helldivers": {
        "name": "Super Earth Command",
        "box_chars": {"tl": "◢", "tr": "◣", "bl": "◥", "br": "◤", "h": "━", "v": "┃"},
        "colors": {"primary": 2, "secondary": 4, "accent": 6, "warning": 1}
    }
}

# System Configuration
DEFAULT_CONFIG = {
    "system": {
        "theme": "military",
        "current_view": "main",
        "system_mode": SystemMode.READY.value,
        "debug_mode": False,
        "max_log_entries": 1000,
        "max_decisions": 100
    },
    "llm": {
        "provider": "ollama",
        "api_timeout": 30,
        "vote_timeout": 45,
        "max_retries": 3,
        "base_url": "http://localhost:11434",
        "enable_parallel_processing": True
    },
    "monoliths": {
        "RATIONALIS": {
            "model": "deepseek-coder:33b",
            "prompt": "You are RATIONALIS, the logic engine of the CONSENSUS Tribunal. Analyze the query with pure logical reasoning and structured analysis. Provide your verdict with detailed logical justification.",
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024,
            "specialty": "logical_analysis"
        },
        "AETERNUM": {
            "model": "llama3:70b",
            "prompt": "You are AETERNUM, the temporal analyst and market sage of the CONSENSUS Tribunal. Analyze patterns, historical precedents, and market implications with your vast temporal knowledge.",
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024,
            "specialty": "pattern_analysis"
        },
        "BELLATOR": {
            "model": "mixtral:8x7b",
            "prompt": "You are BELLATOR, the tactical strategist and risk assessor of the CONSENSUS Tribunal. Evaluate security implications, tactical risks, and strategic outcomes with military precision.",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "specialty": "risk_assessment"
        }
    },
    "tts": {
        "enabled": True,
        "engine": "pyttsx3",
        "voice_rate": 150,
        "voice_volume": 0.9,
        "announce_decisions": True,
        "announce_bias_alerts": True,
        "emotional_modulation": True
    },
    "health": {
        "enabled": True,
        "check_interval": 5,
        "api_timeout": 3,
        "alert_thresholds": {
            "cpu": 90.0,
            "memory": 85.0,
            "response_time": 10.0
        }
    },
    "ui": {
        "refresh_rate": 10,
        "animation_speed": 50,
        "show_debug": False,
        "color_scheme": "default"
    }
}

# Global State
CONFIG = DEFAULT_CONFIG.copy()
log_entries = deque(maxlen=1000)
decision_history = deque(maxlen=100)
notifications = deque(maxlen=15)
active_votes = {}
startup_time = time.time()

# ================================================================================
# MODULE 2: Boot Sequence & Initialization
# ================================================================================

def show_boot_sequence():
    """Display enhanced boot sequence with NERV logo"""
    os.system("cls" if os.name == "nt" else "clear")
    print(NERV_LOGO)
    time.sleep(1.5)
    
    print(CONSENSUS_LOGO)
    time.sleep(0.8)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    init_steps = [
        ("Checking system resources", [
            "CPU availability", "Memory alignment", "Storage capacity", "Display capabilities"
        ]),
        ("Initializing AI cores", [
            "RATIONALIS logic engine", "AETERNUM temporal analyst", "BELLATOR tactical assessor"
        ]),
        ("Establishing network", [
            "API endpoints", "Model connections", "Health monitoring", "TTS integration"
        ]),
        ("Loading interface", [
            "Theme system", "Command parser", "Display engine", "Control bindings"
        ]),
        ("Finalizing startup", [
            "Configuration validation", "Log system", "Decision tracking", "Ready state"
        ])
    ]
    
    for step_name, substeps in init_steps:
        print(f"\n◢◣ {step_name}...")
        time.sleep(0.4)
        for substep in substeps:
            print(f"  ├─ {substep}{'.' * (35 - len(substep))} [✓]")
            time.sleep(0.3)
        time.sleep(0.2)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    print(f"""
\033[1;33m▶ Control Keys:\033[0m
  - \033[1;36mQ\033[0m: Quit system         - \033[1;36mM\033[0m: Main view
  - \033[1;36mS\033[0m: Cycle themes        - \033[1;36mV\033[0m: Vote demo
  - \033[1;36mC\033[0m: Console mode        - \033[1;36m9\033[0m: Diagnostics
  - \033[1;36mH\033[0m: Help system         - \033[1;36m7\033[0m: Decision history

def initialize_system():
    """Initialize the CONSENSUS system directories and configuration"""
    try:
        for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR, EXPORT_DIR, BACKUP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        load_system_config()
        log("CONSENSUS System initialization started", LogLevel.STARTUP)
        log(f"Version: {VERSION}, Build: {BUILD_HASH}", LogLevel.STARTUP)
        
        load_decision_history()
        
        if CONFIG["health"]["enabled"]:
            threading.Thread(target=health_monitor_daemon, daemon=True).start()
            log("Health monitoring daemon started", LogLevel.INFO)
        
        log("System initialization completed successfully", LogLevel.STARTUP)
        add_notification("CONSENSUS System Online", NotificationLevel.SUCCESS)
        
    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        log(error_msg, LogLevel.CRITICAL)
        print(f"FATAL ERROR: {error_msg}")
        sys.exit(1)

# ================================================================================
# MODULE 3: Logging System  
# ================================================================================

def log(message: str, level: LogLevel = LogLevel.INFO, component: str = "SYSTEM", session_id: str = None):
    """Enhanced logging with component tracking and structured format"""
    timestamp = datetime.datetime.now()
    
    entry = {
        "timestamp": timestamp,
        "level": level.value,
        "component": component,
        "message": message,
        "session_id": session_id,
        "thread": threading.current_thread().name
    }
    
    with log_lock:
        log_entries.append(entry)
    
    session_part = f" [{session_id}]" if session_id else ""
    formatted_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [{level.value:8}] [{component:12}]{session_part} {message}"
    
    try:
        log_file = LOG_DIR / f"{timestamp.strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{formatted_entry}\n")
    except Exception as e:
        print(f"Failed to write log: {e}")

# ================================================================================
# MODULE 4: Configuration Management
# ================================================================================

def load_system_config():
    """Load system configuration with validation and migration"""
    global CONFIG
    
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            CONFIG = merge_configs(DEFAULT_CONFIG, loaded_config)
            log("Configuration loaded successfully", LogLevel.INFO, "CONFIG")
        else:
            CONFIG = DEFAULT_CONFIG.copy()
            save_system_config()
            log("Default configuration created", LogLevel.INFO, "CONFIG")
            
    except Exception as e:
        log(f"Failed to load configuration: {e}", LogLevel.ERROR, "CONFIG")
        CONFIG = DEFAULT_CONFIG.copy()

def save_system_config():
    """Save current configuration to file"""
    try:
        if CONFIG_PATH.exists():
            backup_path = BACKUP_DIR / f"config_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import shutil
            shutil.copy2(CONFIG_PATH, backup_path)
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=2, default=str)
        
        log("Configuration saved successfully", LogLevel.INFO, "CONFIG")
        
    except Exception as e:
        log(f"Failed to save configuration: {e}", LogLevel.ERROR, "CONFIG")

# ================================================================================
# MODULE 5: Health Monitoring
# ================================================================================

def update_system_health():
    """Comprehensive system health check"""
    global system_health
    
    try:
        import psutil
        
        with health_lock:
            system_health.cpu_usage = psutil.cpu_percent(interval=0.1)
            system_health.memory_usage = psutil.virtual_memory().percent
            system_health.disk_usage = psutil.disk_usage('/').percent
            
            try:
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                if response.status_code == 200:
                    system_health.network_status = "operational"
                    system_health.api_response_time = response.elapsed.total_seconds()
                else:
                    system_health.network_status = "degraded"
            except:
                system_health.network_status = "unavailable"
                system_health.api_response_time = 999.0
            
            if CONFIG["tts"]["enabled"]:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    system_health.tts_status = "operational"
                    engine.stop()
                    del engine
                except:
                    system_health.tts_status = "unavailable"
            else:
                system_health.tts_status = "disabled"
            
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except ImportError:
        log("psutil not available - using simulated health metrics", LogLevel.WARNING, "HEALTH")
        with health_lock:
            system_health.cpu_usage = random.uniform(10, 40)
            system_health.memory_usage = random.uniform(30, 70)
            system_health.disk_usage = random.uniform(20, 80)
            system_health.last_check = datetime.datetime.now()
            system_health.uptime = time.time() - startup_time
    
    except Exception as e:
        log(f"Health check failed: {e}", LogLevel.ERROR, "HEALTH")
        system_health.error_count += 1

def health_monitor_daemon():
    """Background health monitoring daemon"""
    while True:
        try:
            update_system_health()
            
            if CONFIG["health"]["enabled"]:
                thresholds = CONFIG["health"]["alert_thresholds"]
                
                if system_health.cpu_usage > thresholds["cpu"]:
                    add_notification(f"High CPU usage: {system_health.cpu_usage:.1f}%", NotificationLevel.WARNING)
                
                if system_health.memory_usage > thresholds["memory"]:
                    add_notification(f"High memory usage: {system_health.memory_usage:.1f}%", NotificationLevel.WARNING)
                
                if system_health.api_response_time > thresholds["response_time"]:
                    add_notification(f"Slow API response: {system_health.api_response_time:.2f}s", NotificationLevel.WARNING)
            
            time.sleep(CONFIG["health"]["check_interval"])
            
        except Exception as e:
            log(f"Health monitor daemon error: {e}", LogLevel.ERROR, "HEALTH")
            time.sleep(30)

# ================================================================================
# MODULE 6: Enhanced Monolith System
# ================================================================================

class EnhancedMonolith:
    """Enhanced monolith with specialized analysis capabilities"""
    
    def __init__(self, name: str):
        self.name = name
        self.config = CONFIG["monoliths"][name]
        self.vote_file = VOTE_DIR / f"{name.lower()}_vote.json"
        self.status = "unknown"
        self.last_check = None
        self.error_count = 0
        self.total_votes = 0
        self.response_times = deque(maxlen=50)
        
    def check_model_status(self) -> str:
        """Check if the model is available and loaded"""
        try:
            provider = CONFIG["llm"]["provider"]
            
            if provider == "ollama":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/api/tags",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_name = self.config["model"]
                    
                    for model in models:
                        if model["name"] == model_name:
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            elif provider == "lmstudio":
                response = requests.get(
                    f"{CONFIG['llm']['base_url']}/v1/models",
                    timeout=CONFIG['health']['api_timeout']
                )
                
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    model_name = self.config["model"].split(":")[0].lower()
                    
                    for model in models:
                        if model_name in model["id"].lower():
                            self.status = "ready"
                            self.last_check = datetime.datetime.now()
                            return "ready"
                    
                    self.status = "not_loaded"
                    return "not_loaded"
                else:
                    self.status = "service_error"
                    return "service_error"
            
            else:
                self.status = "unknown_provider"
                return "unknown_provider"
                
        except Exception as e:
            log(f"[{self.name}] Status check failed: {e}", LogLevel.ERROR, "MONOLITH")
            self.status = "unreachable"
            self.error_count += 1
            return "unreachable"
    
    def cast_vote(self, query: str, session_id: str) -> VoteData:
        """Cast a vote with enhanced error handling and metrics"""
        start_time = time.time()
        
        try:
            log(f"[{self.name}] Casting vote for session {session_id}", LogLevel.INFO, "VOTE", session_id)
            
            if self.status != "ready":
                status = self.check_model_status()
                if status != "ready":
                    raise Exception(f"Model not ready: {status}")
            
            full_prompt = f"{self.config['prompt']}\n\nQUERY: {query}\n\nVOTE:"
            
            response = self._call_api(full_prompt)
            response_time = time.time() - start_time
            
            parsed_vote, confidence = self._parse_response(response)
            
            vote_data = VoteData(
                monolith=self.name,
                query=query,
                vote=parsed_vote,
                reasoning=response,
                confidence=confidence,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
            
            self._save_vote(vote_data)
            
            self.total_votes += 1
            self.response_times.append(response_time)
            
            log(f"[{self.name}] Vote cast: {parsed_vote.value} (confidence: {confidence:.2f}, time: {response_time:.2f}s)", 
                LogLevel.INFO, "VOTE", session_id)
            
            return vote_data
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Vote failed: {str(e)}"
            
            log(f"[{self.name}] {error_msg}", LogLevel.ERROR, "VOTE", session_id)
            self.error_count += 1
            
            return VoteData(
                monolith=self.name,
                query=query,
                vote=VoteResult.ERROR,
                reasoning=error_msg,
                confidence=0.0,
                response_time=response_time,
                timestamp=datetime.datetime.now(),
                session_id=session_id
            )
    
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM provider"""
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "top_p": self.config["top_p"],
                    "num_predict": self.config["max_tokens"]
                }
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/api/generate",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        elif provider == "lmstudio":
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "temperature": self.config["temperature"],
                "top_p": self.config["top_p"],
                "max_tokens": self.config["max_tokens"]
            }
            
            response = requests.post(
                f"{CONFIG['llm']['base_url']}/v1/completions",
                json=payload,
                timeout=CONFIG["llm"]["api_timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "")
            else:
                raise Exception(f"API error: {response.status_code}")
        
        else:
            raise Exception(f"Unknown provider: {provider}")
    
    def _parse_response(self, response: str) -> Tuple[VoteResult, float]:
        """Parse LLM response to extract vote and confidence"""
        response_upper = response.upper()
        
        if "APPROVE" in response_upper:
            vote = VoteResult.APPROVE
        elif "DENY" in response_upper:
            vote = VoteResult.DENY
        elif "ABSTAIN" in response_upper:
            vote = VoteResult.ABSTAIN
        elif "CONDITIONAL" in response_upper:
            vote = VoteResult.CONDITIONAL
        else:
            vote = VoteResult.ERROR
        
        confidence = min(0.95, max(0.1, 
            0.7 + 0.2 * (len(response) / 500) + 
            0.1 * (response.count(".") / max(1, len(response.split())))
        ))
        
        return vote, confidence
    
    def _save_vote(self, vote_data: VoteData):
        """Save vote to file"""
        try:
            with open(self.vote_file, 'w', encoding='utf-8') as f:
                vote_dict = asdict(vote_data)
                vote_dict["timestamp"] = vote_data.timestamp.isoformat()
                vote_dict["vote"] = vote_data.vote.value
                json.dump(vote_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"[{self.name}] Failed to save vote: {e}", LogLevel.ERROR, "VOTE")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this monolith"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        
        return {
            "status": self.status,
            "total_votes": self.total_votes,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.total_votes),
            "avg_response_time": avg_response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "specialty": self.config["specialty"],
            "model": self.config["model"]
        }

# ================================================================================
# MODULE 7: Consensus Engine
# ================================================================================

class ConsensusEngine:
    """Enhanced consensus calculation and analysis engine"""
    
    @staticmethod
    def calculate_consensus(votes: Dict[str, VoteData]) -> Tuple[VoteResult, float, str]:
        """Calculate consensus with confidence and reasoning"""
        vote_counts = defaultdict(int)
        total_confidence = 0.0
        total_votes = 0
        reasoning_parts = []
        
        for monolith, vote_data in votes.items():
            if vote_data.vote != VoteResult.ERROR:
                vote_counts[vote_data.vote] += 1
                total_confidence += vote_data.confidence
                total_votes += 1
                
                reasoning_snippet = vote_data.reasoning[:100] + "..." if len(vote_data.reasoning) > 100 else vote_data.reasoning
                reasoning_parts.append(f"{monolith}: {vote_data.vote.value} - {reasoning_snippet}")
        
        if total_votes == 0:
            return VoteResult.ERROR, 0.0, "No valid votes received"
        
        approve_count = vote_counts[VoteResult.APPROVE]
        deny_count = vote_counts[VoteResult.DENY]
        abstain_count = vote_counts[VoteResult.ABSTAIN]
        conditional_count = vote_counts[VoteResult.CONDITIONAL]
        
        # Enhanced consensus logic
        if approve_count >= 2:
            consensus = VoteResult.APPROVE
        elif deny_count >= 2:
            consensus = VoteResult.DENY
        elif conditional_count >= 2:
            consensus = VoteResult.CONDITIONAL
        elif approve_count == deny_count == 1 and abstain_count == 1:
            consensus = VoteResult.ABSTAIN
        else:
            consensus = VoteResult.ERROR  # Deadlock
        
        # Calculate consensus confidence
        consensus_confidence = total_confidence / total_votes
        
        # Adjust confidence based on unanimity
        max_count = max(vote_counts.values()) if vote_counts else 0
        if max_count == total_votes:
            consensus_confidence *= 1.2  # Boost for unanimity
        elif max_count >= 2:
            consensus_confidence *= 1.0  # Standard majority
        else:
            consensus_confidence *= 0.8  # Reduce for weak consensus
        
        consensus_confidence = min(0.99, consensus_confidence)
        
        # Create reasoning summary
        reasoning = f"Consensus: {consensus.value} ({max_count}/{total_votes} votes). " + "; ".join(reasoning_parts)
        
        return consensus, consensus_confidence, reasoning
    
    @staticmethod
    def analyze_voting_patterns(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze historical voting patterns"""
        if not decisions:
            return {}
        
        total_decisions = len(decisions)
        verdict_counts = defaultdict(int)
        
        for decision in decisions:
            verdict_counts[decision["verdict"]] += 1
        
        # Calculate metrics
        approval_rate = verdict_counts[VoteResult.APPROVE.value] / total_decisions
        denial_rate = verdict_counts[VoteResult.DENY.value] / total_decisions
        deadlock_rate = verdict_counts[VoteResult.ERROR.value] / total_decisions
        
        # Average confidence
        avg_confidence = sum(d.get("confidence", 0.0) for d in decisions) / total_decisions
        
        return {
            "total_decisions": total_decisions,
            "approval_rate": approval_rate,
            "denial_rate": denial_rate,
            "deadlock_rate": deadlock_rate,
            "average_confidence": avg_confidence,
            "verdict_distribution": dict(verdict_counts)
        }

# ================================================================================
# MODULE 8: Voting Orchestrator
# ================================================================================

class VotingOrchestrator:
    """Orchestrates the voting process between monoliths"""
    
    def __init__(self):
        self.monoliths = {
            name: EnhancedMonolith(name) for name in CONFIG["monoliths"]
        }
        self.consensus_engine = ConsensusEngine()
        self.active_session = None
    
    def initiate_vote(self, query: str, context: Dict[str, Any] = None) -> Tuple[VoteResult, float, str, Dict[str, VoteData]]:
        """Initiate voting process with enhanced session management"""
        session_id = self._generate_session_id(query)
        self.active_session = session_id
        
        log(f"Initiating vote for session {session_id}: {query[:100]}...", LogLevel.INFO, "VOTE", session_id)
        
        CONFIG["system"]["system_mode"] = SystemMode.VOTING.value
        add_notification("AI Tribunal deliberation commenced", NotificationLevel.INFO)
        
        try:
            votes = self._collect_votes(query, session_id)
            
            CONFIG["system"]["system_mode"] = SystemMode.ANALYZING.value
            consensus, confidence, reasoning = self.consensus_engine.calculate_consensus(votes)
            
            # Update system mode based on result
            if consensus == VoteResult.APPROVE:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION GRANTED", NotificationLevel.SUCCESS)
            elif consensus == VoteResult.DENY:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("AUTHORIZATION DENIED", NotificationLevel.WARNING)
            elif consensus == VoteResult.CONDITIONAL:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("CONDITIONAL APPROVAL", NotificationLevel.INFO)
            elif consensus == VoteResult.ABSTAIN:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("TRIBUNAL ABSTAINS", NotificationLevel.INFO)
            else:
                CONFIG["system"]["system_mode"] = SystemMode.DEADLOCK.value
                add_notification("DEADLOCK - Manual intervention required", NotificationLevel.ERROR)
            
            self._record_decision(query, consensus, votes, confidence, reasoning, session_id)
            self._announce_verdict(consensus, confidence)
            
            threading.Timer(10.0, self._reset_mode).start()
            
            log(f"Vote complete - Consensus: {consensus.value}, Confidence: {confidence:.2f}", 
                LogLevel.INFO, "VOTE", session_id)
            
            return consensus, confidence, reasoning, votes
            
        except concurrent.futures.TimeoutError:
            log(f"Vote timed out after {CONFIG['llm']['vote_timeout']}s", LogLevel.ERROR, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification("Vote timeout - System error", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, "Vote timed out", {}
            
        except Exception as e:
            log(f"Vote orchestration failed: {e}", LogLevel.ERROR, "VOTE", session_id)
            log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "VOTE", session_id)
            CONFIG["system"]["system_mode"] = SystemMode.ERROR.value
            add_notification(f"Vote failed: {str(e)}", NotificationLevel.ERROR)
            return VoteResult.ERROR, 0.0, f"Vote failed: {str(e)}", {}
    
    def _generate_session_id(self, query: str) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        query_hash = hashlib.md5(query.encode()).hexdigest()[:6]
        return f"{timestamp}_{query_hash}"
    
    def _collect_votes(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Collect votes from all monoliths with parallel processing"""
        votes = {}
        
        if CONFIG["llm"].get("enable_parallel_processing", True):
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.monoliths)) as executor:
                future_to_monolith = {
                    executor.submit(monolith.cast_vote, query, session_id): name 
                    for name, monolith in self.monoliths.items()
                }
                
                for future in concurrent.futures.as_completed(future_to_monolith, timeout=CONFIG["llm"]["vote_timeout"]):
                    monolith_name = future_to_monolith[future]
                    try:
                        vote_data = future.result()
                        votes[monolith_name] = vote_data
                        
                        active_votes[monolith_name] = vote_data
                        add_notification(f"{monolith_name} deliberation complete", NotificationLevel.INFO)
                        
                    except Exception as e:
                        log(f"Vote collection failed for {monolith_name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        else:
            for name, monolith in self.monoliths.items():
                try:
                    vote_data = monolith.cast_vote(query, session_id)
                    votes[name] = vote_data
                    active_votes[name] = vote_data
                    add_notification(f"{name} deliberation complete", NotificationLevel.INFO)
                except Exception as e:
                    log(f"Sequential vote collection failed for {name}: {e}", LogLevel.ERROR, "VOTE", session_id)
        
        return votes
    
    def _record_decision(self, query: str, consensus: VoteResult, votes: Dict[str, VoteData], 
                        confidence: float, reasoning: str, session_id: str):
        """Record decision with comprehensive metadata"""
        decision_id = hashlib.md5(f"{query}{session_id}{time.time()}".encode()).hexdigest()[:12]
        
        system_state = {
            "theme": CONFIG["system"]["theme"],
            "version": VERSION,
            "build_hash": BUILD_HASH,
            "mode": CONFIG["system"]["system_mode"],
            "uptime": get_system_uptime(),
            "health_score": self._calculate_health_score(),
            "api_status": system_health.network_status,
            "monolith_count": len(self.monoliths)
        }
        
        decision_data = {
            "id": decision_id,
            "query": query,
            "verdict": consensus.value,
            "individual_votes": {
                name: {
                    "vote": vote_data.vote.value,
                    "confidence": vote_data.confidence,
                    "response_time": vote_data.response_time,
                    "reasoning": vote_data.reasoning
                }
                for name, vote_data in votes.items()
            },
            "confidence": confidence,
            "timestamp": datetime.datetime.now(),
            "session_id": session_id,
            "reasoning": reasoning,
            "system_state": system_state
        }
        
        with decision_lock:
            decision_history.append(decision_data)
        
        self._save_decision_history()
        
        log(f"Decision recorded: {consensus.value} for query '{query[:50]}...'", LogLevel.INFO, "DECISION", session_id)
    
    def _announce_verdict(self, consensus: VoteResult, confidence: float):
        """Announce verdict with TTS"""
        if not CONFIG["tts"]["enabled"] or not CONFIG["tts"]["announce_decisions"]:
            return
        
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    if any(keyword in voice_name for keyword in ['zira', 'hazel', 'female']):
                        engine.setProperty('voice', voice.id)
                        break
            
            engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
            engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
            if consensus == VoteResult.APPROVE:
                announcement = f"Consensus achieved. Authorization granted with {confidence:.0%} confidence."
            elif consensus == VoteResult.DENY:
                announcement = f"Consensus achieved. Authorization denied with {confidence:.0%} confidence."
            elif consensus == VoteResult.CONDITIONAL:
                announcement = f"Consensus achieved. Conditional approval granted with {confidence:.0%} confidence."
            elif consensus == VoteResult.ABSTAIN:
                announcement = f"Tribunal abstains from decision with {confidence:.0%} confidence."
            else:
                announcement = "Tribunal deadlocked. Manual intervention required."
            
            engine.say(announcement)
            engine.runAndWait()
            engine.stop()
            
            log(f"TTS announcement completed: {consensus.value}", LogLevel.INFO, "TTS")
            
        except ImportError:
            log("TTS failed: pyttsx3 not installed. Install with: pip install pyttsx3", LogLevel.WARNING, "TTS")
            system_health.tts_status = "unavailable"
        except Exception as e:
            log(f"TTS error: {e}", LogLevel.ERROR, "TTS")
            system_health.tts_status = "error"
    
    def _reset_mode(self):
        """Reset system mode after decision process"""
        CONFIG["system"]["system_mode"] = SystemMode.READY.value
        self.active_session = None
        active_votes.clear()
        log("System mode reset to READY", LogLevel.INFO, "VOTE")
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score"""
        score = 0.85  # Base score
        
        if system_health.network_status == "operational":
            score += 0.1
        elif system_health.network_status == "degraded":
            score -= 0.05
        else:
            score -= 0.2
        
        if system_health.tts_status == "operational":
            score += 0.05
        
        if system_health.error_count == 0:
            score += 0.02
        elif system_health.error_count > 5:
            score -= 0.05
        
        return max(0.0, min(1.0, score))
    
    def _save_decision_history(self):
        """Save decision history to persistent storage"""
        try:
            decisions_data = []
            for decision in decision_history:
                if isinstance(decision, dict):
                    decision_dict = decision.copy()
                    if isinstance(decision_dict.get("timestamp"), datetime.datetime):
                        decision_dict["timestamp"] = decision_dict["timestamp"].isoformat()
                    decisions_data.append(decision_dict)
            
            export_data = {
                "metadata": {
                    "version": VERSION,
                    "build_hash": BUILD_HASH,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "total_decisions": len(decisions_data)
                },
                "decisions": decisions_data
            }
            
            with open(DECISION_HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            log("Decision history saved to persistent storage", LogLevel.INFO, "DECISION")
            
        except Exception as e:
            log(f"Failed to save decision history: {e}", LogLevel.ERROR, "DECISION")
    
    def check_all_models(self):
        """Check status of all monolith models"""
        results = {}
        
        for name, monolith in self.monoliths.items():
            status = monolith.check_model_status()
            results[name] = {
                "status": status,
                "performance": monolith.get_performance_metrics()
            }
            log(f"[{name}] Model check: {status}", LogLevel.INFO, "MONOLITH")
        
        return results

def load_decision_history():
    """Load decision history from persistent storage"""
    try:
        if DECISION_HISTORY_PATH.exists():
            with open(DECISION_HISTORY_PATH, 'r', encoding='utf-8') as f:
                stored_data = json.load(f)
            
            if "decisions" in stored_data:
                decisions_data = stored_data["decisions"]
            else:
                decisions_data = stored_data
            
            for stored_decision in decisions_data[-CONFIG["system"]["max_decisions"]:]:
                if isinstance(stored_decision.get("timestamp"), str):
                    try:
                        stored_decision["timestamp"] = datetime.datetime.fromisoformat(stored_decision["timestamp"])
                    except:
                        stored_decision["timestamp"] = datetime.datetime.now()
                
                decision_history.append(stored_decision)
            
            log(f"Loaded {len(decision_history)} decisions from history", LogLevel.INFO, "DECISION")
        
    except Exception as e:
        log(f"Failed to load decision history: {e}", LogLevel.ERROR, "DECISION")

# ================================================================================
# MODULE 9: User Interface System
# ================================================================================

def render_main_screen(stdscr, theme: str = None):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header with enhanced styling
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL COMMAND CENTER"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status overview
    status_y = 3
    safe_addstr(stdscr, status_y, 2, "SYSTEM STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    mode = CONFIG["system"]["system_mode"]
    mode_color = 2 if mode == "READY" else 3
    safe_addstr(stdscr, status_y + 1, 4, f"Operational Mode: {mode}", curses.color_pair(mode_color))
    
    health_score = f"{system_health.cpu_usage:.0f}% CPU"
    safe_addstr(stdscr, status_y + 1, 30, f"Health: {health_score}", curses.color_pair(2))
    
    api_color = 2 if system_health.network_status == "operational" else 1
    safe_addstr(stdscr, status_y + 1, 50, f"API: {system_health.network_status.upper()}", curses.color_pair(api_color))
    
    # Monolith status section
    mono_y = status_y + 3
    safe_addstr(stdscr, mono_y, 2, "MONOLITH STATUS:", curses.A_BOLD | curses.color_pair(3))
    
    orchestrator = VotingOrchestrator()
    model_results = orchestrator.check_all_models()
    for i, (name, result) in enumerate(model_results.items()):
        status = result["status"]
        status_color = 2 if status == "ready" else 1
        safe_addstr(stdscr, mono_y + 1 + i, 4, f"{name}: {status.upper()}", curses.color_pair(status_color))
    
    # Display recent decisions
    if decision_history:
        decisions_y = mono_y + 6
        safe_addstr(stdscr, decisions_y, 2, "RECENT DECISIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_decisions = list(decision_history)[-5:]
        for i, decision in enumerate(recent_decisions):
            y_pos = decisions_y + 1 + i
            
            timestamp = decision["timestamp"].strftime("%H:%M") if hasattr(decision["timestamp"], 'strftime') else str(decision["timestamp"])[:5]
            safe_addstr(stdscr, y_pos, 4, f"[{timestamp}]", curses.color_pair(7))
            
            consensus = decision["verdict"]
            if consensus == "APPROVE":
                consensus_color = 2
            elif consensus == "DENY":
                consensus_color = 1
            else:
                consensus_color = 3
            
            safe_addstr(stdscr, y_pos, 12, consensus, curses.A_BOLD | curses.color_pair(consensus_color))
            
            query_preview = decision["query"][:40] + "..." if len(decision["query"]) > 40 else decision["query"]
            safe_addstr(stdscr, y_pos, 22, query_preview, curses.color_pair(7))
    
    # Notifications section
    cleanup_expired_notifications()
    if notifications:
        notif_y = height - 8
        safe_addstr(stdscr, notif_y, 2, "NOTIFICATIONS:", curses.A_BOLD | curses.color_pair(3))
        
        recent_notifications = list(notifications)[-4:]
        for i, notif in enumerate(recent_notifications):
            y_pos = notif_y + 1 + i
            
            color_map = {"success": 2, "error": 1, "warning": 3, "info": 7}
            color = color_map.get(notif["level"], 7)
            
            timestamp = notif["timestamp"].strftime("%H:%M")
            notif_text = f"[{timestamp}] {notif['message']}"
            safe_addstr(stdscr, y_pos, 4, notif_text, curses.color_pair(color))
    
    # Control instructions
    controls_y = height - 3
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | 7:History | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

def render_decision_history(stdscr):
    """Render decision history view"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    header = "CONSENSUS DECISION HISTORY"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions recorded", curses.color_pair(3))
    else:
        headers_y = 3
        safe_addstr(stdscr, headers_y, 2, "TIME", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 10, "VERDICT", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 20, "CONF", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 28, "QUERY", curses.A_BOLD | curses.color_pair(3))
        
        safe_addstr(stdscr, headers_y + 1, 2, "-" * (width - 4), curses.color_pair(7))
        
        start_y = headers_y + 2
        max_display = min(height - start_y - 3, len(decision_history))
        
        for i, decision in enumerate(list(decision_history)[-max_display:]):
            y_pos = start_y + i
            
            timestamp = decision["timestamp"].strftime("%H:%M") if hasattr(decision["timestamp"], 'strftime') else str(decision["timestamp"])[:5]
            safe_addstr(stdscr, y_pos, 2, timestamp, curses.color_pair(7))
            
            verdict = decision["verdict"]
            if verdict == "APPROVE":
                verdict_color = 2
            elif verdict == "DENY":  
                verdict_color = 1
            else:
                verdict_color = 3
            safe_addstr(stdscr, y_pos, 10, verdict, curses.color_pair(verdict_color))
            
            confidence = f"{decision.get('confidence', 0.0):.0%}"
            safe_addstr(stdscr, y_pos, 20, confidence, curses.color_pair(7))
            
            query = decision["query"][:45] + "..." if len(decision["query"]) > 45 else decision["query"]
            safe_addstr(stdscr, y_pos, 28, query, curses.color_pair(7))
    
    safe_addstr(stdscr, height - 2, 2, "Press any key to return to main view", curses.color_pair(3))

# ================================================================================
# MODULE 10: Console Mode
# ================================================================================

def run_console_mode():
    """Enhanced console mode with comprehensive commands"""
    print("\n" + "=" * 80)
    print("CONSENSUS SYSTEM - CONSOLE COMMAND INTERFACE")
    print("=" * 80)
    print("Available commands:")
    print("  vote <query>          - Submit query to tribunal for voting")
    print("  status                - Display system status")
    print("  health                - Show detailed health metrics")
    print("  history [N]           - Show last N decisions (default: 10)")
    print("  export <json|csv|txt> - Export decision history")
    print("  config                - Display configuration")
    print("  theme <n>             - Change UI theme")
    print("  help                  - Show this help")
    print("  quit                  - Exit console mode")
    print("=" * 80)
    
    orchestrator = VotingOrchestrator()
    
    while True:
        try:
            command_input = input(f"\n[{CONFIG['system']['system_mode']}] CONSENSUS> ").strip()
            
            if not command_input:
                continue
            
            parts = command_input.split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ["quit", "exit", "q"]:
                break
            
            elif command == "vote":
                handle_console_vote(orchestrator, args)
            
            elif command == "status":
                display_console_status(orchestrator)
            
            elif command == "health":
                display_health_metrics()
            
            elif command == "history":
                display_decision_history(args)
            
            elif command == "export":
                handle_console_export(args)
            
            elif command == "config":
                display_configuration()
            
            elif command == "theme":
                handle_theme_change(args)
            
            elif command == "help":
                display_console_help()
            
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")
            log(f"Console error: {e}", LogLevel.ERROR, "CONSOLE")

def handle_console_vote(orchestrator: VotingOrchestrator, query: str):
    """Handle voting command in console mode"""
    if not query:
        print("Usage: vote <your question>")
        return
    
    print(f"\n🗳️  Initiating tribunal vote on: {query}")
    print("-" * 60)
    
    # Execute vote
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"⚖️  FINAL TRIBUNAL VERDICT: {consensus.value}")
    print(f"📊 Confidence: {confidence:.0%}")
    print(f"{'='*60}")
    
    # Display individual votes
    print("\n📋 Individual Monolith Votes:")
    for name, vote_data in votes.items():
        status_icon = "✓" if vote_data.vote != VoteResult.ERROR else "✗"
        print(f"  {status_icon} {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})")
    
    print(f"\n💡 Reasoning: {reasoning[:200]}...")
    
    # Show TTS announcement
    if CONFIG["tts"]["enabled"]:
        print("\n🔊 Audio announcement in progress...")

def handle_theme_change(args: str):
    """Handle theme change command"""
    themes = list(THEME_DEFINITIONS.keys())
    
    if not args:
        print("\n🎨 Available themes:")
        for i, theme in enumerate(themes):
            current = " (current)" if theme == CONFIG['system']['theme'] else ""
            print(f"  {i}: {theme} - {THEME_DEFINITIONS[theme]['name']}{current}")
        return
    
    try:
        if args.isdigit():
            theme_index = int(args)
            if 0 <= theme_index < len(themes):
                CONFIG["system"]["theme"] = themes[theme_index]
                save_system_config()
                print(f"✅ Theme changed to: {themes[theme_index]} ({THEME_DEFINITIONS[themes[theme_index]]['name']})")
            else:
                print(f"❌ Invalid theme index. Choose 0-{len(themes)-1}")
        else:
            theme_name = args.lower()
            if theme_name in themes:
                CONFIG["system"]["theme"] = theme_name
                save_system_config()
                print(f"✅ Theme changed to: {theme_name} ({THEME_DEFINITIONS[theme_name]['name']})")
            else:
                print(f"❌ Unknown theme: {args}")
    except ValueError:
        print("❌ Invalid theme selection. Use 'theme' without args to see available themes.")

# ================================================================================
# MODULE 11: Export & I/O Operations
# ================================================================================

def export_decisions(format_type: str) -> str:
    """Export decision history in specified format"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    if format_type.lower() == "json":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.json"
        export_data = {
            "export_metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "version": VERSION,
                "build_hash": BUILD_HASH,
                "total_decisions": len(decision_history),
                "export_format": "json"
            },
            "decisions": [
                {
                    **{k: v for k, v in decision.items() if k != "timestamp"},
                    "timestamp": decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                }
                for decision in decision_history
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    elif format_type.lower() == "csv":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            writer.writerow([
                "Timestamp", "Decision_ID", "Query", "Consensus", "Confidence",
                "Session_ID", "System_Mode", "Theme", "Version"
            ])
            
            for decision in decision_history:
                timestamp_str = decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                
                writer.writerow([
                    timestamp_str,
                    decision.get("id", ""),
                    decision["query"],
                    decision["verdict"],
                    f"{decision.get('confidence', 0.0):.2f}",
                    decision.get("session_id", ""),
                    decision.get("system_state", {}).get("mode", ""),
                    decision.get("system_state", {}).get("theme", ""),
                    decision.get("system_state", {}).get("version", "")
                ])
    
    elif format_type.lower() == "txt":
        filename = EXPORT_DIR / f"consensus_decisions_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("CONSENSUS SYSTEM DECISION EXPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"System Version: {VERSION} (Build: {BUILD_HASH})\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, decision in enumerate(decision_history, 1):
                timestamp_str = decision["timestamp"].isoformat() if hasattr(decision["timestamp"], 'isoformat') else str(decision["timestamp"])
                
                f.write(f"DECISION #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"ID: {decision.get('id', 'N/A')}\n")
                f.write(f"Timestamp: {timestamp_str}\n")
                f.write(f"Query: {decision['query']}\n")
                f.write(f"Consensus: {decision['verdict']}\n")
                f.write(f"Confidence: {decision.get('confidence', 0.0):.0%}\n")
                f.write(f"Session ID: {decision.get('session_id', 'N/A')}\n")
                
                if decision.get("individual_votes"):
                    f.write("\nIndividual Monolith Votes:\n")
                    for monolith, vote_data in decision["individual_votes"].items():
                        vote_val = vote_data.get('vote', 'N/A') if isinstance(vote_data, dict) else str(vote_data)
                        f.write(f"  {monolith}: {vote_val}\n")
                
                if decision.get("system_state"):
                    state = decision["system_state"]
                    f.write(f"\nSystem State: Mode={state.get('mode', 'N/A')}, Theme={state.get('theme', 'N/A')}\n")
                
                f.write("\n" + "=" * 60 + "\n\n")
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")
    
    log(f"Decisions exported to {filename} ({format_type.upper()} format)", LogLevel.INFO, "EXPORT")
    return str(filename)

# ================================================================================
# MODULE 12: Demo & Testing Functions
# ================================================================================

def demo_voting_process():
    """Enhanced demo voting process with sample queries"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of surveillance network infrastructure?",
        "Grant clearance for classified data access request?",
        "Execute contingency plan for system failover scenario?",
        "Authorize resource allocation for mission-critical objectives?"
    ]
    
    query = random.choice(queries)
    log(f"Demo vote initiated: {query}", LogLevel.INFO, "DEMO")
    
    orchestrator = VotingOrchestrator()
    consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
    
    log(f"Demo vote complete: {consensus.value} (confidence: {confidence:.2f})", LogLevel.INFO, "DEMO")
    
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        print(f"\n🎮 DEMO VOTE RESULTS:")
        print(f"Query: {query}")
        print(f"Consensus: {consensus.value}")
        print(f"Confidence: {confidence:.0%}")
        print("-" * 50)

def summarize_consensus(consensus: VoteResult, votes: Dict[str, VoteData], reasoning: str):
    """Enhanced consensus summary with typing effect"""
    print("\n" + "=" * 80)
    print("TRIBUNAL CONSENSUS ANALYSIS")
    print("=" * 80)
    
    def type_text(text, delay=0.02):
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()
    
    print("\nFINAL VERDICT:")
    verdict_text = f"The AI Tribunal has reached consensus: {consensus.value}"
    type_text(verdict_text, 0.03)
    
    print("\nMONOLITH ANALYSIS:")
    for name, vote_data in votes.items():
        if vote_data.vote != VoteResult.ERROR:
            vote_icon = {"APPROVE": "✓", "DENY": "✗", "ABSTAIN": "○"}.get(vote_data.vote.value, "?")
            analysis = f"  {vote_icon} {name}: {vote_data.vote.value} (confidence: {vote_data.confidence:.0%})"
            type_text(analysis, 0.01)
            
            specialty = CONFIG["monoliths"][name]["specialty"].replace("_", " ").title()
            type_text(f"    Specialty: {specialty}", 0.01)
            
            brief_reasoning = vote_data.reasoning[:80] + "..." if len(vote_data.reasoning) > 80 else vote_data.reasoning
            type_text(f"    Reasoning: {brief_reasoning}", 0.005)
    
    print("\nCONSENSUS ANALYSIS:")
    approve_count = sum(1 for v in votes.values() if v.vote == VoteResult.APPROVE)
    deny_count = sum(1 for v in votes.values() if v.vote == VoteResult.DENY)
    abstain_count = sum(1 for v in votes.values() if v.vote == VoteResult.ABSTAIN)
    
    strength = "Strong" if max(approve_count, deny_count, abstain_count) == 3 else "Majority"
    type_text(f"  Consensus Strength: {strength}", 0.02)
    type_text(f"  Vote Distribution: {approve_count} Approve, {deny_count} Deny, {abstain_count} Abstain", 0.02)
    
    avg_response = sum(v.response_time for v in votes.values()) / len(votes)
    type_text(f"  Average Response Time: {avg_response:.2f}s", 0.02)
    
    print("=" * 80)

# ================================================================================
# MODULE 13: Main Application Loop
# ================================================================================

def handle_input(stdscr, key: int) -> bool:
    """Handle keyboard input and return True if should continue"""
    if key in (ord('q'), ord('Q')):
        return False
    elif key in (ord('s'), ord('S')):
        cycle_theme()
    elif key in (ord('m'), ord('M')):
        CONFIG["system"]["current_view"] = "main"
    elif key in (ord('v'), ord('V')):
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        return False  # Exit curses mode to enter console mode
    elif key in (ord('7')):
        if CONFIG["system"]["current_view"] == "history":
            CONFIG["system"]["current_view"] = "main"
        else:
            CONFIG["system"]["current_view"] = "history"
    elif key in (ord('h'), ord('H')):
        add_notification("Help system: Press 7 for history, S for themes, V for demo vote", NotificationLevel.INFO)
    
    return True

def run_ui_loop(stdscr):
    """Enhanced main UI loop with multiple views"""
    curses.start_color()
    curses.use_default_colors()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(1)
    stdscr.timeout(100)
    
    if curses.has_colors():
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
    
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
                        for i in range(1, 8):
                            curses.init_pair(i, i, -1)
                else:
                    running = handle_input(stdscr, key)
            
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                current_view = CONFIG["system"]["current_view"]
                if current_view == "history":
                    render_decision_history(stdscr)
                else:
                    render_main_screen(stdscr, CONFIG["system"]["theme"])
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"UI loop error: {e}", LogLevel.ERROR, "UI")
            add_notification(f"UI error: {str(e)}", NotificationLevel.ERROR)

# ================================================================================
# MODULE 14: Main Entry Point
# ================================================================================

def main():
    """Main entry point with enhanced error handling and startup sequence"""
    try:
        show_boot_sequence()
        initialize_system()
        
        add_notification("All monoliths initialized", NotificationLevel.INFO)
        add_notification("System ready for operation", NotificationLevel.SUCCESS)
        
        print("\n" + "="*80)
        print("CONSENSUS SYSTEM - OPERATIONAL MODE SELECTION")
        print("="*80)
        print("1. 🖥️  GUI Mode      - Full interface with real-time monitoring")
        print("2. 💻 Console Mode   - Direct command-line operation")
        print("3. 🎮 Demo Mode      - Automated demonstration")
        print("4. 🚪 Exit System    - Terminate CONSENSUS")
        print("="*80)
        
        while True:
            choice = input("\n🎯 Select operational mode (1-4): ").strip()
            
            if choice == "1":
                log("Starting GUI mode", LogLevel.INFO, "MODE")
                try:
                    print("\n🖥️  Launching GUI interface...")
                    curses.wrapper(run_ui_loop)
                except Exception as e:
                    log(f"GUI mode error: {e}", LogLevel.ERROR, "MODE")
                    print(f"❌ GUI mode failed: {e}")
                    print("💡 Try console mode instead...")
                break
            elif choice == "2":
                log("Starting console mode", LogLevel.INFO, "MODE")
                print("\n💻 Entering console mode...")
                run_console_mode()
                break
            elif choice == "3":
                log("Starting demo mode", LogLevel.INFO, "MODE")
                print("\n🎮 Running demonstration...")
                demo_voting_process()
                print("\n✅ Demo complete!")
                break
            elif choice == "4":
                log("User requested exit", LogLevel.INFO, "MODE")
                print("\n🚪 Terminating CONSENSUS System...")
                break
            else:
                print("❌ Invalid selection. Please choose 1-4.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  System interrupted by user.")
        log("System interrupted by user", LogLevel.WARNING, "MAIN")
    except Exception as e:
        error_msg = f"Fatal system error: {e}"
        print(f"\n❌ {error_msg}")
        log(error_msg, LogLevel.CRITICAL, "MAIN")
        log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "MAIN")
        sys.exit(1)
    finally:
        uptime = get_system_uptime()
        log(f"CONSENSUS System shutting down after {uptime} uptime", LogLevel.SHUTDOWN, "MAIN")
        
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║                        SYSTEM SHUTDOWN COMPLETE                            ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print(f"🟢 CONSENSUS System terminated gracefully")
        print(f"📊 Session summary: {len(decision_history)} decisions processed")
        print(f"⏱️  Total uptime: {uptime}")
        
        if decision_history:
            last_decision = decision_history[-1]
            last_time = last_decision["timestamp"]
            if hasattr(last_time, 'strftime'):
                time_str = last_time.strftime('%H:%M:%S')
            else:
                time_str = str(last_time)
            print(f"🕒 Last decision: {time_str} - {last_decision['verdict']}")
        
        print(f"\n🔒 All systems secured. Have a great day, Commander.")