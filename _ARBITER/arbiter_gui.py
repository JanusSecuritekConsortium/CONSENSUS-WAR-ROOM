import curses
import time
import json
import os
import datetime
import threading
from pathlib import Path
import random

# Global variables for command processing
current_query = "No active query"
system_mode = "NORMAL"

# Styling options
STYLE = {
    "theme": "military",  # Options: "military", "wh40k", "tars"
    "show_status": True,
    "interactive": True,
    "animated_text": True  # Always enabled
}

# Configuration for monoliths
MONOLITHS = {
    "Rationalis": {
        "symbol": "R",
        "color_pair": 1,  # Will be set to cyan
        "log_path": "../Rationalis/rationalis.log",
        "vote_path": "../_ARBITER/tmp_votes/rationalis_vote.json",
        "analysis_prefix": {
            "military": "LOGICAL ANALYSIS:",
            "wh40k": "++ LOGICAL COGITATION ++",
            "tars": "LOGIC.SYS:"
        },
        "status": "offline"
    },
    "Aeternum": {
        "symbol": "A",
        "color_pair": 2,  # Will be set to blue
        "log_path": "../Aeternum/aeternum.log",
        "vote_path": "../_ARBITER/tmp_votes/aeternum_vote.json",
        "analysis_prefix": {
            "military": "FINANCIAL ASSESSMENT:",
            "wh40k": "++ FISCAL DIVINATION ++",
            "tars": "FINANCE.SYS:"
        },
        "status": "offline"
    },
    "Bellator": {
        "symbol": "B",
        "color_pair": 3,  # Will be set to magenta
        "log_path": "../Bellator/bellator.log",
        "vote_path": "../_ARBITER/tmp_votes/bellator_vote.json",
        "analysis_prefix": {
            "military": "SECURITY ANALYSIS:",
            "wh40k": "++ TACTICAL ASSESSMENT ++",
            "tars": "SECURITY.SYS:"
        },
        "status": "offline"
    }
}

# System modes
SYSTEM_MODES = {
    "NORMAL": {
        "symbol": {"military": "#", "wh40k": "I", "tars": "■"}, 
        "color_pair": 7
    },
    "CRITICAL": {
        "symbol": {"military": "!", "wh40k": "X", "tars": "▲"}, 
        "color_pair": 5
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

# Command history
command_history = []
command_history_index = 0
command_output = ""  # Store feedback from command execution

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
    }
}

def main(stdscr):
    global current_query, system_mode, command_output
    
    # Setup
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.use_default_colors()
    
    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_CYAN, -1)    # Rationalis
    curses.init_pair(2, curses.COLOR_BLUE, -1)    # Aeternum
    curses.init_pair(3, curses.COLOR_MAGENTA, -1) # Bellator
    curses.init_pair(4, curses.COLOR_GREEN, -1)   # APPROVE/Online
    curses.init_pair(5, curses.COLOR_YELLOW, -1)  # WARNING/CRITICAL/Processing
    curses.init_pair(6, curses.COLOR_RED, -1)     # DENY/Offline
    curses.init_pair(7, curses.COLOR_WHITE, -1)   # Normal text
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)    # Alert background
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Success background
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Command input
    
    stdscr.timeout(500)  # Refresh rate in ms
    
    # Local UI state
    last_update = datetime.datetime.now()
    input_mode = False
    command_buffer = ""
    animated_text_position = 0
    
    # Always ensure text animation is enabled
    STYLE["animated_text"] = True
    
    # Start background thread to update statuses
    if STYLE["show_status"]:
        threading.Thread(target=update_statuses, daemon=True).start()
    
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
                header = f" ADEPTUS CONSENSII {mode_info['symbol'][theme]} COMMAND THRONE "
                mode_display = f"IMPERIUM STATUS: {system_mode}"
            elif theme == "tars":
                header = f" CONSENSUS.CORE.{system_mode} {mode_info['symbol'][theme]} "
                mode_display = f"SYS.MODE={system_mode}"
                
            if system_mode == "CRITICAL":
                if theme == "military":
                    header = "/// CRITICAL ALERT ACTIVE ///"
                elif theme == "wh40k":
                    header = "!!! EXTERMINATUS PROTOCOL ACTIVE !!!"
                elif theme == "tars":
                    header = "*** CRITICAL.OVERRIDE.ACTIVE ***"
            
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
                
                # Draw monolith box
                box_width = min(w - 4, 76)
                
                # Style-specific box drawing
                if theme == "military":
                    # Top border
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
                    # Top border
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
                    header = f" [{info['symbol']}] {name.upper()} ADEPTUS "
                elif theme == "tars":
                    header = f" {name.upper()}.NODE "
                    
                safe_addstr(stdscr, panel_y+1, 4, header, 
                         curses.A_BOLD | curses.color_pair(info['color_pair']))
                
                # Display status indicators if enabled
                if STYLE["show_status"]:
                    status = info["status"]
                    status_text, status_color = STATUS_INDICATORS[status]
                    
                    if theme == "military":
                        status_display = f"STATUS: {status_text}"
                    elif theme == "wh40k":
                        status_display = f"MACHINE SPIRIT: {status_text}"
                    elif theme == "tars":
                        status_display = f"STATUS={status_text}"
                        
                    # Ensure status text fits within available space
                    max_status_pos = min(w - len(status_display) - 4, box_width - 30)
                    safe_addstr(stdscr, panel_y+1, max_status_pos, 
                             status_display, curses.color_pair(status_color))
                
                # Display vote with style-specific formatting
                # Calculate space to ensure it fits
                if theme == "military":
                    vote_display = f"[ {vote_str} ]"
                elif theme == "wh40k":
                    vote_display = f"<<< {vote_str} >>>"
                elif theme == "tars":
                    vote_display = f"[{vote_str}]"
                
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
                
                # Draw confidence meter if available - style based on theme
                if 'confidence' in vote_info and panel_y+7 < h:
                    conf_val = vote_info['confidence']
                    
                    if theme == "military":
                        conf_str = f"CONFIDENCE: {conf_val:.1f}%"
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'#' * filled}{' ' * (meter_len - filled)}]"
                    elif theme == "wh40k":
                        conf_str = f"CERTAINTY: {conf_val:.1f}%"
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'+' * filled}{'-' * (meter_len - filled)}]"
                    elif theme == "tars":
                        conf_str = f"CONF={conf_val:.1f}%"
                        meter_len = 20
                        filled = int((conf_val/100) * meter_len)
                        meter = f"[{'=' * filled}{' ' * (meter_len - filled)}]"
                    
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
                
                safe_addstr(stdscr, consensus_y, 2, consensus_box_top, curses.A_BOLD)
                
                if consensus:
                    # Style-specific verdict text
                    if theme == "military":
                        verdict_str = f"CONSENSUS VERDICT: {consensus}"
                    elif theme == "wh40k":
                        verdict_str = f"IMPERIAL DECREE: {consensus}"
                    elif theme == "tars":
                        verdict_str = f"CONSENSUS.VERDICT={consensus}"
                        
                    verdict_color = VOTE_COLORS[consensus]
                    
                    # Center the verdict text
                    safe_addstr(stdscr, consensus_y+1, w//2 - len(verdict_str)//2, verdict_str, 
                             curses.color_pair(verdict_color) | curses.A_BOLD)
                    
                    # Style-specific warning/confirmation for critical mode
                    if system_mode == "CRITICAL" and consensus == "APPROVE" and consensus_y+2 < h:
                        if theme == "military":
                            warn_str = "!!! WARNING: CRITICAL ACTION REQUIRES VERIFICATION !!!"
                        elif theme == "wh40k":
                            warn_str = "!!! BY THE EMPEROR'S WILL: VERIFICATION REQUIRED !!!"
                        elif theme == "tars":
                            warn_str = "!!! CRITICAL.OVERRIDE.VERIFICATION.REQUIRED !!!"
                            
                        safe_addstr(stdscr, consensus_y+2, w//2 - len(warn_str)//2, warn_str, 
                                 curses.color_pair(8) | curses.A_BOLD)
                    elif consensus == "APPROVE" and consensus_y+2 < h:
                        if theme == "military":
                            confirm_str = ">>> ACTION AUTHORIZED <<<"
                        elif theme == "wh40k":
                            confirm_str = ">>> THE EMPEROR APPROVES <<<"
                        elif theme == "tars":
                            confirm_str = ">>> EXECUTION.AUTHORIZED <<<"
                            
                        safe_addstr(stdscr, consensus_y+2, w//2 - len(confirm_str)//2, confirm_str, 
                                 curses.color_pair(9) | curses.A_BOLD)
                else:
                    # Style-specific waiting text
                    if theme == "military":
                        wait_str = "AWAITING CONSENSUS..."
                    elif theme == "wh40k":
                        wait_str = "THE COUNCIL DELIBERATES..."
                    elif theme == "tars":
                        wait_str = "CONSENSUS.PENDING..."
                        
                    safe_addstr(stdscr, consensus_y+1, w//2 - len(wait_str)//2, wait_str, 
                             curses.A_BOLD)
                
                if consensus_y+3 < h:
                    safe_addstr(stdscr, consensus_y+3, 2, consensus_box_bottom, curses.A_BOLD)
            
            # Command input area and history display
            cmd_y = h - 6
            if cmd_y > 0 and STYLE["interactive"]:
                # Display command history and last command output
                history_width = w - 4
                
                if theme == "military":
                    cmd_box_top = f"+{'=' * (history_width)}+"
                    cmd_box_bottom = f"+{'=' * (history_width)}+"
                elif theme == "wh40k":
                    cmd_box_top = f"<{'=' * (history_width)}>"
                    cmd_box_bottom = f"<{'=' * (history_width)}>"
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
                        if len(command_output) > history_width - 5:
                            command_output_display = command_output[:history_width-8] + "..."
                        else:
                            command_output_display = command_output
                        safe_addstr(stdscr, output_y, 4, command_output_display, curses.color_pair(5))
                
                safe_addstr(stdscr, cmd_y + 3, 2, cmd_box_bottom)
            
            # Command help/input prompt at bottom of screen
            help_y = h - 2
            
            if input_mode:
                # Draw command input prompt
                if theme == "military":
                    prompt = "ENTER COMMAND: "
                elif theme == "wh40k":
                    prompt = "ISSUE DECREE: "
                elif theme == "tars":
                    prompt = "CMD> "
                
                safe_addstr(stdscr, help_y, 2, prompt, curses.A_BOLD)
                
                # Display command buffer with cursor
                safe_addstr(stdscr, help_y, 2 + len(prompt), command_buffer)
                curses.curs_set(1)  # Show cursor
                stdscr.move(help_y, 2 + len(prompt) + len(command_buffer))
            else:
                # Draw command help
                if theme == "military":
                    help_text = "[ Q:QUIT | M:MODE | R:REFRESH | S:STYLE | I:INPUT ]"
                elif theme == "wh40k":
                    help_text = "[ Q:RETREAT | M:MODE | R:REFRESH | S:STYLE | I:COMMAND ]"
                elif theme == "tars":
                    help_text = "[ Q:EXIT | M:MODE | R:REFRESH | S:STYLE | I:CMD ]"
                
                # Draw help in a styled box
                help_box_top = f"*{'*' * (w-2)}*"
                safe_addstr(stdscr, help_y-1, 0, help_box_top)
                safe_addstr(stdscr, help_y, w//2 - len(help_text)//2, help_text, curses.A_BOLD)
                safe_addstr(stdscr, help_y+1, 0, help_box_top)
            
            # Process input
            key = stdscr.getch()
            
            if input_mode:
                # Input mode
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
                # Normal mode
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('m') or key == ord('M'):
                    system_mode = "CRITICAL" if system_mode == "NORMAL" else "NORMAL"
                    command_output = f"System mode changed to: {system_mode}"
                elif key == ord('r') or key == ord('R'):
                    last_update = datetime.datetime.now()
                    command_output = "Display refreshed"
                elif key == ord('s') or key == ord('S'):
                    # Cycle through styles
                    if STYLE["theme"] == "military":
                        STYLE["theme"] = "wh40k"
                    elif STYLE["theme"] == "wh40k":
                        STYLE["theme"] = "tars"
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

def process_command(command):
    """Process a command and return output message"""
    global current_query, system_mode
    
    cmd = command.lower().strip()
    
    # Command: query
    if cmd.startswith("query "):
        new_query = command[6:].strip()
        if new_query:
            current_query = new_query
            return f"Query set to: {current_query}"
        else:
            return "Error: Query cannot be empty"
    
    # Command: mode changes
    elif cmd == "critical":
        system_mode = "CRITICAL"
        return "System mode set to CRITICAL"
    elif cmd == "normal":
        system_mode = "NORMAL"
        return "System mode set to NORMAL"
    
    # Command: style changes
    elif cmd.startswith("style "):
        style_arg = cmd[6:].strip().lower()
        if style_arg in ["military", "wh40k", "tars"]:
            STYLE["theme"] = style_arg
            return f"Interface style set to: {style_arg}"
        else:
            return f"Unknown style: {style_arg}. Available styles: military, wh40k, tars"
    
    # Command: help
    elif cmd == "help":
        return "Available commands: query <text>, critical, normal, style [military|wh40k|tars], help"
    
    # Unknown command
    else:
        return f"Unknown command: {command}"

def update_statuses():
    """Background thread to update monolith statuses"""
    while True:
        try:
            # Update each monolith status
            for name, info in MONOLITHS.items():
                # Check if vote file exists and when it was last modified
                if os.path.exists(info['vote_path']):
                    last_modified = os.path.getmtime(info['vote_path'])
                    if time.time() - last_modified > 300:  # No activity for 5 minutes
                        MONOLITHS[name]['status'] = "offline"
                    else:
                        # Check if pending or completed
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
            
            # Sleep before next update
            time.sleep(5)
        except:
            time.sleep(10)  # Longer sleep on error

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
    curses.wrapper(main)