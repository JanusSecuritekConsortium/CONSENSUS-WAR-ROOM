import json
from datetime import datetime
import os

CONSENSUS_PATH = "J:/CONSENSUS_SYSTEM/_ARBITER/proposal.json"
DECISION_LOG_PATH = "J:/CONSENSUS_SYSTEM/_ARBITER/decision_history.json"
LOG_PATH = "J:/CONSENSUS_SYSTEM/_ARBITER/decision_history.log"

def send_to_consensus(text, monolith):
    proposal = {
        "proposal": text,
        "submitted_by": monolith,
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        with open(CONSENSUS_PATH, "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)
        return f"[{monolith}] Proposal sent to ARBITER."
    except Exception as e:
        return f"[ERROR] Could not write proposal: {e}"

def read_latest_verdict():
    if not os.path.exists(DECISION_LOG_PATH):
        return "No decision history available."

    try:
        with open(DECISION_LOG_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not history:
                return "No decisions recorded yet."
            latest = history[-1]
            return f"[ARBITER] {latest.get('final_decision', 'No verdict')} — {latest.get('summary', '')}"
    except Exception as e:
        return f"[ERROR] Could not read decision history: {e}"

def read_log():
    if not os.path.exists(LOG_PATH):
        return "Log not found."
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return f.read()[-2000:]  # Show last 2k chars
    except Exception as e:
        return f"Log read error: {e}"

def execute_system_command(cmd):
    if cmd == "shutdown":
        return "[SYSTEM] Shutdown command issued."
    if cmd == "restart":
        return "[SYSTEM] Restart command issued."
    return "[SYSTEM] Unknown command."
