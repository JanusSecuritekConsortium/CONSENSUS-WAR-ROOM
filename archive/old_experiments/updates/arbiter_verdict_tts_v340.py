# === ARBITER VERDICT + TTS (v3.4.0) ===
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
            engine.setProperty('rate', 150)  # Slower for dramatic effect
            engine.setProperty('volume', 0.9)
            
            # Generate TTS
            tts_text = f"Consensus tribunal decision: {verdict.lower()}"
            engine.say(tts_text)
            engine.runAndWait()
            
            log(f"[TTS] Announced verdict: {verdict}")
            
        except ImportError:
            log("[TTS] pyttsx3 not installed - install with: pip install pyttsx3")
        except Exception as e:
            log(f"[TTS Error] {e}")

# === UPDATED DEMO VOTING PROCESS ===
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

# === CONFIGURATION UPDATE FOR TTS ===
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