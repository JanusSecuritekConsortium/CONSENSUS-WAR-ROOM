#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine (v4.3.0)
Complete tactical implementation with enhanced visualization features.

Features:
- Three specialized AI monoliths (RATIONALIS, AETERNUM, BELLATOR)
- Enhanced voting consensus algorithm with probabilistic scoring
- Multiple UI themes with tactical aesthetics (Military, TARS, EVA, WH40K, Helldivers)
- Specialized monolith-specific views with detailed data visualization
- Financial/Market data integration for AETERNUM
- Tactical risk assessment for BELLATOR
- Text-to-speech verdict announcements with GLaDOS-inspired voice
- Dual-mode operation (GUI/Console with command completion)
- Export/import functionality for decision records
- External API integration for real-time data

Author: Tactical Systems Division
Version: 4.3.0
Build Date: 2025-05-21
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
import hashlib
import traceback
import statistics
import signal
import shutil
import subprocess
from pathlib import Path
from collections import deque, defaultdict, Counter
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import concurrent.futures

# Optional dependencies with fallback handling
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not available. System health monitoring will be limited.")

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    print("colorama not available. Console output will not be colored.")

try:
    from ib_insync import *
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("ib_insync not available. Financial market data will be simulated.")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("pyttsx3 not available. TTS functionality will be disabled.")

# ================================================================================
# MODULE 1: System Constants & Configuration
# ================================================================================

# Version Information
VERSION = "4.3.0"
BUILD_DATE = "2025-05-21"
BUILD_HASH = hashlib.md5(f"{VERSION}{BUILD_DATE}".encode()).hexdigest()[:8]
SESSION_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

# System Paths
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
BACKUP_DIR = ARBITER_DIR / "backups"
CONFIG_PATH = ARBITER_DIR / "config.json"
DECISION_HISTORY_PATH = ARBITER_DIR / "decision_history.json"

# ASCII Art & Logos
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
    VOTE = "VOTE"
    CONSENSUS = "CONSENSUS"
    DECISION = "DECISION"
    ANALYTICS = "ANALYTICS"

class ViewMode(Enum):
    MAIN = "main"
    RATIONALIS = "rationalis"
    AETERNUM = "aeternum"
    BELLATOR = "bellator"
    HISTORY = "history"
    DIAGNOSTICS = "diagnostics"
    ANALYTICS = "analytics"
    HELP = "help"
    CONFIG = "config"

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

@dataclass
class SystemHealthMetrics:
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    api_response_time: float = 0.0
    tts_status: str = "unknown"
    network_status: str = "unknown"
    uptime: float = 0.0
    error_count: int = 0
    last_check: datetime.datetime = field(default_factory=datetime.datetime.now)
    
@dataclass
class ThreatAlert:
    level: str
    source: str
    description: str
    timestamp: datetime.datetime
    confidence: float
    impact_score: float
    recommendation: str
    
@dataclass
class LogicalAnalysis:
    query: str
    conclusion: str
    reasoning: List[str]
    confidence: float
    logical_fallacies: List[str]
    timestamp: datetime.datetime
    execution_time: float
    
@dataclass
class MonolithData:
    rationalis: Dict[str, Any] = field(default_factory=dict)
    aeternum: Dict[str, Any] = field(default_factory=dict)
    bellator: Dict[str, Any] = field(default_factory=dict)
    last_update: datetime.datetime = None

# Theme Definitions with Box Characters
THEME_DEFINITIONS = {
    "military": {
        "name": "Military HQ",
        "box_chars": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
        "colors": {"primary": 2, "secondary": 3, "accent": 6, "warning": 1},
        "labels": {
            "monolith_rationalis": "LOGICAL ANALYSIS MATRIX",
            "monolith_aeternum": "TEMPORAL INTELLIGENCE DIVISION",
            "monolith_bellator": "TACTICAL OPERATIONS CENTER",
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
            "monolith_rationalis": "LOGICAL.INFERENCE.MODULE",
            "monolith_aeternum": "TEMPORAL.ANALYSIS.MODULE",
            "monolith_bellator": "STRATEGIC.ASSESSMENT.MODULE",
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
            "monolith_rationalis": "MAGI CASPER - SCIENTIFIC ANALYSIS",
            "monolith_aeternum": "MAGI BALTHASAR - MATERNAL INTUITION",
            "monolith_bellator": "MAGI MELCHIOR - PATERNAL INSTINCT",
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
            "monolith_rationalis": "ADEPTUS MECHANICUS LOGIS",
            "monolith_aeternum": "ADMINISTRATUM HISTORICUS",
            "monolith_bellator": "MUNITORUM TACTICUS",
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
            "monolith_rationalis": "DEMOCRACY ASSESSMENT ENGINE",
            "monolith_aeternum": "FREEDOM FORECASTING SYSTEM",
            "monolith_bellator": "LIBERTY DEFENSE MATRIX",
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

# Monolith configuration (MAGI/EVA mapping, color per curses convention)
MONOLITHS = {
    "RATIONALIS": {
        "name": "RATIONALIS",
        "model": "deepseek-coder:33b",
        "specialization": "Logic engine",
        "color": 4,  # Cyan
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
        "color": 5,  # Magenta
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
        "color": 1,  # Red
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

# Vote colors - consistent across all monoliths
VOTE_COLORS = {
    "APPROVE": 4,  # Green
    "DENY": 6,     # Red
    "CONDITIONAL": 5,  # Yellow
    "ABSTAIN": 3,  # Blue
    "PENDING": 7,  # White
    "ERROR": 6     # Red
}

# Status indicators
STATUS_INDICATORS = {
    "online": ("ONLINE", 4),      # Green
    "processing": ("PROCESSING", 5),  # Yellow
    "offline": ("OFFLINE", 6),    # Red
    "ready": ("READY", 4),        # Green
    "loading": ("LOADING", 5),    # Yellow
    "error": ("ERROR", 6),        # Red
    "service_down": ("UNAVAILABLE", 6),  # Red
    "not_loaded": ("NOT LOADED", 5)      # Yellow
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

# API Configuration
API_CONFIG = {
    "YahooFinance": {
        "enabled": True,
        "url": "https://api.yahoofinance.com",
        "key": "YF_API_KEY_ENV",
        "timeout": 5.0
    },
    "AlphaVantage": {
        "enabled": True,
        "url": "https://www.alphavantage.co/query",
        "key": "ALPHA_VANTAGE_KEY_ENV",
        "timeout": 5.0
    },
    "CoinGecko": {
        "enabled": True,
        "url": "https://api.coingecko.com/api/v3",
        "key": None,
        "timeout": 5.0
    },
    "NewsAPI": {
        "enabled": True,
        "url": "https://newsapi.org/v2",
        "key": "NEWS_API_KEY_ENV",
        "timeout": 5.0
    },
    "GDELT": {
        "enabled": True,
        "url": "https://api.gdeltproject.org/api/v2",
        "key": None,
        "timeout": 10.0
    },
    "IBKR": {
        "enabled": IB_AVAILABLE,
        "host": "127.0.0.1",
        "port": 7496,
        "client_id": 1,
        "timeout": 20.0
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

# Global Configuration (default)
DEFAULT_CONFIG = {
    "system": {
        "theme": "military",
        "current_view": ViewMode.MAIN.value,
        "system_mode": SystemMode.READY.value,
        "debug_mode": False,
        "max_log_entries": 1000,
        "max_decisions": 100,
        "auto_escalation_enabled": True,
        "human_oversight_threshold": 0.5,
        "enable_bias_detection": True,
        "enable_sentiment_analysis": True,
        "command_history_size": 50
    },
    "llm": {
        "provider": "ollama",
        "api_timeout": 30,
        "vote_timeout": 45,
        "max_retries": 3,
        "base_url": "http://localhost:11434",
        "enable_parallel_processing": True,
        "response_validation": True
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
    "consensus": {
        "algorithm": "probabilistic_weighted",
        "minimum_confidence": 0.6,
        "human_oversight_triggers": ["high_disagreement", "low_confidence", "bias_detected"],
        "precedent_matching_enabled": True,
        "bias_threshold": 0.7
    },
    "tts": {
        "enabled": TTS_AVAILABLE,
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
    },
    "export": {
        "auto_backup": True,
        "backup_interval": 3600,
        "formats": ["json", "csv", "txt"]
    },
    "analytics": {
        "enable_real_time": True,
        "performance_tracking": True,
        "bias_monitoring": True,
        "decision_pattern_analysis": True
    },
    "market_data": {
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD"],
        "update_interval": 60,
        "history_length": 24,
        "volatility_threshold": 2.0
    },
    "security": {
        "defcon_level": 3,
        "threat_categories": ["cyber", "economic", "geopolitical", "military", "environmental"],
        "alert_threshold": 0.7,
        "max_alerts": 10
    }
}

# Global State
CONFIG = DEFAULT_CONFIG.copy()

# State for system health monitoring
system_health = SystemHealthMetrics()

# Global state tracking
notifications = deque(maxlen=5)
decision_history = deque(maxlen=DEFAULT_CONFIG["system"]["max_decisions"])
command_history = deque(maxlen=DEFAULT_CONFIG["system"]["command_history_size"])
log_entries = deque(maxlen=DEFAULT_CONFIG["system"]["max_log_entries"])
active_votes = {}
command_output = ""
COMMANDS = {}  # Command registry

# Initialize model status
MODEL_STATUS = {
    "RATIONALIS": {"status": "unknown", "memory_usage": 0, "loading": False},
    "AETERNUM": {"status": "unknown", "memory_usage": 0, "loading": False},
    "BELLATOR": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# IBKR connection state
IBKR_CONNECTED = False
ib = None

# For verdict typing animation
verdict_display_text = ""
verdict_display_length = 0
verdict_full_text = ""
last_verdict_update = 0

# Initialize specialized monolith data structure
monolith_data = MonolithData(
    rationalis={
        "efficiency_rating": 0.85,
        "logical_analyses": deque(maxlen=20),
        "fallacy_detection": {},
        "system_logs": deque(maxlen=50),
        "execution_times": deque(maxlen=100),
        "confidence_history": deque(maxlen=100),
        "last_update": None
    },
    aeternum={
        "market_indices": {
            "S&P 500": {"value": 5320.42, "change": 0.3, "trend": "up"},
            "NASDAQ": {"value": 18750.65, "change": 0.5, "trend": "up"},
            "Dow Jones": {"value": 42150.30, "change": 0.1, "trend": "up"},
            "BTC/USD": {"value": 84250.75, "change": -2.1, "trend": "down"},
            "ETH/USD": {"value": 5120.25, "change": -1.5, "trend": "down"},
            "Gold": {"value": 2785.50, "change": 0.8, "trend": "up"},
            "Crude Oil": {"value": 82.45, "change": -0.6, "trend": "down"},
            "US 10Y": {"value": 3.85, "change": 0.05, "trend": "up"}
        },
        "historical_prices": {},
        "volatility_index": 18.5,
        "market_sentiment": 0.65,
        "economic_indicators": {},
        "last_update": None
    },
    bellator={
        "defcon_level": 3,
        "threat_alerts": deque(maxlen=10),
        "risk_assessments": deque(maxlen=20),
        "security_index": 72.5,
        "geopolitical_stability": 0.68,
        "cyberattack_probability": 0.45,
        "strategic_recommendations": deque(maxlen=10),
        "last_update": None
    },
    last_update=datetime.datetime.now()
)

# Threading locks
health_lock = threading.Lock()
decision_lock = threading.Lock()
log_lock = threading.Lock()
market_lock = threading.Lock()
security_lock = threading.Lock()

# Current query for consensus voting
current_query = "No active query"
startup_time = time.time()

# ================================================================================
# MODULE 2: Boot Sequence & Initialization
# ================================================================================

def type_out(text, delay=0.01):
    """Type out text with delay for visual effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def boot_system():
    """Display enhanced boot sequence with NERV logo"""
    os.system('cls' if os.name == 'nt' else 'clear')
    if COLORAMA_AVAILABLE:
        print(Fore.RED + NERV_LOGO)
    else:
        print(NERV_LOGO)

    BIOS_BOOT_STEPS = [
        "ARASAKA BIOS v4.3.0 - WAR ROOM Interface",
        "Copyright (C) 1995-2025 NEURODYNE SYSTEMS",
        "",
        "Detecting CPU... Consensus Neural Thread v9.12 .............. \033[32m[OK]",
        "Detecting Memory... 65536MB ................................ \033[32m[OK]",
        "[SYS] Syncing quantum entanglement buffers...",
        "Initializing Monolith Interfaces:",
        " > RATIONALIS [DeepSeek Coder] ............................ \033[32m[OK]",
        " > AETERNUM [LLaMA 3 Temporal] ........................... \033[32m[OK]",
        " > BELLATOR [Mixtral Tactical] ........................... \033[32m[OK]",
        "Verifying Inference Engines ............................... \033[32m[OK]",
        "Loading TTS Subsystem... GLaDOS Interface Ready ........... \033[32m[OK]",
        "Establishing Shadow Context ............................... \033[32m[OK]",
        "All systems functional.",
        "",
        ">>> Press [ENTER] to initiate WAR ROOM <<<"
    ]

    for line in BIOS_BOOT_STEPS:
        color = Fore.GREEN if "[OK]" in line else Fore.WHITE if COLORAMA_AVAILABLE else ""
        type_out(color + line, delay=random.uniform(0.003, 0.012))
        time.sleep(random.uniform(0.08, 0.19))

    input()  # Wait for user to press ENTER

def show_boot_sequence():
    """Display enhanced boot sequence with logo and system initialization"""
    os.system("cls" if os.name == "nt" else "clear")
    print(CONSENSUS_LOGO)
    time.sleep(0.8)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Define initialization steps
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
        ("Initializing security", [
            "DEFCON status", "Threat monitoring", "Geopolitical analysis", "Economic surveillance"
        ]),
        ("Finalizing startup", [
            "
def show_boot_sequence():
    """Display enhanced boot sequence with logo and system initialization"""
    os.system("cls" if os.name == "nt" else "clear")
    print(CONSENSUS_LOGO)
    time.sleep(0.8)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                        SYSTEM INITIALIZATION                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Define initialization steps
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
        ("Initializing security", [
            "DEFCON status", "Threat monitoring", "Geopolitical analysis", "Economic surveillance"
        ]),
        ("Finalizing startup", [
            "Configuration validation", "Log system", "Decision tracking", "Ready state"
        ])
    ]
    
    # Display initialization with typing effect
    for step_name, substeps in init_steps:
        print(f"\n◢◣ {step_name}...")
        time.sleep(0.4)
        for substep in substeps:
            if COLORAMA_AVAILABLE:
                status = Fore.GREEN + "[✓]" + Style.RESET_ALL
            else:
                status = "[✓]"
            type_text(f"  ├─ {substep}{'.' * (35 - len(substep))} {status}", delay=0.01)
            time.sleep(0.2)
        time.sleep(0.2)
    
    print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM READY FOR OPERATION                            ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    
    # Display control information
    if COLORAMA_AVAILABLE:
        controls_info = f"""
{Fore.YELLOW}▶ Control Keys:{Style.RESET_ALL}
  - {Fore.CYAN}Q{Style.RESET_ALL}: Quit system          - {Fore.CYAN}M{Style.RESET_ALL}: Main view
  - {Fore.CYAN}S{Style.RESET_ALL}: Cycle themes         - {Fore.CYAN}V{Style.RESET_ALL}: Vote demo
  - {Fore.CYAN}C{Style.RESET_ALL}: Console mode         - {Fore.CYAN}9{Style.RESET_ALL}: Diagnostics
  - {Fore.CYAN}H{Style.RESET_ALL}: Help system          - {Fore.CYAN}7{Style.RESET_ALL}: Decision history
  - {Fore.CYAN}1{Style.RESET_ALL}: RATIONALIS view      - {Fore.CYAN}2{Style.RESET_ALL}: AETERNUM view
  - {Fore.CYAN}3{Style.RESET_ALL}: BELLATOR view        - {Fore.CYAN}A{Style.RESET_ALL}: Analytics view

{Fore.GREEN}■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE...{Style.RESET_ALL}"""
    else:
        controls_info = """
▶ Control Keys:
  - Q: Quit system          - M: Main view
  - S: Cycle themes         - V: Vote demo
  - C: Console mode         - 9: Diagnostics
  - H: Help system          - 7: Decision history
  - 1: RATIONALIS view      - 2: AETERNUM view
  - 3: BELLATOR view        - A: Analytics view

■ CONSENSUS SYSTEM LOADED. PRESS ANY KEY TO CONTINUE..."""
    
    print(controls_info)
    input()

def type_text(text, delay=0.01):
    """Type out text with delay for visual effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

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
        
        # Initialize market data system if enabled
        if CONFIG["market_data"]["update_interval"] > 0:
            threading.Thread(target=market_data_daemon, daemon=True).start()
            log("Market data monitoring daemon started", LogLevel.INFO)
        
        # Initialize security monitoring
        if CONFIG["security"]["alert_threshold"] > 0:
            threading.Thread(target=security_monitor_daemon, daemon=True).start()
            log("Security monitoring daemon started", LogLevel.INFO)
        
        # Initialize simulated monolith data
        update_simulated_monolith_data()
        
        # Start model status monitoring thread
        threading.Thread(target=update_model_statuses, daemon=True).start()
        
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
    
    # Create log entry
    entry = {
        "timestamp": timestamp,
        "level": level.value,
        "component": component,
        "message": message,
        "session_id": session_id or SESSION_ID,
        "thread": threading.current_thread().name
    }
    
    # Add to memory
    with log_lock:
        log_entries.append(entry)
    
    # Format for file output
    session_part = f" [{session_id or SESSION_ID}]" if session_id else ""
    formatted_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] [{level.value:8}] [{component:12}]{session_part} {message}"
    
    # Output to console if in debug mode or critical
    if CONFIG["system"].get("debug_mode", False) or level in [LogLevel.ERROR, LogLevel.CRITICAL]:
        if COLORAMA_AVAILABLE:
            level_colors = {
                LogLevel.DEBUG.value: Fore.MAGENTA,
                LogLevel.INFO.value: Fore.CYAN,
                LogLevel.WARNING.value: Fore.YELLOW,
                LogLevel.ERROR.value: Fore.RED,
                LogLevel.CRITICAL.value: Fore.RED + Style.BRIGHT,
                LogLevel.STARTUP.value: Fore.GREEN,
                LogLevel.SHUTDOWN.value: Fore.YELLOW,
                LogLevel.VOTE.value: Fore.CYAN,
                LogLevel.CONSENSUS.value: Fore.GREEN,
                LogLevel.DECISION.value: Fore.BLUE,
                LogLevel.ANALYTICS.value: Fore.MAGENTA
            }
            color = level_colors.get(level.value, "")
            print(f"{color}{formatted_entry}{Style.RESET_ALL}")
        else:
            print(formatted_entry)
    
    # Write to daily log file
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"{timestamp.strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{formatted_entry}\n")
    except Exception as e:
        print(f"Failed to write log: {e}")

def log_header(title: str):
    """Log a formatted header for major operations"""
    bar = "=" * 70
    if COLORAMA_AVAILABLE:
        print(Fore.WHITE + Style.BRIGHT + f"\n{bar}\n{title.center(70)}\n{bar}\n" + Style.RESET_ALL)
    else:
        print(f"\n{bar}\n{title.center(70)}\n{bar}\n")

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
    ], maxlen=5)

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
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(CONFIG_PATH, backup_path)
        
        # Save current config
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=2, default=str)
        
        log("Configuration saved successfully", LogLevel.INFO, "CONFIG")
        
    except Exception as e:
        log(f"Failed to save configuration: {e}", LogLevel.ERROR, "CONFIG")

def backup_config(config_path: Path):
    """Create a backup of the configuration file"""
    try:
        if config_path.exists():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{config_path.stem}_{timestamp}{config_path.suffix}"
            backup_path = BACKUP_DIR / backup_name
            
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_path, backup_path)
            
            log(f"Configuration backup created: {backup_path}", LogLevel.INFO, "CONFIG")
            return True
        return False
    except Exception as e:
        log(f"Failed to backup configuration: {e}", LogLevel.ERROR, "CONFIG")
        return False


# ================================================================================
# MODULE 5: Health Monitoring
# ================================================================================

def update_system_health():
    """Comprehensive system health check"""
    global system_health
    
    try:
        if PSUTIL_AVAILABLE:
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
                except:
                    system_health.network_status = "unavailable"
                    system_health.api_response_time = 999.0
                
                # TTS status
                if CONFIG["tts"]["enabled"]:
                    if TTS_AVAILABLE:
                        try:
                            engine = pyttsx3.init()
                            system_health.tts_status = "operational"
                            engine.stop()
                            del engine
                        except:
                            system_health.tts_status = "unavailable"
                    else:
                        system_health.tts_status = "unavailable"
                else:
                    system_health.tts_status = "disabled"
                
                # Update timestamp
                system_health.last_check = datetime.datetime.now()
                system_health.uptime = time.time() - startup_time
        else:
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
    seconds = uptime_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {seconds}s"

def check_model_status(name):
    """Check if a model is loaded and available in the LLM provider"""
    try:
        config = CONFIG["monoliths"][name]
        provider = CONFIG["llm"]["provider"]
        
        if provider == "ollama":
            response = requests.get(
                PROVIDER_ENDPOINTS["ollama"]["status_endpoint"],
                timeout=CONFIG['health']['api_timeout']
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_name = config["model"]
                
                for model in models:
                    if model["name"] == model_name:
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
                
        elif provider == "lmstudio":
            response = requests.get(
                PROVIDER_ENDPOINTS["lmstudio"]["status_endpoint"],
                timeout=CONFIG['health']['api_timeout']
            )
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_name = config["model"].split(":")[0].lower()
                
                for model in models:
                    if model_name in model["id"].lower():
                        MODEL_STATUS[name]["status"] = "ready"
                        return True
                
                MODEL_STATUS[name]["status"] = "not_loaded"
                return False
    except:
        MODEL_STATUS[name]["status"] = "service_down"
        return False

def update_model_statuses():
    """Update all model statuses in a background thread"""
    while True:
        try:
            # Check each model's status
            for name in MODEL_STATUS:
                if not MODEL_STATUS[name]["loading"]:
                    check_model_status(name)
                
                # Update memory usage if possible
                if PSUTIL_AVAILABLE:
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                            if CONFIG["llm"]["provider"] == "ollama" and 'ollama' in proc.info['name'].lower():
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)  # MB
                                break
                            elif CONFIG["llm"]["provider"] == "lmstudio" and 'lmstudio' in proc.info['name'].lower():
                                MODEL_STATUS[name]["memory_usage"] = proc.info['memory_info'].rss / (1024 * 1024)  # MB
                                break
                    except:
                        pass
                    
            time.sleep(5)  # Check every 5 seconds
        except:
            time.sleep(10)  # Longer delay on error

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
                    PROVIDER_ENDPOINTS["ollama"]["status_endpoint"],
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
                    PROVIDER_ENDPOINTS["lmstudio"]["status_endpoint"],
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
                PROVIDER_ENDPOINTS["ollama"]["api_url"],
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
                PROVIDER_ENDPOINTS["lmstudio"]["api_url"],
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
            self.vote_file.parent.mkdir(parents=True, exist_ok=True)
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
    
    def get_specialized_data(self) -> Dict[str, Any]:
        """Get specialized data for this monolith's view"""
        if self.name == "RATIONALIS":
            return monolith_data.rationalis
        elif self.name == "AETERNUM":
            return monolith_data.aeternum
        elif self.name == "BELLATOR":
            return monolith_data.bellator
        else:
            return {}