
# consensus_config.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import time
from collections import deque
from typing import List, Dict, Any

# Version and Constants
VERSION = "6.3.8"
BUILD_DATE = "2025-07-31"
SESSION_ID = datetime.now().strftime("%Y%m%d%H%M%S")

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

# Data Classes
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

# Shared queues
notifications = deque(maxlen=5)
decision_history = deque(maxlen=100)
command_history = deque(maxlen=50)
log_entries = deque(maxlen=1000)
