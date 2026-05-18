import flet as ft
import random
from consensus_connector import (
    send_to_consensus,
    read_latest_verdict,
    read_log,
    execute_system_command
)
from consensus_themes import ConsensusThemes

def main(page: ft.Page):
    page.title = "CONSENSUS CyberUI"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 750

    # Randomly choose a theme at startup
    theme_options = ConsensusThemes().get_available_themes()
    random_theme = random.choice(theme_options)
    theme_manager = ConsensusThemes(random_theme)
    theme_manager.apply_to_page(page)

    logo_path = f"static/boot_logo_{random_theme}.txt"

    try:
        with open(logo_path, "r", encoding="utf-8") as f:
            splash = ft.Text(f.read(), color=theme_manager.get_color("text_color"), size=12)
    except FileNotFoundError:
        splash = ft.Text("[LOGO MISSING]", color="red", size=12)

    page.add(splash)
    page.update()
    import time; time.sleep(2)
    page.controls.clear()

    chat_log = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True, auto_scroll=True)
    input_box = ft.TextField(hint_text="Type proposal...", expand=True)

    monolith_selector = ft.Dropdown(
        label="Target Monolith",
        options=[
            ft.dropdown.Option("Rationalis"),
            ft.dropdown.Option("Bellator"),
            ft.dropdown.Option("Aeternum"),
        ],
        value="Rationalis"
    )

    memory_toggle = ft.Switch(label="Context Memory", value=True)
    theme_dropdown = ft.Dropdown(label="Theme", options=[
        ft.dropdown.Option(t) for t in theme_options
    ], value=random_theme)

    def send_message(e):
        content = input_box.value.strip()
        if not content:
            return
        chat_log.controls.append(ft.Text(f"> {content}", color="cyan"))
        response = send_to_consensus(content, monolith_selector.value)
        chat_log.controls.append(ft.Text(response, color="lightgreen"))
        input_box.value = ""
        page.update()

    def fetch_verdict(e):
        result = read_latest_verdict()
        chat_log.controls.append(ft.Text(result, color="magenta"))
        page.update()

    def refresh_log(e):
        log_viewer.value = read_log()
        page.update()

    def system_shutdown(e):
        chat_log.controls.append(ft.Text(execute_system_command("shutdown"), color="red"))
        page.update()

    def system_restart(e):
        chat_log.controls.append(ft.Text(execute_system_command("restart"), color="yellow"))
        page.update()

    verdict_button = ft.ElevatedButton(text="🔍 Get Verdict", on_click=fetch_verdict)
    refresh_log_button = ft.ElevatedButton(text="🔁 Refresh Log", on_click=refresh_log)
    shutdown_button = ft.OutlinedButton("💀 Shutdown AI", on_click=system_shutdown)
    restart_button = ft.OutlinedButton("♻ Restart AI", on_click=system_restart)

    log_viewer = ft.Text(read_log(), size=12)

    page.appbar = ft.AppBar(title=ft.Text("🧠 CONSENSUS SYSTEM UI"), center_title=True)
    page.add(
        ft.Row([memory_toggle, theme_dropdown, monolith_selector, verdict_button],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        chat_log,
        ft.Row([input_box, ft.IconButton(icon="send", on_click=send_message)]),
        ft.Container(content=log_viewer, bgcolor="#111111", padding=10, border_radius=5),
        ft.Row([refresh_log_button, shutdown_button, restart_button],
               alignment=ft.MainAxisAlignment.SPACE_EVENLY)
    )

ft.app(target=main)