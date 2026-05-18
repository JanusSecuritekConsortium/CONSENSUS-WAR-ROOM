"""
CONSENSUS SYSTEM v7.0.0 - Theme Management Module
Handles UI themes, colors, and visual styling for the system.
"""

from typing import Dict, Any
import flet as ft

class ConsensusThemes:
    """Theme manager for CONSENSUS SYSTEM UI"""
    
    THEMES = {
        "MILITARY": {
            "name": "Military Command",
            "primary_color": "#1a472a",
            "secondary_color": "#2d5a3d",
            "accent_color": "#4caf50",
            "text_color": "#00ff00",
            "error_color": "#ff4444",
            "warning_color": "#ffaa00",
            "info_color": "#00aaff",
            "background": "#0d1f0d",
            "surface": "#1a2e1a",
            "boot_logo": "military_boot.txt",
            "font_family": "Consolas",
            "monolith_colors": {
                "Rationalis": "#00ff88",
                "Bellator": "#ff4400", 
                "Aeternum": "#8800ff"
            }
        },
        
        "EVA": {
            "name": "Evangelion Unit",
            "primary_color": "#4a0080",
            "secondary_color": "#6600aa",
            "accent_color": "#ff6600",
            "text_color": "#00ffff",
            "error_color": "#ff0044",
            "warning_color": "#ffcc00",
            "info_color": "#00ccff",
            "background": "#1a0033",
            "surface": "#2d0055",
            "boot_logo": "eva_boot.txt",
            "font_family": "Courier New",
            "monolith_colors": {
                "Rationalis": "#00ffaa",
                "Bellator": "#ff2200",
                "Aeternum": "#aa00ff"
            }
        },
        
        "WH40K": {
            "name": "Warhammer 40K",
            "primary_color": "#8b0000",
            "secondary_color": "#aa1111",
            "accent_color": "#ffd700",
            "text_color": "#ffdddd",
            "error_color": "#ff0000",
            "warning_color": "#ff8800",
            "info_color": "#4488ff",
            "background": "#220000",
            "surface": "#330000",
            "boot_logo": "wh40k_boot.txt",
            "font_family": "Impact",
            "monolith_colors": {
                "Rationalis": "#00aa88",
                "Bellator": "#ff0000",
                "Aeternum": "#aa44ff"
            }
        }
    }
    
    def __init__(self, theme_name: str = "MILITARY"):
        self.current_theme = theme_name
        self.theme_data = self.THEMES.get(theme_name, self.THEMES["MILITARY"])
    
    def get_theme(self) -> Dict[str, Any]:
        """Get current theme configuration"""
        return self.theme_data.copy()
    
    def set_theme(self, theme_name: str) -> bool:
        """Change current theme"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.theme_data = self.THEMES[theme_name]
            return True
        return False
    
    def get_available_themes(self) -> list:
        """Get list of available theme names"""
        return list(self.THEMES.keys())
    
    def get_color(self, color_type: str) -> str:
        """Get specific color from current theme"""
        return self.theme_data.get(color_type, "#ffffff")
    
    def get_monolith_color(self, monolith_name: str) -> str:
        """Get color for specific monolith"""
        return self.theme_data.get("monolith_colors", {}).get(monolith_name, "#ffffff")
    
    def apply_to_page(self, page: ft.Page):
        """Apply theme colors to Flet page"""
        theme = self.get_theme()
        
        # Create custom theme
        page.theme = ft.Theme(
            color_scheme_seed=theme["accent_color"],
            use_material3=True
        )
        
        # Set theme mode
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = theme["background"]
        
        return page
    
    def create_styled_text(self, text: str, style: str = "text_color", size: int = 14) -> ft.Text:
        """Create styled text component"""
        return ft.Text(
            text,
            color=self.get_color(style),
            size=size,
            font_family=self.theme_data.get("font_family", "Consolas")
        )
    
    def create_styled_button(self, text: str, on_click=None, style: str = "primary") -> ft.ElevatedButton:
        """Create styled button component"""
        if style == "danger":
            color = self.get_color("error_color")
        elif style == "warning":
            color = self.get_color("warning_color")
        else:
            color = self.get_color("accent_color")
            
        return ft.ElevatedButton(
            text=text,
            on_click=on_click,
            bgcolor=color,
            color=self.get_color("text_color")
        )
