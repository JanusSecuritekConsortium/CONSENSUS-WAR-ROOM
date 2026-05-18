def add_decision_to_history(query: str, verdict: str, reasoning: str = None, command_log: str = None):
    """
    Add a decision to the history with enhanced logging capabilities
    
    Args:
        query: The original query/question posed to the tribunal
        verdict: The final consensus decision (APPROVE/DENY/DEADLOCK)
        reasoning: Optional detailed reasoning for the decision
        command_log: Optional command that triggered this decision
    """
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

def log_command_response(command: str, response: str, success: bool = True):
    """
    Simplified logging for command/response pairs
    
    Args:
        command: The command that was executed
        response: The response or result
        success: Whether the command was successful
    """
    status = "SUCCESS" if success else "ERROR"
    log_entry = f"COMMAND: {command}\nRESPONSE: {response}\nSTATUS: {status}"
    log(log_entry)

# Enhanced process_command function with logging
def process_command_with_logging(command: str) -> str:
    """
    Enhanced command processor with built-in logging
    """
    start_time = time.time()
    
    try:
        # Process the command (your existing logic here)
        response = process_command(command)
        
        # Log successful command execution
        execution_time = time.time() - start_time
        log_command_response(
            command=command,
            response=f"{response} (executed in {execution_time:.2f}s)",
            success=True
        )
        
        return response
        
    except Exception as e:
        # Log failed command execution
        execution_time = time.time() - start_time
        error_response = f"Command failed: {str(e)}"
        log_command_response(
            command=command,
            response=f"{error_response} (failed after {execution_time:.2f}s)",
            success=False
        )
        
        return error_response