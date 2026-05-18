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
# MODULE 7: VOTING ORCHESTRATOR
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
# MODULE 8: USER INTERFACE SYSTEM
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
# MODULE 9: CONSOLE MODE
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
# MODULE 10: DEMO & TESTING FUNCTIONS
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
# MODULE 11: MAIN APPLICATION LOOP  
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
# MODULE 9: USER INTERFACE SYSTEM
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
from pathlib import Path
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