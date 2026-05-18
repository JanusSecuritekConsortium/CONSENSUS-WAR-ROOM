    # Draw monolith status boxes
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
    defcon = monolith_data.bellator["defcon_level"]
    defcon_color = 2 if defcon > 3 else 3 if defcon > 1 else 1
    
    system_info = f"Uptime: {uptime} | Theme: {theme_name} | DEFCON: {defcon}"
    safe_addstr(stdscr, info_y, 2, system_info, curses.color_pair(7))
    
    # Control instructions
    controls_y = height - 2
    controls = "Q:Quit | S:Theme | V:Vote | C:Console | 7:History | 1-3:Monolith Views | H:Help"
    safe_addstr(stdscr, controls_y, (width - len(controls)) // 2, controls, curses.color_pair(7))

# ================================================================================
# Enhanced Input Handling
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
        # Toggle config view or enter console mode
        if CONFIG["system"]["current_view"] == ViewMode.CONFIG.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.CONFIG.value
    elif key in (ord('1')):
        # Toggle RATIONALIS view
        if CONFIG["system"]["current_view"] == ViewMode.RATIONALIS.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.RATIONALIS.value
    elif key in (ord('2')):
        # Toggle AETERNUM view
        if CONFIG["system"]["current_view"] == ViewMode.AETERNUM.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.AETERNUM.value
    elif key in (ord('3')):
        # Toggle BELLATOR view
        if CONFIG["system"]["current_view"] == ViewMode.BELLATOR.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.BELLATOR.value
    elif key in (ord('7')):
        # Toggle decision history view
        if CONFIG["system"]["current_view"] == ViewMode.HISTORY.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
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
        # Toggle help view
        if CONFIG["system"]["current_view"] == ViewMode.HELP.value:
            CONFIG["system"]["current_view"] = ViewMode.MAIN.value
        else:
            CONFIG["system"]["current_view"] = ViewMode.HELP.value
    
    return True

def run_ui_loop(stdscr) -> None:
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
                elif current_view == ViewMode."""
CONSENSUS System Enhancement - Enhanced Monolith Views Module
This module adds detailed specialized views for each monolith with real-time data visualization,
performance metrics, and system status displays.

The enhancement maintains the tactical war room aesthetic while providing detailed visualizations
appropriate to each monolith's specialty (Rationalis - logical analysis, Aeternum - market data,
Bellator - security threats).
"""

import curses
import time
import datetime
import threading
import random
from typing import Dict, Any, List

# ================================================================================
# Monolith Data Visualization Module
# ================================================================================

def render_rationalis_screen(stdscr, theme: str = None) -> None:
    """
    Render specialized view for RATIONALIS monolith with logical analysis metrics
    showing efficiency charts, reasoning patterns, and logical flow diagrams.
    """
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
            timestamp = analysis.timestamp.strftime("%H:%M") if hasattr(analysis, "timestamp") else "??:??"
            
            # Display query and conclusion
            query = analysis.query if hasattr(analysis, "query") else "Unknown query"
            conclusion = analysis.conclusion if hasattr(analysis, "conclusion") else "No conclusion"
            
            # Format confidence with color
            confidence = analysis.confidence if hasattr(analysis, "confidence") else 0.0
            conf_color = 2 if confidence > 0.8 else 3 if confidence > 0.6 else 1
            confidence_str = f"({confidence:.0%})"
            
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

def render_aeternum_screen(stdscr, theme: str = None) -> None:
    """
    Render specialized view for AETERNUM monolith with financial metrics
    showing market charts, economic indicators, and trend analysis.
    """
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
    idx_row = 0
    idx_col = 0
    
    for name, data in indices.items():
        if 6 + idx_row < height - 10 and idx_col < 3:
            # Format values
            value = data.get("value", 0.0)
            change = data.get("change", 0.0)
            trend = data.get("trend", "flat")
            
            # Choose color based on trend
            trend_color = 2 if trend == "up" else 1 if trend == "down" else 3
            
            # Calculate position
            pos_x = 4 + idx_col * ((width - 8) // 3)
            pos_y = 6 + idx_row
            
            # Format display with arrow
            arrow = "▲" if trend == "up" else "▼" if trend == "down" else "◆"
            
            # Display index
            safe_addstr(stdscr, pos_y, pos_x, f"{name}: ", curses.color_pair(7))
            
            # Format value based on type (index, crypto, commodity)
            if "BTC" in name or "ETH" in name:
                value_text = f"${value:,.2f}"
            elif "S&P" in name or "NASDAQ" in name or "Dow" in name:
                value_text = f"{value:,.2f}"
            else:
                value_text = f"{value:.2f}"
            
            # Format change
            change_text = f" {arrow} {change:+.2f}%"
            
            # Display value and change
            safe_addstr(stdscr, pos_y, pos_x + len(name) + 2, value_text, curses.A_BOLD | curses.color_pair(7))
            safe_addstr(stdscr, pos_y, pos_x + len(name) + 2 + len(value_text), change_text, curses.color_pair(trend_color))
            
            # Update position counters
            idx_col += 1
            if idx_col >= 3:
                idx_col = 0
                idx_row += 1
    
    # Economic indicators section
    indicators_y = 6 + idx_row + 2
    safe_addstr(stdscr, indicators_y, 4, "ECONOMIC INDICATORS:", curses.A_BOLD | curses.color_pair(5))
    
    indicators = monolith_data.aeternum.get("economic_indicators", {})
    ind_row = 0
    ind_col = 0
    
    for name, value in indicators.items():
        if indicators_y + 1 + ind_row < height - 5 and ind_col < 3:
            # Calculate position
            pos_x = 4 + ind_col * ((width - 8) // 3)
            pos_y = indicators_y + 1 + ind_row
            
            # Display indicator
            safe_addstr(stdscr, pos_y, pos_x, f"{name}: {value}", curses.color_pair(7))
            
            # Update position counters
            ind_col += 1
            if ind_col >= 3:
                ind_col = 0
                ind_row += 1
    
    # Market forecast section (if available)
    forecast_y = height - 9
    safe_addstr(stdscr, forecast_y, 4, "TEMPORAL FORECAST:", curses.A_BOLD | curses.color_pair(5))
    
    # Generate a random forecast for now - in real implementation this would use actual data and models
    forecasts = [
        "Markets trending upward over next 72 hours with 68% confidence",
        "Increased volatility expected in tech sector through end of week",
        "Economic data release tomorrow likely to impact bond markets",
        "Cryptocurrency correlation with traditional assets weakening",
        "Defensive sectors showing relative strength against broader indices"
    ]
    
    for i, forecast in enumerate(forecasts[:3]):
        if forecast_y + 1 + i < height - 5:
            safe_addstr(stdscr, forecast_y + 1 + i, 4, f"→ {forecast}", curses.color_pair(7))
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_bellator_screen(stdscr, theme: str = None) -> None:
    """
    Render specialized view for BELLATOR monolith with tactical and security metrics
    showing threat assessments, geopolitical risks, and strategic recommendations.
    """
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
    defcon = monolith_data.bellator.get("defcon_level", 3)
    defcon_color = 2 if defcon > 3 else 3 if defcon > 1 else 1
    
    defcon_text = f"DEFCON Level: {defcon}"
    security_index = monolith_data.bellator.get("security_index", 72.5)
    security_text = f"Security Index: {security_index:.1f}"
    
    safe_addstr(stdscr, 3, width // 4 - len(defcon_text) // 2, defcon_text, 
               curses.A_BOLD | curses.color_pair(defcon_color))
    
    security_color = 2 if security_index > 80 else 3 if security_index > 50 else 1
    safe_addstr(stdscr, 3, 3*width // 4 - len(security_text) // 2, security_text, 
               curses.A_BOLD | curses.color_pair(security_color))
    
    # Draw main content box
    draw_themed_box(stdscr, 4, 2, height - 7, width - 4, theme)
    
    # Threat alerts section
    safe_addstr(stdscr, 5, 4, "ACTIVE THREAT ALERTS:", curses.A_BOLD | curses.color_pair(1))
    
    alerts = list(monolith_data.bellator.get("threat_alerts", []))
    for i, alert in enumerate(alerts[:6]):  # Display up to 6 alerts
        if 6 + i < height - 10:
            # Format alert data
            level = alert.level if hasattr(alert, "level") else "UNKNOWN"
            level_color = 1 if level == "HIGH" or level == "CRITICAL" else 3 if level == "MEDIUM" else 2
            
            description = alert.description if hasattr(alert, "description") else "Unknown threat"
            source = alert.source if hasattr(alert, "source") else "Unknown"
            
            # Format timestamp
            timestamp = alert.timestamp.strftime("%H:%M") if hasattr(alert, "timestamp") else "??:??"
            
            # Display the alert
            safe_addstr(stdscr, 6 + i, 4, f"[{timestamp}] [{level}]", curses.color_pair(level_color))
            alert_text = f"{description} (Source: {source})"
            alert_display = alert_text[:width - 25] + "..." if len(alert_text) > width - 25 else alert_text
            safe_addstr(stdscr, 6 + i, 20, alert_display, curses.color_pair(7))
    
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

def render_help_screen(stdscr) -> None:
    """
    Render a comprehensive help screen with keyboard shortcuts and command explanations.
    """
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Calculate dimensions for the help box
    help_height = height - 6
    help_width = width - 10
    help_y = 3
    help_x = 5
    
    # Draw themed box for help content
    theme = CONFIG["system"]["theme"]
    draw_themed_box(stdscr, help_y, help_x, help_height, help_width, theme)
    
    # Title based on theme
    if theme == "military":
        title = "CONSENSUS WAR ROOM - TACTICAL COMMAND REFERENCE"
    elif theme == "wh40k":
        title = "IMPERIAL COMMAND THRONE - OPERATION MANUAL"
    elif theme == "tars":
        title = "CONSENSUS.CORE - COMMAND.REFERENCE"
    elif theme == "helldivers":
        title = "SUPER EARTH COMMAND - OPERATION PROTOCOLS"
    elif theme == "eva":
        title = "NERV MAGI SYSTEM - COMMAND CENTER MANUAL"
    else:
        title = "CONSENSUS SYSTEM - COMMAND REFERENCE"
    
    safe_addstr(stdscr, help_y + 1, help_x + (help_width - len(title)) // 2, title, curses.A_BOLD)
    
    # Command sections
    command_sections = [
        ("NAVIGATION COMMANDS", [
            "M - Return to main view",
            "1 - View RATIONALIS monitor",
            "2 - View AETERNUM monitor",
            "3 - View BELLATOR monitor",
            "7 - View decision history",
            "9 - View diagnostics",
            "A - View analytics",
            "H - Toggle help screen",
            "Q - Quit system"
        ]),
        ("SYSTEM COMMANDS", [
            "S - Cycle interface themes",
            "C - Enter console mode",
            "V - Run demo vote",
            "R - Refresh display",
            "critical - Set system to CRITICAL mode",
            "normal - Set system to NORMAL mode",
            "reload - Reload configuration from disk"
        ]),
        ("MONOLITH COMMANDS", [
            "load <monolith> - Load model for specified monolith",
            "status - Display all monolith statuses",
            "vote <monolith> <query> - Generate vote from specific monolith",
            "consensus - Generate votes from all monoliths",
            "template <name> [params] - Apply query template"
        ]),
        ("DATA COMMANDS", [
            "query <text> - Set active query",
            "history [N] - Show last N decisions",
            "export json/csv/txt/all - Export decision history",
            "analyze - Run analytics on decision history"
        ])
    ]
    
    # Display command sections
    y_pos = help_y + 3
    for section_title, commands in command_sections:
        if y_pos < help_y + help_height - len(commands) - 2:
            safe_addstr(stdscr, y_pos, help_x + 2, section_title + ":", curses.A_BOLD)
            y_pos += 1
            
            for cmd in commands:
                safe_addstr(stdscr, y_pos, help_x + 4, cmd)
                y_pos += 1
                
            y_pos += 1
    
    # Footer with notification about pagination
    footer = "Press any key to return to previous view"
    safe_addstr(stdscr, help_y + help_height - 2, help_x + (help_width - len(footer)) // 2, 
              footer, curses.A_BOLD)

def update_rationalis_data() -> bool:
    """
    Update logical analysis data for RATIONALIS monolith with simulated metrics.
    In a production environment, this would fetch actual data from the model.
    """
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
        
        # Simulate efficiency rating with random walk
        current = monolith_data.rationalis.get("efficiency_rating", 0.85)
        monolith_data.rationalis["efficiency_rating"] = max(0.50, min(0.99, current + random.uniform(-0.02, 0.02)))
        
        # Generate a new logical analysis occasionally
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
        
        # Generate system logs occasionally
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
        
        # Update execution times for charting
        monolith_data.rationalis["execution_times"].append(random.uniform(0.1, 1.2))
        
        # Update confidence history for charting
        monolith_data.rationalis["confidence_history"].append(random.uniform(0.7, 0.98))
        
        # Update last updated timestamp
        monolith_data.rationalis["last_update"] = datetime.datetime.now()
        return True
    except Exception as e:
        log(f"Error updating AETERNUM data: {e}", LogLevel.ERROR, "MONOLITH")
        return False

def update_bellator_data() -> bool:
    """
    Update security and tactical data for BELLATOR monolith with simulated metrics.
    In a production environment, this would fetch real data from security APIs.
    """
    try:
        with security_lock:
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
        return False

def render_config_screen(stdscr) -> None:
    """
    Render the configuration screen with theme settings, 
    monolith options, and system parameters.
    """
    height, width = stdscr.getmaxyx()
    stdscr.clear()
    
    # Calculate dimensions for content area
    content_height = height - 6
    content_width = width - 10
    content_y = 3
    content_x = 5
    
    # Draw themed box for content
    theme = CONFIG["system"]["theme"]
    draw_themed_box(stdscr, content_y, content_x, content_height, content_width, theme)
    
    # Title
    if theme == "military":
        title = "CONSENSUS SYSTEM CONFIGURATION"
    elif theme == "wh40k":
        title = "ADEPTUS MECHANICUS CONFIGURATION"
    elif theme == "tars":
        title = "CONSENSUS.CORE.CONFIG"
    elif theme == "helldivers":
        title = "SUPER EARTH SYSTEM PARAMETERS"
    elif theme == "eva":
        title = "MAGI SYSTEM CONFIGURATION"
    else:
        title = "SYSTEM CONFIGURATION"
        
    safe_addstr(stdscr, content_y + 1, content_x + (content_width - len(title)) // 2, 
                title, curses.A_BOLD)
    
    # Display configuration sections
    y_pos = content_y + 3
    
    # System config section
    safe_addstr(stdscr, y_pos, content_x + 2, "SYSTEM CONFIGURATION:", curses.A_BOLD)
    y_pos += 1
    
    system_configs = [
        ("Theme", CONFIG["system"]["theme"]),
        ("Current View", CONFIG["system"]["current_view"]),
        ("System Mode", CONFIG["system"]["system_mode"]),
        ("Debug Mode", str(CONFIG["system"]["debug_mode"])),
        ("Max Log Entries", str(CONFIG["system"]["max_log_entries"])),
        ("Max Decisions", str(CONFIG["system"]["max_decisions"]))
    ]
    
    for key, value in system_configs:
        safe_addstr(stdscr, y_pos, content_x + 4, f"{key}: {value}")
        y_pos += 1
    
    y_pos += 1
    
    # Monolith configuration
    safe_addstr(stdscr, y_pos, content_x + 2, "MONOLITH CONFIGURATION:", curses.A_BOLD)
    y_pos += 1
    
    for name, config in CONFIG["monoliths"].items():
        model = config["model"]
        temp = config["temperature"]
        tokens = config["max_tokens"]
        
        safe_addstr(stdscr, y_pos, content_x + 4, f"{name}: {model} (Temp: {temp}, Tokens: {tokens})")
        y_pos += 1
    
    y_pos += 1
    
    # LLM provider config
    safe_addstr(stdscr, y_pos, content_x + 2, "LLM PROVIDER:", curses.A_BOLD)
    y_pos += 1
    
    llm_configs = [
        ("Provider", CONFIG["llm"]["provider"]),
        ("API Timeout", f"{CONFIG['llm']['api_timeout']}s"),
        ("Vote Timeout", f"{CONFIG['llm']['vote_timeout']}s"),
        ("Base URL", CONFIG["llm"]["base_url"]),
        ("Parallel Processing", str(CONFIG["llm"]["enable_parallel_processing"]))
    ]
    
    for key, value in llm_configs:
        safe_addstr(stdscr, y_pos, content_x + 4, f"{key}: {value}")
        y_pos += 1
    
    y_pos += 1
    
    # Health monitoring config
    if y_pos < content_y + content_height - 4:
        safe_addstr(stdscr, y_pos, content_x + 2, "HEALTH MONITORING:", curses.A_BOLD)
        y_pos += 1
        
        health_configs = [
            ("Enabled", str(CONFIG["health"]["enabled"])),
            ("Check Interval", f"{CONFIG['health']['check_interval']}s"),
            ("CPU Alert Threshold", f"{CONFIG['health']['alert_thresholds']['cpu']}%"),
            ("Memory Alert Threshold", f"{CONFIG['health']['alert_thresholds']['memory']}%")
        ]
        
        for key, value in health_configs:
            safe_addstr(stdscr, y_pos, content_x + 4, f"{key}: {value}")
            y_pos += 1
    
    # Instructions
    footer = "Press 'C' to return to previous view"
    safe_addstr(stdscr, content_y + content_height - 2, 
                content_x + (content_width - len(footer)) // 2, 
                footer, curses.A_BOLD)

# ================================================================================
# Enhanced Decision History View
# ================================================================================

def render_decision_history(stdscr) -> None:
    """
    Render enhanced decision history view with support for sorting, filtering,
    and detailed verdict information.
    """
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
    
    # Display detailed view of selected decision if implemented
    
    # Instructions
    safe_addstr(stdscr, height - 2, 2, "Press M to return to main view", curses.color_pair(3))

def render_main_screen(stdscr, theme: str = None) -> None:
    """
    Render the main CONSENSUS interface with improved layout and visualizations.
    """
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
            
            # Generate economic indicators with small changes
            indicators = {
                "Unemployment": f"{random.uniform(3.0, 6.0):.1f}%",
                "Inflation": f"{random.uniform(1.5, 4.5):.1f}%",
                "GDP Growth": f"{random.uniform(-0.5, 3.5):.1f}%",
                "Interest Rate": f"{random.uniform(2.0, 5.0):.2f}%",
                "Consumer Confidence": f"{random.uniform(70, 110):.1f}",
                "Manufacturing PMI": f"{random.uniform(45, 60):.1f}",
                "Housing Starts": f"{random.randint(1000, 1800)}K"
            }
            monolith_data.aeternum["economic_indicators"] = indicators
            
            # Update last updated timestamp
            monolith_data.aeternum["last_update"] = datetime.datetime.now()
            return True