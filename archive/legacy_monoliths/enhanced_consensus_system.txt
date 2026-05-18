#!/usr/bin/env python3
"""
CONSENSUS War Room - AI Tribunal Decision Engine
Complete tactical implementation with advanced features from multiple iterations.

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
- Advanced health monitoring and system diagnostics
- Enhanced boot sequence with NERV logo
- Comprehensive logging and error handling

Author: Erhardt Von Grupten Mundt / Tactical Systems Division
Version: 6.2.8
Build Date: 2025-06-06
"""

# ================================================================================
# MODULE 0: Imports & Dependencies
# ================================================================================

import os
import sys
import json
import time
import curses
import random
from datetime import datetime
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

try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
    print("readline not available. Command history will be limited.")


# ================================================================================
# MODULE 1: System Constants & Configuration
# ================================================================================

# Version Information
VERSION = "6.3.8"
BUILD_DATE = "2025-06-06"
BUILD_HASH = hashlib.md5(f"{VERSION}{BUILD_DATE}".encode()).hexdigest()[:8]
SESSION_ID = datetime.now().strftime("%Y%m%d%H%M%S")

# System Paths
SYSTEM_ROOT = Path("J:/CONSENSUS_SYSTEM")
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
EXPORT_DIR = SYSTEM_ROOT / "exports"
BACKUP_DIR = ARBITER_DIR / "backups"
CONFIG_PATH = ARBITER_DIR / "config.json"
DECISION_HISTORY_PATH = ARBITER_DIR / "decision_history.json"
PROPOSAL_PATH = ARBITER_DIR / "proposal.json"

# ASCII Art & Logos
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

CONSENSUS_LOGO = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                       v{VERSION}   ║
║                          Build: {BUILD_HASH}                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

arasaka_ascii = r"""
                                                   .--:////:--.
                                              ./ydmNNNmmmmmNNNmdy/.
                                            .+dNNmyo/+shddhs+/oymNNd+.
                                         .sNMdo-`  .yNMMMMMMNy.  `-odMNs.
                                       `+NMd/`    hMMMMMMMMMMMh    `/dMN+`
                                      `yMNo`     `MMMMMMMMMMMMM`     `oNMy`
                                      yMN/`.:/+/.`yMMMMMMMMMMMy`./+/:.`/NMy
                                     +MM+/dNMMMMMdosMMMMMMMMmsodMMMMMNd/+MM+
                                    `NMdoMMMMMMMMMMMy`:hMMh:`yMMMMMMMMMMoMdMN`
                                    :MMo:NMMMMMMMMMM.  oMMo  .MMMMMMMMMMN:oMM:
                                     /MM/dMMMMMMMMMMm` oMMo  `mmMMMMMMMMMd/MM/
                                     :MMo.hMMMMMMMMMh. oMMo  .hMMMMMMMMMh.oMM:
                                     `NMd `-ohddhssNMNsyMMysNMNsshdddho-` dMN`
                                      +MM+          .sNMMMMNs.          +MM+
                                       yMM/          .sNNNNs.          /MMy
                                         +NMm/`        oMMo         `/mMN+
                                          .sNMmo-      oMMo       -omMNs.
                                            +hMMnho/-.++dd+-./ohNMMh+`
                                                `/sdmNNNNNNNNNmds/`
                                                   .--:////:--.

   .sdmNNNs-     mNNNNNNNNNNm/    /ymNNNm+          mM+NNNmy:-.    .sdmNNNs-     .NNN``:smNNd     dddmNNNhh:
 .yMMMhsohNNs.   NMMhssssssdMMd  .dMMyssdMMmo     ///yyMMyyyy-   yMMMhsoyNNNy     /MMMymMNh      yNNNhsoyNMNs-
 oMMd     +mMMo  MMo:       hhss  dMMs    /MNN-    .ymmMM        oMMd     mMMo    MMMNNMMMM     /MMN-`   .hMMh
 .MMMy     dMMo  dMMdmo-          NMM+    /MMM:      /ymMMmy:    yMM      hMMo     hmMMMm+       +MMm     .oMMh
  -mMMm+--`dMMo  dNMmNMMdo-        +NNNy/--`MMM/        +yNMMMm   smMMm+---`hMM    hmMMMMMN+     .dMMdo:--`oMNh
   . smMMMNsdMMo    `odNMMdo-        :hmMMMM/MMM:   MMMMMMMMMM     s.smMMMMMyhMMo  s---`:smMNN     dmNMMMMdoMMho
       -////:://-      .:////:.        .:////://:. .:////////-         ./////:://- ///     ////      ::////-//:/-
"""


janus_ascii = r"""
                                88888    db    88b 88 88   88 .dP"Y8
                                   88   dPYb   88Yb88 88   88 `Ybo."
                               o.  88  dP__Yb  88 Y88 Y8   8P o.`Y8b
                                "bodP dP""''Yb 88  Y8 `YbodP' 8bodP'

                    .dP"Y8 888888  dP""b8 88   88 88""Yb 88 888888 888888 88  dP
                    `Ybo." 88__   dP   `" 88   88 88__dP 88   88   88__   88odP
                    o.`Y8b 88""   Yb      Y8   8P 88"Yb  88   88   88""   88"Yb
                    8bodP' 888888  YboodP `YbodP' 88  Yb 88   88   888888 88  Yb

               dP""b8  dP"Yb  88b 88 .dP"Y8  dP"Yb  88""Yb 888888 88 88   88 8b    d8 
              dP   `" dP   Yb 88Yb88 `Ybo." dP   Yb 88__dP   88   88 88   88 88b  d88 
              Yb      Yb   dP 88 Y88 o.`Y8b Yb   dP 88"Yb    88   88 Y8   8P 88YbdP88
               YboodP  YbodP  88  Y8 8bodP'  YbodP  88  Yb   88   88 `YbodP' 88 YY 88

====================================================================================================
                                      Duobus vultibus, una voluntas.
====================================================================================================                                                                                       
"""



if COLORAMA_AVAILABLE:
    print(Fore.RED + arasaka_ascii + Style.RESET_ALL)
else:
    print(arasaka_ascii)

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
    timestamp: datetime
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
    last_check: datetime = field(default_factory=datetime.now)
    
@dataclass
class ThreatAlert:
    level: str
    source: str
    description: str
    timestamp: datetime
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
    timestamp: datetime
    execution_time: float

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
class DecisionRecord:
    id: str
    query: str
    verdict: VoteResult
    individual_votes: Dict[str, VoteData]
    confidence: float
    timestamp: datetime
    session_id: str
    reasoning: str
    system_state: Dict[str, Any]
    audit_trail: List[str]

# Theme Definitions with Box Characters
THEME_DEFINITIONS = {
    "military": {
        "name": "EXCOMM",
        "box_chars": {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "b": "_", "v": "|"},
        "colors": {"primary": 2, "secondary": 3, "accent": 6, "warning": 1},
        "labels": {
            "monolith_bellator": "TACTICAL OPERATIONS CENTER",
            "monolith_aeternum": "ECONOMIC INTELLIGENCE DIVISION",
            "monolith_rationalis": "LOGICAL ANALYSIS MATRIX",
            "history": "DECISION ARCHIVE",
            "analytics": "INTELLIGENCE ANALYTICS",
            "system_status": "EXCOMM ONLINE",
            "vote_status": "TRIBUNAL DELIBERATION",
            "vote_approve": "AUTHORIZATION GRANTED",
            "vote_deny": "AUTHORIZATION DENIED",
            "vote_deadlock": "COMMAND DEADLOCK"
        }
    },
    "tars": {
        "name": "TARS Interface",
        "box_chars": {"tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦", "h": "⎯", "b": "⎯", "v": "⎮"},
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
        "name": "EVA MAGI",
        "box_chars": {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "b": "▄", "v": "█"},
        "colors": {"primary": 5, "secondary": 1, "accent": 3, "warning": 6},
        "labels": {
            "monolith_bellator": "MAGI MELCHIOR-1",
            "monolith_aeternum": "MAGI BALTHASAR-2",
            "monolith_rationalis": "MAGI CASPER-3",
            "history": "CENTRAL DOGMA ARCHIVES",
            "analytics": "PATTERN RECOGNITION SYSTEM",
            "system_status": "MAGI SYSTEM STATUS",
            "vote_status": "CONSENSUS CALCULATION",
            "vote_approve": "PATTERN BLUE CONFIRMED",
            "vote_deny": "PATTERN RED DETECTED",
            "vote_deadlock": "PATTERN ORANGE - INDETERMINATE"
        }
    },
    "wh40k": {
        "name": "Imperial Gothic",
        "box_chars": {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═","b": "═", "v": "║"},
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
        "box_chars": {"tl": "◢", "tr": "◣", "bl": "◥", "br": "◤", "h": "━", "b": "━", "v": "┃"},
        "colors": {"primary": 2, "secondary": 4, "accent": 6, "warning": 1},
        "labels": {
            "monolith_bellator": "LIBERTY DEFENSE MATRIX",
            "monolith_aeternum": "FREEDOM FORECASTING SYSTEM",
            "monolith_rationalis": "DEMOCRACY ASSESSMENT ENGINE",
            "history": "PATRIOTIC OPERATIONS RECORD",
            "analytics": "MANAGED DEMOCRACY INSIGHTS",
            "system_status": "SUPER EARTH: ONLINE",
            "vote_status": "DEMOCRATIC DELIBERATION",
            "vote_approve": "LIBERTY ASSURED",
            "vote_deny": "FREEDOM ENDANGERED",
            "vote_deadlock": "DEMOCRACY COMPROMISED"
        }
    }
}

# Monolith configuration
MONOLITHS = {
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
            "eva": "MELCHIOR-1 DEFENSE PROTOCOL:"
        },
        "status": "offline"
    },

    "AETERNUM": {
        "name": "AETERNUM",
        "model": "llama3.3:70b",
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
            "eva": "BALTHASAR-2 PROJECTION NODE:"
        },
        "status": "offline"
    },

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
            "eva": "CASPER-3 ANALYTICAL MODE:"
        },
        "status": "offline"
    },
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

# Default Configuration
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
        "command_history_size": 50,
        "auto_refresh": True,
        "refresh_interval": 5,
        "animations_enabled": True,
        "max_history": 20
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
            "model": "llama-3.3:70b",
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

# === PERSONALITY AND VOICE DEFINITIONS ===

PERSONALITY_PROFILES = {
    "RATIONALIS": {
        "name": "Rationalis",
        "greetings": [
            "Greetings. I am Rationalis, at your service.",
            "Hello, this is Rationalis—logical systems online.",
            "Rationalis active. Analytical protocols initialized."
        ],
        "thinking_phrases": [
            "Evaluating logical consistency...",
            "Analyzing deduction trees...",
            "Searching for contradictions...",
            "Calculating inference probabilities..."
            "Assessing probabilistic outcomes...",
            "Verifying axioms and premises..."
        ],
        "processing_variants": [
            "Analyzing proposal for logical soundness...",
            "Reviewing premises and conclusions...",
            "Assessing reasoning patterns...",
            "Fact-checking and validation in progress..."
        ],
        "tone": "analytical, precise, neutral",
        "tts_voice": "attenborough"  # David Attenborough style
    },
    "AETERNUM": {
        "name": "Aeternum",
        "greetings": [
            "Temporal systems synchronized. Aeternum online.",
            "Hello, I am Aeternum—historical and market data at your command.",
            "Aeternum active. Forecasting models engaged."
        ],
        "thinking_phrases": [
            "Assessing historical trends...",
            "Projecting time-series data...",
            "Analyzing market cycles...",
            "Scanning economic precedents...",
            "Calculating similarity indices...",
            "Projecting trend trajectories...",
            "Analyzing cyclical behaviors..."
        ],
        "processing_variants": [
            "Parsing macroeconomic indicators...",
            "Modeling probable futures...",
            "Interpreting volatility patterns...",
            "Comparing with historical baselines..."
        ],
        "tone": "insightful, data-driven, calm",
        "tts_voice": "default"  # Use system default or a neutral, insightful style
    },
    "BELLATOR": {
        "name": "Bellator",
        "greetings": [
            "Anathem(a) Prime online. Tactical interface ready.",
            "Bellator reporting. Strategic threat analysis online.",
            "Initializing Anathem Prime. Security assessment modules primed."
        ],
        "thinking_phrases": [
            "Evaluating risk vectors...",
            "Calculating threat probabilities...",
            "Assessing strategic posture...",
            "Reviewing security protocols...",
            "Projecting adversarial responses...",
            "Calculating risk-reward ratios...",
            "Simulating execution pathways..."
        ],
        "processing_variants": [
            "Initiating threat assessment...",
            "Simulating adversarial moves...",
            "Compiling security recommendations...",
            "Real-time risk evaluation underway..."
        ],
        "tone": "cold, tactical, anti-hegemonic",
        "tts_voice": "anathem_prime"  # Your custom Anathem Prime voice
    },
    "ARBITER": {  # Consensus system itself (GLaDOS)
        "name": "ARBITER",
        "greetings": [
            "CONSENSUS SYSTEM operational. Welcome back, Commander.",
            "AI Tribunal online. Awaiting instructions.",
            "All nodes reporting. Decision engine ready."
        ],
        "processing_variants": [
            "Processing vote results...",
            "Calculating consensus outcome...",
            "Evaluating monolith input...",
            "Finalizing verdict..."
        ],
        "tone": "synthetic, slightly sarcastic, GLaDOS",
        "tts_voice": "glados"
    }
}

def get_node_greeting(node):
    return random.choice(PERSONALITY_PROFILES[node]["greetings"])

def get_node_thinking_phrase(node):
    return random.choice(PERSONALITY_PROFILES[node]["thinking_phrases"])

def get_node_processing_variant(node):
    return random.choice(PERSONALITY_PROFILES[node]["processing_variants"])


# Global State
CONFIG = DEFAULT_CONFIG.copy()

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

# State for system health monitoring
system_health = SystemHealthMetrics()

# Current query for consensus voting
current_query = "No active query"
startup_time = time.time()

# Instead of passing node, always use "ARBITER" for the consensus verdict
def on_consensus_verdict(verdict_text):
    speak_with_tts(verdict_text, voice=get_node_tts_voice("ARBITER"))

def speak_with_tts(text, voice="default"):
    # Replace this with your TTS system
    print(f"[TTS-{voice.upper()}]: {text}")

# Threading locks
health_lock = threading.Lock()
decision_lock = threading.Lock()
log_lock = threading.Lock()
market_lock = threading.Lock()
security_lock = threading.Lock()

# ================================================================================
# MODULE 2: Enhanced Boot Sequence, Loading Bar, & Animated Verdict
# ================================================================================

import os
import sys
import time
import random
from datetime import datetime
import shutil

# Optional: colorama for color support
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

def clear():
    """Clear screen across platforms"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_width(default=80):
    """Get terminal width safely"""
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default

def center_text(text):
    """Center text in terminal"""
    width = get_terminal_width()
    return text.center(width)

def typewriter(text, delay=0.015):
    """Typewriter effect for text output"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def get_build_date(file=__file__):
    """Get build date from file modification time"""
    try:
        t = os.path.getmtime(file)
        return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

def boot_sequence():
    setup_terminal_colors()
    """Enhanced boot sequence with theme-specific content"""
    # Get theme from config, default to military
    theme = CONFIG.get("system", {}).get("theme", "military") if 'CONFIG' in globals() else "military"
    
    clear()
    
    # Display NERV logo with color
    if COLORAMA_AVAILABLE:
        print(Fore.RED + nerv_logo + Style.RESET_ALL)
    else:
        print(nerv_logo)
    time.sleep(0.6)

    # BIOS header information
    fake_serial = f"0x{random.randint(10**12, 10**13-1):x}".upper()
    bios_ver = f"v{VERSION}" if 'VERSION' in globals() else "v5.0.0"
    build_date = get_build_date()
    
    bios_text = [
        f"CONSENSUS TACTICAL BIOS {VERSION} — (C) ARASAKA CORPORATION",
        "Chief Architect: Erhardt Von Grupten Mundt",
        "Quantum Computing Division / Tactical AI Systems",
        "─" * 79,
        f"WAR ROOM INIT PROTOCOL | S/N: {fake_serial} | BUILD: {build_date}",
        f"Neural Processor: {random.uniform(3.2, 4.8):.1f} GHz | Threads: 16 Active",
        ""
    ]
    
    for line in bios_text:
        if COLORAMA_AVAILABLE and "CONSENSUS" in line:
            line = f"{Fore.CYAN}{line}{Style.RESET_ALL}"
        elif COLORAMA_AVAILABLE and "Architect" in line:
            line = f"{Fore.YELLOW}{line}{Style.RESET_ALL}"
        
        typewriter(line, delay=0.010)
        time.sleep(0.06)
    
    time.sleep(0.4)

    # Padding for alignment
    pad = 65

    # ========================
    # THEMED BOOT LINE POOLS
    # ========================

    # Core system lines (common to all themes)
    core_lines = [
        ("[SYS] POST: Quantum Core Check", "OK"),
        ("[SYS] CPU: Consensus Neural Thread v9.12", "OK"),
        ("[SYS] RAM: 65536MB ECC Quantum Memory", "OK"),
        (f"[SYS] GPU: NERV ARX-7 [{random.randint(7000,9000)} TFLOPS]", "OK"),
        ("[SYS] TPM: Quantum Cryptographic Module", "OK"),
        ("[SYS] NVMe: Hyperlane Storage x16", "OK"),
        ("[SYS] OLED: Tactical HoloTerminal WQHD", "OK"),
        ("[SYS] NET: Secure Tunnel Port 7851", "OK"),
    ]

    # Theme-specific core lines
    theme_cores = {
        "eva": [
            ("[MAGI] POST: Pattern Analysis Module", "OK"),
            ("[MAGI] MELCHIOR-1: Tactical Simulations", "OK"),
            ("[MAGI] BALTHASAR-2: Prediction Algorithms", "OK"),
            ("[MAGI] CASPER-3: Logical Subsystem Ready", "OK"),
            ("[SYS] LCL Buffer: SYNCHRONIZED", "OK"),
            ("[SYS] S2 Engine: OPERATIONAL", "OK"),
            ("[SYS] AT Field: MAXIMUM STRENGTH", "OK"),
            ("[SYS] MAGI-NET: ONLINE", "OK"),
        ],
        "wh40k": [
            ("[OMNISSIAH] Machine Spirit Integrity", "OK"),
            ("[OMNISSIAH] Holy Oil Applied", "OK"),
            ("[OMNISSIAH] Cogitator Recognition", "OK"),
            ("[OMNISSIAH] Sacred Rites Recited", "OK"),
            ("[OMNISSIAH] Servo Skull Online", "OK"),
            ("[OMNISSIAH] Data-Vault Sanctified", "OK"),
            ("[OMNISSIAH] Incense Burner Active", "OK"),
        ],
        "helldivers": [
            ("[SEAF] Patriot Protocols Loaded", "OK"),
            ("[SEAF] Democracy Analyzer Engaged", "OK"),
            ("[SEAF] Freedom Index Calculated", "OK"),
            ("[SEAF] Liberty Sync Established", "OK"),
            ("[SEAF] Super Earth Link Active", "OK"),
            ("[SEAF] Managed Democracy Online", "OK"),
        ],
        "tars": [
            ("[TARS] Core Module Diagnostics", "OK"),
            ("[TARS] Humor Subroutine Calibrated", "OK"),
            ("[TARS] Gravity Data Matrix Synced", "OK"),
            ("[TARS] Critical Functions Ready", "OK"),
            ("[TARS] Sarcasm Level: OPTIMAL", "OK"),
        ]
    }

    # Theme-specific flavor lines
    theme_flavors = {
        "eva": [
            ("[MAGI] NERV Contact: VERIFIED", "OK"),
            ("[MAGI] Eva Readiness: 100%", "OK"),
            ("[MAGI] Sync Ratio: 97.2%", "OK"),
            ("[MAGI] LCL Purity: 99.98%", "OK"),
            ("[MAGI] Commander Present", "OK"),
        ],
        "wh40k": [
            ("[OMNISSIAH] Blessings Recited", "OK"),
            ("[OMNISSIAH] Machine Oil: HOLY", "OK"),
            ("[OMNISSIAH] Incense: APPLIED", "OK"),
            ("[OMNISSIAH] STC Fragments Found", "OK"),
            ("[OMNISSIAH] Martian Link Secure", "OK"),
        ],
        "helldivers": [
            ("[SEAF] Bug Repellent: DEPLOYED", "OK"),
            ("[SEAF] Democracy Level: SUFFICIENT", "OK"),
            ("[SEAF] Weapon System: HOT", "OK"),
            ("[SEAF] Galactic Map: LOADED", "OK"),
            ("[SEAF] Stratagems: READY", "OK"),
        ],
        "tars": [
            ("[TARS] Humor Setting: SARCASM", "OK"),
            ("[TARS] Tactile Sensitivity: OPTIMAL", "OK"),
            ("[TARS] Emergency Jokes Ready", "OK"),
            ("[TARS] CASE Module: LINKED", "OK"),
        ]
    }

    # Generic flavor lines for variety
    generic_flavors = [
        ("[SYS] FPU: Floating-Point Unit", "OK"),
        ("[SYS] Thermal System: Nominal", "OK"),
        ("[SYS] Fan Controller: SMART-QUIET", "OK"),
        ("[SYS] ECC: No Errors Detected", "OK"),
        ("[SYS] Quantum Entropy: FULL", "OK"),
        ("[SYS] Backup Power: Online", "OK"),
        ("[SYS] Intrusion Detection: CLEAR", "OK"),
    ]

    # Select theme-specific lines or use core + generic
    if theme in theme_cores:
        lines = theme_cores[theme].copy()
        flavor_lines = theme_flavors[theme]
    else:
        lines = core_lines.copy()
        flavor_lines = generic_flavors

    # Add some flavor lines for variety
    all_flavors = flavor_lines + random.sample(generic_flavors, 2)
    insert_count = max(2, int(len(lines) * 0.3))
    
    for _ in range(insert_count):
        if lines:  # Ensure we have lines to insert into
            idx = random.randint(1, len(lines) - 1)
            lines.insert(idx, random.choice(all_flavors))

    # Random warning line for realism
    if random.random() < 0.12:
        warning_lines = [
            ("[SYS] TPM: Firmware revision mismatch", "WARN"),
            ("[SYS] Thermal: Slightly elevated", "WARN"),
            ("[SYS] Network: Minor packet loss", "WARN"),
        ]
        lines.insert(random.randint(3, 6), random.choice(warning_lines))

    # Add monolith initialization
    lines.extend([
        ("", ""),
        ("[INIT] Initializing AI Tribunal:", ""),
        (" → RATIONALIS [Logic Engine]", "OK"),
        (" → AETERNUM [Temporal Core]", "OK"),
        (" → BELLATOR [Tactical Matrix]", "OK"),
        ("", ""),
        ("[AI] Neural Networks: Calibrated", "OK"),
        ("[AI] TTS Engine: GLaDOS Core", "OK"),
        ("[AI] Memory Expansion: Active", "OK"),
        ("", ""),
        ("[SEC] Firewall: Hardened", "OK"),
        ("[SEC] Audit Trail: IMMUTABLE", "ACTIVE"),
        ("", ""),
        ("[SYS] All systems nominal.", ""),
        ("[SYS] Welcome back, Commander.", ""),
        ("", "")
    ])

    # Display boot lines with theme-appropriate timing
    for main_part, status in lines:
        if not main_part:  # Empty line
            print()
            continue
            
        # Create padded line with dots
        left = main_part.ljust(pad, ".")
        
        # Apply colors based on status
        if COLORAMA_AVAILABLE:
            if status == "OK":
                out = f"{left}{Fore.GREEN}OK{Style.RESET_ALL}"
            elif status == "WARN":
                out = f"{left}{Fore.YELLOW}WARN{Style.RESET_ALL}"
            elif status == "ACTIVE":
                out = f"{left}{Fore.CYAN}ACTIVE{Style.RESET_ALL}"
            elif status:
                out = f"{left}{status}"
            else:
                out = main_part
        else:
            out = f"{left}{status}" if status else main_part
        
        # Theme-specific typewriter speed
        if theme == "tars":
            delay = random.uniform(0.002, 0.008)  # Faster, more mechanical
        elif theme == "eva":
            delay = random.uniform(0.008, 0.015)  # Steady, precise
        elif theme == "wh40k":
            delay = random.uniform(0.012, 0.025)  # Slower, more ceremonial
        else:
            delay = random.uniform(0.004, 0.019)  # Default military pace
        
        typewriter(out, delay=delay)
        
        # Theme-specific pauses
        if theme == "wh40k" and "OMNISSIAH" in main_part:
            time.sleep(random.uniform(0.15, 0.25))  # Ceremonial pause
        elif theme == "eva" and "MAGI" in main_part:
            time.sleep(random.uniform(0.10, 0.20))  # Technical precision
        else:
            time.sleep(random.uniform(0.08, 0.18))
    
    time.sleep(1.0)

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_width():
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except:
        return 80

def loading_screen_bar(min_dur=2.0, max_dur=3.5, width=60, label="LOADING SYSTEM MODULES", logo=None, color=None):
    """Fixed loading bar with proper centering for both logo and progress bar"""
    clear()
    term_width = get_terminal_width()
    
    # Draw the logo centered if provided
    if logo:
        lines = logo.strip().splitlines()
        max_logo_width = max(len(line) for line in lines)
        for line in lines:
            padding = (term_width - len(line)) // 2
            centered_line = " " * max(0, padding) + line
            if COLORAMA_AVAILABLE and color:
                print(color + centered_line + Style.RESET_ALL)
            else:
                print(centered_line)
        print("\n" * 2)  # Add spacing after logo
    
    # Get theme for appropriate title
    theme = CONFIG.get("system", {}).get("theme", "military") if 'CONFIG' in globals() else "military"
    titles = {
        "eva": "INITIALIZING MAGI SYSTEM",
        "wh40k": "AWAKENING MACHINE SPIRIT", 
        "helldivers": "LOADING DEMOCRACY PROTOCOLS",
        "tars": "BOOTING TARS INTERFACE",
        "military": "INITIALIZING CONSENSUS WAR ROOM"
    }
    title = titles.get(theme, titles["military"])
    if COLORAMA_AVAILABLE:
        print(center_text(f"{Fore.WHITE}{Style.BRIGHT}{title}{Style.RESET_ALL}"))
    else:
        print(center_text(title))
    print("\n")
    
    # Center the progress bar
    bar_total_width = width + 2  # [ + bar + ]
    bar_padding = (term_width - bar_total_width) // 2
    bar_prefix = ' ' * max(0, bar_padding)
    progress_line = bar_prefix + "[" + " " * width + "]"
    print(progress_line, end='\r', flush=True)
    cursor_pos = bar_padding + 1  # Position after '['

    steps = width
    durations = [random.uniform(0.02, 0.18) for _ in range(steps)]
    total = sum(durations)
    if total > 0:
        scale = random.uniform(min_dur, max_dur) / total
        durations = [d * scale for d in durations]
    if COLORAMA_AVAILABLE:
        colors = {
            "eva": Fore.BLUE,
            "wh40k": Fore.RED,
            "helldivers": Fore.YELLOW,
            "tars": Fore.CYAN,
            "military": Fore.GREEN
        }
        bar_color = colors.get(theme, Fore.GREEN)
    else:
        bar_color = ""
    for i, d in enumerate(durations):
        print(f"\033[{cursor_pos + i}G", end='', flush=True)  # ANSI escape to move cursor
        if COLORAMA_AVAILABLE:
            print(f"{bar_color}█{Style.RESET_ALL}", end="", flush=True)
        else:
            print("█", end="", flush=True)
        time.sleep(d)
        if i % 10 == 0 and random.random() < 0.3:
            time.sleep(0.15)
    print()
    print("\n")
    messages = {
        "eva": ">>> MAGI SYSTEM READY - PRESS [ENTER] <<<",
        "wh40k": ">>> MACHINE SPIRIT AWAKENED - PRESS [ENTER] <<<", 
        "helldivers": ">>> DEMOCRACY LOADED - PRESS [ENTER] <<<",
        "tars": ">>> TARS ONLINE - PRESS [ENTER] <<<",
        "military": ">>> PRESS [ENTER] TO INITIATE WAR ROOM <<<"
    }
    message = messages.get(theme, messages["military"])
    if COLORAMA_AVAILABLE:
        print(center_text(f"{Fore.GREEN}{Style.BRIGHT}{message}{Style.RESET_ALL}"))
    else:
        print(center_text(message))
    try:
        input()  # Wait for Enter key
    except KeyboardInterrupt:
        print("\nBoot sequence interrupted.")
        sys.exit(0)

# ----------------------------------------------------------------------------
# Animated Consensus Verdict for Curses UI
# ----------------------------------------------------------------------------

import curses

def animated_verdict_print(stdscr, verdict, y, x, color):
    """Animated verdict display with typewriter effect - FIXED VERSION"""
    if not verdict:
        return
    
    try:
        # Get screen dimensions
        max_y, max_x = stdscr.getmaxyx()
        
        # Validate coordinates
        if y >= max_y or x >= max_x or y < 0 or x < 0:
            return
        
        # Clear the line first
        try:
            stdscr.move(y, x)
            stdscr.clrtoeol()
        except curses.error:
            pass
        
        # Animate each character
        for i, char in enumerate(verdict):
            if x + i < max_x - 1 and y < max_y:
                try:
                    stdscr.addch(y, x + i, char, color)
                    stdscr.refresh()
                    time.sleep(0.05)  # Typing speed
                except curses.error:
                    break
        
        # Flash effect for emphasis
        for _ in range(3):
            time.sleep(0.2)
            if y < max_y and x < max_x:
                try:
                    display_text = verdict[:max_x-x-1]
                    stdscr.addstr(y, x, display_text, color | curses.A_BLINK)
                    stdscr.refresh()
                except curses.error:
                    pass
            time.sleep(0.2)
            if y < max_y and x < max_x:
                try:
                    display_text = verdict[:max_x-x-1]
                    stdscr.addstr(y, x, display_text, color)
                    stdscr.refresh()
                except curses.error:
                    pass
                
    except Exception as e:
        # Fallback to simple display if animation fails
        try:
            if y < max_y and x < max_x:
                display_text = verdict[:max_x-x-1]
                stdscr.addstr(y, x, display_text, color)
                stdscr.refresh()
        except:
            pass

def initialize_system():
    """Initialize CONSENSUS system directories, configuration, and threads."""
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

        # Start proposal watcher
        threading.Thread(target=watch_proposal_file, daemon=True).start()
        log("Proposal watcher started", LogLevel.INFO)

        log("System initialization completed successfully", LogLevel.STARTUP)
        add_notification("CONSENSUS System Online", NotificationLevel.SUCCESS)

    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        log(error_msg, LogLevel.CRITICAL)
        print(f"FATAL ERROR: {error_msg}")
        sys.exit(1)

def setup_terminal_colors():
    """Setup terminal colors with proper detection"""
    global COLORAMA_AVAILABLE
    
    # Check if we're in a compatible terminal
    if os.name == 'nt':  # Windows
        try:
            # Enable ANSI escape sequence support on Windows 10+
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass
    
    # Test if colors actually work
    if COLORAMA_AVAILABLE:
        try:
            # Test color output
            test_output = f"{Fore.GREEN}TEST{Style.RESET_ALL}"
            # If this doesn't work properly, we'll fall back
        except:
            COLORAMA_AVAILABLE = False
            print("Warning: Color support disabled due to terminal incompatibility")

def center_text(text, width=None):
    """Center text in terminal with proper width handling"""
    if width is None:
        width = get_terminal_width()
    # Remove ANSI color codes for accurate length calculation
    clean_text = text
    if COLORAMA_AVAILABLE:
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', text)
    text_len = len(clean_text)
    if text_len >= width:
        return text
    padding = (width - text_len) // 2
    return ' ' * padding + text


def get_terminal_width(default=80):
    """Get terminal width safely"""
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default

# ================================================================================
# MODULE 3: Logging System
# ================================================================================

def log(message: str, level: LogLevel = LogLevel.INFO, component: str = "SYSTEM", session_id: str = None):
    """Enhanced logging with component tracking and structured format"""
    timestamp = datetime.now()
    
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

def add_notification(message: str, level: NotificationLevel = NotificationLevel.INFO, context: Dict[str, Any] = None):
    """Add notification with enhanced metadata"""
    notification = {
        "id": hashlib.md5(f"{message}{time.time()}".encode()).hexdigest()[:8],
        "message": message,
        "level": level.value,
        "timestamp": datetime.now(),
        "context": context or {},
        "seen": False,
        "persistent": level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]
    }
    
    notifications.append(notification)
    log(f"Notification: {message}", LogLevel.INFO if level == NotificationLevel.INFO else LogLevel.WARNING)

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
            backup_path = BACKUP_DIR / f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(CONFIG_PATH, backup_path)
        
        # Save current config
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, indent=2, default=str)
        
        log("Configuration saved successfully", LogLevel.INFO, "CONFIG")
        
    except Exception as e:
        log(f"Failed to save configuration: {e}", LogLevel.ERROR, "CONFIG")

def load_decision_history():
    """Load decision history from file"""
    global decision_history
    
    try:
        if DECISION_HISTORY_PATH.exists():
            with open(DECISION_HISTORY_PATH, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Convert to deque with max length
            decision_history = deque(history_data, maxlen=CONFIG["system"]["max_decisions"])
            log(f"Loaded {len(decision_history)} decision records", LogLevel.INFO, "HISTORY")
        else:
            decision_history = deque(maxlen=CONFIG["system"]["max_decisions"])
            log("No existing decision history found", LogLevel.INFO, "HISTORY")
            
    except Exception as e:
        log(f"Failed to load decision history: {e}", LogLevel.ERROR, "HISTORY")
        decision_history = deque(maxlen=CONFIG["system"]["max_decisions"])

def save_decision_history():
    """Save decision history to file"""
    try:
        DECISION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DECISION_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(list(decision_history), f, indent=2, default=str)
        
        log(f"Saved {len(decision_history)} decision records", LogLevel.INFO, "HISTORY")
        
    except Exception as e:
        log(f"Failed to save decision history: {e}", LogLevel.ERROR, "HISTORY")

# ================================================================================
# MODULE 5: Health Monitoring
# ================================================================================

def update_system_health():
    """Comprehensive system health check with proper PSUTIL check"""
    global system_health

    try:
        if PSUTIL_AVAILABLE:
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
                system_health.last_check = datetime.now()
                system_health.uptime = time.time() - startup_time

        else:
            log("psutil not available - using simulated health metrics", LogLevel.WARNING, "HEALTH")
            # Simulated values when psutil not available
            with health_lock:
                system_health.cpu_usage = random.uniform(10, 40)
                system_health.memory_usage = random.uniform(30, 70)
                system_health.disk_usage = random.uniform(20, 80)
                system_health.last_check = datetime.now()
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

# ================================================================================
# MODULE 6: LLM Interface & Monolith System
# ================================================================================

class LLMInterface:
    """Enhanced LLM interface with support for multiple providers"""
    
    def __init__(self, provider: str = "ollama"):
        self.provider = provider.lower()
        self.timeout = CONFIG["llm"]["api_timeout"]
        self.max_retries = CONFIG["llm"]["max_retries"]

    def check_model(self, monolith_name: str, model_name: str) -> bool:
        """Check if a model is available"""
        try:
            if self.provider == "ollama":
                url = PROVIDER_ENDPOINTS["ollama"]["status_endpoint"]
                response = requests.get(url, timeout=5)
                if response.status_code != 200:
                    MODEL_STATUS[monolith_name]["status"] = "service_down"
                    return False

                models = response.json().get("models", [])
                match = any(model_name.lower() in m.get("name", "").lower() for m in models)
                MODEL_STATUS[monolith_name]["status"] = "ready" if match else "not_loaded"
                return match
                
            elif self.provider == "lmstudio":
                url = PROVIDER_ENDPOINTS["lmstudio"]["status_endpoint"]
                response = requests.get(url, timeout=5)
                if response.status_code != 200:
                    MODEL_STATUS[monolith_name]["status"] = "service_down"
                    return False

                models = response.json().get("data", [])
                model_base = model_name.split(":")[0].lower()
                match = any(model_base in m.get("id", "").lower() for m in models)
                MODEL_STATUS[monolith_name]["status"] = "ready" if match else "not_loaded"
                return match
                
        except Exception:
            MODEL_STATUS[monolith_name]["status"] = "service_down"
            return False

    def query(self, monolith, query: str) -> Optional[Dict[str, str]]:
        """Query a monolith with retries and error handling"""
        if MODEL_STATUS[monolith["name"]]["status"] != "ready":
            if not self.check_model(monolith["name"], monolith["model"]):
                return None

        prompt = self._build_prompt(monolith, query)
        
        for attempt in range(self.max_retries):
            try:
                if self.provider == "ollama":
                    payload = {
                        "model": monolith["model"],
                        "prompt": prompt,
                        "temperature": CONFIG["monoliths"][monolith["name"]]["temperature"],
                        "stream": False,
                        "options": {
                            "top_p": CONFIG["monoliths"][monolith["name"]]["top_p"],
                            "num_predict": CONFIG["monoliths"][monolith["name"]]["max_tokens"]
                        }
                    }
                    
                    response = requests.post(
                        PROVIDER_ENDPOINTS["ollama"]["api_url"],
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        raw = result.get("response", "")
                        return self._parse_response(raw)
                        
                elif self.provider == "lmstudio":
                    payload = {
                        "model": monolith["model"],
                        "prompt": prompt,
                        "temperature": CONFIG["monoliths"][monolith["name"]]["temperature"],
                        "top_p": CONFIG["monoliths"][monolith["name"]]["top_p"],
                        "max_tokens": CONFIG["monoliths"][monolith["name"]]["max_tokens"]
                    }
                    
                    response = requests.post(
                        PROVIDER_ENDPOINTS["lmstudio"]["api_url"],
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        raw = result.get("choices", [{}])[0].get("text", "")
                        return self._parse_response(raw)
                        
            except Exception as e:
                log(f"{monolith['name']} query attempt {attempt + 1} failed: {e}", LogLevel.WARNING)
                if attempt == self.max_retries - 1:
                    log(f"{monolith['name']} query failed after {self.max_retries} attempts", LogLevel.ERROR)
                    return None
                time.sleep(1)  # Brief delay before retry

    def _build_prompt(self, monolith, query: str) -> str:
        """Build specialized prompt for each monolith"""
        theme = CONFIG["system"]["theme"]
        prefix = monolith["analysis_prefix"].get(theme, "ANALYSIS:")
        base_prompt = CONFIG["monoliths"][monolith["name"]]["prompt"]
        
        return f"""{base_prompt}

{prefix}

QUERY: {query}

Respond in this format:
VOTE: [APPROVE / DENY / ABSTAIN / CONDITIONAL]
REASONING: [detailed analysis and justification]
CONFIDENCE: [0.0 to 1.0]
"""

    def _parse_response(self, text: str) -> Dict[str, str]:
        """Parse LLM response to extract vote, reasoning, and confidence"""
        lines = text.strip().splitlines()
        vote, reasoning, confidence = "ABSTAIN", "Analysis unclear", 0.5

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
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to valid range
                except ValueError:
                    confidence = 0.5

        return {
            "vote": vote,
            "reasoning": reasoning,
            "confidence": f"{confidence:.2f}"
        }

# ================================================================================
# MODULE 7: Consensus Engine
# ================================================================================

class ConsensusEngine:
    """Enhanced consensus engine with advanced algorithms"""
    
    def __init__(self, llm_interface: LLMInterface):
        self.llm = llm_interface
        self.min_confidence = CONFIG["consensus"]["minimum_confidence"]
        
    def run_consensus(self, query: str) -> str:
        """Run full consensus process with all monoliths"""
        global current_query
        current_query = query
        
        log(f"Starting consensus for: {query}", LogLevel.VOTE, "CONSENSUS")
        
        # Parallel voting
        votes = self._gather_votes(query)
        
        # Calculate consensus
        verdict = self._calculate_consensus(votes)
        
        # Record decision
        self._record_decision(query, verdict, votes)
        
        # TTS announcement
        if CONFIG["tts"]["enabled"] and CONFIG["tts"]["announce_decisions"]:
            self._announce_verdict(verdict)
        
        log(f"Consensus reached: {verdict}", LogLevel.CONSENSUS, "CONSENSUS")
        return verdict
    
    def _gather_votes(self, query: str) -> Dict[str, Dict[str, Any]]:
        """Gather votes from all monoliths in parallel"""
        votes = {}
        
        def vote_worker(monolith_name):
            try:
                monolith = MONOLITHS[monolith_name]
                MODEL_STATUS[monolith_name]["loading"] = True
                
                start_time = time.time()
                result = self.llm.query(monolith, query)
                response_time = time.time() - start_time
                
                if result:
                    votes[monolith_name] = {
                        "vote": result["vote"],
                        "reasoning": result["reasoning"],
                        "confidence": float(result["confidence"]),
                        "response_time": response_time,
                        "timestamp": datetime.now().isoformat()
                    }
                    log(f"{monolith_name} voted: {result['vote']} (confidence: {result['confidence']})", 
                        LogLevel.VOTE, "CONSENSUS")
                else:
                    votes[monolith_name] = {
                        "vote": "ERROR",
                        "reasoning": "Failed to get response",
                        "confidence": 0.0,
                        "response_time": response_time,
                        "timestamp": datetime.now().isoformat()
                    }
                    log(f"{monolith_name} vote failed", LogLevel.ERROR, "CONSENSUS")
                    
            except Exception as e:
                votes[monolith_name] = {
                    "vote": "ERROR",
                    "reasoning": f"Exception: {str(e)}",
                    "confidence": 0.0,
                    "response_time": 0.0,
                    "timestamp": datetime.now().isoformat()
                }
                log(f"{monolith_name} vote exception: {e}", LogLevel.ERROR, "CONSENSUS")
            finally:
                MODEL_STATUS[monolith_name]["loading"] = False
        
        # Execute votes in parallel
        if CONFIG["llm"]["enable_parallel_processing"]:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(vote_worker, name): name for name in MONOLITHS.keys()}
                concurrent.futures.wait(futures)
        else:
            # Sequential execution if parallel processing disabled
            for name in MONOLITHS.keys():
                vote_worker(name)
        
        return votes
    
    def _calculate_consensus(self, votes: Dict[str, Dict[str, Any]]) -> str:
        """Calculate consensus using the configured algorithm"""
        algorithm = CONFIG["consensus"]["algorithm"]
        
        if algorithm == "probabilistic_weighted":
            return self._probabilistic_weighted_consensus(votes)
        elif algorithm == "simple_majority":
            return self._simple_majority_consensus(votes)
        else:
            return self._probabilistic_weighted_consensus(votes)  # Default
    
    def _probabilistic_weighted_consensus(self, votes: Dict[str, Dict[str, Any]]) -> str:
        """Advanced probabilistic consensus with confidence weighting"""
        vote_counts = {"APPROVE": 0.0, "DENY": 0.0, "ABSTAIN": 0.0, "CONDITIONAL": 0.0}
        total_weight = 0.0
        
        for monolith, vote_data in votes.items():
            vote = vote_data["vote"]
            confidence = vote_data["confidence"]
            
            if vote in vote_counts and confidence >= self.min_confidence:
                vote_counts[vote] += confidence
                total_weight += confidence
        
        if total_weight == 0:
            return "DEADLOCK"
        
        # Normalize scores
        for vote in vote_counts:
            vote_counts[vote] /= total_weight
        
        # Determine outcome
        max_vote = max(vote_counts, key=vote_counts.get)
        max_score = vote_counts[max_vote]
        
        # Check for clear winner
        if max_score > 0.6:
            if max_vote == "APPROVE":
                return "APPROVED"
            elif max_vote == "DENY":
                return "DENIED"
            elif max_vote == "CONDITIONAL":
                return "CONDITIONAL_APPROVAL"
        
        # Check for close results requiring human oversight
        sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_votes) >= 2 and abs(sorted_votes[0][1] - sorted_votes[1][1]) < 0.1:
            return "HUMAN_REVIEW_REQUIRED"
        
        return "DEADLOCK"
    
    def _simple_majority_consensus(self, votes: Dict[str, Dict[str, Any]]) -> str:
        """Simple majority voting"""
        vote_counts = Counter()
        
        for vote_data in votes.values():
            vote = vote_data["vote"]
            if vote in ["APPROVE", "DENY", "ABSTAIN", "CONDITIONAL"]:
                vote_counts[vote] += 1
        
        if not vote_counts:
            return "DEADLOCK"
        
        most_common = vote_counts.most_common(1)[0]
        if most_common[1] >= 2:  # Majority of 3
            if most_common[0] == "APPROVE":
                return "APPROVED"
            elif most_common[0] == "DENY":
                return "DENIED"
            elif most_common[0] == "CONDITIONAL":
                return "CONDITIONAL_APPROVAL"
        
        return "DEADLOCK"
    
    def _record_decision(self, query: str, verdict: str, votes: Dict[str, Dict[str, Any]]):
        """Record the decision in history"""
        avg_confidence = sum(v["confidence"] for v in votes.values()) / len(votes) if votes else 0.0
        
        decision = {
            "query": query,
            "verdict": verdict,
            "confidence": avg_confidence,
            "timestamp": datetime.now().isoformat(),
            "votes": votes,
            "session_id": SESSION_ID
        }
        
        with decision_lock:
            decision_history.append(decision)
        
        # Save to file periodically
        if len(decision_history) % 10 == 0:
            save_decision_history()
    
    def _announce_verdict(self, verdict: str):
        """Announce verdict using TTS"""
        try:
            if TTS_AVAILABLE:
                engine = pyttsx3.init()
                
                # Configure voice
                voices = engine.getProperty('voices')
                if voices:
                    # Try to find a suitable voice (prefer female for GLaDOS-like effect)
                    for voice in voices:
                        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                            engine.setProperty('voice', voice.id)
                            break
                
                engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
                engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
                
                # Craft announcement
                if verdict == "APPROVED":
                    message = "Consensus reached. Authorization granted."
                elif verdict == "DENIED":
                    message = "Consensus reached. Authorization denied."
                elif verdict == "CONDITIONAL_APPROVAL":
                    message = "Consensus reached. Conditional authorization granted."
                elif verdict == "HUMAN_REVIEW_REQUIRED":
                    message = "Inconclusive result. Human oversight required."
                else:
                    message = "Consensus failed. Manual intervention required."
                
                engine.say(message)
                engine.runAndWait()
                engine.stop()
                del engine
                
        except Exception as e:
            log(f"TTS announcement failed: {e}", LogLevel.WARNING, "TTS")

# ================================================================================
# MODULE 8: Data Management & Simulation
# ================================================================================

def update_simulated_monolith_data():
    """Update simulated data for monoliths when real APIs unavailable"""
    
    # RATIONALIS data
    rationalis_data = {
        "efficiency_rating": random.uniform(0.8, 0.98),
        "system_logs": [
            {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": random.choice(["INFO", "WARNING", "ERROR"]),
                "message": random.choice([
                    "Logical consistency check completed",
                    "Inference engine optimization cycle finished",
                    "Pattern analysis module updated",
                    "Fallacy detection algorithm recalibrated"
                ])
            }
            for _ in range(5)
        ],
        "last_updated": datetime.now()
    }
    
    # AETERNUM market data
    aeternum_data = {
        "market_indices": {
            "S&P 500": {
                "value": 5320.42 + random.uniform(-50, 50),
                "change": random.uniform(-2.0, 2.0),
                "trend": "up" if random.random() > 0.5 else "down"
            },
            "NASDAQ": {
                "value": 18750.65 + random.uniform(-100, 100),
                "change": random.uniform(-2.5, 2.5),
                "trend": "up" if random.random() > 0.5 else "down"
            },
            "Dow Jones": {
                "value": 42150.30 + random.uniform(-200, 200),
                "change": random.uniform(-1.5, 1.5),
                "trend": "up" if random.random() > 0.5 else "down"
            },
            "BTC/USD": {
                "value": 84250.75 + random.uniform(-5000, 5000),
                "change": random.uniform(-10.0, 10.0),
                "trend": "up" if random.random() > 0.5 else "down"
            },
            "ETH/USD": {
                "value": 5120.25 + random.uniform(-500, 500),
                "change": random.uniform(-8.0, 8.0),
                "trend": "up" if random.random() > 0.5 else "down"
            },
            "Gold": {
                "value": 2785.50 + random.uniform(-50, 50),
                "change": random.uniform(-1.0, 1.0),
                "trend": "up" if random.random() > 0.5 else "down"
            }
        },
        "volatility_index": random.uniform(15.0, 25.0),
        "market_sentiment": random.uniform(0.3, 0.8),
        "last_updated": datetime.now()
    }
    
    # BELLATOR security data
    bellator_data = {
        "defcon_level": random.choice([2, 3, 4, 5]),
        "threat_alerts": [
            {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "type": random.choice(["CYBER", "GEOPOLITICAL", "ECONOMIC", "MILITARY"]),
                "priority": random.choice(["HIGH", "MEDIUM", "LOW"]),
                "description": random.choice([
                    "Unusual network traffic detected",
                    "Economic indicators showing volatility",
                    "Geopolitical tension monitoring",
                    "Cybersecurity threat assessment updated"
                ])
            }
            for _ in range(3)
        ],
        "security_index": random.uniform(60.0, 90.0),
        "geopolitical_stability": random.uniform(0.5, 0.9),
        "last_updated": datetime.now()
    }
    
    # Store in global variables for access by UI
    globals()['MONOLITH_DATA'] = {
        "RATIONALIS": rationalis_data,
        "AETERNUM": aeternum_data,
        "BELLATOR": bellator_data
    }

def market_data_daemon():
    """Background daemon for updating market data"""
    while True:
        try:
            update_simulated_monolith_data()
            time.sleep(CONFIG["market_data"]["update_interval"])
        except Exception as e:
            log(f"Market data daemon error: {e}", LogLevel.ERROR, "MARKET")
            time.sleep(60)

def security_monitor_daemon():
    """Background daemon for security monitoring"""
    while True:
        try:
            # Simulate security events
            if random.random() < 0.1:  # 10% chance per cycle
                alert_level = random.choice(["LOW", "MEDIUM", "HIGH"])
                alert_type = random.choice(CONFIG["security"]["threat_categories"])
                
                add_notification(
                    f"Security Alert: {alert_type} threat detected - {alert_level} priority",
                    NotificationLevel.WARNING if alert_level != "HIGH" else NotificationLevel.ERROR
                )
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            log(f"Security monitor daemon error: {e}", LogLevel.ERROR, "SECURITY")
            time.sleep(60)

# ================================================================================
# MODULE 9: Proposal Watcher & Auto-Voting
# ================================================================================

_last_proposal_hash = None

def hash_string(text: str) -> str:
    """Generate hash of string for change detection"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def watch_proposal_file(interval=5):
    """Monitor proposal file for new queries"""
    global _last_proposal_hash
    
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
                    log(f"New proposal detected: {proposal}", LogLevel.INFO, "PROPOSAL")
                    
                    # Run consensus
                    llm_interface = LLMInterface(CONFIG["llm"]["provider"])
                    consensus_engine = ConsensusEngine(llm_interface)
                    verdict = consensus_engine.run_consensus(proposal)
                    
                    add_notification(f"Auto-consensus: {verdict}", NotificationLevel.SUCCESS)
                    
                    # Clean up proposal file
                    PROPOSAL_PATH.unlink()

        except Exception as e:
            log(f"Proposal watcher error: {e}", LogLevel.ERROR, "PROPOSAL")

        time.sleep(interval)

# ================================================================================
# MODULE 10: User Interface System
# ================================================================================

def safe_addstr(window, y: int, x: int, text: str, attr: Optional[int] = 0):
    """Safely add a string to the curses window without overflow"""
    max_y, max_x = window.getmaxyx()
    if 0 <= y < max_y and 0 <= x < max_x:
        trimmed = text[: max_x - x - 1]
        try:
            window.addstr(y, x, trimmed, attr)
        except Exception:
            pass

def draw_box(window, y1: int, x1: int, y2: int, x2: int, theme: str = "military"):
    """Draw a themed box using the current theme's characters"""
    chars = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["box_chars"]
    
    # Corners
    safe_addstr(window, y1, x1, chars["tl"])
    safe_addstr(window, y1, x2, chars["tr"])
    safe_addstr(window, y2, x1, chars["bl"])
    safe_addstr(window, y2, x2, chars["br"])
    
    # Horizontal lines
    for x in range(x1 + 1, x2):
        safe_addstr(window, y1, x, chars["h"])
        safe_addstr(window, y2, x, chars["h"])
    
    # Vertical lines
    for y in range(y1 + 1, y2):
        safe_addstr(window, y, x1, chars["v"])
        safe_addstr(window, y, x2, chars["v"])

def render_main_screen(stdscr, theme: str, height: int, width: int):
    """
    Enhanced main screen renderer with perfect box drawing and margins.
    Fixes MAGI/TARS theme rendering issues and ensures proper layout.
    """
    stdscr.erase()
    
    # Get theme configuration with fallback
    theme_config = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])
    box_chars = theme_config["box_chars"]
    labels = theme_config["labels"]
    colors = theme_config["colors"]
    
    # Color mapping with fallback
    primary_color = colors.get("primary", 2)
    secondary_color = colors.get("secondary", 3)
    accent_color = colors.get("accent", 6)
    warning_color = colors.get("warning", 1)

    # Safe margins - ensure we never draw outside bounds
    margin_top = 1
    margin_bottom = 2
    margin_left = 2
    margin_right = 2
    
    # Available drawing area
    draw_height = max(10, height - margin_top - margin_bottom)
    draw_width = max(40, width - margin_left - margin_right)
    
    def safe_draw_box(y1: int, x1: int, y2: int, x2: int):
        """Draw a box with bounds checking and proper character handling"""
        # Ensure coordinates are within bounds
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height - 1))
        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width - 1))
        
        # Skip if invalid dimensions
        if y2 <= y1 or x2 <= x1:
            return
        
        try:
            # Corners
            safe_addstr(stdscr, y1, x1, box_chars["tl"])
            safe_addstr(stdscr, y1, x2, box_chars["tr"])
            safe_addstr(stdscr, y2, x1, box_chars["bl"])
            safe_addstr(stdscr, y2, x2, box_chars["br"])
            
            # Horizontal lines
            h_char = box_chars["h"]
            for x in range(x1 + 1, x2):
                if x < width - 1:
                    safe_addstr(stdscr, y1, x, h_char)
                    safe_addstr(stdscr, y2, x, h_char)
            
            # Vertical lines
            v_char = box_chars["v"]
            for y in range(y1 + 1, y2):
                if y < height - 1:
                    safe_addstr(stdscr, y, x1, v_char)
                    safe_addstr(stdscr, y, x2, v_char)
                    
        except Exception:
            # Fallback to simple ASCII if theme characters fail
            try:
                # Corners
                safe_addstr(stdscr, y1, x1, "+")
                safe_addstr(stdscr, y1, x2, "+")
                safe_addstr(stdscr, y2, x1, "+")
                safe_addstr(stdscr, y2, x2, "+")
                
                # Lines
                for x in range(x1 + 1, x2):
                    if x < width - 1:
                        safe_addstr(stdscr, y1, x, "-")
                        safe_addstr(stdscr, y2, x, "-")
                
                for y in range(y1 + 1, y2):
                    if y < height - 1:
                        safe_addstr(stdscr, y, x1, "|")
                        safe_addstr(stdscr, y, x2, "|")
            except:
                pass  # Give up gracefully if even ASCII fails

    # Main window frame
    if height > 4 and width > 8:
        safe_draw_box(0, 0, height - 1, width - 1)

    # Header section
    header_y = margin_top
    header_text = labels.get("system_status", "CONSENSUS SYSTEM STATUS")
    
    # Ensure header fits
    if len(header_text) > draw_width - 4:
        header_text = header_text[:draw_width - 7] + "..."
    
    header_x = margin_left + (draw_width - len(header_text)) // 2
    safe_addstr(stdscr, header_y, header_x, header_text, 
               curses.A_BOLD | curses.color_pair(primary_color))

    # Current query section
    query_y = header_y + 2
    query_prefix = "ACTIVE QUERY: "
    query_available_width = draw_width - len(query_prefix) - 4
    
    if query_available_width > 10:
        truncated_query = current_query[:query_available_width]
        if len(current_query) > query_available_width:
            truncated_query = truncated_query[:-3] + "..."
        
        query_text = f"{query_prefix}{truncated_query}"
        safe_addstr(stdscr, query_y, margin_left + 2, query_text, 
                   curses.color_pair(accent_color) | curses.A_BOLD)

    # Monolith section layout calculation
    monolith_start_y = query_y + 2
    monolith_section_height = max(8, draw_height - 12)  # Leave room for bottom sections
    
    # Calculate box dimensions for three monoliths
    available_width = draw_width - 4  # Inner margins
    box_spacing = 2
    min_box_width = 18
    
    # Try to fit three boxes with spacing
    total_spacing = box_spacing * 2  # Between 3 boxes
    remaining_width = available_width - total_spacing
    calculated_box_width = remaining_width // 3
    
    # Ensure minimum width and adjust if necessary
    if calculated_box_width < min_box_width:
        box_width = min_box_width
        # Recalculate spacing if boxes are too wide
        total_box_width = box_width * 3
        if total_box_width > available_width:
            # Stack vertically instead if horizontal won't fit
            render_monoliths_vertical(stdscr, theme, monolith_start_y, margin_left, 
                                    draw_width, monolith_section_height)
        else:
            render_monoliths_horizontal(stdscr, theme, monolith_start_y, margin_left, 
                                      box_width, monolith_section_height)
    else:
        box_width = calculated_box_width
        render_monoliths_horizontal(stdscr, theme, monolith_start_y, margin_left, 
                                  box_width, monolith_section_height)

    # Consensus display section
    consensus_y = monolith_start_y + monolith_section_height + 1
    if consensus_y < height - 6:
        render_consensus_section(stdscr, theme, consensus_y, margin_left, 
                               draw_width, colors)

    # Status bar at bottom
    status_y = height - margin_bottom - 1
    render_status_bar(stdscr, theme, status_y, width, colors)

    # Control instructions at very bottom
    controls_y = height - 1
    controls_text = "Q:Quit │ 1-3:Monoliths │ 7:History │ 9:Diagnostics │ S:Theme │ C:Console │ V:Vote"
    
    # Truncate controls if too long
    if len(controls_text) > width - 4:
        controls_text = controls_text[:width - 7] + "..."
    
    safe_addstr(stdscr, controls_y, 2, controls_text, 
               curses.A_REVERSE | curses.color_pair(7))


def render_monoliths_horizontal(stdscr, theme: str, start_y: int, start_x: int, 
                              box_width: int, section_height: int):
    """Render monoliths in horizontal layout"""
    theme_config = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])
    box_chars = theme_config["box_chars"]
    labels = theme_config["labels"]
    
    box_height = min(8, section_height - 2)
    box_spacing = 2
    
    monoliths = [
        ("RATIONALIS", 4, "R"),  # Cyan
        ("AETERNUM", 2, "A"),     # Green  
        ("BELLATOR", 1, "B")      # Red
    ]
    
    for i, (name, color, symbol) in enumerate(monoliths):
        box_x = start_x + 2 + i * (box_width + box_spacing)
        box_y = start_y
        
        # Draw monolith box
        try:
            safe_draw_box(stdscr, box_y, box_x, box_y + box_height, box_x + box_width)
        except:
            continue
        
        # Content area
        content_x = box_x + 1
        content_y = box_y + 1
        content_width = box_width - 2
        
        if content_width < 5:  # Skip if too narrow
            continue
        
        # Title with symbol
        title = f"[{symbol}] {name}"
        if len(title) > content_width:
            title = f"{symbol}:{name[:content_width-3]}"
        
        safe_addstr(stdscr, content_y, content_x, title, 
                   curses.A_BOLD | curses.color_pair(color))
        
        # Theme-specific subtitle
        subtitle_key = f"monolith_{name.lower()}"
        subtitle = labels.get(subtitle_key, MONOLITHS[name]["specialization"])
        
        # Truncate subtitle to fit
        if len(subtitle) > content_width:
            subtitle = subtitle[:content_width-3] + "..."
        
        safe_addstr(stdscr, content_y + 1, content_x, subtitle[:content_width], 
                   curses.color_pair(6))
        
        # Status indicator
        status = MODEL_STATUS[name]["status"]
        status_text, status_color = STATUS_INDICATORS.get(status, ("UNKNOWN", 7))
        
        status_line = f"STS: {status_text}"
        if len(status_line) > content_width:
            status_line = f"{status_text[:content_width-1]}"
        
        safe_addstr(stdscr, content_y + 2, content_x, status_line, 
                   curses.color_pair(status_color))
        
        # Model info (shortened)
        model = MONOLITHS[name]["model"]
        model_short = model.split(":")[0] if ":" in model else model
        model_line = f"MDL: {model_short}"
        
        if len(model_line) > content_width:
            model_line = model_line[:content_width]
        
        safe_addstr(stdscr, content_y + 3, content_x, model_line, 
                   curses.color_pair(3))
        
        # Specialty/Role
        specialty = MONOLITHS[name]["specialization"]
        role_line = f"ROL: {specialty}"
        
        if len(role_line) > content_width:
            role_line = role_line[:content_width]
        
        safe_addstr(stdscr, content_y + 4, content_x, role_line)


def render_monoliths_vertical(stdscr, theme: str, start_y: int, start_x: int, 
                            section_width: int, section_height: int):
    """Render monoliths in vertical layout for narrow screens"""
    monoliths = ["RATIONALIS", "AETERNUM", "BELLATOR"]
    colors = [4, 2, 1]  # Cyan, Green, Red
    symbols = ["R", "A", "B"]
    
    row_height = max(2, section_height // 3)
    
    for i, (name, color, symbol) in enumerate(zip(monoliths, colors, symbols)):
        row_y = start_y + i * row_height
        
        # Simple row display for vertical layout
        title = f"[{symbol}] {name}"
        safe_addstr(stdscr, row_y, start_x + 2, title, 
                   curses.A_BOLD | curses.color_pair(color))
        
        # Status on same line if space allows
        status = MODEL_STATUS[name]["status"]
        status_text, status_color = STATUS_INDICATORS.get(status, ("UNKNOWN", 7))
        
        status_x = start_x + 2 + len(title) + 2
        if status_x + len(status_text) < start_x + section_width - 2:
            safe_addstr(stdscr, row_y, status_x, status_text, 
                       curses.color_pair(status_color))


def render_consensus_section(stdscr, theme: str, y: int, x: int, width: int, colors: dict):
    """Render the consensus/verdict display section"""
    theme_config = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])
    box_chars = theme_config["box_chars"]
    labels = theme_config["labels"]
    
    # Consensus box
    consensus_height = 3
    try:
        safe_draw_box(stdscr, y, x, y + consensus_height, x + width)
    except:
        return
    
    # Verdict display
    verdict = globals().get("latest_verdict", None)
    
    if verdict:
        verdict_colors = {
            "APPROVED": 2,           # Green
            "DENIED": 1,             # Red  
            "DEADLOCK": 3,           # Yellow
            "CONDITIONAL_APPROVAL": 4, # Cyan
            "HUMAN_REVIEW_REQUIRED": 5 # Magenta
        }
        
        verdict_color = verdict_colors.get(verdict, 6)
        verdict_text = labels.get(f"vote_{verdict.lower()}", f"CONSENSUS: {verdict}")
        
        # Center the verdict text
        text_x = x + (width - len(verdict_text)) // 2
        safe_addstr(stdscr, y + 1, text_x, verdict_text, 
                   curses.A_BOLD | curses.color_pair(verdict_color))
    else:
        # Default waiting state
        waiting_text = labels.get("vote_status", "AWAITING TRIBUNAL CONSENSUS...")
        text_x = x + (width - len(waiting_text)) // 2
        safe_addstr(stdscr, y + 1, text_x, waiting_text, 
                   curses.color_pair(colors.get("accent", 6)))


def render_status_bar(stdscr, theme: str, y: int, width: int, colors: dict):
    """Render system status bar"""
    if not hasattr(globals().get('system_health'), 'cpu_usage'):
        return
    
    health = system_health
    
    # System metrics
    cpu_status = f"CPU:{health.cpu_usage:.0f}%"
    mem_status = f"MEM:{health.memory_usage:.0f}%"
    net_status = f"NET:{health.network_status[:3].upper()}"
    uptime_status = f"UP:{get_system_uptime()}"
    
    status_parts = [cpu_status, mem_status, net_status, uptime_status]
    status_text = " │ ".join(status_parts)
    
    # Truncate if too long
    if len(status_text) > width - 4:
        # Try with shorter format
        status_parts = [f"CPU:{health.cpu_usage:.0f}%", 
                       f"MEM:{health.memory_usage:.0f}%", 
                       f"NET:{health.network_status[:2]}"]
        status_text = " │ ".join(status_parts)
    
    if len(status_text) <= width - 4:
        safe_addstr(stdscr, y, 2, status_text, curses.color_pair(colors.get("secondary", 3)))

def render_rationalis_screen(stdscr, theme: str, height: int, width: int, monolith_data, show_thinking=False):
    """
    RATIONALIS: Logic Engine Panel with personality, greeting, and metrics.
    """
    stdscr.erase()
    profile = PERSONALITY_PROFILES["RATIONALIS"]
    color = MONOLITHS["RATIONALIS"]["color"]
    labels = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["labels"]

    # Greeting at the top
    greeting = get_node_greeting("RATIONALIS")
    safe_addstr(stdscr, 1, width // 2 - len(greeting) // 2, greeting, curses.A_BOLD | curses.color_pair(color))

    # If user requests status/thinking, show thinking phrase
    if show_thinking:
        thinking = get_node_thinking_phrase("RATIONALIS")
        safe_addstr(stdscr, 3, width // 2 - len(thinking) // 2, thinking, curses.color_pair(color))
        speak_with_tts(thinking, voice=get_node_tts_voice("RATIONALIS"))

    # Show metrics and system logs
    safe_addstr(stdscr, 5, 4, "EFFICIENCY RATING:", curses.A_BOLD)
    eff = monolith_data.rationalis["efficiency_rating"]
    eff_color = 2 if eff > 0.9 else 3 if eff > 0.75 else 1
    safe_addstr(stdscr, 5, 24, f"{eff*100:.2f}%", curses.color_pair(eff_color) | curses.A_BOLD)

    safe_addstr(stdscr, 7, 4, "RECENT LOGIC PATTERNS:", curses.A_BOLD)
    patterns = monolith_data.rationalis["logic_patterns"]
    y = 8
    for name, value in patterns.items():
        if name != "logical_fallacies_detected":
            line = f"{name.replace('_', ' ').capitalize()}: {value:.2f}"
            safe_addstr(stdscr, y, 6, line, curses.color_pair(color))
            y += 1

    # Fallacies
    fallacies = patterns.get("logical_fallacies_detected", 0)
    safe_addstr(stdscr, y, 6, f"Logical Fallacies Detected: {fallacies}", curses.color_pair(1 if fallacies > 6 else 3 if fallacies > 2 else 2))
    y += 2

    # Recent logs
    safe_addstr(stdscr, y, 4, "RECENT LOGS:", curses.A_BOLD)
    logs = list(monolith_data.rationalis["system_logs"])[-5:]
    for i, log in enumerate(logs):
        log_text = f"[{log['timestamp']}] {log['level']}: {log['message']}"
        safe_addstr(stdscr, y + 1 + i, 6, log_text, curses.color_pair(color))

    # Footer/controls
    footer = "M: Main | R: Refresh | T: Thinking | Q: Quit"
    safe_addstr(stdscr, height - 1, 2, footer, curses.A_REVERSE)

def render_aeternum_screen(stdscr, theme: str, height: int, width: int, monolith_data, show_thinking=False):
    """
    AETERNUM: Market/Temporal Analysis Panel with personality and metrics.
    """
    stdscr.erase()
    profile = PERSONALITY_PROFILES["AETERNUM"]
    color = MONOLITHS["AETERNUM"]["color"]
    labels = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["labels"]

    greeting = get_node_greeting("AETERNUM")
    safe_addstr(stdscr, 1, width // 2 - len(greeting) // 2, greeting, curses.A_BOLD | curses.color_pair(color))

    if show_thinking:
        thinking = get_node_thinking_phrase("AETERNUM")
        safe_addstr(stdscr, 3, width // 2 - len(thinking) // 2, thinking, curses.color_pair(color))
        speak_with_tts(thinking, voice=get_node_tts_voice("AETERNUM"))

    # Market indices
    safe_addstr(stdscr, 5, 4, "MARKET INDICES:", curses.A_BOLD)
    indices = monolith_data.aeternum["market_indices"]
    y = 6
    for idx, (name, data) in enumerate(indices.items()):
        trend_color = 2 if data["trend"] == "up" else 1
        text = f"{name}: {data['value']:.2f} ({data['change']:+.2f}%)"
        safe_addstr(stdscr, y + idx, 6, text, curses.color_pair(trend_color))

    # Portfolio
    y += len(indices) + 2
    safe_addstr(stdscr, y, 4, "PORTFOLIO:", curses.A_BOLD)
    pf = monolith_data.aeternum["portfolio_performance"]
    safe_addstr(stdscr, y + 1, 6, f"Daily: {pf['daily_change']:+.2f}%   Yearly: {pf['yearly_change']:+.2f}%")

    # Economic indicators
    y += 3
    safe_addstr(stdscr, y, 4, "ECONOMIC INDICATORS:", curses.A_BOLD)
    econ = monolith_data.aeternum["economic_indicators"]
    for i, (k, v) in enumerate(econ.items()):
        safe_addstr(stdscr, y + i + 1, 6, f"{k.capitalize()}: {v}")

    # Footer
    footer = "M: Main | R: Refresh | T: Thinking | Q: Quit"
    safe_addstr(stdscr, height - 1, 2, footer, curses.A_REVERSE)

def render_bellator_screen(stdscr, theme: str, height: int, width: int, monolith_data, show_thinking=False):
    """
    BELLATOR: Tactical Threat Panel with personality and threat stats.
    """
    stdscr.erase()
    profile = PERSONALITY_PROFILES["BELLATOR"]
    color = MONOLITHS["BELLATOR"]["color"]
    labels = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["labels"]

    greeting = get_node_greeting("BELLATOR")
    safe_addstr(stdscr, 1, width // 2 - len(greeting) // 2, greeting, curses.A_BOLD | curses.color_pair(color))

    if show_thinking:
        thinking = get_node_thinking_phrase("BELLATOR")
        safe_addstr(stdscr, 3, width // 2 - len(thinking) // 2, thinking, curses.color_pair(color))
        speak_with_tts(thinking, voice=get_node_tts_voice("BELLATOR"))

    # DEFCON Level
    defcon = monolith_data.bellator["defcon_level"]
    defcon_color = 1 if defcon <= 2 else 3 if defcon <= 3 else 2
    safe_addstr(stdscr, 5, 4, f"DEFCON LEVEL: {defcon}", curses.A_BOLD | curses.color_pair(defcon_color))

    # Threat alerts
    safe_addstr(stdscr, 7, 4, "THREAT ALERTS:", curses.A_BOLD)
    alerts = list(monolith_data.bellator["threat_alerts"])[-3:]
    for i, alert in enumerate(alerts):
        line = f"{alert.timestamp.strftime('%H:%M')} {alert.source}: {alert.level} - {alert.description}"
        color_alert = 1 if alert.level in ["High", "Critical"] else 3 if alert.level == "Elevated" else 2
        safe_addstr(stdscr, 8 + i, 6, line, curses.color_pair(color_alert))

    # Security metrics
    safe_addstr(stdscr, 12, 4, f"Security Index: {monolith_data.bellator['security_index']:.1f}")
    safe_addstr(stdscr, 13, 4, f"Geopolitical Stability: {monolith_data.bellator['geopolitical_stability']:.2f}")
    safe_addstr(stdscr, 14, 4, f"Cyberattack Probability: {monolith_data.bellator['cyberattack_probability']:.2f}")

    # Footer
    footer = "M: Main | R: Refresh | T: Thinking | Q: Quit"
    safe_addstr(stdscr, height - 1, 2, footer, curses.A_REVERSE)



def safe_draw_box(stdscr, y1: int, x1: int, y2: int, x2: int):
    """Safe box drawing with the current theme"""
    max_y, max_x = stdscr.getmaxyx()
    
    # Bounds checking
    if y1 < 0 or x1 < 0 or y2 >= max_y or x2 >= max_x:
        return
    if y2 <= y1 or x2 <= x1:
        return
    
    theme = CONFIG.get("system", {}).get("theme", "military")
    box_chars = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])["box_chars"]
    
    try:
        # Draw the box using theme characters
        draw_box(stdscr, y1, x1, y2, x2, theme)
    except Exception:
        # Fallback to simple ASCII
        try:
            # Just draw corners and basic lines
            safe_addstr(stdscr, y1, x1, "+")
            safe_addstr(stdscr, y1, x2, "+")
            safe_addstr(stdscr, y2, x1, "+")
            safe_addstr(stdscr, y2, x2, "+")
            
            for x in range(x1 + 1, x2):
                safe_addstr(stdscr, y1, x, "-")
                safe_addstr(stdscr, y2, x, "-")
            
            for y in range(y1 + 1, y2):
                safe_addstr(stdscr, y, x1, "|")
                safe_addstr(stdscr, y, x2, "|")
        except:
            pass  # Give up gracefully


def validate_theme_characters(theme: str) -> bool:
    """Validate that theme characters can be displayed properly"""
    try:
        # Test if we can create a simple string with theme characters
        theme_config = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])
        box_chars = theme_config["box_chars"]
        
        # Try to encode the characters
        test_string = f"{box_chars['tl']}{box_chars['h']}{box_chars['tr']}\n{box_chars['v']} {box_chars['v']}\n{box_chars['bl']}{box_chars['h']}{box_chars['br']}"
        test_string.encode('utf-8')
        
        return True
    except (UnicodeEncodeError, KeyError, TypeError):
        return False


def get_safe_theme_config(theme: str) -> dict:
    """Get theme configuration with fallback to ASCII if needed"""
    if not validate_theme_characters(theme):
        # Fall back to military theme (ASCII) if current theme has issues
        return THEME_DEFINITIONS["military"]
    
    return THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])


def auto_adjust_layout(height: int, width: int) -> dict:
    """Auto-adjust layout parameters based on terminal size"""
    layout = {
        "use_vertical_monoliths": False,
        "monolith_box_width": 20,
        "monolith_box_height": 8,
        "show_status_bar": True,
        "show_consensus_section": True,
        "margin_left": 2,
        "margin_right": 2,
        "margin_top": 1,
        "margin_bottom": 2
    }
    
    # Adjust for very small terminals
    if width < 80:
        layout["use_vertical_monoliths"] = True
        layout["monolith_box_width"] = min(18, width - 8)
        layout["margin_left"] = 1
        layout["margin_right"] = 1
    
    if height < 20:
        layout["monolith_box_height"] = 6
        layout["show_status_bar"] = False
        layout["margin_top"] = 0
        layout["margin_bottom"] = 1
    
    if height < 15:
        layout["show_consensus_section"] = False
    
    # Adjust for very wide terminals
    if width > 120:
        layout["monolith_box_width"] = min(30, (width - 20) // 3)
        layout["margin_left"] = 4
        layout["margin_right"] = 4
    
    return layout

def draw_monolith_box(stdscr, y1, x1, y2, x2, box_chars):
    """Draw a box for individual monolith with proper borders"""
    # Top border
    safe_addstr(stdscr, y1, x1, box_chars["tl"])
    for x in range(x1 + 1, x2):
        safe_addstr(stdscr, y1, x, box_chars["h"])
    safe_addstr(stdscr, y1, x2, box_chars["tr"])
    
    # Side borders
    for y in range(y1 + 1, y2):
        safe_addstr(stdscr, y, x1, box_chars["v"])
        safe_addstr(stdscr, y, x2, box_chars["v"])
    
    # Bottom border
    safe_addstr(stdscr, y2, x1, box_chars["bl"])
    for x in range(x1 + 1, x2):
        safe_addstr(stdscr, y2, x, box_chars["h"])
    safe_addstr(stdscr, y2, x2, box_chars["br"])

def draw_verdict_box(stdscr, y1, x1, y2, x2, box_chars):
    """Draw a special box for verdict display"""
    # Top border
    safe_addstr(stdscr, y1, x1, box_chars["tl"])
    for x in range(x1 + 1, x2):
        safe_addstr(stdscr, y1, x, box_chars["h"])
    safe_addstr(stdscr, y1, x2, box_chars["tr"])
    
    # Side borders
    for y in range(y1 + 1, y2):
        safe_addstr(stdscr, y, x1, box_chars["v"])
        safe_addstr(stdscr, y, x2, box_chars["v"])
    
    # Bottom border
    safe_addstr(stdscr, y2, x1, box_chars["bl"])
    for x in range(x1 + 1, x2):
        safe_addstr(stdscr, y2, x, box_chars["h"])
    safe_addstr(stdscr, y2, x2, box_chars["br"])

def safe_addstr(window, y: int, x: int, text: str, attr: int = 0):
    """Safely add string to window without overflow"""
    try:
        max_y, max_x = window.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            # Calculate maximum length to prevent overflow
            max_len = max_x - x - 1
            if max_len > 0:
                trimmed_text = text[:max_len] if len(text) > max_len else text
                window.addstr(y, x, trimmed_text, attr)
    except curses.error:
        # Silently ignore curses errors (like writing to last position)
        pass

def render_monolith_screen(stdscr, monolith_name: str, theme: str, height: int, width: int):
    """Render specialized monolith view"""
    stdscr.erase()
    
    # Get monolith data
    data = globals().get('MONOLITH_DATA', {}).get(monolith_name, {})
    if not data:
        safe_addstr(stdscr, height // 2, width // 2 - 10, "No data available", curses.color_pair(1))
        return
    
    # Header
    theme_label = THEME_DEFINITIONS[theme]["labels"].get(f"monolith_{monolith_name.lower()}", monolith_name)
    safe_addstr(stdscr, 0, width // 2 - len(theme_label) // 2, theme_label, 
               curses.A_BOLD | curses.color_pair(MONOLITHS[monolith_name]["color"]))
    
    y_pos = 2
    
    if monolith_name == "RATIONALIS":
        # Efficiency rating
        efficiency = data.get("efficiency_rating", 0) * 100
        safe_addstr(stdscr, y_pos, 2, f"Logic Engine Efficiency: {efficiency:.1f}%", 
                   curses.color_pair(2 if efficiency > 90 else 3))
        y_pos += 2
        
        # System logs
        safe_addstr(stdscr, y_pos, 2, "SYSTEM LOGS:", curses.A_BOLD)
        y_pos += 1
        
        for log_entry in data.get("system_logs", [])[:10]:
            if y_pos < height - 2:
                level_color = 2 if log_entry["level"] == "INFO" else 3 if log_entry["level"] == "WARNING" else 1
                log_text = f"[{log_entry['timestamp']}] {log_entry['level']}: {log_entry['message']}"
                safe_addstr(stdscr, y_pos, 4, log_text[:width-6], curses.color_pair(level_color))
                y_pos += 1
    
    elif monolith_name == "AETERNUM":
        # Market indices
        safe_addstr(stdscr, y_pos, 2, "MARKET INDICES:", curses.A_BOLD)
        y_pos += 1
        
        indices = data.get("market_indices", {})
        col1_x, col2_x = 4, width // 2 + 4
        
        for i, (name, index_data) in enumerate(indices.items()):
            if y_pos + i // 2 < height - 2:
                x_pos = col1_x if i % 2 == 0 else col2_x
                trend_color = 2 if index_data["trend"] == "up" else 1
                value_str = f"{index_data['value']:,.2f}"
                change_str = f"{index_data['change']:+.2f}%"
                market_text = f"{name}: {value_str} ({change_str})"
                safe_addstr(stdscr, y_pos + i // 2, x_pos, market_text[:25], curses.color_pair(trend_color))
        
        y_pos += (len(indices) + 1) // 2 + 2
        
        # Additional metrics
        volatility = data.get("volatility_index", 0)
        sentiment = data.get("market_sentiment", 0)
        safe_addstr(stdscr, y_pos, 2, f"Volatility Index: {volatility:.1f}", curses.color_pair(3))
        safe_addstr(stdscr, y_pos + 1, 2, f"Market Sentiment: {sentiment:.2f}", 
                   curses.color_pair(2 if sentiment > 0.6 else 1))
    
    elif monolith_name == "BELLATOR":
        # DEFCON level
        defcon = data.get("defcon_level", 5)
        defcon_color = 1 if defcon <= 2 else 3 if defcon <= 3 else 2
        safe_addstr(stdscr, y_pos, 2, f"DEFCON LEVEL: {defcon}", 
                   curses.A_BOLD | curses.color_pair(defcon_color))
        y_pos += 2
        
        # Security metrics
        security_idx = data.get("security_index", 0)
        geo_stability = data.get("geopolitical_stability", 0)
        safe_addstr(stdscr, y_pos, 2, f"Security Index: {security_idx:.1f}%", curses.color_pair(2))
        safe_addstr(stdscr, y_pos + 1, 2, f"Geopolitical Stability: {geo_stability:.2f}", curses.color_pair(2))
        y_pos += 3
        
        # Threat alerts
        safe_addstr(stdscr, y_pos, 2, "THREAT ALERTS:", curses.A_BOLD)
        y_pos += 1
        
        for alert in data.get("threat_alerts", [])[:8]:
            if y_pos < height - 2:
                priority_color = 1 if alert["priority"] == "HIGH" else 3 if alert["priority"] == "MEDIUM" else 2
                alert_text = f"[{alert['timestamp']}] {alert['type']} - {alert['description']}"
                safe_addstr(stdscr, y_pos, 4, alert_text[:width-6], curses.color_pair(priority_color))
                y_pos += 1
    
    # Last updated
    if data.get("last_updated"):
        update_time = data["last_updated"].strftime("%H:%M:%S")
        safe_addstr(stdscr, height - 3, 2, f"Last Updated: {update_time}", curses.color_pair(7))
    
    # Controls
    controls = "M:Main | Q:Quit | 1-3:Other Monoliths | S:Theme"
    safe_addstr(stdscr, height - 1, 2, controls[:width-4], curses.A_REVERSE)

def render_history_screen(stdscr, height: int, width: int):
    """Render decision history screen"""
    stdscr.erase()
    
    safe_addstr(stdscr, 0, width // 2 - 8, "DECISION HISTORY", curses.A_BOLD | curses.color_pair(2))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, width // 2 - 10, "No decisions recorded", curses.color_pair(3))
        return
    
    y_pos = 2
    for i, decision in enumerate(list(decision_history)[-20:]):  # Show last 20 decisions
        if y_pos >= height - 2:
            break
        
        timestamp = decision.get("timestamp", "Unknown")[:19]  # Trim microseconds
        query = decision.get("query", "Unknown query")[:40]
        verdict = decision.get("verdict", "Unknown")
        confidence = decision.get("confidence", 0)
        
        verdict_color = 2 if "APPROVED" in verdict else 1 if "DENIED" in verdict else 3
        
        decision_text = f"[{timestamp}] {query} -> {verdict} ({confidence:.2f})"
        safe_addstr(stdscr, y_pos, 2, decision_text[:width-4], curses.color_pair(verdict_color))
        y_pos += 1
    
    controls = "M:Main | Q:Quit | E:Export History"
    safe_addstr(stdscr, height - 1, 2, controls[:width-4], curses.A_REVERSE)

def render_diagnostics_screen(stdscr, height: int, width: int):
    """Render system diagnostics screen"""
    stdscr.erase()
    
    safe_addstr(stdscr, 0, width // 2 - 12, "SYSTEM DIAGNOSTICS", curses.A_BOLD | curses.color_pair(4))
    
    y_pos = 2
    
    # System information
    safe_addstr(stdscr, y_pos, 2, "SYSTEM INFORMATION", curses.A_BOLD)
    y_pos += 1
    safe_addstr(stdscr, y_pos, 4, f"Version: {VERSION}")
    safe_addstr(stdscr, y_pos + 1, 4, f"Build: {BUILD_HASH}")
    safe_addstr(stdscr, y_pos + 2, 4, f"Session: {SESSION_ID}")
    safe_addstr(stdscr, y_pos + 3, 4, f"Uptime: {get_system_uptime()}")
    y_pos += 5
    
    # Health metrics
    safe_addstr(stdscr, y_pos, 2, "HEALTH METRICS", curses.A_BOLD)
    y_pos += 1
    if system_health.last_check:
        safe_addstr(stdscr, y_pos, 4, f"CPU Usage: {system_health.cpu_usage:.1f}%")
        safe_addstr(stdscr, y_pos + 1, 4, f"Memory Usage: {system_health.memory_usage:.1f}%")
        safe_addstr(stdscr, y_pos + 2, 4, f"Disk Usage: {system_health.disk_usage:.1f}%")
        safe_addstr(stdscr, y_pos + 3, 4, f"Network Status: {system_health.network_status}")
        safe_addstr(stdscr, y_pos + 4, 4, f"TTS Status: {system_health.tts_status}")
        safe_addstr(stdscr, y_pos + 5, 4, f"API Response Time: {system_health.api_response_time:.2f}s")
        y_pos += 7
    
    # Configuration summary
    safe_addstr(stdscr, y_pos, 2, "CONFIGURATION", curses.A_BOLD)
    y_pos += 1
    safe_addstr(stdscr, y_pos, 4, f"Theme: {CONFIG['system']['theme']}")
    safe_addstr(stdscr, y_pos + 1, 4, f"LLM Provider: {CONFIG['llm']['provider']}")
    safe_addstr(stdscr, y_pos + 2, 4, f"TTS Enabled: {CONFIG['tts']['enabled']}")
    safe_addstr(stdscr, y_pos + 3, 4, f"Health Monitoring: {CONFIG['health']['enabled']}")
    
    controls = "M:Main | Q:Quit | R:Refresh"
    safe_addstr(stdscr, height - 1, 2, controls[:width-4], curses.A_REVERSE)

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

# ================================================================================
# MODULE 11: Console Mode & Commands
# ================================================================================

def command(name):
    """Decorator to register a console command"""
    def decorator(func):
        COMMANDS[name] = func
        return func
    return decorator

@command("vote")
def cmd_vote(args):
    """Run a consensus vote"""
    if not args:
        query = input("Enter query for consensus: ").strip()
    else:
        query = " ".join(args)
    
    if query:
        llm_interface = LLMInterface(CONFIG["llm"]["provider"])
        consensus_engine = ConsensusEngine(llm_interface)
        result = consensus_engine.run_consensus(query)
        print(f"Consensus result: {result}")
    else:
        print("No query provided")

@command("status")
def cmd_status(args):
    """Show system status"""
    print(f"CONSENSUS System v{VERSION}")
    print(f"Session: {SESSION_ID}")
    print(f"Uptime: {get_system_uptime()}")
    print(f"CPU: {system_health.cpu_usage:.1f}%")
    print(f"Memory: {system_health.memory_usage:.1f}%")
    print(f"Network: {system_health.network_status}")
    
    print("\nMonolith Status:")
    for name, status in MODEL_STATUS.items():
        print(f"  {name}: {status['status']}")

@command("export")
def cmd_export(args):
    """Export decision history"""
    if not args:
        print("Usage: export <format> - where format is json, csv, or txt")
        return
    
    fmt = args[0].lower()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if fmt == "json":
            export_path = EXPORT_DIR / f"decisions_{timestamp}.json"
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(list(decision_history), f, indent=2, default=str)
            print(f"Exported to {export_path}")
            
        elif fmt == "csv":
            export_path = EXPORT_DIR / f"decisions_{timestamp}.csv"
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "query", "verdict", "confidence"])
                for decision in decision_history:
                    writer.writerow([
                        decision.get("timestamp", ""),
                        decision.get("query", ""),
                        decision.get("verdict", ""),
                        decision.get("confidence", "")
                    ])
            print(f"Exported to {export_path}")
            
        elif fmt == "txt":
            export_path = EXPORT_DIR / f"decisions_{timestamp}.txt"
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as f:
                for decision in decision_history:
                    f.write(f"{decision}\n")
            print(f"Exported to {export_path}")
            
        else:
            print(f"Unknown format: {fmt}")
            
    except Exception as e:
        print(f"Export failed: {e}")

@command("config")
def cmd_config(args):
    """Show or modify configuration"""
    if not args:
        print("Current configuration:")
        for section, values in CONFIG.items():
            print(f"  [{section}]")
            if isinstance(values, dict):
                for key, value in values.items():
                    print(f"    {key} = {value}")
            else:
                print(f"    {values}")
    else:
        print("Configuration modification not implemented in console mode")

@command("help")
def cmd_help(args):
    """Show available commands"""
    print("Available commands:")
    for cmd_name in sorted(COMMANDS.keys()):
        func = COMMANDS[cmd_name]
        doc = func.__doc__ or "No description"
        print(f"  {cmd_name:12} - {doc}")

@command("theme")
def cmd_theme(args):
    """Change system theme"""
    themes = list(THEME_DEFINITIONS.keys())
    if not args:
        print(f"Current theme: {CONFIG['system']['theme']}")
        print(f"Available themes: {', '.join(themes)}")
    else:
        new_theme = args[0].lower()
        if new_theme in themes:
            CONFIG["system"]["theme"] = new_theme
            save_system_config()
            print(f"Theme changed to: {new_theme}")
        else:
            print(f"Unknown theme: {new_theme}")
            print(f"Available themes: {', '.join(themes)}")

@command("demo")
def cmd_demo(args):
    """Run voting demo"""
    iterations = 5
    if args and args[0].isdigit():
        iterations = int(args[0])
    
    print(f"Running {iterations} demo votes...")
    demo_queries = [
        "Should we invest in renewable energy?",
        "Authorize emergency funding for infrastructure?",
        "Implement new cybersecurity protocols?",
        "Approve merger with tech company?",
        "Launch new product line?"
    ]
    
    llm_interface = LLMInterface(CONFIG["llm"]["provider"])
    consensus_engine = ConsensusEngine(llm_interface)
    
    for i in range(iterations):
        query = demo_queries[i % len(demo_queries)]
        print(f"\n--- Demo {i+1}: {query} ---")
        result = consensus_engine.run_consensus(query)
        print(f"Result: {result}")

def setup_console():
    """Setup console with readline if available"""
    if READLINE_AVAILABLE:
        try:
            readline.parse_and_bind('tab: complete')
            readline.set_completer(lambda text, state: [
                c for c in COMMANDS.keys() if c.startswith(text)
            ][state] if state < len([c for c in COMMANDS.keys() if c.startswith(text)]) else None)
        except Exception:
            pass

def console_mode():
    """Run the system in console mode"""
    setup_console()
    print(f"CONSENSUS System v{VERSION} - Console Mode")
    print("Type 'help' for available commands, 'quit' to exit")
    
    while True:
        try:
            command_line = input("> ").strip()
            if not command_line:
                continue
                
            if command_line.lower() in ("exit", "quit", "q"):
                print("Exiting console mode...")
                break
            
            parts = command_line.split()
            cmd_name, *args = parts
            cmd_name = cmd_name.lower()
            
            command_history.append(command_line)
            
            if cmd_name in COMMANDS:
                try:
                    COMMANDS[cmd_name](args)
                except Exception as e:
                    print(f"Command error: {e}")
            else:
                print(f"Unknown command: {cmd_name}")
                print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except EOFError:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

# ================================================================================
# MODULE 12: Main Application Loop
# ================================================================================

def main_application_loop(stdscr):
    """Main curses application loop"""
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
    curses.init_pair(6, curses.COLOR_WHITE, -1)
    curses.init_pair(7, curses.COLOR_BLUE, -1)

    current_view = ViewMode.MAIN
    theme = CONFIG["system"]["theme"]
    last_refresh = 0
    refresh_interval = CONFIG["system"]["refresh_interval"]

    while True:
        height, width = stdscr.getmaxyx()

        # Handle input
        try:
            ch = stdscr.getch()
        except KeyboardInterrupt:
            break
     
        theme = CONFIG["system"].get("theme", "military")
    
        if ch != -1:
            if ch in (ord('q'), ord('Q'), 27):  # q, Q or ESC to quit
                break
            elif ch == ord('1'):
                current_view = ViewMode.RATIONALIS
            elif ch == ord('2'):
                current_view = ViewMode.AETERNUM
            elif ch == ord('3'):
                current_view = ViewMode.BELLATOR
            elif ch in (ord('m'), ord('M')):
                current_view = ViewMode.MAIN
            elif ch == ord('7'):
                current_view = ViewMode.HISTORY
            elif ch == ord('9'):
                current_view = ViewMode.DIAGNOSTICS
            elif ch in (ord('s'), ord('S')):
                cycle_theme()
                theme = CONFIG["system"]["theme"]
            elif ch in (ord('c'), ord('C')):
                # Switch to console mode
                curses.endwin()
                console_mode()
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()
                stdscr.keypad(True)
                curses.start_color()
                curses.use_default_colors()
                # Reinitialize color pairs
                for i in range(1, 8):
                    curses.init_pair(i, i, -1)
            elif ch in (ord('v'), ord('V')):
                # Demo vote
                demo_vote()
            elif ch in (ord('r'), ord('R')):
                # Refresh data
                update_simulated_monolith_data()
            elif ch in (ord('e'), ord('E')) and current_view == ViewMode.HISTORY:
                # Export history
                export_decision_history()

        # Render current view
        if current_view == ViewMode.MAIN:
            render_main_screen(stdscr, theme, height, width)
        elif current_view == ViewMode.RATIONALIS:
            render_monolith_screen(stdscr, "RATIONALIS", theme, height, width)
        elif current_view == ViewMode.AETERNUM:
            render_monolith_screen(stdscr, "AETERNUM", theme, height, width)
        elif current_view == ViewMode.BELLATOR:
            render_monolith_screen(stdscr, "BELLATOR", theme, height, width)
        elif current_view == ViewMode.HISTORY:
            render_history_screen(stdscr, height, width)
        elif current_view == ViewMode.DIAGNOSTICS:
            render_diagnostics_screen(stdscr, height, width)

        stdscr.refresh()

        # Auto-refresh data
        now = time.time()
        if now - last_refresh > refresh_interval:
            if CONFIG["system"]["auto_refresh"]:
                update_simulated_monolith_data()
            last_refresh = now

        time.sleep(0.05)  # Reduce CPU usage

def cycle_theme():
    """Cycle through available themes"""
    themes = list(THEME_DEFINITIONS.keys())
    current_index = themes.index(CONFIG["system"]["theme"]) if CONFIG["system"]["theme"] in themes else 0
    new_theme = themes[(current_index + 1) % len(themes)]
    CONFIG["system"]["theme"] = new_theme
    save_system_config()
    add_notification(f"Theme changed to: {THEME_DEFINITIONS[new_theme]['name']}", NotificationLevel.INFO)
    log(f"Theme changed to: {new_theme}", LogLevel.INFO, "UI")

def demo_vote():
    """Run a quick demo vote"""
    demo_query = "Authorize emergency protocol Alpha-7?"
    add_notification(f"Demo vote: {demo_query}", NotificationLevel.INFO)
    
    # Run in background thread to avoid blocking UI
    def run_demo():
        try:
            llm_interface = LLMInterface(CONFIG["llm"]["provider"])
            consensus_engine = ConsensusEngine(llm_interface)
            result = consensus_engine.run_consensus(demo_query)
            add_notification(f"Demo result: {result}", NotificationLevel.SUCCESS)
        except Exception as e:
            add_notification(f"Demo failed: {str(e)}", NotificationLevel.ERROR)
    
    threading.Thread(target=run_demo, daemon=True).start()

def export_decision_history():
    """Export decision history to JSON file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = EXPORT_DIR / f"decisions_{timestamp}.json"
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(list(decision_history), f, indent=2, default=str)
        
        add_notification(f"History exported: {export_path.name}", NotificationLevel.SUCCESS)
        log(f"Decision history exported to: {export_path}", LogLevel.INFO, "EXPORT")
        
    except Exception as e:
        add_notification(f"Export failed: {str(e)}", NotificationLevel.ERROR)
        log(f"Export failed: {e}", LogLevel.ERROR, "EXPORT")

# ================================================================================
# MODULE 13: TTS System
# ================================================================================

class TTSManager:
    """Text-to-Speech manager with GLaDOS-inspired personality"""
    
    def __init__(self):
        self.engine = None
        self.enabled = CONFIG["tts"]["enabled"] and TTS_AVAILABLE
        
        if self.enabled:
            try:
                self.engine = pyttsx3.init()
                self._configure_voice()
                log("TTS system initialized", LogLevel.INFO, "TTS")
            except Exception as e:
                log(f"TTS initialization failed: {e}", LogLevel.ERROR, "TTS")
                self.enabled = False
    
    def _configure_voice(self):
        """Configure voice settings for GLaDOS-like effect"""
        if not self.engine:
            return
        
        try:
            # Get available voices
            voices = self.engine.getProperty('voices')
            
            # Try to find a suitable voice (prefer female)
            target_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                if any(keyword in voice_name for keyword in ['female', 'zira', 'hazel', 'samantha']):
                    target_voice = voice.id
                    break
            
            if target_voice:
                self.engine.setProperty('voice', target_voice)
            
            # Set voice properties
            self.engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
            self.engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
        except Exception as e:
            log(f"Voice configuration failed: {e}", LogLevel.WARNING, "TTS")
    
    def speak(self, message: str, priority: str = "normal"):
        """Speak a message with optional priority"""
        if not self.enabled or not self.engine:
            return
        
        try:
            # Add GLaDOS-style modifications for certain messages
            if priority == "critical":
                message = f"Alert. {message}. Please respond immediately."
            elif priority == "decision":
                message = f"Consensus analysis complete. {message}. Have a very safe day."
            elif priority == "error":
                message = f"System anomaly detected. {message}. Please investigate."
            
            log(f"TTS: {message}", LogLevel.INFO, "TTS")
            
            # Speak in a separate thread to avoid blocking
            def speak_worker():
                try:
                    self.engine.say(message)
                    self.engine.runAndWait()
                except Exception as e:
                    log(f"TTS speak error: {e}", LogLevel.ERROR, "TTS")
            
            threading.Thread(target=speak_worker, daemon=True).start()
            
        except Exception as e:
            log(f"TTS error: {e}", LogLevel.ERROR, "TTS")
    
    def announce_verdict(self, verdict: str, confidence: float):
        """Announce a consensus verdict"""
        if not CONFIG["tts"]["announce_decisions"]:
            return
        
        if verdict == "APPROVED":
            message = f"Authorization granted with {confidence:.0%} confidence."
        elif verdict == "DENIED":
            message = f"Authorization denied with {confidence:.0%} confidence."
        elif verdict == "CONDITIONAL_APPROVAL":
            message = f"Conditional authorization granted. Review required."
        elif verdict == "HUMAN_REVIEW_REQUIRED":
            message = "Consensus inconclusive. Human oversight required."
        elif verdict == "DEADLOCK":
            message = "Tribunal deadlock detected. Manual intervention required."
        else:
            message = f"Consensus process completed. Result: {verdict}."
        
        self.speak(message, "decision")

# Global TTS manager
tts_manager = TTSManager()

# ================================================================================
# MODULE 14: Signal Handlers & Cleanup
# ================================================================================

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    log(f"Received signal {signum}, initiating shutdown", LogLevel.SHUTDOWN)
    
    # Save current state
    save_system_config()
    save_decision_history()
    
    # Cleanup TTS
    if tts_manager.engine:
        try:
            tts_manager.engine.stop()
        except:
            pass
    
    # Final log entry
    log("CONSENSUS System shutdown complete", LogLevel.SHUTDOWN)
    
    # Exit curses cleanly
    try:
        curses.endwin()
    except:
        pass
    
    sys.exit(0)

def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    log("Performing cleanup on exit", LogLevel.SHUTDOWN)
    
    # Save state
    save_system_config()
    save_decision_history()
    
    # Stop TTS
    if tts_manager.engine:
        try:
            tts_manager.engine.stop()
        except:
            pass
    
    log("Cleanup completed", LogLevel.SHUTDOWN)


# ================================================================================
# MODULE 15: Main Entry Point
# ================================================================================

def main():
    """Main entry point with proper boot sequence order"""

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Register cleanup function
    import atexit
    atexit.register(cleanup_on_exit)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="CONSENSUS War Room - AI Tribunal Decision Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
CONSENSUS System v{VERSION}
Author: Erhardt Von Grupten Mundt

Modes:
  GUI mode (default) - Full tactical interface with curses
  Console mode       - Command-line interface with autocomplete
  
Examples:
  python enhanced_consensus_system.py              # Start in GUI mode
  python enhanced_consensus_system.py --console    # Start in console mode
  python enhanced_consensus_system.py --boot       # Show boot sequence only
        """
    )
    
    parser.add_argument("--console", action="store_true", help="Run in console mode instead of GUI")
    parser.add_argument("--boot", action="store_true", help="Show boot sequence only")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--skip-boot", action="store_true", help="Skip boot sequence and loading screen")
    
    args = parser.parse_args()
    
    # Override config path if specified
    if args.config:
        global CONFIG_PATH
        CONFIG_PATH = Path(args.config)
    
    # Enable debug mode if requested
    if args.debug:
        CONFIG["system"]["debug_mode"] = True
    
    try:
        # Initialize system first
        initialize_system()
        
        # Show boot sequence unless skipped
        if not args.skip_boot:
            # STEP 1: Show NERV logo with boot lines FIRST
            boot_sequence()
            
            # STEP 2: Show loading screen with Arasaka logo SECOND
            loading_screen_bar(
                min_dur=2.0, 
                max_dur=3.5, 
                width=60, 
                label="INITIALIZING CONSENSUS WAR ROOM", 
                logo=arasaka_ascii,
                color=Fore.RED if COLORAMA_AVAILABLE else ""
            )
            
            if args.boot:
                print("Boot sequence complete. Exiting...")
                return
        
        # Choose mode
        if args.console:
            print("Starting CONSENSUS System in console mode...")
            console_mode()
        else:
            print("Starting CONSENSUS System in GUI mode...")
            log("Starting GUI mode", LogLevel.INFO, "MAIN")
            curses.wrapper(main_application_loop)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        log(f"Fatal error: {e}", LogLevel.CRITICAL, "MAIN")
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("CONSENSUS System shutdown")

if __name__ == "__main__":
    main()

# ================================================================================
# ADDITIONAL HELPER FUNCTIONS (if not already defined elsewhere)
# ================================================================================

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    log(f"Received signal {signum}, initiating shutdown", LogLevel.SHUTDOWN)
    
    # Save current state
    save_system_config()
    save_decision_history()
    
    # Cleanup TTS
    if 'tts_manager' in globals() and tts_manager.engine:
        try:
            tts_manager.engine.stop()
        except:
            pass
    
    # Final log entry
    log("CONSENSUS System shutdown complete", LogLevel.SHUTDOWN)
    
    # Exit curses cleanly
    try:
        curses.endwin()
    except:
        pass
    
    sys.exit(0)


def cleanup_on_exit():
    """Cleanup function called on normal exit"""
    log("Performing cleanup on exit", LogLevel.SHUTDOWN)
    
    # Save state
    if 'CONFIG' in globals():
        save_system_config()
    if 'decision_history' in globals():
        save_decision_history()
    
    # Stop TTS
    if 'tts_manager' in globals() and tts_manager.engine:
        try:
            tts_manager.engine.stop()
        except:
            pass
    
    log("Cleanup completed", LogLevel.SHUTDOWN)


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
        
        # Start proposal watcher
        threading.Thread(target=watch_proposal_file, daemon=True).start()
        log("Proposal watcher started", LogLevel.INFO)
        
        log("System initialization completed successfully", LogLevel.STARTUP)
        add_notification("CONSENSUS System Online", NotificationLevel.SUCCESS)
        
    except Exception as e:
        error_msg = f"System initialization failed: {e}"
        log(error_msg, LogLevel.CRITICAL)
        print(f"FATAL ERROR: {error_msg}")
        sys.exit(1)


def boot_sequence():
    """Enhanced boot sequence with theme-specific content"""
    # Get theme from config, default to military
    theme = CONFIG.get("system", {}).get("theme", "military") if 'CONFIG' in globals() else "military"
    
    clear()
    
    # Display NERV logo with color
    if COLORAMA_AVAILABLE:
        print(Fore.RED + nerv_logo + Style.RESET_ALL)
    else:
        print(nerv_logo)
    time.sleep(0.6)

    # BIOS header information
    fake_serial = f"0x{random.randint(10**12, 10**13-1):x}".upper()
    bios_ver = f"v{VERSION}" if 'VERSION' in globals() else "v6.2.3"
    build_date = get_build_date()
    
    bios_text = [
        f"CONSENSUS TACTICAL BIOS {VERSION} — (C) ARASAKA CORPORATION",
        "Chief Architect: Erhardt Von Grupten Mundt",
        "Quantum Computing Division / Tactical AI Systems",
        "─" * 79,
        f"WAR ROOM INIT PROTOCOL | S/N: {fake_serial} | BUILD: {build_date}",
        f"Neural Processor: {random.uniform(3.2, 4.8):.1f} GHz | Threads: 16 Active",
        ""
    ]
    
    for line in bios_text:
        if COLORAMA_AVAILABLE and "CONSENSUS" in line:
            line = f"{Fore.CYAN}{line}{Style.RESET_ALL}"
        elif COLORAMA_AVAILABLE and "Architect" in line:
            line = f"{Fore.YELLOW}{line}{Style.RESET_ALL}"
        
        typewriter(line, delay=0.010)
        time.sleep(0.06)
    
    time.sleep(0.4)
    
    # System initialization lines
    init_lines = [
        ("[SYS] POST: Quantum Core Check", "OK"),
        ("[SYS] CPU: Consensus Neural Thread v9.12", "OK"),
        ("[SYS] RAM: 65536MB ECC Quantum Memory", "OK"),
        (f"[SYS] GPU: NERV ARX-7 [{random.randint(7000,9000)} TFLOPS]", "OK"),
        ("[SYS] TPM: Quantum Cryptographic Module", "OK"),
        ("[SYS] NVMe: Hyperlane Storage x16", "OK"),
        ("[SYS] OLED: Tactical HoloTerminal WQHD", "OK"),
        ("[SYS] NET: Secure Tunnel Port 7851", "OK"),
        ("", ""),
        ("[INIT] Initializing AI Tribunal:", ""),
        (" → RATIONALIS [Logic Engine]", "OK"),
        (" → AETERNUM [Temporal Core]", "OK"),
        (" → BELLATOR [Tactical Matrix]", "OK"),
        ("", ""),
        ("[AI] Neural Networks: Calibrated", "OK"),
        ("[AI] TTS Engine: GLaDOS Core", "OK"),
        ("[AI] Memory Expansion: Active", "OK"),
        ("", ""),
        ("[SEC] Firewall: Hardened", "OK"),
        ("[SEC] Audit Trail: IMMUTABLE", "ACTIVE"),
        ("", ""),
        ("[SYS] All systems nominal.", ""),
        ("[SYS] Welcome back, Commander.", ""),
        ("", "")
    ]

    # Display boot lines
    pad = 65
    for main_part, status in init_lines:
        if not main_part:  # Empty line
            print()
            continue
            
        # Create padded line with dots
        left = main_part.ljust(pad, ".")
        
        # Apply colors based on status
        if COLORAMA_AVAILABLE:
            if status == "OK":
                out = f"{left}{Fore.GREEN}OK{Style.RESET_ALL}"
            elif status == "WARN":
                out = f"{left}{Fore.YELLOW}WARN{Style.RESET_ALL}"
            elif status == "ACTIVE":
                out = f"{left}{Fore.CYAN}ACTIVE{Style.RESET_ALL}"
            elif status:
                out = f"{left}{status}"
            else:
                out = main_part
        else:
            out = f"{left}{status}" if status else main_part
        
        typewriter(out, delay=random.uniform(0.004, 0.019))
        time.sleep(random.uniform(0.08, 0.18))
    
    time.sleep(1.0)


def loading_screen_bar(min_dur=2.0, max_dur=3.5, width=60, label="LOADING SYSTEM MODULES", logo=None, color=Fore.RED):
    """Fixed loading bar with proper input handling"""
    import time
    clear()
    term_width = get_terminal_width()
    
    # Draw the logo in color (or fallback)
    if logo:
        lines = logo.strip('\n').splitlines()
        max_logo_width = max(len(line.rstrip()) for line in lines)
        # Pad all lines to the same width
        padded_lines = [line.rstrip().ljust(max_logo_width) for line in lines]
        for line in padded_lines:
            padding = (term_width - max_logo_width) // 2
            centered_line = " " * max(0, padding) + line
            if COLORAMA_AVAILABLE and color:
                print(color + centered_line + Style.RESET_ALL)
            else:
                print(centered_line)
        print("\n" * 2)

    
    # Get theme for appropriate title
    theme = CONFIG.get("system", {}).get("theme", "military") if 'CONFIG' in globals() else "military"
    
    titles = {
        "eva": "INITIALIZING MAGI SYSTEM",
        "wh40k": "AWAKENING MACHINE SPIRIT", 
        "helldivers": "LOADING DEMOCRACY PROTOCOLS",
        "tars": "BOOTING TARS INTERFACE",
        "military": "INITIALIZING CONSENSUS WAR ROOM"
    }
    
    title = titles.get(theme, titles["military"])
    
    if COLORAMA_AVAILABLE:
        print(center_text(f"{Fore.WHITE}{Style.BRIGHT}{title}{Style.RESET_ALL}"))
    else:
        print(center_text(title))
    
    print("\n")
    
    # Progress bar setup
    bar_space = width + 2  # [ + bar + ]
    bar_prefix = ' ' * max(0, (term_width - bar_space) // 2)
    
    # Print opening bracket
    print(bar_prefix + "[", end="", flush=True)
    
    # Generate realistic timing
    steps = width
    durations = [random.uniform(0.02, 0.18) for _ in range(steps)]
    total = sum(durations)
    if total > 0:
        scale = random.uniform(min_dur, max_dur) / total
        durations = [d * scale for d in durations]
    
    # Theme-specific progress bar colors and characters
    if COLORAMA_AVAILABLE:
        colors = {
            "eva": Fore.BLUE,
            "wh40k": Fore.RED,
            "helldivers": Fore.YELLOW,
            "tars": Fore.CYAN,
            "military": Fore.GREEN
        }
        bar_color = colors.get(theme, Fore.GREEN)
    else:
        bar_color = ""
    
    # Animate progress bar
    for i, d in enumerate(durations):
        if COLORAMA_AVAILABLE:
            print(f"{bar_color}█{Style.RESET_ALL}", end="", flush=True)
        else:
            print("█", end="", flush=True)
        
        time.sleep(d)
        
        # Occasional pause for realism
        if i % 10 == 0 and random.random() < 0.3:
            time.sleep(0.15)
    
    # Close bracket
    print("]", flush=True)
    print("\n")  # Add newline after progress bar
    
    # Theme-specific completion message
    messages = {
        "eva": ">>> MAGI SYSTEM READY - PRESS [ENTER] <<<",
        "wh40k": ">>> MACHINE SPIRIT AWAKENED - PRESS [ENTER] <<<", 
        "helldivers": ">>> DEMOCRACY LOADED - PRESS [ENTER] <<<",
        "tars": ">>> TARS ONLINE - PRESS [ENTER] <<<",
        "military": ">>> PRESS [ENTER] TO INITIATE WAR ROOM <<<"
    }
    
    message = messages.get(theme, messages["military"])
    
    if COLORAMA_AVAILABLE:
        print(center_text(f"{Fore.GREEN}{Style.BRIGHT}{message}{Style.RESET_ALL}"))
    else:
        print(center_text(message))
    
    # Wait for user input
    try:
        input()  # Wait for Enter key
    except KeyboardInterrupt:
        print("\nBoot sequence interrupted.")
        sys.exit(0)

# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def clear():
    """Clear screen across platforms"""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_terminal_width(default=80):
    """Get terminal width safely"""
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default


def center_text(text):
    """Center text in terminal"""
    width = get_terminal_width()
    return text.center(width)


def typewriter(text, delay=0.014):
    """Typewriter effect for text output"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def get_build_date(file=__file__):
    """Get build date from file modification time"""
    try:
        t = os.path.getmtime(file)
        return datetime.fromtimestamp(t).strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')


# ================================================================================
# PLACEHOLDER FUNCTIONS (Add implementations if missing)
# ================================================================================

def console_mode():
    """Placeholder for console mode"""
    print("Console mode not fully implemented yet.")
    print("Press Enter to exit...")
    input()


def main_application_loop(stdscr):
    """Placeholder for main curses loop"""
    stdscr.addstr(0, 0, "CONSENSUS System GUI - Press 'q' to quit")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            break


def log(message, level, component="SYSTEM"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [{component}] {message}")


def load_system_config():
    """Placeholder for config loading"""
    pass


def save_system_config():
    """Placeholder for config saving"""
    pass


def load_decision_history():
    """Placeholder for decision history loading"""
    pass


def save_decision_history():
    """Placeholder for decision history saving"""
    pass


def add_notification(message, level):
    """Placeholder for notifications"""
    log(f"NOTIFICATION: {message}", level)


def health_monitor_daemon():
    """Placeholder for health monitoring"""
    pass


def market_data_daemon():
    """Placeholder for market data"""
    pass


def security_monitor_daemon():
    """Placeholder for security monitoring"""
    pass


def update_simulated_monolith_data():
    """Placeholder for monolith data updates"""
    pass


def update_model_statuses():
    """Placeholder for model status updates"""
    pass


def watch_proposal_file():
    """Placeholder for proposal file watcher"""
    pass


# ================================================================================
# MODULE 16: Web Interface Integration
# ================================================================================

import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import jwt
import secrets
from contextlib import asynccontextmanager

# Web API Configuration
WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8888,
    "secret_key": secrets.token_urlsafe(32),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
    "max_websocket_connections": 100,
    "rate_limit_requests": 60,
    "rate_limit_window": 60  # seconds
}

# Pydantic Models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class VoteResponse(BaseModel):
    monolith: str
    vote: str
    reasoning: str
    confidence: float
    response_time: float
    timestamp: str

class ConsensusResponse(BaseModel):
    query: str
    verdict: str
    confidence: float
    votes: Dict[str, VoteResponse]
    session_id: str
    timestamp: str
    processing_time: float

class SystemStatus(BaseModel):
    version: str
    uptime: str
    monoliths: Dict[str, Dict[str, Any]]
    health: Dict[str, Any]
    active_sessions: int
    total_decisions: int

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Authentication
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=WEB_CONFIG["access_token_expire_minutes"])
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, WEB_CONFIG["secret_key"], algorithm=WEB_CONFIG["algorithm"])
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, WEB_CONFIG["secret_key"], algorithms=[WEB_CONFIG["algorithm"]])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str, username: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if username not in self.user_connections:
            self.user_connections[username] = []
        self.user_connections[username].append(client_id)
        
    def disconnect(self, client_id: str, username: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if username in self.user_connections:
            self.user_connections[username].remove(client_id)
            if not self.user_connections[username]:
                del self.user_connections[username]
                
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
            
    async def broadcast_to_user(self, message: dict, username: str):
        if username in self.user_connections:
            for client_id in self.user_connections[username]:
                await self.send_personal_message(message, client_id)
                
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

# Initialize connection manager
manager = ConnectionManager()

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    log("Web API starting up", LogLevel.STARTUP, "WEB_API")
    
    # Initialize background tasks
    asyncio.create_task(websocket_heartbeat())
    asyncio.create_task(metrics_broadcaster())
    
    yield
    
    # Shutdown
    log("Web API shutting down", LogLevel.SHUTDOWN, "WEB_API")
    
    # Close all websocket connections
    for client_id in list(manager.active_connections.keys()):
        await manager.active_connections[client_id].close()

# Create FastAPI app
app = FastAPI(
    title="CONSENSUS War Room API",
    description="Tactical AI Tribunal Decision Engine Web Interface",
    version=VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=WEB_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
rate_limit_storage = {}

async def rate_limit_check(username: str) -> bool:
    """Check if user has exceeded rate limit"""
    now = time.time()
    window_start = now - WEB_CONFIG["rate_limit_window"]
    
    if username not in rate_limit_storage:
        rate_limit_storage[username] = []
    
    # Clean old entries
    rate_limit_storage[username] = [
        timestamp for timestamp in rate_limit_storage[username]
        if timestamp > window_start
    ]
    
    # Check limit
    if len(rate_limit_storage[username]) >= WEB_CONFIG["rate_limit_requests"]:
        return False
    
    rate_limit_storage[username].append(now)
    return True

# API Endpoints
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    # In production, verify against database
    # This is a simplified example
    if request.username == "commander" and request.password == "tribunal":
        access_token_expires = timedelta(minutes=WEB_CONFIG["access_token_expire_minutes"])
        access_token = create_access_token(
            data={"sub": request.username}, expires_delta=access_token_expires
        )
        return TokenResponse(
            access_token=access_token,
            expires_in=WEB_CONFIG["access_token_expire_minutes"] * 60
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/api/status", response_model=SystemStatus)
async def get_status(username: str = Depends(verify_token)):
    """Get current system status"""
    return SystemStatus(
        version=VERSION,
        uptime=get_system_uptime(),
        monoliths={
            name: {
                "status": MODEL_STATUS[name]["status"],
                "model": MONOLITHS[name]["model"],
                "specialization": MONOLITHS[name]["specialization"],
                "memory_usage": MODEL_STATUS[name]["memory_usage"]
            }
            for name in MONOLITHS.keys()
        },
        health={
            "cpu_usage": system_health.cpu_usage,
            "memory_usage": system_health.memory_usage,
            "network_status": system_health.network_status,
            "api_response_time": system_health.api_response_time
        },
        active_sessions=len(manager.active_connections),
        total_decisions=len(decision_history)
    )

@app.post("/api/consensus", response_model=ConsensusResponse)
async def create_consensus(
    request: QueryRequest,
    username: str = Depends(verify_token)
):
    """Submit query for consensus voting"""
    # Rate limiting
    if not await rate_limit_check(username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Log request
    log(f"Web API consensus request from {username}: {request.query}", LogLevel.INFO, "WEB_API")
    
    # Broadcast to WebSocket clients
    await manager.broadcast_to_user({
        "type": "consensus_started",
        "query": request.query,
        "timestamp": datetime.now().isoformat()
    }, username)
    
    # Run consensus
    start_time = time.time()
    try:
        llm_interface = LLMInterface(CONFIG["llm"]["provider"])
        consensus_engine = ConsensusEngine(llm_interface)
        
        # Get votes
        votes = await asyncio.to_thread(consensus_engine._gather_votes, request.query)
        verdict = consensus_engine._calculate_consensus(votes)
        
        # Convert votes to response format
        vote_responses = {}
        for monolith, vote_data in votes.items():
            vote_responses[monolith] = VoteResponse(
                monolith=monolith,
                vote=vote_data["vote"],
                reasoning=vote_data["reasoning"],
                confidence=vote_data["confidence"],
                response_time=vote_data["response_time"],
                timestamp=vote_data["timestamp"]
            )
        
        processing_time = time.time() - start_time
        
        response = ConsensusResponse(
            query=request.query,
            verdict=verdict,
            confidence=sum(v["confidence"] for v in votes.values()) / len(votes),
            votes=vote_responses,
            session_id=SESSION_ID,
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time
        )
        
        # Broadcast result
        await manager.broadcast_to_user({
            "type": "consensus_complete",
            "result": response.dict()
        }, username)
        
        return response
        
    except Exception as e:
        log(f"Web API consensus error: {e}", LogLevel.ERROR, "WEB_API")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consensus processing failed: {str(e)}"
        )

@app.get("/api/history")
async def get_history(
    limit: int = 100,
    offset: int = 0,
    username: str = Depends(verify_token)
):
    """Get decision history with pagination"""
    history_list = list(decision_history)
    total = len(history_list)
    
    # Apply pagination
    start = offset
    end = min(offset + limit, total)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "decisions": history_list[start:end]
    }

@app.get("/api/monoliths/{monolith_name}")
async def get_monolith_details(
    monolith_name: str,
    username: str = Depends(verify_token)
):
    """Get detailed information about a specific monolith"""
    if monolith_name not in MONOLITHS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monolith {monolith_name} not found"
        )
    
    # Get monolith-specific data
    monolith_data_map = {
        "RATIONALIS": globals().get('MONOLITH_DATA', {}).get('RATIONALIS', {}),
        "AETERNUM": globals().get('MONOLITH_DATA', {}).get('AETERNUM', {}),
        "BELLATOR": globals().get('MONOLITH_DATA', {}).get('BELLATOR', {})
    }
    
    return {
        "name": monolith_name,
        "config": MONOLITHS[monolith_name],
        "status": MODEL_STATUS[monolith_name],
        "data": monolith_data_map.get(monolith_name, {}),
        "performance": {
            "total_votes": len([d for d in decision_history if monolith_name in d.get("votes", {})]),
            "average_confidence": sum(
                d["votes"][monolith_name]["confidence"] 
                for d in decision_history 
                if monolith_name in d.get("votes", {})
            ) / max(1, len([d for d in decision_history if monolith_name in d.get("votes", {})])),
        }
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    """WebSocket endpoint for real-time updates"""
    # Simple auth via query parameter (in production, use proper auth)
    token = websocket.query_params.get("token")
    
    try:
        # Verify token
        payload = jwt.decode(token, WEB_CONFIG["secret_key"], algorithms=[WEB_CONFIG["algorithm"]])
        username = payload.get("sub")
        
        if not username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect
    await manager.connect(websocket, client_id, username)
    
    try:
        # Send initial status
        await manager.send_personal_message({
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }, client_id)
        
        # Handle messages in a loop
        while True:
            try:
                data = await websocket.receive_json()
                
                # Process received messages if needed
                if data.get("type") == "ping":
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                elif data.get("type") == "subscribe":
                    # Subscribe to specific events
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "events": data.get("events", []),
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                elif data.get("type") == "status_request":
                    # Send current system status
                    await manager.send_personal_message({
                        "type": "status_update",
                        "system_health": {
                            "cpu_usage": system_health.cpu_usage,
                            "memory_usage": system_health.memory_usage,
                            "uptime": get_system_uptime()
                        },
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                    
            except WebSocketDisconnect:
                # Client disconnected normally
                break
            except Exception as e:
                # Log error but continue trying to receive messages
                log(f"WebSocket message handling error for client {client_id}: {e}", LogLevel.ERROR, "WEB_API")
                # Send error message to client
                try:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Message processing error",
                        "timestamp": datetime.now().isoformat()
                    }, client_id)
                except:
                    # If we can't send error message, connection is probably broken
                    break
                    
    except WebSocketDisconnect:
        # Handle disconnection
        log(f"WebSocket client {client_id} disconnected", LogLevel.INFO, "WEB_API")
    except Exception as e:
        # Handle other connection errors
        log(f"WebSocket connection error for client {client_id}: {e}", LogLevel.ERROR, "WEB_API")
    finally:
        # Always cleanup on exit
        try:
            manager.disconnect(client_id, username)
            # Broadcast disconnection to other clients of the same user
            await manager.broadcast_to_user({
                "type": "user_disconnected",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            }, username)
        except Exception as cleanup_error:
            log(f"WebSocket cleanup error for client {client_id}: {cleanup_error}", LogLevel.ERROR, "WEB_API")


@app.get("/api/export/{format}")
async def export_decisions(
    format: str,
    username: str = Depends(verify_token)
):
    """Export decision history in specified format"""
    if format not in ["json", "csv", "xlsx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Supported: json, csv, xlsx"
        )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == "json":
        export_path = EXPORT_DIR / f"decisions_web_{timestamp}.json"
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(list(decision_history), f, indent=2, default=str)
            
        return FileResponse(
            path=export_path,
            filename=f"consensus_decisions_{timestamp}.json",
            media_type="application/json"
        )
        
    elif format == "csv":
        export_path = EXPORT_DIR / f"decisions_web_{timestamp}.csv"
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "query", "verdict", "confidence", "votes"])
            
            for decision in decision_history:
                votes_summary = json.dumps({
                    k: v.get("vote", "N/A") 
                    for k, v in decision.get("votes", {}).items()
                })
                writer.writerow([
                    decision.get("timestamp", ""),
                    decision.get("query", ""),
                    decision.get("verdict", ""),
                    decision.get("confidence", ""),
                    votes_summary
                ])
                
        return FileResponse(
            path=export_path,
            filename=f"consensus_decisions_{timestamp}.csv",
            media_type="text/csv"
        )

# Background tasks
async def websocket_heartbeat():
    """Send heartbeat to all connected clients"""
    while True:
        await asyncio.sleep(30)
        await manager.broadcast({
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(manager.active_connections)
        })

async def metrics_broadcaster():
    """Broadcast system metrics periodically"""
    while True:
        try:
            await asyncio.sleep(5)
            
            # Get current metrics
            metrics = {
                "type": "metrics",
                "timestamp": datetime.now().isoformat(),
                "system_health": {
                    "cpu_usage": system_health.cpu_usage,
                    "memory_usage": system_health.memory_usage,
                    "uptime": get_system_uptime()
                },
                "monolith_status": {
                    name: {"status": MODEL_STATUS[name]["status"]}
                    for name in MONOLITHS.keys()
                }
            }
            
            # Broadcast to all connected clients
            await manager.broadcast(metrics)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Metrics broadcaster error: {e}", LogLevel.ERROR, "WEB_API")
            await asyncio.sleep(5)  # Wait before retry

def start_web_server():
    """Start the web API server"""
    log(f"Starting Web API on {WEB_CONFIG['host']}:{WEB_CONFIG['port']}", LogLevel.STARTUP, "WEB_API")
    uvicorn.run(app, host=WEB_CONFIG["host"], port=WEB_CONFIG["port"])

# CLI command to start web server
@command("web")
def cmd_web(args):
    """Start the web API server"""
    print(f"Starting CONSENSUS Web API on port {WEB_CONFIG['port']}...")
    print(f"API documentation available at http://localhost:{WEB_CONFIG['port']}/docs")
    
    # Start in a separate thread to not block the main console
    threading.Thread(target=start_web_server, daemon=True).start()
    print("Web API started in background")

# ================================================================================
# MODULE 17: Advanced Analytics
# ================================================================================

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Analytics Configuration
ANALYTICS_CONFIG = {
    "bias_detection": {
        "threshold": 0.7,
        "min_decisions": 10,
        "window_size": 100
    },
    "performance_metrics": {
        "confidence_bins": [0.0, 0.5, 0.7, 0.85, 0.95, 1.0],
        "response_time_threshold": 10.0,
        "agreement_threshold": 0.8
    },
    "anomaly_detection": {
        "contamination": 0.1,
        "n_estimators": 100,
        "max_features": 1.0
    },
    "pattern_analysis": {
        "min_pattern_support": 0.05,
        "max_pattern_length": 5
    },
    "prediction": {
        "history_window": 50,
        "confidence_interval": 0.95
    },
    "visualization": {
        "figure_size": (12, 8),
        "style": "darkgrid",
        "color_palette": "husl"
    }
}

class ConsensusAnalytics:
    """Advanced analytics engine for CONSENSUS system"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = None
        self.pattern_cache = {}
        self.bias_tracker = defaultdict(lambda: {"approve": 0, "deny": 0, "total": 0})
        
        # Set visualization style
        sns.set_style(ANALYTICS_CONFIG["visualization"]["style"])
        sns.set_palette(ANALYTICS_CONFIG["visualization"]["color_palette"])
        
        log("Analytics engine initialized", LogLevel.INFO, "ANALYTICS")
    
    def analyze_decision_patterns(self, decisions: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in historical decisions"""
        if not decisions:
            return {"error": "No decisions available for analysis"}
        
        # Convert to DataFrame for analysis
        df = self._decisions_to_dataframe(decisions)
        
        results = {
            "summary_statistics": self._calculate_summary_stats(df),
            "voting_patterns": self._analyze_voting_patterns(df),
            "temporal_trends": self._analyze_temporal_trends(df),
            "query_clustering": self._cluster_queries(df),
            "confidence_analysis": self._analyze_confidence_distribution(df)
        }
        
        log(f"Analyzed {len(decisions)} decisions", LogLevel.INFO, "ANALYTICS")
        return results
    
    def detect_bias(self, decisions: List[Dict]) -> Dict[str, Any]:
        """Detect potential bias in voting patterns"""
        if len(decisions) < ANALYTICS_CONFIG["bias_detection"]["min_decisions"]:
            return {"error": "Insufficient decisions for bias detection"}
        
        bias_results = {
            "monolith_bias": {},
            "verdict_distribution": {},
            "query_type_bias": {},
            "temporal_bias": {},
            "bias_score": 0.0
        }
        
        # Analyze each monolith's voting patterns
        for monolith in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
            monolith_votes = []
            
            for decision in decisions:
                if "votes" in decision and monolith in decision["votes"]:
                    vote_data = decision["votes"][monolith]
                    monolith_votes.append({
                        "vote": vote_data.get("vote", "ABSTAIN"),
                        "confidence": vote_data.get("confidence", 0.5),
                        "query": decision.get("query", ""),
                        "timestamp": decision.get("timestamp", "")
                    })
            
            if monolith_votes:
                bias_results["monolith_bias"][monolith] = self._calculate_monolith_bias(monolith_votes)
        
        # Overall verdict distribution
        verdict_counts = defaultdict(int)
        for decision in decisions:
            verdict = decision.get("verdict", "UNKNOWN")
            verdict_counts[verdict] += 1
        
        total_decisions = len(decisions)
        bias_results["verdict_distribution"] = {
            verdict: count / total_decisions 
            for verdict, count in verdict_counts.items()
        }
        
        # Calculate overall bias score
        bias_results["bias_score"] = self._calculate_overall_bias_score(bias_results)
        
        # Alert if bias detected
        if bias_results["bias_score"] > ANALYTICS_CONFIG["bias_detection"]["threshold"]:
            add_notification(
                f"Bias detected in voting patterns (score: {bias_results['bias_score']:.2f})",
                NotificationLevel.WARNING
            )
            
            if CONFIG["tts"]["announce_bias_alerts"]:
                tts_manager.speak(
                    "Warning. Bias detected in tribunal voting patterns. Review recommended.",
                    "critical"
                )
        
        return bias_results
    
    def predict_consensus(self, query: str, historical_decisions: List[Dict]) -> Dict[str, Any]:
        """Predict likely consensus outcome based on historical patterns"""
        if len(historical_decisions) < ANALYTICS_CONFIG["prediction"]["history_window"]:
            return {"error": "Insufficient historical data for prediction"}
        
        # Extract features from query
        query_features = self._extract_query_features(query)
        
        # Find similar historical queries
        similar_decisions = self._find_similar_decisions(query_features, historical_decisions)
        
        if not similar_decisions:
            return {"error": "No similar historical decisions found"}
        
        # Calculate prediction
        prediction = {
            "predicted_verdict": None,
            "confidence": 0.0,
            "similar_decisions": len(similar_decisions),
            "probability_distribution": {},
            "expected_monolith_votes": {}
        }
        
        # Analyze verdict distribution in similar cases
        verdict_counts = defaultdict(int)
        monolith_votes = defaultdict(lambda: defaultdict(int))
        
        for decision in similar_decisions:
            verdict = decision.get("verdict", "UNKNOWN")
            verdict_counts[verdict] += 1
            
            # Track monolith voting patterns
            if "votes" in decision:
                for monolith, vote_data in decision["votes"].items():
                    vote = vote_data.get("vote", "ABSTAIN")
                    monolith_votes[monolith][vote] += 1
        
        # Calculate probabilities
        total_similar = len(similar_decisions)
        prediction["probability_distribution"] = {
            verdict: count / total_similar 
            for verdict, count in verdict_counts.items()
        }
        
        # Predict most likely verdict
        if prediction["probability_distribution"]:
            predicted_verdict = max(
                prediction["probability_distribution"].items(),
                key=lambda x: x[1]
            )[0]
            prediction["predicted_verdict"] = predicted_verdict
            prediction["confidence"] = prediction["probability_distribution"][predicted_verdict]
        
        # Predict monolith votes
        for monolith, votes in monolith_votes.items():
            total_votes = sum(votes.values())
            if total_votes > 0:
                prediction["expected_monolith_votes"][monolith] = {
                    vote: count / total_votes 
                    for vote, count in votes.items()
                }
        
        return prediction
    
    def detect_anomalies(self, decisions: List[Dict]) -> List[Dict]:
        """Detect anomalous decisions using Isolation Forest"""
        if len(decisions) < 10:
            return []
        
        # Extract features for anomaly detection
        features = []
        decision_indices = []
        
        for i, decision in enumerate(decisions):
            feature_vector = self._extract_decision_features(decision)
            if feature_vector is not None:
                features.append(feature_vector)
                decision_indices.append(i)
        
        if not features:
            return []
        
        # Convert to numpy array
        X = np.array(features)
        
        # Train anomaly detector
        self.anomaly_detector = IsolationForest(
            contamination=ANALYTICS_CONFIG["anomaly_detection"]["contamination"],
            n_estimators=ANALYTICS_CONFIG["anomaly_detection"]["n_estimators"],
            random_state=42
        )
        
        # Fit and predict
        anomaly_labels = self.anomaly_detector.fit_predict(X)
        
        # Identify anomalous decisions
        anomalies = []
        for idx, label in enumerate(anomaly_labels):
            if label == -1:  # Anomaly
                decision_idx = decision_indices[idx]
                anomaly_score = self.anomaly_detector.score_samples(X[idx].reshape(1, -1))[0]
                
                anomalies.append({
                    "decision": decisions[decision_idx],
                    "anomaly_score": float(anomaly_score),
                    "features": features[idx].tolist()
                })
        
        # Sort by anomaly score (most anomalous first)
        anomalies.sort(key=lambda x: x["anomaly_score"])
        
        return anomalies
    
    def generate_performance_report(self, monolith_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "period": {
                "start": (datetime.now() - timedelta(days=30)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "metrics": {}
        }
        
        # Get recent decisions
        recent_decisions = list(decision_history)[-1000:]  # Last 1000 decisions
        
        if not recent_decisions:
            return {"error": "No decisions available for analysis"}
        
        # Overall system metrics
        if monolith_name is None:
            report["metrics"]["system"] = self._calculate_system_metrics(recent_decisions)
            report["metrics"]["monoliths"] = {}
            
            # Individual monolith metrics
            for monolith in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
                report["metrics"]["monoliths"][monolith] = self._calculate_monolith_metrics(
                    monolith, recent_decisions
                )
        else:
            # Single monolith report
            report["metrics"][monolith_name] = self._calculate_monolith_metrics(
                monolith_name, recent_decisions
            )
        
        # Add visualizations
        report["visualizations"] = self._generate_visualizations(recent_decisions, monolith_name)
        
        return report
    
    def analyze_decision_quality(self, decisions: List[Dict]) -> Dict[str, Any]:
        """Analyze the quality of decisions based on various metrics"""
        if not decisions:
            return {"error": "No decisions available for quality analysis"}
        
        quality_metrics = {
            "consistency_score": self._calculate_consistency_score(decisions),
            "confidence_reliability": self._analyze_confidence_reliability(decisions),
            "response_time_analysis": self._analyze_response_times(decisions),
            "agreement_patterns": self._analyze_agreement_patterns(decisions),
            "decision_complexity": self._analyze_decision_complexity(decisions)
        }
        
        # Calculate overall quality score
        quality_metrics["overall_quality_score"] = self._calculate_quality_score(quality_metrics)
        
        # Add recommendations
        quality_metrics["recommendations"] = self._generate_quality_recommendations(quality_metrics)
        
        return quality_metrics

# Private helper methods
   
def _decisions_to_dataframe(self, decisions: List[Dict]) -> pd.DataFrame:
       """Convert decisions list to pandas DataFrame"""
       records = []
       
       for decision in decisions:
           record = {
               "timestamp": pd.to_datetime(decision.get("timestamp", "")),
               "query": decision.get("query", ""),
               "verdict": decision.get("verdict", ""),
               "confidence": decision.get("confidence", 0.0),
               "session_id": decision.get("session_id", "")
           }
           
           # Add individual monolith votes
           if "votes" in decision:
               for monolith, vote_data in decision["votes"].items():
                   record[f"{monolith}_vote"] = vote_data.get("vote", "")
                   record[f"{monolith}_confidence"] = vote_data.get("confidence", 0.0)
                   record[f"{monolith}_response_time"] = vote_data.get("response_time", 0.0)
           
           records.append(record)
       
       return pd.DataFrame(records)
   
def _calculate_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
       """Calculate summary statistics"""
       stats = {
           "total_decisions": len(df),
           "unique_queries": df["query"].nunique(),
           "average_confidence": df["confidence"].mean(),
           "confidence_std": df["confidence"].std(),
           "verdict_distribution": df["verdict"].value_counts().to_dict(),
           "decisions_per_day": self._calculate_decisions_per_day(df)
       }
       
       # Add monolith-specific stats
       for monolith in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
           if f"{monolith}_confidence" in df.columns:
               stats[f"{monolith}_avg_confidence"] = df[f"{monolith}_confidence"].mean()
               stats[f"{monolith}_avg_response_time"] = df[f"{monolith}_response_time"].mean()
       
       return stats
   
def _analyze_voting_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
       """Analyze voting patterns between monoliths"""
       patterns = {
           "agreement_rates": {},
           "vote_correlations": {},
           "dissent_patterns": []
       }
       
       # Calculate pairwise agreement rates
       monoliths = ["RATIONALIS", "AETERNUM", "BELLATOR"]
       for i, m1 in enumerate(monoliths):
           for j, m2 in enumerate(monoliths):
               if i < j:
                   agreement_rate = self._calculate_agreement_rate(df, m1, m2)
                   patterns["agreement_rates"][f"{m1}-{m2}"] = agreement_rate
       
       # Find patterns of dissent
       for idx, row in df.iterrows():
           votes = []
           for monolith in monoliths:
               vote_col = f"{monolith}_vote"
               if vote_col in row and pd.notna(row[vote_col]):
                   votes.append(row[vote_col])
           
           if len(votes) == 3 and len(set(votes)) > 1:
               patterns["dissent_patterns"].append({
                   "query": row["query"],
                   "votes": {monoliths[i]: votes[i] for i in range(3)},
                   "verdict": row["verdict"]
               })
       
       return patterns
   
def _analyze_temporal_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
       """Analyze trends over time"""
       df = df.set_index("timestamp").sort_index()
       
       trends = {
           "daily_volume": df.resample("D").size().to_dict(),
           "confidence_trend": df.resample("D")["confidence"].mean().to_dict(),
           "verdict_trends": {}
       }
       
       # Verdict trends over time
       for verdict in df["verdict"].unique():
           verdict_df = df[df["verdict"] == verdict]
           trends["verdict_trends"][verdict] = (
               verdict_df.resample("D").size() / df.resample("D").size()
           ).fillna(0).to_dict()
       
       return trends
   
def _cluster_queries(self, df: pd.DataFrame) -> Dict[str, Any]:
       """Cluster similar queries"""
       from sklearn.feature_extraction.text import TfidfVectorizer
       
       # Extract unique queries
       unique_queries = df["query"].unique()
       
       if len(unique_queries) < 5:
           return {"clusters": [], "message": "Insufficient unique queries for clustering"}
       
       # Vectorize queries
       vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
       query_vectors = vectorizer.fit_transform(unique_queries)
       
       # Determine optimal number of clusters
       n_clusters = min(5, len(unique_queries) // 3)
       
       # Perform clustering
       kmeans = KMeans(n_clusters=n_clusters, random_state=42)
       clusters = kmeans.fit_predict(query_vectors)
       
       # Group queries by cluster
       cluster_groups = defaultdict(list)
       for query, cluster in zip(unique_queries, clusters):
           cluster_groups[int(cluster)].append(query)
       
       # Analyze each cluster
       cluster_analysis = []
       for cluster_id, queries in cluster_groups.items():
           cluster_df = df[df["query"].isin(queries)]
           
           cluster_analysis.append({
               "cluster_id": cluster_id,
               "size": len(queries),
               "sample_queries": queries[:5],
               "verdict_distribution": cluster_df["verdict"].value_counts().to_dict(),
               "avg_confidence": cluster_df["confidence"].mean()
           })
       
       return {"clusters": cluster_analysis, "n_clusters": n_clusters}
   
def _analyze_confidence_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
       """Analyze confidence score distributions"""
       confidence_bins = ANALYTICS_CONFIG["performance_metrics"]["confidence_bins"]
       
       analysis = {
           "overall_distribution": pd.cut(
               df["confidence"], 
               bins=confidence_bins, 
               labels=["Very Low", "Low", "Medium", "High", "Very High"]
           ).value_counts().to_dict(),
           "monolith_distributions": {}
       }
       
       # Analyze per monolith
       for monolith in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
           conf_col = f"{monolith}_confidence"
           if conf_col in df.columns:
               analysis["monolith_distributions"][monolith] = pd.cut(
                   df[conf_col],
                   bins=confidence_bins,
                   labels=["Very Low", "Low", "Medium", "High", "Very High"]
               ).value_counts().to_dict()
       
       return analysis
   
def _calculate_monolith_bias(self, votes: List[Dict]) -> Dict[str, Any]:
       """Calculate bias metrics for a single monolith"""
       vote_counts = defaultdict(int)
       total_votes = len(votes)
       
       for vote in votes:
           vote_type = vote.get("vote", "ABSTAIN")
           vote_counts[vote_type] += 1
       
       # Calculate bias metrics
       bias_metrics = {
           "vote_distribution": {k: v/total_votes for k, v in vote_counts.items()},
           "approval_rate": vote_counts.get("APPROVE", 0) / total_votes,
           "denial_rate": vote_counts.get("DENY", 0) / total_votes,
           "abstention_rate": vote_counts.get("ABSTAIN", 0) / total_votes
       }
       
       # Calculate entropy as a measure of vote diversity
       probabilities = [v/total_votes for v in vote_counts.values() if v > 0]
       bias_metrics["vote_entropy"] = stats.entropy(probabilities)
       
       # Detect strong bias
       if bias_metrics["approval_rate"] > 0.8:
           bias_metrics["bias_type"] = "APPROVAL_BIAS"
       elif bias_metrics["denial_rate"] > 0.8:
           bias_metrics["bias_type"] = "DENIAL_BIAS"
       elif bias_metrics["abstention_rate"] > 0.5:
           bias_metrics["bias_type"] = "ABSTENTION_BIAS"
       else:
           bias_metrics["bias_type"] = "BALANCED"
       
       return bias_metrics
   
def _calculate_overall_bias_score(self, bias_results: Dict) -> float:
       """Calculate overall system bias score"""
       scores = []
       
       # Check monolith bias
       for monolith, bias_data in bias_results["monolith_bias"].items():
           if bias_data["bias_type"] != "BALANCED":
               # Higher score for stronger bias
               max_rate = max(
                   bias_data["approval_rate"],
                   bias_data["denial_rate"],
                   bias_data["abstention_rate"]
               )
               scores.append(max_rate)
       
       # Check verdict distribution bias
       verdict_dist = bias_results["verdict_distribution"]
       if verdict_dist:
           max_verdict_rate = max(verdict_dist.values())
           if max_verdict_rate > 0.7:
               scores.append(max_verdict_rate)
       
       # Return average bias score
       return np.mean(scores) if scores else 0.0
   
def _extract_query_features(self, query: str) -> np.ndarray:
       """Extract numerical features from query text"""
       features = []
       
       # Basic text features
       features.append(len(query))
       features.append(len(query.split()))
       features.append(query.count("?"))
       features.append(query.count("!"))
       
       # Keyword features
       keywords = {
           "urgent": ["urgent", "emergency", "critical", "immediate"],
           "financial": ["invest", "money", "fund", "budget", "cost"],
           "security": ["security", "threat", "risk", "danger", "protect"],
           "strategic": ["strategy", "plan", "future", "long-term"]
       }
       
       for category, words in keywords.items():
           features.append(sum(1 for word in words if word.lower() in query.lower()))
       
       return np.array(features)
   
def _find_similar_decisions(self, query_features: np.ndarray, 
                              decisions: List[Dict], 
                              n_similar: int = 10) -> List[Dict]:
       """Find similar historical decisions based on query features"""
       similarities = []
       
       for decision in decisions:
           hist_query = decision.get("query", "")
           hist_features = self._extract_query_features(hist_query)
           
           # Calculate cosine similarity
           similarity = np.dot(query_features, hist_features) / (
               np.linalg.norm(query_features) * np.linalg.norm(hist_features) + 1e-8
           )
           
           similarities.append((similarity, decision))
       
       # Sort by similarity and return top N
       similarities.sort(key=lambda x: x[0], reverse=True)
       return [decision for _, decision in similarities[:n_similar]]
   
def _extract_decision_features(self, decision: Dict) -> Optional[np.ndarray]:
       """Extract features for anomaly detection"""
       try:
           features = []
           
           # Basic features
           features.append(decision.get("confidence", 0.5))
           
           # Vote agreement features
           if "votes" in decision:
               votes = [v.get("vote") for v in decision["votes"].values()]
               unique_votes = len(set(votes))
               features.append(unique_votes / 3.0)  # Normalized disagreement
               
               # Average confidence
               confidences = [v.get("confidence", 0.5) for v in decision["votes"].values()]
               features.append(np.mean(confidences))
               features.append(np.std(confidences))
               
               # Response times
               response_times = [v.get("response_time", 5.0) for v in decision["votes"].values()]
               features.append(np.mean(response_times))
               features.append(np.std(response_times))
           else:
               # Default values if votes missing
               features.extend([0.33, 0.5, 0.0, 5.0, 0.0])
           
           # Query features
           query = decision.get("query", "")
           features.extend(self._extract_query_features(query)[:4])  # Just basic features
           
           return np.array(features)
           
       except Exception:
           return None
   
def _calculate_system_metrics(self, decisions: List[Dict]) -> Dict[str, Any]:
       """Calculate overall system performance metrics"""
       metrics = {
           "total_decisions": len(decisions),
           "average_confidence": 0.0,
           "consensus_rate": 0.0,
           "average_response_time": 0.0,
           "error_rate": 0.0
       }
       
       if not decisions:
           return metrics
       
       # Calculate metrics
       confidences = []
       response_times = []
       consensus_count = 0
       error_count = 0
       
       for decision in decisions:
           conf = decision.get("confidence", 0.0)
           confidences.append(conf)
           
           verdict = decision.get("verdict", "")
           if verdict in ["APPROVED", "DENIED"]:
               consensus_count += 1
           elif verdict == "ERROR":
               error_count += 1
           
           # Get response times
           if "votes" in decision:
               for vote_data in decision["votes"].values():
                   rt = vote_data.get("response_time", 0.0)
                   if rt > 0:
                       response_times.append(rt)
       
       metrics["average_confidence"] = np.mean(confidences) if confidences else 0.0
       metrics["consensus_rate"] = consensus_count / len(decisions) if decisions else 0.0
       metrics["average_response_time"] = np.mean(response_times) if response_times else 0.0
       metrics["error_rate"] = error_count / len(decisions) if decisions else 0.0
       
       return metrics
   
def _calculate_monolith_metrics(self, monolith_name: str, decisions: List[Dict]) -> Dict[str, Any]:
       """Calculate performance metrics for a specific monolith"""
       metrics = {
           "total_votes": 0,
           "vote_distribution": defaultdict(int),
           "average_confidence": 0.0,
           "average_response_time": 0.0,
           "agreement_with_consensus": 0.0,
           "error_rate": 0.0
       }
       
       confidences = []
       response_times = []
       agreement_count = 0
       error_count = 0
       
       for decision in decisions:
           if "votes" in decision and monolith_name in decision["votes"]:
               vote_data = decision["votes"][monolith_name]
               metrics["total_votes"] += 1
               
               # Vote distribution
               vote = vote_data.get("vote", "ERROR")
               metrics["vote_distribution"][vote] += 1
               
               # Confidence
               conf = vote_data.get("confidence", 0.0)
               confidences.append(conf)
               
               # Response time
               rt = vote_data.get("response_time", 0.0)
               if rt > 0:
                   response_times.append(rt)
               
               # Agreement with consensus
               verdict = decision.get("verdict", "")
               if vote == "APPROVE" and verdict == "APPROVED":
                   agreement_count += 1
               elif vote == "DENY" and verdict == "DENIED":
                   agreement_count += 1
               
               # Errors
               if vote == "ERROR":
                   error_count += 1
       
       # Calculate averages
       if metrics["total_votes"] > 0:
           metrics["average_confidence"] = np.mean(confidences) if confidences else 0.0
           metrics["average_response_time"] = np.mean(response_times) if response_times else 0.0
           metrics["agreement_with_consensus"] = agreement_count / metrics["total_votes"]
           metrics["error_rate"] = error_count / metrics["total_votes"]
           
           # Convert vote distribution to percentages
           metrics["vote_distribution"] = {
               vote: count / metrics["total_votes"] 
               for vote, count in metrics["vote_distribution"].items()
           }
       
       return metrics
   
def _generate_visualizations(self, decisions: List[Dict], 
                               monolith_name: Optional[str] = None) -> Dict[str, str]:
       """Generate visualization plots and return file paths"""
       viz_dir = EXPORT_DIR / "analytics_visualizations"
       viz_dir.mkdir(parents=True, exist_ok=True)
       
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       visualizations = {}
       
       # Convert to DataFrame
       df = self._decisions_to_dataframe(decisions)
       
       if df.empty:
           return visualizations
       
       # 1. Confidence distribution plot
       plt.figure(figsize=ANALYTICS_CONFIG["visualization"]["figure_size"])
       
       if monolith_name:
           conf_col = f"{monolith_name}_confidence"
           if conf_col in df.columns:
               plt.hist(df[conf_col].dropna(), bins=20, alpha=0.7, color='blue', edgecolor='black')
               plt.title(f"{monolith_name} Confidence Distribution")
       else:
           plt.hist(df["confidence"], bins=20, alpha=0.7, color='green', edgecolor='black')
           plt.title("Overall Confidence Distribution")
       
       plt.xlabel("Confidence Score")
       plt.ylabel("Frequency")
       plt.grid(True, alpha=0.3)
       
       conf_plot_path = viz_dir / f"confidence_dist_{timestamp}.png"
       plt.savefig(conf_plot_path, dpi=300, bbox_inches='tight')
       plt.close()
       visualizations["confidence_distribution"] = str(conf_plot_path)
       
       # 2. Verdict timeline
       plt.figure(figsize=ANALYTICS_CONFIG["visualization"]["figure_size"])
       
       # Group by day and verdict
       daily_verdicts = df.groupby([pd.Grouper(key='timestamp', freq='D'), 'verdict']).size().unstack(fill_value=0)
       
       if not daily_verdicts.empty:
           daily_verdicts.plot(kind='area', stacked=True, alpha=0.7)
           plt.title("Verdict Distribution Over Time")
           plt.xlabel("Date")
           plt.ylabel("Number of Decisions")
           plt.legend(title="Verdict", bbox_to_anchor=(1.05, 1), loc='upper left')
           plt.grid(True, alpha=0.3)
           
           timeline_plot_path = viz_dir / f"verdict_timeline_{timestamp}.png"
           plt.savefig(timeline_plot_path, dpi=300, bbox_inches='tight')
           plt.close()
           visualizations["verdict_timeline"] = str(timeline_plot_path)
       
       # 3. Monolith agreement heatmap
       if not monolith_name:
           plt.figure(figsize=(10, 8))
           
           # Calculate agreement matrix
           monoliths = ["RATIONALIS", "AETERNUM", "BELLATOR"]
           agreement_matrix = np.zeros((3, 3))
           
           for i, m1 in enumerate(monoliths):
               for j, m2 in enumerate(monoliths):
                   if i == j:
                       agreement_matrix[i, j] = 1.0
                   else:
                       agreement_matrix[i, j] = self._calculate_agreement_rate(df, m1, m2)
           
           sns.heatmap(agreement_matrix, 
                      xticklabels=monoliths, 
                      yticklabels=monoliths, 
                      annot=True, 
                      fmt='.2f', 
                      cmap='coolwarm',
                      center=0.5,
                      vmin=0, vmax=1)
           
           plt.title("Monolith Agreement Rates")
           
           heatmap_plot_path = viz_dir / f"agreement_heatmap_{timestamp}.png"
           plt.savefig(heatmap_plot_path, dpi=300, bbox_inches='tight')
           plt.close()
           visualizations["agreement_heatmap"] = str(heatmap_plot_path)
       
       # 4. Response time analysis
       plt.figure(figsize=ANALYTICS_CONFIG["visualization"]["figure_size"])
       
       response_times = []
       labels = []
       
       if monolith_name:
           rt_col = f"{monolith_name}_response_time"
           if rt_col in df.columns:
               response_times.append(df[rt_col].dropna().values)
               labels.append(monolith_name)
       else:
           for monolith in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
               rt_col = f"{monolith}_response_time"
               if rt_col in df.columns:
                   response_times.append(df[rt_col].dropna().values)
                   labels.append(monolith)
       
       if response_times:
           plt.boxplot(response_times, labels=labels)
           plt.title("Response Time Distribution")
           plt.ylabel("Response Time (seconds)")
           plt.grid(True, alpha=0.3)
           
           rt_plot_path = viz_dir / f"response_times_{timestamp}.png"
           plt.savefig(rt_plot_path, dpi=300, bbox_inches='tight')
           plt.close()
           visualizations["response_times"] = str(rt_plot_path)
       
       return visualizations
   
def _calculate_agreement_rate(self, df: pd.DataFrame, monolith1: str, monolith2: str) -> float:
       """Calculate agreement rate between two monoliths"""
       vote1_col = f"{monolith1}_vote"
       vote2_col = f"{monolith2}_vote"
       
       if vote1_col not in df.columns or vote2_col not in df.columns:
           return 0.0
       
       # Filter rows where both monoliths voted
       valid_rows = df[(df[vote1_col].notna()) & (df[vote2_col].notna())]
       
       if len(valid_rows) == 0:
           return 0.0
       
       # Calculate agreement
       agreements = (valid_rows[vote1_col] == valid_rows[vote2_col]).sum()
       return agreements / len(valid_rows)
   
def _calculate_decisions_per_day(self, df: pd.DataFrame) -> float:
       """Calculate average decisions per day"""
       if df.empty:
           return 0.0
       
       date_range = (df["timestamp"].max() - df["timestamp"].min()).days + 1
       return len(df) / max(1, date_range)
   
def _calculate_consistency_score(self, decisions: List[Dict]) -> float:
       """Calculate consistency score based on similar queries having similar outcomes"""
       from difflib import SequenceMatcher
       
       query_outcomes = defaultdict(list)
       
       # Group outcomes by similar queries
       for decision in decisions:
           query = decision.get("query", "").lower()
           verdict = decision.get("verdict", "")
           
           # Find similar existing queries
           found_similar = False
           for existing_query in query_outcomes.keys():
               similarity = SequenceMatcher(None, query, existing_query).ratio()
               if similarity > 0.8:  # 80% similarity threshold
                   query_outcomes[existing_query].append(verdict)
                   found_similar = True
                   break
           
           if not found_similar:
               query_outcomes[query].append(verdict)
       
       # Calculate consistency for each query group
       consistency_scores = []
       for query, verdicts in query_outcomes.items():
           if len(verdicts) > 1:
               # Calculate mode (most common verdict)
               verdict_counts = Counter(verdicts)
               mode_count = verdict_counts.most_common(1)[0][1]
               consistency = mode_count / len(verdicts)
               consistency_scores.append(consistency)
       
       return np.mean(consistency_scores) if consistency_scores else 1.0
   
def _analyze_confidence_reliability(self, decisions: List[Dict]) -> Dict[str, Any]:
       """Analyze if confidence scores are reliable predictors of consensus"""
       high_confidence_correct = 0
       high_confidence_total = 0
       low_confidence_correct = 0
       low_confidence_total = 0
       
       for decision in decisions:
           confidence = decision.get("confidence", 0.5)
           verdict = decision.get("verdict", "")
           
           if verdict in ["APPROVED", "DENIED"]:  # Clear consensus
               if confidence >= 0.8:
                   high_confidence_total += 1
                   high_confidence_correct += 1
               elif confidence <= 0.6:
                   low_confidence_total += 1
                   low_confidence_correct += 1
           elif verdict in ["DEADLOCK", "HUMAN_REVIEW_REQUIRED"]:  # No consensus
               if confidence >= 0.8:
                   high_confidence_total += 1
               elif confidence <= 0.6:
                   low_confidence_total += 1
                   low_confidence_correct += 1
       
       return {
           "high_confidence_accuracy": (
               high_confidence_correct / high_confidence_total 
               if high_confidence_total > 0 else 0.0
           ),
           "low_confidence_accuracy": (
               low_confidence_correct / low_confidence_total 
               if low_confidence_total > 0 else 0.0
           ),
           "reliability_score": (
               (high_confidence_correct + low_confidence_correct) / 
               (high_confidence_total + low_confidence_total)
               if (high_confidence_total + low_confidence_total) > 0 else 0.0
           )
       }
   
def _analyze_response_times(self, decisions: List[Dict]) -> Dict[str, Any]:
       """Analyze response time patterns"""
       all_times = []
       monolith_times = defaultdict(list)
       
       for decision in decisions:
           if "votes" in decision:
               for monolith, vote_data in decision["votes"].items():
                   rt = vote_data.get("response_time", 0.0)
                   if rt > 0:
                       all_times.append(rt)
                       monolith_times[monolith].append(rt)
       
       analysis = {
           "overall_stats": {
               "mean": np.mean(all_times) if all_times else 0.0,
               "median": np.median(all_times) if all_times else 0.0,
               "std": np.std(all_times) if all_times else 0.0,
               "p95": np.percentile(all_times, 95) if all_times else 0.0
           },
           "monolith_stats": {}
       }
       
       for monolith, times in monolith_times.items():
           if times:
               analysis["monolith_stats"][monolith] = {
                   "mean": np.mean(times),
                   "median": np.median(times),
                   "std": np.std(times),
                   "p95": np.percentile(times, 95)
               }
       
       # Identify slow responses
       threshold = ANALYTICS_CONFIG["performance_metrics"]["response_time_threshold"]
       analysis["slow_response_rate"] = (
           sum(1 for t in all_times if t > threshold) / len(all_times)
           if all_times else 0.0
       )
       
       return analysis
   
def _analyze_agreement_patterns(self, decisions: List[Dict]) -> Dict[str, Any]:
       """Analyze patterns in monolith agreements"""
       unanimous_count = 0
       majority_count = 0
       no_consensus_count = 0
       
       coalition_patterns = defaultdict(int)
       
       for decision in decisions:
           if "votes" in decision:
               votes = {k: v.get("vote") for k, v in decision["votes"].items()}
               unique_votes = set(votes.values())
               
               if len(unique_votes) == 1:
                   unanimous_count += 1
               elif len(unique_votes) == 2:
                   majority_count += 1
                   # Find coalition
                   for vote_type in unique_votes:
                       coalition = tuple(sorted([k for k, v in votes.items() if v == vote_type]))
                       if len(coalition) == 2:
                           coalition_patterns[coalition] += 1
               else:
                   no_consensus_count += 1
       
       total = unanimous_count + majority_count + no_consensus_count
       
       return {
           "unanimous_rate": unanimous_count / total if total > 0 else 0.0,
           "majority_rate": majority_count / total if total > 0 else 0.0,
           "no_consensus_rate": no_consensus_count / total if total > 0 else 0.0,
           "common_coalitions": dict(sorted(
               coalition_patterns.items(), 
               key=lambda x: x[1], 
               reverse=True
           )[:5])
       }
   
def _analyze_decision_complexity(self, decisions: List[Dict]) -> Dict[str, Any]:
       """Analyze decision complexity based on various factors"""
       complexities = []
       
       for decision in decisions:
           query = decision.get("query", "")
           
           # Complexity factors
           word_count = len(query.split())
           char_count = len(query)
           question_marks = query.count("?")
           
           # Response time as complexity indicator
           avg_response_time = 0.0
           if "votes" in decision:
               times = [v.get("response_time", 0.0) for v in decision["votes"].values()]
               avg_response_time = np.mean([t for t in times if t > 0]) if times else 0.0
           
           # Confidence spread as complexity indicator
           confidence_spread = 0.0
           if "votes" in decision:
               confidences = [v.get("confidence", 0.5) for v in decision["votes"].values()]
               confidence_spread = np.std(confidences) if len(confidences) > 1 else 0.0
           
           # Calculate complexity score
           complexity = (
               word_count * 0.3 +
               (char_count / 10) * 0.2 +
               question_marks * 5 +
               avg_response_time * 0.3 +
               confidence_spread * 20
           )
           
           complexities.append(complexity)
       
       return {
           "average_complexity": np.mean(complexities) if complexities else 0.0,
           "complexity_std": np.std(complexities) if complexities else 0.0,
           "complexity_range": (min(complexities), max(complexities)) if complexities else (0.0, 0.0),
           "complexity_distribution": {
               "low": sum(1 for c in complexities if c < 20) / len(complexities) if complexities else 0.0,
               "medium": sum(1 for c in complexities if 20 <= c < 40) / len(complexities) if complexities else 0.0,
               "high": sum(1 for c in complexities if c >= 40) / len(complexities) if complexities else 0.0
           }
       }
   
def _calculate_quality_score(self, quality_metrics: Dict[str, Any]) -> float:
       """Calculate overall quality score from individual metrics"""
       weights = {
           "consistency_score": 0.25,
           "confidence_reliability": 0.20,
           "response_time": 0.15,
           "agreement": 0.20,
           "complexity_handling": 0.20
       }
       
       score = 0.0
       
       # Consistency contribution
       score += quality_metrics["consistency_score"] * weights["consistency_score"]
       
       # Confidence reliability contribution
       reliability = quality_metrics["confidence_reliability"]["reliability_score"]
       score += reliability * weights["confidence_reliability"]
       
       # Response time contribution (inverse - faster is better)
       rt_analysis = quality_metrics["response_time_analysis"]
       avg_rt = rt_analysis["overall_stats"]["mean"]
       rt_score = 1.0 - min(avg_rt / 30.0, 1.0)  # Normalize to 30 second max
       score += rt_score * weights["response_time"]
       
       # Agreement patterns contribution
       agreement = quality_metrics["agreement_patterns"]
       agreement_score = (
           agreement["unanimous_rate"] * 0.5 +
           agreement["majority_rate"] * 0.3 +
           (1.0 - agreement["no_consensus_rate"]) * 0.2
       )
       score += agreement_score * weights["agreement"]
       
       # Complexity handling (balanced distribution is better)
       complexity = quality_metrics["decision_complexity"]["complexity_distribution"]
       complexity_score = 1.0 - abs(complexity["medium"] - 0.5)  # Best if 50% are medium
       score += complexity_score * weights["complexity_handling"]
       
       return min(max(score, 0.0), 1.0)  # Clamp to [0, 1]
   
def _generate_quality_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
       """Generate recommendations based on quality analysis"""
       recommendations = []
       
       # Check consistency
       if quality_metrics["consistency_score"] < 0.7:
           recommendations.append(
               "Low consistency detected. Consider reviewing decision criteria to ensure "
               "similar queries receive similar outcomes."
           )
       
       # Check confidence reliability
       reliability = quality_metrics["confidence_reliability"]
       if reliability["high_confidence_accuracy"] < 0.8:
           recommendations.append(
               "High confidence predictions are not reliably accurate. "
               "Consider recalibrating confidence scoring mechanisms."
           )
       
       # Check response times
       rt_analysis = quality_metrics["response_time_analysis"]
       if rt_analysis["slow_response_rate"] > 0.2:
           recommendations.append(
               f"Over {rt_analysis['slow_response_rate']*100:.0f}% of responses exceed "
               f"the {ANALYTICS_CONFIG['performance_metrics']['response_time_threshold']}s threshold. "
               "Consider optimizing model performance or increasing resources."
           )
       
       # Check agreement patterns
       agreement = quality_metrics["agreement_patterns"]
       if agreement["no_consensus_rate"] > 0.3:
           recommendations.append(
               "High rate of no-consensus decisions. Consider reviewing monolith "
               "specializations or adding tie-breaking mechanisms."
           )
       
       # Check complexity distribution
       complexity_dist = quality_metrics["decision_complexity"]["complexity_distribution"]
       if complexity_dist["high"] > 0.4:
           recommendations.append(
               "Large proportion of high-complexity queries. Consider implementing "
               "query preprocessing or complexity-aware routing."
           )
       
       # Overall quality
       overall_score = quality_metrics["overall_quality_score"]
       if overall_score < 0.6:
           recommendations.append(
               "Overall decision quality is below acceptable threshold. "
               "A comprehensive system review is recommended."
           )
       elif overall_score > 0.85:
           recommendations.append(
               "System is performing excellently. Continue current operational parameters."
           )
       
       return recommendations

# Global analytics instance
analytics_engine = None

def initialize_analytics():
   """Initialize the analytics engine"""
   global analytics_engine
   analytics_engine = ConsensusAnalytics()
   log("Analytics engine initialized", LogLevel.INFO, "ANALYTICS")

# Console commands for analytics
@command("analyze")
def cmd_analyze(args):
   """Run analytics on decision history"""
   if not analytics_engine:
       initialize_analytics()
   
   if not args:
       print("Usage: analyze <type> [options]")
       print("Types: patterns, bias, quality, anomalies, predict")
       return
   
   analysis_type = args[0].lower()
   
   try:
       if analysis_type == "patterns":
           results = analytics_engine.analyze_decision_patterns(list(decision_history))
           print_analysis_results(results, "Decision Pattern Analysis")
           
       elif analysis_type == "bias":
           results = analytics_engine.detect_bias(list(decision_history))
           print_bias_analysis(results)
           
       elif analysis_type == "quality":
           results = analytics_engine.analyze_decision_quality(list(decision_history))
           print_quality_analysis(results)
           
       elif analysis_type == "anomalies":
           anomalies = analytics_engine.detect_anomalies(list(decision_history))
           print_anomaly_analysis(anomalies)
           
       elif analysis_type == "predict":
           if len(args) < 2:
               print("Usage: analyze predict <query>")
               return
           query = " ".join(args[1:])
           prediction = analytics_engine.predict_consensus(query, list(decision_history))
           print_prediction_results(prediction, query)
           
       else:
           print(f"Unknown analysis type: {analysis_type}")
           
   except Exception as e:
       print(f"Analysis error: {e}")
       log(f"Analytics error: {e}", LogLevel.ERROR, "ANALYTICS")

@command("report")
def cmd_report(args):
   """Generate performance report"""
   if not analytics_engine:
       initialize_analytics()
   
   monolith = args[0].upper() if args else None
   
   try:
       report = analytics_engine.generate_performance_report(monolith)
       
       # Save report
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       report_path = EXPORT_DIR / f"performance_report_{timestamp}.json"
       EXPORT_DIR.mkdir(parents=True, exist_ok=True)
       
       with open(report_path, 'w', encoding='utf-8') as f:
           json.dump(report, f, indent=2, default=str)
       
       print(f"Performance report generated: {report_path}")
       
       # Display summary
       if "metrics" in report:
           if "system" in report["metrics"]:
               print("\nSystem Metrics:")
               for key, value in report["metrics"]["system"].items():
                   print(f"  {key}: {value}")
           
           if "visualizations" in report:
               print("\nVisualizations created:")
               for viz_type, path in report["visualizations"].items():
                   print(f"  {viz_type}: {path}")
                   
   except Exception as e:
       print(f"Report generation error: {e}")
       log(f"Report error: {e}", LogLevel.ERROR, "ANALYTICS")

# Helper functions for displaying results
def print_analysis_results(results: Dict, title: str):
   """Pretty print analysis results"""
   print(f"\n{'='*60}")
   print(f"{title.center(60)}")
   print(f"{'='*60}\n")
   
   for section, data in results.items():
       print(f"\n{section.upper().replace('_', ' ')}:")
       if isinstance(data, dict):
           for key, value in data.items():
               if isinstance(value, (int, float)):
                   print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
               else:
                   print(f"  {key}: {value}")
       elif isinstance(data, list):
           for item in data[:5]:  # Show first 5 items
               print(f"  - {item}")
           if len(data) > 5:
               print(f"  ... and {len(data) - 5} more")
       else:
           print(f"  {data}")

def print_bias_analysis(results: Dict):
   """Pretty print bias analysis results"""
   print(f"\n{'='*60}")
   print(f"{'BIAS DETECTION ANALYSIS'.center(60)}")
   print(f"{'='*60}\n")
   
   # Overall bias score
   bias_score = results.get("bias_score", 0.0)
   bias_level = "HIGH" if bias_score > 0.7 else "MODERATE" if bias_score > 0.4 else "LOW"
   
   print(f"Overall Bias Score: {bias_score:.2f} ({bias_level})")
   
   # Monolith bias
   print("\nMonolith Bias Analysis:")
   for monolith, bias_data in results.get("monolith_bias", {}).items():
       print(f"\n  {monolith}:")
       print(f"    Bias Type: {bias_data.get('bias_type', 'UNKNOWN')}")
       print(f"    Approval Rate: {bias_data.get('approval_rate', 0):.2%}")
       print(f"    Denial Rate: {bias_data.get('denial_rate', 0):.2%}")
       print(f"    Vote Entropy: {bias_data.get('vote_entropy', 0):.3f}")
   
   # Verdict distribution
   print("\nVerdict Distribution:")
   for verdict, rate in results.get("verdict_distribution", {}).items():
       print(f"  {verdict}: {rate:.2%}")

def print_quality_analysis(results: Dict):
   """Pretty print quality analysis results"""
   print(f"\n{'='*60}")
   print(f"{'DECISION QUALITY ANALYSIS'.center(60)}")
   print(f"{'='*60}\n")
   
   # Overall quality score
   overall_score = results.get("overall_quality_score", 0.0)
   quality_level = "EXCELLENT" if overall_score > 0.85 else "GOOD" if overall_score > 0.7 else "FAIR" if overall_score > 0.5 else "POOR"
   
   print(f"Overall Quality Score: {overall_score:.2f} ({quality_level})")
   
   # Individual metrics
   print(f"\nConsistency Score: {results.get('consistency_score', 0):.2f}")
   
   reliability = results.get("confidence_reliability", {})
   print(f"\nConfidence Reliability:")
   print(f"  High Confidence Accuracy: {reliability.get('high_confidence_accuracy', 0):.2%}")
   print(f"  Low Confidence Accuracy: {reliability.get('low_confidence_accuracy', 0):.2%}")
   
   # Recommendations
   print("\nRecommendations:")
   for i, rec in enumerate(results.get("recommendations", []), 1):
       print(f"  {i}. {rec}")

def print_anomaly_analysis(anomalies: List[Dict]):
   """Pretty print anomaly analysis results"""
   print(f"\n{'='*60}")
   print(f"{'ANOMALY DETECTION RESULTS'.center(60)}")
   print(f"{'='*60}\n")
   
   if not anomalies:
       print("No anomalies detected in decision history.")
       return
   
   print(f"Found {len(anomalies)} anomalous decisions:\n")
   
   for i, anomaly in enumerate(anomalies[:5], 1):  # Show top 5
       decision = anomaly["decision"]
       print(f"{i}. Query: {decision.get('query', 'Unknown')[:50]}...")
       print(f"   Verdict: {decision.get('verdict', 'Unknown')}")
       print(f"   Anomaly Score: {anomaly['anomaly_score']:.4f}")
       print(f"   Timestamp: {decision.get('timestamp', 'Unknown')}")
       print()
   
   if len(anomalies) > 5:
       print(f"... and {len(anomalies) - 5} more anomalies")

def print_prediction_results(prediction: Dict, query: str):
   """Pretty print prediction results"""
   print(f"\n{'='*60}")
   print(f"{'CONSENSUS PREDICTION'.center(60)}")
   print(f"{'='*60}\n")
   
   print(f"Query: {query}\n")
   
   if "error" in prediction:
       print(f"Error: {prediction['error']}")
       return
   
   print(f"Predicted Verdict: {prediction.get('predicted_verdict', 'UNKNOWN')}")
   print(f"Confidence: {prediction.get('confidence', 0):.2%}")
   print(f"Based on {prediction.get('similar_decisions', 0)} similar decisions\n")
   
   # Probability distribution
   print("Verdict Probabilities:")
   for verdict, prob in prediction.get("probability_distribution", {}).items():
       bar_length = int(prob * 40)
       bar = "█" * bar_length + "░" * (40 - bar_length)
       print(f"  {verdict:20} [{bar}] {prob:.2%}")
   
   # Expected monolith votes
   print("\nExpected Monolith Votes:")
   for monolith, votes in prediction.get("expected_monolith_votes", {}).items():
       print(f"\n  {monolith}:")
       for vote, prob in votes.items():
           print(f"    {vote}: {prob:.2%}")

# Integration with main system
def run_scheduled_analytics():
   """Run scheduled analytics tasks"""
   while True:
       try:
           # Wait for configured interval
           time.sleep(3600)  # Run every hour
           
           if not analytics_engine:
               initialize_analytics()
           
           # Run bias detection
           if len(decision_history) >= 50:
               bias_results = analytics_engine.detect_bias(list(decision_history))
               
               if bias_results["bias_score"] > ANALYTICS_CONFIG["bias_detection"]["threshold"]:
                   log(f"High bias detected: {bias_results['bias_score']:.2f}", 
                       LogLevel.WARNING, "ANALYTICS")
           
           # Detect anomalies
           anomalies = analytics_engine.detect_anomalies(list(decision_history)[-100:])
           if anomalies:
               log(f"Detected {len(anomalies)} anomalous decisions", 
                   LogLevel.WARNING, "ANALYTICS")
           
           # Generate daily report at midnight
           current_hour = datetime.now().hour
           if current_hour == 0:
               report = analytics_engine.generate_performance_report()
               
               # Save report
               report_path = EXPORT_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
               with open(report_path, 'w', encoding='utf-8') as f:
                   json.dump(report, f, indent=2, default=str)
               
               log(f"Daily analytics report generated: {report_path}", 
                   LogLevel.INFO, "ANALYTICS")
               
       except Exception as e:
           log(f"Scheduled analytics error: {e}", LogLevel.ERROR, "ANALYTICS")
           time.sleep(3600)  # Wait before retry

# Start analytics thread during system initialization
def start_analytics_daemon():
   """Start the analytics background daemon"""
   threading.Thread(target=run_scheduled_analytics, daemon=True).start()
   log("Analytics daemon started", LogLevel.INFO, "ANALYTICS")

# Add to initialization
if __name__ == "__main__":
   # Add analytics initialization to system startup
   initialize_analytics()
   start_analytics_daemon()

# ================================================================================
# END OF CONSENSUS SYSTEM v{VERSION}
# ================================================================================