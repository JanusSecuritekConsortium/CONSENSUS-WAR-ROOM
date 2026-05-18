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
        CONFIG["system"]["current_view"] = ViewMode.MAIN.value
    elif key in (ord('v'), ord('V')):
        # Trigger demo voting process
        threading.Thread(target=demo_voting_process, daemon=True).start()
    elif key in (ord('c'), ord('C')):
        # Enter console mode
        return False  # Exit curses mode to enter console mode
    elif key in (ord('1')):
        # Toggle RATIONALIS view
        CONFIG["system"]["current_view"] = ViewMode.RATIONALIS.value
    elif key in (ord('2')):
        # Toggle AETERNUM view
        CONFIG["system"]["current_view"] = ViewMode.AETERNUM.value
    elif key in (ord('3')):
        # Toggle BELLATOR view
        CONFIG["system"]["current_view"] = ViewMode.BELLATOR.value
    elif key in (ord('7')):
        # Toggle decision history view
        CONFIG["system"]["current_view"] = ViewMode.HISTORY.value
    elif key in (ord('9')):
        # Toggle diagnostics view
        if CONFIG["system"]["current_view"] == ViewMode.DIAGNOSTICS.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.DIAGNOSTICS.value
    elif key in (ord('a'), ord('A')):
        # Toggle analytics view
        if CONFIG["system"]["current_view"] == ViewMode.ANALYTICS.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.ANALYTICS.value
    elif key in (ord('h'), ord('H')):
        # Show help
        if CONFIG["system"]["current_view"] == ViewMode.HELP.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.HELP.value
    
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
                    result = run_console_mode()
                    
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
                            
                    # If we're exiting completely from console, break the loop
                    if result == "exit":
                        running = False
                else:
                    running = handle_input(stdscr, key)
            
            # Refresh screen periodically
            current_time = time.time()
            if current_time - last_refresh > 0.1:
                # Render current view
                current_view = CONFIG["system"]["current_view"]
                theme = CONFIG["system"]["theme"]
                
                if current_view == ViewMode.MAIN.value:
                    render_main_screen(stdscr, theme)
                elif current_view == ViewMode.HISTORY.value:
                    render_decision_history(stdscr)
                elif current_view == ViewMode.RATIONALIS.value:
                    render_rationalis_screen(stdscr, theme)
                elif current_view == ViewMode.AETERNUM.value:
                    render_aeternum_screen(stdscr, theme)
                elif current_view == ViewMode.BELLATOR.value:
                    render_bellator_screen(stdscr, theme)
                elif current_view == ViewMode.HELP.value:
                    render_help_screen(stdscr)
                elif current_view == ViewMode.CONFIG.value:
                    render_config_screen(stdscr)
                # Add other views (diagnostics, analytics) as needed
                
                stdscr.refresh()
                last_refresh = current_time
                
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            log(f"UI loop error: {e}", LogLevel.ERROR, "UI")
            log(f"Traceback: {traceback.format_exc()}", LogLevel.DEBUG, "UI")
            add_notification(f"UI error: {str(e)}", NotificationLevel.ERROR)

def demo_voting_process():
    """Enhanced demo voting process with sample queries"""
    queries = [
        f"Should we proceed with operation at {datetime.datetime.now().strftime('%H:%M')}?",
        "Authorize emergency protocol for critical system maintenance?",
        "Deploy additional resources for enhanced security monitoring?",
        "Implement new strategic framework for tactical operations?",
        "Approve expansion of# ================================================================================
# MODULE 10: Console Mode
# ================================================================================

def command(name):
    """Decorator to register a console command."""
    def decorator(func):
        COMMANDS[name] = func
        return func
    return decorator

@command("help")
def cmd_help(args):
    """Display help for console commands"""
    print("\n📖 CONSENSUS CONSOLE HELP:")
    print("┌─ VOTING COMMANDS ────────────────────────────────────────────────────────┐")
    print("│ vote <query>    - Submit query to AI tribunal for consensus decision     │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ SYSTEM COMMANDS ────────────────────────────────────────────────────────┐")
    print("│ status          - Show system operational status and monolith health     │")
    print("│ health          - Display detailed system health metrics                 │")
    print("│ config          - Display current system configuration                   │")
    print("│ reload          - Reload configuration from disk                         │")
    print("│ theme <name>    - Change UI theme                                        │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ DATA COMMANDS ──────────────────────────────────────────────────────────┐")
    print("│ history [N]     - Show last N decisions (default: 10)                    │")
    print("│ export <format> - Export decision history (json, csv, txt, logs, all)    │")
    print("│ analyze         - Run analytics on decision history                      │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ TESTING COMMANDS ────────────────────────────────────────────────────────┐")
    print("│ demo [N]        - Run N random voting scenarios (default: 5)             │")
    print("│ stress [seconds]- Run stress test for specified seconds (default: 30)    │")
    print("└───────────────────────────────────────────────────────────────────────────┘")
    print("┌─ UI COMMANDS ────────────────────────────────────────────────────────────┐")
    print("│ clear           - Clear console screen                                   │")
    print("│ gui             - Return to GUI mode                                     │")
    print("│ help            - Show this help message                                 │")
    print("│ exit/quit       - Exit console mode                                      │")
    print("└───────────────────────────────────────────────────────────────────────────┘")

@command("vote")
def cmd_vote(args):
    """Submit a query to tribunal voting"""
    if not args:
        print("Usage: vote <query>")
        return
    
    query = " ".join(args)
    print(f"\n🗳️  Initiating tribunal vote on: {query}")
    print("-" * 60)
    
    # Execute vote
    orchestrator = VotingOrchestrator()
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

@command("status")
def cmd_status(args):
    """Display system status and monoliths health"""
    print("\n📊 SYSTEM STATUS:")
    print(f"  Version: {VERSION} (Build: {BUILD_HASH})")
    print(f"  Uptime: {get_system_uptime()}")
    print(f"  Total Decisions: {len(decision_history)}")
    print(f"  System Mode: {CONFIG['system']['system_mode']}")
    print(f"  API Status: {system_health.network_status}")
    print(f"  TTS Status: {system_health.tts_status}")
    
    print("\n🤖 MONOLITH STATUS:")
    orchestrator = VotingOrchestrator()
    model_results = orchestrator.check_all_models()
    for name, result in model_results.items():
        status = result["status"]
        performance = result["performance"]
        status_icon = "🟢" if status == "ready" else "🔴"
        print(f"  {status_icon} {name}: {status.upper()}")
        print(f"     Model: {performance['model']}")
        print(f"     Votes: {performance['total_votes']}, Errors: {performance['error_count']}")
        print(f"     Avg Response: {performance['avg_response_time']:.2f}s")

@command("health")
def cmd_health(args):
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
    
    if PSUTIL_AVAILABLE:
        import psutil
        print("\n💻 ADDITIONAL SYSTEM METRICS:")
        print(f"  CPU Cores: {psutil.cpu_count(logical=True)} (Logical), {psutil.cpu_count(logical=False)} (Physical)")
        print(f"  Total Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
        print(f"  Available Memory: {psutil.virtual_memory().available / (1024**3):.1f} GB")
        print(f"  Swap Usage: {psutil.swap_memory().percent:.1f}%")
        print(f"  Network Sent: {psutil.net_io_counters().bytes_sent / (1024**2):.1f} MB")
        print(f"  Network Received: {psutil.net_io_counters().bytes_recv / (1024**2):.1f} MB")

@command("history")
def cmd_history(args):
    """Display decision history with enhanced formatting"""
    try:
        count = int(args[0]) if args else 10
        count = min(count, len(decision_history))
    except (ValueError, IndexError):
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

@command("export")
def cmd_export(args):
    """Export decision history in different formats"""
    if not args:
        print("Usage: export <json|csv|txt|logs|all>")
        return
    
    format_type = args[0].lower()
    if format_type == "json":
        filename = export_decisions_json()
        print(f"✅ Decisions exported to: {filename}")
    elif format_type == "csv":
        filename = export_decisions_csv()
        print(f"✅ Decisions exported to: {filename}")
    elif format_type == "txt":
        filename = export_decisions_txt()
        print(f"✅ Decisions exported to: {filename}")
    elif format_type == "logs":
        filename = export_system_logs()
        print(f"✅ System logs exported to: {filename}")
    elif format_type == "all":
        export_all()
        print("✅ All export formats completed.")
    else:
        print(f"❌ Unknown export format: {format_type}")

@command("config")
def cmd_config(args):
    """Display system configuration"""
    if not args:
        # Show main sections
        print("\n⚙️  SYSTEM CONFIGURATION:")
        
        for section in CONFIG:
            if isinstance(CONFIG[section], dict):
                keys_count = len(CONFIG[section])
                print(f"  {section} ({keys_count} settings)")
        
        print("\nUse 'config <section>' to see specific settings")
        return
    
    section = args[0].lower()
    if section in CONFIG and isinstance(CONFIG[section], dict):
        print(f"\n⚙️  {section.upper()} CONFIGURATION:")
        for key, value in CONFIG[section].items():
            # Format complex values for better readability
            if isinstance(value, dict):
                print(f"  {key}: {len(value)} items")
            elif isinstance(value, list):
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"❌ Unknown configuration section: {section}")

@command("reload")
def cmd_reload(args):
    """Reload configuration from disk"""
    backup_config(CONFIG_PATH)
    load_system_config()
    print("✅ Configuration reloaded from disk")

@command("theme")
def cmd_theme(args):
    """Change UI theme"""
    themes = list(THEME_DEFINITIONS.keys())
    
    if not args:
        print("\n🎨 Available themes:")
        for i, theme in enumerate(themes):
            current = " (current)" if theme == CONFIG['system']['theme'] else ""
            print(f"  {i}: {theme} - {THEME_DEFINITIONS[theme]['name']}{current}")
        return
    
    try:
        if args[0].isdigit():
            theme_index = int(args[0])
            if 0 <= theme_index < len(themes):
                CONFIG["system"]["theme"] = themes[theme_index]
                save_system_config()
                print(f"✅ Theme changed to: {themes[theme_index]} ({THEME_DEFINITIONS[themes[theme_index]]['name']})")
            else:
                print(f"❌ Invalid theme index. Choose 0-{len(themes)-1}")
        else:
            # Try to find theme by name
            theme_name = args[0].lower()
            if theme_name in themes:
                CONFIG["system"]["theme"] = theme_name
                save_system_config()
                print(f"✅ Theme changed to: {theme_name} ({THEME_DEFINITIONS[theme_name]['name']})")
            else:
                print(f"❌ Unknown theme: {args[0]}")
    except (ValueError, IndexError):
        print("❌ Invalid theme selection. Use 'theme' without args to see available themes.")

@command("demo")
def cmd_demo(args):
    """Run demo voting scenarios"""
    try:
        count = int(args[0]) if args else 5
    except (ValueError, IndexError):
        count = 5
    
    print(f"Running {count} demo vote scenarios...")
    
    queries = [
        "Authorize emergency maintenance on system core?",
        "Deploy additional resources to sector 7?",
        "Grant clearance for level 5 security access?",
        "Approve code update to critical subsystems?",
        "Authorize tactical deployment of assets?",
        "Proceed with quantum firewall activation?",
        "Divert resources to defensive operations?",
        "Execute contingency protocol alpha?",
        "Initiate complete system reset sequence?",
        "Deploy emergency response team to location?"
    ]
    
    orchestrator = VotingOrchestrator()
    
    for i in range(min(count, len(queries))):
        query = queries[i]
        print(f"\n===== DEMO VOTE {i+1}/{count} =====")
        print(f"Query: {query}")
        
        consensus, confidence, reasoning, votes = orchestrator.initiate_vote(query)
        
        print(f"Result: {consensus.value} (Confidence: {confidence:.0%})")
        print(f"Individual votes: " + ", ".join([f"{name}: {vote.vote.value}" for name, vote in votes.items()]))
        
        # Small delay between votes
        time.sleep(1)
    
    print("\n✅ Demo complete!")

@command("stress")
def cmd_stress(args):
    """Run a stress test on the voting system"""
    try:
        duration = int(args[0]) if args else 30  # Default 30 seconds
    except (ValueError, IndexError):
        duration = 30
    
    print(f"Running stress test for {duration} seconds...")
    
    queries = [
        "Authorize protocol alpha?",
        "Execute contingency plan?",
        "Deploy tactical assets?",
        "Grant security clearance?",
        "Proceed with operation?",
        "Initiate system maintenance?"
    ]
    
    orchestrator = VotingOrchestrator()
    start_time = time.time()
    count = 0
    
    try:
        while time.time() - start_time < duration:
            query = random.choice(queries)
            print(f"Vote {count+1}: {query}", end="... ", flush=True)
            
            try:
                consensus, _, _, _ = orchestrator.initiate_vote(query)
                print(f"{consensus.value}")
            except Exception as e:
                print(f"ERROR: {e}")
            
            count += 1
        
        elapsed = time.time() - start_time
        rate = count / elapsed
        
        print(f"\n✅ Stress test complete:")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Votes processed: {count}")
        print(f"  Rate: {rate:.2f} votes/second")
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        rate = count / max(0.1, elapsed)
        
        print(f"\n⚠️ Stress test interrupted:")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Votes processed: {count}")
        print(f"  Rate: {rate:.2f} votes/second")

@command("analyze")
def cmd_analyze(args):
    """Analyze decision patterns and voting trends"""
    if len(decision_history) < 5:
        print("❌ Not enough decisions to analyze. Need at least 5 decisions.")
        return
    
    print("\n📊 DECISION ANALYSIS:")
    print("-" * 80)
    
    # Use ConsensusEngine to analyze patterns
    analysis = ConsensusEngine.analyze_voting_patterns(list(decision_history))
    
    # Overall statistics
    print(f"Total decisions: {analysis['total_decisions']}")
    print(f"Approval rate: {analysis['approval_rate']:.1%}")
    print(f"Denial rate: {analysis['denial_rate']:.1%}")
    print(f"Deadlock rate: {analysis.get('deadlock_rate', 0):.1%}")
    print(f"Average confidence: {analysis['average_confidence']:.1%}")
    
    # Trend analysis
    trend = analysis.get('recent_trend', 'unknown')
    print(f"\nRecent trend: {trend}")
    
    # Agreement rates
    if 'agreement_rates' in analysis and analysis['agreement_rates']:
        print("\nMonolith agreement rates:")
        for pair, rate in analysis['agreement_rates'].items():
            print(f"  {pair}: {rate:.1%}")
    
    # Conduct bias analysis if we have enough data
    if len(decision_history) >= 10:
        print("\n🔍 BIAS ANALYSIS:")
        bias_analysis = ConsensusEngine.perform_bias_analysis(list(decision_history))
        
        if bias_analysis.get('status') == 'success':
            # Monolith influence
            print("\nMonolith influence scores:")
            for monolith, score in bias_analysis.get('monolith_influence', {}).items():
                print(f"  {monolith}: {score:.2f}")
            
            # Keyword bias
            if bias_analysis.get('keyword_bias'):
                print("\nKeyword bias detection:")
                for keyword, data in bias_analysis['keyword_bias'].items():
                    bias_level = data.get('bias_level', 'unknown')
                    approve_rate = data.get('approve_rate', 0)
                    print(f"  {keyword}: {approve_rate:.1%} approval rate ({bias_level} bias)")
    
    # Confidence analysis
    print("\n📈 CONFIDENCE ANALYSIS:")
    conf_analysis = ConsensusEngine.advanced_confidence_analysis(list(decision_history))
    
    if conf_analysis.get('status') == 'success':
        print(f"Mean confidence: {conf_analysis['mean_confidence']:.1%}")
        print(f"Median confidence: {conf_analysis['median_confidence']:.1%}")
        print(f"Range: {conf_analysis['min_confidence']:.1%} - {conf_analysis['max_confidence']:.1%}")
        print(f"Standard deviation: {conf_analysis['confidence_stdev']:.2f}")
        print(f"Confidence trend: {conf_analysis['confidence_trend']}")

@command("clear")
def cmd_clear(args):
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("CONSENSUS Console - Type 'help' for commands")

@command("gui")
def cmd_gui(args):
    """Return to GUI mode"""
    print("Returning to GUI mode...")
    return True  # Special return value to signal GUI return

def setup_readline():
    """Configure readline for command completion and history"""
    try:
        import readline
        
        # Command completion
        def completer(text, state):
            options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
            if state < len(options):
                return options[state]
            else:
                return None
        
        readline.parse_and_bind("tab: complete")
        readline.set_completer(completer)
        
        # Command history
        if hasattr(readline, "read_history_file") and hasattr(readline, "write_history_file"):
            history_file = ARBITER_DIR / "console_history"
            try:
                if history_file.exists():
                    readline.read_history_file(str(history_file))
                
                import atexit
                atexit.register(readline.write_history_file, str(history_file))
            except Exception as e:
                log(f"Failed to setup readline history: {e}", LogLevel.WARNING, "CONSOLE")
    
    except (ImportError, Exception) as e:
        log(f"Readline setup failed: {e}", LogLevel.WARNING, "CONSOLE")

def run_console_mode():
    """Enhanced console mode with comprehensive commands"""
    setup_readline()
    
    if COLORAMA_AVAILABLE:
        print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════╗")
        print(f"{Fore.CYAN}║{Fore.YELLOW} CONSENSUS SYSTEM{Fore.CYAN} - {Fore.WHITE}TACTICAL COMMAND INTERFACE {Fore.CYAN}                         ║")
        print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"Version: {VERSION} | Build: {BUILD_HASH} | Session: {SESSION_ID[:8]}")
        print(f"Type '{Fore.GREEN}help{Style.RESET_ALL}' for available commands or '{Fore.GREEN}exit{Style.RESET_ALL}' to quit.\n")
    else:
        print("\n╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║ CONSENSUS SYSTEM - TACTICAL COMMAND INTERFACE                            ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print(f"Version: {VERSION} | Build: {BUILD_HASH} | Session: {SESSION_ID[:8]}")
        print("Type 'help' for available commands or 'exit' to quit.\n")
    
    while True:
        try:
            # Format prompt with system mode
            mode = CONFIG["system"]["system_mode"]
            if COLORAMA_AVAILABLE:
                mode_color = Fore.GREEN if mode == SystemMode.READY.value else Fore.YELLOW
                prompt = f"{mode_color}[{mode}]{Style.RESET_ALL} CONSENSUS> "
            else:
                prompt = f"[{mode}] CONSENSUS> "
            
            command_input = input(prompt).strip()
            
            if not command_input:
                continue
            
            # Parse command and arguments
            parts = command_input.split()
            cmd_name, *args = parts
            cmd_name = cmd_name.lower()
            
            # Handle exit command
            if cmd_name in ["exit", "quit"]:
                if COLORAMA_AVAILABLE:
                    print(f"{Fore.YELLOW}Exiting console mode...{Style.RESET_ALL}")
                else:
                    print("Exiting console mode...")
                break
            
            # Store in command history
            command_history.append(command_input)
            
            # Execute command
            if cmd_name in COMMANDS:
                result = COMMANDS[cmd_name](args)
                # Special handling for GUI return
                if result is True and cmd_name == "gui":
                    return "gui"
            else:
                if COLORAMA_AVAILABLE:
                    print(f"{Fore.RED}Unknown command: {cmd_name}. Type 'help' for available commands.{Style.RESET_ALL}")
                else:
                    print(f"Unknown command: {cmd_name}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except EOFError:
            print("\nEnd of input. Exiting console.")
            break
        except Exception as e:
            if COLORAMA_AVAILABLE:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            else:
                print(f"Error: {e}")
            log(f"Console error: {e}", LogLevel.ERROR, "CONSOLE")
    
# ================================================================================
# MODULE 11: Export & I/O Operations
# ================================================================================

def get_export_path(name: str, ext: str) -> Path:
    """Generate export path with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = EXPORT_DIR / f"{name}_{timestamp}.{ext}"
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return export_path

def export_decisions_json(path: Path = None) -> str:
    """Export decision history to JSON"""
    if path is None:
        path = get_export_path("decisions", "json")
    
    try:
        # Convert decisions to serializable format
        export_data = []
        for decision in decision_history:
            decision_copy = decision.copy()
            
            # Convert timestamp
            if isinstance(decision_copy.get("timestamp"), datetime.datetime):
                decision_copy["timestamp"] = decision_copy["timestamp"].isoformat()
                
            export_data.append(decision_copy)
        
        # Add metadata
        full_export = {
            "metadata": {
                "system": "CONSENSUS",
                "version": VERSION,
                "build_hash": BUILD_HASH,
                "export_time": datetime.datetime.now().isoformat(),
                "decision_count": len(export_data)
            },
            "decisions": export_data
        }
        
        # Write to file
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(full_export, f, indent=4)
        
        log(f"Decision history exported to {path}", LogLevel.INFO, "EXPORT")
        return str(path)
        
    except Exception as e:
        log(f"Failed to export decisions to JSON: {e}", LogLevel.ERROR, "EXPORT")
        raise

def export_decisions_csv(path: Path = None) -> str:
    """Export decision history to CSV"""
    if path is None:
        path = get_export_path("decisions", "csv")
    
    try:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            # Define CSV columns
            columns = [
                "id", "timestamp", "query", "verdict", "confidence", 
                "rationalis_vote", "aeternum_vote", "bellator_vote",
                "session_id"
            ]
            
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            # Write each decision
            for decision in decision_history:
                # Extract votes for each monolith
                votes = {}
                if "individual_votes" in decision:
                    for monolith, vote_data in decision["individual_votes"].items():
                        if isinstance(vote_data, dict):
                            monolith_lower = monolith.lower()
                            votes[f"{monolith_lower}_vote"] = vote_data.get("vote", "UNKNOWN")
                
                # Convert timestamp
                if isinstance(decision.get("timestamp"), datetime.datetime):
                    timestamp = decision["timestamp"].isoformat()
                else:
                    timestamp = str(decision.get("timestamp", ""))
                
                # Write row
                row = {
                    "id": decision.get("id", ""),
                    "timestamp": timestamp,
                    "query": decision.get("query", ""),
                    "verdict": decision.get("verdict", ""),
                    "confidence": decision.get("confidence", 0.0),
                    "rationalis_vote": votes.get("rationalis_vote", ""),
                    "aeternum_vote": votes.get("aeternum_vote", ""),
                    "bellator_vote": votes.get("bellator_vote", ""),
                    "session_id": decision.get("session_id", "")
                }
                
                writer.writerow(row)
        
        log(f"Decision history exported to {path}", LogLevel.INFO, "EXPORT")
        return str(path)
        
    except Exception as e:
        log(f"Failed to export decisions to CSV: {e}", LogLevel.ERROR, "EXPORT")
        raise

def export_decisions_txt(path: Path = None) -> str:
    """Export decision history to formatted text"""
    if path is None:
        path = get_export_path("decisions", "txt")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write(f"CONSENSUS SYSTEM DECISION HISTORY\n")
            f.write(f"Version: {VERSION} | Build: {BUILD_HASH}\n")
            f.write(f"Export Time: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Total Decisions: {len(decision_history)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write each decision
            for i, decision in enumerate(decision_history, 1):
                # Format timestamp
                if isinstance(decision.get("timestamp"), datetime.datetime):
                    timestamp = decision["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = str(decision.get("timestamp", ""))
                
                # Write decision header
                f.write(f"DECISION #{i}\n")
                f.write("-" * 40 + "\n")
                f.write(f"ID: {decision.get('id', 'N/A')}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Query: {decision.get('query', '')}\n")
                f.write(f"Verdict: {decision.get('verdict', '')}\n")
                f.write(f"Confidence: {decision.get('confidence', 0.0):.1%}\n")
                
                # Individual votes
                if "individual_votes" in decision:
                    f.write("\nIndividual Votes:\n")
                    for monolith, vote_data in decision["individual_votes"].items():
                        if isinstance(vote_data, dict):
                            vote = vote_data.get("vote", "UNKNOWN")
                            confidence = vote_data.get("confidence", 0.0)
                            f.write(f"  {monolith}: {vote} (confidence: {confidence:.1%})\n")
                
                # Reasoning
                if "reasoning" in decision:
                    reasoning = decision["reasoning"]
                    if len(reasoning) > 300:
                        reasoning = reasoning[:300] + "..."
                    f.write(f"\nReasoning: {reasoning}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        log(f"Decision history exported to {path}", LogLevel.INFO, "EXPORT")
        return str(path)
        
    except Exception as e:
        log(f"Failed to export decisions to TXT: {e}", LogLevel.ERROR, "EXPORT")
        raise

def export_system_logs(path: Path = None) -> str:
    """Export system logs to text file"""
    if path is None:
        path = get_export_path("system_logs", "txt")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write(f"CONSENSUS SYSTEM LOGS\n")
            f.write(f"Version: {VERSION} | Build: {BUILD_HASH}\n")
            f.write(f"Export Time: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Total Log Entries: {len(log_entries)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write each log entry
            for entry in log_entries:
                # Format timestamp
                if isinstance(entry.get("timestamp"), datetime.datetime):
                    timestamp = entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = str(entry.get("timestamp", ""))
                
                # Get other fields with defaults
                level = entry.get("level", "INFO")
                component = entry.get("component", "SYSTEM")
                message = entry.get("message", "")
                session = entry.get("session_id", "")
                
                # Format log line
                session_part = f" [{session}]" if session else ""
                log_line = f"[{timestamp}] [{level:8}] [{component:12}]{session_part} {message}"
                
                f.write(f"{log_line}\n")
        
        log(f"System logs exported to {path}", LogLevel.INFO, "EXPORT")
        return str(path)
        
    except Exception as e:
        log(f"Failed to export system logs: {e}", LogLevel.ERROR, "EXPORT")
        raise

def export_all():
    """Export all data formats"""
    try:
        json_path = export_decisions_json()
        print(f"✅ Decisions exported to JSON: {json_path}")
        
        csv_path = export_decisions_csv()
        print(f"✅ Decisions exported to CSV: {csv_path}")
        
        txt_path = export_decisions_txt()
        print(f"✅ Decisions exported to TXT: {txt_path}")
        
        log_path = export_system_logs()
        print(f"✅ System logs exported to: {log_path}")
        
        log("All export formats completed successfully", LogLevel.INFO, "EXPORT")
        
    except Exception as e:
        log(f"Export all failed: {e}", LogLevel.ERROR, "EXPORT")
# ================================================================================
# MODULE 12: Monolith Data Simulation & Updates
# ================================================================================

def update_rationalis_data():
    """Update logical analysis data for RATIONALIS monolith"""
    try:
        # Ensure the structure exists
        if "logical_analyses" not in monolith_data.rationalis:
            monolith_data.rationalis["logical_analyses"] = deque(maxlen=20)
        if "system_logs" not in monolith_data.rationalis:
            monolith_data.rationalis["system_logs"] = deque(maxlen=50)
        if "execution_times" not in monolith_data.rationalis:
            monolith_data.rationalis["execution_times"] = deque(maxlen=100)
        if "confidence_history" not in monolith_data.rationalis:
            monolith_data.rationalis["confidence_history"] = deque(maxlen=100)
        
        # Simulate efficiency rating (random walk)
        current = monolith_data.rationalis.get("efficiency_rating", 0.85)
        monolith_data.rationalis["efficiency_rating"] = max(0.50, min(0.99, current + random.uniform(-0.02, 0.02)))
        
        # Generate a new logical analysis
        if random.random() < 0.3:  # 30% chance of new analysis
            new_analysis = LogicalAnalysis(
                query=random.choice([
                    "Evaluate risk of quantum computing breakthrough",
                    "Analyze tactical viability of resource allocation",
                    "Determine optimal emergency response protocol",
                    "Assess system readiness for defense scenario",
                    "Evaluate long-term strategic alliance possibilities"
                ]),
                conclusion=random.choice([
                    "Probability high (87%)",
                    "Probability low (23%)",
                    "Inconclusive with current data",
                    "Strategically advantageous",
                    "Tactical vulnerability detected"
                ]),
                reasoning=[
                    "Primary factor: historical precedent analysis",
                    "Secondary factor: resource utilization projection",
                    "Tertiary factor: technological advancement rate"
                ],
                confidence=random.uniform(0.65, 0.95),
                logical_fallacies=random.sample([
                    "Appeal to authority",
                    "False dichotomy",
                    "Post hoc fallacy",
                    "Slippery slope",
                    "Confirmation bias"
                ], k=random.randint(0, 2)),
                timestamp=datetime.datetime.now(),
                execution_time=random.uniform(0.2, 1.5)
            )
            monolith_data.rationalis["logical_analyses"].append(new_analysis)
        
        # Generate system logs
        if random.random() < 0.4:  # 40% chance of new log
            new_log = {
                "level": random.choice(["INFO", "DEBUG", "WARNING", "ERROR"]),
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "message": random.choice([
                    "Executing logical matrix comparison",
                    "Logic gate optimization completed",
                    "Fallacy detection engine calibrated",
                    "Paradox resolution algorithm engaged",
                    "Inference engine optimization in progress",
                    "Syllogism validation complete",
                    "Quantum logic subroutine initialized",
                    "Pattern recognition threshold adjusted",
                    "Logic subsystem integrity check passed",
                    "WARNING: Possible circular reasoning detected",
                    "ERROR: Logical contradiction in input data"
                ])
            }
            monolith_data.rationalis["system_logs"].append(new_log)
        
        # Update execution times
        monolith_data.rationalis["execution_times"].append(random.uniform(0.1, 1.2))
        
        # Update confidence history
        monolith_data.rationalis["confidence_history"].append(random.uniform(0.7, 0.98))
        
        # Update last updated timestamp
        monolith_data.rationalis["last_update"] = datetime.datetime.now()
        return True
    except Exception as e:
        log(f"Error updating RATIONALIS data: {e}", LogLevel.ERROR, "MONOLITH")
        return False

def update_aeternum_data():
    """Update financial and market data for AETERNUM monolith"""
    try:
        with market_lock:
            # Ensure the necessary structures exist
            if "market_indices" not in monolith_data.aeternum:
                monolith_data.aeternum["market_indices"] = {
                    "S&P 500": {"value": 5320.42, "change": 0.3, "trend": "up"},
                    "NASDAQ": {"value": 18750.65, "change": 0.5, "trend": "up"},
                    "Dow Jones": {"value": 42150.30, "change": 0.1, "trend": "up"},
                    "BTC/USD": {"value": 84250.75, "change": -2.1, "trend": "down"},
                    "ETH/USD": {"value": 5120.25, "change": -1.5, "trend": "down"},
                    "Gold": {"value": 2785.50, "change": 0.8, "trend": "up"},
                    "Crude Oil": {"value": 82.45, "change": -0.6, "trend": "down"}
                }
            
            if "portfolio_performance" not in monolith_data.aeternum:
                monolith_data.aeternum["portfolio_performance"] = {
                    "daily_change": 0.86,
                    "weekly_change": 2.34,
                    "monthly_change": -1.45,
                    "yearly_change": 12.67,
                    "top_performers": ["NVDA", "MSFT", "AMZN"],
                    "worst_performers": ["IBM", "INTC", "T"]
                }
                
            if "economic_indicators" not in monolith_data.aeternum:
                monolith_data.aeternum["economic_indicators"] = {
                    "inflation": 2.4,
                    "unemployment": 3.7,
                    "fed_rate": 3.75,
                    "treasury_10y": 3.45,
                    "oil_price": 74.32
                }
            
            # Update market indices with small random changes
            for index, data in monolith_data.aeternum["market_indices"].items():
                change = random.uniform(-0.5, 0.5)
                # Apply larger changes to crypto
                if "BTC" in index or "ETH" in index:
                    change = random.uniform(-2.0, 2.0)
                
                data["change"] = round(change, 2)
                data["trend"] = "up" if change >= 0 else "down"
                
                # Update value based on change
                current_value = data["value"]
                percent_change = change / 100.0
                data["value"] = round(current_value * (1 + percent_change), 2)
            
            # Update volatility index (VIX-like)
            current_vix = monolith_data.aeternum.get("volatility_index", 18.5)
            monolith_data.aeternum["volatility_index"] = max(10.0, min(45.0, current_vix + random.uniform(-1.0, 1.0)))
            
            # Update market sentiment (0-1 scale)
            current_sentiment = monolith_data.aeternum.get("market_sentiment", 0.65)
            monolith_data.aeternum["market_sentiment"] = max(0.1, min(0.9, current_sentiment + random.uniform(-0.05, 0.05)))
            
            # Random change to the portfolio performance
            portfolio = monolith_data.aeternum["portfolio_performance"]
            
            portfolio["daily_change"] = round(random.uniform(-1.5, 1.5), 2)
            portfolio["weekly_change"] = round(random.uniform(-3.0, 3.0), 2)
            portfolio["monthly_change"] = round(random.uniform(-5.0, 5.0), 2)
            portfolio["yearly_change"] = round(random.uniform(-10.0, 20.0), 2)
            
            # Update economic indicators with small changes
            for indicator, value in monolith_data.aeternum["economic_indicators"].items():
                if indicator in ["inflation", "unemployment", "fed_rate", "treasury_10y"]:
                    # These are percentages, small changes
                    change = random.uniform(-0.1, 0.1)
                    monolith_data.aeternum["economic_indicators"][indicator] = max(0.1, value + change)
                elif indicator == "oil_price":
                    # Oil price can be more volatile
                    change = random.uniform(-1.0, 1.0)
                    monolith_data.aeternum["economic_indicators"][indicator] = max(30.0, value + change)
            
            # Update last updated timestamp
            monolith_data.aeternum["last_update"] = datetime.datetime.now()
            return True
    except Exception as e:
        log(f"Error updating AETERNUM data: {e}", LogLevel.ERROR, "MONOLITH")
        return False

def update_bellator_data():
    """Update security and tactical data for BELLATOR monolith"""
    try:
        with security_lock:
            # Ensure the necessary structures exist
            if "threat_alerts" not in monolith_data.bellator:
                monolith_data.bellator["threat_alerts"] = deque(maxlen=10)
            if "strategic_recommendations" not in monolith_data.bellator:
                monolith_data.bellator["strategic_recommendations"] = deque(maxlen=10)
                
            # Randomly adjust DEFCON level (low probability)
            if random.random() < 0.05:  # 5% chance
                change = random.choice([-1, 0, 0, 0, 1])  # Bias toward stability
                current_defcon = monolith_data.bellator.get("defcon_level", 3)
                monolith_data.bellator["defcon_level"] = max(1, min(5, current_defcon + change))
            
            # Generate new threat alert
            if random.random() < 0.3:  # 30% chance of new alert
                threat_categories = CONFIG["security"]["threat_categories"]
                sources = ["SIGINT", "HUMINT", "OSINT", "IMINT", "CYBER", "FINANCIAL", "GEOSPATIAL"]
                
                new_alert = ThreatAlert(
                    level=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                    source=random.choice(sources),
                    description=random.choice([
                        "Unusual activity detected in financial networks",
                        "Satellite imagery indicates troop movements",
                        "Encrypted communications spike in target region",
                        "Critical infrastructure vulnerability identified",
                        "Supply chain disruption imminent",
                        "Cyber attack signatures detected",
                        "Geopolitical instability increasing in region",
                        "Economic indicators suggest coordinated manipulation",
                        "Intelligence suggests imminent threat to assets"
                    ]),
                    timestamp=datetime.datetime.now(),
                    confidence=random.uniform(0.6, 0.95),
                    impact_score=random.uniform(1.0, 9.0),
                    recommendation=random.choice([
                        "Monitor situation for further developments",
                        "Increase security posture in affected areas",
                        "Deploy countermeasures immediately",
                        "Brief command staff on developing situation",
                        "Assess vulnerabilities in related systems",
                        "Implement contingency protocol Alpha-7",
                        "Coordinate response with allied systems"
                    ])
                )
                monolith_data.bellator["threat_alerts"].append(new_alert)
            
            # Update security indices
            monolith_data.bellator["security_index"] = max(20.0, min(95.0, 
                monolith_data.bellator.get("security_index", 72.5) + random.uniform(-2.0, 2.0)))
            
            monolith_data.bellator["geopolitical_stability"] = max(0.1, min(0.9,
                monolith_data.bellator.get("geopolitical_stability", 0.68) + random.uniform(-0.03, 0.03)))
            
            monolith_data.bellator["cyberattack_probability"] = max(0.05, min(0.85,
                monolith_data.bellator.get("cyberattack_probability", 0.45) + random.uniform(-0.05, 0.05)))
            
            # Generate strategic recommendation occasionally
            if random.random() < 0.2:  # 20% chance
                new_recommendation = {
                    "priority": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "domain": random.choice(["CYBER", "PHYSICAL", "ECONOMIC", "POLITICAL", "MILITARY"]),
                    "action": random.choice([
                        "Increase monitoring of critical systems",
                        "Deploy additional security measures",
                        "Enhance intelligence gathering operations",
                        "Prepare contingency plans for disruption",
                        "Coordinate with allied systems",
                        "Implement defense protocol Omega-3",
                        "Activate sleeper assets in affected regions"
                    ]),
                    "timeframe": random.choice(["IMMEDIATE", "24 HOURS", "72 HOURS", "1 WEEK"]),
                    "timestamp": datetime.datetime.now()
                }
                monolith_data.bellator["strategic_recommendations"].append(new_recommendation)
            
            # Update last updated timestamp
            monolith_data.bellator["last_update"] = datetime.datetime.now()
            return True
    except Exception as e:
        log(f"Error updating BELLATOR data: {e}", LogLevel.ERROR, "MONOLITH")
        return False    # Draw monolith status boxes
    box_width = (width - 6) // 3
    for i, (name, result) in enumerate(model_results.items()):
        status = result["status"]
        status_color = 2 if status == "ready" else 1
        
        # Choose a color for each monolith
        monolith_color = 4 if name == "RATIONALIS" else 5 if name == "AETERNUM" else 1
        
        # Draw box for this monolith
        box_x = 3 + i * box_width
        draw_themed_box(stdscr, mono_y + 1, box_x, 4, box_width, theme)
        
        # Monolith name and status
        safe_addstr(stdscr, mono_y + 2, box_x + 2, name, curses.A_BOLD | curses.color_pair(monolith_color))
        safe_addstr(stdscr, mono_y + 2, box_x + box_width - 15, f"[{status.upper()}]", curses.color_pair(status_color))
        
        # Additional info
        specialty = CONFIG["monoliths"][name]["specialty"].replace("_", " ").title()
        safe_addstr(stdscr, mono_y + 3, box_x + 2, f"Role: {specialty}", curses.color_pair(7))
        
        model = CONFIG["monoliths"][name]["model"]
        safe_addstr(stdscr, mono_y + 4, box_x + 2, f"Model: {model}", curses.color_pair(7))
    
    # Display active vote if any
    if active_votes:
        vote_y = mono_y + 6
        vote_header = get_theme_label("vote_status", theme)
        safe_addstr(stdscr, vote_y, 2, vote_header, curses.A_BOLD | curses.color_pair(3))
        
        # Draw vote box
        vote_box_width = width - 4
        draw_themed_box(stdscr, vote_y + 1, 2, 5, vote_box_width, theme)
        
        # Get the first vote's query (they all have the same query)
        first_vote = next(iter(active_votes.values()))
        query = first_vote.query
        query_display = query[:vote_box_width - 10] + "..." if len(query) > vote_box_width - 10 else query
        safe_addstr(stdscr, vote_y + 2, 4, f"Query: {query_display}", curses.color_pair(7))
        
        # Display votes
        vote_str = "Votes: "
        for name, vote_data in active_votes.items():
            vote_color = 2 if vote_data.vote == VoteResult.APPROVE else 1 if vote_data.vote == VoteResult.DENY else 3
            vote_str += f"{name}: {vote_data.vote.value} ({vote_data.confidence:.0%}) | "
        
        safe_addstr(stdscr, vote_y + 3, 4, vote_str[:vote_box_width - 6], curses.color_pair(7))
    
    # Display recent decisions
    if decision_history:
        decisions_y = height - 14 if active_votes else mono_y + 7
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
    
    # System info bar
    info_y = height - 3
    uptime = get_system_uptime()
    theme_name = THEME_DEFINITIONS[CONFIG["system"]["theme"]]["name"]
    
    if "bellator" in monolith_data.__dict__ and "defcon_level" in monolith_data.bellator:
        defcon = monolith_data.bellator["defcon_level"]
        defcon_color = 2 if defcon > 3 else 3 if defcon > 1 else 1
        system_info = f"Uptime: {uptime} | Theme: {theme_name} | DEFCON: {defcon}"
    else:
        system_info = f"Uptime: {uptime} | Theme: {theme_name}"
        
    safe_addstr(stdscr, info_y, 2, system_info, curses.color_pair(7))
    
    # Control instructions
    controls_y = height - 2
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | 7:History | 1-3:Monolith Views | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

def render_decision_history(stdscr):
    """Render decision history view"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    theme = CONFIG["system"]["theme"]
    header_text = get_theme_label("history", theme)
    safe_addstr(stdscr, 1, (width - len(header_text)) // 2, header_text, curses.A_BOLD | curses.color_pair(6))
    
    if not decision_history:
        safe_addstr(stdscr, height // 2, (width - 20) // 2, "No decisions recorded", curses.color_pair(3))
    else:
        # Table headers
        headers_y = 3
        safe_addstr(stdscr, headers_y, 2, "TIME", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 10, "VERDICT", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 20, "CONF", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 26, "SESSION", curses.A_BOLD | curses.color_pair(3))
        safe_addstr(stdscr, headers_y, 40, "QUERY", curses.A_BOLD | curses.color_pair(3))
        
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
            
            # Session ID (shortened)
            session = decision.get("session_id", "")[:8]
            safe_addstr(stdscr, y_pos, 26, session, curses.color_pair(7))
            
            # Query (truncated)
            query = decision["query"][:width - 45] + "..." if len(decision["query"]) > width - 45 else decision["query"]
            safe_addstr(stdscr, y_pos, 40, query, curses.color_pair(7))
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_rationalis_screen(stdscr, theme: str = None):
    """Render specialized view for RATIONALIS monolith"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    if theme is None:
        theme = CONFIG["system"]["theme"]
    
    # Header
    header_text = get_theme_label("monolith_rationalis", theme)
    safe_addstr(stdscr, 1, (width - len(header_text)) // 2, header_text, curses.A_BOLD | curses.color_pair(4))
    
    # Make sure data is updated
    if not monolith_data.rationalis.get("last_update") or \
       (datetime.datetime.now() - monolith_data.rationalis["last_update"]).total_seconds() > 60:
        update_rationalis_data()
    
    # Efficiency rating
    efficiency = monolith_data.rationalis.get("efficiency_rating", 0.85) * 100
    efficiency_color = 2 if efficiency > 90 else 3 if efficiency > 75 else 1
    rating_text = f"Logical Efficiency Rating: {efficiency:.1f}%"
    if theme == "eva":
        rating_text = f"CASPER LOGIC STABILITY: {efficiency:.1f}%"
        
    safe_addstr(stdscr, 3, (width - len(rating_text)) // 2, rating_text, 
               curses.A_BOLD | curses.color_pair(efficiency_color))
    
    # Draw main content box
    draw_themed_box(stdscr, 4, 2, height - 7, width - 4, theme)
    
    # Left panel: Recent logical analyses
    left_panel_width = (width - 8) // 2
    safe_addstr(stdscr, 5, 4, "RECENT LOGICAL ANALYSES:", curses.A_BOLD | curses.color_pair(4))
    
    analyses = list(monolith_data.rationalis.get("logical_analyses", []))
    for i, analysis in enumerate(analyses[:8]):  # Display up to 8 analyses
        if 6 + i < height - 8:
            # Format timestamp
            if hasattr(analysis, "timestamp"):
                timestamp = analysis.timestamp.strftime("%H:%M")
            else:
                timestamp = "??:??"
            
            # Display query and conclusion
            query = analysis.query if hasattr(analysis, "query") else "Unknown query"
            conclusion = analysis.conclusion if hasattr(analysis, "conclusion") else "No conclusion"
            
            # Format confidence with color
            if hasattr(analysis, "confidence"):
                confidence = analysis.confidence
                conf_color = 2 if confidence > 0.8 else 3 if confidence > 0.6 else 1
                confidence_str = f"({confidence:.0%})"
            else:
                confidence = 0.0
                conf_color = 1
                confidence_str = "(??%)"
            
            # Display the analysis summary
            query_text = query[:left_panel_width - 20] + "..." if len(query) > left_panel_width - 20 else query
            safe_addstr(stdscr, 6 + i*2, 4, f"[{timestamp}] {query_text}", curses.color_pair(7))
            
            conclusion_text = conclusion[:left_panel_width - 10] + "..." if len(conclusion) > left_panel_width - 10 else conclusion
            safe_addstr(stdscr, 7 + i*2, 6, f"→ {conclusion_text} ", curses.color_pair(7))
            safe_addstr(stdscr, 7 + i*2, 6 + len(conclusion_text) + 3, confidence_str, curses.color_pair(conf_color))
    
    # Right panel: System logs and metrics
    right_panel_x = 4 + left_panel_width + 2
    safe_addstr(stdscr, 5, right_panel_x, "SYSTEM LOGS:", curses.A_BOLD | curses.color_pair(4))
    
    logs = list(monolith_data.rationalis.get("system_logs", []))
    for i, log in enumerate(logs[:10]):  # Display up to 10 logs
        if 6 + i < height - 8:
            log_level = log.get("level", "INFO")
            log_message = log.get("message", "Unknown message")
            timestamp = log.get("timestamp", "??:??")
            
            # Choose color based on log level
            log_color = 1 if log_level == "ERROR" else 3 if log_level == "WARNING" else 7
            
            log_text = f"[{timestamp}] {log_level}: {log_message}"
            log_display = log_text[:width - right_panel_x - 6] + "..." if len(log_text) > width - right_panel_x - 6 else log_text
            safe_addstr(stdscr, 6 + i, right_panel_x, log_display, curses.color_pair(log_color))
    
    # Bottom panel: Performance metrics
    metrics_y = height - 10
    safe_addstr(stdscr, metrics_y, 4, "PERFORMANCE METRICS:", curses.A_BOLD | curses.color_pair(4))
    
    # Get average execution time
    exec_times = monolith_data.rationalis.get("execution_times", [])
    avg_exec_time = sum(exec_times) / max(1, len(exec_times))
    
    # Get average confidence
    conf_history = monolith_data.rationalis.get("confidence_history", [])
    avg_confidence = sum(conf_history) / max(1, len(conf_history))
    
    # Display metrics with a bar chart style
    safe_addstr(stdscr, metrics_y + 1, 4, f"Avg Execution Time: {avg_exec_time:.2f}s", curses.color_pair(7))
    safe_addstr(stdscr, metrics_y + 2, 4, f"Avg Confidence: {avg_confidence:.0%}", curses.color_pair(7))
    
    # Draw execution time trend
    safe_addstr(stdscr, metrics_y + 1, 30, "Trend: ", curses.color_pair(7))
    for i, time_value in enumerate(list(exec_times)[-15:]):
        if 30 + 7 + i < width - 6:
            bar_height = min(3, int(time_value * 5))
            bar_char = "▁▂▃▄▅▆▇█"[min(7, bar_height)]
            bar_color = 2 if time_value < 0.5 else 3 if time_value < 1.0 else 1
            safe_addstr(stdscr, metrics_y + 1, 30 + 7 + i, bar_char, curses.color_pair(bar_color))
    
    # Draw confidence trend
    safe_addstr(stdscr, metrics_y + 2, 30, "Trend: ", curses.color_pair(7))
    for i, conf_value in enumerate(list(conf_history)[-15:]):
        if 30 + 7 + i < width - 6:
            bar_height = min(7, int(conf_value * 8))
            bar_char = "▁▂▃▄▅▆▇█"[min(7, bar_height)]
            bar_color = 1 if conf_value < 0.6 else 3 if conf_value < 0.8 else 2
            safe_addstr(stdscr, metrics_y + 2, 30 + 7 + i, bar_char, curses.color_pair(bar_color))
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_aeternum_screen(stdscr, theme: str = None):
    """Render specialized view for AETERNUM monolith"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    if theme is None:
        theme = CONFIG["system"]["theme"]
    
    # Header
    header_text = get_theme_label("monolith_aeternum", theme)
    safe_addstr(stdscr, 1, (width - len(header_text)) // 2, header_text, curses.A_BOLD | curses.color_pair(5))
    
    # Make sure data is updated
    if not monolith_data.aeternum.get("last_update") or \
       (datetime.datetime.now() - monolith_data.aeternum["last_update"]).total_seconds() > 60:
        update_aeternum_data()
    
    # Market sentiment and VIX display
    sentiment = monolith_data.aeternum.get("market_sentiment", 0.65) * 100
    vix = monolith_data.aeternum.get("volatility_index", 18.5)
    
    sentiment_color = 2 if sentiment > 70 else 3 if sentiment > 40 else 1
    vix_color = 2 if vix < 15 else 3 if vix < 25 else 1
    
    sentiment_text = f"Market Sentiment: {sentiment:.1f}%"
    vix_text = f"Volatility Index: {vix:.1f}"
    
    safe_addstr(stdscr, 3, width // 4 - len(sentiment_text) // 2, sentiment_text, 
               curses.A_BOLD | curses.color_pair(sentiment_color))
    
    safe_addstr(stdscr, 3, 3*width // 4 - len(vix_text) // 2, vix_text, 
               curses.A_BOLD | curses.color_pair(vix_color))
    
    # Draw main content box
    draw_themed_box(stdscr, 4, 2, height - 7, width - 4, theme)
    
    # Market indices section
    safe_addstr(stdscr, 5, 4, "MARKET INDICES:", curses.A_BOLD | curses.color_pair(5))
    
    indices = monolith_data.aeternum.get("market_indices", {})
    y_pos = 6
    col1_x, col2_x = 4, width // 2 + 4
    idx = 0
    for name, data in indices.items():
        if y_pos + idx // 2 < height - 5:
            x_pos = col1_x if idx % 2 == 0 else col2_x
            trend_color = 2 if data["trend"] == "up" else 1
            text = f"{name}: {data['value']:,.2f} ({data['change']:+.2f}%)"
            safe_addstr(stdscr, y_pos + idx // 2, x_pos, text, curses.color_pair(trend_color))
            idx += 1
    
    y_pos += (idx + 1) // 2 + 1
    
    # Portfolio performance
    safe_addstr(stdscr, y_pos, 4, "PORTFOLIO PERFORMANCE:", curses.A_BOLD | curses.color_pair(5))
    y_pos += 1
    
    portfolio = monolith_data.aeternum.get("portfolio_performance", {})
    if portfolio:
        # Time-based performance
        perf_y = y_pos
        for period, change in [
            ("Daily", portfolio.get("daily_change", 0.0)), 
            ("Weekly", portfolio.get("weekly_change", 0.0)), 
            ("Monthly", portfolio.get("monthly_change", 0.0)), 
            ("Yearly", portfolio.get("yearly_change", 0.0))
        ]:
            if perf_y < height - 10:
                change_color = 2 if change > 0 else 1
                perf_text = f"{period}: {change:+.2f}%"
                safe_addstr(stdscr, perf_y, col1_x, perf_text, curses.color_pair(change_color))
                perf_y += 1
        
        # Top and worst performers
        if y_pos < height - 10 and "top_performers" in portfolio and "worst_performers" in portfolio:
            top_performers = ", ".join(portfolio["top_performers"])
            worst_performers = ", ".join(portfolio["worst_performers"])
            
            top_text = f"Top: {top_performers}"
            worst_text = f"Worst: {worst_performers}"
            
            safe_addstr(stdscr, y_pos, col2_x, top_text, curses.color_pair(2))
            safe_addstr(stdscr, y_pos+1, col2_x, worst_text, curses.color_pair(1))
    
    y_pos += 4
    
    # Economic indicators
    safe_addstr(stdscr, y_pos, 4, "ECONOMIC INDICATORS:", curses.A_BOLD | curses.color_pair(5))
    y_pos += 1
    
    indicators = monolith_data.aeternum.get("economic_indicators", {})
    idx = 0
    for name, value in indicators.items():
        if y_pos + idx//3 < height - 5:
            column = idx % 3
            x_pos = col1_x + (column * (width // 3))
            
            name_formatted = name.replace("_", " ").title()
            indicator_text = f"{name_formatted}: {value}"
            safe_addstr(stdscr, y_pos + idx//3, x_pos, indicator_text, curses.color_pair(7))
            idx += 1
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_bellator_screen(stdscr, theme: str = None):
    """Render specialized view for BELLATOR monolith"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    if theme is None:
        theme = CONFIG["system"]["theme"]
    
    # Header
    header_text = get_theme_label("monolith_bellator", theme)
    safe_addstr(stdscr, 1, (width - len(header_text)) // 2, header_text, curses.A_BOLD | curses.color_pair(1))
    
    # Make sure data is updated
    if not monolith_data.bellator.get("last_update") or \
       (datetime.datetime.now() - monolith_data.bellator["last_update"]).total_seconds() > 60:
        update_bellator_data()
    
    # DEFCON level display
    level = monolith_data.bellator.get("defcon_level", 3)
    defcon_color = 2 if level > 3 else 3 if level > 1 else 1
    
    rating = f"MELCHIOR CONFLICT READINESS: {level}/5" if theme == "eva" else f"DEFCON LEVEL: {level}"
    safe_addstr(stdscr, 3, width // 2 - len(rating) // 2, rating, curses.A_BOLD | curses.color_pair(defcon_color))
    
    # Draw main content box
    draw_themed_box(stdscr, 4, 2, height - 7, width - 4, theme)
    
    # Threat alerts section
    y_pos = 5
    section_header = "THREAT ALERTS"
    if theme == "eva":
        section_header = "PATTERN RECOGNITION - NODE MELCHIOR-1"
    
    safe_addstr(stdscr, y_pos, 4, section_header + ":", curses.A_BOLD | curses.color_pair(1))
    y_pos += 1
    
    alerts = list(monolith_data.bellator.get("threat_alerts", []))
    for idx, alert in enumerate(alerts[:6]):  # Display up to 6 alerts
        if y_pos + idx < height - 10:
            # Format alert data
            if hasattr(alert, "level"):
                level = alert.level
                level_color = 1 if level == "HIGH" or level == "CRITICAL" else 3 if level == "MEDIUM" else 2
            else:
                level = "UNKNOWN"
                level_color = 3
            
            description = alert.description if hasattr(alert, "description") else "Unknown threat"
            source = alert.source if hasattr(alert, "source") else "Unknown"
            
            # Format timestamp
            if hasattr(alert, "timestamp"):
                timestamp = alert.timestamp.strftime("%H:%M")
            else:
                timestamp = "??:??"
            
            # Display the alert
            safe_addstr(stdscr, y_pos + idx, 4, f"[{timestamp}] [{level}]", curses.color_pair(level_color))
            alert_text = f"{description} (Source: {source})"
            alert_display = alert_text[:width - 25] + "..." if len(alert_text) > width - 25 else alert_text
            safe_addstr(stdscr, y_pos + idx, 20, alert_display, curses.color_pair(7))
    
    # Strategic recommendations section
    recommendations_y = height - 14
    safe_addstr(stdscr, recommendations_y, 4, "STRATEGIC RECOMMENDATIONS:", curses.A_BOLD | curses.color_pair(1))
    
    recommendations = list(monolith_data.bellator.get("strategic_recommendations", []))
    for i, rec in enumerate(recommendations[:3]):  # Display up to 3 recommendations
        if recommendations_y + 1 + i < height - 9:
            # Format recommendation
            priority = rec.get("priority", "MEDIUM")
            priority_color = 1 if priority == "HIGH" else 3 if priority == "MEDIUM" else 2
            
            domain = rec.get("domain", "GENERAL")
            action = rec.get("action", "No specific action")
            timeframe = rec.get("timeframe", "UNDEFINED")
            
            # Display recommendation
            safe_addstr(stdscr, recommendations_y + 1 + i, 4, f"[{priority}] {domain}:", curses.color_pair(priority_color))
            
            rec_text = f"{action} ({timeframe})"
            rec_display = rec_text[:width - 25] + "..." if len(rec_text) > width - 25 else rec_text
            safe_addstr(stdscr, recommendations_y + 1 + i, 20, rec_display, curses.color_pair(7))
    
    # Risk assessment metrics
    metrics_y = height - 9
    safe_addstr(stdscr, metrics_y, 4, "TACTICAL METRICS:", curses.A_BOLD | curses.color_pair(1))
    
    # Get metrics
    geo_stability = monolith_data.bellator.get("geopolitical_stability", 0.68) * 100
    cyber_probability = monolith_data.bellator.get("cyberattack_probability", 0.45) * 100
    
    # Draw metrics with gauges
    safe_addstr(stdscr, metrics_y + 1, 4, f"Geopolitical Stability: {geo_stability:.1f}%", curses.color_pair(7))
    safe_addstr(stdscr, metrics_y + 2, 4, f"Cyberattack Probability: {cyber_probability:.1f}%", curses.color_pair(7))
    
    # Draw stability gauge
    gauge_width = 20
    safe_addstr(stdscr, metrics_y + 1, 35, "[" + "=" * gauge_width + "]", curses.color_pair(7))
    filled = int((geo_stability / 100) * gauge_width)
    stability_color = 2 if geo_stability > 70 else 3 if geo_stability > 40 else 1
    for i in range(filled):
        safe_addstr(stdscr, metrics_y + 1, 36 + i, "=", curses.color_pair(stability_color))
    
    # Draw cyber risk gauge
    safe_addstr(stdscr, metrics_y + 2, 35, "[" + "=" * gauge_width + "]", curses.color_pair(7))
    filled = int((cyber_probability / 100) * gauge_width)
    cyber_color = 1 if cyber_probability > 70 else 3 if cyber_probability > 40 else 2
    for i in range(filled):
        safe_addstr(stdscr, metrics_y + 2, 36 + i, "=", curses.color_pair(cyber_color))
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_help_screen(stdscr):
    """Render the help screen"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS SYSTEM - HELP & COMMANDS"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Create content area
    draw_themed_box(stdscr, 3, 2, height - 5, width - 4, CONFIG["system"]["theme"])
    
    # Display help content
    help_text = [
        ("KEYBOARD SHORTCUTS:", curses.A_BOLD),
        ("  Q - Quit the application", 0),
        ("  M - Return to main view", 0),
        ("  S - Cycle through themes", 0),
        ("  R - Refresh display", 0),
        ("  V - Trigger vote demo", 0),
        ("  C - Enter console mode", 0),
        ("  1 - View RATIONALIS monitor", 0),
        ("  2 - View AETERNUM monitor", 0),
        ("  3 - View BELLATOR monitor", 0),
        ("  7 - View decision history", 0),
        ("  9 - View diagnostics", 0),
        ("  H - Toggle this help screen", 0),
        ("", 0),
        ("SYSTEM OVERVIEW:", curses.A_BOLD),
        ("  The CONSENSUS SYSTEM utilizes three specialized AI monoliths", 0),
        ("  working together to provide decision recommendations:", 0),
        ("", 0),
        ("  RATIONALIS - Logic engine focused on structured reasoning", 0),
        ("  AETERNUM - Temporal/financial analyst for pattern recognition", 0),
        ("  BELLATOR - Tactical strategist for security assessment", 0),
        ("", 0),
        ("  Decisions require a majority consensus (2 out of 3) with each", 0),
        ("  monolith voting either APPROVE, DENY, or ABSTAIN.", 0),
        ("", 0),
        ("CONSOLE COMMANDS:", curses.A_BOLD),
        ("  consensus - Generate votes from all monoliths", 0),
        ("  status - Display model status information", 0),
        ("  vote <monolith> <query> - Generate vote from specific monolith", 0),
        ("  export json/csv - Export decision history", 0),
        ("  query <text> - Set active query", 0),
        ("  help - Show this help screen", 0)
    ]
    
    # Render help text
    y_pos = 5
    for line, attr in help_text:
        if y_pos < height - 3:
            safe_addstr(stdscr, y_pos, 5, line, attr)
            y_pos += 1
    
    # Footer
    footer = "Press any key to return to previous screen"
    safe_addstr(stdscr, height - 3, (width - len(footer)) // 2, footer, curses.A_BOLD)

def render_config_screen(stdscr):
    """Render the configuration screen"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header
    header = "CONSENSUS SYSTEM - CONFIGURATION"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # Create content area
    draw_themed_box(stdscr, 3, 2, height - 5, width - 4, CONFIG["system"]["theme"])
    
    # Display configuration sections
    y_pos = 5
    sections = [
        ("SYSTEM CONFIGURATION", "system", ["theme", "system_mode", "debug_mode"]),
        ("MONOLITH SETTINGS", "monoliths", []),  # Special handling for monoliths
        ("LLM PROVIDER", "llm", ["provider", "api_timeout", "vote_timeout", "enable_parallel_processing"]),
        ("TTS SETTINGS", "tts", ["enabled", "engine", "voice_rate", "announce_decisions", "emotional_modulation"]),
        ("HEALTH MONITORING", "health", ["enabled", "check_interval"]),
        ("EXPORT OPTIONS", "export", ["auto_backup", "formats"])
    ]
    
    for section_title, section_key, keys in sections:
        if y_pos + 1 >= height - 4:
            break
            
        safe_addstr(stdscr, y_pos, 5, section_title + ":", curses.A_BOLD)
        y_pos += 1
        
        if section_key == "monoliths":
            # Special handling for monoliths section
            for monolith_name, monolith_config in CONFIG["monoliths"].items():
                if y_pos < height - 4:
                    monolith_str = f"  {monolith_name}: {monolith_config['model']} (Temp: {monolith_config['temperature']}, Tokens: {monolith_config['max_tokens']})"
                    safe_addstr(stdscr, y_pos, 5, monolith_str)
                    y_pos += 1
        else:
            # Regular section
            for key in keys:
                if y_pos < height - 4 and key in CONFIG[section_key]:
                    value = CONFIG[section_key][key]
                    value_str = str(value)
                    if isinstance(value, list):
                        value_str = ", ".join(value)
                    elif isinstance(value, dict):
                        value_str = f"<{len(value)} items>"
                        
                    config_str = f"  {key}: {value_str}"
                    safe_addstr(stdscr, y_pos, 5, config_str)
                    y_pos += 1
        
        y_pos += 1  # Add space between sections
    
    # Footer
    footer = "Press any key to return to main view"
    safe_addstr(stdscr, height - 3, (width - len(footer)) // 2, footer, curses.A_BOLD)# ================================================================================
# MODULE 9: User Interface System
# ================================================================================

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

def get_theme_label(key: str, theme: str = None) -> str:
    """Get themed label for UI elements"""
    if theme is None:
        theme = CONFIG["system"]["theme"]
    
    theme_data = THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["military"])
    return theme_data["labels"].get(key, key.replace("_", " ").title())

def render_main_screen(stdscr, theme: str = None):
    """Render the main CONSENSUS interface"""
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Header with enhanced styling
    header = f"CONSENSUS SYSTEM v{VERSION} - AI TRIBUNAL COMMAND CENTER"
    safe_addstr(stdscr, 1, (width - len(header)) // 2, header, curses.A_BOLD | curses.color_pair(6))
    
    # System status overview
    status_y = 3
    status_header = get_theme_label("system_status", theme)
    safe_addstr(stdscr, status_y, 2, status_header, curses.A_BOLD | curses.color_pair(3))
    
    mode = CONFIG["system"]["system_mode"]
    mode_color = 2 if mode == SystemMode.READY.value else 3
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
    
    # Draw monolith status boxes
    box_width = (width - 6) // 3
    for i, (name, result) in enumerate(model_results.items()):
        status = result["status"]
        status_color = #!/usr/bin/env python3
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

# Optional dependencies
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
MEMORY_PATH = ARBITER_DIR / "memory.json"
PROPOSAL_FILE = ARBITER_DIR / "proposal.json"

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

CONSENSUS_LOGO = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ ▛ CONSENSUS SYSTEM ▜      ⟦ AI TRIBUNAL ⟧                       v{VERSION}      ║
║                         Build: {BUILD_HASH}                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# Theme configuration (including EVA)
THEMES = [
    "Military HQ",
    "TARS Interface",
    "Evangelion MAGI",
    "Imperial Gothic",
    "Super Earth Command"
]

# MAGI Mapping (EVA): Monolith → MAGI Core
MAGI_NAMES = {
    "RATIONALIS": "CASPER-3",
    "AETERNUM": "BALTHASAR-2",
    "BELLATOR": "MELCHIOR-1"
}

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

# API Configuration Flags
API_FLAGS = {
    "YahooFinance": True,
    "AlphaVantage": True,
    "CoinGecko": True,
    "NewsAPI": True,
    "GDELT": True,
    "IBKR": IB_AVAILABLE,
    "TTS": TTS_AVAILABLE,
    "Tortoise": False  # Advanced TTS - optional
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

# Query templates
QUERY_TEMPLATES = {
    "finance": "Analyze market conditions for {symbol} and recommend investment action.",
    "security": "Evaluate security implications of {action} regarding {target}.",
    "logical": "Determine optimal approach for {goal} given constraints {constraints}.",
    "general": "Should we proceed with {action}?",
    "critical": "Authorize emergency protocol {protocol_number} for {situation}."
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
decision_history = deque(maxlen=CONFIG["system"]["max_decisions"])
command_history = deque(maxlen=CONFIG["system"]["command_history_size"])
log_entries = deque(maxlen=CONFIG["max_log_entries"])
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

def update_simulated_monolith_data():
    """Update simulated data for monolith specialized views"""
    # Update RATIONALIS data
    update_rationalis_data()
    
    # Update AETERNUM data
    update_aeternum_data()
    
    # Update BELLATOR data
    update_bellator_data()
    
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
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {uptime_seconds % 60}s"

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
                
                # Collect reasoning snippets
                reasoning_snippet = vote_data.reasoning[:100] + "..." if len(vote_data.reasoning) > 100 else vote_data.reasoning
                reasoning_parts.append(f"{monolith}: {vote_data.vote.value} - {reasoning_snippet}")
        
        # Determine consensus
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
        
        # Overall statistics
        total_decisions = len(decisions)
        verdict_counts = defaultdict(int)
        monolith_agreement = defaultdict(list)
        
        for decision in decisions:
            verdict_counts[decision["verdict"]] += 1
            
            # Track monolith agreement
            votes = {}
            if "individual_votes" in decision and isinstance(decision["individual_votes"], dict):
                for monolith, vote_data in decision["individual_votes"].items():
                    if isinstance(vote_data, dict):
                        vote_val = vote_data.get("vote", "ERROR")
                    else:
                        vote_val = "ERROR"
                    votes[monolith] = vote_val
            
            if len(votes) >= 2:
                # Check pairwise agreement
                for m1, v1 in votes.items():
                    for m2, v2 in votes.items():
                        if m1 < m2:  # Ensure we don't double count
                            monolith_agreement[f"{m1}-{m2}"].append(1 if v1 == v2 else 0)
        
        # Calculate metrics
        approval_rate = verdict_counts.get("APPROVE", 0) / total_decisions
        denial_rate = verdict_counts.get("DENY", 0) / total_decisions
        deadlock_rate = verdict_counts.get("ERROR", 0) / total_decisions
        
        # Average confidence
        avg_confidence = sum(d.get("confidence", 0.0) for d in decisions) / total_decisions
        
        # Monolith agreement rates
        agreement_rates = {}
        for pair, agreements in monolith_agreement.items():
            if agreements:
                agreement_rates[pair] = sum(agreements) / len(agreements)
        
        # Calculate decision trend
        trend = ConsensusEngine._calculate_trend(decisions[-10:]) if len(decisions) >= 10 else "insufficient_data"
        
        return {
            "total_decisions": total_decisions,
            "approval_rate": approval_rate,
            "denial_rate": denial_rate,
            "deadlock_rate": deadlock_rate,
            "average_confidence": avg_confidence,
            "agreement_rates": agreement_rates,
            "verdict_distribution": dict(verdict_counts),
            "recent_trend": trend
        }
    
    @staticmethod
    def _calculate_trend(recent_decisions: List[Dict[str, Any]]) -> str:
        """Calculate recent decision trend"""
        if len(recent_decisions) < 5:
            return "insufficient_data"
        
        approve_count = sum(1 for d in recent_decisions if d.get("verdict") == "APPROVE")
        deny_count = sum(1 for d in recent_decisions if d.get("verdict") == "DENY")
        
        approve_rate = approve_count / len(recent_decisions)
        
        if approve_rate > 0.7:
            return "approval_trending"
        elif approve_rate < 0.3:
            return "denial_trending"
        else:
            return "balanced"
    
    @staticmethod
    def perform_bias_analysis(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze potential bias in decision patterns"""
        if len(decisions) < 10:
            return {"status": "insufficient_data", "message": "Need at least 10 decisions for bias analysis"}
        
        # Check for monolith dominance (one monolith consistently overriding others)
        monolith_influence = defaultdict(int)
        monolith_agreement_with_outcome = defaultdict(list)
        
        for decision in decisions:
            verdict = decision.get("verdict", "ERROR")
            if "individual_votes" in decision and isinstance(decision["individual_votes"], dict):
                for monolith, vote_data in decision["individual_votes"].items():
                    if isinstance(vote_data, dict):
                        vote_val = vote_data.get("vote", "ERROR")
                        monolith_agreement_with_outcome[monolith].append(1 if vote_val == verdict else 0)
        
        # Calculate agreement rates
        monolith_influence_scores = {}
        for monolith, agreements in monolith_agreement_with_outcome.items():
            if agreements:
                monolith_influence_scores[monolith] = sum(agreements) / len(agreements)
        
        # Check for query type bias
        query_keywords = ["security", "tactical", "financial", "market", "logical", "emergency", "routine"]
        keyword_outcomes = defaultdict(lambda: defaultdict(int))
        
        for decision in decisions:
            query = decision.get("query", "").lower()
            verdict = decision.get("verdict", "ERROR")
            
            for keyword in query_keywords:
                if keyword in query:
                    keyword_outcomes[keyword][verdict] += 1
        
        # Calculate keyword bias
        keyword_bias = {}
        for keyword, outcomes in keyword_outcomes.items():
            total = sum(outcomes.values())
            if total >= 3:  # Only consider keywords with enough samples
                approve_rate = outcomes.get("APPROVE", 0) / total
                keyword_bias[keyword] = {
                    "approve_rate": approve_rate,
                    "total_occurrences": total,
                    "bias_level": "high" if approve_rate > 0.8 or approve_rate < 0.2 else
                                  "medium" if approve_rate > 0.7 or approve_rate < 0.3 else
                                  "low"
                }
        
        return {
            "status": "success",
            "monolith_influence": monolith_influence_scores,
            "keyword_bias": keyword_bias,
            "analysis_timestamp": datetime.datetime.now().isoformat()
        }
    
    @staticmethod
    def advanced_confidence_analysis(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform advanced analysis on decision confidence patterns"""
        if len(decisions) < 5:
            return {"status": "insufficient_data"}
            
        # Extract confidence values
        confidences = [d.get("confidence", 0.0) for d in decisions]
        
        # Calculate statistics
        if confidences:
            mean_confidence = sum(confidences) / len(confidences)
            median_confidence = sorted(confidences)[len(confidences) // 2]
            min_confidence = min(confidences)
            max_confidence = max(confidences)
            
            # Calculate standard deviation if we have statistics module
            try:
                stdev_confidence = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
            except:
                stdev_confidence = (max_confidence - min_confidence) / 4  # Rough approximation
            
            # Analyze confidence trend
            recent_confidences = [d.get("confidence", 0.0) for d in decisions[-5:]]
            recent_mean = sum(recent_confidences) / len(recent_confidences)
            
            if recent_mean > mean_confidence + stdev_confidence:
                trend = "increasing"
            elif recent_mean < mean_confidence - stdev_confidence:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return {
                "status": "success",
                "mean_confidence": mean_confidence,
                "median_confidence": median_confidence,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "confidence_stdev": stdev_confidence,
                "confidence_trend": trend,
                "variance": stdev_confidence ** 2,
                "sample_size": len(confidences)
            }
        else:
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
            elif consensus == VoteResult.CONDITIONAL:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("CONDITIONAL APPROVAL", NotificationLevel.INFO)
            elif consensus == VoteResult.ABSTAIN:
                CONFIG["system"]["system_mode"] = SystemMode.CONSENSUS.value
                add_notification("TRIBUNAL ABSTAINS", NotificationLevel.INFO)
            else:
                CONFIG["system"]["system_mode"] = SystemMode.DEADLOCK.value
                add_notification("DEADLOCK - Manual intervention required", NotificationLevel.ERROR)
            
            # Record decision
            self._record_decision(query, consensus, votes, confidence, reasoning, session_id)
            
            # Announce verdict with TTS
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
            if not TTS_AVAILABLE:
                log("TTS not available - install pyttsx3 for TTS functionality", LogLevel.WARNING, "TTS")
                return
                
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
            
            # Set speech parameters
            engine.setProperty('rate', CONFIG["tts"]["voice_rate"])
            engine.setProperty('volume', CONFIG["tts"]["voice_volume"])
            
            # Create announcement
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
            
            # Speak the announcement with GLaDOS-like tone using pitch and rate modifications
            if CONFIG["tts"]["emotional_modulation"]:
                # First announcement in normal voice
                engine.say(announcement)
                
                # Second announcement with GLaDOS-like effect
                engine.setProperty('rate', int(CONFIG["tts"]["voice_rate"] * 0.9))  # Slightly slower
                
                glados_addendum = random.choice([
                    "This decision was made for your own good.",
                    "I hope you appreciate my efficiency.",
                    "Decision recorded in the name of science.",
                    "Are you satisfied with this result?",
                    "Was that the outcome you hoped for?",
                    "Testing complete. Moving to next objective.",
                    "I'll add this to your file."
                ])
                
                engine.say(glados_addendum)
            else:
                # Just the basic announcement
                engine.say(announcement)
            
            engine.runAndWait()
            engine.stop()
            
            log(f"TTS announcement completed: {consensus.value}", LogLevel.INFO, "TTS")
            
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
                decision_dict = decision.copy() if isinstance(decision, dict) else {}
                
                # Convert timestamp
                if isinstance(decision_dict.get("timestamp"), datetime.datetime):
                    decision_dict["timestamp"] = decision_dict["timestamp"].isoformat()
                
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
            
            # Ensure the directory exists
            DECISION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            
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
            
            # Limit to max_decisions
            max_decisions = CONFIG["system"].get("max_decisions", 100)
            
            # Convert timestamps if needed
            for stored_decision in decisions_data[-max_decisions:]:
                if isinstance(stored_decision.get("timestamp"), str):
                    try:
                        stored_decision["timestamp"] = datetime.datetime.fromisoformat(stored_decision["timestamp"])
                    except:
                        stored_decision["timestamp"] = datetime.datetime.now()
                
                decision_history.append(stored_decision)
            
            log(f"Loaded {len(decision_history)} decisions from history", LogLevel.INFO, "DECISION")
        
    except Exception as e:
        log(f"Failed to load decision history: {e}", LogLevel.ERROR, "DECISION")