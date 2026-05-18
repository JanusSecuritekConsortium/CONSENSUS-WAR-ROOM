"""
CONSENSUS SYSTEM v7.0.0 - Main Application
Enhanced modular multi-agent LLM architecture with Flet GUI
"""

import asyncio
import flet as ft
import traceback
from typing import Optional

# Import all modules
from consensus_config import CONFIG, log_system_change
from consensus_themes import ConsensusThemes
from consensus_animations import BootAnimations
from consensus_logging import get_logger, get_recent_logs
from consensus_llm import initialize_llm_system, shutdown_llm_system
from consensus_tts import initialize_tts, shutdown_tts, speak_system_event
from consensus_voting import process_consensus_request, get_consensus_stats

# Initialize logger
logger = get_logger(__name__)

class ConsensusGUI:
    """Main GUI application for CONSENSUS SYSTEM"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.theme_manager = ConsensusThemes(CONFIG.get("system.theme", "MILITARY"))
        self.boot_animations = BootAnimations(self.theme_manager)
        
        # UI Components
        self.chat_log = None
        self.input_box = None
        self.monolith_selector = None
        self.theme_selector = None
        self.status_bar = None
        self.log_viewer = None
        
        # State
        self.conversation_history = []
        self.system_ready = False
        
        # Setup page
        self.setup_page()
    
    def setup_page(self):
        """Setup the main page configuration"""
        self.page.title = f"CONSENSUS SYSTEM v{CONFIG.get('system.version')}"
        self.page.window_width = CONFIG.get("ui.window_width", 1200)
        self.page.window_height = CONFIG.get("ui.window_height", 800)
        self.page.window_resizable = CONFIG.get("ui.window_resizable", True)
        
        # Apply theme
        self.theme_manager.apply_to_page(self.page)
        
        # Set up event handlers
        self.page.on_window_event = self.on_window_event
        self.page.on_route_change = self.on_route_change
    
    async def initialize_system(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing CONSENSUS SYSTEM v7.0.0...")
            
            # Show boot animation
            await self.show_boot_sequence()
            
            # Initialize subsystems
            await self.init_subsystems()
            
            # Build main UI
            self.build_main_ui()
            
            self.system_ready = True
            logger.info("CONSENSUS SYSTEM initialization complete")
            speak_system_event("System ready for operation")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            await self.show_error_screen(f"Initialization failed: {str(e)}")
    
    async def show_boot_sequence(self):
        """Show the boot animation sequence"""
        if CONFIG.get("ui.boot_animation", True):
            await self.boot_animations.animate_boot_sequence(
                self.page,
                on_complete=lambda: None
            )
    
    async def init_subsystems(self):
        """Initialize all subsystems"""
        # Initialize LLM system
        await initialize_llm_system()
        
        # Initialize TTS
        initialize_tts()
        
        log_system_change("System components initialized")
    
    def build_main_ui(self):
        """Build the main user interface"""
        self.page.controls.clear()
        
        # Create components
        self.create_header()
        self.create_control_panel()
        self.create_chat_interface()
        self.create_input_section()
        self.create_log_section()
        self.create_status_bar()
        
        # Layout components
        main_content = ft.Column([
            self.header,
            self.control_panel,
            ft.Container(height=10),
            ft.Row([
                ft.Container(
                    content=self.chat_container,
                    expand=2,
                    padding=10
                ),
                ft.Container(
                    content=self.log_container,
                    expand=1,
                    padding=10
                )
            ], expand=True),
            self.input_section,
            self.status_bar
        ], expand=True, spacing=5)
        
        self.page.add(main_content)
        self.page.update()
    
    def create_header(self):
        """Create application header"""
        title_text = self.theme_manager.create_styled_text(
            f"🧠 CONSENSUS SYSTEM v{CONFIG.get('system.version')} - {self.theme_manager.theme_data['name']}",
            "accent_color",
            16
        )
        
        self.header = ft.Container(
            content=ft.Row([
                title_text,
                ft.Container(expand=True),
                self.theme_manager.create_styled_text(
                    f"Build: {CONFIG.get('system.build_date')}",
                    "text_color",
                    10
                )
            ]),
            bgcolor=self.theme_manager.get_color("surface"),
            padding=15,
            border_radius=5
        )
    
    def create_control_panel(self):
        """Create control panel with settings"""
        # Theme selector
        self.theme_selector = ft.Dropdown(
            label="Theme",
            options=[ft.dropdown.Option(theme) for theme in self.theme_manager.get_available_themes()],
            value=self.theme_manager.current_theme,
            on_change=self.on_theme_change,
            width=150
        )
        
        # Monolith selector
        self.monolith_selector = ft.Dropdown(
            label="Target Monolith",
            options=[
                ft.dropdown.Option("All", "All Monoliths"),
                ft.dropdown.Option("Rationalis", "Rationalis - Logic"),
                ft.dropdown.Option("Bellator", "Bellator - Action"),
                ft.dropdown.Option("Aeternum", "Aeternum - Wisdom")
            ],
            value="All",
            width=200
        )
        
        # Control buttons
        verdict_button = self.theme_manager.create_styled_button(
            "🔍 Get Verdict",
            self.get_latest_verdict
        )
        
        stats_button = self.theme_manager.create_styled_button(
            "📊 Statistics",
            self.show_statistics
        )
        
        settings_button = self.theme_manager.create_styled_button(
            "⚙️ Settings",
            self.show_settings
        )
        
        # Memory and voice toggles
        memory_toggle = ft.Switch(
            label="Context Memory",
            value=True,
            active_color=self.theme_manager.get_color("accent_color")
        )
        
        voice_toggle = ft.Switch(
            label="Voice Output",
            value=CONFIG.get("tts.enabled", True),
            on_change=self.on_voice_toggle,
            active_color=self.theme_manager.get_color("accent_color")
        )
        
        self.control_panel = ft.Container(
            content=ft.Row([
                self.theme_selector,
                self.monolith_selector,
                memory_toggle,
                voice_toggle,
                verdict_button,
                stats_button,
                settings_button
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            bgcolor=self.theme_manager.get_color("surface"),
            padding=10,
            border_radius=5
        )
    
    def create_chat_interface(self):
        """Create chat interface"""
        self.chat_log = ft.Column(
            scroll=ft.ScrollMode.ALWAYS,
            auto_scroll=CONFIG.get("ui.auto_scroll_chat", True),
            expand=True,
            spacing=5
        )
        
        # Add welcome message
        welcome_msg = self.create_system_message(
            "CONSENSUS SYSTEM v7.0.0 Online. Ready for queries.",
            "info"
        )
        self.chat_log.controls.append(welcome_msg)
        
        self.chat_container = ft.Container(
            content=self.chat_log,
            bgcolor=self.theme_manager.get_color("background"),
            padding=10,
            border_radius=5,
            border=ft.border.all(1, self.theme_manager.get_color("surface")),
            expand=True
        )
    
    def create_input_section(self):
        """Create input section"""
        self.input_box = ft.TextField(
            hint_text="Enter your proposal or query...",
            multiline=True,
            max_lines=3,
            expand=True,
            on_submit=self.send_message,
            border_color=self.theme_manager.get_color("accent_color"),
            focused_border_color=self.theme_manager.get_color("accent_color")
        )
        
        send_button = ft.IconButton(
            icon=ft.icons.SEND,
            icon_color=self.theme_manager.get_color("accent_color"),
            on_click=self.send_message,
            tooltip="Send message (Ctrl+Enter)"
        )
        
        clear_button = ft.IconButton(
            icon=ft.icons.CLEAR,
            icon_color=self.theme_manager.get_color("warning_color"),
            on_click=self.clear_chat,
            tooltip="Clear chat"
        )
        
        self.input_section = ft.Container(
            content=ft.Row([
                self.input_box,
                send_button,
                clear_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor=self.theme_manager.get_color("surface"),
            border_radius=5
        )
    
    def create_log_section(self):
        """Create log viewer section"""
        self.log_viewer = ft.Text(
            value=get_recent_logs(30),
            size=10,
            color=self.theme_manager.get_color("text_color"),
            font_family="Consolas"
        )
        
        log_scroll = ft.Column([
            self.log_viewer
        ], scroll=ft.ScrollMode.ALWAYS, height=200)
        
        refresh_log_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            icon_color=self.theme_manager.get_color("info_color"),
            on_click=self.refresh_logs,
            tooltip="Refresh logs"
        )
        
        export_log_button = ft.IconButton(
            icon=ft.icons.DOWNLOAD,
            icon_color=self.theme_manager.get_color("accent_color"),
            on_click=self.export_logs,
            tooltip="Export logs"
        )
        
        self.log_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.theme_manager.create_styled_text("System Logs", "accent_color", 12),
                    ft.Container(expand=True),
                    refresh_log_button,
                    export_log_button
                ]),
                ft.Divider(color=self.theme_manager.get_color("surface")),
                log_scroll
            ], spacing=5),
            bgcolor=self.theme_manager.get_color("surface"),
            padding=10,
            border_radius=5
        )
    
    def create_status_bar(self):
        """Create status bar"""
        self.status_text = self.theme_manager.create_styled_text("Ready", "accent_color", 10)
        
        # System status indicators
        monolith_status = ft.Row([
            ft.Icon(ft.icons.CIRCLE, color=self.theme_manager.get_monolith_color("Rationalis"), size=10),
            ft.Text("R", size=8),
            ft.Icon(ft.icons.CIRCLE, color=self.theme_manager.get_monolith_color("Bellator"), size=10),
            ft.Text("B", size=8),
            ft.Icon(ft.icons.CIRCLE, color=self.theme_manager.get_monolith_color("Aeternum"), size=10),
            ft.Text("A", size=8),
        ], spacing=2)
        
        self.status_bar = ft.Container(
            content=ft.Row([
                self.status_text,
                ft.Container(expand=True),
                monolith_status,
                self.theme_manager.create_styled_text(f"Theme: {self.theme_manager.current_theme}", "text_color", 8)
            ]),
            bgcolor=self.theme_manager.get_color("surface"),
            padding=8,
            height=30
        )
    
    def create_system_message(self, message: str, msg_type: str = "info") -> ft.Container:
        """Create a system message"""
        colors = {
            "info": self.theme_manager.get_color("info_color"),
            "success": self.theme_manager.get_color("accent_color"),
            "warning": self.theme_manager.get_color("warning_color"),
            "error": self.theme_manager.get_color("error_color")
        }
        
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        color = colors.get(msg_type, colors["info"])
        icon = icons.get(msg_type, icons["info"])
        
        return ft.Container(
            content=ft.Row([
                ft.Text(icon, size=14),
                ft.Text(f"[SYSTEM] {message}", color=color, size=12)
            ]),
            padding=5,
            bgcolor=self.theme_manager.get_color("surface"),
            border_radius=3
        )
    
    def create_monolith_message(self, monolith_name: str, message: str, 
                              vote: str = None, confidence: float = None) -> ft.Container:
        """Create a monolith response message"""
        monolith_color = self.theme_manager.get_monolith_color(monolith_name)
        
        # Build header
        header_parts = [f"[{monolith_name}]"]
        if vote:
            vote_icon = "✅" if vote == "approve" else "❌" if vote == "reject" else "🤷"
            header_parts.append(f"{vote_icon} {vote.upper()}")
        if confidence is not None:
            header_parts.append(f"({confidence:.1%})")
        
        header = " ".join(header_parts)
        
        return ft.Container(
            content=ft.Column([
                ft.Text(header, color=monolith_color, weight=ft.FontWeight.BOLD, size=12),
                ft.Text(message, color=self.theme_manager.get_color("text_color"), size=11)
            ], spacing=2),
            padding=10,
            margin=ft.margin.only(left=20),
            bgcolor=self.theme_manager.get_color("surface"),
            border_radius=5,
            border=ft.border.all(1, monolith_color)
        )
    
    def create_user_message(self, message: str) -> ft.Container:
        """Create a user message"""
        return ft.Container(
            content=ft.Text(f"👤 {message}", color=self.theme_manager.get_color("info_color"), size=12),
            padding=5,
            margin=ft.margin.only(right=20),
            bgcolor=self.theme_manager.get_color("background"),
            border_radius=3
        )
    
    async def send_message(self, e=None):
        """Send message to consensus system"""
        if not self.system_ready:
            return
        
        message = self.input_box.value.strip()
        if not message:
            return
        
        # Clear input
        self.input_box.value = ""
        self.page.update()
        
        # Add user message to chat
        user_msg = self.create_user_message(message)
        self.chat_log.controls.append(user_msg)
        self.page.update()
        
        # Update status
        self.update_status("Processing request...")
        
        # Show loading indicator
        loading_msg = self.boot_animations.create_loading_indicator("Consulting monoliths...")
        self.chat_log.controls.append(loading_msg)
        self.page.update()
        
        try:
            # Determine target
            target_monolith = None if self.monolith_selector.value == "All" else self.monolith_selector.value
            
            # Process consensus request
            result = await process_consensus_request(
                query=message,
                target_monolith=target_monolith,
                context=self.get_conversation_context()
            )
            
            # Remove loading indicator
            self.chat_log.controls.remove(loading_msg)
            
            # Add monolith responses
            for response in result.monolith_responses:
                monolith_msg = self.create_monolith_message(
                    response.monolith_name,
                    response.response.content,
                    response.vote,
                    response.confidence
                )
                self.chat_log.controls.append(monolith_msg)
            
            # Add consensus result
            result_msg = self.create_system_message(
                f"Consensus: {result.decision.upper()} (Confidence: {result.confidence:.1%}) - {result.reasoning}",
                "success" if result.decision in ["approved", "rejected"] else "warning"
            )
            self.chat_log.controls.append(result_msg)
            
            # Store in conversation history
            self.conversation_history.append({
                "user_message": message,
                "result": result,
                "timestamp": result.request.timestamp
            })
            
            # Limit conversation history
            if len(self.conversation_history) > CONFIG.get("ui.chat_history_limit", 500):
                self.conversation_history = self.conversation_history[-CONFIG.get("ui.chat_history_limit", 500):]
            
            self.update_status("Ready")
            
        except Exception as ex:
            # Remove loading indicator
            if loading_msg in self.chat_log.controls:
                self.chat_log.controls.remove(loading_msg)
            
            error_msg = self.create_system_message(f"Error: {str(ex)}", "error")
            self.chat_log.controls.append(error_msg)
            self.update_status("Error occurred")
            logger.error(f"Error processing message: {ex}")
        
        self.page.update()
    
    def get_conversation_context(self) -> list:
        """Get recent conversation context for LLM"""
        context = []
        recent_history = self.conversation_history[-5:]  # Last 5 exchanges
        
        for item in recent_history:
            context.append({"role": "user", "content": item["user_message"]})
            for response in item["result"].monolith_responses:
                context.append({
                    "role": "assistant", 
                    "content": f"[{response.monolith_name}] {response.response.content}"
                })
        
        return context
    
    def update_status(self, status: str):
        """Update status bar"""
        self.status_text.value = status
        self.status_text.color = self.theme_manager.get_color("accent_color")
        if hasattr(self, 'page'):
            self.page.update()
    
    async def on_theme_change(self, e):
        """Handle theme change"""
        new_theme = e.control.value
        if self.theme_manager.set_theme(new_theme):
            CONFIG.set("system.theme", new_theme)
            self.theme_manager.apply_to_page(self.page)
            
            # Show message
            msg = self.create_system_message(f"Theme changed to {new_theme}", "success")
            self.chat_log.controls.append(msg)
            
            # Rebuild UI with new theme
            self.build_main_ui()
            log_system_change(f"Theme changed to {new_theme}")
    
    def on_voice_toggle(self, e):
        """Handle voice toggle"""
        enabled = e.control.value
        CONFIG.set("tts.enabled", enabled)
        
        status = "enabled" if enabled else "disabled"
        msg = self.create_system_message(f"Voice output {status}", "info")
        self.chat_log.controls.append(msg)
        self.page.update()
    
    def clear_chat(self, e=None):
        """Clear chat log"""
        self.chat_log.controls.clear()
        welcome_msg = self.create_system_message("Chat cleared. Ready for new conversation.", "info")
        self.chat_log.controls.append(welcome_msg)
        self.conversation_history.clear()
        self.page.update()
    
    def refresh_logs(self, e=None):
        """Refresh system logs"""
        self.log_viewer.value = get_recent_logs(30)
        self.page.update()
    
    def export_logs(self, e=None):
        """Export system logs"""
        # In a real implementation, this would open a file save dialog
        msg = self.create_system_message("Log export feature would open file save dialog", "info")
        self.chat_log.controls.append(msg)
        self.page.update()
    
    def get_latest_verdict(self, e=None):
        """Get latest consensus verdict"""
        if not self.conversation_history:
            msg = self.create_system_message("No previous verdicts available", "warning")
            self.chat_log.controls.append(msg)
        else:
            latest = self.conversation_history[-1]
            result = latest["result"]
            verdict_msg = f"Latest verdict: {result.decision.upper()} (Confidence: {result.confidence:.1%})"
            msg = self.create_system_message(verdict_msg, "info")
            self.chat_log.controls.append(msg)
        
        self.page.update()
    
    def show_statistics(self, e=None):
        """Show system statistics"""
        stats = get_consensus_stats()
        
        if stats["total_requests"] > 0:
            stats_text = f"""Statistics:
• Total Requests: {stats['total_requests']}
• Average Confidence: {stats.get('average_confidence', 0):.1%}
• Success Rate: {stats.get('success_rate', 0):.1%}
• Average Time: {stats.get('average_deliberation_time', 0):.2f}s"""
        else:
            stats_text = "No statistics available yet"
        
        msg = self.create_system_message(stats_text, "info")
        self.chat_log.controls.append(msg)
        self.page.update()
    
    def show_settings(self, e=None):
        """Show settings dialog"""
        msg = self.create_system_message("Settings dialog would open here", "info")
        self.chat_log.controls.append(msg)
        self.page.update()
    
    async def show_error_screen(self, error_message: str):
        """Show error screen"""
        self.page.controls.clear()
        
        error_container = ft.Container(
            content=ft.Column([
                self.theme_manager.create_styled_text("SYSTEM ERROR", "error_color", 24),
                ft.Container(height=20),
                self.theme_manager.create_styled_text(error_message, "text_color", 14),
                ft.Container(height=30),
                self.theme_manager.create_styled_button(
                    "Retry Initialization",
                    self.retry_initialization
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True
        )
        
        self.page.add(error_container)
        self.page.update()
    
    async def retry_initialization(self, e=None):
        """Retry system initialization"""
        try:
            await self.initialize_system()
        except Exception as ex:
            await self.show_error_screen(f"Retry failed: {str(ex)}")
    
    def on_window_event(self, e):
        """Handle window events"""
        if e.data == "close":
            self.cleanup()
    
    def on_route_change(self, route):
        """Handle route changes"""
        pass
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Shutting down CONSENSUS SYSTEM...")
        
        # Shutdown subsystems
        try:
            asyncio.run(shutdown_llm_system())
            shutdown_tts()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("CONSENSUS SYSTEM shutdown complete")

async def main(page: ft.Page):
    """Main application entry point"""
    try:
        # Create and initialize GUI
        gui = ConsensusGUI(page)
        await gui.initialize_system()
        
        # Keep the app running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        logger.error(traceback.format_exc())
    finally:
        if 'gui' in locals():
            gui.cleanup()

if __name__ == "__main__":
    # Log system startup
    log_system_change("CONSENSUS SYSTEM v7.0.0 starting up")
    
    # Run the Flet app
    ft.app(target=main)
