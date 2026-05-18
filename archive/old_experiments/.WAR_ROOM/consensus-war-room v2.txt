#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine

A decision-making system that simulates parallel AI reasoning using three distinct monolithic agents:
- RATIONALIS: Logical analysis and protocol compliance using DeepSeek Coder
- AETERNUM: Historical pattern recognition and risk assessment using Llama 3
- BELLATOR: Strategic and tactical analysis using Mixtral

Each agent operates independently and votes on queries, with results coordinated
by the central ARBITER module.

Author: Claude AI
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
from pathlib import Path
from contextlib import contextmanager
from collections import deque

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
 
 __        ___    ____    ____   ___   ___  __  __ 
 \ \      / / \  |  _ \  |  _ \ / _ \ / _ \|  \/  |
  \ \ /\ / / _ \ | |_) | | |_) | | | | | | | |\/| |
   \ V  V / ___ \|  _ <  |  _ <| |_| | |_| | |  | |
    \_/\_/_/   \_\_| \_\ |_| \_\\___/ \___/|_|  |_|
                                      
   *** AI TRIBUNAL DECISION SYSTEM v2.0 ***
"""

# NERV-inspired logo (simplified version that works in terminal)
NERV_LOGO = """
    /\\      
   /  \\     
  /    \\    
 /______\\   
 |      |   
 | NERV |   
 |______|   
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

# Status indicators
STATUS_INDICATORS = {
    "online": ("ONLINE", 4),      # Green
    "processing": ("PROCESSING", 5),  # Yellow
    "offline": ("OFFLINE", 6)     # Red
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

# Query templates
QUERY_TEMPLATES = {
    "finance": "Analyze market conditions for {symbol} and recommend investment action.",
    "security": "Evaluate security implications of {action} regarding {target}.",
    "logical": "Determine optimal approach for {goal} given constraints {constraints}.",
    "general": "Should we proceed with {action}?",
    "critical": "Authorize emergency protocol {protocol_number} for {situation}."
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

def add_decision_to_history(query, verdict, reasoning=None):
    """Add a decision to the history"""
    decision_history.append({
        "query": query,
        "verdict": verdict,
        "timestamp": datetime.datetime.now(),
        "reasoning": reasoning or "No reasoning provided"
    })

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
        # Service not available
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
                # Call Ollama to pull/load the model
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
                # For LM Studio, just check if it's available
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
            # Check each model's status
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
            # Send request to the Ollama API
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
            # Send request to the LM Studio API
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
        # Record start time for performance metrics
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

def apply_template(template_name, params=None):
    """Apply a query template with parameters"""
    if template_name not in QUERY_TEMPLATES:
        return f"Unknown template: {template_name}"
    
    template = QUERY_TEMPLATES[template_name]
    
    if not params:
        # Return template with placeholders
        return template
    
    try:
        # Parse parameters and apply to template
        param_dict = {}
        param_pairs = params.split(',')
        for pair in param_pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                param_dict[key.strip()] = value.strip()
        
        return template.format(**param_dict)
    except Exception as e:
        return f"Error applying template: {str(e)}"

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
        # This can happen when writing to the bottom-right corner
        pass

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
        safe_addstr(stdscr, y, title_x, f" {title} ", curses.A